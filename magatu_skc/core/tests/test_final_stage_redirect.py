from __future__ import annotations

from types import SimpleNamespace
import unittest

from magatu_skc.core import final_stage_redirect as target
from magatu_skc.core import stage_ext


def _levels(count=53):
    return [SimpleNamespace(stage_ext_flags=0) for _index in range(count)]


class FinalStageRedirectTests(unittest.TestCase):
    def test_stage_50_cannot_redirect_to_itself(self) -> None:
        levels = _levels()
        stage_ext.set_final_stage_redirect_enabled(
            levels[target.FINAL_STAGE_INDEX], True
        )
        with self.assertRaisesRegex(target.FinalStageRedirectError, "itself"):
            target.validate_levels(levels)

    def test_other_bonus_stages_may_redirect_to_stage_50(self) -> None:
        for stage_no in (48, 49, 51, 52, 53):
            levels = _levels()
            stage_ext.set_final_stage_redirect_enabled(levels[stage_no - 1], True)
            target.validate_levels(levels)

    def test_verify_requires_the_complete_runtime_cave(self) -> None:
        truncated = bytearray(target.OFF_CAVE)
        truncated[
            target.OFF_SIG_AFTER_CLEAR_RESET:
            target.OFF_SIG_AFTER_CLEAR_RESET + len(target.SIG_AFTER_CLEAR_RESET)
        ] = target.SIG_AFTER_CLEAR_RESET
        truncated[
            target.OFF_HOOK_CLEAR_RESET:
            target.OFF_HOOK_CLEAR_RESET + len(target.ORIG_HOOK_CLEAR_RESET)
        ] = target.ORIG_HOOK_CLEAR_RESET
        with self.assertRaisesRegex(target.FinalStageRedirectError, "too small"):
            target._verify(truncated)

    def test_complete_blank_cave_passes_verification(self) -> None:
        rom = bytearray(target.OFF_CAVE + len(target.CAVE))
        rom[
            target.OFF_SIG_AFTER_CLEAR_RESET:
            target.OFF_SIG_AFTER_CLEAR_RESET + len(target.SIG_AFTER_CLEAR_RESET)
        ] = target.SIG_AFTER_CLEAR_RESET
        rom[
            target.OFF_HOOK_CLEAR_RESET:
            target.OFF_HOOK_CLEAR_RESET + len(target.ORIG_HOOK_CLEAR_RESET)
        ] = target.ORIG_HOOK_CLEAR_RESET
        target._verify(rom)


if __name__ == "__main__":
    unittest.main()
