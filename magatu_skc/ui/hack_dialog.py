"""ゲーム挙動改造ダイアログ - 既知のROMアドレスを書き換え

参考: docs/rom_analysis.html, magatu_skc/core/hack_data.py
"""
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QMessageBox, QDialogButtonBox, QScrollArea, QGridLayout, QWidget,
    QLineEdit, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor

from .. import __version__
from ..core import hack_data
from ..core import walk_speed
from ..core import panel_monster_hack
from ..core import panel_monster_stage_variant
from ..core import panel_bullet_speed_fix
from ..core import demo_stage_hack
from ..core import dragon_hack
from ..core import shared_flame_start_wait
from ..core import demonhead_hack
from ..core import golem_hack
from ..core import golem_speed
from ..core import neul_ghost_speed
from ..core import spark_ball_speed
from ..core import spark_ball_variant
from ..core import phantom_preset_runtime
from ..core import ghostb0_runtime
from ..core import neul84_runtime
from ..core import gargoyle_hack
from ..core import gargoyle_variant
from ..core import saramandor_variant
from ..core import clearscreen_hack
from ..core import clear_message
from ..core import demo_input
from ..core import enemy_drop
from ..core import gap_fix_alternative as gap_fix
from ..core import room_flags
from ..core import warp_feather
from ..core import initial_magic
from ..core import initial_lives
from ..core import time_decrease_hack
from ..core import wall_color_hack
from ..core import stage_frame
from ..core import solomon_seal_stage
from ..core import stage_ext
from ..core import final_stage_redirect
from ..core import constants as c
from ..core.config import normalize_panel_variant_settings
from ..core.element import Wall
from ..core.i18n import t
from ..nes import palette as nes_palette


def _enemy_group_pixmap(tile_renderer, config, enemy_code: int) -> QPixmap:
    if tile_renderer is None or config is None:
        return QPixmap()
    from PyQt5.QtGui import QImage, QPainter
    from .element_picker import (
        ENEMY_PICKER_PALETTE_OVERRIDE,
        ENEMY_VISUAL_SOURCE,
        apply_enemy_picker_overlay,
    )
    visual_code = ENEMY_VISUAL_SOURCE.get(enemy_code, enemy_code)
    anim = config.enemy_map.get(visual_code, 0)
    try:
        sprite = tile_renderer.get_tile_image(
            anim,
            0,
            transparent=True,
            palette_no_override=ENEMY_PICKER_PALETTE_OVERRIDE.get(enemy_code),
        )
        sprite = apply_enemy_picker_overlay(sprite, enemy_code)
    except Exception:
        return QPixmap()
    bg = QImage(36, 36, QImage.Format_ARGB32)
    bg.fill(QColor(20, 20, 20))
    painter = QPainter(bg)
    scaled = sprite.scaled(36, 36, Qt.KeepAspectRatio, Qt.FastTransformation)
    painter.drawImage((36 - scaled.width()) // 2, (36 - scaled.height()) // 2, scaled)
    painter.end()
    return QPixmap.fromImage(bg)


def _pixmap_signature(pixmap: QPixmap):
    image = pixmap.toImage()
    bits = image.constBits()
    bits.setsize(image.byteCount())
    return (image.width(), image.height(), image.format(), bytes(bits))


def _setup_enemy_group(dialog, group, form, sort_key: int, enemy_codes=()):
    group.setProperty("enemy_sort_key", sort_key)
    if not enemy_codes:
        return
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 2)
    lay.setSpacing(4)
    seen_icons = set()
    for code in enemy_codes:
        pix = _enemy_group_pixmap(dialog.tile_renderer, dialog.config, code)
        if pix.isNull():
            continue
        signature = _pixmap_signature(pix)
        if signature in seen_icons:
            continue
        seen_icons.add(signature)
        lbl = QLabel()
        lbl.setFixedSize(36, 36)
        lbl.setPixmap(pix)
        lbl.setToolTip(f"0x{code:02X}")
        lay.addWidget(lbl)
    if lay.count() <= 0:
        return
    lay.addStretch(1)
    form.addRow(row)


DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO = 48


class HackDialog(QDialog):
    """ゲーム挙動改造ダイアログ"""

    def __init__(
        self,
        rom,
        parent=None,
        app_config=None,
        initial_level_no: int = 0,
        view_mode: str = "game",
        tile_renderer=None,
        config=None,
        levels=None,
    ):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self._view_mode = view_mode
        self.setWindowTitle(t(
            "hack_dialog.title.enemy" if view_mode == "enemy" else "hack_dialog.title.game",
            "敵" if view_mode == "enemy" else "ゲーム挙動改造",
        ))
        self.resize(940, 720)
        self.rom = rom
        self._app_config = app_config   # サイズ/位置 復元用 (None=保存しない)
        self._initial_level_no = initial_level_no
        self.tile_renderer = tile_renderer
        self.config = config
        self.levels = levels

        # 縦長で画面に入らないため: グループ群は 2列グリッド + 縦スクロール、
        # 補助ボタン/OK等は下に固定。呼び出し側(layout.addWidget/addLayout)は
        # 変更せず、収集してから組み立てる方式。
        class _Collector:
            def __init__(self):
                self.items = []
            def addWidget(self, w):
                self.items.append(("w", w))
            def addLayout(self, lo):
                self.items.append(("l", lo))
        layout = _Collector()

        if view_mode == "enemy":
            info_text = (
                t(
                    "hack_dialog.info.enemy_html",
                    "敵の挙動に関係する既知アドレスを書き換えます。<br>"
                    "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
                    "保存ボタンを押すまでは元に戻せます（再読込で復元可）。",
                )
            )
        else:
            info_text = (
                t(
                    "hack_dialog.info.game_html",
                    "ROMの既知アドレスを書き換えてゲーム挙動を変更します。<br>"
                    "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
                    "保存ボタンを押すまでは元に戻せます（再読込で復元可）。",
                )
            )
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        # ====== 開始ステージ ======
        stage_group = QGroupBox(t("hack_dialog.group.start_stage", "開始ステージ"))
        stage_group.setProperty("settings_category", "基本")
        sf = QFormLayout(stage_group)
        self.spin_stage = QSpinBox()
        self.spin_stage.setRange(1, 53)
        self.spin_stage.setValue((rom.data[0x1145] if 0x1145 < len(rom.data) else 0) + 1)
        sf.addRow("", self.spin_stage)
        layout.addWidget(stage_group)

        # ====== コンティニュー上限ステージ ======
        cont_group = QGroupBox(t("hack_dialog.group.continue_limit", "コンティニュー上限"))
        cont_group.setProperty("settings_category", "基本")
        cf = QFormLayout(cont_group)
        self._continue_offset = hack_data.get_continue_max_offset(rom.region)
        self.spin_continue = QSpinBox()
        self.spin_continue.setRange(1, 53)
        cur = rom.data[self._continue_offset] if self._continue_offset < len(rom.data) else 0x28
        self.spin_continue.setValue(cur + 1)
        cf.addRow("", self.spin_continue)
        layout.addWidget(cont_group)

        # ====== 最終面への移行 ======
        final_group = QGroupBox(t("hack_dialog.group.final_stage", "最終ステージ"))
        final_group.setProperty("settings_category", "基本")
        ff = QFormLayout(final_group)
        self.combo_final_stage_redirect = QComboBox()
        for stage_no in range(1, 54):
            if stage_no == final_stage_redirect.FINAL_STAGE_NO:
                continue
            label = t(
                "hack_dialog.final_stage.option",
                "{stage}面をクリアした後",
            ).format(stage=stage_no)
            data = stage_no - 1
            if stage_no == DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO:
                label += t("hack_dialog.original_suffix", "（原作）")
                data = -1
            self.combo_final_stage_redirect.addItem(label, data)
        current_final_redirect = self._current_final_stage_redirect_level_no()
        idx = self.combo_final_stage_redirect.findData(current_final_redirect)
        self.combo_final_stage_redirect.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_final_stage_redirect.setToolTip(
            t(
                "hack_dialog.final_stage.tooltip",
                "選んだ面をクリアした後、次の面を原作最終面に差し替えます。"
                "48面は原作相当なので追加フラグを書きません。",
            )
        )
        ff.addRow("", self.combo_final_stage_redirect)
        layout.addWidget(final_group)

        # ====== ワープ羽 ======
        wftr_group = QGroupBox(t("hack_dialog.group.warp_feather", "ワープの羽"))
        wftr_group.setProperty("settings_category", "基本")
        wftr = QFormLayout(wftr_group)
        self._warp_feather_ok = False
        self.spin_warp_feather = QSpinBox()
        self.spin_warp_feather.setRange(
            warp_feather.MIN_STEPS, warp_feather.MAX_STEPS)
        self.spin_warp_feather.setSuffix(t("hack_dialog.warp_feather.suffix", " 面分ワープ"))
        try:
            self.spin_warp_feather.setValue(
                warp_feather.current_steps(rom.data))
            self._warp_feather_ok = True
        except warp_feather.WarpFeatherError as e:
            self.spin_warp_feather.setValue(warp_feather.ORIGINAL_STEPS)
            self.spin_warp_feather.setEnabled(False)
            note = QLabel(t(
                "hack_dialog.validation_failed_disabled",
                "⚠ 検証失敗のため無効: {error}",
            ).format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wftr.addRow(note)
        wftr.addRow("", self.spin_warp_feather)
        wftr_hint = QLabel(
            t(
                "hack_dialog.warp_feather.hint",
                "原作は6面分。実コードは $C69F の #$05 と通常クリアの +1 で合計6。"
                "この値は $28 bit6 ルートのクリア進行数を変えます。",
            ))
        wftr_hint.setWordWrap(True)
        wftr_hint.setStyleSheet("color:#888; font-size:11px;")
        wftr.addRow(wftr_hint)
        layout.addWidget(wftr_group)

        # ====== ソロモンの封印 出現面 ======
        seal_group = QGroupBox(t("hack_dialog.group.solomon_seal_stage", "ソロモンの封印 出現面"))
        seal_group.setProperty("settings_category", "基本")
        seal_f = QFormLayout(seal_group)
        self._seal_stage_ok = solomon_seal_stage.supported(rom.region)
        self._seal_stage_loading = False
        self.combo_seal_stages = []
        try:
            current_seal_stages = solomon_seal_stage.current_stages(rom.data, rom.region)
        except solomon_seal_stage.SolomonSealStageError:
            current_seal_stages = solomon_seal_stage.defaults()
            self._seal_stage_ok = False
        seal_grid = QGridLayout()
        seal_grid.setHorizontalSpacing(8)
        seal_grid.setVerticalSpacing(4)
        for spec in solomon_seal_stage.SLOTS:
            combo = QComboBox()
            for stage_no in solomon_seal_stage.candidates(spec.slot, rom.data, rom.region):
                combo.addItem(t("hack_dialog.stage.option", "{stage}面").format(stage=stage_no), stage_no)
            wanted = current_seal_stages[spec.slot]
            idx = combo.findData(wanted)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.setEnabled(self._seal_stage_ok)
            combo.currentIndexChanged.connect(self._refresh_solomon_seal_stage_choices)
            self.combo_seal_stages.append(combo)
            row = spec.slot // 2
            col = (spec.slot % 2) * 2
            seal_grid.addWidget(QLabel(t(
                "hack_dialog.solomon_seal.slot.label",
                "封印{slot}:",
            ).format(slot=spec.slot + 1)), row, col)
            seal_grid.addWidget(combo, row, col + 1)
        seal_f.addRow(seal_grid)
        self._refresh_solomon_seal_stage_choices()
        seal_hint = QLabel(
            t(
                "hack_dialog.solomon_seal.hint",
                "1面につき封印1個まで。20面までに4個以上、44面までに6個以上、"
                "48面までに8個配置される必要があります。ROM保存できる候補だけ表示します。",
            )
        )
        seal_hint.setWordWrap(True)
        seal_hint.setStyleSheet("color:#888; font-size:11px;")
        seal_f.addRow(seal_hint)
        if not self._seal_stage_ok:
            note = QLabel(t(
                "hack_dialog.solomon_seal.unsupported",
                "⚠ JP ROM以外、または特殊処理テーブル検証失敗のため無効です。",
            ))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            seal_f.addRow(note)
        layout.addWidget(seal_group)

        # ====== 初期魔法 (共通) ======
        im_group = QGroupBox(t("hack_dialog.group.initial_magic", "初期魔法（共通）"))
        im_group.setProperty("settings_category", "プレイヤー")
        imf = QFormLayout(im_group)
        self._initial_magic_ok = False
        self.spin_initial_magic_max = QSpinBox()
        self.spin_initial_magic_max.setRange(
            initial_magic.MAX_COUNT_MIN, initial_magic.MAX_COUNT_MAX)
        self.spin_initial_magic_max.setToolTip(
            t(
                "hack_dialog.initial_magic.max.tooltip",
                "持てる巻物の最大数。原作は3。0にすると巻物を持てません。",
            ))
        self.edit_initial_magic = QLineEdit()
        self.edit_initial_magic.setMaxLength(initial_magic.MAX_PATTERN_CHARS)
        self.edit_initial_magic.setPlaceholderText(t("hack_dialog.initial_magic.placeholder", "例: FFF / SSS / FSFS"))
        self.edit_initial_magic.setToolTip(
            t(
                "hack_dialog.initial_magic.pattern.tooltip",
                "開始時に持っている巻物。F=通常ファイヤー、S=スーパー。"
                "最大8文字。空欄で原作(所持なし)。",
            ))
        try:
            max_count, pattern = initial_magic.current(rom.data)
            self.spin_initial_magic_max.setValue(max_count)
            self.edit_initial_magic.setText(pattern)
            self._initial_magic_ok = True
        except initial_magic.InitialMagicError as e:
            self.spin_initial_magic_max.setValue(initial_magic.ORIGINAL_MAX)
            self.spin_initial_magic_max.setEnabled(False)
            self.edit_initial_magic.setEnabled(False)
            note = QLabel(t(
                "hack_dialog.validation_failed_disabled",
                "⚠ 検証失敗のため無効: {error}",
            ).format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            imf.addRow(note)
        imf.addRow(t("hack_dialog.initial_magic.max.label", "最大数:"), self.spin_initial_magic_max)
        imf.addRow(t("hack_dialog.initial_magic.pattern.label", "初期所持:"), self.edit_initial_magic)
        imhint = QLabel(
            t(
                "hack_dialog.initial_magic.hint",
                "原作は最大3・初期所持なし。例: FFF=通常火球3つ、SSS=超火球3つ。"
                "原作値(最大3・空欄)に戻すと追加フックも復元します。",
            ))
        imhint.setWordWrap(True)
        imhint.setStyleSheet("color:#888; font-size:11px;")
        imf.addRow(imhint)
        layout.addWidget(im_group)

        # ====== 初期残数 ======
        lives_group = QGroupBox(t("hack_dialog.group.initial_lives", "初期残数"))
        lives_group.setProperty("settings_category", "プレイヤー")
        lives_f = QFormLayout(lives_group)
        self._initial_lives_ok = False
        self.spin_initial_lives = QSpinBox()
        self.spin_initial_lives.setRange(
            initial_lives.MIN_LIVES, initial_lives.MAX_LIVES)
        self.spin_initial_lives.setToolTip(
            t(
                "hack_dialog.initial_lives.tooltip",
                "開始時のダーナ残数。原作は3。$0452だけを書き換え、初期魔法の$042Bには影響させません。",
            ))
        try:
            self.spin_initial_lives.setValue(
                initial_lives.current(rom.data))
            self._initial_lives_ok = True
        except initial_lives.InitialLivesError as e:
            self.spin_initial_lives.setValue(initial_lives.ORIGINAL_LIVES)
            self.spin_initial_lives.setEnabled(False)
            note = QLabel(t(
                "hack_dialog.validation_failed_disabled",
                "⚠ 検証失敗のため無効: {error}",
            ).format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            lives_f.addRow(note)
        lives_f.addRow(t("hack_dialog.initial_lives.label", "開始時の残数:"), self.spin_initial_lives)
        lives_hint = QLabel(
            t(
                "hack_dialog.initial_lives.hint",
                "原作は3。単純な #$03 変更では巻物最大数にも漏れるため、専用フックで残数だけ変更します。",
            ))
        lives_hint.setWordWrap(True)
        lives_hint.setStyleSheet("color:#888; font-size:11px;")
        lives_f.addRow(lives_hint)
        layout.addWidget(lives_group)

        # ====== ステージ制限時間 ======
        time_group = QGroupBox(t("hack_dialog.group.time_decrease", "ステージ制限時間"))
        time_group.setProperty("settings_category", "敵以外")
        time_f = QFormLayout(time_group)
        self._time_rate_ok = False
        self.spin_time_fast = QSpinBox()
        self.spin_time_normal = QSpinBox()
        self.spin_time_slow = QSpinBox()
        self.lbl_time_fast_est = QLabel()
        self.lbl_time_normal_est = QLabel()
        self.lbl_time_slow_est = QLabel()
        for sp in (self.spin_time_fast, self.spin_time_normal, self.spin_time_slow):
            sp.setRange(0, 255)
            sp.setDisplayIntegerBase(16)
            sp.setPrefix("$")
            sp.setToolTip(t("hack_dialog.time_decrease.tooltip", "CPU $9942 のステージ制限時間テーブル値。値が大きいほど短くなります。"))
            sp.valueChanged.connect(self._update_time_rate_estimates)
        try:
            fast, normal, slow = time_decrease_hack.current_values(rom.data)
            self.spin_time_fast.setValue(fast)
            self.spin_time_normal.setValue(normal)
            self.spin_time_slow.setValue(slow)
            self._time_rate_ok = True
        except time_decrease_hack.TimeDecreaseHackError as e:
            for sp in (self.spin_time_fast, self.spin_time_normal, self.spin_time_slow):
                sp.setValue(0)
                sp.setEnabled(False)
            note = QLabel(t("hack_dialog.validation_failed_disabled", "⚠ 検証失敗のため無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            time_f.addRow(note)
        def time_row(sp, label):
            row = QHBoxLayout()
            row.addWidget(sp)
            row.addWidget(label)
            row.addStretch()
            return row

        time_f.addRow(t("hack_dialog.time_decrease.fast.label", "0=速い:"), time_row(self.spin_time_fast, self.lbl_time_fast_est))
        time_f.addRow(t("hack_dialog.time_decrease.normal.label", "1=普通:"), time_row(self.spin_time_normal, self.lbl_time_normal_est))
        time_f.addRow(t("hack_dialog.time_decrease.slow.label", "2=遅い:"), time_row(self.spin_time_slow, self.lbl_time_slow_est))
        time_hint = QLabel(t("hack_dialog.time_decrease.hint", "原作値は 速い=$2D / 普通=$22 / 遅い=$19。目安は開始LIFE 10000が0になるまでの時間です。"))
        time_hint.setWordWrap(True)
        time_hint.setStyleSheet("color:#888; font-size:11px;")
        time_f.addRow(time_hint)
        self._update_time_rate_estimates()
        layout.addWidget(time_group)

        # ====== ステージ壁色 ======
        wall_group = QGroupBox(t("hack_dialog.group.wall_color", "ステージ壁色 (1-48面)"))
        wall_group.setProperty("settings_category", "画面・演出")
        wall_f = QFormLayout(wall_group)
        self._wall_color_ok = False
        self.combo_wall_colors = []
        self._wall_color_table_ok = False
        try:
            cur_wall_colors = wall_color_hack.current_values(rom.data)
            wall_color_hack.special_values(rom.data)
            self._wall_color_ok = True
            self._wall_color_table_ok = True
        except wall_color_hack.WallColorHackError as e:
            cur_wall_colors = wall_color_hack.ORIGINAL_VALUES
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wall_f.addRow(note)
        grid_wall = QGridLayout()
        for i in range(wall_color_hack.EDIT_COUNT):
            combo = self._make_wall_color_combo(cur_wall_colors[i])
            combo.setToolTip(t("hack_dialog.wall_color.tooltip", "CPU $9122 の4面単位壁色テーブル値。NESパレット番号です。"))
            if not self._wall_color_ok:
                combo.setEnabled(False)
            self.combo_wall_colors.append(combo)
            row = i // 4
            col = (i % 4) * 2
            grid_wall.addWidget(QLabel(t("hack_dialog.wall_color.stage_range", "{range}面").format(range=wall_color_hack.stage_range_label(i))), row, col)
            grid_wall.addWidget(combo, row, col + 1)
        wall_f.addRow(grid_wall)
        wall_hint = QLabel(
            t(
                "hack_dialog.wall_color.hint",
                "4面ごとの壁の基調色です。ROM $9122 の先頭12バイトだけを変更します。"
                "49面以降の特殊値 $80/$80 は触りません。",
            ))
        wall_hint.setWordWrap(True)
        wall_hint.setStyleSheet("color:#888; font-size:11px;")
        wall_f.addRow(wall_hint)
        # Wall color editing is handled in PaletteDialog where the shared
        # 64-color picker is available.
        self._wall_color_ok = False
        self.combo_wall_colors = []

        # ====== ダーナ歩行速度 ======
        ws_group = QGroupBox(t("hack_dialog.group.walk_speed", "ダーナ歩行速度"))
        ws_group.setProperty("settings_category", "プレイヤー")
        wf = QFormLayout(ws_group)
        self.combo_walk = QComboBox()
        self._walk_ok = False
        try:
            cur_mult = walk_speed.current_multiplier(rom.data)
            self._walk_ok = True
        except walk_speed.WalkSpeedError as e:
            cur_mult = None
            self.combo_walk.setEnabled(False)
            note = QLabel(t("hack_dialog.validation_failed_disabled", "⚠ 検証失敗のため無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wf.addRow(note)

        sel_idx = 1  # デフォルト 1.0x
        for i, (m, _r, _l) in enumerate(walk_speed.PRESETS):
            label = f"{m:g}x" + (t("hack_dialog.original_suffix", "（原作）") if abs(m - 1.0) < 1e-6 else "")
            self.combo_walk.addItem(label, m)
            if cur_mult is not None and abs(m - cur_mult) < 0.01:
                sel_idx = i
        self.combo_walk.setCurrentIndex(sel_idx)
        wf.addRow(t("hack_dialog.walk_speed.label", "移動速度:"), self.combo_walk)
        hint = QLabel(t(
            "hack_dialog.walk_speed.hint",
            "原作 1.0x = 0.75 px/frame（4コマ歩行アニメと同期した精密値）。"
            "地上・空中の左右4方向すべてに適用。JP/US 共通。",
        ))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888; font-size:11px;")
        wf.addRow(hint)
        layout.addWidget(ws_group)

        # ====== パネルモンスター ======
        pm_group = QGroupBox(t("hack_dialog.group.panel_monster", "パネルモンスター"))
        pm_group.setProperty("settings_category", "敵・AI")
        pmf = QFormLayout(pm_group)
        _setup_enemy_group(self, pm_group, pmf, 10, (0x24, 0x52, 0x5A))
        self._pm_ok = False
        try:
            pm_region = panel_monster_hack.detect_region(rom.data)
            cur_frames = panel_monster_hack.current_cooldown_frames(rom.data)
            self._pm_ok = True
        except panel_monster_hack.PanelMonsterHackError as e:
            cur_frames = panel_monster_hack.ORIG_THRESHOLD
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            pmf.addRow(note)

        self._pm_bullet_speed_ok = False
        try:
            cur_bullet_speed_fix, cur_bullet_speed_value = panel_bullet_speed_fix.current_state(rom.data)
            self._pm_bullet_speed_ok = True
        except panel_bullet_speed_fix.PanelBulletSpeedFixError as e:
            cur_bullet_speed_fix = False
            cur_bullet_speed_value = panel_bullet_speed_fix.SLOW_VALUE
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            pmf.addRow(note)

        self.chk_pm_bullet_speed_fix = QCheckBox(t("hack_dialog.panel_monster.bullet_fix", "弾の左右速度バグ修正"))
        self.combo_pm_bullet_speed_fix = QComboBox()
        self.combo_pm_bullet_speed_fix.addItem(t("hack_dialog.panel_monster.bullet_speed.slow", "$30/$50（右下$30・左上$50）"), panel_bullet_speed_fix.SLOW_VALUE)
        self.combo_pm_bullet_speed_fix.addItem(t("hack_dialog.panel_monster.bullet_speed.fast", "$3F/$41（右下$3F・左上$41）"), panel_bullet_speed_fix.FAST_VALUE)
        self.chk_pm_bullet_speed_fix.toggled.connect(self.combo_pm_bullet_speed_fix.setEnabled)
        self.spin_pm = QSpinBox()
        self.spin_pm.setRange(
            panel_monster_hack.MIN_THRESHOLD,
            panel_monster_hack.MAX_THRESHOLD)
        self.spin_pm.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
        if self._pm_ok:
            self.spin_pm.setValue(cur_frames)
            self.chk_pm_bullet_speed_fix.setChecked(cur_bullet_speed_fix)
            self._set_combo_data(self.combo_pm_bullet_speed_fix, cur_bullet_speed_value)
            self.combo_pm_bullet_speed_fix.setEnabled(cur_bullet_speed_fix and self._pm_bullet_speed_ok)
            pmf.addRow(t("hack_dialog.panel_monster.cooldown.label", "クールダウン:"), self.spin_pm)
            pmf.addRow(self.chk_pm_bullet_speed_fix)
            pmf.addRow(t("hack_dialog.panel_monster.fixed_speed.label", "修正後の速度:"), self.combo_pm_bullet_speed_fix)
            phint = QLabel(t(
                "hack_dialog.panel_monster.hint",
                "判定: {region} / 原作 クールダウン192F。"
                "値を小さくすると連射化します。下限32F。"
                "短すぎる値は複数パネル面で17個のsub-slotを使い切りやすく、"
                "発射失敗や弾抜けの原因になります。"
                " 弾の左右速度バグ修正は共有Bullet速度テーブルを補正するため、バレットを使う敵すべてに影響します。",
            ).format(region=pm_region))
            phint.setWordWrap(True)
            phint.setStyleSheet("color:#888; font-size:11px;")
            pmf.addRow(phint)
        else:
            self.spin_pm.setEnabled(False)
        if not self._pm_bullet_speed_ok:
            self.chk_pm_bullet_speed_fix.setEnabled(False)
            self.combo_pm_bullet_speed_fix.setEnabled(False)

        pv_note = QLabel(
            t(
                "hack_dialog.panel_variant.note",
                "A/B/C/Dパネルモンスターはステージ別ではなく、全ステージ共通の固定値を使います。"
                "既存ステージデータ内の旧A/B/C個別値は読み込み互換のみで、保存時には使いません。",
            )
        )
        pv_note.setWordWrap(True)
        pv_note.setStyleSheet("color:#888; font-size:11px;")
        pmf.addRow(pv_note)
        self._panel_variant_controls = {}
        pv_settings = normalize_panel_variant_settings(
            (self._app_config or {}).get("panel_variant_settings")
        )
        for key, label in (("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            combo = QComboBox()
            for preset, preset_label in panel_monster_stage_variant.SPEED_PRESET_NAMES.items():
                combo.addItem(preset_label, preset)
            self._set_combo_data(combo, pv_settings[f"{key}_speed"])
            spin = QSpinBox()
            spin.setRange(1, 255)
            spin.setSuffix(" F")
            spin.setValue(pv_settings[f"{key}_interval"])
            row_layout.addWidget(QLabel(t("hack_dialog.panel_variant.speed", "速度")))
            row_layout.addWidget(combo, 1)
            row_layout.addWidget(QLabel(t("hack_dialog.panel_variant.interval", "間隔")))
            row_layout.addWidget(spin, 1)
            pmf.addRow(f"Panel {label}:", row)
            self._panel_variant_controls[key] = (combo, spin)
        layout.addWidget(pm_group)

        # ====== デモプレイのステージ ======
        ds_group = QGroupBox(t("hack_dialog.group.demo_stage", "デモプレイのステージ"))
        ds_group.setProperty("settings_category", "基本")
        dsf = QFormLayout(ds_group)
        self._ds_ok = False
        try:
            ds_region = demo_stage_hack.detect_region(rom.data)
            cur_stage = demo_stage_hack.current_stage(rom.data)
            self._ds_ok = True
        except demo_stage_hack.DemoStageHackError as e:
            cur_stage = None
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            dsf.addRow(note)

        self.spin_ds = QSpinBox()
        self.spin_ds.setRange(demo_stage_hack.MIN_STAGE,
                              demo_stage_hack.MAX_STAGE)
        self.spin_ds.setSuffix(t("hack_dialog.stage.suffix", " 面"))
        if self._ds_ok:
            self.spin_ds.setValue(cur_stage or 3)
            dsf.addRow(t("hack_dialog.demo_stage.label", "デモの面:"), self.spin_ds)
            dhint = QLabel(t(
                "hack_dialog.demo_stage.hint",
                "判定: {region} / 原作の既定は3面。"
                "3面以上のみ(内部のX連鎖制約)。録画入力は3面用なので"
                "別面ではDanaが録画通り動く=見た目で別面と分かる。"
                "正規プレイには影響なし。",
            ).format(region=ds_region))
            dhint.setWordWrap(True)
            dhint.setStyleSheet("color:#888; font-size:11px;")
            dsf.addRow(dhint)
        else:
            self.spin_ds.setEnabled(False)
        layout.addWidget(ds_group)

        # ====== ゴーレム ======
        golem_group = QGroupBox(t("hack_dialog.group.golem", "ゴブリン"))
        golem_group.setProperty("settings_category", "敵・AI")
        glf = QFormLayout(golem_group)
        _setup_enemy_group(self, golem_group, glf, 50, (0x70, 0x74))
        self._golem_ok = False
        try:
            golem_hack.detect_region(rom.data)
            self._golem_ok = True
        except golem_hack.GolemHackError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            glf.addRow(note)

        self.chk_golem_snappy = QCheckBox(
            t("hack_dialog.golem.snappy", "キビキビ動作（視認後復帰・方向転換の待ちを最小化）"))
        if self._golem_ok:
            self.chk_golem_snappy.setChecked(golem_hack.is_snappy(rom.data))
            glf.addRow(self.chk_golem_snappy)
        else:
            self.chk_golem_snappy.setEnabled(False)
        layout.addWidget(golem_group)

        # ====== 共通移動速度 ======
        shared_speed_group = QGroupBox(t("hack_dialog.group.shared_walk", "ゴブリン/ドラゴン/ガーゴイル移動速度"))
        shared_speed_group.setProperty("settings_category", "敵・AI")
        ssf = QFormLayout(shared_speed_group)
        _setup_enemy_group(self, shared_speed_group, ssf, 55, (0x70, 0x68, 0x78))
        self.combo_shared_walk = QComboBox()
        self._golem_spd_ok = False
        try:
            golem_speed.verify(rom.data)
            self._golem_spd_ok = True
        except golem_speed.GolemSpeedError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            ssf.addRow(note)
        for m in golem_speed.MULTIPLIERS:
            lab = f"{m:g}x" + (t("hack_dialog.original_suffix", "（原作）") if abs(m - 1.0) < 1e-6 else "")
            self.combo_shared_walk.addItem(lab, m)

        if self._golem_spd_ok:
            csw = golem_speed.current_shared_walk_mult(rom.data)
            for i in range(self.combo_shared_walk.count()):
                if abs(self.combo_shared_walk.itemData(i) - csw) < 0.01:
                    self.combo_shared_walk.setCurrentIndex(i)
                    break
            ssf.addRow(t("hack_dialog.shared_walk.label", "移動速度:"), self.combo_shared_walk)
            sshint = QLabel(t(
                "hack_dialog.shared_walk.hint",
                "Goblin/Dragon/Gargoyle の移動速度が同じ倍率で変わります。",
            ))
            sshint.setWordWrap(True)
            sshint.setStyleSheet("color:#888; font-size:11px;")
            ssf.addRow(sshint)
        else:
            self.combo_shared_walk.setEnabled(False)
        layout.addWidget(shared_speed_group)

        # ====== ゴースト＆ヌエル移動速度 ======
        ng_speed_group = QGroupBox(t("hack_dialog.group.neul_ghost_speed", "ゴースト＆ヌエル移動速度"))
        ng_speed_group.setProperty("settings_category", "敵・AI")
        ngf = QFormLayout(ng_speed_group)
        _setup_enemy_group(self, ng_speed_group, ngf, 30, (0x34, 0x30))
        self.combo_neul_ghost_speed = QComboBox()
        self._neul_ghost_spd_ok = False
        try:
            neul_ghost_speed.verify(rom.data)
            self._neul_ghost_spd_ok = True
        except neul_ghost_speed.NeulGhostSpeedError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            ngf.addRow(note)
        for m in neul_ghost_speed.MULTIPLIERS:
            lab = f"{m:g}x" + (t("hack_dialog.original_suffix", "（原作）") if abs(m - 1.0) < 1e-6 else "")
            self.combo_neul_ghost_speed.addItem(lab, m)
        if self._neul_ghost_spd_ok:
            cur_ng = neul_ghost_speed.current_multiplier(rom.data)
            for i in range(self.combo_neul_ghost_speed.count()):
                if abs(self.combo_neul_ghost_speed.itemData(i) - cur_ng) < 0.01:
                    self.combo_neul_ghost_speed.setCurrentIndex(i)
                    break
            ngf.addRow(t("hack_dialog.move_speed.label", "移動速度:"), self.combo_neul_ghost_speed)
            nghint = QLabel(
                t(
                    "hack_dialog.neul_ghost_speed.hint",
                    "GhostはX方向、NeulはY方向の速度を変更します。"
                    "SP1/SP2と通常/noslow版がまとめて同じ倍率で変わります。",
                ))
            nghint.setWordWrap(True)
            nghint.setStyleSheet("color:#888; font-size:11px;")
            ngf.addRow(nghint)
        else:
            self.combo_neul_ghost_speed.setEnabled(False)
        layout.addWidget(ng_speed_group)

        # ====== スパークボール移動速度 ======
        sb_speed_group = QGroupBox(t("hack_dialog.group.spark_ball_speed", "スパークボール移動速度"))
        sb_speed_group.setProperty("settings_category", "敵・AI")
        sbf = QFormLayout(sb_speed_group)
        _setup_enemy_group(self, sb_speed_group, sbf, 40, (0x28, 0x6A, 0x72))
        self.combo_spark_ball_speed = QComboBox()
        self._spark_ball_spd_ok = False
        try:
            spark_ball_speed.verify(rom.data)
            self._spark_ball_spd_ok = True
        except spark_ball_speed.SparkBallSpeedError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            sbf.addRow(note)
        for m in spark_ball_speed.MULTIPLIERS:
            lab = f"{m:g}x" + (t("hack_dialog.original_suffix", "（原作）") if abs(m - 1.0) < 1e-6 else "")
            self.combo_spark_ball_speed.addItem(lab, m)
        if self._spark_ball_spd_ok:
            cur_sb = spark_ball_speed.current_multiplier(rom.data)
            for i in range(self.combo_spark_ball_speed.count()):
                if abs(self.combo_spark_ball_speed.itemData(i) - cur_sb) < 0.01:
                    self.combo_spark_ball_speed.setCurrentIndex(i)
                    break
            sbf.addRow(t("hack_dialog.move_speed.label", "移動速度:"), self.combo_spark_ball_speed)
            sbhint = QLabel(
                t(
                    "hack_dialog.spark_ball_speed.hint",
                    "Spark Ball専用の $A9DF/$A9E7 移動差分テーブルを倍率変更します。"
                    "通常スパークボールと強化スパークボール(6A/6B/6E/6F)の両方に効きます。",
                ))
            sbhint.setWordWrap(True)
            sbhint.setStyleSheet("color:#888; font-size:11px;")
            sbf.addRow(sbhint)
        else:
            self.combo_spark_ball_speed.setEnabled(False)
        layout.addWidget(sb_speed_group)

        # ====== 強化スパークボール ======
        sb_variant_group = QGroupBox(t("hack_dialog.group.spark_ball_variant", "強化スパークボール"))
        sb_variant_group.setProperty("settings_category", "敵・AI")
        sbvf = QFormLayout(sb_variant_group)
        _setup_enemy_group(self, sb_variant_group, sbvf, 41, (0xC0, 0xC8, 0xD0))
        self._spark_ball_variant_ok = False
        self.chk_spark_pause_digits = []
        self.chk_spark_reverse_digits = []
        self.combo_spark_transparency = QComboBox()
        try:
            pause_digits = set(spark_ball_variant.current_pause_digits(rom.data))
            reverse_digits = set(spark_ball_variant.current_reverse_digits(rom.data))
            transparency_period = spark_ball_variant.current_transparency_period(rom.data)
            self._spark_ball_variant_ok = True
        except spark_ball_variant.SparkBallVariantError as e:
            pause_digits = set(spark_ball_variant.DEFAULT_PAUSE_DIGITS)
            reverse_digits = set(spark_ball_variant.DEFAULT_REVERSE_DIGITS)
            transparency_period = spark_ball_variant.DEFAULT_TRANSPARENCY_PERIOD
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            sbvf.addRow(note)

        digit_grid = QGridLayout()
        for digit in range(10):
            chk = QCheckBox(str(digit))
            chk.setChecked(digit in pause_digits)
            chk.stateChanged.connect(self._on_spark_pause_digit_changed)
            chk.setEnabled(self._spark_ball_variant_ok)
            self.chk_spark_pause_digits.append(chk)
            digit_grid.addWidget(chk, digit // 5, digit % 5)
        sbvf.addRow(t("hack_dialog.spark_ball_variant.pause_digits.label", "停止するLIFE百の位:"), digit_grid)

        reverse_grid = QGridLayout()
        for digit in range(10):
            chk = QCheckBox(str(digit))
            chk.setChecked(digit in reverse_digits)
            chk.stateChanged.connect(self._on_spark_reverse_digit_changed)
            chk.setEnabled(self._spark_ball_variant_ok)
            self.chk_spark_reverse_digits.append(chk)
            reverse_grid.addWidget(chk, digit // 5, digit % 5)
        sbvf.addRow(t("hack_dialog.spark_ball_variant.reverse_digits.label", "反転するLIFE百の位:"), reverse_grid)

        for value in spark_ball_variant.TRANSPARENCY_PERIODS:
            self.combo_spark_transparency.addItem(f"${value:02X}", value)
        self._set_combo_data(self.combo_spark_transparency, transparency_period)
        self.combo_spark_transparency.setEnabled(self._spark_ball_variant_ok)
        sbvf.addRow(t("hack_dialog.spark_ball_variant.transparency.label", "透明化周期:"), self.combo_spark_transparency)

        sbvhint = QLabel(
            t(
                "hack_dialog.spark_ball_variant.hint24",
                "停止型($C0-$C7)は停止ポイント、透明型($C8-$CF)は透明化周期、"
                "停止後反転型($D0-$D7)は反転ポイントを個別に設定します。",
            ))
        sbvhint.setWordWrap(True)
        sbvhint.setStyleSheet("color:#888; font-size:11px;")
        sbvf.addRow(sbvhint)
        layout.addWidget(sb_variant_group)

        phantom_group = QGroupBox(
            t("hack_dialog.group.phantom_preset", "Phantom Bullet Presets A-D")
        )
        phantom_group.setProperty("settings_category", "敵・AI")
        phantom_form = QFormLayout(phantom_group)
        _setup_enemy_group(self, phantom_group, phantom_form, 42, (0x20, 0x21, 0x22, 0x23))
        self._phantom_preset_controls = []
        self._phantom_preset_ok = False
        try:
            phantom_settings = phantom_preset_runtime.current_settings(rom.data)
            self._phantom_preset_ok = True
        except phantom_preset_runtime.PhantomPresetRuntimeError as e:
            phantom_settings = {
                "groups": phantom_preset_runtime.default_group_settings()
            }
            note = QLabel(
                t("hack_dialog.disabled", "⚠ 無効: {error}").format(
                    error=str(e).splitlines()[0]
                )
            )
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            phantom_form.addRow(note)
        for index, group_name in enumerate(phantom_preset_runtime.GROUP_NAMES):
            group_settings = phantom_settings["groups"][index]
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            speed = QSpinBox()
            speed.setRange(
                phantom_preset_runtime.MIN_SPEED_VALUE,
                phantom_preset_runtime.MAX_SPEED_VALUE,
            )
            speed.setDisplayIntegerBase(16)
            speed.setPrefix("$")
            speed.setValue(group_settings["speed_value"])

            amplitude = QComboBox()
            for value in phantom_preset_runtime.AMPLITUDE_VALUES:
                amplitude.addItem(f"{value}%", value)
            self._set_combo_data(amplitude, group_settings["amplitude_percent"])

            phase = QSpinBox()
            phase.setRange(0, 63)
            phase.setValue(group_settings["phase_offset"])

            row_layout.addWidget(QLabel(t(
                "hack_dialog.phantom_preset.speed.short", "Speed"
            )))
            row_layout.addWidget(speed)
            row_layout.addWidget(QLabel(t(
                "hack_dialog.phantom_preset.amplitude.short", "Amplitude"
            )))
            row_layout.addWidget(amplitude)
            row_layout.addWidget(QLabel(t(
                "hack_dialog.phantom_preset.phase.short", "Start"
            )))
            row_layout.addWidget(phase)
            row_layout.addStretch(1)

            first_id = phantom_preset_runtime.FIRST_ID + index * 4
            last_id = first_id + 3
            phantom_form.addRow(
                f"{group_name} (${first_id:02X}-${last_id:02X}):", row
            )
            if not self._phantom_preset_ok:
                speed.setEnabled(False)
                amplitude.setEnabled(False)
                phase.setEnabled(False)
            self._phantom_preset_controls.append((speed, amplitude, phase))
        layout.addWidget(phantom_group)

        neul_ab_group = QGroupBox(
            t("hack_dialog.group.neul_ab", "ヌエル強化版 A/B")
        )
        neul_ab_group.setProperty("settings_category", "敵・AI")
        neul_ab_form = QFormLayout(neul_ab_group)
        _setup_enemy_group(self, neul_ab_group, neul_ab_form, 32, neul84_runtime.NEW_ENEMY_IDS)
        self._neul_ab_controls = []
        self._neul_ab_ok = False
        try:
            neul_ab_settings = neul84_runtime.current_settings(rom.data)
            self._neul_ab_ok = True
        except neul84_runtime.Neul84RuntimeError as e:
            neul_ab_settings = {"groups": neul84_runtime.default_group_settings()}
            note = QLabel(
                t("hack_dialog.disabled", "⚠ 無効: {error}").format(
                    error=str(e).splitlines()[0]
                )
            )
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            neul_ab_form.addRow(note)
        for index, group_name in enumerate(neul84_runtime.GROUP_NAMES):
            group_settings = neul_ab_settings["groups"][index]
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            body_speed = QComboBox()
            body_speed.addItem(t("hack_dialog.neul_ab.body_speed.normal", "通常"), neul84_runtime.BODY_SPEED_NORMAL)
            body_speed.addItem(t("hack_dialog.neul_ab.body_speed.fast", "高速"), neul84_runtime.BODY_SPEED_FAST)
            self._set_combo_data(body_speed, group_settings["body_speed"])

            fire_interval = QSpinBox()
            fire_interval.setRange(neul84_runtime.MIN_FIRE_INTERVAL, neul84_runtime.MAX_FIRE_INTERVAL)
            fire_interval.setSuffix(t("hack_dialog.frames_suffix", " フレーム"))
            fire_interval.setValue(group_settings["fire_interval"])

            bullet_speed = QComboBox()
            for label_key, label, value in (
                ("stock", "原作", neul84_runtime.BULLET_SPEED_STOCK),
                ("quarter", "1/4", neul84_runtime.BULLET_SPEED_QUARTER),
                ("half", "1/2", neul84_runtime.BULLET_SPEED_HALF),
                ("double", "2倍", neul84_runtime.BULLET_SPEED_2X),
                ("triple", "3倍", neul84_runtime.BULLET_SPEED_3X),
            ):
                bullet_speed.addItem(t(f"hack_dialog.neul_ab.bullet_speed.{label_key}", label), value)
            self._set_combo_data(bullet_speed, group_settings["bullet_speed"])

            row_layout.addWidget(QLabel(t("hack_dialog.neul_ab.body_speed.short", "本体速度")))
            row_layout.addWidget(body_speed)
            row_layout.addWidget(QLabel(t("hack_dialog.neul_ab.fire_interval.short", "発射間隔")))
            row_layout.addWidget(fire_interval)
            row_layout.addWidget(QLabel(t("hack_dialog.neul_ab.bullet_speed.short", "弾速度")))
            row_layout.addWidget(bullet_speed)
            row_layout.addStretch(1)

            first_id = neul84_runtime.FIRST_ID + index * 2
            neul_ab_form.addRow(f"{group_name} (${first_id:02X}-${first_id + 1:02X}):", row)
            if not self._neul_ab_ok:
                body_speed.setEnabled(False)
                fire_interval.setEnabled(False)
                bullet_speed.setEnabled(False)
            self._neul_ab_controls.append((body_speed, fire_interval, bullet_speed))
        layout.addWidget(neul_ab_group)

        ghost_ab_group = QGroupBox(
            t("hack_dialog.group.ghost_ab", "ゴースト強化版 A-F")
        )
        ghost_ab_group.setProperty("settings_category", "敵・AI")
        ghost_ab_form = QFormLayout(ghost_ab_group)
        _setup_enemy_group(self, ghost_ab_group, ghost_ab_form, 34, ghostb0_runtime.NEW_ENEMY_IDS)
        self._ghost_ab_controls = []
        self._ghost_ab_ok = False
        try:
            ghost_ab_settings = ghostb0_runtime.current_settings(rom.data)
            self._ghost_ab_ok = True
        except ghostb0_runtime.GhostB0RuntimeError as e:
            ghost_ab_settings = {"groups": ghostb0_runtime.default_group_settings()}
            note = QLabel(
                t("hack_dialog.disabled", "⚠ 無効: {error}").format(
                    error=str(e).splitlines()[0]
                )
            )
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            ghost_ab_form.addRow(note)
        for index, group_name in enumerate(ghostb0_runtime.GROUP_NAMES):
            group_settings = ghost_ab_settings["groups"][index]
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            body_speed = QComboBox()
            body_speed.addItem(t("hack_dialog.ghost_ab.body_speed.normal", "通常"), ghostb0_runtime.BODY_SPEED_NORMAL)
            body_speed.addItem(t("hack_dialog.ghost_ab.body_speed.fast", "高速"), ghostb0_runtime.BODY_SPEED_FAST)
            self._set_combo_data(body_speed, group_settings["body_speed"])

            fire_interval = QSpinBox()
            fire_interval.setRange(ghostb0_runtime.MIN_FIRE_INTERVAL, ghostb0_runtime.MAX_FIRE_INTERVAL)
            fire_interval.setSuffix(t("hack_dialog.frames_suffix", " フレーム"))
            fire_interval.setValue(group_settings["fire_interval"])

            bullet_speed = QComboBox()
            for label_key, label, value in (
                ("stock", "原作", ghostb0_runtime.BULLET_SPEED_STOCK),
                ("quarter", "1/4", ghostb0_runtime.BULLET_SPEED_QUARTER),
                ("half", "1/2", ghostb0_runtime.BULLET_SPEED_HALF),
                ("double", "2倍", ghostb0_runtime.BULLET_SPEED_2X),
                ("triple", "3倍", ghostb0_runtime.BULLET_SPEED_3X),
            ):
                bullet_speed.addItem(t(f"hack_dialog.ghost_ab.bullet_speed.{label_key}", label), value)
            self._set_combo_data(bullet_speed, group_settings["bullet_speed"])

            fire_direction = QComboBox()
            for label_key, label, value in (
                ("backward", "後方", ghostb0_runtime.DIRECTION_BACKWARD),
                ("up", "上", ghostb0_runtime.DIRECTION_UP),
                ("down", "下", ghostb0_runtime.DIRECTION_DOWN),
            ):
                fire_direction.addItem(t(f"hack_dialog.ghost_ab.fire_direction.{label_key}", label), value)
            self._set_combo_data(fire_direction, group_settings["fire_direction"])

            row_layout.addWidget(QLabel(t("hack_dialog.ghost_ab.body_speed.short", "本体速度")))
            row_layout.addWidget(body_speed)
            row_layout.addWidget(QLabel(t("hack_dialog.ghost_ab.fire_interval.short", "発射間隔")))
            row_layout.addWidget(fire_interval)
            row_layout.addWidget(QLabel(t("hack_dialog.ghost_ab.bullet_speed.short", "弾速度")))
            row_layout.addWidget(bullet_speed)
            row_layout.addWidget(QLabel(t("hack_dialog.ghost_ab.fire_direction.short", "発射方向")))
            row_layout.addWidget(fire_direction)
            row_layout.addStretch(1)

            first_id = ghostb0_runtime.FIRST_ID + index * 2
            ghost_ab_form.addRow(f"{group_name} (${first_id:02X}-${first_id + 1:02X}):", row)
            if not self._ghost_ab_ok:
                body_speed.setEnabled(False)
                fire_interval.setEnabled(False)
                bullet_speed.setEnabled(False)
                fire_direction.setEnabled(False)
            self._ghost_ab_controls.append((body_speed, fire_interval, bullet_speed, fire_direction))
        layout.addWidget(ghost_ab_group)

        # ====== デーモンヘッド ======
        demonhead_group = QGroupBox(t("hack_dialog.group.demonhead", "デーモンヘッド"))
        demonhead_group.setProperty("settings_category", "敵・AI")
        dhf = QFormLayout(demonhead_group)
        _setup_enemy_group(self, demonhead_group, dhf, 20, (0x50, 0x54, 0x58))
        self._demonhead_ok = False
        try:
            demonhead_hack.current_wait(rom.data)
            self._demonhead_ok = True
        except demonhead_hack.DemonheadHackError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            dhf.addRow(note)
        self.chk_demonhead_snappy = QCheckBox(t("hack_dialog.demonhead.snappy", "キビキビ動作（方向転換の待ちを最小化）"))
        if self._demonhead_ok:
            self.chk_demonhead_snappy.setChecked(
                demonhead_hack.is_snappy(rom.data))
            dhf.addRow(self.chk_demonhead_snappy)
            dhhint = QLabel(t("hack_dialog.demonhead.hint", "Demonheadの方向転換待ち $0F を $01 にします。"))
            dhhint.setWordWrap(True)
            dhhint.setStyleSheet("color:#888; font-size:11px;")
            dhf.addRow(dhhint)
        else:
            self.chk_demonhead_snappy.setEnabled(False)
        layout.addWidget(demonhead_group)

        # ====== 強化サラマンダー ======
        saramandor_variant_group = QGroupBox(
            t("hack_dialog.group.saramandor_variant", "強化サラマンダー")
        )
        saramandor_variant_group.setProperty("settings_category", "敵・AI")
        svf = QFormLayout(saramandor_variant_group)
        _setup_enemy_group(self, saramandor_variant_group, svf, 59, (0x5E, 0x62, 0x66))
        self._saramandor_variant_controls = []
        self._saramandor_variant_ok = False
        try:
            initial_saramandor_settings = [
                {
                    "movement_speed": saramandor_variant.current_movement_speed(rom.data, index),
                    "flame_speed": saramandor_variant.current_speed_preset(rom.data, index),
                    "refire_wait": saramandor_variant.current_refire_wait(rom.data, index),
                    "post_fire_stop": saramandor_variant.current_post_fire_stop(rom.data, index),
                }
                for index in range(saramandor_variant.VARIANT_COUNT)
            ]
            self._saramandor_variant_ok = True
        except saramandor_variant.SaramandorVariantError as e:
            initial_saramandor_settings = [
                {
                    "movement_speed": saramandor_variant.DEFAULT_MOVEMENT_SPEEDS[index],
                    "flame_speed": saramandor_variant.DEFAULT_SPEED_PRESET,
                    "refire_wait": saramandor_variant.ORIGINAL_REFIRE_WAIT,
                    "post_fire_stop": saramandor_variant.ORIGINAL_POST_FIRE_STOP,
                }
                for index in range(saramandor_variant.VARIANT_COUNT)
            ]
            note = QLabel(
                t("hack_dialog.disabled", "⚠ 無効: {error}").format(
                    error=str(e).splitlines()[0]
                )
            )
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            svf.addRow(note)
        for index, group_name in enumerate(saramandor_variant.VARIANT_NAMES):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            movement = QComboBox()
            for preset in saramandor_variant.MOVEMENT_SPEED_PRESETS:
                movement.addItem(
                    t(f"hack_dialog.saramandor_variant.movement_speed.{preset}", f"速度{preset}"),
                    preset,
                )
            flame = QComboBox()
            for preset, key, label in (
                (saramandor_variant.SPEED_PRESET_NORMAL, "normal", "通常"),
                (saramandor_variant.SPEED_PRESET_HALF, "half", "1/2"),
                (saramandor_variant.SPEED_PRESET_QUARTER, "quarter", "1/4"),
            ):
                flame.addItem(t(f"hack_dialog.saramandor_variant.speed.{key}", label), preset)
            refire = QSpinBox()
            refire.setRange(saramandor_variant.MIN_REFIRE_WAIT, saramandor_variant.MAX_REFIRE_WAIT)
            stop = QSpinBox()
            stop.setRange(saramandor_variant.MIN_POST_FIRE_STOP, saramandor_variant.MAX_POST_FIRE_STOP)
            stop.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))

            values = initial_saramandor_settings[index]
            self._set_combo_data(movement, values["movement_speed"])
            self._set_combo_data(flame, values["flame_speed"])
            refire.setValue(values["refire_wait"])
            stop.setValue(values["post_fire_stop"])
            for control in (movement, flame, refire, stop):
                control.setEnabled(self._saramandor_variant_ok)

            row_layout.addWidget(QLabel(t("hack_dialog.saramandor_variant.movement.short", "移動速度")))
            row_layout.addWidget(movement)
            row_layout.addWidget(QLabel(t("hack_dialog.saramandor_variant.flame.short", "炎速度")))
            row_layout.addWidget(flame)
            row_layout.addWidget(QLabel(t("hack_dialog.saramandor_variant.refire.short", "最低歩行")))
            row_layout.addWidget(refire)
            row_layout.addWidget(QLabel(t("hack_dialog.saramandor_variant.stop.short", "発射後停止")))
            row_layout.addWidget(stop)
            row_layout.addStretch(1)
            first_id = 0x5E + index * 4
            svf.addRow(f"{group_name} (${first_id:02X}-${first_id + 1:02X}):", row)
            self._saramandor_variant_controls.append((movement, flame, refire, stop))
        svhint = QLabel(
            t(
                "hack_dialog.saramandor_variant.hint",
                "移動速度、炎速度、最低歩行時間、発射後停止時間をA/B/Cごとに設定します。"
                "最低歩行時間は1～255、原作32です。初回発射は原作32のまま、"
                "発射後停止を終えて歩き始めた後の2回目以降だけ設定値を適用します。"
                "ダーナが範囲外なら設定時間を過ぎても歩き続けます。"
                "発射後停止時間は炎が口元に出てから歩き出すまでの時間で、28～231、原作28です。",
            )
        )
        svhint.setWordWrap(True)
        svhint.setStyleSheet("color:#888; font-size:11px;")
        svf.addRow(svhint)
        layout.addWidget(saramandor_variant_group)

        # ====== ガーゴイル ======
        gargoyle_group = QGroupBox(t("hack_dialog.group.gargoyle", "ガーゴイル"))
        gargoyle_group.setProperty("settings_category", "敵・AI")
        gyf = QFormLayout(gargoyle_group)
        _setup_enemy_group(self, gargoyle_group, gyf, 70, (0x78, 0x7C))
        self._gargoyle_ok = False
        try:
            gargoyle_hack.detect_region(rom.data)
            self._gargoyle_ok = True
        except gargoyle_hack.GargoyleHackError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            gyf.addRow(note)

        self.chk_gargoyle_snappy = QCheckBox(
            t("hack_dialog.gargoyle.snappy", "キビキビ動作（検知後・発射直前・復帰待ちを最小化）"))
        self.spin_gargoyle_cooldown = QSpinBox()
        self.spin_gargoyle_cooldown.setRange(
            gargoyle_hack.COOLDOWN_MIN, gargoyle_hack.COOLDOWN_MAX)
        self.spin_gargoyle_cooldown.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
        self.spin_gargoyle_cooldown.setToolTip(
            t(
                "hack_dialog.gargoyle.cooldown.tooltip",
                "発射後に通常行動へ戻るまでの待ち。原作は80F。"
                "1F化は危険なので下限を設けています。",
            ))
        if self._gargoyle_ok:
            self.chk_gargoyle_snappy.setChecked(
                gargoyle_hack.is_snappy(rom.data))
            self.spin_gargoyle_cooldown.setValue(
                gargoyle_hack.current_cooldown(rom.data))
            gyf.addRow(self.chk_gargoyle_snappy)
            gyf.addRow(t("hack_dialog.gargoyle.cooldown.label", "発射後クールダウン:"), self.spin_gargoyle_cooldown)
            ghint = QLabel(t(
                "hack_dialog.gargoyle.hint",
                "ONでガーゴイル固有の待ち3箇所を$01にします。"
                "弾の連射強化とは別軸で併用できます。",
            ))
            ghint.setWordWrap(True)
            ghint.setStyleSheet("color:#888; font-size:11px;")
            gyf.addRow(ghint)
        else:
            self.chk_gargoyle_snappy.setEnabled(False)
            self.spin_gargoyle_cooldown.setEnabled(False)
        layout.addWidget(gargoyle_group)

        # ====== 強化ガーゴイル ======
        gargoyle_variant_group = QGroupBox(t("hack_dialog.group.gargoyle_variant", "強化ガーゴイル"))
        gargoyle_variant_group.setProperty("settings_category", "敵・AI")
        gvf = QFormLayout(gargoyle_variant_group)
        _setup_enemy_group(self, gargoyle_variant_group, gvf, 71, (0x7A, 0x7E))
        self._gargoyle_variant_ok = False
        gv_default_settings = {
            "movement_speed": gargoyle_variant.DEFAULT_MOVEMENT_SPEED,
            "speed_preset": gargoyle_variant.DEFAULT_SPEED_PRESET,
            "inter_shot_frames": gargoyle_variant.DEFAULT_INTER_SHOT_FRAMES,
            "cooldown_frames": gargoyle_variant.DEFAULT_COOLDOWN_FRAMES,
        }
        gv_settings = dict(gv_default_settings)
        gv_settings_b = dict(gv_default_settings)
        try:
            gv_settings = gargoyle_variant.current_settings(rom.data, "a")
            gv_settings_b = gargoyle_variant.current_settings(rom.data, "b")
            self._gargoyle_variant_ok = True
        except gargoyle_variant.GargoyleVariantError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            gvf.addRow(note)

        def make_gv_speed_combo(value: int) -> QComboBox:
            combo = QComboBox()
            for preset in gargoyle_variant.SELECTABLE_SPEED_PRESETS:
                label = gargoyle_variant.BULLET_SPEED_PRESETS[preset][0]
                if preset == 4:
                    label = t("hack_dialog.gargoyle_variant.speed.normal", "通常")
                combo.addItem(label, preset)
            self._set_combo_data(combo, value)
            return combo

        def make_gv_movement_combo(value: int) -> QComboBox:
            combo = QComboBox()
            for preset in gargoyle_variant.MOVEMENT_SPEED_PRESETS:
                combo.addItem(
                    t(f"hack_dialog.gargoyle_variant.movement_speed.{preset}", f"速度{preset}"),
                    preset,
                )
            self._set_combo_data(combo, value)
            return combo

        def make_gv_row(settings):
            movement = make_gv_movement_combo(settings["movement_speed"])
            combo = make_gv_speed_combo(settings["speed_preset"])
            inter_shot = QSpinBox()
            inter_shot.setRange(0, 255)
            inter_shot.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
            inter_shot.setValue(settings["inter_shot_frames"])
            cooldown = QSpinBox()
            cooldown.setRange(0, 255)
            cooldown.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
            cooldown.setValue(settings["cooldown_frames"])
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            row_layout.addWidget(QLabel(t("hack_dialog.gargoyle_variant.movement.label", "移動速度")))
            row_layout.addWidget(movement, 1)
            row_layout.addWidget(QLabel(t("hack_dialog.gargoyle_variant.speed.label", "弾速")))
            row_layout.addWidget(combo, 1)
            row_layout.addWidget(QLabel(t("hack_dialog.gargoyle_variant.inter_shot.label", "発射間隔")))
            row_layout.addWidget(inter_shot, 1)
            row_layout.addWidget(QLabel(t("hack_dialog.gargoyle_variant.cooldown.label", "クールダウン")))
            row_layout.addWidget(cooldown, 1)
            return movement, combo, inter_shot, cooldown, row

        (
            self.combo_gargoyle_variant_movement,
            self.combo_gargoyle_variant_speed,
            self.spin_gargoyle_variant_inter_shot,
            self.spin_gargoyle_variant_cooldown,
            row_gv_a,
        ) = make_gv_row(gv_settings)
        (
            self.combo_gargoyle_variant_b_movement,
            self.combo_gargoyle_variant_b_speed,
            self.spin_gargoyle_variant_b_inter_shot,
            self.spin_gargoyle_variant_b_cooldown,
            row_gv_b,
        ) = make_gv_row(gv_settings_b)
        gvf.addRow(t("hack_dialog.gargoyle_variant.row.a", "A (7A/7B):"), row_gv_a)
        gvf.addRow(t("hack_dialog.gargoyle_variant.row.b", "B (7E/7F):"), row_gv_b)

        if not self._gargoyle_variant_ok:
            self.combo_gargoyle_variant_movement.setEnabled(False)
            self.combo_gargoyle_variant_speed.setEnabled(False)
            self.spin_gargoyle_variant_inter_shot.setEnabled(False)
            self.spin_gargoyle_variant_cooldown.setEnabled(False)
            self.combo_gargoyle_variant_b_movement.setEnabled(False)
            self.combo_gargoyle_variant_b_speed.setEnabled(False)
            self.spin_gargoyle_variant_b_inter_shot.setEnabled(False)
            self.spin_gargoyle_variant_b_cooldown.setEnabled(False)

        gvhint = QLabel(
            t(
                "hack_dialog.gargoyle_variant.hint",
                "A/Bとも移動速度1・2を選べます。どちらもLIFE百の位が偶数なら2発、奇数なら3発撃ちます。"
                "移動速度・弾速・発射間隔・発射後クールダウンはA/B別に設定できます。",
            ))
        gvhint.setWordWrap(True)
        gvhint.setStyleSheet("color:#888; font-size:11px;")
        gvf.addRow(gvhint)
        layout.addWidget(gargoyle_variant_group)

        # ====== ドラゴン ======
        dragon_group = QGroupBox(t("hack_dialog.group.dragon", "ドラゴン"))
        dragon_group.setProperty("settings_category", "敵・AI")
        drf = QFormLayout(dragon_group)
        _setup_enemy_group(self, dragon_group, drf, 60, (0x68, 0x6C))
        self._dragon_ok = False
        try:
            dragon_hack.detect_region(rom.data)
            self._dragon_ok = True
        except dragon_hack.DragonHackError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            drf.addRow(note)

        self.chk_dragon_snappy = QCheckBox(
            t("hack_dialog.dragon.snappy", "キビキビ動作（方向転換の待ちを最小化）"))
        if self._dragon_ok:
            self.chk_dragon_snappy.setChecked(
                dragon_hack.is_snappy(rom.data))
            drf.addRow(self.chk_dragon_snappy)
            dhint = QLabel(t(
                "hack_dialog.dragon.hint",
                "ONでドラゴン固有の方向転換待ち1箇所を$01にします。"
                "サラマンダー共有の火吐き開始waitは変更しません。",
            ))
            dhint.setWordWrap(True)
            dhint.setStyleSheet("color:#888; font-size:11px;")
            drf.addRow(dhint)
        else:
            self.chk_dragon_snappy.setEnabled(False)
        layout.addWidget(dragon_group)

        # ====== ドラゴン/サラマンダー共通 火吐き開始待ち ======
        flame_group = QGroupBox(t("hack_dialog.group.shared_flame_wait", "ドラゴン/サラマンダー 火吐き開始待ち"))
        flame_group.setProperty("settings_category", "敵・AI")
        flame_f = QFormLayout(flame_group)
        _setup_enemy_group(self, flame_group, flame_f, 61, (0x68, 0x5C))
        self.spin_shared_flame_wait = QSpinBox()
        self.spin_shared_flame_wait.setRange(
            shared_flame_start_wait.MIN_WAIT,
            shared_flame_start_wait.MAX_WAIT,
        )
        self.spin_shared_flame_wait.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
        self._shared_flame_wait_ok = False
        try:
            self.spin_shared_flame_wait.setValue(
                shared_flame_start_wait.current_wait(rom.data))
            self._shared_flame_wait_ok = True
        except shared_flame_start_wait.SharedFlameStartWaitError as e:
            note = QLabel(t("hack_dialog.disabled", "⚠ 無効: {error}").format(error=str(e).splitlines()[0]))
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            flame_f.addRow(note)
        if self._shared_flame_wait_ok:
            flame_f.addRow(
                t("hack_dialog.shared_flame_wait.label", "待ち時間:"),
                self.spin_shared_flame_wait,
            )
            flame_hint = QLabel(
                t(
                    "hack_dialog.shared_flame_wait.hint",
                    "ドラゴン/サラマンダーが火炎を出し始めるまでの待ち時間です。"
                    "原作は24F。小さいほど早く吐き、255Fにすると大きく遅れます。",
                ))
            flame_hint.setWordWrap(True)
            flame_hint.setStyleSheet("color:#888; font-size:11px;")
            flame_f.addRow(flame_hint)
        else:
            self.spin_shared_flame_wait.setEnabled(False)
        layout.addWidget(flame_group)

        # クリア画面 (THANK YOU DANA) のキャラ差し替え
        cs_group = QGroupBox(t("hack_dialog.group.clear_screen_char", "クリア画面のキャラ (おめでとう画面の2体)"))
        cs_group.setProperty("settings_category", "画面・演出")
        csf = QFormLayout(cs_group)
        self.combo_clearscreen = QComboBox()
        for preset_id, preset in clearscreen_hack.PRESET_DEFS.items():
            self.combo_clearscreen.addItem(preset["label"], preset_id)
        try:
            cur = clearscreen_hack.current_preset_id(self.rom.data)
            if cur:
                self._set_combo_data(self.combo_clearscreen, cur)
            self._cs_ok = True
        except Exception:
            self._cs_ok = False
            self.combo_clearscreen.setEnabled(False)
        csf.addRow(t("hack_dialog.clear_screen_char.label", "表示キャラ:"), self.combo_clearscreen)
        cshint = QLabel(
            t(
                "hack_dialog.clear_screen_char.hint",
                "ステージクリア画面で左右に出る2体を差し替え。"
                "全プリセットは速度ゼロ=落下せず置物表示 (ROM解析確定)。",
            ))
        cshint.setWordWrap(True)
        cshint.setStyleSheet("color:#888; font-size:11px;")
        csf.addRow(cshint)
        layout.addWidget(cs_group)
        cs_group.setVisible(False)

        # ステージ外枠
        frame_group = QGroupBox(t("hack_dialog.group.stage_frame", "ステージ外枠"))
        frame_group.setProperty("settings_category", "画面・演出")
        frame_f = QVBoxLayout(frame_group)
        self.chk_stage_frame_white = QCheckBox(
            t("hack_dialog.stage_frame.checkbox", "ゲーム画面の外枠を白ブロック柄にする"))
        self.chk_stage_frame_white.setToolTip(
            t(
                "hack_dialog.stage_frame.tooltip",
                "ステージ外枠テーブルを外枠用白ブロック反復へ変更し、"
                "4つのCHRバンクすべてで対応CHRを白ブロック柄へ差し替えます。\n"
                "境界セル$F8や衝突判定、ステージデータ形式は変更しません。",
            ))
        self._stage_frame_ok = False
        base_region = (
            self.rom.base_region()
            if hasattr(self.rom, "base_region")
            else getattr(self.rom, "region", "")
        )
        state = stage_frame.current_state(self.rom.data)
        if (
                stage_frame.is_supported_region(base_region)
                and state in ("stock", "customizer_white")):
            self.chk_stage_frame_white.setChecked(state == "customizer_white")
            self._stage_frame_ok = True
        else:
            self.chk_stage_frame_white.setEnabled(False)
        frame_f.addWidget(self.chk_stage_frame_white)
        frame_hint = QLabel(
            t(
                "hack_dialog.stage_frame.hint",
                "ONにすると保存ROM/テストプレイROMの左右・下外枠が白ブロック柄になります。"
                "OFFに戻して適用すると外枠テーブルとハードコード済み原作CHRを復元します。",
            ))
        if state == "unknown":
            frame_hint.setText(
                t("hack_dialog.stage_frame.unknown", "外枠タイル列またはCHRが既知値と一致しないため、このROMでは変更を無効化しています。"))
        elif not stage_frame.is_supported_region(base_region):
            frame_hint.setText(t("hack_dialog.jp_base_only", "日本版ベースROM専用です。"))
        frame_hint.setWordWrap(True)
        frame_hint.setStyleSheet("color:#888; font-size:11px;")
        frame_f.addWidget(frame_hint)
        layout.addWidget(frame_group)

        # 原作バグ回避: 左右の新規入力後、横穴縁の位相拒否だけを無視 (グローバル)
        gf_group = QGroupBox(t("hack_dialog.group.gap_fix", "原作バグ回避"))
        gf_group.setProperty("settings_category", "保守・特殊")
        gff = QVBoxLayout(gf_group)
        self.chk_gapfix = QCheckBox(
            t("hack_dialog.gap_fix.checkbox", "横穴侵入を安定させる"))
        self.chk_gapfix.setToolTip(
            t(
                "hack_dialog.gap_fix.tooltip",
                "左/右の新規入力から設定フレーム中、上側角が壁・下側角が空間の時だけ"
                "上側の位相拒否bitを消します。\n"
                "上下とも壁の普通の壁では原作結果を変更しません。",
            ))
        try:
            self.chk_gapfix.setChecked(gap_fix.is_applied(self.rom.data))
            gap_frames = gap_fix.get_window_frames(self.rom.data)
            self._gapfix_ok = True
        except gap_fix.GapFixError:
            gap_frames = gap_fix.DEFAULT_WINDOW_FRAMES
            self._gapfix_ok = False
            self.chk_gapfix.setEnabled(False)
        gff.addWidget(self.chk_gapfix)
        gap_frames_row = QHBoxLayout()
        gap_frames_row.addWidget(QLabel(t("hack_dialog.gap_fix.frames", "押し直し後の受付フレーム数:")))
        self.spin_gapfix_frames = QSpinBox()
        self.spin_gapfix_frames.setRange(gap_fix.MIN_WINDOW_FRAMES, gap_fix.MAX_WINDOW_FRAMES)
        self.spin_gapfix_frames.setValue(gap_frames)
        self.spin_gapfix_frames.setEnabled(self._gapfix_ok)
        gap_frames_row.addWidget(self.spin_gapfix_frames)
        gap_frames_row.addStretch(1)
        gff.addLayout(gap_frames_row)
        gfhint = QLabel(
            t(
                "hack_dialog.gap_fix.hint",
                "横穴の少し上から、穴へ向かって入力し直すと入れます。押しっぱなしは原作どおりです。",
            ))
        gfhint.setWordWrap(True)
        gfhint.setStyleSheet("color:#888; font-size:11px;")
        gff.addWidget(gfhint)
        layout.addWidget(gf_group)

        # 暗闇テンポ (全体共通)。どの面を暗闇にするかは
        # 「レベル設定」パネルの『この画面を暗闇にする』(部屋別)。
        dk_group = QGroupBox(t("hack_dialog.group.dark_tempo", "暗闇テンポ (全体共通・必ず明から開始)"))
        dk_group.setProperty("settings_category", "画面・演出")
        dkf = QFormLayout(dk_group)
        self.spin_dark_light = QSpinBox()
        self.spin_dark_light.setRange(1, 200)
        self.spin_dark_light.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
        self.spin_dark_dark = QSpinBox()
        self.spin_dark_dark.setRange(1, 240)
        self.spin_dark_dark.setSuffix(t("hack_dialog.frame.suffix", " フレーム"))
        try:
            lf, df = room_flags.get_tempo(self.rom.data)
            self.spin_dark_light.setValue(lf)
            self.spin_dark_dark.setValue(df)
            self._dark_tempo_ok = True
        except room_flags.RoomFlagError:
            self._dark_tempo_ok = False
            self.spin_dark_light.setEnabled(False)
            self.spin_dark_dark.setEnabled(False)
        dkf.addRow(t("hack_dialog.dark_tempo.light.label", "明るい (見える):"), self.spin_dark_light)
        dkf.addRow(t("hack_dialog.dark_tempo.dark.label", "暗い (見えない):"), self.spin_dark_dark)
        dkhint = QLabel(
            t(
                "hack_dialog.dark_tempo.hint",
                "60フレーム≒1秒。既定: 明45/暗100。"
                "暗闇面を1つでも設定して保存すると有効。",
            ))
        dkhint.setWordWrap(True)
        dkhint.setStyleSheet("color:#888; font-size:11px;")
        dkf.addRow(dkhint)
        layout.addWidget(dk_group)

        related_group = QGroupBox(t("hack_dialog.group.related_edit", "関連編集"))
        related_group.setProperty("settings_category", "敵以外")
        related_layout = QVBoxLayout(related_group)

        self.btn_enemy_drop = QPushButton(t("hack_dialog.related.enemy_drop.button", "敵ドロップ編集"))
        self.btn_enemy_drop.setToolTip(
            t(
                "hack_dialog.related.enemy_drop.tooltip",
                "敵を炎で倒した時に出る効果(スコア/1UP/特殊等)と確率を"
                "グローバルに編集 ($C293)。通常アイテムIDではない点に注意",
            ))
        self.btn_enemy_drop.clicked.connect(self._on_show_enemy_drop)
        related_layout.addWidget(self.btn_enemy_drop)

        self.btn_demo_input = QPushButton(t("hack_dialog.related.demo_input.button", "デモ操作編集"))
        self.btn_demo_input.setToolTip(
            t(
                "hack_dialog.related.demo_input.tooltip",
                "タイトル放置で流れるデモの操作(34ステップ固定)を編集。"
                "各ステップ=入力を何フレーム続けるか。録画不要・原作方式手入力"
                "($CF9A/$CFBC、JP専用)",
            ))
        self.btn_demo_input.clicked.connect(self._on_show_demo_input)
        related_layout.addWidget(self.btn_demo_input)

        self.btn_clear_msg = QPushButton(t("hack_dialog.related.clear_message.button", "クリア画面メッセージ編集"))
        self.btn_clear_msg.setToolTip(
            t(
                "hack_dialog.related.clear_message.tooltip",
                "ステージクリア後の『おめでとう画面』3行を編集。"
                "英大文字+スペース、原作と同字数まで(JP専用・同字数置換)",
            ))
        self.btn_clear_msg.clicked.connect(self._on_show_clear_message)
        related_layout.addWidget(self.btn_clear_msg)
        self.btn_clear_msg.setVisible(False)

        layout.addWidget(related_group)

        # 補助ボタン
        helper_row = QHBoxLayout()
        self.btn_export_global = QPushButton(t("hack_dialog.export.button", "共通設定をエクスポート..."))
        self.btn_export_global.setToolTip(t(
            "hack_dialog.export.tooltip",
            "このダイアログの共通設定をJSONファイルに保存します",
        ))
        self.btn_export_global.clicked.connect(self._on_export_global_settings)
        helper_row.addWidget(self.btn_export_global)
        self.btn_import_global = QPushButton(t("hack_dialog.import.button", "共通設定をインポート..."))
        self.btn_import_global.setToolTip(t(
            "hack_dialog.import.tooltip",
            "JSONファイルから共通設定を読み込み、画面の値に反映します",
        ))
        self.btn_import_global.clicked.connect(self._on_import_global_settings)
        helper_row.addWidget(self.btn_import_global)
        helper_row.addSpacing(16)
        self.btn_revert = QPushButton(t("hack_dialog.revert.button", "オリジナル値に戻す"))
        self.btn_revert.setToolTip(t(
            "hack_dialog.revert.tooltip",
            "このダイアログで設定した項目を全てデフォルトに戻します",
        ))
        self.btn_revert.clicked.connect(self._on_revert)
        helper_row.addWidget(self.btn_revert)
        helper_row.addStretch()
        layout.addLayout(helper_row)

        # ボタン
        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply_changes)
        layout.addWidget(btnbox)

        # --- 実レイアウト組み立て (単一スクロール + 2列グリッド) ---
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(inner)
        rowi, col = 0, 0
        bottom = []          # helper_row / btnbox は下に固定
        top_info = None
        self._hidden_groups = []
        layout_items = layout.items
        if self._view_mode == "enemy":
            def _enemy_layout_key(item):
                kind, obj = item
                if kind == "w" and isinstance(obj, QLabel):
                    return (0, 0)
                if kind == "w" and isinstance(obj, QGroupBox):
                    return (1, int(obj.property("enemy_sort_key") or 9999))
                return (2, 0)
            layout_items = sorted(layout.items, key=_enemy_layout_key)
        for kind, obj in layout_items:
            if kind == "w" and isinstance(obj, QGroupBox):
                cat = obj.property("settings_category") or "敵以外"
                if self._view_mode == "enemy" and cat != "敵・AI":
                    self._hidden_groups.append(obj)
                    continue
                if self._view_mode != "enemy" and cat == "敵・AI":
                    self._hidden_groups.append(obj)
                    continue
                grid.addWidget(obj, rowi, col)
                col += 1
                if col >= 2:          # 2列
                    col = 0
                    rowi += 1
            elif kind == "w" and isinstance(obj, QLabel) and top_info is None:
                top_info = obj        # 冒頭の説明ラベル
            else:
                bottom.append((kind, obj))   # helper_row(QHBoxLayout)/btnbox
        grid.setRowStretch(rowi + 1, 1)
        if top_info is not None:
            outer.addWidget(top_info)
        outer.addWidget(scroll, 1)
        for kind, obj in bottom:
            if kind == "l":
                outer.addLayout(obj)
            else:
                outer.addWidget(obj)

        self._restore_geometry()

    def _combo_data(self, combo):
        return combo.currentData()

    def _selected_spark_pause_digits(self) -> list[int]:
        return [
            i for i, chk in enumerate(getattr(self, "chk_spark_pause_digits", []))
            if chk.isChecked()
        ]

    def _selected_spark_reverse_digits(self) -> list[int]:
        return [
            i for i, chk in enumerate(getattr(self, "chk_spark_reverse_digits", []))
            if chk.isChecked()
        ]

    def _panel_variant_settings_from_ui(self) -> dict:
        values = {}
        for key, (combo, spin) in getattr(self, "_panel_variant_controls", {}).items():
            values[f"{key}_speed"] = int(combo.currentData())
            values[f"{key}_interval"] = int(spin.value())
        return normalize_panel_variant_settings(values)

    def _gargoyle_variant_settings_from_ui(self, variant: str = "a") -> dict:
        if str(variant).lower() == "b":
            movement = self.combo_gargoyle_variant_b_movement
            combo = self.combo_gargoyle_variant_b_speed
            inter_shot = self.spin_gargoyle_variant_b_inter_shot
            cooldown = self.spin_gargoyle_variant_b_cooldown
        else:
            movement = self.combo_gargoyle_variant_movement
            combo = self.combo_gargoyle_variant_speed
            inter_shot = self.spin_gargoyle_variant_inter_shot
            cooldown = self.spin_gargoyle_variant_cooldown
        return {
            "movement_speed": int(movement.currentData()),
            "speed_preset": int(combo.currentData()),
            "inter_shot_frames": int(inter_shot.value()),
            "cooldown_frames": int(cooldown.value()),
        }

    def _saramandor_variant_settings_from_ui(self) -> list[dict[str, int]]:
        return [
            {
                "movement_speed": int(movement.currentData()),
                "flame_speed": int(flame.currentData()),
                "refire_wait": int(refire.value()),
                "post_fire_stop": int(stop.value()),
            }
            for movement, flame, refire, stop in self._saramandor_variant_controls
        ]

    def _phantom_group_settings_from_ui(self) -> tuple[dict[str, int], ...]:
        return tuple(
            {
                "speed_value": int(speed.value()),
                "amplitude_percent": int(amplitude.currentData()),
                "phase_offset": int(phase.value()),
            }
            for speed, amplitude, phase in self._phantom_preset_controls
        )

    @staticmethod
    def _phantom_global_key(group_index: int, field: str) -> str:
        if group_index == 0:
            return f"phantom_preset_{field}"
        group = phantom_preset_runtime.GROUP_NAMES[group_index].lower()
        return f"phantom_preset_{group}_{field}"

    def _phantom_global_settings_from_ui(self) -> dict:
        values = {}
        for index, group in enumerate(self._phantom_group_settings_from_ui()):
            values[self._phantom_global_key(index, "speed")] = group["speed_value"]
            values[self._phantom_global_key(index, "amplitude_percent")] = group["amplitude_percent"]
            values[self._phantom_global_key(index, "phase_offset")] = group["phase_offset"]
        return values

    def _ghost_ab_group_settings_from_ui(self) -> tuple[dict[str, int], ...]:
        return tuple({
            "body_speed": int(body_speed.currentData()),
            "fire_interval": int(fire_interval.value()),
            "bullet_speed": int(bullet_speed.currentData()),
            "fire_direction": int(fire_direction.currentData()),
        } for body_speed, fire_interval, bullet_speed, fire_direction in self._ghost_ab_controls)

    def _neul_ab_group_settings_from_ui(self) -> tuple[dict[str, int], ...]:
        return tuple({
            "body_speed": int(body_speed.currentData()),
            "fire_interval": int(fire_interval.value()),
            "bullet_speed": int(bullet_speed.currentData()),
        } for body_speed, fire_interval, bullet_speed in self._neul_ab_controls)

    def _neul_ab_global_settings_from_ui(self) -> dict:
        values = {}
        for index, group in enumerate(self._neul_ab_group_settings_from_ui()):
            name = neul84_runtime.GROUP_NAMES[index].lower()
            for field, value in group.items():
                values[f"neul_ab_{name}_{field}"] = value
        return values

    def _ghost_ab_global_settings_from_ui(self) -> dict:
        values = {}
        for index, group in enumerate(self._ghost_ab_group_settings_from_ui()):
            name = ghostb0_runtime.GROUP_NAMES[index].lower()
            for field, value in group.items():
                values[f"ghost_ab_{name}_{field}"] = value
        return values

    def _on_spark_pause_digit_changed(self, _state):
        selected = self._selected_spark_pause_digits()
        if len(selected) <= spark_ball_variant.PAUSE_DIGIT_COUNT:
            return
        sender = self.sender()
        if sender is not None:
            sender.blockSignals(True)
            sender.setChecked(False)
            sender.blockSignals(False)
        QMessageBox.information(
            self,
            t("hack_dialog.group.spark_ball_variant", "強化スパークボール"),
            t("hack_dialog.spark_ball_variant.max_digits", "停止するLIFE百の位は最大4個までです。"),
        )

    def _on_spark_reverse_digit_changed(self, _state):
        selected = self._selected_spark_reverse_digits()
        if len(selected) <= spark_ball_variant.PAUSE_DIGIT_COUNT:
            return
        sender = self.sender()
        if sender is not None:
            sender.blockSignals(True)
            sender.setChecked(False)
            sender.blockSignals(False)
        QMessageBox.information(
            self,
            t("hack_dialog.group.spark_ball_variant", "強化スパークボール"),
            t("hack_dialog.spark_ball_variant.max_reverse_digits", "反転するLIFE百の位は最大4個までです。"),
        )

    def _mark_parent_dirty(self, log_message: str):
        parent = self.parent()
        if parent is None:
            return
        set_dirty = getattr(parent, "_set_dirty", None)
        if callable(set_dirty):
            set_dirty(True)
        log = getattr(parent, "_log", None)
        if callable(log):
            log(log_message)

    def _on_show_enemy_drop(self):
        from .enemy_drop_dialog import EnemyDropDialog, format_enemy_drop_error
        from ..core import enemy_drop as _ed
        o, n = _ed.OFF_C293, _ed.LEN_C293
        before = bytes(self.rom.data[o:o + n])
        try:
            dlg = EnemyDropDialog(
                self.rom.data,
                parent=self,
                tile_renderer=self.tile_renderer,
                config=self.config,
                app_config=self._app_config,
            )
        except _ed.EnemyDropError as e:
            from ..core.i18n import t
            QMessageBox.critical(
                self,
                t("enemy_drop.open_failed", "敵ドロップ編集不可"),
                format_enemy_drop_error(e),
            )
            return
        dlg.exec_()
        if bytes(self.rom.data[o:o + n]) != before:
            self._mark_parent_dirty(t("hack_dialog.log.enemy_drop_changed", "敵ドロップ効果表 $C293 書換"))

    def _on_show_demo_input(self):
        from .demo_input_dialog import DemoInputDialog, format_demo_input_error
        from ..core import demo_input as _di
        o0, o1 = _di.OFF_WAIT, _di.OFF_JOY + _di.STEPS
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = DemoInputDialog(
                self.rom.data,
                parent=self,
                app_config=self._app_config,
            )
        except _di.DemoInputError as e:
            from ..core.i18n import t
            QMessageBox.critical(
                self,
                t("demo_input.open_failed", "デモ操作編集不可"),
                format_demo_input_error(e),
            )
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._mark_parent_dirty(t("hack_dialog.log.demo_input_changed", "デモ操作データ ($CF9A/$CFBC) 書換"))

    def _on_show_clear_message(self):
        from .clear_message_dialog import ClearMessageDialog, format_clear_message_error
        from ..core import clear_message as _cm
        o0 = _cm.MESSAGES[0]["off"]
        last = _cm.MESSAGES[-1]
        o1 = last["off"] + 3 + last["count"] + 1
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = ClearMessageDialog(
                self.rom.data,
                parent=self,
                app_config=self._app_config,
            )
        except _cm.ClearMessageError as e:
            from ..core.i18n import t
            QMessageBox.critical(
                self,
                t("clear_message.open_failed", "クリア画面メッセージ編集不可"),
                format_clear_message_error(e),
            )
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._mark_parent_dirty(t("hack_dialog.log.clear_message_changed", "クリア画面メッセージ ($94DB/$94ED/$9507) 書換"))

    def _on_show_special_process(self):
        from .special_process_dialog import SpecialProcessDialog
        dlg = SpecialProcessDialog(
            self.rom,
            initial_level_no=self._initial_level_no,
            parent=self,
            app_config=self._app_config,
        )
        dlg.exec_()

    def _make_nes_color_icon(self, value: int) -> QIcon:
        rgb = nes_palette.get_nes_color(int(value) & 0x3F)
        pm = QPixmap(24, 16)
        pm.fill(QColor(*rgb))
        return QIcon(pm)

    def _make_wall_color_combo(self, value: int) -> QComboBox:
        combo = QComboBox()
        for i in range(0x40):
            combo.addItem(self._make_nes_color_icon(i), f"${i:02X}", i)
        self._set_combo_data(combo, int(value) & 0x3F)
        return combo

    def _format_time_rate_estimate(self, value: int) -> str:
        seconds = time_decrease_hack.estimate_total_seconds(value)
        if seconds is None:
            return t("hack_dialog.time_estimate.never", "目安: 減らない")
        total = int(round(seconds))
        minutes, sec = divmod(total, 60)
        if minutes:
            return t("hack_dialog.time_estimate.minutes", "目安: 約{minutes}分{seconds:02d}秒").format(minutes=minutes, seconds=sec)
        return t("hack_dialog.time_estimate.seconds", "目安: 約{seconds}秒").format(seconds=sec)

    def _update_time_rate_estimates(self):
        if hasattr(self, "lbl_time_fast_est"):
            self.lbl_time_fast_est.setText(
                self._format_time_rate_estimate(self.spin_time_fast.value()))
            self.lbl_time_normal_est.setText(
                self._format_time_rate_estimate(self.spin_time_normal.value()))
            self.lbl_time_slow_est.setText(
                self._format_time_rate_estimate(self.spin_time_slow.value()))

    def _set_combo_data(self, combo, value) -> bool:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return True
            try:
                if float(combo.itemData(i)) == float(value):
                    combo.setCurrentIndex(i)
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _hex_bytes(data) -> str:
        return " ".join(f"{int(b) & 0xFF:02X}" for b in data)

    @staticmethod
    def _parse_hex_bytes(value: str, expected_len: int, key: str) -> bytes:
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a hex string.")
        compact = "".join(value.split())
        if len(compact) != expected_len * 2:
            raise ValueError(f"{key} must contain {expected_len} bytes.")
        try:
            return bytes.fromhex(compact)
        except ValueError as e:
            raise ValueError(f"{key} contains invalid hex.") from e

    def _bonus_stage_offsets(self) -> tuple[int, int]:
        from ..core.constants import ROM_OFFSETS

        region = self.rom.base_region() if self.rom is not None else "JP"
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        return (
            offsets.get("bonus_pos", 0x1955),
            offsets.get("bonus_items", 0x1975),
        )

    def _sync_parent_bonus_stage(self):
        parent = self.parent()
        if parent is None:
            return
        load_bonus = getattr(parent, "_load_bonus_stage_table", None)
        if callable(load_bonus):
            load_bonus(self.rom)
        refresh = getattr(parent, "_refresh_view", None)
        if callable(refresh):
            refresh()
        refresh_thumb = getattr(parent, "_refresh_thumbnail", None)
        current_level_no = getattr(parent, "current_level_no", None)
        if callable(refresh_thumb) and current_level_no == 50:
            refresh_thumb(50)

    def _sync_parent_wall_color(self):
        parent = self.parent()
        if parent is None:
            return
        applied = getattr(parent, "_on_hack_dialog_applied", None)
        if callable(applied):
            applied()

    def _sync_parent_solomon_seal_stages(self, stages: list):
        cfg = self._level_meta_config()
        if cfg is not None:
            for mi in getattr(cfg, "level_meta_items", []) or []:
                no = int(getattr(mi, "no", -1))
                desc = str(getattr(mi, "description", "")).lower()
                if 0 <= no < len(stages) and "solomon" in desc and "seal" in desc:
                    mi.level_no = int(stages[no]) - 1
        parent = self.parent()
        if parent is None:
            return
        refresh = getattr(parent, "_refresh_view", None)
        if callable(refresh):
            refresh()
        refresh_thumb = getattr(parent, "_refresh_thumbnail", None)
        current_level_no = getattr(parent, "current_level_no", None)
        if callable(refresh_thumb) and current_level_no is not None:
            refresh_thumb(current_level_no)

    def _solomon_seal_is_clear_air(self, level, level_no: int, tile: tuple, seal_no: int) -> bool:
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return False
        if x >= c.LEVEL_W - 1:
            return False
        if level.tiles[y][x] != Wall.NONE:
            return False
        runtime_marker_names = (
            "breakable_white_cells",
            "invisible_breakable_cells",
            "invisible_solid_cells",
            "passable_white_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        )
        for name in runtime_marker_names:
            if tile in getattr(level, name, set()):
                return False
        if tuple(getattr(level, "fixed_start_pos", (-1, -1))) == tile:
            return False
        if not level.is_key_removed() and tuple(getattr(level, "fixed_key_pos", (-1, -1))) == tile:
            return False
        if not level.is_door_removed() and tuple(getattr(level, "fixed_door_pos", (-1, -1))) == tile:
            return False
        if level.get_item_index(tile) >= 0 or level.get_enemy_index(tile) >= 0:
            return False
        for mirror in getattr(level, "demon_mirrors", []) or []:
            if tuple(getattr(mirror, "position", (-1, -1))) == tile:
                return False
        cfg = self._level_meta_config()
        if cfg is not None:
            for mi in getattr(cfg, "level_meta_items", []) or []:
                no = int(getattr(mi, "no", -1))
                if no == int(seal_no):
                    continue
                if int(getattr(mi, "level_no", -1)) != int(level_no):
                    continue
                if tuple(getattr(mi, "position", (-1, -1))) == tile:
                    return False
        return True

    def _nearest_solomon_seal_clear_air(self, level, level_no: int, origin: tuple, seal_no: int):
        ox, oy = origin
        candidates = []
        for y in range(c.LEVEL_H):
            for x in range(c.LEVEL_W):
                tile = (x, y)
                if not self._solomon_seal_is_clear_air(level, level_no, tile, seal_no):
                    continue
                dist = abs(x - ox) + abs(y - oy)
                candidates.append((dist, abs(y - oy), abs(x - ox), y, x, tile))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][-1]

    def _plan_solomon_seal_stage_relocations(self, stages: list) -> list:
        parent = self.parent()
        levels = getattr(parent, "levels", None)
        cfg = self._level_meta_config()
        if cfg is None or not levels:
            return []
        from ..core.element import position_from_byte

        relocations = []
        for mi in getattr(cfg, "level_meta_items", []) or []:
            no = int(getattr(mi, "no", -1))
            desc = str(getattr(mi, "description", "")).lower()
            if not (0 <= no < len(stages) and "solomon" in desc and "seal" in desc):
                continue
            old_level_no = int(getattr(mi, "level_no", -1))
            new_level_no = int(stages[no]) - 1
            if old_level_no == new_level_no:
                continue
            if not (0 <= new_level_no < len(levels)):
                continue
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if self.rom is not None and 0 <= rom_offset < len(self.rom.data):
                old_pos = position_from_byte(self.rom.data[rom_offset])
            else:
                old_pos = tuple(getattr(mi, "position", (0, 0)))
            level = levels[new_level_no]
            if self._solomon_seal_is_clear_air(level, new_level_no, old_pos, no):
                new_pos = old_pos
            else:
                new_pos = self._nearest_solomon_seal_clear_air(level, new_level_no, old_pos, no)
            if new_pos is None:
                raise solomon_seal_stage.SolomonSealStageError(
                    t(
                        "hack_dialog.solomon_seal.no_clear_air",
                        "封印{seal}: {stage}面に配置可能な空気マスがありません。",
                    ).format(seal=no + 1, stage=new_level_no + 1)
                )
            relocations.append({
                "meta": mi,
                "no": no,
                "old_level_no": old_level_no,
                "new_level_no": new_level_no,
                "old_pos": old_pos,
                "new_pos": new_pos,
                "relocated": tuple(old_pos) != tuple(new_pos),
            })
        return relocations

    def _apply_solomon_seal_stage_relocations(self, relocations: list, rom_data: bytearray) -> list:
        from ..core.element import byte_from_position

        notes = []
        for item in relocations:
            mi = item["meta"]
            mi.level_no = int(item["new_level_no"])
            mi.position = tuple(item["new_pos"])
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if 0 <= rom_offset < len(rom_data):
                rom_data[rom_offset] = byte_from_position(mi.position)
            if item.get("relocated"):
                notes.append(
                    t(
                        "hack_dialog.solomon_seal.relocation_note",
                        "封印{seal}: {stage}面 {old_pos} -> {new_pos}",
                    ).format(
                        seal=int(item["no"]) + 1,
                        stage=int(item["new_level_no"]) + 1,
                        old_pos=tuple(item["old_pos"]),
                        new_pos=tuple(item["new_pos"]),
                    )
                )
        return notes

    def _collect_wall_color_values(self) -> list:
        try:
            wall_color_hack.special_values(self.rom.data)
            return [int(v) & 0x3F for v in wall_color_hack.current_values(self.rom.data)]
        except wall_color_hack.WallColorHackError:
            return []

    @staticmethod
    def _is_global_meta_position_target(mi) -> bool:
        no = int(getattr(mi, "no", -1))
        if 0 <= no <= 7:
            return True
        return no in (12, 13)

    @staticmethod
    def _global_meta_kind(no: int) -> str:
        if 0 <= no <= 7:
            return "solomon_seal"
        if no == 12:
            return "page_space"
        if no == 13:
            return "page_time"
        return "unknown"

    def _level_meta_config(self):
        if self.config is not None:
            return self.config
        parent = self.parent()
        return getattr(parent, "config", None)

    def _collect_level_meta_positions(self) -> list:
        cfg = self._level_meta_config()
        if cfg is None:
            return []
        from ..core.element import position_from_byte

        result = []
        for mi in getattr(cfg, "level_meta_items", []) or []:
            if not self._is_global_meta_position_target(mi):
                continue
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if rom_offset < 0:
                continue
            if self.rom is not None and 0 <= rom_offset < len(self.rom.data):
                pos = position_from_byte(self.rom.data[rom_offset])
            else:
                pos = tuple(getattr(mi, "position", (0, 0)))
            result.append({
                "kind": self._global_meta_kind(int(mi.no)),
                "no": int(mi.no),
                "level_no": int(mi.level_no),
                "description": str(getattr(mi, "description", "")),
                "position": [int(pos[0]), int(pos[1])],
            })
        return result

    @staticmethod
    def _parse_level_meta_position_entry(entry: dict) -> tuple:
        from ..core import constants as c

        if not isinstance(entry, dict):
            raise ValueError("level_meta_positions entries must be objects.")
        no = int(entry["no"])
        level_no = int(entry["level_no"])
        pos = entry["position"]
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            raise ValueError("level_meta_positions position must be [x, y].")
        x = int(pos[0])
        y = int(pos[1])
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            raise ValueError(f"level_meta_positions position out of range: {x},{y}")
        return no, level_no, (x, y)

    def _apply_level_meta_positions(self, entries) -> list:
        if entries is None:
            return []
        if not isinstance(entries, list):
            raise ValueError("level_meta_positions must be a list.")
        cfg = self._level_meta_config()
        if cfg is None:
            return []
        from ..core.element import byte_from_position, position_from_byte

        meta_by_key = {
            (int(getattr(mi, "no", -1)), int(getattr(mi, "level_no", -1))): mi
            for mi in getattr(cfg, "level_meta_items", []) or []
        }
        changed = []
        for entry in entries:
            no, level_no, pos = self._parse_level_meta_position_entry(entry)
            if not (0 <= no <= 7 or no in (12, 13)):
                continue
            mi = meta_by_key.get((no, level_no))
            if mi is None:
                continue
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if rom_offset < 0 or self.rom is None or rom_offset >= len(self.rom.data):
                continue
            old_pos = position_from_byte(self.rom.data[rom_offset])
            if old_pos == pos:
                continue
            self.rom.data[rom_offset] = byte_from_position(pos)
            mi.position = pos
            changed.append(str(getattr(mi, "description", "") or f"meta {no}"))
        return changed

    def _selected_solomon_seal_stages(self) -> list:
        combos = getattr(self, "combo_seal_stages", []) or []
        if len(combos) != len(solomon_seal_stage.SLOTS):
            return solomon_seal_stage.defaults()
        return [int(combo.currentData()) for combo in combos]

    def _refresh_solomon_seal_stage_choices(self, *_args):
        if getattr(self, "_seal_stage_loading", False):
            return
        combos = getattr(self, "combo_seal_stages", []) or []
        if len(combos) != len(solomon_seal_stage.SLOTS):
            return
        current = self._selected_solomon_seal_stages()
        self._seal_stage_loading = True
        try:
            for slot, combo in enumerate(combos):
                old_value = current[slot]
                valid_choices = []
                for stage_no in solomon_seal_stage.candidates(slot, self.rom.data, self.rom.region):
                    if stage_no != old_value and stage_no in (
                        current[:slot] + current[slot + 1:]
                    ):
                        continue
                    trial = list(current)
                    trial[slot] = stage_no
                    try:
                        solomon_seal_stage.validate_stages(trial)
                    except solomon_seal_stage.SolomonSealStageError:
                        continue
                    valid_choices.append(stage_no)
                if old_value not in valid_choices:
                    valid_choices.insert(0, old_value)
                combo.blockSignals(True)
                combo.clear()
                for stage_no in valid_choices:
                    combo.addItem(t("hack_dialog.stage.option", "{stage}面").format(stage=stage_no), stage_no)
                idx = combo.findData(old_value)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
                combo.blockSignals(False)
        finally:
            self._seal_stage_loading = False

    def _current_final_stage_redirect_level_no(self) -> int:
        for i, level in enumerate(self.levels or []):
            if (
                i != final_stage_redirect.FINAL_STAGE_INDEX
                and stage_ext.final_stage_redirect_enabled(level)
            ):
                return i
        return -1

    def _current_final_stage_redirect_stage_no(self) -> int:
        level_no = self._current_final_stage_redirect_level_no()
        return level_no + 1 if level_no >= 0 else DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO

    def _set_final_stage_redirect_stage_no(self, stage_no: int) -> bool:
        if not self.levels:
            return False
        try:
            stage_no = int(stage_no)
        except Exception:
            stage_no = DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO
        if (
            stage_no < 1
            or stage_no > len(self.levels)
            or stage_no == final_stage_redirect.FINAL_STAGE_NO
        ):
            stage_no = DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO
        selected = -1 if stage_no == DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO else stage_no - 1
        old = self._current_final_stage_redirect_level_no()
        idx = self.combo_final_stage_redirect.findData(selected)
        self.combo_final_stage_redirect.setCurrentIndex(idx if idx >= 0 else 0)
        return old != selected

    def _apply_final_stage_redirect_setting(self) -> bool:
        if not self.levels:
            return False
        selected = int(self.combo_final_stage_redirect.currentData())
        changed = False
        for i, level in enumerate(self.levels):
            want = i == selected
            old = stage_ext.final_stage_redirect_enabled(level)
            if old != want:
                stage_ext.set_final_stage_redirect_enabled(level, want)
                changed = True
        return changed

    def _collect_global_settings(self) -> dict:
        """現在の画面値をROM非依存のJSON設定として集める。"""
        settings = {
            "start_stage": self.spin_stage.value(),
            "continue_max_stage": self.spin_continue.value(),
            "final_stage_redirect_after_stage": self._current_final_stage_redirect_stage_no(),
            "warp_feather_steps": self.spin_warp_feather.value(),
            "initial_magic_max": self.spin_initial_magic_max.value(),
            "initial_magic_pattern": self.edit_initial_magic.text(),
            "initial_lives": self.spin_initial_lives.value(),
            "time_rate_fast": self.spin_time_fast.value(),
            "time_rate_normal": self.spin_time_normal.value(),
            "time_rate_slow": self.spin_time_slow.value(),
            "main_palette_hex": self._hex_bytes(
                self.rom.data[0x0ED4:0x0ED4 + 32]
            ),
            "demo_input_wait_hex": self._hex_bytes(
                self.rom.data[demo_input.OFF_WAIT:demo_input.OFF_WAIT + demo_input.STEPS]
            ),
            "demo_input_joy_hex": self._hex_bytes(
                self.rom.data[demo_input.OFF_JOY:demo_input.OFF_JOY + demo_input.STEPS]
            ),
            "enemy_drop_c278_hex": self._hex_bytes(
                self.rom.data[enemy_drop.OFF_C278:enemy_drop.OFF_C278 + enemy_drop.LEN_C278]
            ),
            "enemy_drop_c293_hex": self._hex_bytes(
                self.rom.data[enemy_drop.OFF_C293:enemy_drop.OFF_C293 + enemy_drop.LEN_C293]
            ),
            "clear_message_hex": self._hex_bytes(
                self.rom.data[
                    clear_message.MESSAGES[0]["off"]:
                    clear_message.MESSAGES[-1]["off"] + 3 + clear_message.MESSAGES[-1]["count"] + 1
                ]
            ),
            "bonus_stage_pos_hex": self._hex_bytes(
                self.rom.data[
                    self._bonus_stage_offsets()[0]:
                    self._bonus_stage_offsets()[0] + 32
                ]
            ),
            "bonus_stage_items_hex": self._hex_bytes(
                self.rom.data[
                    self._bonus_stage_offsets()[1]:
                    self._bonus_stage_offsets()[1] + 16
                ]
            ),
            "wall_colors_1_48": self._collect_wall_color_values(),
            "walk_speed_multiplier": self._combo_data(self.combo_walk),
            "panel_monster_cooldown_frames": self.spin_pm.value(),
            "panel_bullet_speed_fix_enabled": self.chk_pm_bullet_speed_fix.isChecked(),
            "panel_bullet_speed_fix_value": self._combo_data(self.combo_pm_bullet_speed_fix),
            "panel_variant_settings": self._panel_variant_settings_from_ui(),
            "demo_stage": self.spin_ds.value(),
            "golem_snappy": self.chk_golem_snappy.isChecked(),
            "saramandor_variant_settings": self._saramandor_variant_settings_from_ui(),
            "gargoyle_snappy": self.chk_gargoyle_snappy.isChecked(),
            "gargoyle_cooldown_frames": self.spin_gargoyle_cooldown.value(),
            "gargoyle_variant_settings": self._gargoyle_variant_settings_from_ui("a"),
            "gargoyle_variant_b_settings": self._gargoyle_variant_settings_from_ui("b"),
            "dragon_snappy": self.chk_dragon_snappy.isChecked(),
            "shared_flame_start_wait_frames": self.spin_shared_flame_wait.value(),
            "shared_monster_walk_multiplier": self._combo_data(self.combo_shared_walk),
            "neul_ghost_speed_multiplier": self._combo_data(self.combo_neul_ghost_speed),
            "spark_ball_speed_multiplier": self._combo_data(self.combo_spark_ball_speed),
            "spark_ball_pause_digits": self._selected_spark_pause_digits(),
            "spark_ball_reverse_digits": self._selected_spark_reverse_digits(),
            "spark_ball_transparency_period": self._combo_data(self.combo_spark_transparency),
            **self._phantom_global_settings_from_ui(),
            **self._neul_ab_global_settings_from_ui(),
            **self._ghost_ab_global_settings_from_ui(),
            "demonhead_snappy": self.chk_demonhead_snappy.isChecked(),
            "clear_screen_preset": self._combo_data(self.combo_clearscreen),
            "stage_frame_white_enabled": self.chk_stage_frame_white.isChecked(),
            "gap_fix_enabled": self.chk_gapfix.isChecked(),
            "gap_fix_frames": self.spin_gapfix_frames.value(),
            "dark_light_frames": self.spin_dark_light.value(),
            "dark_dark_frames": self.spin_dark_dark.value(),
            "solomon_seal_stages": self._selected_solomon_seal_stages(),
            "level_meta_positions": self._collect_level_meta_positions(),
        }
        supported = {
            "warp_feather": bool(getattr(self, "_warp_feather_ok", False)),
            "initial_magic": bool(getattr(self, "_initial_magic_ok", False)),
            "initial_lives": bool(getattr(self, "_initial_lives_ok", False)),
            "time_rate": bool(getattr(self, "_time_rate_ok", False)),
            "wall_colors": bool(getattr(self, "_wall_color_table_ok", False)),
            "walk_speed": bool(getattr(self, "_walk_ok", False)),
            "panel_monster": bool(getattr(self, "_pm_ok", False)),
            "panel_bullet_speed_fix": bool(getattr(self, "_pm_bullet_speed_ok", False)),
            "demo_stage": bool(getattr(self, "_ds_ok", False)),
            "golem": bool(getattr(self, "_golem_ok", False)),
            "saramandor_variant": bool(
                getattr(self, "_saramandor_variant_ok", False)
            ),
            "gargoyle": bool(getattr(self, "_gargoyle_ok", False)),
            "gargoyle_variant": bool(getattr(self, "_gargoyle_variant_ok", False)),
            "dragon": bool(getattr(self, "_dragon_ok", False)),
            "shared_flame_start_wait": bool(getattr(self, "_shared_flame_wait_ok", False)),
            "golem_speed": bool(getattr(self, "_golem_spd_ok", False)),
            "neul_ghost_speed": bool(getattr(self, "_neul_ghost_spd_ok", False)),
            "spark_ball_speed": bool(getattr(self, "_spark_ball_spd_ok", False)),
            "spark_ball_variant": bool(getattr(self, "_spark_ball_variant_ok", False)),
            "phantom_preset": bool(getattr(self, "_phantom_preset_ok", False)),
            "neul_ab": bool(getattr(self, "_neul_ab_ok", False)),
            "ghost_ab": bool(getattr(self, "_ghost_ab_ok", False)),
            "demonhead": bool(getattr(self, "_demonhead_ok", False)),
            "clear_screen": bool(getattr(self, "_cs_ok", False)),
            "stage_frame": bool(getattr(self, "_stage_frame_ok", False)),
            "gap_fix": bool(getattr(self, "_gapfix_ok", False)),
            "dark_tempo": bool(getattr(self, "_dark_tempo_ok", False)),
            "solomon_seal_stages": bool(getattr(self, "_seal_stage_ok", False)),
        }
        return {
            "format": "solomon_customizer_global_settings",
            "version": 1,
            "app_version": __version__,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rom_region": getattr(self.rom, "region", ""),
            "settings": settings,
            "supported": supported,
        }

    def _apply_imported_global_settings(self, settings: dict) -> list:
        """JSON設定を反映する。一部のROM直持ちデータは即時にrom.dataへ書く。"""
        changed = []

        def has(key):
            return key in settings

        def set_spin(key, spin, label):
            if has(key) and spin.isEnabled():
                old = spin.value()
                spin.setValue(int(settings[key]))
                if spin.value() != old:
                    changed.append(label)

        def set_double(key, spin, label):
            if has(key) and spin.isEnabled():
                old = spin.value()
                spin.setValue(float(settings[key]))
                if abs(spin.value() - old) > 1e-6:
                    changed.append(label)

        def set_check(key, chk, label):
            if has(key) and chk.isEnabled():
                old = chk.isChecked()
                chk.setChecked(bool(settings[key]))
                if chk.isChecked() != old:
                    changed.append(label)

        def set_spark_digits(key, label, checkboxes, getter):
            if not has(key) or not getattr(self, "_spark_ball_variant_ok", False):
                return
            old = getter()
            try:
                selected = spark_ball_variant.normalize_pause_digits(settings[key])
            except (TypeError, ValueError, spark_ball_variant.SparkBallVariantError):
                return
            visible = set(selected)
            for i, chk in enumerate(checkboxes):
                chk.setChecked(i in visible)
            if getter() != old:
                changed.append(label)

        def set_combo(key, combo, label):
            if has(key) and combo.isEnabled():
                old = combo.currentIndex()
                if self._set_combo_data(combo, settings[key]) and combo.currentIndex() != old:
                    changed.append(label)

        def set_panel_variant_settings(key, label):
            if not has(key):
                return
            old = self._panel_variant_settings_from_ui()
            values = normalize_panel_variant_settings(settings[key])
            for name, (combo, spin) in getattr(self, "_panel_variant_controls", {}).items():
                self._set_combo_data(combo, values[f"{name}_speed"])
                spin.setValue(values[f"{name}_interval"])
            if self._panel_variant_settings_from_ui() != old:
                changed.append(label)

        def set_gargoyle_variant_settings(key, label, variant="a"):
            if not has(key) or not getattr(self, "_gargoyle_variant_ok", False):
                return
            raw = settings[key]
            if not isinstance(raw, dict):
                return
            old = self._gargoyle_variant_settings_from_ui(variant)
            try:
                movement_speed = gargoyle_variant.normalize_movement_speed(
                    raw.get("movement_speed", gargoyle_variant.DEFAULT_MOVEMENT_SPEED)
                )
                speed = gargoyle_variant.normalize_speed_preset(
                    raw.get("speed_preset", gargoyle_variant.DEFAULT_SPEED_PRESET)
                )
                inter_shot = gargoyle_variant.normalize_inter_shot(
                    raw.get("inter_shot_frames", gargoyle_variant.DEFAULT_INTER_SHOT_FRAMES)
                )
                cooldown = gargoyle_variant.normalize_cooldown(
                    raw.get("cooldown_frames", gargoyle_variant.DEFAULT_COOLDOWN_FRAMES)
                )
            except gargoyle_variant.GargoyleVariantError:
                return
            if variant == "b":
                movement_combo = self.combo_gargoyle_variant_b_movement
                combo = self.combo_gargoyle_variant_b_speed
                inter_spin = self.spin_gargoyle_variant_b_inter_shot
                cooldown_spin = self.spin_gargoyle_variant_b_cooldown
            else:
                movement_combo = self.combo_gargoyle_variant_movement
                combo = self.combo_gargoyle_variant_speed
                inter_spin = self.spin_gargoyle_variant_inter_shot
                cooldown_spin = self.spin_gargoyle_variant_cooldown
            self._set_combo_data(movement_combo, movement_speed)
            self._set_combo_data(combo, speed)
            inter_spin.setValue(inter_shot)
            cooldown_spin.setValue(cooldown)
            if self._gargoyle_variant_settings_from_ui(variant) != old:
                changed.append(label)

        def set_saramandor_variant_settings(key, label):
            if not has(key) or not getattr(self, "_saramandor_variant_ok", False):
                return
            raw = settings[key]
            if not isinstance(raw, (list, tuple)) or len(raw) != saramandor_variant.VARIANT_COUNT:
                return
            old = self._saramandor_variant_settings_from_ui()
            try:
                values = saramandor_variant._normalize_settings(raw)
            except (KeyError, TypeError, saramandor_variant.SaramandorVariantError):
                return
            for controls, item in zip(self._saramandor_variant_controls, values):
                movement, flame, refire, stop = controls
                self._set_combo_data(movement, item["movement_speed"])
                self._set_combo_data(flame, item["flame_speed"])
                refire.setValue(item["refire_wait"])
                stop.setValue(item["post_fire_stop"])
            if self._saramandor_variant_settings_from_ui() != old:
                changed.append(label)

        set_spin("start_stage", self.spin_stage, t("hack_dialog.setting.start_stage", "開始ステージ"))
        set_spin("continue_max_stage", self.spin_continue, t("hack_dialog.setting.continue_limit", "コンティニュー上限"))
        if has("final_stage_redirect_after_stage"):
            if self._set_final_stage_redirect_stage_no(settings["final_stage_redirect_after_stage"]):
                changed.append(t("hack_dialog.setting.final_stage_redirect", "最終面への移行"))
        set_spin("warp_feather_steps", self.spin_warp_feather, t("hack_dialog.setting.warp_feather", "ワープ羽"))
        set_spin("initial_magic_max", self.spin_initial_magic_max, t("hack_dialog.setting.initial_magic_max", "初期魔法 最大数"))
        if has("initial_magic_pattern") and self.edit_initial_magic.isEnabled():
            old = self.edit_initial_magic.text()
            self.edit_initial_magic.setText(str(settings["initial_magic_pattern"]))
            if self.edit_initial_magic.text() != old:
                changed.append(t("hack_dialog.setting.initial_magic_pattern", "初期魔法 初期所持"))
        set_spin("initial_lives", self.spin_initial_lives, t("hack_dialog.setting.initial_lives", "初期残数"))
        set_spin("time_rate_fast", self.spin_time_fast, t("hack_dialog.setting.time_fast", "ステージ制限時間 速い"))
        set_spin("time_rate_normal", self.spin_time_normal, t("hack_dialog.setting.time_normal", "ステージ制限時間 普通"))
        set_spin("time_rate_slow", self.spin_time_slow, t("hack_dialog.setting.time_slow", "ステージ制限時間 遅い"))
        if has("solomon_seal_stages") and getattr(self, "_seal_stage_ok", False):
            values = solomon_seal_stage.validate_stages(settings["solomon_seal_stages"])
            old = self._selected_solomon_seal_stages()
            for combo, stage_no in zip(self.combo_seal_stages, values):
                idx = combo.findData(int(stage_no))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            if self._selected_solomon_seal_stages() != old:
                changed.append(t("hack_dialog.setting.solomon_seal_stage", "ソロモンの封印 出現面"))
                self._sync_parent_solomon_seal_stages(values)
        if has("wall_colors_1_48"):
            values = settings["wall_colors_1_48"]
            if values == []:
                pass
            elif not isinstance(values, list) or len(values) != wall_color_hack.EDIT_COUNT:
                raise ValueError(
                    f"wall_colors_1_48 must be a {wall_color_hack.EDIT_COUNT}-item list."
                )
            else:
                wall_changed = wall_color_hack.apply(self.rom.data, values)
                if wall_changed:
                    changed.append(t("hack_dialog.setting.wall_color", "ステージ壁色"))
                    self._sync_parent_wall_color()
        if has("main_palette_hex"):
            values = settings["main_palette_hex"]
            if not isinstance(values, str):
                raise ValueError("main_palette_hex must be a hex string.")
            old = bytes(self.rom.data[0x0ED4:0x0ED4 + 32])
            new = self._parse_hex_bytes(values, 32, "main_palette_hex")
            if new != old:
                self.rom.data[0x0ED4:0x0ED4 + 32] = new
                changed.append(t("hack_dialog.setting.main_palette", "メインパレット"))
        if has("demo_input_wait_hex"):
            values = settings["demo_input_wait_hex"]
            if not isinstance(values, str):
                raise ValueError("demo_input_wait_hex must be a hex string.")
            old = bytes(self.rom.data[demo_input.OFF_WAIT:demo_input.OFF_WAIT + demo_input.STEPS])
            new = self._parse_hex_bytes(values, demo_input.STEPS, "demo_input_wait_hex")
            if new != old:
                self.rom.data[demo_input.OFF_WAIT:demo_input.OFF_WAIT + demo_input.STEPS] = new
                changed.append(t("hack_dialog.setting.demo_wait", "デモ操作 wait"))
        if has("demo_input_joy_hex"):
            values = settings["demo_input_joy_hex"]
            if not isinstance(values, str):
                raise ValueError("demo_input_joy_hex must be a hex string.")
            old = bytes(self.rom.data[demo_input.OFF_JOY:demo_input.OFF_JOY + demo_input.STEPS])
            new = self._parse_hex_bytes(values, demo_input.STEPS, "demo_input_joy_hex")
            if new != old:
                self.rom.data[demo_input.OFF_JOY:demo_input.OFF_JOY + demo_input.STEPS] = new
                changed.append(t("hack_dialog.setting.demo_joy", "デモ操作 joy"))
        if has("enemy_drop_c278_hex"):
            values = settings["enemy_drop_c278_hex"]
            if not isinstance(values, str):
                raise ValueError("enemy_drop_c278_hex must be a hex string.")
            old = bytes(self.rom.data[enemy_drop.OFF_C278:enemy_drop.OFF_C278 + enemy_drop.LEN_C278])
            new = self._parse_hex_bytes(values, enemy_drop.LEN_C278, "enemy_drop_c278_hex")
            if new != old:
                self.rom.data[enemy_drop.OFF_C278:enemy_drop.OFF_C278 + enemy_drop.LEN_C278] = new
                changed.append(t("hack_dialog.setting.enemy_drop_c278", "敵ドロップ C278"))
        if has("enemy_drop_c293_hex"):
            values = settings["enemy_drop_c293_hex"]
            if not isinstance(values, str):
                raise ValueError("enemy_drop_c293_hex must be a hex string.")
            old = bytes(self.rom.data[enemy_drop.OFF_C293:enemy_drop.OFF_C293 + enemy_drop.LEN_C293])
            new = self._parse_hex_bytes(values, enemy_drop.LEN_C293, "enemy_drop_c293_hex")
            if new != old:
                self.rom.data[enemy_drop.OFF_C293:enemy_drop.OFF_C293 + enemy_drop.LEN_C293] = new
                changed.append(t("hack_dialog.setting.enemy_drop_c293", "敵ドロップ C293"))
        if has("clear_message_hex"):
            start = clear_message.MESSAGES[0]["off"]
            end = clear_message.MESSAGES[-1]["off"] + 3 + clear_message.MESSAGES[-1]["count"] + 1
            values = settings["clear_message_hex"]
            if not isinstance(values, str):
                raise ValueError("clear_message_hex must be a hex string.")
            old = bytes(self.rom.data[start:end])
            new = self._parse_hex_bytes(values, end - start, "clear_message_hex")
            if new != old:
                self.rom.data[start:end] = new
                changed.append(t("hack_dialog.setting.clear_message", "クリア画面メッセージ"))
        bonus_changed = False
        if has("bonus_stage_pos_hex"):
            pos_addr, _item_addr = self._bonus_stage_offsets()
            values = settings["bonus_stage_pos_hex"]
            if not isinstance(values, str):
                raise ValueError("bonus_stage_pos_hex must be a hex string.")
            old = bytes(self.rom.data[pos_addr:pos_addr + 32])
            new = self._parse_hex_bytes(values, 32, "bonus_stage_pos_hex")
            if new != old:
                self.rom.data[pos_addr:pos_addr + 32] = new
                changed.append(t("hack_dialog.setting.bonus_positions", "ボーナスステージ配置"))
                bonus_changed = True
        if has("bonus_stage_items_hex"):
            _pos_addr, item_addr = self._bonus_stage_offsets()
            values = settings["bonus_stage_items_hex"]
            if not isinstance(values, str):
                raise ValueError("bonus_stage_items_hex must be a hex string.")
            old = bytes(self.rom.data[item_addr:item_addr + 16])
            new = self._parse_hex_bytes(values, 16, "bonus_stage_items_hex")
            if new != old:
                self.rom.data[item_addr:item_addr + 16] = new
                changed.append(t("hack_dialog.setting.bonus_items", "ボーナスステージアイテム"))
                bonus_changed = True
        if bonus_changed:
            self._sync_parent_bonus_stage()
        if has("level_meta_positions"):
            meta_changed = self._apply_level_meta_positions(settings["level_meta_positions"])
            for name in meta_changed:
                changed.append(t("hack_dialog.setting.meta_position", "メタ項目座標: {name}").format(name=name))
        set_combo("walk_speed_multiplier", self.combo_walk, t("hack_dialog.setting.walk_speed", "ダーナ歩行速度"))

        set_spin("panel_monster_cooldown_frames", self.spin_pm, t("hack_dialog.setting.panel_cooldown", "パネルモンスター クールダウン"))
        set_check("panel_bullet_speed_fix_enabled", self.chk_pm_bullet_speed_fix, t("hack_dialog.setting.panel_bullet_fix", "パネルモンスター 弾の左右速度バグ修正"))
        set_combo("panel_bullet_speed_fix_value", self.combo_pm_bullet_speed_fix, t("hack_dialog.setting.panel_bullet_speed", "パネルモンスター 弾速度"))
        set_panel_variant_settings("panel_variant_settings", t("hack_dialog.setting.panel_variant", "パネルモンスター A/B/C/D共通値"))
        set_spin("demo_stage", self.spin_ds, t("hack_dialog.setting.demo_stage", "デモステージ"))
        set_check("golem_snappy", self.chk_golem_snappy, t("hack_dialog.setting.golem_snappy", "ゴブリン キビキビ"))
        set_saramandor_variant_settings(
            "saramandor_variant_settings",
            t("hack_dialog.setting.saramandor_variant_abc", "強化サラマンダーA/B/C"),
        )
        set_check("gargoyle_snappy", self.chk_gargoyle_snappy, t("hack_dialog.setting.gargoyle_snappy", "ガーゴイル キビキビ"))
        set_spin("gargoyle_cooldown_frames", self.spin_gargoyle_cooldown, t("hack_dialog.setting.gargoyle_cooldown", "ガーゴイル クールダウン"))
        set_gargoyle_variant_settings("gargoyle_variant_settings", t("hack_dialog.setting.gargoyle_variant_a", "強化ガーゴイルA"), "a")
        set_gargoyle_variant_settings("gargoyle_variant_b_settings", t("hack_dialog.setting.gargoyle_variant_b", "強化ガーゴイルB"), "b")
        set_check("dragon_snappy", self.chk_dragon_snappy, t("hack_dialog.setting.dragon_snappy", "ドラゴン キビキビ"))
        set_spin("shared_flame_start_wait_frames", self.spin_shared_flame_wait, t("hack_dialog.setting.shared_flame_wait", "火吐き開始待ち"))
        set_combo("shared_monster_walk_multiplier", self.combo_shared_walk, t("hack_dialog.setting.shared_walk", "共通歩行速度"))
        set_combo("neul_ghost_speed_multiplier", self.combo_neul_ghost_speed, t("hack_dialog.setting.neul_ghost_speed", "ゴースト＆ヌエル移動速度"))
        set_combo("spark_ball_speed_multiplier", self.combo_spark_ball_speed, t("hack_dialog.setting.spark_ball_speed", "スパークボール移動速度"))
        set_spark_digits("spark_ball_pause_digits", t("hack_dialog.setting.spark_ball_pause", "強化スパークボール停止"), self.chk_spark_pause_digits, self._selected_spark_pause_digits)
        set_spark_digits("spark_ball_reverse_digits", t("hack_dialog.setting.spark_ball_reverse", "強化スパークボール反転"), self.chk_spark_reverse_digits, self._selected_spark_reverse_digits)
        set_combo("spark_ball_transparency_period", self.combo_spark_transparency, t("hack_dialog.setting.spark_ball_transparency", "強化スパークボール透明化"))
        for index, (speed, amplitude, phase) in enumerate(
            self._phantom_preset_controls
        ):
            group = phantom_preset_runtime.GROUP_NAMES[index]
            set_spin(
                self._phantom_global_key(index, "speed"),
                speed,
                t(
                    "hack_dialog.setting.phantom_preset_speed",
                    "Phantom group {group} speed",
                ).format(group=group),
            )
            set_combo(
                self._phantom_global_key(index, "amplitude_percent"),
                amplitude,
                t(
                    "hack_dialog.setting.phantom_preset_amplitude",
                    "Phantom group {group} amplitude",
                ).format(group=group),
            )
            set_spin(
                self._phantom_global_key(index, "phase_offset"),
                phase,
                t(
                    "hack_dialog.setting.phantom_preset_phase",
                    "Phantom group {group} sine table start",
                ).format(group=group),
            )
        for index, (body_speed, fire_interval, bullet_speed) in enumerate(
            self._neul_ab_controls
        ):
            group = neul84_runtime.GROUP_NAMES[index]
            prefix = f"neul_ab_{group.lower()}"
            set_combo(f"{prefix}_body_speed", body_speed, t("hack_dialog.setting.neul_ab_body_speed", "ヌエル{group} 本体速度").format(group=group))
            set_spin(f"{prefix}_fire_interval", fire_interval, t("hack_dialog.setting.neul_ab_fire_interval", "ヌエル{group} 発射間隔").format(group=group))
            set_combo(f"{prefix}_bullet_speed", bullet_speed, t("hack_dialog.setting.neul_ab_bullet_speed", "ヌエル{group} 弾速度").format(group=group))
        for index, (body_speed, fire_interval, bullet_speed, fire_direction) in enumerate(
            self._ghost_ab_controls
        ):
            group = ghostb0_runtime.GROUP_NAMES[index]
            prefix = f"ghost_ab_{group.lower()}"
            set_combo(f"{prefix}_body_speed", body_speed, t("hack_dialog.setting.ghost_ab_body_speed", "ゴースト{group} 本体速度").format(group=group))
            set_spin(f"{prefix}_fire_interval", fire_interval, t("hack_dialog.setting.ghost_ab_fire_interval", "ゴースト{group} 発射間隔").format(group=group))
            set_combo(f"{prefix}_bullet_speed", bullet_speed, t("hack_dialog.setting.ghost_ab_bullet_speed", "ゴースト{group} 弾速度").format(group=group))
            set_combo(f"{prefix}_fire_direction", fire_direction, t("hack_dialog.setting.ghost_ab_fire_direction", "ゴースト{group} 発射方向").format(group=group))
        set_check("demonhead_snappy", self.chk_demonhead_snappy, t("hack_dialog.setting.demonhead_snappy", "デーモンヘッド キビキビ"))
        if has("clear_screen_preset") and self.combo_clearscreen.isEnabled():
            old = self.combo_clearscreen.currentIndex()
            self._set_combo_data(self.combo_clearscreen, str(settings["clear_screen_preset"]))
            if self.combo_clearscreen.currentIndex() != old:
                changed.append(t("hack_dialog.setting.clear_screen_char", "クリア画面キャラ"))
        set_check("stage_frame_white_enabled", self.chk_stage_frame_white, t("hack_dialog.setting.stage_frame", "ステージ外枠"))
        set_check("gap_fix_enabled", self.chk_gapfix, t("hack_dialog.setting.gap_fix", "横穴侵入安定化"))
        set_spin("gap_fix_frames", self.spin_gapfix_frames, t("hack_dialog.setting.gap_fix_frames", "横穴侵入 許可フレーム"))
        set_spin("dark_light_frames", self.spin_dark_light, t("hack_dialog.setting.dark_light", "暗闇 明フレーム"))
        set_spin("dark_dark_frames", self.spin_dark_dark, t("hack_dialog.setting.dark_dark", "暗闇 暗フレーム"))
        return changed

    def _on_export_global_settings(self):
        from .file_dialog_compat import get_path
        path = get_path(
            self,
            title=t("hack_dialog.export.title", "共通設定をエクスポート"),
            directory=f"solomon_global_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            filter=t("common.file_filter.json", "JSON (*.json);;All Files (*)"),
            mode="save",
            app_config=self._app_config,
            config_key="global_settings_json",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_global_settings(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, t("hack_dialog.export.failed", "エクスポート失敗"), f"{type(e).__name__}: {e}")
            return
        QMessageBox.information(
            self,
            t("hack_dialog.export.complete.title", "エクスポート完了"),
            t("hack_dialog.export.complete.body", "共通設定を保存しました:\n{path}").format(path=path),
        )

    def _on_import_global_settings(self):
        ans = QMessageBox.warning(
            self,
            t("hack_dialog.import.confirm.title", "共通設定インポートの確認"),
            t(
                "hack_dialog.import.confirm.body",
                "これから選択する共通設定を読み込むと、メインパレット、ステージ壁色、デモ操作、敵ドロップ、"
                "クリア画面メッセージ、ボーナスステージ、ソロモンの紋章/Page座標などROMデータは"
                "読み込み時点で反映されます。\n\n"
                "この操作はUndoできません。元に戻す可能性がある場合は、先に現在の共通設定を"
                "エクスポートしてください。\n\n"
                "共通設定ファイルを選択しますか？",
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        from .file_dialog_compat import get_file
        path = get_file(
            self,
            title=t("hack_dialog.import.title", "共通設定をインポート"),
            filter=t("common.file_filter.json", "JSON (*.json);;All Files (*)"),
            app_config=self._app_config,
            config_key="global_settings_json",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, t("hack_dialog.import.failed", "インポート失敗"), f"{type(e).__name__}: {e}")
            return
        if payload.get("format") != "solomon_customizer_global_settings":
            QMessageBox.warning(
                self,
                t("hack_dialog.import.format_error.title", "形式エラー"),
                t("hack_dialog.import.format_error.not_global", "このファイルは共通設定JSONではありません。"),
            )
            return
        settings = payload.get("settings")
        if not isinstance(settings, dict):
            QMessageBox.warning(
                self,
                t("hack_dialog.import.format_error.title", "形式エラー"),
                t("hack_dialog.import.format_error.no_settings", "settings が見つからないか不正です。"),
            )
            return
        try:
            changed = self._apply_imported_global_settings(settings)
        except Exception as e:
            QMessageBox.critical(self, t("hack_dialog.import.failed", "インポート失敗"), f"{type(e).__name__}: {e}")
            return
        msg = t(
            "hack_dialog.import.complete.body",
            "共通設定を読み込みました。\n"
            "一部のROMデータは読み込み時点で反映済みです。\n"
            "画面上の設定値は [適用] または [OK] で反映されます。",
        )
        if changed:
            msg += t("hack_dialog.import.changed_header", "\n\n変更された項目:\n")
            msg += "\n".join(t("common.bullet_item", "・{item}").format(item=x) for x in changed)
        else:
            msg += t("hack_dialog.import.no_changes", "\n\n現在の画面値と同じ内容でした。")
        if "level_meta_positions" in settings:
            parent = self.parent()
            refresh = getattr(parent, "_refresh_view", None)
            if callable(refresh):
                refresh()
            refresh_thumb = getattr(parent, "_generate_all_thumbnails", None)
            if callable(refresh_thumb):
                refresh_thumb()
        QMessageBox.information(self, t("hack_dialog.import.complete.title", "インポート完了"), msg)

    def _restore_geometry(self):
        cfg = self._app_config
        if not cfg:
            return
        w = int(cfg.get("hack_dlg_w", -1))
        h = int(cfg.get("hack_dlg_h", -1))
        x = int(cfg.get("hack_dlg_x", -1))
        y = int(cfg.get("hack_dlg_y", -1))
        if w > 100 and h > 100:
            self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)

    def _save_geometry(self):
        cfg = self._app_config
        if cfg is None:
            return
        try:
            from ..core.config import save_config
            cfg["hack_dlg_x"] = max(0, self.x())
            cfg["hack_dlg_y"] = max(0, self.y())
            cfg["hack_dlg_w"] = self.width()
            cfg["hack_dlg_h"] = self.height()
            save_config(cfg)
        except Exception:
            pass   # 設定保存失敗でダイアログ閉鎖を妨げない

    def done(self, r):
        # OK/キャンセル/Esc/×ボタン すべて経由する。閉じる直前に保存。
        self._save_geometry()
        super().done(r)

    def _apply_changes(self) -> bool:
        """各値を rom.data に書き込み"""
        if self.rom is None or self.rom.data is None:
            return False
        d = self.rom.data
        applied = []

        # 開始ステージ
        stage_no = self.spin_stage.value()
        if stage_no == 1:
            if d[0x1145] != 0x00:
                d[0x1145] = 0x00
                applied.append(t("hack_dialog.applied.start_stage.default", "開始ステージ → 1面"))
            if d[0x1149] != 0x8D:
                d[0x1149] = 0x8D
            if d[0x114B] != 0x04:
                d[0x114B] = 0x04
        else:
            stage_byte = (stage_no - 1) & 0xff
            if d[0x1145] != stage_byte:
                d[0x1145] = stage_byte
                applied.append(t("hack_dialog.applied.start_stage", "開始ステージ → {stage}面").format(stage=stage_no))
            if d[0x1149] != 0xAD:
                d[0x1149] = 0xAD
            if d[0x114B] != 0x93:
                d[0x114B] = 0x93

        # コンティニュー上限ステージ
        new_cont = (self.spin_continue.value() - 1) & 0xff
        if self._continue_offset < len(d) and d[self._continue_offset] != new_cont:
            d[self._continue_offset] = new_cont
            applied.append(t("hack_dialog.applied.continue_limit", "コンティニュー上限 → {stage}").format(stage=self.spin_continue.value()))

        if self._apply_final_stage_redirect_setting():
            selected = int(self.combo_final_stage_redirect.currentData())
            if selected < 0:
                applied.append(
                    t(
                        "hack_dialog.applied.final_stage.original",
                        "最終ステージ → {stage}面をクリアした後（原作）",
                    ).format(stage=DEFAULT_FINAL_STAGE_REDIRECT_STAGE_NO)
                )
            else:
                applied.append(t("hack_dialog.applied.final_stage", "最終ステージ → {stage}面をクリアした後").format(stage=selected + 1))
            self._mark_parent_dirty(t("hack_dialog.log.final_stage_changed", "最終ステージ設定を変更"))

        # ワープ羽
        if getattr(self, "_warp_feather_ok", False):
            try:
                applied.extend(
                    warp_feather.apply(d, self.spin_warp_feather.value()))
            except warp_feather.WarpFeatherError as e:
                QMessageBox.warning(self, t("hack_dialog.error.warp_feather", "ワープ羽 設定失敗"), str(e))

        # ソロモンの封印 出現面
        if getattr(self, "_seal_stage_ok", False):
            try:
                stages = self._selected_solomon_seal_stages()
                seal_relocations = self._plan_solomon_seal_stage_relocations(stages)
                seal_changes = solomon_seal_stage.apply(d, self.rom.region, stages)
                if seal_changes:
                    relocation_notes = self._apply_solomon_seal_stage_relocations(seal_relocations, d)
                    applied.append(t("hack_dialog.applied.solomon_seal_stage", "ソロモンの封印 出現面: {changes}").format(changes=" / ".join(seal_changes)))
                    if relocation_notes:
                        applied.append(t("hack_dialog.applied.solomon_seal_relocation", "ソロモンの封印 位置補正: {changes}").format(changes=" / ".join(relocation_notes)))
                    self._sync_parent_solomon_seal_stages(stages)
            except solomon_seal_stage.SolomonSealStageError as e:
                QMessageBox.warning(self, t("hack_dialog.error.solomon_seal_stage", "ソロモンの封印 出現面 設定失敗"), str(e))
                return False

        # 初期魔法 (共通)
        if getattr(self, "_initial_magic_ok", False):
            try:
                pattern = initial_magic.normalize_pattern_text(
                    self.edit_initial_magic.text())
                self.edit_initial_magic.setText(pattern)
                imch = initial_magic.apply(
                    d, self.spin_initial_magic_max.value(), pattern)
                if imch:
                    applied.append(t("hack_dialog.applied.initial_magic", "初期魔法: {changes}").format(changes=" / ".join(imch)))
            except initial_magic.InitialMagicError as e:
                QMessageBox.warning(self, t("hack_dialog.error.initial_magic", "初期魔法 設定失敗"), str(e))

        # 初期残数
        if getattr(self, "_initial_lives_ok", False):
            try:
                lvch = initial_lives.apply(
                    d, self.spin_initial_lives.value())
                if lvch:
                    applied.append(t("hack_dialog.applied.initial_lives", "初期残数: {changes}").format(changes=" / ".join(lvch)))
            except initial_lives.InitialLivesError as e:
                QMessageBox.warning(self, t("hack_dialog.error.initial_lives", "初期残数 設定失敗"), str(e))

        # ステージ制限時間
        if getattr(self, "_time_rate_ok", False):
            try:
                tch = time_decrease_hack.apply(
                    d,
                    (
                        self.spin_time_fast.value(),
                        self.spin_time_normal.value(),
                        self.spin_time_slow.value(),
                    ),
                )
                if tch:
                    applied.append(t("hack_dialog.applied.time_decrease", "ステージ制限時間: {changes}").format(changes=" / ".join(tch)))
            except time_decrease_hack.TimeDecreaseHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.time_decrease", "ステージ制限時間 設定失敗"), str(e))

        # ステージ壁色 (1-48面)
        if getattr(self, "_wall_color_ok", False):
            try:
                wch = wall_color_hack.apply(
                    d, [self._combo_data(c) for c in self.combo_wall_colors])
                if wch:
                    applied.append(t("hack_dialog.applied.wall_color", "ステージ壁色: {changes}").format(changes=" / ".join(wch)))
            except wall_color_hack.WallColorHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.wall_color", "ステージ壁色 設定失敗"), str(e))

        # ダーナ歩行速度
        if self._walk_ok:
            mult = self.combo_walk.currentData()
            try:
                changed = walk_speed.apply_multiplier(d, mult)
                if changed:
                    applied.append(t("hack_dialog.applied.walk_speed", "歩行速度 → {mult:g}x ({changes})").format(mult=mult, changes="/".join(changed)))
            except walk_speed.WalkSpeedError as e:
                QMessageBox.warning(self, t("hack_dialog.error.walk_speed", "歩行速度の改造失敗"), str(e))

        # Enhanced Saramandor A/B/C reaction range is handled by saramandor_variant.
        # Do not rewrite the shared stock Saramandor/Dragon distance bytes.
        if getattr(self, "_saramandor_variant_ok", False):
            try:
                svch = saramandor_variant.apply(
                    d,
                    self._saramandor_variant_settings_from_ui(),
                )
                if svch:
                    applied.append(
                        t(
                            "hack_dialog.applied.saramandor_variant",
                            "強化サラマンダー: {changes}",
                        ).format(changes=" / ".join(svch))
                    )
            except saramandor_variant.SaramandorVariantError as e:
                QMessageBox.warning(
                    self,
                    t(
                        "hack_dialog.error.saramandor_variant",
                        "強化サラマンダー設定失敗",
                    ),
                    str(e),
                )
                return

        # パネルモンスター
        if self._pm_ok:
            try:
                pch = panel_monster_hack.apply_cooldown(
                    d, self.spin_pm.value())
                if getattr(self, "_pm_bullet_speed_ok", False):
                    pch.extend(panel_bullet_speed_fix.apply(
                        d,
                        self.chk_pm_bullet_speed_fix.isChecked(),
                        self._combo_data(self.combo_pm_bullet_speed_fix),
                    ))
                if pch:
                    applied.append(t("hack_dialog.applied.panel_monster", "パネルモンスター: {changes}").format(changes=" / ".join(pch)))
            except panel_monster_hack.PanelMonsterHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.panel_monster", "パネルモンスター改造失敗"), str(e))
            except panel_bullet_speed_fix.PanelBulletSpeedFixError as e:
                QMessageBox.warning(self, t("hack_dialog.error.panel_bullet_speed", "パネルモンスター弾速度修正失敗"), str(e))

        # デモプレイのステージ
        if self._ds_ok:
            try:
                dch = demo_stage_hack.apply(d, self.spin_ds.value())
                if dch:
                    applied.append(t("hack_dialog.applied.demo_stage", "デモプレイ: {changes}").format(changes=" / ".join(dch)))
            except demo_stage_hack.DemoStageHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.demo_stage", "デモステージ改造失敗"), str(e))

        # ゴーレム キビキビ
        if self._golem_ok:
            try:
                gch = golem_hack.apply(d, self.chk_golem_snappy.isChecked())
                if gch:
                    applied.append(t("hack_dialog.applied.golem", "ゴブリン: {changes}").format(changes=" / ".join(gch)))
            except golem_hack.GolemHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.golem", "ゴブリン改造失敗"), str(e))

        # ガーゴイル キビキビ
        if self._gargoyle_ok:
            try:
                gych = gargoyle_hack.apply(
                    d, self.chk_gargoyle_snappy.isChecked())
                cdch = gargoyle_hack.apply_cooldown(
                    d, self.spin_gargoyle_cooldown.value())
                gych.extend(cdch)
                if gych:
                    applied.append(t("hack_dialog.applied.gargoyle", "ガーゴイル: {changes}").format(changes=" / ".join(gych)))
            except gargoyle_hack.GargoyleHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.gargoyle", "ガーゴイル改造失敗"), str(e))

        # 強化ガーゴイル
        if getattr(self, "_gargoyle_variant_ok", False):
            try:
                gv_settings = self._gargoyle_variant_settings_from_ui("a")
                gv_settings_b = self._gargoyle_variant_settings_from_ui("b")
                gvch = gargoyle_variant.apply(
                    d,
                    gv_settings["speed_preset"],
                    gv_settings["inter_shot_frames"],
                    gv_settings["cooldown_frames"],
                    gv_settings_b["speed_preset"],
                    gv_settings_b["inter_shot_frames"],
                    gv_settings_b["cooldown_frames"],
                    movement_speed=gv_settings["movement_speed"],
                    b_movement_speed=gv_settings_b["movement_speed"],
                )
                if gvch:
                    applied.append(t("hack_dialog.applied.gargoyle_variant", "強化ガーゴイル: {changes}").format(changes=" / ".join(gvch)))
            except gargoyle_variant.GargoyleVariantError as e:
                QMessageBox.warning(self, t("hack_dialog.error.gargoyle_variant", "強化ガーゴイル設定失敗"), str(e))
                return

        # ドラゴン キビキビ
        if self._dragon_ok:
            try:
                drch = dragon_hack.apply(
                    d, self.chk_dragon_snappy.isChecked())
                if drch:
                    applied.append(t("hack_dialog.applied.dragon", "ドラゴン: {changes}").format(changes=" / ".join(drch)))
            except dragon_hack.DragonHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.dragon", "ドラゴン改造失敗"), str(e))

        # ドラゴン/サラマンダー共通 火吐き開始待ち
        if getattr(self, "_shared_flame_wait_ok", False):
            try:
                sfch = shared_flame_start_wait.apply(
                    d, self.spin_shared_flame_wait.value())
                if sfch:
                    applied.append(t("hack_dialog.applied.shared_flame_wait", "火吐き開始待ち: {changes}").format(changes=" / ".join(sfch)))
            except shared_flame_start_wait.SharedFlameStartWaitError as e:
                QMessageBox.warning(self, t("hack_dialog.error.shared_flame_wait", "火吐き開始待ち設定失敗"), str(e))

        # 共通移動速度 (Golem/Dragon/Gargoyle)
        if self._golem_spd_ok:
            try:
                gsch = golem_speed.apply_shared_walk(
                    d, self.combo_shared_walk.currentData())
                if gsch:
                    applied.append(t("hack_dialog.applied.shared_walk", "共通移動速度: {changes}").format(changes=" / ".join(gsch)))
            except golem_speed.GolemSpeedError as e:
                QMessageBox.warning(self, t("hack_dialog.error.shared_walk", "共通移動速度改造失敗"), str(e))

        # ゴースト＆ヌエル移動速度
        if self._neul_ghost_spd_ok:
            try:
                ngch = neul_ghost_speed.apply(
                    d, self.combo_neul_ghost_speed.currentData())
                if ngch:
                    applied.append(t("hack_dialog.applied.neul_ghost", "ゴースト＆ヌエル: {changes}").format(changes=" / ".join(ngch)))
            except neul_ghost_speed.NeulGhostSpeedError as e:
                QMessageBox.warning(self, t("hack_dialog.error.neul_ghost", "ゴースト＆ヌエル速度改造失敗"), str(e))

        # スパークボール移動速度
        if self._spark_ball_spd_ok:
            try:
                sbch = spark_ball_speed.apply(
                    d, self.combo_spark_ball_speed.currentData())
                if sbch:
                    applied.append(t("hack_dialog.applied.spark_ball", "スパークボール: {changes}").format(changes=" / ".join(sbch)))
            except spark_ball_speed.SparkBallSpeedError as e:
                QMessageBox.warning(self, t("hack_dialog.error.spark_ball", "スパークボール速度改造失敗"), str(e))

        # 強化スパークボール
        if getattr(self, "_spark_ball_variant_ok", False):
            try:
                selected_digits = self._selected_spark_pause_digits()
                sbvch = spark_ball_variant.apply(
                    d,
                    pause_digits=selected_digits,
                    reverse_digits=self._selected_spark_reverse_digits(),
                    transparency_period=self.combo_spark_transparency.currentData(),
                )
                if sbvch:
                    applied.append(t("hack_dialog.applied.spark_ball_variant", "強化スパークボール: {changes}").format(changes=" / ".join(sbvch)))
            except spark_ball_variant.SparkBallVariantError as e:
                QMessageBox.warning(self, t("hack_dialog.error.spark_ball_variant", "強化スパークボール設定失敗"), str(e))
                return

        if getattr(self, "_phantom_preset_ok", False):
            try:
                phantom_changes = phantom_preset_runtime.apply_settings(
                    d,
                    self._phantom_group_settings_from_ui(),
                )
                if phantom_changes:
                    group_summaries = []
                    for index, group in enumerate(
                        self._phantom_group_settings_from_ui()
                    ):
                        group_summaries.append(
                            t(
                                "hack_dialog.applied.phantom_preset.group",
                                "{group}: speed=${speed:02X}, amplitude={amplitude}%, start={phase}",
                            ).format(
                                group=phantom_preset_runtime.GROUP_NAMES[index],
                                speed=group["speed_value"],
                                amplitude=group["amplitude_percent"],
                                phase=group["phase_offset"],
                            )
                        )
                    applied.append(
                        t(
                            "hack_dialog.applied.phantom_preset",
                            "Phantom presets: {settings}",
                        ).format(settings=" / ".join(group_summaries))
                    )
            except phantom_preset_runtime.PhantomPresetRuntimeError as e:
                QMessageBox.warning(
                    self,
                    t(
                        "hack_dialog.error.phantom_preset",
                        "Phantom Preset settings failed",
                    ),
                    str(e),
                )
                return

        if getattr(self, "_neul_ab_ok", False):
            try:
                neul_ab_changes = neul84_runtime.apply_settings(
                    d,
                    self._neul_ab_group_settings_from_ui(),
                )
                if neul_ab_changes:
                    summaries = []
                    for index, group in enumerate(self._neul_ab_group_settings_from_ui()):
                        summaries.append(t(
                            "hack_dialog.applied.neul_ab.group",
                            "{group}: 本体=${body:02X}、間隔={interval}、弾=${bullet:02X}",
                        ).format(
                            group=neul84_runtime.GROUP_NAMES[index],
                            body=group["body_speed"],
                            interval=group["fire_interval"],
                            bullet=group["bullet_speed"],
                        ))
                    applied.append(t("hack_dialog.applied.neul_ab", "ヌエル強化版: {settings}").format(settings=" / ".join(summaries)))
            except neul84_runtime.Neul84RuntimeError as e:
                QMessageBox.warning(self, t("hack_dialog.error.neul_ab", "ヌエル強化版設定失敗"), str(e))
                return

        if getattr(self, "_ghost_ab_ok", False):
            try:
                ghost_ab_changes = ghostb0_runtime.apply_settings(
                    d,
                    self._ghost_ab_group_settings_from_ui(),
                )
                if ghost_ab_changes:
                    summaries = []
                    for index, group in enumerate(self._ghost_ab_group_settings_from_ui()):
                        summaries.append(t(
                            "hack_dialog.applied.ghost_ab.group",
                            "{group}: 本体=${body:02X}、間隔={interval}、弾=${bullet:02X}、方向={direction}",
                        ).format(
                            group=ghostb0_runtime.GROUP_NAMES[index],
                            body=group["body_speed"],
                            interval=group["fire_interval"],
                            bullet=group["bullet_speed"],
                            direction=group["fire_direction"],
                        ))
                    applied.append(t("hack_dialog.applied.ghost_ab", "ゴースト強化版: {settings}").format(settings=" / ".join(summaries)))
            except ghostb0_runtime.GhostB0RuntimeError as e:
                QMessageBox.warning(self, t("hack_dialog.error.ghost_ab", "ゴースト強化版設定失敗"), str(e))
                return

        # デーモンヘッド キビキビ
        if self._demonhead_ok:
            try:
                dhch = demonhead_hack.apply(
                    d, self.chk_demonhead_snappy.isChecked())
                if dhch:
                    applied.append(t("hack_dialog.applied.demonhead", "デーモンヘッド: {changes}").format(changes=" / ".join(dhch)))
            except demonhead_hack.DemonheadHackError as e:
                QMessageBox.warning(self, t("hack_dialog.error.demonhead", "デーモンヘッド改造失敗"), str(e))

        if getattr(self, "_cs_ok", False):
            preset_id = self._combo_data(self.combo_clearscreen)
            name = self.combo_clearscreen.currentText()
            cur = clearscreen_hack.current_preset_id(d)
            if preset_id != cur:
                try:
                    clearscreen_hack.apply_preset(d, preset_id)
                    applied.append(t("hack_dialog.applied.clear_screen_char", "クリア画面キャラ → {name}").format(name=name))
                except clearscreen_hack.ClearScreenHackError as e:
                    QMessageBox.warning(self, t("hack_dialog.error.clear_screen", "クリア画面改造失敗"), str(e))

        # ステージ外枠
        if getattr(self, "_stage_frame_ok", False):
            want = self.chk_stage_frame_white.isChecked()
            try:
                sfch = stage_frame.apply(d, want, self.rom.base_region())
                if sfch:
                    applied.append(t("hack_dialog.applied.stage_frame", "ステージ外枠: {changes}").format(changes=" / ".join(sfch)))
            except stage_frame.StageFrameError as e:
                QMessageBox.warning(self, t("hack_dialog.error.stage_frame", "ステージ外枠 設定失敗"), str(e))

        # 原作バグ回避: 横穴侵入安定化
        if getattr(self, "_gapfix_ok", False):
            want = self.chk_gapfix.isChecked()
            try:
                gch = gap_fix.apply(d, want, self.spin_gapfix_frames.value())
                if gch:
                    applied.append(
                        t("hack_dialog.applied.gap_fix", "横穴侵入安定化 {state}").format(state=("ON" if want else "OFF")))
            except gap_fix.GapFixError as e:
                QMessageBox.warning(self, t("hack_dialog.error.gap_fix", "横穴侵入安定化 失敗"), str(e))

        # 暗闇テンポ (全体共通)
        if getattr(self, "_dark_tempo_ok", False):
            lf = self.spin_dark_light.value()
            df = self.spin_dark_dark.value()
            try:
                if (lf, df) != room_flags.get_tempo(d):
                    room_flags.set_tempo(d, lf, df)
                    applied.append(t("hack_dialog.applied.dark_tempo", "暗闇テンポ → 明{light}/暗{dark}フレーム").format(light=lf, dark=df))
            except room_flags.RoomFlagError as e:
                QMessageBox.warning(self, t("hack_dialog.error.dark_tempo", "暗闇テンポ設定 失敗"), str(e))

        panel_variant_settings = self._panel_variant_settings_from_ui()
        if self._app_config is not None:
            old_panel_variant_settings = normalize_panel_variant_settings(
                self._app_config.get("panel_variant_settings")
            )
            if panel_variant_settings != old_panel_variant_settings:
                self._app_config["panel_variant_settings"] = panel_variant_settings
                try:
                    from ..core.config import save_config
                    save_config(self._app_config)
                except Exception:
                    pass
                applied.append(t("hack_dialog.setting.panel_variant", "パネルモンスター A/B/C/D共通値"))

        if applied:
            QMessageBox.information(
                self,
                t("hack_dialog.apply.complete.title", "適用完了"),
                t("hack_dialog.apply.complete.header", "以下の項目を変更しました:\n\n")
                + "\n".join(t("common.bullet_item", "・{item}").format(item=a) for a in applied)
                + t("hack_dialog.apply.complete.footer", "\n\n※ 改造ROMとして保存しないと永続化されません。")
            )
        else:
            QMessageBox.information(
                self,
                t("hack_dialog.apply.no_changes.title", "変更なし"),
                t("hack_dialog.apply.no_changes.body", "書き換えられた箇所はありません。"),
            )
        if applied:
            parent = self.parent()
            cb = getattr(parent, "_on_hack_dialog_applied", None)
            if callable(cb):
                cb()
        return bool(applied)

    def _apply_and_close(self):
        self._apply_changes()
        self.accept()

    def _on_revert(self):
        ans = QMessageBox.question(
            self,
            t("common.confirm", "確認"),
            t(
                "hack_dialog.revert.confirm.body",
                "このダイアログで設定した項目を全てデフォルト（オリジナル値）に戻します。\n"
                "適用するには [適用] または [OK] を押してください。\n\n"
                "続行しますか？",
            ),
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return
        self.spin_stage.setValue(1)
        self.spin_continue.setValue(41)
        if getattr(self, "_warp_feather_ok", False):
            self.spin_warp_feather.setValue(warp_feather.ORIGINAL_STEPS)
        if getattr(self, "_initial_magic_ok", False):
            self.spin_initial_magic_max.setValue(initial_magic.ORIGINAL_MAX)
            self.edit_initial_magic.setText(initial_magic.ORIGINAL_PATTERN)
        if getattr(self, "_initial_lives_ok", False):
            self.spin_initial_lives.setValue(initial_lives.ORIGINAL_LIVES)
        if getattr(self, "_time_rate_ok", False):
            self.spin_time_fast.setValue(time_decrease_hack.ORIGINAL_VALUES[0])
            self.spin_time_normal.setValue(time_decrease_hack.ORIGINAL_VALUES[1])
            self.spin_time_slow.setValue(time_decrease_hack.ORIGINAL_VALUES[2])
        if getattr(self, "_wall_color_ok", False):
            for combo, value in zip(self.combo_wall_colors, wall_color_hack.ORIGINAL_VALUES):
                self._set_combo_data(combo, value)
        if self._walk_ok:
            for i in range(self.combo_walk.count()):
                if abs(self.combo_walk.itemData(i) - 1.0) < 1e-6:
                    self.combo_walk.setCurrentIndex(i)
                    break
        if self._pm_ok:
            self.spin_pm.setValue(panel_monster_hack.ORIG_THRESHOLD)
            if getattr(self, "_pm_bullet_speed_ok", False):
                self.chk_pm_bullet_speed_fix.setChecked(False)
                self._set_combo_data(
                    self.combo_pm_bullet_speed_fix,
                    panel_bullet_speed_fix.SLOW_VALUE,
                )
        default_panel_variant = normalize_panel_variant_settings({})
        for key, (combo, spin) in getattr(self, "_panel_variant_controls", {}).items():
            self._set_combo_data(combo, default_panel_variant[f"{key}_speed"])
            spin.setValue(default_panel_variant[f"{key}_interval"])
        if self._golem_ok:
            self.chk_golem_snappy.setChecked(False)
        if self._gargoyle_ok:
            self.chk_gargoyle_snappy.setChecked(False)
            self.spin_gargoyle_cooldown.setValue(0x50)
        if getattr(self, "_gargoyle_variant_ok", False):
            self._set_combo_data(
                self.combo_gargoyle_variant_speed,
                gargoyle_variant.DEFAULT_SPEED_PRESET,
            )
            self.spin_gargoyle_variant_inter_shot.setValue(
                gargoyle_variant.DEFAULT_INTER_SHOT_FRAMES
            )
            self.spin_gargoyle_variant_cooldown.setValue(
                gargoyle_variant.DEFAULT_COOLDOWN_FRAMES
            )
            self._set_combo_data(
                self.combo_gargoyle_variant_b_speed,
                gargoyle_variant.DEFAULT_SPEED_PRESET,
            )
            self.spin_gargoyle_variant_b_inter_shot.setValue(
                gargoyle_variant.DEFAULT_INTER_SHOT_FRAMES
            )
            self.spin_gargoyle_variant_b_cooldown.setValue(
                gargoyle_variant.DEFAULT_COOLDOWN_FRAMES
            )
        if self._dragon_ok:
            self.chk_dragon_snappy.setChecked(False)
        if self._golem_spd_ok:
            for i in range(self.combo_shared_walk.count()):
                if abs(self.combo_shared_walk.itemData(i) - 1.0) < 1e-6:
                    self.combo_shared_walk.setCurrentIndex(i)
                    break
        if self._neul_ghost_spd_ok:
            for i in range(self.combo_neul_ghost_speed.count()):
                if abs(self.combo_neul_ghost_speed.itemData(i) - 1.0) < 1e-6:
                    self.combo_neul_ghost_speed.setCurrentIndex(i)
                    break
        if self._spark_ball_spd_ok:
            for i in range(self.combo_spark_ball_speed.count()):
                if abs(self.combo_spark_ball_speed.itemData(i) - 1.0) < 1e-6:
                    self.combo_spark_ball_speed.setCurrentIndex(i)
                    break
        if getattr(self, "_spark_ball_variant_ok", False):
            defaults = set(spark_ball_variant.DEFAULT_PAUSE_DIGITS)
            for digit, chk in enumerate(self.chk_spark_pause_digits):
                chk.setChecked(digit in defaults)
            reverse_defaults = set(spark_ball_variant.DEFAULT_REVERSE_DIGITS)
            for digit, chk in enumerate(self.chk_spark_reverse_digits):
                chk.setChecked(digit in reverse_defaults)
            self._set_combo_data(
                self.combo_spark_transparency,
                spark_ball_variant.DEFAULT_TRANSPARENCY_PERIOD,
            )
        if getattr(self, "_phantom_preset_ok", False):
            for speed, amplitude, phase in self._phantom_preset_controls:
                speed.setValue(phantom_preset_runtime.DEFAULT_SPEED_VALUE)
                self._set_combo_data(
                    amplitude,
                    phantom_preset_runtime.DEFAULT_AMPLITUDE_PERCENT,
                )
                phase.setValue(phantom_preset_runtime.DEFAULT_PHASE_OFFSET)
        if getattr(self, "_neul_ab_ok", False):
            for body_speed, fire_interval, bullet_speed in self._neul_ab_controls:
                self._set_combo_data(body_speed, neul84_runtime.DEFAULT_BODY_SPEED)
                fire_interval.setValue(neul84_runtime.DEFAULT_FIRE_INTERVAL)
                self._set_combo_data(bullet_speed, neul84_runtime.DEFAULT_BULLET_SPEED)
        if getattr(self, "_ghost_ab_ok", False):
            for body_speed, fire_interval, bullet_speed, fire_direction in self._ghost_ab_controls:
                self._set_combo_data(body_speed, ghostb0_runtime.DEFAULT_BODY_SPEED)
                fire_interval.setValue(ghostb0_runtime.DEFAULT_FIRE_INTERVAL)
                self._set_combo_data(bullet_speed, ghostb0_runtime.DEFAULT_BULLET_SPEED)
                self._set_combo_data(fire_direction, ghostb0_runtime.DEFAULT_FIRE_DIRECTION)
        if self._demonhead_ok:
            self.chk_demonhead_snappy.setChecked(False)
        if getattr(self, "_cs_ok", False):
            self._set_combo_data(self.combo_clearscreen, "fairy_original")
        if getattr(self, "_stage_frame_ok", False):
            self.chk_stage_frame_white.setChecked(False)
        if getattr(self, "_gapfix_ok", False):
            self.chk_gapfix.setChecked(False)
        if getattr(self, "_dark_tempo_ok", False):
            self.spin_dark_light.setValue(45)
            self.spin_dark_dark.setValue(100)
