"""左右の新規入力後、横穴の縁に対する原作の位相拒否bitを消すruntime。

現行 ``gap_fix.py`` は復帰用として変更せず、このモジュールだけがROMを
書き込む。座標や落下状態は判定しない。

$83A8 のJOY1保存hookで左/右の neutral->press を検出し、方向別に
設定フレームの窓を開始する。窓の間でも、上側角が壁、下側角が空間の
組み合わせだけ、$8784 で上側の位相拒否bitを消す。普通の壁のように
上下とも壁なら変更しない。
本物の壁・ブロック判定は原作へそのまま任せる。

ROM: $83A8-$83AA input hook / $8784-$8786 collision hook / $E879 runtime
RAM: $0774 前フレームの左右入力、$0775 右窓、$0776 左窓
"""

import hashlib


OFF_INPUT_HOOK = 0x03B8
INPUT_ORIG = bytes.fromhex("9d e4 03")
INPUT_HOOK = bytes.fromhex("4c 79 e8")  # JMP $E879
INPUT_SIG_OFF = 0x03BB
INPUT_SIG = bytes.fromhex("ca 10 eb")

OFF_COLLISION_SIG = 0x078F
COLLISION_SIG = bytes.fromhex("a5 0a 6a 6a 6a")
OFF_COLLISION_HOOK = 0x0794
COLLISION_ORIG = bytes.fromhex("a0 0b 91")
LEGACY_COLLISION_HOOK = bytes.fromhex("4c 79 e8")
PREVIOUS_BOTH_COLLISION_HOOK = bytes.fromhex("4c c8 e8")

OFF_CAVE = 0x6889
CPU_CAVE = 0xE879
RAM_DIRECTION_PREVIOUS = 0x0774
RAM_RIGHT_WINDOW = 0x0775
RAM_LEFT_WINDOW = 0x0776
DEFAULT_WINDOW_FRAMES = 20
MIN_WINDOW_FRAMES = 1
MAX_WINDOW_FRAMES = 255
CANONICAL_WINDOW_FRAMES = 5
LEGACY_CAVE_SIZE = 136

# 現行Gap Fixと、この実験ブランチで既に出した試作だけを切替元として許可。
KNOWN_REPLACEABLE_CAVE_SHA256 = {
    "43ee1e08cb49962b15c398338895f0e9ec3efab5b2a020f99314c06df248f9a2",
    "1480f18de48838727c8b39c7ca36dd1ee2e0efe3204fe56731a6cd9d06660d5b",
    "d64ff030da93a430f218767f84e1e47b828d3f19ab6fcae0adabd75abe8614fd",
    "a590056047678ac8a69f622b56dd5a608fc9348a4c44e3bd1a8dac9a0b60f347",
    "32570e49d47b3fd0cdf345d78b2eabc779f33ac76620b8d23fba945bc233038a",
    "e623ddaa64240457f496e55c48dcc45f35deb0064bf5dc36bf624d273a4c7e7b",
    "b12bd6954835bb9aa2d63f8f18521086807a75de4ba2fdfccfba264e4415924f",
    "a90a0a23206931b96be41648729f5516a9d34930fe7e47a71c2eb019b8b8a890",
    "04047f73e56ddfe97b30d0cf613e393eebdc74522458d229bc31ba79cc902d95",
    "854b561628efd2961d73b5e7f7f8d44229ac82904b51e7a97892604eadc28349",
}
KNOWN_REPLACEABLE_PARAMETERIZED_CAVE_SHA256 = {
    "13b270a01c26b9e8067f13c7596b2c7d72261f907dc537d3f00eff2e7f64af5e",
}


def _build_cave():
    code = bytearray()
    labels = {}
    rel_fixups = []
    abs_fixups = []

    def emit(*values):
        code.extend(values)

    def label(name):
        labels[name] = len(code)

    def branch(opcode, target):
        emit(opcode, 0)
        rel_fixups.append((len(code) - 1, target))

    # $83A8 hook。原作の STA $03E4,X を再現する。
    label("input_entry")
    emit(0x9D, 0xE4, 0x03)             # STA $03E4,X
    emit(0xE0, 0x00)                   # CPX #$00 (JOY1 only)
    branch(0xD0, "input_return")

    # 左右の既存窓を1ゲームフレーム進める。0は減算せず、255化させない。
    emit(0xA0, 0x01)                   # LDY #1: right, then left
    label("counter_loop")
    emit(0xB9, 0x74, 0x07)             # LDA $0774,Y
    emit(0xC9, 0x00)                   # restore zero flag from counter value
    branch(0xF0, "counter_store")
    emit(0x38, 0xE9, 0x01)             # SEC / SBC #1
    label("counter_store")
    emit(0x99, 0x74, 0x07)             # STA $0774,Y
    emit(0xC8, 0xC0, 0x03)             # INY / CPY #3
    branch(0xD0, "counter_loop")

    # edge = current & ~previous。左右を独立して5へ再設定する。
    emit(0xAD, 0xE4, 0x03, 0x29, 0x03) # LDA $03E4 / AND #LR
    emit(0x85, 0x0B)                   # STA $0B (current)
    emit(0xAD, 0x74, 0x07, 0x49, 0xFF) # LDA $0774 / EOR #$FF
    emit(0x25, 0x0B, 0x85, 0x0A)       # AND $0B / STA $0A (edge)
    emit(0xA5, 0x0B, 0x8D, 0x74, 0x07) # LDA $0B / STA $0774

    emit(0xA5, 0x0A, 0x29, 0x01)       # right edge?
    branch(0xF0, "check_left_edge")
    emit(0xA9)
    label("right_window_operand")
    emit(DEFAULT_WINDOW_FRAMES, 0x8D, 0x75, 0x07)

    label("check_left_edge")
    emit(0xA5, 0x0A, 0x29, 0x02)       # left edge?
    branch(0xF0, "input_return")
    emit(0xA9)
    label("left_window_operand")
    emit(DEFAULT_WINDOW_FRAMES, 0x8D, 0x76, 0x07)

    label("input_return")
    emit(0x4C, 0xAB, 0x83)             # JMP $83AB

    # $8784 hook。A=原作の位相拒否mask。Dana以外は変更しない。
    label("collision_entry")
    emit(0x48)                          # PHA
    emit(0xA5, 0x08, 0xC9, 0x7F)       # LDA $08 / CMP #$7F
    branch(0xD0, "collision_done")
    emit(0xAD, 0x75, 0x07)             # right window
    branch(0xF0, "check_left_window")
    emit(0x68, 0x48, 0x29, 0x06)       # mask & (right upper/lower)
    emit(0xC9, 0x02)                   # upper=1, lower=0 ?
    branch(0xD0, "check_left_window")
    emit(0x68, 0x29, 0xFD, 0x48)       # clear right upper only

    label("check_left_window")
    emit(0xAD, 0x76, 0x07)             # left window
    branch(0xF0, "collision_done")
    emit(0x68, 0x48, 0x29, 0x09)       # mask & (left upper/lower)
    emit(0xC9, 0x01)                   # upper=1, lower=0 ?
    branch(0xD0, "collision_done")
    emit(0x68, 0x29, 0xFE, 0x48)       # clear left upper only

    label("collision_done")
    emit(0x68, 0xA0, 0x0B, 0x91, 0x08, 0x60)

    for operand_pos, target in rel_fixups:
        delta = labels[target] - (operand_pos + 1)
        if not -128 <= delta <= 127:
            raise AssertionError(f"branch out of range: {target} {delta}")
        code[operand_pos] = delta & 0xFF
    return bytes(code), labels


CAVE, CAVE_LABELS = _build_cave()
CAVE_WINDOW_OPERAND_OFFSETS = (
    CAVE_LABELS["right_window_operand"],
    CAVE_LABELS["left_window_operand"],
)
CPU_COLLISION_ENTRY = CPU_CAVE + CAVE_LABELS["collision_entry"]
COLLISION_HOOK = bytes((0x4C, CPU_COLLISION_ENTRY & 0xFF, CPU_COLLISION_ENTRY >> 8))
assert CAVE_LABELS["input_entry"] == 0
assert len(CAVE) <= LEGACY_CAVE_SIZE
CAVE_WRITE_IMAGE = CAVE + bytes([0xEA]) * (LEGACY_CAVE_SIZE - len(CAVE))

RESERVED_SPANS = (
    (OFF_INPUT_HOOK, len(INPUT_HOOK)),
    (OFF_COLLISION_HOOK, len(COLLISION_HOOK)),
    (OFF_CAVE, len(CAVE)),
)
RAM_RESERVED_SPANS = ((RAM_DIRECTION_PREVIOUS, 3),)


class GapFixError(ValueError):
    """横穴侵入安定化runtimeの位置・署名・競合検証失敗。"""


def _cave_hash(seg: bytes) -> str:
    return hashlib.sha256(seg).hexdigest()


def _parameter_normalized_cave_hash(seg: bytes) -> str:
    mutable = bytearray(seg)
    for offset in CAVE_WINDOW_OPERAND_OFFSETS:
        mutable[offset] = CANONICAL_WINDOW_FRAMES
    return _cave_hash(bytes(mutable))


def _is_current_cave(seg: bytes) -> bool:
    if len(seg) != LEGACY_CAVE_SIZE:
        return False
    mutable = bytearray(seg)
    wanted = bytearray(CAVE_WRITE_IMAGE)
    for offset in CAVE_WINDOW_OPERAND_OFFSETS:
        mutable[offset] = CANONICAL_WINDOW_FRAMES
        wanted[offset] = CANONICAL_WINDOW_FRAMES
    return bytes(mutable) == bytes(wanted)


def _verify(rom_data) -> None:
    if len(rom_data) < OFF_CAVE + LEGACY_CAVE_SIZE:
        raise GapFixError(f"ROM が小さすぎます (len={len(rom_data)})。")
    if bytes(rom_data[INPUT_SIG_OFF:INPUT_SIG_OFF + len(INPUT_SIG)]) != INPUT_SIG:
        raise GapFixError("$83AB 入力処理署名不一致。別改造との競合があるため中止します。")
    if bytes(rom_data[OFF_COLLISION_SIG:OFF_COLLISION_SIG + len(COLLISION_SIG)]) != COLLISION_SIG:
        raise GapFixError("$877F 衝突処理署名不一致。別改造との競合があるため中止します。")

    input_hook = bytes(rom_data[OFF_INPUT_HOOK:OFF_INPUT_HOOK + 3])
    collision_hook = bytes(rom_data[OFF_COLLISION_HOOK:OFF_COLLISION_HOOK + 3])
    if input_hook not in (INPUT_ORIG, INPUT_HOOK):
        raise GapFixError(f"$83A8 が想定外 ({input_hook.hex()})。")
    if collision_hook not in (
        COLLISION_ORIG, LEGACY_COLLISION_HOOK,
        PREVIOUS_BOTH_COLLISION_HOOK, COLLISION_HOOK,
    ):
        raise GapFixError(f"$8784 が想定外 ({collision_hook.hex()})。")

    seg = bytes(rom_data[OFF_CAVE:OFF_CAVE + LEGACY_CAVE_SIZE])
    if (
        not _is_current_cave(seg)
        and _cave_hash(seg) not in KNOWN_REPLACEABLE_CAVE_SHA256
        and _parameter_normalized_cave_hash(seg) not in KNOWN_REPLACEABLE_PARAMETERIZED_CAVE_SHA256
        and not all(b in (0xEA, 0x00) for b in seg)
    ):
        raise GapFixError("cave $E879 が既知runtimeまたは空きではありません。")


def is_applied(rom_data) -> bool:
    _verify(rom_data)
    return (
        bytes(rom_data[OFF_INPUT_HOOK:OFF_INPUT_HOOK + 3]) == INPUT_HOOK
        and bytes(rom_data[OFF_COLLISION_HOOK:OFF_COLLISION_HOOK + 3]) == COLLISION_HOOK
    )


def get_window_frames(rom_data) -> int:
    _verify(rom_data)
    seg = bytes(rom_data[OFF_CAVE:OFF_CAVE + LEGACY_CAVE_SIZE])
    if not _is_current_cave(seg):
        return DEFAULT_WINDOW_FRAMES
    values = [seg[offset] for offset in CAVE_WINDOW_OPERAND_OFFSETS]
    if values[0] != values[1] or not MIN_WINDOW_FRAMES <= values[0] <= MAX_WINDOW_FRAMES:
        raise GapFixError("左右の許可フレーム設定が一致しません。")
    return values[0]


def apply(rom_data, enable: bool, window_frames=None) -> list:
    """左右の新規入力後、設定フレーム中だけ横穴縁の位相拒否bitを消す。"""
    _verify(rom_data)
    changed = []
    current_seg = bytes(rom_data[OFF_CAVE:OFF_CAVE + LEGACY_CAVE_SIZE])
    if window_frames is None:
        window_frames = get_window_frames(rom_data)
    window_frames = int(window_frames)
    if not MIN_WINDOW_FRAMES <= window_frames <= MAX_WINDOW_FRAMES:
        raise GapFixError(f"許可フレームは {MIN_WINDOW_FRAMES}-{MAX_WINDOW_FRAMES} の範囲です。")
    wanted_cave = bytearray(CAVE_WRITE_IMAGE)
    for offset in CAVE_WINDOW_OPERAND_OFFSETS:
        wanted_cave[offset] = window_frames
    wanted_cave = bytes(wanted_cave)
    if current_seg != wanted_cave:
        rom_data[OFF_CAVE:OFF_CAVE + LEGACY_CAVE_SIZE] = wanted_cave
        changed.append("横穴侵入安定化runtime $E879-$E8F0 注入")
    wanted_input = INPUT_HOOK if enable else INPUT_ORIG
    if bytes(rom_data[OFF_INPUT_HOOK:OFF_INPUT_HOOK + 3]) != wanted_input:
        rom_data[OFF_INPUT_HOOK:OFF_INPUT_HOOK + 3] = wanted_input
        changed.append("$83A8 左右入力監視hook " + ("ON" if enable else "OFF"))
    wanted_collision = COLLISION_HOOK if enable else COLLISION_ORIG
    if bytes(rom_data[OFF_COLLISION_HOOK:OFF_COLLISION_HOOK + 3]) != wanted_collision:
        rom_data[OFF_COLLISION_HOOK:OFF_COLLISION_HOOK + 3] = wanted_collision
        changed.append("$8784 左右位相拒否解除hook " + ("ON" if enable else "OFF"))
    return changed
