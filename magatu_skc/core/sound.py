"""Sound data reader for Solomon's Key PRG0 music sequences.

This module is intentionally read-only.  It follows the sound driver
confirmed at SUB_F190/SUB_F235 in the commented ASM:

* $00-$7F: note/hold byte
* $80-$EF: duration byte, index = byte & $3F
* $F0-$F9: sound commands
"""
from dataclasses import dataclass


SOUND_POINTER_TABLE_CPU = 0xF47C
SOUND_POINTER_COUNT = 26
SOUND_HEADER_FIRST_CPU = 0xF4B0
SOUND_SEQUENCE_FIRST_CPU = 0xF592
DURATION_TABLE_CPU = 0xF380
DURATION_TABLE_COUNT = 26

NOTE_NAMES = (
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
)
FLAT_ALIASES = {
    1: "Db",
    3: "Eb",
    6: "Gb",
    8: "Ab",
    10: "Bb",
}

SOUND_NAMES = (
    "ステージBGM",
    "ボーナス面BGM",
    "死亡",
    "残り時間警告",
    "ゲームオーバー",
    "1UP",
    "石を作る",
    "石を消す",
    "炎で敵撃破",
    "炎発射",
    "ドラゴン火炎",
    "ポーズ音",
    "アイテム取得",
    "未使用/無音",
    "妖精取得",
    "エンディングBGM",
    "頭突き音",
    "壊せない石",
    "スコア加算中",
    "ステージ開始",
    "ステージクリア",
    "鍵取得",
    "パネルモンスター発射",
    "未使用/無音枠",
    "迷宮崩れ1",
    "迷宮崩れ2",
)

CHANNEL_HINTS = {
    0: "ch0",
    1: "ch1 Triangle/Bass",
    2: "ch2 Pulse2/Harmony",
    3: "ch3 Pulse1/Melody",
    4: "ch4",
    5: "ch5",
    6: "ch6",
    7: "ch7 Noise/Rhythm",
}


@dataclass(frozen=True)
class SoundChannel:
    raw_channel_id: int
    channel_id: int
    sequence_cpu: int


@dataclass(frozen=True)
class SoundSong:
    sound_id: int
    name: str
    header_cpu: int
    channels: tuple[SoundChannel, ...]


def cpu_to_file(cpu_addr: int) -> int:
    """Convert fixed PRG0 CPU address to iNES file offset."""
    if not (0x8000 <= int(cpu_addr) <= 0xFFFF):
        raise ValueError(f"CPU address out of PRG0 range: ${int(cpu_addr):04X}")
    return 0x10 + (int(cpu_addr) - 0x8000)


def _u8(rom_data: bytes | bytearray, cpu_addr: int) -> int:
    off = cpu_to_file(cpu_addr)
    if off >= len(rom_data):
        raise ValueError(f"sound address out of ROM range: ${cpu_addr:04X}")
    return int(rom_data[off])


def _word_at(rom_data: bytes | bytearray, cpu_addr: int) -> int:
    lo = _u8(rom_data, cpu_addr)
    hi = _u8(rom_data, cpu_addr + 1)
    return lo | (hi << 8)


def _read_bytes(rom_data: bytes | bytearray, cpu_addr: int, count: int) -> bytes:
    off = cpu_to_file(cpu_addr)
    end = off + int(count)
    if end > len(rom_data):
        raise ValueError(f"sound byte range out of ROM range: ${cpu_addr:04X}+{count}")
    return bytes(rom_data[off:end])


def _duration_ticks(rom_data: bytes | bytearray, index: int) -> int | None:
    if not (0 <= index < DURATION_TABLE_COUNT):
        return None
    return _u8(rom_data, DURATION_TABLE_CPU + index)


def read_sound_songs(rom_data: bytes | bytearray) -> list[SoundSong]:
    """Read the 26 sound headers from the original PRG0 sound table."""
    ptrs = [
        _word_at(rom_data, SOUND_POINTER_TABLE_CPU + i * 2)
        for i in range(SOUND_POINTER_COUNT)
    ]
    songs: list[SoundSong] = []
    for index, header_cpu in enumerate(ptrs):
        if not (SOUND_HEADER_FIRST_CPU <= header_cpu < SOUND_SEQUENCE_FIRST_CPU):
            raise ValueError(
                f"sound header pointer #{index + 1} out of expected range: ${header_cpu:04X}"
            )
        next_cpu = ptrs[index + 1] if index + 1 < len(ptrs) else SOUND_SEQUENCE_FIRST_CPU
        channels: list[SoundChannel] = []
        pos = header_cpu
        while pos + 2 < next_cpu:
            raw_channel_id = _u8(rom_data, pos)
            if raw_channel_id >= 0xF0:
                break
            seq_cpu = _word_at(rom_data, pos + 1)
            if not (SOUND_SEQUENCE_FIRST_CPU <= seq_cpu <= 0xFFFF):
                break
            channels.append(
                SoundChannel(
                    raw_channel_id=raw_channel_id,
                    channel_id=raw_channel_id & 0x7F,
                    sequence_cpu=seq_cpu,
                )
            )
            pos += 3
        name = SOUND_NAMES[index] if index < len(SOUND_NAMES) else f"Sound {index + 1}"
        songs.append(
            SoundSong(
                sound_id=index + 1,
                name=name,
                header_cpu=header_cpu,
                channels=tuple(channels),
            )
        )
    return songs


def note_name(byte_value: int) -> str:
    semi = int(byte_value) & 0x0F
    octave = (int(byte_value) >> 4) + 2
    if semi == 0x0C:
        return "HOLD/TIE"
    if semi > 0x0B:
        return f"RAW_NOTE semi={semi}"
    name = NOTE_NAMES[semi]
    alias = FLAT_ALIASES.get(semi)
    if alias:
        return f"{name}{octave}/{alias}{octave}"
    return f"{name}{octave}"


def _raw_hex(raw: bytes) -> str:
    return " ".join(f"{b:02X}" for b in raw)


def _channel_label(channel: SoundChannel) -> str:
    hint = CHANNEL_HINTS.get(channel.channel_id, f"ch{channel.channel_id}")
    first = " first" if channel.raw_channel_id & 0x80 else ""
    return f"{hint}{first}"


def _line(cpu_addr: int, raw: bytes, text: str, depth: int = 0) -> str:
    indent = "  " * depth
    return f"{indent}${cpu_addr:04X}: {_raw_hex(raw):<8} {text}"


def _decode_stream(
    rom_data: bytes | bytearray,
    start_cpu: int,
    *,
    expand_calls: bool,
    depth: int = 0,
    max_depth: int = 3,
    max_events: int = 500,
    stop_on_return: bool = False,
    current_duration: tuple[int, int | None] | None = None,
) -> tuple[list[str], tuple[int, int | None] | None, str]:
    lines: list[str] = []
    pos = int(start_cpu)
    events = 0
    while events < max_events:
        events += 1
        b = _u8(rom_data, pos)

        if b <= 0x7F:
            dur = ""
            if current_duration is not None:
                dur_byte, ticks = current_duration
                dur = f" len=0x{dur_byte:02X}"
                if ticks is not None:
                    dur += f"({ticks}f)"
            lines.append(_line(pos, bytes((b,)), f"NOTE {note_name(b)}{dur}", depth))
            pos += 1
            continue

        if b < 0xF0:
            idx = b & 0x3F
            ticks = _duration_ticks(rom_data, idx)
            current_duration = (b, ticks)
            if ticks is None:
                msg = f"DURATION idx={idx} ticks=? (outside confirmed table)"
            else:
                msg = f"DURATION idx={idx} ticks={ticks}"
            if b > 0x98:
                msg += " [not used by original sequences]"
            lines.append(_line(pos, bytes((b,)), msg, depth))
            pos += 1
            continue

        if b == 0xF0:
            raw = _read_bytes(rom_data, pos, 2)
            lines.append(_line(pos, raw, f"INSTRUMENT {raw[1]}", depth))
            pos += 2
            continue
        if b == 0xF1:
            raw = _read_bytes(rom_data, pos, 2)
            lines.append(_line(pos, raw, f"VOLUME {raw[1] & 0x0F}", depth))
            pos += 2
            continue
        if b == 0xF2:
            raw = _read_bytes(rom_data, pos, 3)
            target = raw[1] | (raw[2] << 8)
            lines.append(_line(pos, raw, f"JUMP ${target:04X} (loop/sequence redirect)", depth))
            return lines, current_duration, "jump"
        if b == 0xF3:
            raw = _read_bytes(rom_data, pos, 3)
            target = raw[1] | (raw[2] << 8)
            lines.append(_line(pos, raw, f"CALL ${target:04X}", depth))
            if expand_calls and depth < max_depth:
                sub_lines, current_duration, reason = _decode_stream(
                    rom_data,
                    target,
                    expand_calls=expand_calls,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_events=max_events,
                    stop_on_return=True,
                    current_duration=current_duration,
                )
                lines.extend(sub_lines)
                if reason not in ("return", "jump", "channel_end"):
                    lines.append("  " * (depth + 1) + f"; CALL ${target:04X} stopped: {reason}")
            pos += 3
            continue
        if b == 0xF4:
            lines.append(_line(pos, bytes((b,)), "RETURN", depth))
            return lines, current_duration, "return" if stop_on_return else "top_return"
        if b == 0xF5:
            raw = _read_bytes(rom_data, pos, 2)
            lines.append(_line(pos, raw, f"LOOP_START count={raw[1]}", depth))
            pos += 2
            continue
        if b == 0xF6:
            lines.append(_line(pos, bytes((b,)), "LOOP_DEC_BNE", depth))
            pos += 1
            continue
        if b == 0xF7:
            raw = _read_bytes(rom_data, pos, 2)
            lines.append(_line(pos, raw, f"SWEEP 0x{raw[1]:02X}", depth))
            pos += 2
            continue
        if b == 0xF8:
            raw = _read_bytes(rom_data, pos, 2)
            lines.append(_line(pos, raw, f"DUTY {raw[1]}", depth))
            pos += 2
            continue
        if b == 0xF9:
            lines.append(_line(pos, bytes((b,)), "CHANNEL_END", depth))
            return lines, current_duration, "channel_end"

        lines.append(_line(pos, bytes((b,)), f"UNKNOWN_COMMAND 0x{b:02X}", depth))
        return lines, current_duration, "unknown_command"

    lines.append("  " * depth + f"; decode stopped at ${pos:04X}: max events reached")
    return lines, current_duration, "max_events"


def format_song_text(
    rom_data: bytes | bytearray,
    song: SoundSong,
    *,
    expand_calls: bool = True,
) -> str:
    lines = [
        f"Sound ${song.sound_id:02X}: {song.name}",
        f"Header: ${song.header_cpu:04X}",
        f"Channels: {len(song.channels)}",
        "",
        "Legend:",
        "  $00-$7F = NOTE / HOLD",
        "  $80-$EF = DURATION (index = byte & $3F)",
        "  $F0-$F9 = command (ASM SUB_F235 dispatch)",
        "",
    ]
    for channel in song.channels:
        lines.append(
            f"== {_channel_label(channel)} / sequence ${channel.sequence_cpu:04X} =="
        )
        decoded, _duration, reason = _decode_stream(
            rom_data,
            channel.sequence_cpu,
            expand_calls=expand_calls,
        )
        lines.extend(decoded)
        lines.append(f"; channel stop reason: {reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def combo_label(song: SoundSong) -> str:
    return f"${song.sound_id:02X} {song.name} ({len(song.channels)}ch)"
