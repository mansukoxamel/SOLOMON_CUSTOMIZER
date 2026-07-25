from __future__ import annotations

import unittest

from magatu_skc.core import panel_monster_stage_variant as panel
from magatu_skc.core import phantom_preset_runtime as phantom
from tools.verify_spark_trail_d8_isolated_v7 import C, Cpu, SENTINEL


class WrapperCpu(Cpu):
    def external_jsr(self, target: int) -> bool:
        if target == panel.CPU_SARAMANDOR_ABC_SPEED_INIT:
            self.a = 0x66
            self.x = 0x4D
            self.y = 0x77
            return True
        if target == phantom._OFFSETS["apply_speed"]:
            enemy_id = self.memory[0x0201]
            self.a = (enemy_id * 3 + 1) & 0xFF
            self.y = 0x05 if enemy_id & 0x02 else 0x08
            self.set_zn(self.a)
            return True
        return False

    def step(self) -> bool:
        op = self.memory[self.pc]
        if op == 0x88:  # DEY
            self.y = (self.y - 1) & 0xFF
            self.set_zn(self.y)
            self.pc = (self.pc + 1) & 0xFFFF
            self.steps += 1
            return True
        if op == 0x91:  # STA (zp),Y
            zp = self.memory[self.pc + 1]
            base = self.memory[zp] | (self.memory[(zp + 1) & 0xFF] << 8)
            self.memory[(base + self.y) & 0xFFFF] = self.a
            self.pc = (self.pc + 2) & 0xFFFF
            self.steps += 1
            return True
        return super().step()


class PhysicsWrapperSafeOptimizationTests(unittest.TestCase):
    @staticmethod
    def _run_speed_guard(enemy_id: int) -> tuple[int, bytes]:
        memory = bytearray(0x10000)
        guard = panel.FINAL_PARENT_SPEED_GUARD
        classifier = panel.FINAL_PANEL_TYPE_CLASSIFIER
        memory[
            panel.CPU_FINAL_PARENT_SPEED_GUARD:
            panel.CPU_FINAL_PARENT_SPEED_GUARD + len(guard)
        ] = guard
        memory[
            panel.CPU_FINAL_PANEL_TYPE_CLASSIFIER:
            panel.CPU_FINAL_PANEL_TYPE_CLASSIFIER + len(classifier)
        ] = classifier
        memory[0x08:0x0A] = bytes((0x00, 0x02))
        memory[0x0201] = enemy_id
        memory[0x0205:0x020A] = bytes((1, 2, 3, 4, 5))
        cpu = WrapperCpu(memory, panel.CPU_FINAL_PARENT_SPEED_GUARD)
        cpu.x = enemy_id
        return_address = (SENTINEL - 1) & 0xFFFF
        cpu.push(return_address >> 8)
        cpu.push(return_address)
        while cpu.step():
            pass
        return cpu.x, bytes(memory[0x0205:0x020A])

    @staticmethod
    def _run_prephysics(enemy_id: int, state: int, x_value: int) -> tuple[int, int]:
        memory = bytearray(0x10000)
        start = phantom.CPU_PREPHYSICS
        rel_start = start - phantom.CPU_RUNTIME
        rel_end = phantom._OFFSETS["velocity_table"] - phantom.CPU_RUNTIME
        blob = phantom.RUNTIME[rel_start:rel_end]
        memory[start:start + len(blob)] = blob
        memory[0x08:0x0A] = bytes((0x00, 0x02))
        memory[0x0201] = enemy_id
        memory[0x0203] = state
        cpu = WrapperCpu(memory, start)
        cpu.x = x_value
        cpu.y = 0x04
        while start <= cpu.pc < start + len(blob):
            cpu.step()
        return cpu.pc, cpu.y

    def test_all_ids_states_and_speed_paths_classify_correctly(self) -> None:
        compared = 0
        for speed_init in (False, True):
            for enemy_id in range(0x100):
                if speed_init:
                    x_value, fields = self._run_speed_guard(enemy_id)
                    expected_fields = (
                        bytes((0, 0, 3, 0, 0))
                        if 0xE0 <= enemy_id < 0xF8
                        else bytes((1, 2, 3, 4, 5))
                    )
                    self.assertEqual(fields, expected_fields)
                else:
                    x_value = enemy_id
                self.assertEqual(x_value, enemy_id)

                for state in range(0x100):
                    pc, y = self._run_prephysics(enemy_id, state, x_value)
                    active = (
                        phantom.FIRST_ID <= enemy_id <= phantom.LAST_ID
                        and state & 0xFC == 0x08
                    )
                    expected_pc = (
                        phantom.CPU_VERTICAL_PHYSICS
                        if active
                        else phantom.CPU_STOCK_PHYSICS
                    )
                    self.assertEqual(
                        pc,
                        expected_pc,
                        f"speed={int(speed_init)} ID=${enemy_id:02X} "
                        f"state=${state:02X}",
                    )
                    if active:
                        self.assertEqual(
                            y,
                            0x05 if enemy_id & 0x02 else 0x08,
                        )
                    compared += 1
        self.assertEqual(compared, 0x100 * 0x100 * 2)

    def test_shared_classifier_entry_and_parent_return_do_not_overlap(self) -> None:
        self.assertEqual(len(panel.FINAL_PARENT_SPEED_GUARD), 30)
        self.assertEqual(len(panel.FINAL_PANEL_TYPE_CLASSIFIER), 6)
        self.assertEqual(
            panel.CPU_FINAL_PANEL_TYPE_CLASSIFIER,
            panel._cpu(panel.OFF_FINAL_PANEL_TYPE_CLASSIFIER),
        )
        self.assertLess(
            panel.OFF_FINAL_PANEL_TYPE_CLASSIFIER
            + len(panel.FINAL_PANEL_TYPE_CLASSIFIER),
            panel.OFF_FINAL_PANEL_ANIM_DIR_HELPER,
        )


if __name__ == "__main__":
    unittest.main()
