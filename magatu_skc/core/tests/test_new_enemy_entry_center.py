from __future__ import annotations

import unittest
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

    def test_optimized_entry_center_frees_51_bytes(self) -> None:
        self.assertEqual(
            tuple(map(len, (
                target.AI_ENTRY_RUNTIME,
                target.SETUP_ENTRY_RUNTIME,
                target.INIT_ENTRY_RUNTIME,
                target.ANIM_ENTRY_RUNTIME,
            ))),
            (88, 84, 87, 117),
        )
        self.assertEqual(target.ENTRY_CENTER_SIZE, 376)
        self.assertEqual(target.ENTRY_CENTER_CAPACITY, 427)
        self.assertEqual(target.ENTRY_CENTER_FREE_SIZE, 51)
        self.assertEqual(target.OFF_ANIM_ENTRY + len(target.ANIM_ENTRY_RUNTIME), 0x3D6A)

    def test_all_four_hook_destinations_follow_compacted_entries(self) -> None:
        self.assertEqual(target.CPU_AI_ENTRY, 0xBBE2)
        self.assertEqual(target.CPU_SETUP_ENTRY, 0xBC3A)
        self.assertEqual(target.CPU_INIT_ENTRY, 0xBC8E)
        self.assertEqual(target.CPU_ANIM_ENTRY, 0xBCE5)
        self.assertEqual(target.HOOK_SETUP_META_LOAD, bytes.fromhex("20 3a bc"))
        self.assertEqual(target.HOOK_INIT_WRITE_CALL, bytes.fromhex("20 8e bc"))
        self.assertEqual(target.HOOK_ANIM_UPDATE_CALL, bytes.fromhex("20 e5 bc"))

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

    def test_all_256_ids_have_the_same_entry_to_exit_behavior(self) -> None:
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
        for enemy_id in range(0x100):
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
                    self.assertEqual(new[:5], old[:5])
                    legacy_steps += old[5]
                    current_steps += new[5]
                    legacy_id_steps += old[5]
                    current_id_steps += new[5]
            self.assertLessEqual(
                current_id_steps,
                legacy_id_steps,
                f"ID ${enemy_id:02X} dispatcher instruction count increased",
            )
        self.assertLess(current_steps, legacy_steps)

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
            0xD8, 0xDF, 0xE0, 0xF7,
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
