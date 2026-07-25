"""Integrated 24-ID Spark Ball settings and ROM writer."""
from __future__ import annotations

from . import spark24_runtime as _spark24


class SparkBallVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


ORIG_AB13_HEAD = bytes.fromhex("A0 07 B5")
ORIG_A2CC_HEAD = bytes.fromhex("B9 0E A3")
ORIG_85FA = bytes.fromhex("9D 16 02 4C 08 86")

OFF_AB13 = _cf(0xAB13)
OFF_A2CC = _cf(0xA2CC)
OFF_85FA = _cf(0x85FA)

CPU_PANEL_PROPERTY_HOOK = _spark24.CPU_PANEL_PROPERTY_HOOK

DEFAULT_PAUSE_DIGITS = _spark24.DEFAULT_PAUSE_DIGITS
DEFAULT_REVERSE_DIGITS = _spark24.DEFAULT_REVERSE_DIGITS
PAUSE_DIGIT_COUNT = _spark24.PAUSE_DIGIT_COUNT
TRANSPARENCY_PERIODS = _spark24.TRANSPARENCY_PERIODS
DEFAULT_TRANSPARENCY_PERIOD = _spark24.DEFAULT_TRANSPARENCY_PERIOD

RESERVED_SPANS = _spark24.RESERVED_SPANS


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


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _runtime_present(rom_data) -> bool:
    return _runtime_layout_offsets(rom_data) is not None


def _runtime_layout_offsets(rom_data):
    prefix = bytes(rom_data[_spark24.OFF_RUNTIME:_spark24.OFF_RUNTIME + 3])
    if prefix == _spark24.RUNTIME[:3]:
        return "current", _spark24._OFFSETS
    if prefix == _spark24.PRE_SPARK_TRAIL_RUNTIME[:3]:
        return "pre_spark_trail", _spark24._PRE_SPARK_TRAIL_OFFSETS
    return None


def current_pause_digits(rom_data) -> tuple[int, int, int, int]:
    if rom_data is None:
        raise SparkBallVariantError("ROM is not loaded")
    layout = _runtime_layout_offsets(rom_data)
    if layout is not None:
        _name, offsets = layout
        return tuple(
            int(rom_data[_spark24.OFF_RUNTIME + off])
            for off in offsets["pause_digits"]
        )
    return DEFAULT_PAUSE_DIGITS


def current_transparency_period(rom_data) -> int:
    if rom_data is None:
        raise SparkBallVariantError("ROM is not loaded")
    layout = _runtime_layout_offsets(rom_data)
    if layout is not None:
        _name, offsets = layout
        value = int(
            rom_data[
                _spark24.OFF_RUNTIME + offsets["transparency_period"]
            ]
        )
        return value if value in TRANSPARENCY_PERIODS else DEFAULT_TRANSPARENCY_PERIOD
    return DEFAULT_TRANSPARENCY_PERIOD


def current_reverse_digits(rom_data) -> tuple[int, int, int, int]:
    if rom_data is None:
        raise SparkBallVariantError("ROM is not loaded")
    layout = _runtime_layout_offsets(rom_data)
    if layout is not None:
        _name, offsets = layout
        return tuple(
            int(rom_data[_spark24.OFF_RUNTIME + off])
            for off in offsets["reverse_digits"]
        )
    return DEFAULT_REVERSE_DIGITS


def _runtime_matches_supported_configuration(rom_data, current_runtime: bytes) -> bool:
    layout = _runtime_layout_offsets(rom_data)
    if layout is None:
        return False
    try:
        builder = (
            _spark24.build_runtime
            if layout[0] == "current"
            else _spark24.build_pre_spark_trail_runtime
        )
        expected, _offsets = builder(
            current_pause_digits(rom_data),
            current_reverse_digits(rom_data),
            current_transparency_period(rom_data),
        )
    except _spark24.Spark24RuntimeError:
        return False
    if current_runtime[:len(expected)] != expected:
        return False
    return all(value in (0x00, 0xEA) for value in current_runtime[len(expected):])


def apply(rom_data, pause_digits=None, transparency_period=None,
          reverse_digits=None) -> list[str]:
    min_len = max(
        _spark24.OFF_RUNTIME + len(_spark24.RUNTIME),
        OFF_AB13 + 3,
        OFF_A2CC + 3,
        OFF_85FA + len(ORIG_85FA),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise SparkBallVariantError("ROM is too short for Spark24 runtime patch.")
    try:
        pause_digits = _spark24.normalize_digits(
            current_pause_digits(rom_data) if pause_digits is None else pause_digits
        )
        reverse_digits = _spark24.normalize_digits(
            current_reverse_digits(rom_data) if reverse_digits is None else reverse_digits
        )
        if transparency_period is None:
            transparency_period = current_transparency_period(rom_data)
        runtime, offsets = _spark24.build_runtime(
            pause_digits, reverse_digits, transparency_period
        )
    except _spark24.Spark24RuntimeError as exc:
        raise SparkBallVariantError(str(exc)) from exc

    hook_ab13 = bytes((0x4C, offsets["pause"] & 0xFF, offsets["pause"] >> 8))
    hook_a2cc = bytes((0x20, offsets["property"] & 0xFF, offsets["property"] >> 8))
    hook_85fa = bytes((0x4C, offsets["oam"] & 0xFF, offsets["oam"] >> 8))
    previous_offsets = _spark24._PRE_SPARK_TRAIL_OFFSETS
    previous_hook_ab13 = bytes((
        0x4C,
        previous_offsets["pause"] & 0xFF,
        previous_offsets["pause"] >> 8,
    ))
    previous_hook_a2cc = bytes((
        0x20,
        previous_offsets["property"] & 0xFF,
        previous_offsets["property"] >> 8,
    ))
    previous_hook_85fa = bytes((
        0x4C,
        previous_offsets["oam"] & 0xFF,
        previous_offsets["oam"] >> 8,
    )) + bytes((0xEA,)) * 3
    panel_a2cc = bytes((0x20, CPU_PANEL_PROPERTY_HOOK & 0xFF, CPU_PANEL_PROPERTY_HOOK >> 8))
    new_oam = hook_85fa + bytes((0xEA,)) * 3

    current_runtime = bytes(
        rom_data[_spark24.OFF_RUNTIME:_spark24.OFF_RUNTIME + len(runtime)]
    )
    current_is_blank = all(value in (0x00, 0xEA) for value in current_runtime)
    current_is_supported = _runtime_matches_supported_configuration(
        rom_data, current_runtime
    )
    if current_runtime != runtime and not current_is_blank and not current_is_supported:
        raise SparkBallVariantError(
            f"Spark24 runtime area is not blank at file 0x{_spark24.OFF_RUNTIME:X}: "
            f"got {current_runtime.hex(' ')}"
        )
    current_ab13 = bytes(rom_data[OFF_AB13:OFF_AB13 + 3])
    current_a2cc = bytes(rom_data[OFF_A2CC:OFF_A2CC + 3])
    current_85fa = bytes(rom_data[OFF_85FA:OFF_85FA + len(ORIG_85FA)])
    if current_ab13 not in (ORIG_AB13_HEAD, previous_hook_ab13, hook_ab13):
        raise SparkBallVariantError(f"$AB13 signature mismatch: got {current_ab13.hex(' ')}")
    if current_a2cc not in (
        ORIG_A2CC_HEAD, panel_a2cc, previous_hook_a2cc, hook_a2cc,
    ):
        raise SparkBallVariantError(f"$A2CC signature mismatch: got {current_a2cc.hex(' ')}")
    if current_85fa not in (ORIG_85FA, previous_hook_85fa, new_oam):
        raise SparkBallVariantError(f"$85FA signature mismatch: got {current_85fa.hex(' ')}")

    changed: list[str] = []
    _write_blob(rom_data, _spark24.OFF_RUNTIME, runtime, changed, "Spark24 integrated runtime")
    _write_blob(rom_data, OFF_AB13, hook_ab13, changed, "$AB13 Spark24 pause dispatch")
    _write_blob(rom_data, OFF_A2CC, hook_a2cc, changed, "$A2CC Spark24 property dispatch")
    _write_blob(rom_data, OFF_85FA, new_oam, changed, "$85FA Spark24 transparency dispatch")
    return changed
