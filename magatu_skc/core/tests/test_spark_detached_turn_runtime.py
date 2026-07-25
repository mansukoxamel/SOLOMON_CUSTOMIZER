from __future__ import annotations

import unittest
from types import SimpleNamespace

from magatu_skc.core import spark_detached_turn_runtime as target
from magatu_skc.core import spark24_runtime
from tools.verify_spark_trail_d8_isolated_v7 import Cpu as BaseCpu, SENTINEL


class GateCpu(BaseCpu):
    def step(self) -> bool:
        op = self.memory[self.pc]
        if op == 0x49:  # EOR #imm
            self.a ^= self.memory[self.pc + 1]
            self.set_zn(self.a)
            self.pc = (self.pc + 2) & 0xFFFF
            self.steps += 1
            return True
        if op == 0x91:  # STA (zp),Y
            zp = self.memory[self.pc + 1]
            base = self.memory[zp] | (self.memory[(zp + 1) & 0xFF] << 8)
            self.memory[(base + self.y) & 0xFFFF] = self.a
            self.pc = (self.pc + 2) & 0xFFFF
            self.steps += 1
            return True
        if op == 0xC8:  # INY
            self.y = (self.y + 1) & 0xFF
            self.set_zn(self.y)
            self.pc = (self.pc + 1) & 0xFFFF
            self.steps += 1
            return True
        return super().step()

    def run_gate(self) -> int:
        return_address = (SENTINEL - 1) & 0xFFFF
        self.push(return_address >> 8)
        self.push(return_address)
        runtime_end = target.CPU_RUNTIME + len(target.RUNTIME)
        while target.CPU_RUNTIME <= self.pc < runtime_end:
            if not self.step():
                return SENTINEL
        return self.pc


def new_cpu(
    enemy_id: int,
    collision_mask: int,
    direction: int,
    reserved_direction: int,
) -> GateCpu:
    memory = bytearray(0x10000)
    memory[
        target.CPU_RUNTIME:
        target.CPU_RUNTIME + len(target.RUNTIME)
    ] = target.RUNTIME
    memory[0x2E:0x30] = bytes((0x00, 0x02))
    memory[0x2C:0x2E] = bytes((0x20, 0x02))
    memory[0x0201] = enemy_id
    memory[0x07] = collision_mask
    memory[0x04] = direction
    memory[0x05] = reserved_direction
    memory[0x0226] = direction
    memory[0x0227] = reserved_direction
    return GateCpu(memory, target.CPU_RUNTIME)


class SparkDetachedTurnRuntimeTests(unittest.TestCase):
    def test_accepted_runtime_shape_and_placement_are_exact(self) -> None:
        self.assertEqual(target.OFF_RUNTIME, 0x60A3)
        self.assertEqual(target.CPU_RUNTIME, 0xE093)
        self.assertEqual(len(target.RUNTIME), 29)
        self.assertEqual(
            target.RUNTIME.hex(),
            "a001b12ec9f89012a507f00e"
            "a505a006912ca5044901c8912c604c13ab",
        )
        self.assertEqual(target.HOOK_POSITION_COMMIT, bytes.fromhex("4c 93 e0"))
        self.assertEqual(target.OFF_RUNTIME + len(target.RUNTIME), 0x60C0)

    def test_all_ids_masks_and_reserved_directions_have_the_expected_result(
        self,
    ) -> None:
        for enemy_id in range(0x100):
            for collision_mask in (0x00, 0x01, 0x02, 0x04, 0x07, 0x80, 0xFF):
                for direction in range(4):
                    for reserved_direction in range(4):
                        with self.subTest(
                            enemy_id=enemy_id,
                            collision_mask=collision_mask,
                            direction=direction,
                            reserved_direction=reserved_direction,
                        ):
                            cpu = new_cpu(
                                enemy_id,
                                collision_mask,
                                direction,
                                reserved_direction,
                            )
                            endpoint = cpu.run_gate()
                            if (
                                enemy_id < target.FIRST_ID
                                or collision_mask == 0
                            ):
                                self.assertEqual(
                                    endpoint,
                                    target.CPU_STOCK_POSITION_COMMIT,
                                )
                                self.assertEqual(
                                    cpu.memory[0x0226],
                                    direction,
                                )
                            else:
                                self.assertEqual(endpoint, SENTINEL)
                                self.assertEqual(
                                    cpu.memory[0x0226],
                                    reserved_direction,
                                )
                                self.assertEqual(
                                    cpu.memory[0x0227],
                                    direction ^ 0x01,
                                )
                            if (
                                enemy_id < target.FIRST_ID
                                or collision_mask == 0
                            ):
                                self.assertEqual(
                                    cpu.memory[0x0227],
                                    reserved_direction,
                                )

    def test_all_eight_ids_preserve_their_stock_turn_handedness(self) -> None:
        right_hand = (2, 3, 1, 0)
        left_hand = (3, 2, 0, 1)
        initial_next = (2, 2, 0, 0)
        for enemy_id in target.NEW_ENEMY_IDS:
            direction = enemy_id & 0x03
            reserved_direction = initial_next[direction]
            turn_table = (
                right_hand
                if direction in (0, 3)
                else left_hand
            )
            for turn in range(4):
                with self.subTest(enemy_id=enemy_id, turn=turn):
                    self.assertEqual(
                        reserved_direction,
                        turn_table[direction],
                    )
                    cpu = new_cpu(
                        enemy_id,
                        0x01,
                        direction,
                        reserved_direction,
                    )
                    self.assertEqual(cpu.run_gate(), SENTINEL)
                    direction = cpu.memory[0x0226]
                    reserved_direction = cpu.memory[0x0227]
            self.assertEqual(direction, enemy_id & 0x03)
            self.assertEqual(
                reserved_direction,
                initial_next[enemy_id & 0x03],
            )

    def test_no_global_or_additional_subslot_storage_is_allocated(self) -> None:
        self.assertEqual(target.RESERVED_SPANS, ((0x60A3, 29),))
        self.assertEqual(
            target.RUNTIME.count(bytes((0x91, 0x2C))),
            2,
        )

    def test_property_fold_selects_only_spark_and_final_enemy_ranges(self) -> None:
        property_start = (
            spark24_runtime.CPU_PROPERTY_DISPATCH
            - spark24_runtime.CPU_RUNTIME
        )
        property_end = (
            spark24_runtime.CPU_OAM_DISPATCH
            - spark24_runtime.CPU_RUNTIME
        )
        self.assertEqual(
            spark24_runtime.RUNTIME[property_start:property_end],
            bytes.fromhex(
                "a5 05 49 20 c9 d8 90 03 "
                "a9 19 60 4c df e6 ea ea"
            ),
        )
        self.assertEqual(
            spark24_runtime._OFFSETS,
            spark24_runtime._PRE_FINAL_ENEMY_OFFSETS,
        )
        for enemy_id in range(0x100):
            folded_is_spark = (enemy_id ^ 0x20) >= 0xD8
            expected = (
                spark24_runtime.FIRST_ID
                <= enemy_id
                <= spark24_runtime.PROPERTY_LAST_ID
                or target.FIRST_ID <= enemy_id <= target.LAST_ID
            )
            with self.subTest(enemy_id=enemy_id):
                self.assertEqual(folded_is_spark, expected)

    def test_direct_and_mirror_placements_are_detected(self) -> None:
        for enemy_id in target.NEW_ENEMY_IDS:
            with self.subTest(enemy_id=enemy_id):
                direct = SimpleNamespace(element_no=enemy_id)
                level = SimpleNamespace(enemies=[direct])
                self.assertTrue(target.levels_need_runtime([level]))

    def test_apply_is_idempotent_and_preserves_the_twelve_byte_tail(
        self,
    ) -> None:
        rom = bytearray((0xEA,)) * 0x10000
        rom[
            target.OFF_POSITION_COMMIT_HOOK:
            target.OFF_POSITION_COMMIT_HOOK + 3
        ] = target.ORIG_POSITION_COMMIT_HOOK
        tail_start = target.OFF_RUNTIME + len(target.RUNTIME)
        tail_end = 0x60CC
        tail_before = bytes(rom[tail_start:tail_end])

        changed = target.apply(rom)
        self.assertEqual(len(changed), 2)
        self.assertEqual(bytes(rom[tail_start:tail_end]), tail_before)
        self.assertEqual(target.apply(rom), [])


if __name__ == "__main__":
    unittest.main()
