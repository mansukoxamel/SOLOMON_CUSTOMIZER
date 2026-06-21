"""Build a normalized wide-title ROM and visual probe artifacts.

This is for checking what the emulator should show, using the same normalized
ROM that Mesen can open.  It also writes PNG/CSV artifacts so CHR bank3 tile
usage can be compared without relying on the editor UI.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
from collections import Counter
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtGui import QColor, QImage, QPainter, QPen

from magatu_skc.core import m66_expander
from magatu_skc.core import title_screen as TS
from magatu_skc.nes.palette import NES_COLORS

TITLE_W = 256
TITLE_H = 240
NT_W = 32
BG_BASE = 0x100
DEFAULT_MESEN = Path(r"C:\Users\jinn\Desktop\Mesen.0.9.9\Mesen.exe")


def parse_tile_list(text: str) -> list[int]:
    out: list[int] = []
    for part in str(text).replace(";", ",").split(","):
        s = part.strip().lower()
        if not s:
            continue
        out.append(int(s, 16 if s.startswith("0x") else 10))
    return out


def title_palette(rom: bytearray) -> list[int]:
    off = 0x10 + (0x958A - 0x8000)
    if off + 19 <= len(rom) and rom[off] == 0x3F and rom[off + 1] == 0x00:
        ctrl = rom[off + 2]
        if ctrl & 0x40 and (ctrl & 0x3F) + 1 >= 16:
            return [rom[off + 3 + i] & 0x3F for i in range(16)]
    return [
        0x0F, 0x0F, 0x10, 0x30,
        0x0F, 0x0F, 0x27, 0x30,
        0x0F, 0x0F, 0x16, 0x30,
        0x0F, 0x0F, 0x27, 0x38,
    ]


def title_attributes(rom: bytearray) -> list[int]:
    attr = [0xFF] * 64
    off = 0x4D68
    if off + 21 <= len(rom):
        src = bytes(rom[off:off + 21])
        for i in range(21):
            attr[9 + i] = src[20 - i]
    attr[42] = 0xCF
    off2 = 0x10 + (0xCDF5 - 0x8000)
    if off2 + 7 <= len(rom):
        src = bytes(rom[off2:off2 + 7])
        for i in range(7):
            attr[48 + i] = src[6 - i]
    for i in range(8):
        attr[56 + i] = 0xF5
    return attr


def attr_palette_no(attr: list[int], row: int, col: int) -> int:
    ai = (row // 4) * 8 + (col // 4)
    qx = (col % 4) // 2
    qy = (row % 4) // 2
    return (attr[ai] >> ((qy * 2 + qx) * 2)) & 0x03


def render_title(rom: bytearray, grid: list[int]) -> QImage:
    tiles = TS.get_chr_bank3_tiles(rom)
    pal = title_palette(rom)
    attr = title_attributes(rom)
    img = QImage(TITLE_W, TITLE_H, QImage.Format_RGB888)
    for cell, stream in enumerate(grid):
        row, col = divmod(cell, NT_W)
        bank_tile = (BG_BASE + (int(stream) & 0xFF)) & 0x1FF
        px = tiles[bank_tile].pixels
        pal_no = attr_palette_no(attr, row, col)
        ox = col * 8
        oy = row * 8
        for y in range(8):
            for x in range(8):
                pi = px[y][x] & 0x03
                nes_idx = pal[0] if pi == 0 else pal[pal_no * 4 + pi]
                r, g, b = NES_COLORS[nes_idx & 0x3F]
                img.setPixelColor(ox + x, oy + y, QColor(r, g, b))
    return img


def display_corrected(img: QImage) -> QImage:
    out = QImage(TITLE_W, TITLE_H, QImage.Format_RGB888)
    for y in range(TITLE_H):
        sy = (y - 1) % TITLE_H
        for x in range(TITLE_W):
            sx = (x - 8) % TITLE_W
            out.setPixelColor(x, y, img.pixelColor(sx, sy))
    return out


def draw_grid(img: QImage) -> None:
    p = QPainter(img)
    p.setPen(QPen(QColor(255, 255, 255, 90), 1))
    for x in range(0, TITLE_W + 1, 8):
        p.drawLine(x, 0, x, TITLE_H)
    for y in range(0, TITLE_H + 1, 8):
        p.drawLine(0, y, TITLE_W, y)
    p.end()


def draw_highlight(img: QImage, grid: list[int], bank_tile: int) -> int:
    stream = (int(bank_tile) - BG_BASE) & 0xFF
    p = QPainter(img)
    p.setBrush(QColor(255, 0, 180, 90))
    p.setPen(QPen(QColor(255, 70, 210), 2))
    count = 0
    for cell, t in enumerate(grid):
        if (int(t) & 0xFF) != stream:
            continue
        row, col = divmod(cell, NT_W)
        dx = ((col * 8) + 8) % TITLE_W
        dy = ((row * 8) + 1) % TITLE_H
        p.drawRect(dx, dy, 7, 7)
        count += 1
    p.end()
    return count


def save_usage_csv(path: Path, grid: list[int], chr_start: int) -> Counter:
    counts = Counter((BG_BASE + (int(t) & 0xFF)) & 0x1FF for t in grid)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bank_tile_hex", "stream_hex", "count", "first_cells", "rom_file_start", "rom_file_end"])
        for bank_tile in sorted(counts):
            stream = (bank_tile - BG_BASE) & 0xFF
            cells = [i for i, t in enumerate(grid) if ((BG_BASE + (int(t) & 0xFF)) & 0x1FF) == bank_tile]
            first = " ".join(f"({c % NT_W},{c // NT_W})" for c in cells[:12])
            f0 = chr_start + bank_tile * 0x10
            w.writerow([f"0x{bank_tile:03X}", f"0x{stream:02X}", counts[bank_tile], first, f"0x{f0:X}", f"0x{f0 + 0x0F:X}"])
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(ROOT / "ROM" / "Solomon no Kagi (J).nes"))
    ap.add_argument("--outdir", default=str(ROOT / "test_output" / "title_wide_emulator_probe"))
    ap.add_argument("--tiles", default="0x1DE,0x1DF")
    ap.add_argument("--mesen", default=str(DEFAULT_MESEN))
    ap.add_argument("--launch-mesen", action="store_true")
    args = ap.parse_args()

    source = Path(args.source)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles = parse_tile_list(args.tiles)

    src = source.read_bytes()
    rom = bytearray(m66_expander.change_mapper(src, region="JP"))
    messages = TS.normalize_title_to_wide(rom)
    rom_path = outdir / "normalized_wide_title_probe.nes"
    rom_path.write_bytes(rom)

    info = TS.decode_title_grid(rom)
    grid = [int(t) & 0xFF for t in info["grid"]]
    chr_start = TS.chr_bank3_offset(rom)
    usage = save_usage_csv(outdir / "tile_usage.csv", grid, chr_start)

    base = display_corrected(render_title(rom, grid))
    grid_img = QImage(base)
    draw_grid(grid_img)
    grid_img.save(str(outdir / "title_preview_grid.png"))

    rows = []
    for bank_tile in tiles:
        img = QImage(grid_img)
        count = draw_highlight(img, grid, bank_tile)
        out_png = outdir / f"title_tile_{bank_tile:03X}_highlight.png"
        img.save(str(out_png))
        stream = (bank_tile - BG_BASE) & 0xFF
        rows.append(f"bank内 0x{bank_tile:03X} / stream 0x{stream:02X}: grid {usage.get(bank_tile, 0)} cells, highlight {count} cells")

    report = outdir / "README_title_wide_probe.txt"
    report.write_text(
        "\n".join([
            "Title wide emulator probe",
            f"source: {source}",
            f"normalized ROM: {rom_path}",
            f"CHR bank3 start: 0x{chr_start:X}",
            "",
            *messages,
            "",
            "Target tile summary:",
            *rows,
            "",
            "Open normalized_wide_title_probe.nes in Mesen and compare with:",
            "  title_preview_grid.png",
            "  title_tile_XXX_highlight.png",
            "  tile_usage.csv",
            "",
        ]),
        encoding="utf-8",
    )

    if args.launch_mesen:
        mesen = Path(args.mesen)
        if not mesen.exists():
            raise FileNotFoundError(f"Mesen.exe not found: {mesen}")
        subprocess.Popen([str(mesen), str(rom_path)])

    print(report.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
