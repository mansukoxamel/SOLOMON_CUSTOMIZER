from __future__ import annotations

import unittest

from magatu_skc.core import spark24_runtime
from magatu_skc.core import spark_trail_runtime as target
from tools.verify_spark_trail_d8_isolated_v7 import Cpu as BaseCpu


MAP_BASE = 0x0304
MAP_SIZE = 0xE0
N = 0x80


class Cpu(BaseCpu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spark_speeds: list[int] = []

    def external_jsr(self, destination: int) -> bool:
        if destination == target.CPU_STOCK_SPARK_BODY:
            self.spark_speeds.append(self.x)
            # The real stock body clears $00-$07 at $A93A-$A941.
            # Reproduce that destructive contract instead of using a no-op.
            self.memory[0x00:0x08] = bytes(8)
            return True
        return super().external_jsr(destination)

    def step(self) -> bool:
        opcode = self.memory[self.pc]
        if opcode == 0x10:  # BPL
            self.steps += 1
            if self.steps > 2000:
                raise RuntimeError(f"step limit at ${self.pc:04X}")
            self.branch(not self.p & N)
            return True
        if opcode == 0x4A:  # LSR A
            carry = self.a & 0x01
            self.a >>= 1
            self.p = (self.p & ~0x01) | carry
            self.set_zn(self.a)
            self.pc = (self.pc + 1) & 0xFFFF
            self.steps += 1
            return True
        return super().step()


def runtime_memory() -> bytearray:
    memory = bytearray(0x10000)
    memory[
        target.CPU_MAIN_RUNTIME:
        target.CPU_MAIN_RUNTIME + len(target.MAIN_RUNTIME)
    ] = target.MAIN_RUNTIME
    memory[
        target.CPU_AUX_RUNTIME:
        target.CPU_AUX_RUNTIME + len(target.AUX_RUNTIME)
    ] = target.AUX_RUNTIME
    return memory


def new_cpu(entry: int, *, enemy_id: int = target.FIRST_ID) -> Cpu:
    cpu = Cpu(runtime_memory(), entry)
    cpu.memory[0x2E] = 0x00
    cpu.memory[0x2F] = 0x02
    cpu.memory[0x0201] = enemy_id
    return cpu


def fill_map(cpu: Cpu, value: int = 0xF8) -> None:
    cpu.memory[MAP_BASE:MAP_BASE + MAP_SIZE] = bytes((value,)) * MAP_SIZE


class SparkTrailRuntimeTests(unittest.TestCase):
    def test_prg0_growth_is_exactly_242_bytes(self) -> None:
        spark24_growth = (
            len(spark24_runtime.RUNTIME)
            - len(spark24_runtime.PRE_SPARK_TRAIL_RUNTIME)
        )
        self.assertEqual(spark24_growth, 7)
        self.assertEqual(len(target.MAIN_RUNTIME), 133)
        self.assertEqual(len(target.AUX_RUNTIME), 102)
        self.assertEqual(
            spark24_growth + len(target.MAIN_RUNTIME) + len(target.AUX_RUNTIME),
            242,
        )
        self.assertEqual(
            spark24_runtime.OFF_RUNTIME + len(spark24_runtime.RUNTIME),
            target.OFF_AUX_RUNTIME,
        )
        self.assertEqual(target.OFF_AUX_RUNTIME + len(target.AUX_RUNTIME), 0x3FF0)
        self.assertEqual(target.OFF_MAIN_RUNTIME + len(target.MAIN_RUNTIME), 0x6E9E)

    def test_all_eight_ids_select_the_expected_speed(self) -> None:
        for enemy_id in range(target.FIRST_ID, target.LAST_ID + 1):
            with self.subTest(enemy_id=enemy_id):
                cpu = new_cpu(
                    target.CPU_MAIN_RUNTIME,
                    enemy_id=enemy_id,
                )
                cpu.a = enemy_id - 0x14
                cpu.position_cells = [0x55, 0x55]
                cpu.run()
                expected = 0 if enemy_id < target.FAST_FIRST_ID else 4
                self.assertEqual(cpu.spark_speeds, [expected])

    def test_stock_spark_zero_page_clear_does_not_destroy_old_cell(self) -> None:
        old_cell = 0x55
        cpu = new_cpu(target.CPU_MAIN_RUNTIME)
        cpu.a = target.FIRST_ID - 0x14
        cpu.position_cells = [old_cell, old_cell + 1]
        fill_map(cpu)
        cpu.memory[MAP_BASE + old_cell] = 0x08
        for slot in range(21):
            pointer = 0x0400 + slot * 0x14
            cpu.memory[target.CPU_MAIN_PTR_LO + slot] = pointer & 0xFF
            cpu.memory[target.CPU_MAIN_PTR_HI + slot] = pointer >> 8
        cpu.run()
        self.assertEqual(cpu.memory[MAP_BASE + old_cell], 0xC8)

    def test_map_read_is_passable_only_for_spark_trail_ids(self) -> None:
        cell = 0x55
        for enemy_id in range(0x100):
            for value in range(0x100):
                cpu = new_cpu(target.CPU_SPARK_MAP_READ, enemy_id=enemy_id)
                cpu.x = cell
                cpu.y = 7
                cpu.memory[MAP_BASE + cell] = value
                cpu.run()
                expected = value
                if (
                    target.FIRST_ID <= enemy_id <= target.LAST_ID
                    and 0xC8 <= value <= 0xF7
                ):
                    expected &= 0x7F
                self.assertEqual(
                    cpu.a,
                    expected,
                    f"id=${enemy_id:02X} value=${value:02X}",
                )
                self.assertEqual(cpu.y, 7)

    def test_frontier_source_ranges_are_exact(self) -> None:
        center = 0x55
        candidate = center - 0x10
        for value in range(0x100):
            with self.subTest(value=value):
                cpu = new_cpu(target.CPU_AUX_RUNTIME)
                cpu.y = center
                fill_map(cpu)
                cpu.memory[MAP_BASE + candidate] = value
                for slot in range(21):
                    pointer = 0x0400 + slot * 0x14
                    cpu.memory[target.CPU_MAIN_PTR_LO + slot] = pointer & 0xFF
                    cpu.memory[target.CPU_MAIN_PTR_HI + slot] = pointer >> 8
                cpu.run()
                should_fill = (
                    0x08 <= value <= 0x37
                    or 0x48 <= value <= 0x77
                )
                expected = (value | 0xC0) if should_fill else value
                self.assertEqual(cpu.memory[MAP_BASE + candidate], expected)

    def test_each_nonself_sprite_slot_blocks_placement(self) -> None:
        old_cell = 0x55
        candidate_x = ((old_cell & 0x0F) << 4) + 0x08
        candidate_y = (old_cell & 0xF0) + 0x10
        self_pointer = 0x0200

        for occupied_slot in range(21):
            with self.subTest(occupied_slot=occupied_slot):
                cpu = new_cpu(target.CPU_MAIN_RUNTIME)
                cpu.a = target.FIRST_ID - 0x14
                cpu.position_cells = [old_cell, old_cell + 1]
                fill_map(cpu)
                cpu.memory[MAP_BASE + old_cell] = 0x08

                for slot in range(21):
                    pointer = 0x0400 + slot * 0x14
                    cpu.memory[target.CPU_MAIN_PTR_LO + slot] = pointer & 0xFF
                    cpu.memory[target.CPU_MAIN_PTR_HI + slot] = pointer >> 8
                cpu.memory[
                    target.CPU_MAIN_PTR_LO + 20
                ] = self_pointer & 0xFF
                cpu.memory[
                    target.CPU_MAIN_PTR_HI + 20
                ] = self_pointer >> 8

                pointer = (
                    cpu.memory[target.CPU_MAIN_PTR_LO + occupied_slot]
                    | (cpu.memory[target.CPU_MAIN_PTR_HI + occupied_slot] << 8)
                )
                cpu.memory[pointer] = 0x80
                cpu.memory[pointer + 0x0A] = candidate_x
                cpu.memory[pointer + 0x07] = candidate_y
                cpu.run()

                expected = 0xC8 if occupied_slot == 20 else 0x08
                self.assertEqual(cpu.memory[MAP_BASE + old_cell], expected)


if __name__ == "__main__":
    unittest.main()
