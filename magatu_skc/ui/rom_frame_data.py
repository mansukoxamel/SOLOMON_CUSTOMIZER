"""Shared extraction and attribute decoding for ROM 16x16 entity frames."""

from __future__ import annotations

from dataclasses import dataclass


FRAME_DATA_LO = 0xD600
FRAME_DATA_HI = 0xDA00
GROUP_POINTER_TABLE = 0xD0E8
GROUP_COUNT = 32
MAX_STATES_PER_GROUP = 64


@dataclass(frozen=True)
class RomFrameRecord:
    group: int
    state: int
    type_variant: int | None
    frame: int
    left_tile: int
    right_tile: int
    attr: int

    @property
    def enemy_type(self) -> int | None:
        if self.type_variant is None:
            return None
        return self.group * 4 + self.type_variant

    @property
    def edit_key(self) -> tuple[int, int, int]:
        return self.left_tile, self.right_tile, self.attr


def packed_sprite_palette_numbers(attr: int) -> tuple[int, int]:
    """Decode the two palette numbers exactly like the original OAM writer."""
    value = int(attr) & 0xFF
    left = ((value >> 7) & 1) | (((value >> 6) & 1) << 1)
    right = (value >> 2) & 3
    return left, right


def read_rom_frame_records(rom_data: bytes | bytearray) -> list[RomFrameRecord]:
    """Read every type/state/frame route reachable through the $D0E8 tables."""
    data = rom_data

    def file_offset(cpu_address: int) -> int:
        return 0x10 + (int(cpu_address) - 0x8000)

    def byte_at(cpu_address: int) -> int | None:
        offset = file_offset(cpu_address)
        if 0 <= offset < len(data):
            return int(data[offset])
        return None

    def word_at(cpu_address: int) -> int | None:
        lo = byte_at(cpu_address)
        hi = byte_at(cpu_address + 1)
        if lo is None or hi is None:
            return None
        return lo | (hi << 8)

    group_ptrs = [word_at(GROUP_POINTER_TABLE + group * 2) for group in range(GROUP_COUNT)]
    valid_ptrs = sorted({ptr for ptr in group_ptrs if ptr is not None})
    bounds = {
        ptr: valid_ptrs[index + 1] if index + 1 < len(valid_ptrs) else FRAME_DATA_LO
        for index, ptr in enumerate(valid_ptrs)
    }

    records = []
    for group, base in enumerate(group_ptrs):
        if base is None:
            continue
        state_count = min(
            max(0, (bounds.get(base, base + 4) - base) // 4),
            MAX_STATES_PER_GROUP,
        )
        for state in range(state_count):
            entry_address = base + state * 4
            phase = byte_at(entry_address)
            reference_info = byte_at(entry_address + 1)
            pointer = word_at(entry_address + 2)
            if phase is None or reference_info is None or pointer is None:
                continue
            frame_count = (phase & 0x0F) + 1
            if reference_info & 1:
                final_pointers = [
                    (type_variant, word_at(pointer + type_variant * 2))
                    for type_variant in range(4)
                ]
            else:
                final_pointers = [(None, pointer)]

            for type_variant, final_pointer in final_pointers:
                if final_pointer is None or not (FRAME_DATA_LO <= final_pointer < FRAME_DATA_HI):
                    continue
                for frame in range(frame_count):
                    frame_address = final_pointer + frame * 3
                    if frame_address + 2 >= FRAME_DATA_HI:
                        break
                    left_tile = byte_at(frame_address)
                    right_tile = byte_at(frame_address + 1)
                    attr = byte_at(frame_address + 2)
                    if left_tile is None or right_tile is None or attr is None:
                        break
                    records.append(RomFrameRecord(
                        group=group,
                        state=state,
                        type_variant=type_variant,
                        frame=frame,
                        left_tile=left_tile,
                        right_tile=right_tile,
                        attr=attr,
                    ))
    records.extend(_read_installed_runtime_frame_records(data))
    return records


def _read_installed_runtime_frame_records(
    rom_data: bytes | bytearray,
) -> list[RomFrameRecord]:
    from ..core import ice_flame_runtime, seraphic_radiance9d_runtime

    records = []
    runtime_specs = (
        (
            ice_flame_runtime.NEW_ENEMY_ID,
            ice_flame_runtime.OFF_RUNTIME,
            ice_flame_runtime.RUNTIME,
            0x14,
            ((0xD6, 0xD4, 0x5A),),
        ),
        (
            seraphic_radiance9d_runtime.NEW_ENEMY_ID,
            seraphic_radiance9d_runtime.OFF_RUNTIME,
            seraphic_radiance9d_runtime.RUNTIME,
            0x00,
            ((0xB2, 0xB2, 0xCF), (0xB0, 0xB0, 0xCE)),
        ),
    )
    for enemy_id, offset, runtime, state, frames in runtime_specs:
        end = offset + len(runtime)
        if end > len(rom_data) or bytes(rom_data[offset:end]) != runtime:
            continue
        for frame, (left_tile, right_tile, attr) in enumerate(frames):
            records.append(RomFrameRecord(
                group=enemy_id // 4,
                state=state,
                type_variant=enemy_id & 3,
                frame=frame,
                left_tile=left_tile,
                right_tile=right_tile,
                attr=attr,
            ))
    return records
