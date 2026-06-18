#!/usr/bin/env python3
"""Audit PRG0 padding/cave candidates for the JP mapper66 target.

This is a read-only tool. It scans the original JP ROM for repeated-byte runs,
cross-checks known implementation reservations, and reports whether each run is
already used, known dangerous, statically referenced, or a candidate that still
needs human review.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ROM = ROOT / "ROM" / "Solomon no Kagi (J).nes"
PRG0_FILE_START = 0x10
PRG0_FILE_END = 0x4010


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    kind: str

    def overlaps(self, start: int, end: int) -> bool:
        return self.start < end and start < self.end


ABS_OPS = {
    0x20: "JSR abs",
    0x4C: "JMP abs",
    0x6C: "JMP (abs)",
    0xAD: "LDA abs",
    0xAE: "LDX abs",
    0xAC: "LDY abs",
    0x8D: "STA abs",
    0x8E: "STX abs",
    0x8C: "STY abs",
    0x2D: "AND abs",
    0x0D: "ORA abs",
    0x4D: "EOR abs",
    0x6D: "ADC abs",
    0xED: "SBC abs",
    0xCD: "CMP abs",
    0xEC: "CPX abs",
    0xCC: "CPY abs",
    0x2C: "BIT abs",
    0x0E: "ASL abs",
    0x4E: "LSR abs",
    0x2E: "ROL abs",
    0x6E: "ROR abs",
    0xCE: "DEC abs",
    0xEE: "INC abs",
}

INDEXED_OPS = {
    0xBD: "LDA abs,X",
    0xB9: "LDA abs,Y",
    0xBE: "LDX abs,Y",
    0xBC: "LDY abs,X",
    0x9D: "STA abs,X",
    0x99: "STA abs,Y",
    0x3D: "AND abs,X",
    0x39: "AND abs,Y",
    0x1D: "ORA abs,X",
    0x19: "ORA abs,Y",
    0x5D: "EOR abs,X",
    0x59: "EOR abs,Y",
    0x7D: "ADC abs,X",
    0x79: "ADC abs,Y",
    0xFD: "SBC abs,X",
    0xF9: "SBC abs,Y",
    0xDD: "CMP abs,X",
    0xD9: "CMP abs,Y",
    0x1E: "ASL abs,X",
    0x5E: "LSR abs,X",
    0x3E: "ROL abs,X",
    0x7E: "ROR abs,X",
    0xDE: "DEC abs,X",
    0xFE: "INC abs,X",
}


def cpu_to_file(cpu: int) -> int:
    return PRG0_FILE_START + (int(cpu) - 0x8000)


def file_to_cpu(off: int) -> int:
    return 0x8000 + (int(off) - PRG0_FILE_START)


def known_ng_spans() -> list[Span]:
    return [
        Span(0x5A25, 0x5B9D, "enemy state-speed index data", "NG"),
        Span(0x5B71, 0x5B85, "gargoyle smoke-loop bug source, state-speed data", "NG"),
        Span(0x5BA9, 0x5BEF, "enemy speed table", "NG"),
        Span(0x5C10, 0x5C22, "mirror rate tables", "NG"),
        Span(0x5C30, 0x5C4A, "mirror enemy pointer table", "NG"),
        Span(0x5C82, 0x5CB3, "original sentinel/table data", "NG"),
        Span(0x5CFC, 0x5D65, "enemy data pointer table", "NG"),
        Span(0x6A2C, 0x6A95, "item data pointer table", "NG"),
    ]


def reserved_spans() -> list[Span]:
    from magatu_skc.core import (
        gargoyle_variant,
        key_enemy_runtime,
        m66,
        panel_monster_stage_variant,
        panel_monster_variant,
        room_flags,
        saramandor_variant,
        solomon_seal_block,
        spark_ball_variant,
        stage_announcement,
    )

    spans: list[Span] = []
    modules = [
        m66,
        solomon_seal_block,
        gargoyle_variant,
        panel_monster_variant,
        panel_monster_stage_variant,
        spark_ball_variant,
        saramandor_variant,
        key_enemy_runtime,
        stage_announcement,
    ]
    for mod in modules:
        for off, size in getattr(mod, "RESERVED_SPANS", ()):
            if off < PRG0_FILE_END:
                spans.append(Span(off, off + size, mod.__name__.rsplit(".", 1)[-1], "reserved"))
    for label, off, size in [
        ("initial_magic/initial_lives", 0x0BF2, 0x1C),
        ("m66 key cell patch", 0x17F5, 0x0F),
        ("spark_ball property selector compression", 0x2569, 0x15),
        ("spark_ball animation hook", 0x4FEE, 0x17),
        ("panel variant type classifier tail", 0x5AC9, 0x14),
        ("panel/spark property selector", 0x5BEF, 0x1C),
        ("spark ball pause hook", 0x6FD4, 0x31),
        ("room_flags.LOADER", room_flags.OFF_LOADER_CAVE, len(room_flags.LOADER_CAVE)),
        ("room_flags.MAGIC", room_flags.OFF_MAGIC_CAVE, len(room_flags.MAGIC_CAVE)),
        ("room_flags.DOOR", room_flags.OFF_DOOR_CAVE, len(room_flags.DOOR_CAVE)),
        ("room_flags.DARK", room_flags.OFF_DARK_CAVE, room_flags.DARK_CAVE_RESERVED_SIZE),
        ("room_flags.BW", room_flags.OFF_BW_CAVE, room_flags.BW_CAVE_RESERVED_SIZE),
        ("room_flags.VISIBLE_HELPER", room_flags.OFF_VISIBLE_INBLOCK_HELPER, len(room_flags.VISIBLE_INBLOCK_HELPER)),
        ("room_flags.WHITE_EXT", room_flags.OFF_WHITE_INBLOCK_RUNTIME_EXT, len(room_flags.WHITE_INBLOCK_RUNTIME_EXT)),
    ]:
        spans.append(Span(off, off + size, label, "reserved"))
    return sorted(spans, key=lambda s: (s.start, s.end, s.label))


def repeated_runs(data: bytes, min_len: int) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    i = PRG0_FILE_START
    while i < min(len(data), PRG0_FILE_END):
        b = data[i]
        j = i + 1
        while j < min(len(data), PRG0_FILE_END) and data[j] == b:
            j += 1
        if j - i >= min_len:
            runs.append((i, j, b))
        i = j
    return runs


def operand_hits(data: bytes, start: int, end: int) -> list[str]:
    cpu_start = file_to_cpu(start)
    cpu_end = file_to_cpu(end - 1)
    hits: list[str] = []
    scan_end = min(len(data) - 2, PRG0_FILE_END)
    for off in range(PRG0_FILE_START, scan_end):
        op = data[off]
        operand = data[off + 1] | (data[off + 2] << 8)
        pc = file_to_cpu(off)
        if op in ABS_OPS and cpu_start <= operand <= cpu_end:
            hits.append(f"${pc:04X} {ABS_OPS[op]} ${operand:04X}")
        if op in INDEXED_OPS and operand <= cpu_end and operand + 0xFF >= cpu_start:
            hits.append(f"${pc:04X} {INDEXED_OPS[op]} ${operand:04X}")
    return hits


def pointer_hits(data: bytes, start: int, end: int) -> list[str]:
    hits: list[str] = []
    for cpu in range(file_to_cpu(start), file_to_cpu(end - 1) + 1):
        pat = bytes((cpu & 0xFF, cpu >> 8))
        pos = data.find(pat)
        while pos >= 0:
            if PRG0_FILE_START <= pos < PRG0_FILE_END:
                hits.append(f"${cpu:04X} at file 0x{pos:04X} CPU ${file_to_cpu(pos):04X}")
            pos = data.find(pat, pos + 1)
    return hits


def classify(start: int, end: int, reserved: list[Span], ng: list[Span], op_hits: list[str]) -> tuple[str, str]:
    ng_hits = [s for s in ng if s.overlaps(start, end)]
    if ng_hits:
        return "NG", ", ".join(s.label for s in ng_hits[:3])
    res_hits = [s for s in reserved if s.overlaps(start, end)]
    if res_hits:
        return "reserved", ", ".join(s.label for s in res_hits[:3])
    if op_hits:
        return "referenced", "; ".join(op_hits[:3])
    return "candidate", "needs ASM boundary review and optional Mesen READ/EXEC probe"


def emit_markdown(data: bytes, min_len: int) -> str:
    reserved = reserved_spans()
    ng = known_ng_spans()
    rows: list[str] = []
    counts: dict[str, int] = {}
    for start, end, byte in repeated_runs(data, min_len):
        op_hits = operand_hits(data, start, end)
        ptr_hits = pointer_hits(data, start, end)
        status, note = classify(start, end, reserved, ng, op_hits)
        if status == "candidate" and ptr_hits:
            status = "pointer-bytes"
            note = "possible pointer byte sequence: " + "; ".join(ptr_hits[:3])
        counts[status] = counts.get(status, 0) + 1
        rows.append(
            "| {status} | `0x{start:04X}-0x{endm:04X}` | `${cpus:04X}-${cpue:04X}` | "
            "`{byte:02X}` | {size} | {note} |".format(
                status=status,
                start=start,
                endm=end - 1,
                cpus=file_to_cpu(start),
                cpue=file_to_cpu(end - 1),
                byte=byte,
                size=end - start,
                note=note.replace("|", "/"),
            )
        )
    out = [
        "# PRG0 Free Space Audit",
        "",
        "Generated by `tools/prg0_free_space_audit.py`.",
        "",
        "## Summary",
        "",
    ]
    for key in sorted(counts):
        out.append(f"- {key}: {counts[key]}")
    out.extend([
        "",
        "## Runs",
        "",
        "| Status | File offset | CPU | Byte | Size | Note |",
        "| --- | --- | --- | --- | ---: | --- |",
        *rows,
        "",
    ])
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM, help="Original JP ROM path")
    parser.add_argument("--min-len", type=int, default=4, help="Minimum repeated-byte run length")
    args = parser.parse_args()

    data = args.rom.read_bytes()
    print(emit_markdown(data, args.min_len))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
