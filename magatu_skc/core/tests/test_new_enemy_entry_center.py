from __future__ import annotations

import unittest
import hashlib
from types import SimpleNamespace

from magatu_skc.core.element import ElementType
from magatu_skc.core import new_enemy_runtime as target
from tools.verify_spark_trail_d8_isolated_v7 import Cpu as BaseCpu, SENTINEL


class EntryCpu(BaseCpu):
    def external_jsr(self, destination: int) -> bool:
        if destination in (0x8789, 0x9D1C):
            return True
        return super().external_jsr(destination)

    def run_entry(self, ranges: tuple[tuple[int, int], ...]) -> int:
        return_address = (SENTINEL - 1) & 0xFFFF
        self.push(return_address >> 8)
        self.push(return_address)
        while any(start <= self.pc < end for start, end in ranges):
            if not self.step():
                return SENTINEL
        return self.pc

    def step(self) -> bool:
        if self.memory[self.pc] == 0x91:  # STA (zp),Y
            zp = self.memory[self.pc + 1]
            base = self.memory[zp] | (self.memory[(zp + 1) & 0xFF] << 8)
            self.memory[(base + self.y) & 0xFFFF] = self.a
            self.pc = (self.pc + 2) & 0xFFFF
            self.steps += 1
            return True
        return super().step()


class NewEnemyEntryCenterTests(unittest.TestCase):
    @staticmethod
    def _branch_target(blob: bytes, opcode_pos: int) -> int:
        displacement = blob[opcode_pos + 1]
        if displacement >= 0x80:
            displacement -= 0x100
        return opcode_pos + 2 + displacement

    def test_entry_center_frees_34_bytes_after_spark_trail_palette_hook(self) -> None:
        self.assertEqual(
            tuple(map(len, (
                target.AI_ENTRY_RUNTIME,
                target.SETUP_ENTRY_RUNTIME,
                target.INIT_ENTRY_RUNTIME,
                target.ANIM_ENTRY_RUNTIME,
            ))),
            (97, 84, 87, 125),
        )
        self.assertEqual(target.ENTRY_CENTER_SIZE, 393)
        self.assertEqual(target.ENTRY_CENTER_CAPACITY, 427)
        self.assertEqual(target.ENTRY_CENTER_FREE_SIZE, 34)
        self.assertEqual(target.OFF_ANIM_ENTRY + len(target.ANIM_ENTRY_RUNTIME), 0x3D7B)

    def test_all_four_hook_destinations_follow_compacted_entries(self) -> None:
        self.assertEqual(target.CPU_AI_ENTRY, 0xBBE2)
        self.assertEqual(target.CPU_SETUP_ENTRY, 0xBC43)
        self.assertEqual(target.CPU_INIT_ENTRY, 0xBC97)
        self.assertEqual(target.CPU_ANIM_ENTRY, 0xBCEE)
        self.assertEqual(target.HOOK_SETUP_META_LOAD, bytes.fromhex("20 43 bc"))
        self.assertEqual(target.HOOK_INIT_WRITE_CALL, bytes.fromhex("20 97 bc"))
        self.assertEqual(target.HOOK_ANIM_UPDATE_CALL, bytes.fromhex("20 ee bc"))
        self.assertEqual(
            target.PRE_FINAL_ENEMY_HOOK_SETUP_META_LOAD,
            bytes.fromhex("20 3a bc"),
        )
        self.assertEqual(
            target.PRE_FINAL_ENEMY_HOOK_INIT_WRITE_CALL,
            bytes.fromhex("20 8e bc"),
        )
        self.assertEqual(
            target.PRE_FINAL_ENEMY_HOOK_ANIM_UPDATE_CALL,
            bytes.fromhex("20 e5 bc"),
        )

    def test_spark_trail_and_future_families_are_classified_in_all_entries(self) -> None:
        self.assertEqual(target.SPARK_TRAIL_FIRST_ID, 0xD8)
        self.assertEqual(target.SPARK_TRAIL_LAST_ID, 0xDF)
        self.assertEqual(target.FUTURE_ENEMY_FIRST_ID, 0xF8)
        self.assertEqual(target.FUTURE_ENEMY_LAST_ID, 0xFF)
        self.assertIn(bytes((0xC9, 0xE0)), target.AI_ENTRY_RUNTIME)
        self.assertIn(bytes((0xC9, 0xE0)), target.INIT_ENTRY_RUNTIME)
        self.assertIn(bytes((0xC9, 0xF8)), target.AI_ENTRY_RUNTIME)
        self.assertIn(bytes((0xC9, 0xF8)), target.SETUP_ENTRY_RUNTIME)

    def test_short_legacy_prefix_is_not_accepted(self) -> None:
        rom = bytearray(target.OFF_ANIM_ENTRY + len(target.ANIM_ENTRY_RUNTIME))
        legacy_prefix = bytes.fromhex("a0 01 b1 08 c9 84 f0 03 4c 89 87 4c 92 e0")
        rom[target.OFF_ANIM_ENTRY:target.OFF_ANIM_ENTRY + len(legacy_prefix)] = legacy_prefix
        before = bytes(rom)
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_blank_or(
                rom,
                target.OFF_ANIM_ENTRY,
                target.ANIM_ENTRY_RUNTIME,
                "animation entry",
            )
        self.assertEqual(bytes(rom), before)

    def test_current_and_checkpoint_entry_centers_require_full_match(self) -> None:
        for image in (
            target.CURRENT_ENTRY_CENTER_IMAGE,
            target.LEGACY_ENTRY_CENTER_IMAGE,
        ):
            with self.subTest(prefix=image[:4].hex()):
                rom = bytearray(target.ENTRY_CENTER_LIMIT)
                rom[target.OFF_AI_ENTRY:target.OFF_AI_ENTRY + len(image)] = image
                target._expect_entry_center(rom)
                rom[target.OFF_AI_ENTRY + len(image) - 1] ^= 0x01
                with self.assertRaises(target.NewEnemyRuntimeError):
                    target._expect_entry_center(rom)

    def test_pre_final_enemy_entry_image_matches_the_previous_source_exactly(self) -> None:
        previous = target.PRE_FINAL_ENEMY_ENTRY_CENTER_IMAGE
        self.assertEqual(len(previous), 376)
        self.assertEqual(
            hashlib.sha256(previous).hexdigest(),
            "a0ebe1bbe5d5d087c32cbbcf95a979d608db96a81afb544ca22335b0a4bd96bf",
        )
        rom = bytearray((0xEA,)) * target.ENTRY_CENTER_LIMIT
        rom[
            target.OFF_AI_ENTRY:
            target.OFF_AI_ENTRY + len(previous)
        ] = previous
        self.assertFalse(target._expect_entry_center(rom))

    def test_pre_final_enemy_entry_requires_the_new_nine_bytes_to_be_blank(self) -> None:
        previous = target.PRE_FINAL_ENEMY_ENTRY_CENTER_IMAGE
        rom = bytearray((0xEA,)) * target.ENTRY_CENTER_LIMIT
        rom[
            target.OFF_AI_ENTRY:
            target.OFF_AI_ENTRY + len(previous)
        ] = previous
        rom[target.OFF_AI_ENTRY + len(previous)] = 0x5A
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_entry_center(rom)

    def test_pre_spark_trail_spr2_entry_is_accepted_for_upgrade(self) -> None:
        previous = target.PRE_SPARK_TRAIL_SPR2_ENTRY_CENTER_IMAGE
        self.assertEqual(len(previous), 385)
        rom = bytearray((0xEA,)) * target.ENTRY_CENTER_LIMIT
        rom[
            target.OFF_AI_ENTRY:
            target.OFF_AI_ENTRY + len(previous)
        ] = previous
        self.assertFalse(target._expect_entry_center(rom))
        rom[target.OFF_AI_ENTRY + len(previous)] = 0x5A
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_entry_center(rom)

    def test_current_entry_does_not_claim_released_tail(self) -> None:
        rom = bytearray(target.ENTRY_CENTER_LIMIT)
        start = target.OFF_AI_ENTRY
        end = start + target.ENTRY_CENTER_SIZE
        rom[start:end] = target.CURRENT_ENTRY_CENTER_IMAGE
        rom[end:target.ENTRY_CENTER_LIMIT] = bytes((0x5A,)) * target.ENTRY_CENTER_FREE_SIZE
        self.assertFalse(target._expect_entry_center(rom))

    @staticmethod
    def _run_image(
        image: bytes,
        entry: int,
        enemy_id: int,
        ranges: tuple[tuple[int, int], ...],
    ) -> tuple[int, int, int, int, int, int]:
        memory = bytearray(0x10000)
        memory[target.CPU_AI_ENTRY:target.CPU_AI_ENTRY + len(image)] = image
        memory[0x08:0x0A] = bytes((0x00, 0x02))
        memory[0x0201] = enemy_id
        memory[0x05] = enemy_id
        memory[0x0E] = 7
        memory[0xD9DA] = 0x5A
        memory[0x0213] = 0xB7
        cpu = EntryCpu(memory, entry)
        cpu.a = (enemy_id - 0x14) & 0xFF if entry == target.CPU_AI_ENTRY else 0x55
        endpoint = cpu.run_entry(ranges)
        if endpoint == 0x8789:
            a = 0
            y = 0
        else:
            a = cpu.a
            y = cpu.y
        return endpoint, a, y, cpu.sp, cpu.memory[0x0213], cpu.steps

    def test_all_preexisting_ids_keep_the_same_entry_to_exit_behavior(self) -> None:
        legacy_entries = (0xBBE2, 0xBC32, 0xBC84, 0xBCD0)
        current_entries = (
            target.CPU_AI_ENTRY,
            target.CPU_SETUP_ENTRY,
            target.CPU_INIT_ENTRY,
            target.CPU_ANIM_ENTRY,
        )
        legacy_ranges = ((target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + 427),)
        current_ranges = (
            (target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + target.ENTRY_CENTER_SIZE),
        )
        legacy_steps = 0
        current_steps = 0
        for enemy_id in range(0xF8):
            legacy_id_steps = 0
            current_id_steps = 0
            for legacy_entry, current_entry in zip(legacy_entries, current_entries):
                with self.subTest(enemy_id=enemy_id, entry=current_entry):
                    old = self._run_image(
                        target.LEGACY_ENTRY_CENTER_IMAGE,
                        legacy_entry,
                        enemy_id,
                        legacy_ranges,
                    )
                    new = self._run_image(
                        target.CURRENT_ENTRY_CENTER_IMAGE,
                        current_entry,
                        enemy_id,
                        current_ranges,
                    )
                    if (
                        0xD8 <= enemy_id <= 0xDF
                        and current_entry == target.CPU_ANIM_ENTRY
                    ):
                        self.assertEqual(old[0], 0x8789)
                        self.assertEqual(old[4], 0xB7)
                        self.assertEqual(new[0], SENTINEL)
                        self.assertEqual(new[4], 0x7B)
                    else:
                        self.assertEqual(new[:5], old[:5])
                    legacy_steps += old[5]
                    current_steps += new[5]
                    legacy_id_steps += old[5]
                    current_id_steps += new[5]
            if enemy_id < 0xB0:
                self.assertLessEqual(
                    current_id_steps,
                    legacy_id_steps,
                    f"ID ${enemy_id:02X} dispatcher instruction count increased",
                )
        self.assertLess(current_steps, legacy_steps)

    def test_spark_trail_animation_forces_spr2_palette(self) -> None:
        ranges = (
            (target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + target.ENTRY_CENTER_SIZE),
        )
        for enemy_id in range(0xD8, 0xE0):
            with self.subTest(enemy_id=enemy_id):
                result = self._run_image(
                    target.CURRENT_ENTRY_CENTER_IMAGE,
                    target.CPU_ANIM_ENTRY,
                    enemy_id,
                    ranges,
                )
                self.assertEqual(result[0], SENTINEL)
                self.assertEqual(result[4], 0x7B)

    def test_spr2_hook_changes_only_spark_trail_entry_output(self) -> None:
        previous = target.PRE_SPARK_TRAIL_SPR2_ENTRY_CENTER_IMAGE
        current = target.CURRENT_ENTRY_CENTER_IMAGE
        previous_ranges = (
            (target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + len(previous)),
        )
        current_ranges = (
            (target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + len(current)),
        )
        entries = (
            target.CPU_AI_ENTRY,
            target.CPU_SETUP_ENTRY,
            target.CPU_INIT_ENTRY,
            target.CPU_ANIM_ENTRY,
        )
        for enemy_id in range(0x100):
            for entry in entries:
                with self.subTest(enemy_id=enemy_id, entry=entry):
                    old = self._run_image(
                        previous,
                        entry,
                        enemy_id,
                        previous_ranges,
                    )
                    new = self._run_image(
                        current,
                        entry,
                        enemy_id,
                        current_ranges,
                    )
                    is_trail_animation = (
                        0xD8 <= enemy_id <= 0xDF
                        and entry == target.CPU_ANIM_ENTRY
                    )
                    if is_trail_animation:
                        self.assertEqual(old[0], 0x8789)
                        self.assertEqual(old[4], 0xB7)
                        self.assertEqual(new[0], SENTINEL)
                        self.assertEqual(new[4], 0x7B)
                    else:
                        self.assertEqual(new[:5], old[:5])
                    if enemy_id < 0xB0:
                        self.assertEqual(new[5], old[5])

    def test_all_final_enemy_ids_reach_the_expected_four_entry_outputs(self) -> None:
        current_entries = (
            target.CPU_AI_ENTRY,
            target.CPU_SETUP_ENTRY,
            target.CPU_INIT_ENTRY,
            target.CPU_ANIM_ENTRY,
        )
        current_ranges = (
            (target.CPU_AI_ENTRY, target.CPU_AI_ENTRY + target.ENTRY_CENTER_SIZE),
        )
        for enemy_id in range(0xF8, 0x100):
            results = tuple(
                self._run_image(
                    target.CURRENT_ENTRY_CENTER_IMAGE,
                    entry,
                    enemy_id,
                    current_ranges,
                )
                for entry in current_entries
            )
            expected_ai = (
                target._spark24.CPU_STOCK_SPARK_SLOW
                if enemy_id < 0xFC
                else target._spark24.CPU_STOCK_SPARK_FAST
            )
            with self.subTest(enemy_id=enemy_id):
                self.assertEqual(results[0][0], expected_ai)
                self.assertEqual(results[1][0], SENTINEL)
                self.assertEqual(results[1][2], 0x14)
                self.assertEqual(results[2][0], SENTINEL)
                self.assertEqual(results[3][0], 0x8789)

    def test_legacy_ice_only_hook_is_not_accepted(self) -> None:
        rom = bytearray(target._ice.OFF_AI_DISPATCH_CALL + 3)
        rom[target._ice.OFF_AI_DISPATCH_CALL:target._ice.OFF_AI_DISPATCH_CALL + 3] = (
            target._ice.HOOK_AI_DISPATCH_CALL
        )
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_one(
                rom,
                target._ice.OFF_AI_DISPATCH_CALL,
                (target._ice.ORIG_AI_DISPATCH_CALL, target.HOOK_AI_DISPATCH_CALL),
                "AI hook",
            )

    def test_mirror_enemy_sets_detect_every_new_enemy_family(self) -> None:
        new_enemy_ids = (
            0x82, 0x84, 0x87, 0x9C, 0x9D, 0x9E,
            0xA0, 0xAF, 0xB0, 0xBB, 0xC0, 0xD7,
            0xD8, 0xDF, 0xE0, 0xF7, 0xF8, 0xFF,
        )
        for enemy_id in new_enemy_ids:
            with self.subTest(enemy_id=enemy_id):
                mirror = SimpleNamespace(enemy_codes=[enemy_id])
                level = SimpleNamespace(enemies=[], demon_mirrors=[mirror])
                self.assertTrue(target.levels_need_runtime([level]))

    def test_stock_mirror_enemy_set_does_not_require_new_enemy_runtime(self) -> None:
        mirror = SimpleNamespace(enemy_codes=[0x14, 0x80, 0x81, 0x83])
        level = SimpleNamespace(enemies=[], demon_mirrors=[mirror])
        self.assertFalse(target.levels_need_runtime([level]))

    def test_direct_ice_burn_still_requires_new_enemy_runtime(self) -> None:
        enemy = SimpleNamespace(type=ElementType.ENEMY, element_no=0x82)
        level = SimpleNamespace(enemies=[enemy], demon_mirrors=[])
        self.assertTrue(target.levels_need_runtime([level]))


if __name__ == "__main__":
    unittest.main()
