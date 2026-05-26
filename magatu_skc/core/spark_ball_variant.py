"""Spark Ball borrowed-ID variants.

JP/JPC66 only.  The accepted Dragon #2 IDs are reused as Spark Ball variants:

  $6A -> Spark Ball up phase, speed 1
  $6B -> Spark Ball right-hand/down phase, speed 1
  $6E -> Spark Ball up phase, speed 2
  $6F -> Spark Ball right-hand/down phase, speed 2

The accepted Golem #2 IDs are reused as transparent Spark Ball variants:

  $72 -> Transparent Spark Ball up phase, speed 1
  $73 -> Transparent Spark Ball down phase, speed 1
  $76 -> Transparent Spark Ball up phase, speed 2
  $77 -> Transparent Spark Ball down phase, speed 2

The normal Dragon IDs in the same AI-table groups ($68/$69/$6C/$6D) are sent
back to the stock Dragon routine.  The borrowed IDs enter the confirmed stock
Spark Ball AI while keeping their original type byte.  Property and animation
metadata are selected by type-specific hooks so the shared Dragon groups remain
unchanged for stock Dragons.

The normal Golem IDs in the same AI-table groups ($70/$71/$74/$75) are sent
back to the stock Golem routine.  The transparent variants use the same Spark
Ball metadata and additionally hide their OAM tiles every other long phase
after the normal draw routine has completed.

The LIFE-hundreds pause hook checks main-slot +1 for the borrowed IDs.  Stock
$28-$2F Spark Balls do not match and continue through the original speed commit.
"""

from __future__ import annotations


class SparkBallVariantError(ValueError):
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
                raise SparkBallVariantError(f"branch to {label} is out of range")
            self.code[off] = rel & 0xFF
        return bytes(self.code)


OFF_AI_DRAGON_SLOW = _cf(0xA358)
OFF_AI_DRAGON_FAST = _cf(0xA35A)
OFF_AI_GOLEM_SLOW = _cf(0xA35C)
OFF_AI_GOLEM_FAST = _cf(0xA35E)

ORIG_AI_DRAGON = _word(0xA64A)
ORIG_AI_GOLEM = _word(0xAD11)
ORIG_AB13_HEAD = bytes.fromhex("A0 07 B5")
ORIG_A2CC_HEAD = bytes.fromhex("B9 0E A3")
ORIG_8B05_HEAD = bytes.fromhex("B9 E8 D0 85 0A B9 E9 D0 85 0B")
ORIG_85FA = bytes.fromhex("9D 16 02 4C 08 86")

OFF_PROPERTY_DRAGON_SLOW = _cf(0xA322)
OFF_PROPERTY_DRAGON_FAST = _cf(0xA323)
ORIG_DRAGON_PROPERTY = 0x00
SPARK_PROPERTY = 0x19

OFF_ANIM_META_DRAGON_SLOW = 0x512C
OFF_ANIM_META_DRAGON_FAST = 0x512E
ORIG_DRAGON_ANIM_META = _word(0xD4CA)
SPARK_ANIM_META = _word(0xD35A)

CPU_AI_DRAGON_SLOW_WRAPPER = _cpu(0x3FE8)  # $BFD8
CPU_AI_DRAGON_FAST_WRAPPER_OLD = _cpu(0x4008)  # $BFF8, v0.6.129-v0.6.130
CPU_AI_DRAGON_FAST_WRAPPER_OLD2 = _cpu(0x4018) # $C008, v0.6.131-v0.6.133
CPU_AI_DRAGON_FAST_WRAPPER = _cpu(0x3D36)      # $BD26
CPU_AI_GOLEM_WRAPPER_OLD = _cpu(0x0BF2)        # $8BE2, v0.7.53-v0.7.69
CPU_AI_GOLEM_WRAPPER = _cpu(0x681C)            # $E80C, original 00-fill
CPU_PAUSE_HOOK_OLD = _cpu(0x4048)              # $C038, v0.6.131-v0.6.133
CPU_PAUSE_HOOK = _cpu(0x6FD4)                  # $EFC4
CPU_PROPERTY_HOOK_OLD = _cpu(0x3E72)           # $BE62, v0.6.130-v0.7.52
CPU_PROPERTY_HOOK = _cpu(0x2569)               # $A559
CPU_ANIM_HOOK = _cpu(0x4FEE)                   # $CFDE
CPU_ANIM_SPARK_SET = _cpu(0x3EFA)              # $BEEA
CPU_OAM_HIDE_HOOK = _cpu(0x3ED7)               # $BEC7
CPU_PANEL_PROPERTY_HOOK = _cpu(0x5BEF)         # $DBDF
CPU_PANEL_ANIM_HOOK = _cpu(0x40D2)             # $C0C2

DEFAULT_PAUSE_DIGITS = (0, 3, 6, 9)
PAUSE_DIGIT_COUNT = 4
TRANSPARENCY_PERIODS = (0x20, 0x30, 0x40, 0x60, 0x80)
DEFAULT_TRANSPARENCY_PERIOD = 0x40

OFF_AI_DRAGON_SLOW_WRAPPER = _cf(CPU_AI_DRAGON_SLOW_WRAPPER)
OFF_AI_DRAGON_FAST_WRAPPER = _cf(CPU_AI_DRAGON_FAST_WRAPPER)
OFF_AI_GOLEM_WRAPPER_OLD = _cf(CPU_AI_GOLEM_WRAPPER_OLD)
OFF_AI_GOLEM_WRAPPER = _cf(CPU_AI_GOLEM_WRAPPER)
OFF_PAUSE_HOOK = _cf(CPU_PAUSE_HOOK)
OFF_PROPERTY_HOOK = _cf(CPU_PROPERTY_HOOK)
OFF_ANIM_HOOK = _cf(CPU_ANIM_HOOK)
OFF_ANIM_SPARK_SET = _cf(CPU_ANIM_SPARK_SET)
OFF_OAM_HIDE_HOOK = _cf(CPU_OAM_HIDE_HOOK)
OFF_AB13 = _cf(0xAB13)
OFF_A2CC = _cf(0xA2CC)
OFF_8B05 = _cf(0x8B05)
OFF_85FA = _cf(0x85FA)

OFF_PAUSE_DIGITS = tuple(OFF_PAUSE_HOOK + rel for rel in (0x25, 0x29, 0x2D, 0x31))
OFF_TRANSPARENCY_PERIOD = OFF_OAM_HIDE_HOOK + 0x14


def normalize_pause_digits(digits) -> tuple[int, int, int, int]:
    vals = []
    for value in digits:
        iv = int(value)
        if not 0 <= iv <= 9:
            raise SparkBallVariantError("停止するLIFE百の位は0-9で指定してください。")
        if iv not in vals:
            vals.append(iv)
        if len(vals) > PAUSE_DIGIT_COUNT:
            raise SparkBallVariantError("停止するLIFE百の位は最大4個までです。")
    if not vals:
        raise SparkBallVariantError("停止するLIFE百の位を最低1個選んでください。")
    while len(vals) < PAUSE_DIGIT_COUNT:
        vals.append(vals[-1])
    return tuple(vals)


def _build_ai_wrapper(low_type: int, high_type: int, low_spark: int,
                      high_spark: int, spark_ai: int, stock_ai: int = 0xA64A) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)       # LDY #1 / LDA ($2E),Y
    a.b(0xC9, low_type); a.branch(0xF0, "low")
    a.b(0xC9, high_type); a.branch(0xF0, "high")
    a.jmp(stock_ai)
    a.label("low")
    a.jmp(spark_ai)
    a.label("high")
    a.jmp(spark_ai)
    return a.finish()


def _build_pause_hook(pause_digits=DEFAULT_PAUSE_DIGITS) -> bytes:
    pause_digits = normalize_pause_digits(pause_digits)
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)       # LDY #1 / LDA ($2E),Y
    for type_id in (0x6A, 0x6B, 0x6E, 0x6F):
        a.b(0xC9, type_id); a.branch(0xF0, "check_pause")
    a.label("commit")
    a.b(0xA0, 0x07, 0xB5, 0x02, 0x91, 0x2E)
    a.b(0xA0, 0x0A, 0xB5, 0x03, 0x91, 0x2E, 0x60)
    a.label("check_pause")
    a.b(0xAD, 0x39, 0x04)             # LDA $0439 (LIFE hundreds digit)
    for digit in pause_digits:
        a.b(0xC9, digit); a.branch(0xF0, "stop")
    a.branch(0xD0, "commit")
    a.label("stop")
    a.b(0x60)
    return a.finish()


def _build_property_hook() -> bytes:
    a = _Asm()
    a.b(0xA5, 0x05)                      # LDA $05 (spawn type)
    a.b(0x29, 0xFE)                      # pair-normalize direction bit
    for type_id in (0x6A, 0x6E, 0x72, 0x76):
        a.b(0xC9, type_id); a.branch(0xF0, "spark")
    a.jmp(CPU_PANEL_PROPERTY_HOOK)        # fall through to Panel/stock selector
    a.label("spark")
    a.b(0xA9, SPARK_PROPERTY, 0x60)      # LDA #$19 / RTS
    return a.finish()


def _build_anim_hook() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x08)          # LDY #1 / LDA ($08),Y (entity type)
    a.b(0x29, 0xFE)                      # ignore right/left phase bit
    for type_id in (0x6A, 0x6E, 0x72, 0x76):
        a.b(0xC9, type_id); a.branch(0xF0, "spark")
    a.jmp(CPU_PANEL_ANIM_HOOK)            # fall through to Panel/stock selector
    a.label("spark")
    a.b(0x4C, CPU_ANIM_SPARK_SET & 0xFF, (CPU_ANIM_SPARK_SET >> 8) & 0xFF)
    return a.finish()


def _build_anim_spark_set() -> bytes:
    return bytes((
        0xA9, SPARK_ANIM_META[0], 0x85, 0x0A,
        0xA9, SPARK_ANIM_META[1], 0x85, 0x0B,
        0x60,
    ))


def _build_golem_ai_wrapper() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0xFE)  # read type, normalize phase bit
    a.b(0xC9, 0x72); a.branch(0xF0, "slow")
    a.b(0xC9, 0x76); a.branch(0xF0, "fast")
    a.jmp(0xAD11)
    a.label("slow")
    a.jmp(0xA929)
    a.label("fast")
    a.jmp(0xA92D)
    return a.finish()


def _build_oam_hide_hook(transparency_period=DEFAULT_TRANSPARENCY_PERIOD) -> bytes:
    transparency_period = int(transparency_period)
    if transparency_period not in TRANSPARENCY_PERIODS:
        raise SparkBallVariantError(
            f"未対応の透明スパークボール周期です: ${transparency_period:02X}")
    a = _Asm()
    a.b(0x9D, 0x16, 0x02)             # original STA $0216,X
    a.b(0xA0, 0x01, 0xB1, 0x08)       # LDY #1 / LDA ($08),Y (entity type)
    a.b(0x29, 0xFE)                   # normalize up/down phase bit
    a.b(0xC9, 0x72); a.branch(0xF0, "maybe_hide")
    a.b(0xC9, 0x76); a.branch(0xD0, "done")
    a.label("maybe_hide")
    a.b(0xA5, 0x21, 0x29, transparency_period)  # LDA frame counter / AND #mask
    a.branch(0xF0, "done")
    a.b(0xA9, 0xF8, 0x9D, 0x10, 0x02, 0x9D, 0x14, 0x02)
    a.label("done")
    a.jmp(0x8608)
    return a.finish()


CAVE_AI_DRAGON_SLOW_WRAPPER = _build_ai_wrapper(0x6A, 0x6B, 0x2A, 0x2B, 0xA929)
CAVE_AI_DRAGON_FAST_WRAPPER = _build_ai_wrapper(0x6E, 0x6F, 0x2E, 0x2F, 0xA92D)
CAVE_AI_GOLEM_WRAPPER = _build_golem_ai_wrapper()
CAVE_PAUSE_HOOK = _build_pause_hook()
CAVE_PROPERTY_HOOK = _build_property_hook()
CAVE_ANIM_HOOK = _build_anim_hook()
CAVE_ANIM_SPARK_SET = _build_anim_spark_set()
CAVE_OAM_HIDE_HOOK = _build_oam_hide_hook()

RESERVED_SPANS = (
    (OFF_AI_DRAGON_SLOW_WRAPPER, len(CAVE_AI_DRAGON_SLOW_WRAPPER)),
    (OFF_AI_DRAGON_FAST_WRAPPER, len(CAVE_AI_DRAGON_FAST_WRAPPER)),
    (OFF_AI_GOLEM_WRAPPER, len(CAVE_AI_GOLEM_WRAPPER)),
    (OFF_PAUSE_HOOK, len(CAVE_PAUSE_HOOK)),
    (OFF_PROPERTY_HOOK, len(CAVE_PROPERTY_HOOK)),
    (OFF_ANIM_HOOK, len(CAVE_ANIM_HOOK)),
    (OFF_ANIM_SPARK_SET, len(CAVE_ANIM_SPARK_SET)),
    (OFF_OAM_HIDE_HOOK, len(CAVE_OAM_HIDE_HOOK)),
)


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _expect_or_hooked(rom_data, off: int, orig: bytes, hook: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(orig)])
    if cur == orig:
        return
    if cur[:len(hook)] == hook:
        return
    raise SparkBallVariantError(
        f"{name} signature mismatch at file 0x{off:X}: "
        f"expected {orig.hex(' ')} or hook {hook.hex(' ')}, got {cur.hex(' ')}"
    )


def _has_pause_hook(rom_data) -> bool:
    return bytes(rom_data[OFF_PAUSE_HOOK:OFF_PAUSE_HOOK + 4]) == bytes((0xA0, 0x01, 0xB1, 0x2E))


def _has_oam_hide_hook(rom_data) -> bool:
    return bytes(rom_data[OFF_OAM_HIDE_HOOK:OFF_OAM_HIDE_HOOK + 3]) == bytes((0x9D, 0x16, 0x02))


def current_pause_digits(rom_data) -> tuple[int, int, int, int]:
    if rom_data is None or len(rom_data) <= max(OFF_PAUSE_DIGITS):
        raise SparkBallVariantError("ROM is too short for Spark Ball pause settings.")
    if not _has_pause_hook(rom_data):
        return DEFAULT_PAUSE_DIGITS
    return tuple(int(rom_data[off]) for off in OFF_PAUSE_DIGITS)


def current_transparency_period(rom_data) -> int:
    if rom_data is None or len(rom_data) <= OFF_TRANSPARENCY_PERIOD:
        raise SparkBallVariantError("ROM is too short for Spark Ball transparency settings.")
    if not _has_oam_hide_hook(rom_data):
        return DEFAULT_TRANSPARENCY_PERIOD
    value = int(rom_data[OFF_TRANSPARENCY_PERIOD])
    if value not in TRANSPARENCY_PERIODS:
        return DEFAULT_TRANSPARENCY_PERIOD
    return value


def apply(rom_data, pause_digits=None, transparency_period=None) -> list[str]:
    if pause_digits is None:
        pause_digits = current_pause_digits(rom_data)
    else:
        pause_digits = normalize_pause_digits(pause_digits)
    if transparency_period is None:
        transparency_period = current_transparency_period(rom_data)
    else:
        transparency_period = int(transparency_period)
        if transparency_period not in TRANSPARENCY_PERIODS:
            raise SparkBallVariantError(
                f"未対応の透明スパークボール周期です: ${transparency_period:02X}")
    pause_hook = _build_pause_hook(pause_digits)
    oam_hide_hook = _build_oam_hide_hook(transparency_period)

    min_len = max(
        OFF_AI_DRAGON_SLOW_WRAPPER + len(CAVE_AI_DRAGON_SLOW_WRAPPER),
        OFF_AI_DRAGON_FAST_WRAPPER + len(CAVE_AI_DRAGON_FAST_WRAPPER),
        OFF_AI_GOLEM_WRAPPER + len(CAVE_AI_GOLEM_WRAPPER),
        OFF_PAUSE_HOOK + len(pause_hook),
        OFF_PROPERTY_HOOK + len(CAVE_PROPERTY_HOOK),
        OFF_ANIM_HOOK + len(CAVE_ANIM_HOOK),
        OFF_ANIM_SPARK_SET + len(CAVE_ANIM_SPARK_SET),
        OFF_OAM_HIDE_HOOK + len(oam_hide_hook),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise SparkBallVariantError("ROM is too short for Spark Ball variant patch.")

    for off, hooks, name in (
        (OFF_AI_DRAGON_SLOW, (_word(CPU_AI_DRAGON_SLOW_WRAPPER),), "$A358"),
        (OFF_AI_DRAGON_FAST, (
            _word(CPU_AI_DRAGON_FAST_WRAPPER),
            _word(CPU_AI_DRAGON_FAST_WRAPPER_OLD),
            _word(CPU_AI_DRAGON_FAST_WRAPPER_OLD2),
        ), "$A35A"),
    ):
        cur = bytes(rom_data[off:off + 2])
        if cur not in (ORIG_AI_DRAGON, *hooks):
            raise SparkBallVariantError(f"{name} AI table signature mismatch: got {cur.hex(' ')}")
    for off, hooks, name in (
        (OFF_AI_GOLEM_SLOW, (
            _word(CPU_AI_GOLEM_WRAPPER),
            _word(CPU_AI_GOLEM_WRAPPER_OLD),
        ), "$A35C"),
        (OFF_AI_GOLEM_FAST, (
            _word(CPU_AI_GOLEM_WRAPPER),
            _word(CPU_AI_GOLEM_WRAPPER_OLD),
        ), "$A35E"),
    ):
        cur = bytes(rom_data[off:off + 2])
        if cur not in (ORIG_AI_GOLEM, *hooks):
            raise SparkBallVariantError(f"{name} AI table signature mismatch: got {cur.hex(' ')}")

    changed: list[str] = []
    cur_ab13 = bytes(rom_data[OFF_AB13:OFF_AB13 + 3])
    hook_ab13 = bytes((0x4C, CPU_PAUSE_HOOK & 0xFF, (CPU_PAUSE_HOOK >> 8) & 0xFF))
    hook_ab13_old = bytes((0x4C, CPU_PAUSE_HOOK_OLD & 0xFF, (CPU_PAUSE_HOOK_OLD >> 8) & 0xFF))
    if cur_ab13 not in (ORIG_AB13_HEAD, hook_ab13, hook_ab13_old):
        raise SparkBallVariantError(f"$AB13 signature mismatch: got {cur_ab13.hex(' ')}")
    hook_a2cc = bytes((0x20, CPU_PROPERTY_HOOK & 0xFF, (CPU_PROPERTY_HOOK >> 8) & 0xFF))
    hook_a2cc_old = bytes((0x20, CPU_PROPERTY_HOOK_OLD & 0xFF, (CPU_PROPERTY_HOOK_OLD >> 8) & 0xFF))
    hook_a2cc_panel = bytes((0x20, CPU_PANEL_PROPERTY_HOOK & 0xFF, (CPU_PANEL_PROPERTY_HOOK >> 8) & 0xFF))
    cur_a2cc = bytes(rom_data[OFF_A2CC:OFF_A2CC + len(ORIG_A2CC_HEAD)])
    if cur_a2cc not in (ORIG_A2CC_HEAD, hook_a2cc, hook_a2cc_old, hook_a2cc_panel):
        raise SparkBallVariantError(f"$A2CC property signature mismatch: got {cur_a2cc.hex(' ')}")
    hook_8b05 = bytes((0x20, CPU_ANIM_HOOK & 0xFF, (CPU_ANIM_HOOK >> 8) & 0xFF))
    anim_patch = hook_8b05 + bytes((0xEA,)) * (len(ORIG_8B05_HEAD) - len(hook_8b05))
    hook_8b05_panel = bytes((0x20, CPU_PANEL_ANIM_HOOK & 0xFF, (CPU_PANEL_ANIM_HOOK >> 8) & 0xFF))
    anim_patch_panel = hook_8b05_panel + bytes((0xEA,)) * (len(ORIG_8B05_HEAD) - len(hook_8b05_panel))
    cur_8b05 = bytes(rom_data[OFF_8B05:OFF_8B05 + len(ORIG_8B05_HEAD)])
    if cur_8b05 not in (ORIG_8B05_HEAD, anim_patch, anim_patch_panel):
        raise SparkBallVariantError(f"$8B05 animation signature mismatch: got {cur_8b05.hex(' ')}")
    hook_85fa = bytes((0x4C, CPU_OAM_HIDE_HOOK & 0xFF, (CPU_OAM_HIDE_HOOK >> 8) & 0xFF))
    oam_patch = hook_85fa + bytes((0xEA,)) * (len(ORIG_85FA) - len(hook_85fa))
    cur_85fa = bytes(rom_data[OFF_85FA:OFF_85FA + len(ORIG_85FA)])
    if cur_85fa not in (ORIG_85FA, oam_patch):
        raise SparkBallVariantError(f"$85FA OAM signature mismatch: got {cur_85fa.hex(' ')}")

    _write_blob(
        rom_data,
        OFF_AI_DRAGON_SLOW_WRAPPER,
        CAVE_AI_DRAGON_SLOW_WRAPPER,
        changed,
        "Spark Ball Dragon-ID slow AI wrapper $BFD8",
    )
    _write_blob(
        rom_data,
        OFF_AI_DRAGON_FAST_WRAPPER,
        CAVE_AI_DRAGON_FAST_WRAPPER,
        changed,
        "Spark Ball Dragon-ID fast AI wrapper $BD26",
    )
    _write_blob(
        rom_data,
        OFF_AI_GOLEM_WRAPPER,
        CAVE_AI_GOLEM_WRAPPER,
        changed,
        "Transparent Spark Ball Golem-ID AI wrapper $E80C",
    )
    if bytes(rom_data[OFF_AI_GOLEM_WRAPPER_OLD:OFF_AI_GOLEM_WRAPPER_OLD + len(CAVE_AI_GOLEM_WRAPPER)]) == CAVE_AI_GOLEM_WRAPPER:
        _write_blob(
            rom_data,
            OFF_AI_GOLEM_WRAPPER_OLD,
            bytes([0xEA] * len(CAVE_AI_GOLEM_WRAPPER)),
            changed,
            "clear old Transparent Spark Ball Golem-ID AI wrapper $8BE2",
        )
    _write_blob(
        rom_data,
        OFF_PAUSE_HOOK,
        pause_hook,
        changed,
        "Spark Ball Dragon-ID pause hook $EFC4",
    )
    _write_blob(
        rom_data,
        OFF_PROPERTY_HOOK,
        CAVE_PROPERTY_HOOK,
        changed,
        "Spark Ball property hook $D055",
    )
    _write_blob(
        rom_data,
        OFF_ANIM_HOOK,
        CAVE_ANIM_HOOK,
        changed,
        "Spark Ball Dragon-ID animation hook $CFDE",
    )
    _write_blob(
        rom_data,
        OFF_ANIM_SPARK_SET,
        CAVE_ANIM_SPARK_SET,
        changed,
        "Spark Ball Dragon-ID animation setter $BEEA",
    )
    _write_blob(
        rom_data,
        OFF_OAM_HIDE_HOOK,
        oam_hide_hook,
        changed,
        "Transparent Spark Ball OAM hide hook $D026",
    )
    _write_blob(rom_data, OFF_AI_DRAGON_SLOW, _word(CPU_AI_DRAGON_SLOW_WRAPPER), changed, "$A358 Spark Ball Dragon-ID AI")
    _write_blob(rom_data, OFF_AI_DRAGON_FAST, _word(CPU_AI_DRAGON_FAST_WRAPPER), changed, "$A35A Spark Ball Dragon-ID AI")
    _write_blob(rom_data, OFF_AI_GOLEM_SLOW, _word(CPU_AI_GOLEM_WRAPPER), changed, "$A35C Transparent Spark Ball Golem-ID AI")
    _write_blob(rom_data, OFF_AI_GOLEM_FAST, _word(CPU_AI_GOLEM_WRAPPER), changed, "$A35E Transparent Spark Ball Golem-ID AI")
    _write_blob(rom_data, OFF_AB13, hook_ab13, changed, "$AB13 Spark Ball Dragon-ID pause dispatch")
    _write_blob(rom_data, OFF_A2CC, hook_a2cc, changed, "$A2CC Spark Ball Dragon-ID property dispatch")
    _write_blob(rom_data, OFF_8B05, anim_patch, changed, "$8B05 Spark Ball Dragon-ID animation dispatch")
    _write_blob(rom_data, OFF_85FA, oam_patch, changed, "$85FA Transparent Spark Ball OAM dispatch")
    _write_blob(rom_data, OFF_PROPERTY_DRAGON_SLOW, bytes((ORIG_DRAGON_PROPERTY,)), changed, "$A322 restore Dragon property")
    _write_blob(rom_data, OFF_PROPERTY_DRAGON_FAST, bytes((ORIG_DRAGON_PROPERTY,)), changed, "$A323 restore Dragon property")
    _write_blob(rom_data, OFF_ANIM_META_DRAGON_SLOW, ORIG_DRAGON_ANIM_META, changed, "restore Dragon slow animation")
    _write_blob(rom_data, OFF_ANIM_META_DRAGON_FAST, ORIG_DRAGON_ANIM_META, changed, "restore Dragon fast animation")
    return changed
