import unittest

from magatu_skc.core import title_screen as target


class WideTitleRuntimeSafetyTests(unittest.TestCase):
    def test_reserved_spans_cover_every_direct_write_site(self):
        expected = {
            (target._wjp_cf(target._WT_BOOT_CPU), 87),
            (target._wjp_cf(target._WT_BOOT_CALL_A_CPU), 3),
            (target._wjp_cf(target._WT_BOOT_CALL_B_CPU), 3),
            (target._wjp_cf(target._WT_TITLE_START_CLEAR_CPU), 3),
            (target._wjp_cf(target._WT_IDLE_DEMO_TIMEOUT_CPU), 5),
            (target._wjp_cf(target._WT_IDLE_DEMO_CLEAR_STUB_CPU), 9),
            (target._wjp_cf(target._WT_ENDING_CALL_CPU), 3),
            (target._WT_DEC_FILE, target._WT_WIDE_END - target._WT_DEC_FILE),
            (
                target._WT_ENDING_DEC_FILE,
                target._WT_ENDING_RESERVED_END - target._WT_ENDING_DEC_FILE,
            ),
            (target._WT_SW_B1_OFF, 1),
        }
        expected.update(
            (target._wjp_cf(cpu), len(orig))
            for cpu, orig in target._WT_LEGACY_ATTR_WRITE_SITES
        )
        expected.update(
            (target._wjp_cf(cpu), 1)
            for cpu in (
                target._WT_PTRA_LO,
                target._WT_PTRA_HI,
                target._WT_PTRB_LO,
                target._WT_PTRB_HI,
            )
        )
        self.assertEqual(set(target.RESERVED_SPANS), expected)

    def test_cleanup_failure_does_not_partially_modify_rom(self):
        rom = bytearray(target._WT_ENDING_RESERVED_END)
        boot_off = target._wjp_cf(target._WT_BOOT_CPU)
        rom[boot_off:boot_off + len(target._WT_BOOT_SIG)] = target._WT_BOOT_SIG
        start_off = target._wjp_cf(target._WT_TITLE_START_CLEAR_CPU)
        rom[start_off:start_off + 3] = bytes.fromhex("2018CC")
        idle_off = target._wjp_cf(target._WT_IDLE_DEMO_TIMEOUT_CPU)
        rom[idle_off:idle_off + 5] = target._WT_IDLE_DEMO_TIMEOUT_ORIG
        stub_off = target._wjp_cf(target._WT_IDLE_DEMO_CLEAR_STUB_CPU)
        rom[stub_off:stub_off + len(target._WT_IDLE_DEMO_CLEAR_STUB)] = \
            b"\xEA" * len(target._WT_IDLE_DEMO_CLEAR_STUB)
        for cpu, orig in target._WT_LEGACY_ATTR_WRITE_SITES:
            off = target._wjp_cf(cpu)
            rom[off:off + len(orig)] = orig
        before = bytes(rom)

        with self.assertRaises(target.TitleScreenError):
            target.apply_wide_title_idle_demo_cleanup(rom)

        self.assertEqual(bytes(rom), before)

    def test_bootstrap_call_preflight_is_atomic(self):
        rom = bytearray(target._wjp_cf(target._WT_BOOT_CPU) + 28)
        old_off = target._wjp_cf(target._WT_OLD_BOOT_CPU)
        rom[old_off:old_off + len(target._WT_STOCK_CC4F_DECODER)] = \
            target._WT_STOCK_CC4F_DECODER
        call_a = target._wjp_cf(target._WT_BOOT_CALL_A_CPU)
        call_b = target._wjp_cf(target._WT_BOOT_CALL_B_CPU)
        rom[call_a:call_a + 3] = target._WT_BOOT_CALL_ORIG
        rom[call_b:call_b + 3] = b"\x00\x00\x00"
        before = bytes(rom)

        with self.assertRaises(target.TitleScreenError):
            target._wt_install_bootstrap_and_restore_stock(rom, bytes(28))

        self.assertEqual(bytes(rom), before)

    def test_legacy_03c0_bootstrap_is_not_current(self):
        rom = bytearray(target._wjp_cf(target._WT_OLD_BOOT_CPU) + 14)
        old_off = target._wjp_cf(target._WT_OLD_BOOT_CPU)
        rom[old_off:old_off + 14] = bytes.fromhex(
            "A20DBD5DCC9DC003CA10F74CC003"
        )
        self.assertFalse(target._wt_has_ram_bootstrap(rom))


if __name__ == "__main__":
    unittest.main()
