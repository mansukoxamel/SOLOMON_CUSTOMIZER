import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from magatu_skc.core import us_jp_normalizer
from magatu_skc.core import rom_diff
from magatu_skc.core.rom import Rom
from tools import start_stage_patch


def _mapper3_rom(region_byte: int) -> bytes:
    data = bytearray(16 + 0x8000 + 0x8000)
    data[:6] = b"NES\x1a\x02\x04"
    data[6] = 0x30
    data[0x0BF2] = int(region_byte) & 0xFF
    return bytes(data)


class UsInputRouteTest(unittest.TestCase):
    def setUp(self):
        self.us_source = _mapper3_rom(0x00)
        self.jp_normalized = _mapper3_rom(0xEA)

    def _normalizer_mocks(self):
        return (
            mock.patch.object(
                us_jp_normalizer,
                "is_supported_us_original",
                side_effect=lambda data: bytes(data) == self.us_source,
            ),
            mock.patch.object(
                us_jp_normalizer,
                "normalize_us_original",
                return_value=bytearray(self.jp_normalized),
            ),
            mock.patch.object(
                us_jp_normalizer,
                "is_normalized_us_data",
                side_effect=lambda data: bytes(data) == self.jp_normalized,
            ),
        )

    def test_direct_nes_editor_input_uses_us_normalizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "us.nes"
            path.write_bytes(self.us_source)
            p1, p2, p3 = self._normalizer_mocks()
            with p1, p2 as normalize, p3:
                rom = Rom.load(str(path))
                accepted = rom.is_supported_editor_input()

        normalize.assert_called_once_with(self.us_source)
        self.assertEqual(bytes(rom.data), self.jp_normalized)
        self.assertEqual(rom.source_data, self.us_source)
        self.assertEqual(rom.source_region, "US")
        self.assertEqual(rom.region, "JP")
        self.assertTrue(rom.was_us_normalized)
        self.assertTrue(accepted)

    def test_zip_migration_target_preflight_uses_us_normalizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "us.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("inside/us.nes", self.us_source)
            p1, p2, p3 = self._normalizer_mocks()
            with p1, p2 as normalize, p3:
                base_rom = Rom.load(str(path))
                accepted = base_rom.is_supported_editor_input()

        normalize.assert_called_once_with(self.us_source)
        self.assertTrue(accepted)
        self.assertEqual(base_rom.display_name, "us.nes")
        self.assertEqual(base_rom.region, "JP")

    def test_modified_us_mapper3_uses_raw_readonly_fallback(self):
        rom = Rom(self.us_source)
        self.assertFalse(rom.is_supported_editor_input())
        self.assertEqual(rom.readonly_input_reason(), "US mapper3 ROM")
        self.assertTrue(rom.is_supported_readonly_input())

    def test_rom_comparison_route_uses_normalizing_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.nes"
            right = Path(tmp) / "right.nes"
            left.write_bytes(self.us_source)
            right.write_bytes(self.us_source)
            p1, p2, p3 = self._normalizer_mocks()
            with p1, p2 as normalize, p3, mock.patch.object(
                rom_diff,
                "load_all_levels",
                return_value=[],
            ):
                result = rom_diff.compare_rom_stage_data(str(left), str(right))

        self.assertEqual(normalize.call_count, 2)
        self.assertEqual(result.left_region, "JP")
        self.assertEqual(result.right_region, "JP")

    def test_rom_comparison_constellation_signature(self):
        item = SimpleNamespace(element_no=0x42, position=(7, 9))
        self.assertEqual(
            rom_diff._constellation_signature(item),
            (0x42, 7, 9),
        )

    def test_start_stage_tool_normalizes_verified_us_before_patch(self):
        with mock.patch.object(
            us_jp_normalizer,
            "is_supported_us_original",
            return_value=True,
        ), mock.patch.object(
            us_jp_normalizer,
            "normalize_us_original",
            return_value=bytearray(self.jp_normalized),
        ) as normalize:
            working, source_crc, note = start_stage_patch.prepare_input_rom(
                self.us_source,
                force=False,
            )
            patched = start_stage_patch.patched_data_for_stage(working, 7)

        normalize.assert_called_once_with(self.us_source)
        self.assertEqual(working, self.jp_normalized)
        self.assertEqual(source_crc, start_stage_patch.crc32_hex(self.us_source))
        self.assertIn("normalized", note)
        self.assertEqual(patched[start_stage_patch.OFFSET_START_STAGE], 6)

    def test_start_stage_zip_output_defaults_to_nes(self):
        output = start_stage_patch.default_output_path(Path("source.zip"), 12)
        self.assertEqual(output, Path("source_stage12.nes"))


if __name__ == "__main__":
    unittest.main()
