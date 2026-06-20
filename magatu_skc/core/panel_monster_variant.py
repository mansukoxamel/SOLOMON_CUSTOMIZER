"""Panel Monster borrowed-ID variants.

JP/JPC66 only.  The original Panel Monster IDs are $24-$27.  This patch
repurposes the finalized borrowed IDs as two stronger Panel Monster families:

  $52/$53/$56/$57 -> two diagonal shots
  $5A/$5B/$66/$67 -> three-way shots

The borrowed IDs keep their own type byte so the fire hook can identify the
variant.  Their init properties and animation metadata are changed to Panel
Monster values, and their AI table entries are routed through small wrappers
that force the intended direction bits before entering the stock Panel AI.
"""

from __future__ import annotations


class PanelMonsterVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


def _cpu(file_off: int) -> int:
    return 0x8000 + (file_off - 0x10)


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


class _Asm:
    def __init__(self):
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def b(self, *vals: int) -> None:
        self.code.extend(v & 0xFF for v in vals)

    def label(self, name: str) -> None:
        self.labels[name] = len(self.code)

    def branch(self, opcode: int, label: str) -> None:
        self.b(opcode, 0x00)
        self.fixups.append((len(self.code) - 1, label))

    def jmp(self, cpu: int) -> None:
        self.b(0x4C, cpu & 0xFF, (cpu >> 8) & 0xFF)

    def finish(self) -> bytes:
        for off, label in self.fixups:
            target = self.labels[label]
            rel = target - (off + 1)
            if not -128 <= rel <= 127:
                raise PanelMonsterVariantError(f"branch to {label} is out of range")
            self.code[off] = rel & 0xFF
        return bytes(self.code)


# Hook sites.
OFF_HOOK_PANEL_FIRE = _cf(0xA556)
OFF_HOOK_BULLET_MOVE = _cf(0xAFBB)

OFF_AI_DEMON_52_53 = _cf(0xA34C)
OFF_AI_DEMON_56_57 = _cf(0xA34E)
OFF_AI_DEMON_5A_5B = _cf(0xA350)
OFF_AI_SARAM_66_67 = _cf(0xA356)

OFF_PROPERTY_TABLE = _cf(0xA30E)
OFF_ANIM_META_TABLE = 0x50F8
OFF_A2CC = _cf(0xA2CC)
OFF_8B05 = _cf(0x8B05)

ORIG_PANEL_FIRE = bytes.fromhex(
    "a0 01 b1 2c c9 10 90 16 a0 03 b1 2e 29 03 aa 20 76 ae "
    "a0 03 98 31 2e 91 2e 88 a9 00 91 2c 60"
)
ORIG_FIRE_DELAY = 0x10
SNAPPY_FIRE_DELAY = 0x01
ORIG_BULLET_MOVE_HOOK = bytes.fromhex("20 01 b2")
ORIG_AI_DEMON = _word(0xB208)
ORIG_AI_SARAM = _word(0xB038)
ORIG_A2CC_HEAD = bytes.fromhex("B9 0E A3")
ORIG_8B05_HEAD = bytes.fromhex("B9 E8 D0 85 0A B9 E9 D0 85 0B")

ORIG_PANEL_GROUP_PROPERTIES = {
    14: 0x00,
    15: 0x00,
    16: 0x00,
    19: 0x00,
}
ORIG_PANEL_GROUP_ANIMS = {
    20: _word(0xD3EA),
    21: _word(0xD3EA),
    22: _word(0xD3EA),
    25: _word(0xD45A),
}
PANEL_PROPERTY = 0x08
PANEL_ANIM_META = _word(0xD33A)

CPU_FIRE_DISPATCH = _cpu(0x3CE2)       # $BCD2
CPU_AI_SARAM_WRAPPER = _cpu(0x3C6B)    # $BC5B
CPU_FIRE_3WAY = _cpu(0x3D98)           # $BD88
CPU_BULLET_HOOK = _cpu(0x3F79)         # $BF69
CPU_FIRE_2WAY = _cpu(0x4098)           # $C088
CPU_AI_DEMON_WRAPPER = _cpu(0x4156)    # $C146
CPU_PANEL_STAGE_AI_DEMON_WRAPPER = _cpu(0x68C4) # $E8B4, Panel Variant A/B/C override
CPU_PROPERTY_HOOK = _cpu(0x5BEF)       # $DBDF
CPU_ANIM_HOOK = _cpu(0x40D2)           # $C0C2
CPU_SPARK_PROPERTY_HOOK = _cpu(0x3E72) # $BE62
CPU_SPARK_PROPERTY_HOOK_CURRENT = _cpu(0x2569) # $A559
CPU_SPARK_ANIM_HOOK = _cpu(0x4FEE)     # $CFDE

OFF_FIRE_DISPATCH = _cf(CPU_FIRE_DISPATCH)
OFF_AI_SARAM_WRAPPER = _cf(CPU_AI_SARAM_WRAPPER)
OFF_FIRE_3WAY = _cf(CPU_FIRE_3WAY)
OFF_BULLET_HOOK = _cf(CPU_BULLET_HOOK)
BULLET_HOOK_SLOT_SIZE = 0x51
OFF_FIRE_2WAY = _cf(CPU_FIRE_2WAY)
OFF_AI_DEMON_WRAPPER = _cf(CPU_AI_DEMON_WRAPPER)
OFF_PROPERTY_HOOK = _cf(CPU_PROPERTY_HOOK)
OFF_ANIM_HOOK = _cf(CPU_ANIM_HOOK)

HOOK_PANEL_FIRE = bytes.fromhex("4c") + _word(CPU_FIRE_DISPATCH) + bytes([0xEA] * 28)
HOOK_PANEL_FIRE_HEAD = HOOK_PANEL_FIRE[:3]
HOOK_BULLET_MOVE = bytes.fromhex("20") + _word(CPU_BULLET_HOOK)
HOOK_A2CC = bytes.fromhex("20") + _word(CPU_PROPERTY_HOOK)
HOOK_8B05 = bytes.fromhex("20") + _word(CPU_ANIM_HOOK) + bytes([0xEA] * 7)
HOOK_A2CC_SPARK = bytes.fromhex("20") + _word(CPU_SPARK_PROPERTY_HOOK)
HOOK_A2CC_SPARK_CURRENT = bytes.fromhex("20") + _word(CPU_SPARK_PROPERTY_HOOK_CURRENT)
HOOK_8B05_SPARK = bytes.fromhex("20") + _word(CPU_SPARK_ANIM_HOOK) + bytes([0xEA] * 7)
SPARK_PROPERTY_HOOK_CURRENT_BODY = bytes.fromhex(
    "a5 05 29 fe 38 e9 6a c9 0d b0 07 29 03 d0 03 "
    "a9 19 60 4c df db"
)


RAW_FIRE_2WAY = bytearray.fromhex(
    "a0 01 b1 2c c9 10 90 4c a0 03 b1 2e 29 03 aa 20 76 ae "
    "a9 01 20 39 be 20 ea b2 90 29 8a a0 06 91 2c a0 00 a9 "
    "80 91 04 a0 03 b1 2e 29 03 aa 20 76 ae a9 02 20 39 be "
    "4c 45 be 48 a5 02 20 56 b1 a0 07 68 91 00 60 a0 03 98 "
    "31 2e 91 2e 88 a9 00 91 2c 88 91 2c 60"
)

RAW_FIRE_3WAY = bytearray.fromhex(
    "a0 01 b1 2c c9 10 90 6b a0 03 b1 2e 29 03 aa 20 76 ae "
    "a9 01 20 58 be 20 ea b2 90 48 8a a0 06 91 2c a0 00 a9 "
    "80 91 04 a0 03 b1 2e 29 03 aa 20 76 ae a9 00 20 58 be "
    "20 ea b2 90 29 8a a0 06 91 2c a0 00 a9 80 91 04 a0 03 "
    "b1 2e 29 03 aa 20 76 ae a9 02 20 58 be 4c 64 be 48 a5 "
    "02 20 56 b1 a0 07 68 91 00 60 a0 03 98 31 2e 91 2e 88 "
    "a9 00 91 2c 88 91 2c 60"
)


def _relocate_fire(raw: bytearray, base_cpu: int, helper_off: int, exit_off: int,
                   marker_a: int | None = None, marker_b: int | None = None,
                   helper_cpu: int | None = None, exit_cpu: int | None = None) -> bytes:
    blob = bytearray(raw)
    if marker_a is not None:
        blob[18:20] = bytes([0xA9, marker_a & 0xFF])
    if marker_b is not None:
        at = blob.rfind(bytes.fromhex("a9 02"))
        if at < 0:
            raise PanelMonsterVariantError("second marker opcode not found")
        blob[at:at + 2] = bytes([0xA9, marker_b & 0xFF])
    for i in range(len(blob) - 2):
        if blob[i] in (0x20, 0x4C):
            old = blob[i + 1] | (blob[i + 2] << 8)
            if old == 0xBE00 + helper_off:
                blob[i + 1:i + 3] = _word(helper_cpu or (base_cpu + helper_off))
            elif old == 0xBE00 + exit_off:
                blob[i + 1:i + 3] = _word(exit_cpu or (base_cpu + exit_off))
    return bytes(blob)


def _with_fire_delay(blob: bytes, fire_delay: int) -> bytes:
    out = bytearray(blob)
    if len(out) > 5 and out[4] == 0xC9:
        out[5] = fire_delay & 0xFF
    return bytes(out)


def _build_fire_3way(fire_delay: int) -> bytes:
    return _build_fire_common(fire_delay)


def _build_fire_common(fire_delay: int) -> bytes:
    a = _Asm()
    # Entry points set X = marker table offset: 0=2-way, 3=3-way, 7=normal.
    a.label("normal_entry")
    a.b(0xA2, 0x07); a.branch(0xD0, "start")
    a.label("three_entry")
    a.b(0xA2, 0x03); a.branch(0xD0, "start")
    a.label("two_entry")
    a.b(0xA2, 0x00)
    a.label("start")
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0xC9, fire_delay & 0xFF)
    a.branch(0x90, "rts")
    a.label("loop")
    a.b(0x8A, 0x48)                   # save marker-table offset
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03, 0xAA)
    a.b(0x20, 0x76, 0xAE)             # spawn current Bullet from parent sub[6]
    a.b(0x68, 0xAA)                   # restore marker-table offset
    a.b(0xBD, 0xFF, 0xFF, 0xC9, 0xFF)
    a.branch(0xF0, "mark_done")
    a.b(0x86, 0x0F)                   # helper clobbers X through $B156
    a.b(0x20, 0xFF, 0xFF)
    a.b(0xA6, 0x0F)
    a.label("mark_done")
    a.b(0xE8)                         # next marker table entry
    a.b(0xBD, 0xFF, 0xFF, 0xC9, 0xFF)
    a.branch(0xF0, "exit")
    a.b(0x8A, 0x48)                   # save next marker-table offset
    a.b(0x20, 0xEA, 0xB2)             # find next child sub-slot
    a.branch(0x90, "alloc_fail")
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)
    a.b(0x68, 0xAA)
    a.jmp(CPU_FIRE_3WAY)              # loop
    a.label("alloc_fail")
    a.b(0x68, 0xAA)
    a.jmp(CPU_FIRE_3WAY + 1)          # exit placeholder
    a.label("rts")
    a.b(0x60)
    a.label("helper")
    a.b(0x48, 0xA5, 0x02, 0x20, 0x56, 0xB1, 0xA0, 0x07, 0x68, 0x91, 0x00, 0x60)
    a.label("exit")
    a.b(0xA0, 0x03, 0x98, 0x31, 0x2E, 0x91, 0x2E)
    a.b(0x88, 0xA9, 0x00, 0x91, 0x2C, 0x88, 0x91, 0x2C, 0x60)
    a.label("table")
    a.b(0x83, 0x84, 0xFF, 0x81, 0x80, 0x82, 0xFF, 0xFF, 0xFF)
    blob = bytearray(a.finish())
    loop_cpu = CPU_FIRE_3WAY + a.labels["loop"]
    exit_cpu = CPU_FIRE_3WAY + a.labels["exit"]
    helper_cpu = CPU_FIRE_3WAY + a.labels["helper"]
    table_cpu = CPU_FIRE_3WAY + a.labels["table"]
    for i in range(len(blob) - 2):
        if blob[i] == 0x4C and blob[i + 1:i + 3] == _word(CPU_FIRE_3WAY):
            blob[i + 1:i + 3] = _word(loop_cpu)
        elif blob[i] == 0x4C and blob[i + 1:i + 3] == _word(CPU_FIRE_3WAY + 1):
            blob[i + 1:i + 3] = _word(exit_cpu)
        elif blob[i] == 0x20 and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = _word(helper_cpu)
        elif blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = _word(table_cpu)
    return bytes(blob)


CAVE_FIRE_3WAY = _build_fire_common(ORIG_FIRE_DELAY)
CPU_FIRE_NORMAL_ENTRY = CPU_FIRE_3WAY
CPU_FIRE_THREE_ENTRY = CPU_FIRE_3WAY + 0x04
CPU_FIRE_TWO_ENTRY = CPU_FIRE_3WAY + 0x08
CPU_FIRE_COMMON_MARKER = CPU_FIRE_3WAY + 0x58  # legacy 3-way helper address
CPU_FIRE_COMMON_EXIT = CPU_FIRE_3WAY + 0x64    # legacy 3-way exit address


def _build_fire_2way(fire_delay: int = ORIG_FIRE_DELAY) -> bytes:
    blob = bytearray(_relocate_fire(
        RAW_FIRE_2WAY[:0x39],
        CPU_FIRE_2WAY,
        0x39,
        0x45,
        0x03,
        0x04,
        helper_cpu=CPU_FIRE_COMMON_MARKER,
        exit_cpu=CPU_FIRE_COMMON_EXIT,
    ))
    blob[5] = fire_delay & 0xFF
    blob[0x07] = 0x39 - 0x08       # BCC -> local RTS when the fire timer is not ready.
    blob[0x1B] = 0x36 - 0x1C       # BCC -> local JMP common exit on second-slot failure.
    blob.append(0x60)
    return bytes(blob)


CAVE_FIRE_2WAY = _build_fire_2way(ORIG_FIRE_DELAY)
CPU_FIRE_NORMAL = CPU_BULLET_HOOK + 0x50
OFF_FIRE_NORMAL = _cf(CPU_FIRE_NORMAL)


def _build_fire_dispatch() -> bytes:
    a = _Asm()
    # A = parent type.
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0x29, 0xFE)
    a.b(0xC9, 0x52); a.branch(0xF0, "two")
    a.b(0xC9, 0x56); a.branch(0xF0, "two")
    a.b(0xC9, 0x5A); a.branch(0xF0, "three")
    a.b(0xC9, 0x66); a.branch(0xF0, "three")
    a.jmp(CPU_FIRE_NORMAL_ENTRY)
    a.label("two")
    a.jmp(CPU_FIRE_TWO_ENTRY)
    a.label("three")
    a.jmp(CPU_FIRE_THREE_ENTRY)
    return a.finish()


def _build_bullet_hook() -> bytes:
    a = _Asm()
    a.b(0x20, 0x01, 0xB2, 0x48)       # JSR $B201 / PHA
    a.b(0xC9, 0x02); a.branch(0xD0, "done")
    a.b(0x8A, 0x48)                   # Preserve caller-visible X before using it.
    a.b(0xA0, 0x07, 0xB1, 0x2C)
    a.branch(0x10, "done_x")          # Only marked Panel Bullets use bit7.
    a.b(0x29, 0x7F, 0xAA)
    a.branch(0xF0, "done_x")
    a.b(0xE0, 0x05); a.branch(0xB0, "done_x")
    a.b(0xE0, 0x03); a.branch(0x90, "axis")
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0x29, 0x01)
    a.branch(0xD0, "done_x")
    a.label("axis")
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x02)
    a.branch(0xF0, "y_axis")
    a.b(0xA0, 0x0A)
    a.branch(0xD0, "axis_done")
    a.label("y_axis")
    a.b(0xA0, 0x07)
    a.label("axis_done")
    a.b(0x8A, 0x29, 0x01)
    a.branch(0xD0, "plus")
    a.label("minus")
    a.b(0xB1, 0x2E, 0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.b(0x68, 0xAA, 0x68, 0x60)       # PLA / TAX / PLA / RTS
    a.label("plus")
    a.b(0xB1, 0x2E, 0x18, 0x69, 0x01, 0x91, 0x2E)
    a.label("done_x")
    a.b(0x68, 0xAA)                   # PLA / TAX
    a.label("done")
    a.b(0x68, 0x60)                   # PLA / RTS
    return a.finish()


def _build_demon_ai_wrapper() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0xC9, 0x52); a.branch(0x90, "orig")
    a.b(0xC9, 0x5C); a.branch(0xB0, "orig")
    a.b(0xC9, 0x54); a.branch(0x90, "rl")
    a.b(0xC9, 0x56); a.branch(0x90, "orig")
    a.b(0xC9, 0x58); a.branch(0x90, "ud")
    a.b(0xC9, 0x5A); a.branch(0x90, "orig")
    a.label("rl")
    a.b(0x29, 0x01)
    a.jmp(CPU_AI_DEMON_WRAPPER + 0x28)
    a.label("ud")
    a.b(0x29, 0x01, 0x09, 0x02)
    a.label("set")
    a.b(0x48, 0xA0, 0x03, 0xB1, 0x2E, 0x29, 0xFC, 0x91, 0x2E)
    a.b(0x68, 0x11, 0x2E, 0x91, 0x2E)
    a.jmp(0xA54C)
    a.label("orig")
    a.jmp(0xB208)
    blob = bytearray(a.finish())
    set_cpu = CPU_AI_DEMON_WRAPPER + a.labels["set"]
    for i in range(len(blob) - 2):
        if blob[i] == 0x4C and blob[i + 1:i + 3] == _word(CPU_AI_DEMON_WRAPPER + 0x28):
            blob[i + 1:i + 3] = _word(set_cpu)
    return bytes(blob)


def _build_saram_ai_wrapper() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0xC9, 0x66); a.branch(0x90, "orig")
    a.b(0xC9, 0x68); a.branch(0xB0, "orig")
    a.b(0x29, 0x01, 0x09, 0x02)
    a.b(0x48, 0xA0, 0x03, 0xB1, 0x2E, 0x29, 0xFC, 0x91, 0x2E)
    a.b(0x68, 0x11, 0x2E, 0x91, 0x2E)
    a.jmp(0xA54C)
    a.label("orig")
    a.jmp(0xB038)
    return a.finish()


def _build_property_hook() -> bytes:
    a = _Asm()
    a.b(0xA5, 0x05)                    # LDA $05 (spawn type)
    a.b(0x29, 0xFE)                    # pair-normalize direction bit
    a.b(0x38, 0xE9, 0x52)              # A -= $52
    a.b(0xC9, 0x09); a.branch(0x90, "low_panel_candidate")
    a.b(0xC9, 0x14); a.branch(0xF0, "panel")
    a.branch(0xD0, "orig")
    a.label("low_panel_candidate")
    a.b(0x29, 0x03); a.branch(0xF0, "panel")
    a.label("orig")
    a.b(0xB9, 0x0E, 0xA3, 0x60)        # LDA $A30E,Y / RTS
    a.label("panel")
    a.b(0xA9, PANEL_PROPERTY, 0x60)
    return a.finish()


def _build_anim_hook() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x08)        # LDY #1 / LDA ($08),Y (entity type)
    a.b(0x29, 0xFE)
    a.b(0x38, 0xE9, 0x52)
    a.b(0xC9, 0x09); a.branch(0x90, "low_panel_candidate")
    a.b(0xC9, 0x14); a.branch(0xF0, "panel")
    a.b(0x4C, 0xEF, 0xC0)              # JMP orig
    a.label("low_panel_candidate")
    a.b(0x29, 0x03); a.branch(0xF0, "panel")
    a.label("orig")
    a.b(0xA4, 0x0E)
    a.b(0xB9, 0xE8, 0xD0, 0x85, 0x0A)
    a.b(0xB9, 0xE9, 0xD0, 0x85, 0x0B)
    a.b(0x60)
    a.label("panel")
    a.b(0xA9, PANEL_ANIM_META[0], 0x85, 0x0A)
    a.b(0xA9, PANEL_ANIM_META[1], 0x85, 0x0B)
    a.b(0x60)
    blob = bytearray(a.finish())
    orig_cpu = CPU_ANIM_HOOK + a.labels["orig"]
    for i in range(len(blob) - 2):
        if blob[i] == 0x4C and blob[i + 1:i + 3] == bytes((0xEF, 0xC0)):
            blob[i + 1:i + 3] = _word(orig_cpu)
    return bytes(blob)


CAVE_FIRE_DISPATCH = _build_fire_dispatch()
CAVE_BULLET_HOOK = _build_bullet_hook()
CAVE_BULLET_HOOK_SLOT = (
    CAVE_BULLET_HOOK
    + bytes([0xEA] * (BULLET_HOOK_SLOT_SIZE - len(CAVE_BULLET_HOOK)))
)


def _build_fire_normal(fire_delay: int) -> bytes:
    return _with_fire_delay(ORIG_PANEL_FIRE, fire_delay)


CAVE_FIRE_NORMAL = _build_fire_normal(ORIG_FIRE_DELAY)
CAVE_AI_DEMON_WRAPPER = _build_demon_ai_wrapper()
CAVE_AI_SARAM_WRAPPER = _build_saram_ai_wrapper()
CAVE_PROPERTY_HOOK = _build_property_hook()
CAVE_ANIM_HOOK = _build_anim_hook()

RESERVED_SPANS = (
    (OFF_FIRE_DISPATCH, len(CAVE_FIRE_DISPATCH)),
    (OFF_AI_SARAM_WRAPPER, len(CAVE_AI_SARAM_WRAPPER)),
    (OFF_FIRE_3WAY, len(CAVE_FIRE_3WAY)),
    (OFF_BULLET_HOOK, len(CAVE_BULLET_HOOK_SLOT)),
    (OFF_AI_DEMON_WRAPPER, len(CAVE_AI_DEMON_WRAPPER)),
    (OFF_PROPERTY_HOOK, len(CAVE_PROPERTY_HOOK)),
    (OFF_ANIM_HOOK, len(CAVE_ANIM_HOOK)),
)


def _expect_or_hooked(rom_data, off: int, orig: bytes, hook: bytes, name: str,
                      extra_hooks: tuple[bytes, ...] = ()) -> None:
    cur = bytes(rom_data[off:off + len(orig)])
    if cur == orig:
        return
    for accepted in (hook, *extra_hooks):
        if cur[:len(accepted)] == accepted:
            return
    raise PanelMonsterVariantError(
        f"{name} signature mismatch at file 0x{off:X}: "
        f"expected {orig.hex(' ')} or hook {hook.hex(' ')}, got {cur.hex(' ')}"
    )


def _is_panel_fire_with_delay(cur: bytes) -> bool:
    return (
        len(cur) == len(ORIG_PANEL_FIRE)
        and cur[:5] == ORIG_PANEL_FIRE[:5]
        and cur[6:] == ORIG_PANEL_FIRE[6:]
        and cur[5] in (ORIG_FIRE_DELAY, SNAPPY_FIRE_DELAY)
    )


def _is_orig_panel_fire_with_current_spark_property(cur: bytes) -> bool:
    return (
        cur[:3] == ORIG_PANEL_FIRE[:3]
        and cur[3:3 + len(SPARK_PROPERTY_HOOK_CURRENT_BODY)] == SPARK_PROPERTY_HOOK_CURRENT_BODY
    )


def _current_panel_fire_delay(rom_data) -> int:
    cur = bytes(rom_data[OFF_HOOK_PANEL_FIRE:OFF_HOOK_PANEL_FIRE + len(ORIG_PANEL_FIRE)])
    if _is_panel_fire_with_delay(cur):
        return cur[5]
    if cur[:len(HOOK_PANEL_FIRE_HEAD)] == HOOK_PANEL_FIRE_HEAD:
        if (
            len(rom_data) > OFF_FIRE_3WAY + 15
            and rom_data[OFF_FIRE_3WAY:OFF_FIRE_3WAY + 3] == bytes((0xA2, 0x07, 0xD0))
            and rom_data[OFF_FIRE_3WAY + 14] == 0xC9
        ):
            value = rom_data[OFF_FIRE_3WAY + 15]
            if value in (ORIG_FIRE_DELAY, SNAPPY_FIRE_DELAY):
                return value
        for off in (OFF_FIRE_NORMAL, OFF_FIRE_2WAY, OFF_FIRE_3WAY):
            if len(rom_data) > off + 5 and rom_data[off + 4] == 0xC9:
                value = rom_data[off + 5]
                if value in (ORIG_FIRE_DELAY, SNAPPY_FIRE_DELAY):
                    return value
    return ORIG_FIRE_DELAY


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _set_byte(rom_data, off: int, value: int, changed: list[str], name: str) -> None:
    if rom_data[off] != (value & 0xFF):
        rom_data[off] = value & 0xFF
        changed.append(name)


def _clear_old_blob_if_present(rom_data, off: int, blob: bytes,
                               changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) == blob:
        rom_data[off:off + len(blob)] = bytes([0xEA] * len(blob))
        changed.append(name)


def apply(rom_data) -> list[str]:
    if rom_data is None or len(rom_data) < OFF_ANIM_META_TABLE + 52:
        raise PanelMonsterVariantError("ROM is too short for Panel Monster variant patch.")

    fire_site = bytes(rom_data[OFF_HOOK_PANEL_FIRE:OFF_HOOK_PANEL_FIRE + len(ORIG_PANEL_FIRE)])
    if not (
        _is_panel_fire_with_delay(fire_site)
        or fire_site[:len(HOOK_PANEL_FIRE_HEAD)] == HOOK_PANEL_FIRE_HEAD
        or _is_orig_panel_fire_with_current_spark_property(fire_site)
    ):
        _expect_or_hooked(rom_data, OFF_HOOK_PANEL_FIRE, ORIG_PANEL_FIRE, HOOK_PANEL_FIRE, "$A556")
    fire_delay = _current_panel_fire_delay(rom_data)
    cave_fire_normal = _build_fire_normal(fire_delay)
    cave_fire_2way = _build_fire_2way(fire_delay)
    cave_fire_3way = _build_fire_3way(fire_delay)
    _expect_or_hooked(rom_data, OFF_HOOK_BULLET_MOVE, ORIG_BULLET_MOVE_HOOK, HOOK_BULLET_MOVE, "$AFBC")
    _expect_or_hooked(
        rom_data,
        OFF_A2CC,
        ORIG_A2CC_HEAD,
        HOOK_A2CC,
        "$A2CC",
        (HOOK_A2CC_SPARK, HOOK_A2CC_SPARK_CURRENT),
    )
    _expect_or_hooked(rom_data, OFF_8B05, ORIG_8B05_HEAD, HOOK_8B05, "$8B05", (HOOK_8B05_SPARK,))
    for off, orig, hook, name in (
        (OFF_AI_DEMON_52_53, ORIG_AI_DEMON, _word(CPU_AI_DEMON_WRAPPER), "$A34C"),
        (OFF_AI_DEMON_56_57, ORIG_AI_DEMON, _word(CPU_AI_DEMON_WRAPPER), "$A34E"),
        (OFF_AI_DEMON_5A_5B, ORIG_AI_DEMON, _word(CPU_AI_DEMON_WRAPPER), "$A350"),
        (OFF_AI_SARAM_66_67, ORIG_AI_SARAM, _word(CPU_AI_SARAM_WRAPPER), "$A356"),
    ):
        cur = bytes(rom_data[off:off + 2])
        accepted = (orig, hook)
        if off in (OFF_AI_DEMON_52_53, OFF_AI_DEMON_56_57, OFF_AI_DEMON_5A_5B):
            accepted = (*accepted, _word(CPU_PANEL_STAGE_AI_DEMON_WRAPPER))
        if cur not in accepted:
            raise PanelMonsterVariantError(f"{name} AI table signature mismatch: got {cur.hex(' ')}")

    changed: list[str] = []
    for off, blob, name in (
        (OFF_FIRE_DISPATCH, CAVE_FIRE_DISPATCH, "Panel Monster variant fire dispatch $BCD2"),
        (OFF_AI_SARAM_WRAPPER, CAVE_AI_SARAM_WRAPPER, "Panel Monster variant Saramandor-ID AI wrapper $BC5B"),
        (OFF_FIRE_3WAY, cave_fire_3way, "Panel Monster common fire loop $BD88"),
        (OFF_BULLET_HOOK, CAVE_BULLET_HOOK_SLOT, "Panel Monster diagonal Bullet hook $BF69"),
        (OFF_AI_DEMON_WRAPPER, CAVE_AI_DEMON_WRAPPER, "Panel Monster Demonhead-ID AI wrapper $C146"),
        (OFF_PROPERTY_HOOK, CAVE_PROPERTY_HOOK, "Panel Monster type-specific property hook $DBDF"),
        (OFF_ANIM_HOOK, CAVE_ANIM_HOOK, "Panel Monster type-specific animation hook $C0C2"),
    ):
        _write_blob(rom_data, off, blob, changed, name)
    _clear_old_blob_if_present(
        rom_data, OFF_FIRE_NORMAL, cave_fire_normal, changed,
        "reclaim old Panel Monster normal fire copy",
    )
    _clear_old_blob_if_present(
        rom_data, OFF_FIRE_2WAY, cave_fire_2way, changed,
        "reclaim old Panel Monster 2-way fire cave",
    )

    _write_blob(rom_data, OFF_HOOK_PANEL_FIRE, HOOK_PANEL_FIRE, changed, "$A556 Panel Monster variant fire hook")
    _write_blob(rom_data, OFF_HOOK_BULLET_MOVE, HOOK_BULLET_MOVE, changed, "$AFBC Panel Monster Bullet Y hook")
    _write_blob(rom_data, OFF_AI_DEMON_52_53, _word(CPU_AI_DEMON_WRAPPER), changed, "$A34C Panel Monster borrowed AI")
    _write_blob(rom_data, OFF_AI_DEMON_56_57, _word(CPU_AI_DEMON_WRAPPER), changed, "$A34E Panel Monster borrowed AI")
    _write_blob(rom_data, OFF_AI_DEMON_5A_5B, _word(CPU_AI_DEMON_WRAPPER), changed, "$A350 Panel Monster borrowed AI")
    _write_blob(rom_data, OFF_AI_SARAM_66_67, _word(CPU_AI_SARAM_WRAPPER), changed, "$A356 Panel Monster borrowed AI")
    _write_blob(rom_data, OFF_A2CC, HOOK_A2CC, changed, "$A2CC Panel Monster property dispatch")
    _write_blob(rom_data, OFF_8B05, HOOK_8B05, changed, "$8B05 Panel Monster animation dispatch")

    # Restore shared 4-ID groups.  The hooks above select Panel visuals only
    # for the borrowed IDs, so stock $50/$51, $54/$55, etc. remain untouched.
    for idx, value in ORIG_PANEL_GROUP_PROPERTIES.items():
        _set_byte(rom_data, OFF_PROPERTY_TABLE + idx, value, changed, f"restore property index {idx}")

    for group, ptr in ORIG_PANEL_GROUP_ANIMS.items():
        _write_blob(
            rom_data,
            OFF_ANIM_META_TABLE + group * 2,
            ptr,
            changed,
            f"restore animation group {group}",
        )
    return changed
