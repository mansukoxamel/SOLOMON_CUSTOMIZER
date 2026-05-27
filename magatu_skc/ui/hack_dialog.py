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
from ..core import salamander_hack
from ..core import panel_monster_hack
from ..core import panel_bullet_speed_fix
from ..core import demo_stage_hack
from ..core import dragon_hack
from ..core import demonhead_hack
from ..core import golem_hack
from ..core import golem_speed
from ..core import neul_ghost_speed
from ..core import spark_ball_speed
from ..core import spark_ball_variant
from ..core import gargoyle_hack
from ..core import gargoyle_variant
from ..core import clearscreen_hack
from ..core import clear_message
from ..core import demo_input
from ..core import enemy_drop
from ..core import gap_fix
from ..core import room_flags
from ..core import warp_feather
from ..core import initial_magic
from ..core import initial_lives
from ..core import time_decrease_hack
from ..core import wall_color_hack
from ..nes import palette as nes_palette


def _enemy_group_pixmap(tile_renderer, config, enemy_code: int) -> QPixmap:
    if tile_renderer is None or config is None:
        return QPixmap()
    from PyQt5.QtGui import QImage, QPainter
    anim = config.enemy_map.get(enemy_code, 0)
    try:
        sprite = tile_renderer.get_tile_image(anim, 0, transparent=True)
    except Exception:
        return QPixmap()
    bg = QImage(36, 36, QImage.Format_ARGB32)
    bg.fill(QColor(20, 20, 20))
    painter = QPainter(bg)
    scaled = sprite.scaled(36, 36, Qt.KeepAspectRatio, Qt.FastTransformation)
    painter.drawImage((36 - scaled.width()) // 2, (36 - scaled.height()) // 2, scaled)
    painter.end()
    return QPixmap.fromImage(bg)


def _setup_enemy_group(dialog, group, form, sort_key: int, enemy_codes=()):
    group.setProperty("enemy_sort_key", sort_key)
    if not enemy_codes:
        return
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 2)
    lay.setSpacing(4)
    for code in enemy_codes:
        pix = _enemy_group_pixmap(dialog.tile_renderer, dialog.config, code)
        if pix.isNull():
            continue
        lbl = QLabel()
        lbl.setFixedSize(36, 36)
        lbl.setPixmap(pix)
        lbl.setToolTip(f"0x{code:02X}")
        lay.addWidget(lbl)
    if lay.count() <= 0:
        return
    lay.addStretch(1)
    form.addRow(row)


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
    ):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self._view_mode = view_mode
        self.setWindowTitle("敵" if view_mode == "enemy" else "ゲーム挙動改造")
        self.resize(940, 720)
        self.rom = rom
        self._app_config = app_config   # サイズ/位置 復元用 (None=保存しない)
        self._initial_level_no = initial_level_no
        self.tile_renderer = tile_renderer
        self.config = config

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
                "敵の挙動に関係する既知アドレスを書き換えます。<br>"
                "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
                "保存ボタンを押すまでは元に戻せます（再読込で復元可）。"
            )
        else:
            info_text = (
                "ROMの既知アドレスを書き換えてゲーム挙動を変更します。<br>"
                "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
                "保存ボタンを押すまでは元に戻せます（再読込で復元可）。"
            )
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        # ====== 開始ステージ ======
        stage_group = QGroupBox("開始ステージ")
        stage_group.setProperty("settings_category", "基本")
        sf = QFormLayout(stage_group)
        self.spin_stage = QSpinBox()
        self.spin_stage.setRange(1, 53)
        self.spin_stage.setValue((rom.data[0x1145] if 0x1145 < len(rom.data) else 0) + 1)
        sf.addRow("開始ステージ:", self.spin_stage)
        layout.addWidget(stage_group)

        # ====== コンティニュー上限ステージ ======
        cont_group = QGroupBox("コンティニュー上限")
        cont_group.setProperty("settings_category", "基本")
        cf = QFormLayout(cont_group)
        self._continue_offset = hack_data.get_continue_max_offset(rom.region)
        self.spin_continue = QSpinBox()
        self.spin_continue.setRange(1, 53)
        cur = rom.data[self._continue_offset] if self._continue_offset < len(rom.data) else 0x28
        self.spin_continue.setValue(cur + 1)
        cf.addRow("コンティニュー上限:", self.spin_continue)
        layout.addWidget(cont_group)

        # ====== ワープ羽 ======
        wftr_group = QGroupBox("ワープ羽")
        wftr_group.setProperty("settings_category", "基本")
        wftr = QFormLayout(wftr_group)
        self._warp_feather_ok = False
        self.spin_warp_feather = QSpinBox()
        self.spin_warp_feather.setRange(
            warp_feather.MIN_STEPS, warp_feather.MAX_STEPS)
        self.spin_warp_feather.setSuffix(" 面分")
        try:
            self.spin_warp_feather.setValue(
                warp_feather.current_steps(rom.data))
            self._warp_feather_ok = True
        except warp_feather.WarpFeatherError as e:
            self.spin_warp_feather.setValue(warp_feather.ORIGINAL_STEPS)
            self.spin_warp_feather.setEnabled(False)
            note = QLabel(f"⚠ 検証失敗のため無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wftr.addRow(note)
        wftr.addRow("取得後の進行数:", self.spin_warp_feather)
        wftr_hint = QLabel(
            "原作は6面分。実コードは $C69F の #$05 と通常クリアの +1 で合計6。"
            "この値は $28 bit6 ルートのクリア進行数を変えます。")
        wftr_hint.setWordWrap(True)
        wftr_hint.setStyleSheet("color:#888; font-size:11px;")
        wftr.addRow(wftr_hint)
        layout.addWidget(wftr_group)

        # ====== 初期魔法 (共通) ======
        im_group = QGroupBox("初期魔法（共通）")
        im_group.setProperty("settings_category", "プレイヤー")
        imf = QFormLayout(im_group)
        self._initial_magic_ok = False
        self.spin_initial_magic_max = QSpinBox()
        self.spin_initial_magic_max.setRange(
            initial_magic.MAX_COUNT_MIN, initial_magic.MAX_COUNT_MAX)
        self.spin_initial_magic_max.setToolTip(
            "持てる巻物の最大数。原作は3。0にすると巻物を持てません。")
        self.edit_initial_magic = QLineEdit()
        self.edit_initial_magic.setMaxLength(initial_magic.MAX_PATTERN_CHARS)
        self.edit_initial_magic.setPlaceholderText("例: FFF / SSS / FSFS")
        self.edit_initial_magic.setToolTip(
            "開始時に持っている巻物。F=通常ファイヤー、S=スーパー。"
            "最大8文字。空欄で原作(所持なし)。")
        try:
            max_count, pattern = initial_magic.current(rom.data)
            self.spin_initial_magic_max.setValue(max_count)
            self.edit_initial_magic.setText(pattern)
            self._initial_magic_ok = True
        except initial_magic.InitialMagicError as e:
            self.spin_initial_magic_max.setValue(initial_magic.ORIGINAL_MAX)
            self.spin_initial_magic_max.setEnabled(False)
            self.edit_initial_magic.setEnabled(False)
            note = QLabel(f"⚠ 検証失敗のため無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            imf.addRow(note)
        imf.addRow("最大数:", self.spin_initial_magic_max)
        imf.addRow("初期所持:", self.edit_initial_magic)
        imhint = QLabel(
            "原作は最大3・初期所持なし。例: FFF=通常火球3つ、SSS=超火球3つ。"
            "原作値(最大3・空欄)に戻すと追加フックも復元します。")
        imhint.setWordWrap(True)
        imhint.setStyleSheet("color:#888; font-size:11px;")
        imf.addRow(imhint)
        layout.addWidget(im_group)

        # ====== 初期残数 ======
        lives_group = QGroupBox("初期残数")
        lives_group.setProperty("settings_category", "プレイヤー")
        lives_f = QFormLayout(lives_group)
        self._initial_lives_ok = False
        self.spin_initial_lives = QSpinBox()
        self.spin_initial_lives.setRange(
            initial_lives.MIN_LIVES, initial_lives.MAX_LIVES)
        self.spin_initial_lives.setToolTip(
            "開始時のダーナ残数。原作は3。$0452だけを書き換え、初期魔法の$042Bには影響させません。")
        try:
            self.spin_initial_lives.setValue(
                initial_lives.current(rom.data))
            self._initial_lives_ok = True
        except initial_lives.InitialLivesError as e:
            self.spin_initial_lives.setValue(initial_lives.ORIGINAL_LIVES)
            self.spin_initial_lives.setEnabled(False)
            note = QLabel(f"⚠ 検証失敗のため無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            lives_f.addRow(note)
        lives_f.addRow("開始時の残数:", self.spin_initial_lives)
        lives_hint = QLabel(
            "原作は3。単純な #$03 変更では巻物最大数にも漏れるため、専用フックで残数だけ変更します。")
        lives_hint.setWordWrap(True)
        lives_hint.setStyleSheet("color:#888; font-size:11px;")
        lives_f.addRow(lives_hint)
        layout.addWidget(lives_group)

        # ====== ステージ制限時間 ======
        time_group = QGroupBox("ステージ制限時間")
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
            sp.setToolTip("CPU $9942 のステージ制限時間テーブル値。値が大きいほど短くなります。")
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
            note = QLabel(f"⚠ 検証失敗のため無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            time_f.addRow(note)
        def time_row(sp, label):
            row = QHBoxLayout()
            row.addWidget(sp)
            row.addWidget(label)
            row.addStretch()
            return row

        time_f.addRow("0=速い:", time_row(self.spin_time_fast, self.lbl_time_fast_est))
        time_f.addRow("1=普通:", time_row(self.spin_time_normal, self.lbl_time_normal_est))
        time_f.addRow("2=遅い:", time_row(self.spin_time_slow, self.lbl_time_slow_est))
        time_hint = QLabel("原作値は 速い=$2D / 普通=$22 / 遅い=$19。目安は開始LIFE 10000が0になるまでの時間です。")
        time_hint.setWordWrap(True)
        time_hint.setStyleSheet("color:#888; font-size:11px;")
        time_f.addRow(time_hint)
        self._update_time_rate_estimates()
        layout.addWidget(time_group)

        # ====== ステージ壁色 ======
        wall_group = QGroupBox("ステージ壁色 (1-48面)")
        wall_group.setProperty("settings_category", "画面・演出")
        wall_f = QFormLayout(wall_group)
        self._wall_color_ok = False
        self.combo_wall_colors = []
        try:
            cur_wall_colors = wall_color_hack.current_values(rom.data)
            wall_color_hack.special_values(rom.data)
            self._wall_color_ok = True
        except wall_color_hack.WallColorHackError as e:
            cur_wall_colors = wall_color_hack.ORIGINAL_VALUES
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wall_f.addRow(note)
        grid_wall = QGridLayout()
        for i in range(wall_color_hack.EDIT_COUNT):
            combo = self._make_wall_color_combo(cur_wall_colors[i])
            combo.setToolTip("CPU $9122 の4面単位壁色テーブル値。NESパレット番号です。")
            if not self._wall_color_ok:
                combo.setEnabled(False)
            self.combo_wall_colors.append(combo)
            row = i // 4
            col = (i % 4) * 2
            grid_wall.addWidget(QLabel(f"{wall_color_hack.stage_range_label(i)}面"), row, col)
            grid_wall.addWidget(combo, row, col + 1)
        wall_f.addRow(grid_wall)
        wall_hint = QLabel(
            "4面ごとの壁の基調色です。ROM $9122 の先頭12バイトだけを変更します。"
            "49面以降の特殊値 $80/$80 は触りません。")
        wall_hint.setWordWrap(True)
        wall_hint.setStyleSheet("color:#888; font-size:11px;")
        wall_f.addRow(wall_hint)
        # Wall color editing is handled in PaletteDialog where the shared
        # 64-color picker is available.
        self._wall_color_ok = False
        self.combo_wall_colors = []

        # ====== ダーナ歩行速度 ======
        ws_group = QGroupBox("ダーナ歩行速度")
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
            note = QLabel(f"⚠ 検証失敗のため無効: {e}".split("\n")[0])
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            wf.addRow(note)

        sel_idx = 1  # デフォルト 1.0x
        for i, (m, _r, _l) in enumerate(walk_speed.PRESETS):
            label = f"{m:g}x" + ("（原作）" if abs(m - 1.0) < 1e-6 else "")
            self.combo_walk.addItem(label, m)
            if cur_mult is not None and abs(m - cur_mult) < 0.01:
                sel_idx = i
        self.combo_walk.setCurrentIndex(sel_idx)
        wf.addRow("移動速度:", self.combo_walk)
        hint = QLabel("原作 1.0x = 0.75 px/frame（4コマ歩行アニメと同期した精密値）。"
                      "地上・空中の左右4方向すべてに適用。JP/US 共通。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888; font-size:11px;")
        wf.addRow(hint)
        layout.addWidget(ws_group)

        # ====== サラマンダー強化 (火球発射化) ======
        sala_group = QGroupBox("サラマンダー強化（火球発射化）")
        sala_group.setProperty("settings_category", "敵・AI")
        slf = QFormLayout(sala_group)
        self._sala_ok = False
        try:
            self._sala_region = salamander_hack.detect_region(rom.data)
            self._sala_ok = True
        except salamander_hack.SalamanderHackError as e:
            self._sala_region = None
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            slf.addRow(note)

        self.combo_sala_x = QComboBox()
        self.combo_sala_y = QComboBox()
        for label, val in salamander_hack.XDIST_PRESETS:
            self.combo_sala_x.addItem(label, val)
        for label, val in salamander_hack.YDIST_PRESETS:
            self.combo_sala_y.addItem(label, val)

        if self._sala_ok:
            cx = salamander_hack.current_xdist(rom.data)
            cy = salamander_hack.current_ydist(rom.data)
            for i in range(self.combo_sala_x.count()):
                if self.combo_sala_x.itemData(i) == cx:
                    self.combo_sala_x.setCurrentIndex(i)
            for i in range(self.combo_sala_y.count()):
                if self.combo_sala_y.itemData(i) == cy:
                    self.combo_sala_y.setCurrentIndex(i)
            slf.addRow("反応距離(X):", self.combo_sala_x)
            shint = QLabel(f"判定リージョン: {self._sala_region} / "
                           "SUB_B1E9の攻撃可能距離。サラマンダー/ドラゴンで共有。")
            shint.setWordWrap(True)
            shint.setStyleSheet("color:#888; font-size:11px;")
            slf.addRow(shint)
        else:
            for w in (self.combo_sala_x, self.combo_sala_y):
                w.setEnabled(False)
        self._hidden_sala_group = sala_group

        # ====== パネルモンスター ======
        pm_group = QGroupBox("パネルモンスター")
        pm_group.setProperty("settings_category", "敵・AI")
        pmf = QFormLayout(pm_group)
        _setup_enemy_group(self, pm_group, pmf, 10, (0x24, 0x52, 0x5A))
        self._pm_ok = False
        try:
            pm_region = panel_monster_hack.detect_region(rom.data)
            cur_frames = panel_monster_hack.current_cooldown_frames(rom.data)
            cur_delay = panel_monster_hack.current_fire_delay(rom.data)
            cur_snappy = panel_monster_hack.is_snappy(rom.data)
            self._pm_ok = True
        except panel_monster_hack.PanelMonsterHackError as e:
            cur_frames = panel_monster_hack.ORIG_THRESHOLD
            cur_delay = panel_monster_hack.ORIG_FIRE_DELAY
            cur_snappy = False
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
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
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            pmf.addRow(note)

        self.chk_pm_snappy = QCheckBox("キビキビ動作（発射前の待ちを最小化）")
        self.chk_pm_bullet_speed_fix = QCheckBox("弾の左右速度バグ修正")
        self.combo_pm_bullet_speed_fix = QComboBox()
        self.combo_pm_bullet_speed_fix.addItem("$30/$50（右下$30・左上$50）", panel_bullet_speed_fix.SLOW_VALUE)
        self.combo_pm_bullet_speed_fix.addItem("$3F/$41（右下$3F・左上$41）", panel_bullet_speed_fix.FAST_VALUE)
        self.chk_pm_bullet_speed_fix.toggled.connect(self.combo_pm_bullet_speed_fix.setEnabled)
        self.spin_pm = QSpinBox()
        self.spin_pm.setRange(
            panel_monster_hack.MIN_THRESHOLD,
            panel_monster_hack.MAX_THRESHOLD)
        self.spin_pm.setSuffix(" フレーム")
        if self._pm_ok:
            self.chk_pm_snappy.setChecked(cur_snappy)
            self.spin_pm.setValue(cur_frames)
            self.chk_pm_bullet_speed_fix.setChecked(cur_bullet_speed_fix)
            self._set_combo_data(self.combo_pm_bullet_speed_fix, cur_bullet_speed_value)
            self.combo_pm_bullet_speed_fix.setEnabled(cur_bullet_speed_fix and self._pm_bullet_speed_ok)
            pmf.addRow("クールダウン:", self.spin_pm)
            pmf.addRow(self.chk_pm_snappy)
            pmf.addRow(self.chk_pm_bullet_speed_fix)
            pmf.addRow("修正後の速度:", self.combo_pm_bullet_speed_fix)
            phint = QLabel(f"判定: {pm_region} / 原作 クールダウン192F + 発射前待ち16F。"
                           f"現在の発射前待ち: {cur_delay}F。"
                           "値を小さくすると連射化します。下限32F。"
                           "短すぎる値は複数パネル面で17個のsub-slotを使い切りやすく、"
                           "発射失敗や弾抜けの原因になります。")
            phint.setWordWrap(True)
            phint.setStyleSheet("color:#888; font-size:11px;")
            pmf.addRow(phint)
        else:
            self.chk_pm_snappy.setEnabled(False)
            self.spin_pm.setEnabled(False)
        if not self._pm_bullet_speed_ok:
            self.chk_pm_bullet_speed_fix.setEnabled(False)
            self.combo_pm_bullet_speed_fix.setEnabled(False)
        layout.addWidget(pm_group)

        # ====== デモプレイのステージ ======
        ds_group = QGroupBox("デモプレイのステージ")
        ds_group.setProperty("settings_category", "基本")
        dsf = QFormLayout(ds_group)
        self._ds_ok = False
        try:
            ds_region = demo_stage_hack.detect_region(rom.data)
            cur_stage = demo_stage_hack.current_stage(rom.data)
            self._ds_ok = True
        except demo_stage_hack.DemoStageHackError as e:
            cur_stage = None
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            dsf.addRow(note)

        self.spin_ds = QSpinBox()
        self.spin_ds.setRange(demo_stage_hack.MIN_STAGE,
                              demo_stage_hack.MAX_STAGE)
        self.spin_ds.setSuffix(" 面")
        if self._ds_ok:
            self.spin_ds.setValue(cur_stage or 3)
            dsf.addRow("デモの面:", self.spin_ds)
            dhint = QLabel(
                f"判定: {ds_region} / 原作の既定は3面。"
                "3面以上のみ(内部のX連鎖制約)。録画入力は3面用なので"
                "別面ではDanaが録画通り動く=見た目で別面と分かる。"
                "正規プレイには影響なし。")
            dhint.setWordWrap(True)
            dhint.setStyleSheet("color:#888; font-size:11px;")
            dsf.addRow(dhint)
        else:
            self.spin_ds.setEnabled(False)
        layout.addWidget(ds_group)

        # ====== ゴーレム ======
        golem_group = QGroupBox("ゴーレム")
        golem_group.setProperty("settings_category", "敵・AI")
        glf = QFormLayout(golem_group)
        _setup_enemy_group(self, golem_group, glf, 50, (0x70, 0x74))
        self._golem_ok = False
        try:
            golem_hack.detect_region(rom.data)
            self._golem_ok = True
        except golem_hack.GolemHackError as e:
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            glf.addRow(note)

        self.chk_golem_snappy = QCheckBox(
            "キビキビ動作（視認→即反応・方向転換・移動再開、隙を最小化）")
        if self._golem_ok:
            self.chk_golem_snappy.setChecked(golem_hack.is_snappy(rom.data))
            glf.addRow(self.chk_golem_snappy)
        else:
            self.chk_golem_snappy.setEnabled(False)
        layout.addWidget(golem_group)

        # ====== 共通歩行速度 ======
        shared_speed_group = QGroupBox("ゴーレム/ドラゴン/ガーゴイル歩行速度")
        shared_speed_group.setProperty("settings_category", "敵・AI")
        ssf = QFormLayout(shared_speed_group)
        _setup_enemy_group(self, shared_speed_group, ssf, 55, (0x70, 0x68, 0x78))
        self.combo_shared_walk = QComboBox()
        self._golem_spd_ok = False
        try:
            golem_speed.verify(rom.data)
            self._golem_spd_ok = True
        except golem_speed.GolemSpeedError as e:
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            ssf.addRow(note)
        for m in golem_speed.MULTIPLIERS:
            lab = f"{m:g}x" + ("（原作）" if abs(m - 1.0) < 1e-6 else "")
            self.combo_shared_walk.addItem(lab, m)

        if self._golem_spd_ok:
            csw = golem_speed.current_shared_walk_mult(rom.data)
            for i in range(self.combo_shared_walk.count()):
                if abs(self.combo_shared_walk.itemData(i) - csw) < 0.01:
                    self.combo_shared_walk.setCurrentIndex(i)
                    break
            ssf.addRow("歩行速度:", self.combo_shared_walk)
            sshint = QLabel("Golem/Dragon/Gargoyle の s0 通常歩行が同じ速度で連動します。"
                            "ゴーレム専用の歩行速度・突進速度は混乱を避けるため一旦表示しません。")
            sshint.setWordWrap(True)
            sshint.setStyleSheet("color:#888; font-size:11px;")
            ssf.addRow(sshint)
        else:
            self.combo_shared_walk.setEnabled(False)
        layout.addWidget(shared_speed_group)

        # ====== ゴースト＆ヌエル移動速度 ======
        ng_speed_group = QGroupBox("ゴースト＆ヌエル移動速度")
        ng_speed_group.setProperty("settings_category", "敵・AI")
        ngf = QFormLayout(ng_speed_group)
        _setup_enemy_group(self, ng_speed_group, ngf, 30, (0x34, 0x30))
        self.combo_neul_ghost_speed = QComboBox()
        self._neul_ghost_spd_ok = False
        try:
            neul_ghost_speed.verify(rom.data)
            self._neul_ghost_spd_ok = True
        except neul_ghost_speed.NeulGhostSpeedError as e:
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            ngf.addRow(note)
        for m in neul_ghost_speed.MULTIPLIERS:
            lab = f"{m:g}x" + ("（原作）" if abs(m - 1.0) < 1e-6 else "")
            self.combo_neul_ghost_speed.addItem(lab, m)
        if self._neul_ghost_spd_ok:
            cur_ng = neul_ghost_speed.current_multiplier(rom.data)
            for i in range(self.combo_neul_ghost_speed.count()):
                if abs(self.combo_neul_ghost_speed.itemData(i) - cur_ng) < 0.01:
                    self.combo_neul_ghost_speed.setCurrentIndex(i)
                    break
            ngf.addRow("移動速度:", self.combo_neul_ghost_speed)
            nghint = QLabel(
                "GhostはX方向、NeulはY方向の速度を変更します。"
                "SP1/SP2と通常/noslow版がまとめて同じ倍率で変わります。")
            nghint.setWordWrap(True)
            nghint.setStyleSheet("color:#888; font-size:11px;")
            ngf.addRow(nghint)
        else:
            self.combo_neul_ghost_speed.setEnabled(False)
        layout.addWidget(ng_speed_group)

        # ====== スパークボール移動速度 ======
        sb_speed_group = QGroupBox("スパークボール移動速度")
        sb_speed_group.setProperty("settings_category", "敵・AI")
        sbf = QFormLayout(sb_speed_group)
        _setup_enemy_group(self, sb_speed_group, sbf, 40, (0x28, 0x6A, 0x72))
        self.combo_spark_ball_speed = QComboBox()
        self._spark_ball_spd_ok = False
        try:
            spark_ball_speed.verify(rom.data)
            self._spark_ball_spd_ok = True
        except spark_ball_speed.SparkBallSpeedError as e:
            note = QLabel(f"笞 辟｡蜉ｹ: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            sbf.addRow(note)
        for m in spark_ball_speed.MULTIPLIERS:
            lab = f"{m:g}x" + (" (原作)" if abs(m - 1.0) < 1e-6 else "")
            self.combo_spark_ball_speed.addItem(lab, m)
        if self._spark_ball_spd_ok:
            cur_sb = spark_ball_speed.current_multiplier(rom.data)
            for i in range(self.combo_spark_ball_speed.count()):
                if abs(self.combo_spark_ball_speed.itemData(i) - cur_sb) < 0.01:
                    self.combo_spark_ball_speed.setCurrentIndex(i)
                    break
            sbf.addRow("移動速度:", self.combo_spark_ball_speed)
            sbhint = QLabel(
                "Spark Ball専用の $A9DF/$A9E7 移動差分テーブルを倍率変更します。"
                "通常スパークボールと強化スパークボール(6A/6B/6E/6F)の両方に効きます。")
            sbhint.setWordWrap(True)
            sbhint.setStyleSheet("color:#888; font-size:11px;")
            sbf.addRow(sbhint)
        else:
            self.combo_spark_ball_speed.setEnabled(False)
        layout.addWidget(sb_speed_group)

        # ====== 強化スパークボール ======
        sb_variant_group = QGroupBox("強化スパークボール")
        sb_variant_group.setProperty("settings_category", "敵・AI")
        sbvf = QFormLayout(sb_variant_group)
        _setup_enemy_group(self, sb_variant_group, sbvf, 41, (0x6A, 0x72))
        self._spark_ball_variant_ok = False
        self.chk_spark_pause_digits = []
        self.combo_spark_transparency = QComboBox()
        try:
            pause_digits = set(spark_ball_variant.current_pause_digits(rom.data))
            transparency_period = spark_ball_variant.current_transparency_period(rom.data)
            self._spark_ball_variant_ok = True
        except spark_ball_variant.SparkBallVariantError as e:
            pause_digits = set(spark_ball_variant.DEFAULT_PAUSE_DIGITS)
            transparency_period = spark_ball_variant.DEFAULT_TRANSPARENCY_PERIOD
            note = QLabel(f"無効: {str(e).splitlines()[0]}")
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
        sbvf.addRow("停止するLIFE百の位:", digit_grid)

        for value in spark_ball_variant.TRANSPARENCY_PERIODS:
            self.combo_spark_transparency.addItem(f"${value:02X}", value)
        self._set_combo_data(self.combo_spark_transparency, transparency_period)
        self.combo_spark_transparency.setEnabled(self._spark_ball_variant_ok)
        sbvf.addRow("透明化周期:", self.combo_spark_transparency)

        sbvhint = QLabel(
            "停止型(6A/6B/6E/6F)は選択したLIFE百の位で停止します。"
            "透明型(72/73/76/77)はフレームカウンタのANDマスクで透明化周期を変えます。")
        sbvhint.setWordWrap(True)
        sbvhint.setStyleSheet("color:#888; font-size:11px;")
        sbvf.addRow(sbvhint)
        layout.addWidget(sb_variant_group)

        # ====== デーモンヘッド ======
        demonhead_group = QGroupBox("デーモンヘッド")
        demonhead_group.setProperty("settings_category", "敵・AI")
        dhf = QFormLayout(demonhead_group)
        _setup_enemy_group(self, demonhead_group, dhf, 20, (0x50, 0x54, 0x58))
        self._demonhead_ok = False
        try:
            demonhead_hack.current_wait(rom.data)
            self._demonhead_ok = True
        except demonhead_hack.DemonheadHackError as e:
            note = QLabel(f"笞 辟｡蜉ｹ: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            dhf.addRow(note)
        self.chk_demonhead_snappy = QCheckBox("キビキビ動作（反転後の溜めを最小化）")
        if self._demonhead_ok:
            self.chk_demonhead_snappy.setChecked(
                demonhead_hack.is_snappy(rom.data))
            dhf.addRow(self.chk_demonhead_snappy)
            dhhint = QLabel("Demonheadが増殖/反転した直後の待ち $0F を $01 にします。")
            dhhint.setWordWrap(True)
            dhhint.setStyleSheet("color:#888; font-size:11px;")
            dhf.addRow(dhhint)
        else:
            self.chk_demonhead_snappy.setEnabled(False)
        layout.addWidget(demonhead_group)

        # ====== ガーゴイル ======
        gargoyle_group = QGroupBox("ガーゴイル")
        gargoyle_group.setProperty("settings_category", "敵・AI")
        gyf = QFormLayout(gargoyle_group)
        _setup_enemy_group(self, gargoyle_group, gyf, 70, (0x78, 0x7C))
        self._gargoyle_ok = False
        try:
            gargoyle_hack.detect_region(rom.data)
            self._gargoyle_ok = True
        except gargoyle_hack.GargoyleHackError as e:
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            gyf.addRow(note)

        self.chk_gargoyle_snappy = QCheckBox(
            "キビキビ動作（検知後・発射直前・復帰待ちを最小化）")
        self.spin_gargoyle_cooldown = QSpinBox()
        self.spin_gargoyle_cooldown.setRange(
            gargoyle_hack.COOLDOWN_MIN, gargoyle_hack.COOLDOWN_MAX)
        self.spin_gargoyle_cooldown.setSuffix(" フレーム")
        self.spin_gargoyle_cooldown.setToolTip(
            "発射後に通常行動へ戻るまでの待ち。原作は80F。"
            "1F化は危険なので下限を設けています。")
        if self._gargoyle_ok:
            self.chk_gargoyle_snappy.setChecked(
                gargoyle_hack.is_snappy(rom.data))
            self.spin_gargoyle_cooldown.setValue(
                gargoyle_hack.current_cooldown(rom.data))
            gyf.addRow(self.chk_gargoyle_snappy)
            gyf.addRow("発射後クールダウン:", self.spin_gargoyle_cooldown)
            ghint = QLabel("ONでガーゴイル固有の待ち3箇所を$01にします。"
                           "弾の2発化とは別軸で併用できます。")
            ghint.setWordWrap(True)
            ghint.setStyleSheet("color:#888; font-size:11px;")
            gyf.addRow(ghint)
        else:
            self.chk_gargoyle_snappy.setEnabled(False)
            self.spin_gargoyle_cooldown.setEnabled(False)
        layout.addWidget(gargoyle_group)

        # ====== 強化ガーゴイル ======
        gargoyle_variant_group = QGroupBox("強化ガーゴイル")
        gargoyle_variant_group.setProperty("settings_category", "敵・AI")
        gvf = QFormLayout(gargoyle_variant_group)
        _setup_enemy_group(self, gargoyle_variant_group, gvf, 71, (0x7A, 0x7E))
        self._gargoyle_variant_ok = False
        self.combo_gargoyle_variant_offset = QComboBox()
        try:
            cur_gv_offset = gargoyle_variant.current_second_offset(rom.data)
            self._gargoyle_variant_ok = True
        except gargoyle_variant.GargoyleVariantError as e:
            cur_gv_offset = gargoyle_variant.DEFAULT_SECOND_OFFSET
            note = QLabel(f"無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            gvf.addRow(note)

        for value in gargoyle_variant.SECOND_OFFSET_PRESETS:
            label = f"{value}px" + ("（標準）" if value == gargoyle_variant.DEFAULT_SECOND_OFFSET else "")
            self.combo_gargoyle_variant_offset.addItem(label, value)
        self._set_combo_data(self.combo_gargoyle_variant_offset, cur_gv_offset)
        self.combo_gargoyle_variant_offset.setEnabled(self._gargoyle_variant_ok)
        gvf.addRow("2発目の位置:", self.combo_gargoyle_variant_offset)

        gvhint = QLabel(
            "強化ガーゴイル(7A/7B/7E/7F)の2発目だけを調整します。"
            "1発目は原作の弾生成処理をそのまま使います。")
        gvhint.setWordWrap(True)
        gvhint.setStyleSheet("color:#888; font-size:11px;")
        gvf.addRow(gvhint)
        layout.addWidget(gargoyle_variant_group)

        # ====== ドラゴン ======
        dragon_group = QGroupBox("ドラゴン")
        dragon_group.setProperty("settings_category", "敵・AI")
        drf = QFormLayout(dragon_group)
        _setup_enemy_group(self, dragon_group, drf, 60, (0x68, 0x6C))
        self._dragon_ok = False
        try:
            dragon_hack.detect_region(rom.data)
            self._dragon_ok = True
        except dragon_hack.DragonHackError as e:
            note = QLabel(f"⚠ 無効: {str(e).splitlines()[0]}")
            note.setWordWrap(True)
            note.setStyleSheet("color:#c33;")
            drf.addRow(note)

        self.chk_dragon_snappy = QCheckBox(
            "キビキビ動作（攻撃前の待ちを最小化）")
        if self._dragon_ok:
            self.chk_dragon_snappy.setChecked(
                dragon_hack.is_snappy(rom.data))
            drf.addRow(self.chk_dragon_snappy)
            dhint = QLabel("ONでドラゴン固有の攻撃前待ち1箇所を$01にします。"
                           "サラマンダー共有の火吐き開始waitは変更しません。")
            dhint.setWordWrap(True)
            dhint.setStyleSheet("color:#888; font-size:11px;")
            drf.addRow(dhint)
        else:
            self.chk_dragon_snappy.setEnabled(False)
        layout.addWidget(dragon_group)

        # クリア画面 (THANK YOU DANA) のキャラ差し替え
        cs_group = QGroupBox("クリア画面のキャラ (おめでとう画面の2体)")
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
        csf.addRow("表示キャラ:", self.combo_clearscreen)
        cshint = QLabel(
            "ステージクリア画面で左右に出る2体を差し替え。"
            "全プリセットは速度ゼロ=落下せず置物表示 (ROM解析確定)。")
        cshint.setWordWrap(True)
        cshint.setStyleSheet("color:#888; font-size:11px;")
        csf.addRow(cshint)
        layout.addWidget(cs_group)

        # 原作バグ回避: 落下中の横穴侵入を安定化 (グローバル)
        gf_group = QGroupBox("原作バグ回避")
        gf_group.setProperty("settings_category", "保守・特殊")
        gff = QVBoxLayout(gf_group)
        self.chk_gapfix = QCheckBox(
            "落下中の横穴侵入を安定化（運ゲー解消・左右対応）")
        self.chk_gapfix.setToolTip(
            "上から落ちながら左/右で横穴に入れる時と入れない時がある"
            "原作の挙動(サブピクセル位相依存)を解消し、毎回入れるように\n"
            "します。横穴がある時だけ作用し通常の壁・歩行・着地は原作"
            "どおり(副作用なし、実機確認済)。Mesen解析 asm R182")
        try:
            self.chk_gapfix.setChecked(gap_fix.is_applied(self.rom.data))
            self._gapfix_ok = True
        except gap_fix.GapFixError:
            self._gapfix_ok = False
            self.chk_gapfix.setEnabled(False)
        gff.addWidget(self.chk_gapfix)
        gfhint = QLabel(
            "ソロモンの鍵 積年の謎「横穴に入れる/入れないが運任せ」を"
            "機構解明し回避。詳細 docs/gap_entry_mechanism.html")
        gfhint.setWordWrap(True)
        gfhint.setStyleSheet("color:#888; font-size:11px;")
        gff.addWidget(gfhint)
        layout.addWidget(gf_group)

        # 暗闇テンポ (全体共通)。どの面を暗闇にするかは
        # 「レベル設定」パネルの『この画面を暗闇にする』(部屋別)。
        dk_group = QGroupBox("暗闇テンポ (全体共通・必ず明から開始)")
        dk_group.setProperty("settings_category", "画面・演出")
        dkf = QFormLayout(dk_group)
        self.spin_dark_light = QSpinBox()
        self.spin_dark_light.setRange(1, 200)
        self.spin_dark_light.setSuffix(" フレーム")
        self.spin_dark_dark = QSpinBox()
        self.spin_dark_dark.setRange(1, 240)
        self.spin_dark_dark.setSuffix(" フレーム")
        try:
            lf, df = room_flags.get_tempo(self.rom.data)
            self.spin_dark_light.setValue(lf)
            self.spin_dark_dark.setValue(df)
            self._dark_tempo_ok = True
        except room_flags.RoomFlagError:
            self._dark_tempo_ok = False
            self.spin_dark_light.setEnabled(False)
            self.spin_dark_dark.setEnabled(False)
        dkf.addRow("明るい (見える):", self.spin_dark_light)
        dkf.addRow("暗い (見えない):", self.spin_dark_dark)
        dkhint = QLabel(
            "60フレーム≒1秒。既定: 明45/暗100。"
            "暗闇面を1つでも設定して保存すると有効。")
        dkhint.setWordWrap(True)
        dkhint.setStyleSheet("color:#888; font-size:11px;")
        dkf.addRow(dkhint)
        layout.addWidget(dk_group)

        related_group = QGroupBox("関連編集")
        related_group.setProperty("settings_category", "敵以外")
        related_layout = QVBoxLayout(related_group)

        self.btn_enemy_drop = QPushButton("敵ドロップ編集")
        self.btn_enemy_drop.setToolTip(
            "敵を炎で倒した時に出る効果(スコア/1UP/特殊等)と確率を"
            "グローバルに編集 ($C293)。通常アイテムIDではない点に注意")
        self.btn_enemy_drop.clicked.connect(self._on_show_enemy_drop)
        related_layout.addWidget(self.btn_enemy_drop)

        self.btn_demo_input = QPushButton("デモ操作編集")
        self.btn_demo_input.setToolTip(
            "タイトル放置で流れるデモの操作(34ステップ固定)を編集。"
            "各ステップ=入力を何フレーム続けるか。録画不要・原作方式手入力"
            "($CF9A/$CFBC、JP専用)")
        self.btn_demo_input.clicked.connect(self._on_show_demo_input)
        related_layout.addWidget(self.btn_demo_input)

        self.btn_clear_msg = QPushButton("クリア画面メッセージ編集")
        self.btn_clear_msg.setToolTip(
            "ステージクリア後の『おめでとう画面』3行を編集。"
            "英大文字+スペース、原作と同字数まで(JP専用・同字数置換)")
        self.btn_clear_msg.clicked.connect(self._on_show_clear_message)
        related_layout.addWidget(self.btn_clear_msg)

        self.btn_special_proc = QPushButton("特殊処理ビューア")
        self.btn_special_proc.setToolTip(
            "各ステージにハードコードされた特殊処理 (Per-Room Special Process) を表示。\n"
            "壊せる白壁・マイティボンジャック・ソロモン封印・エンディング処理などはここで実装されている。\n"
            "読込専用。"
        )
        self.btn_special_proc.clicked.connect(self._on_show_special_process)
        related_layout.addWidget(self.btn_special_proc)
        layout.addWidget(related_group)

        # 補助ボタン
        helper_row = QHBoxLayout()
        self.btn_export_global = QPushButton("共通設定をエクスポート...")
        self.btn_export_global.setToolTip("このダイアログの共通設定をJSONファイルに保存します")
        self.btn_export_global.clicked.connect(self._on_export_global_settings)
        helper_row.addWidget(self.btn_export_global)
        self.btn_import_global = QPushButton("共通設定をインポート...")
        self.btn_import_global.setToolTip("JSONファイルから共通設定を読み込み、画面の値に反映します")
        self.btn_import_global.clicked.connect(self._on_import_global_settings)
        helper_row.addWidget(self.btn_import_global)
        helper_row.addSpacing(16)
        self.btn_revert = QPushButton("オリジナル値に戻す")
        self.btn_revert.setToolTip("このダイアログで設定した項目を全てデフォルトに戻します")
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
            "強化スパークボール",
            "停止するLIFE百の位は最大4個までです。",
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
        from .enemy_drop_dialog import EnemyDropDialog
        from ..core import enemy_drop as _ed
        o, n = _ed.OFF_C293, _ed.LEN_C293
        before = bytes(self.rom.data[o:o + n])
        try:
            dlg = EnemyDropDialog(self.rom.data, parent=self)
        except _ed.EnemyDropError as e:
            QMessageBox.critical(self, "敵ドロップ編集 不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o:o + n]) != before:
            self._mark_parent_dirty("敵ドロップ効果表 $C293 書換")

    def _on_show_demo_input(self):
        from .demo_input_dialog import DemoInputDialog
        from ..core import demo_input as _di
        o0, o1 = _di.OFF_WAIT, _di.OFF_JOY + _di.STEPS
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = DemoInputDialog(self.rom.data, parent=self)
        except _di.DemoInputError as e:
            QMessageBox.critical(self, "デモ操作編集 不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._mark_parent_dirty("デモ操作データ ($CF9A/$CFBC) 書換")

    def _on_show_clear_message(self):
        from .clear_message_dialog import ClearMessageDialog
        from ..core import clear_message as _cm
        o0 = _cm.MESSAGES[0]["off"]
        last = _cm.MESSAGES[-1]
        o1 = last["off"] + 3 + last["count"] + 1
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = ClearMessageDialog(self.rom.data, parent=self)
        except _cm.ClearMessageError as e:
            QMessageBox.critical(self, "クリア画面メッセージ編集 不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._mark_parent_dirty("クリア画面メッセージ ($94DB/$94ED/$9507) 書換")

    def _on_show_special_process(self):
        from .special_process_dialog import SpecialProcessDialog
        dlg = SpecialProcessDialog(
            self.rom,
            initial_level_no=self._initial_level_no,
            parent=self,
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
            return "目安: 減らない"
        total = int(round(seconds))
        minutes, sec = divmod(total, 60)
        if minutes:
            return f"目安: 約{minutes}分{sec:02d}秒"
        return f"目安: 約{sec}秒"

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

    def _collect_global_settings(self) -> dict:
        """現在の画面値をROM非依存のJSON設定として集める。"""
        settings = {
            "start_stage": self.spin_stage.value(),
            "continue_max_stage": self.spin_continue.value(),
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
            "wall_colors_1_48": [self._combo_data(c) for c in self.combo_wall_colors],
            "walk_speed_multiplier": self._combo_data(self.combo_walk),
            "salamander_xdist": self._combo_data(self.combo_sala_x),
            "salamander_ydist": self._combo_data(self.combo_sala_y),
            "panel_monster_cooldown_frames": self.spin_pm.value(),
            "panel_monster_snappy": self.chk_pm_snappy.isChecked(),
            "panel_bullet_speed_fix_enabled": self.chk_pm_bullet_speed_fix.isChecked(),
            "panel_bullet_speed_fix_value": self._combo_data(self.combo_pm_bullet_speed_fix),
            "demo_stage": self.spin_ds.value(),
            "golem_snappy": self.chk_golem_snappy.isChecked(),
            "gargoyle_snappy": self.chk_gargoyle_snappy.isChecked(),
            "gargoyle_cooldown_frames": self.spin_gargoyle_cooldown.value(),
            "gargoyle_variant_second_offset": self._combo_data(self.combo_gargoyle_variant_offset),
            "dragon_snappy": self.chk_dragon_snappy.isChecked(),
            "shared_monster_walk_multiplier": self._combo_data(self.combo_shared_walk),
            "neul_ghost_speed_multiplier": self._combo_data(self.combo_neul_ghost_speed),
            "spark_ball_speed_multiplier": self._combo_data(self.combo_spark_ball_speed),
            "spark_ball_pause_digits": self._selected_spark_pause_digits(),
            "spark_ball_transparency_period": self._combo_data(self.combo_spark_transparency),
            "demonhead_snappy": self.chk_demonhead_snappy.isChecked(),
            "clear_screen_preset": self._combo_data(self.combo_clearscreen),
            "gap_fix_enabled": self.chk_gapfix.isChecked(),
            "dark_light_frames": self.spin_dark_light.value(),
            "dark_dark_frames": self.spin_dark_dark.value(),
        }
        supported = {
            "warp_feather": bool(getattr(self, "_warp_feather_ok", False)),
            "initial_magic": bool(getattr(self, "_initial_magic_ok", False)),
            "initial_lives": bool(getattr(self, "_initial_lives_ok", False)),
            "time_rate": bool(getattr(self, "_time_rate_ok", False)),
            "wall_colors": bool(getattr(self, "_wall_color_ok", False)),
            "walk_speed": bool(getattr(self, "_walk_ok", False)),
            "salamander": bool(getattr(self, "_sala_ok", False)),
            "panel_monster": bool(getattr(self, "_pm_ok", False)),
            "panel_bullet_speed_fix": bool(getattr(self, "_pm_bullet_speed_ok", False)),
            "demo_stage": bool(getattr(self, "_ds_ok", False)),
            "golem": bool(getattr(self, "_golem_ok", False)),
            "gargoyle": bool(getattr(self, "_gargoyle_ok", False)),
            "gargoyle_variant": bool(getattr(self, "_gargoyle_variant_ok", False)),
            "dragon": bool(getattr(self, "_dragon_ok", False)),
            "golem_speed": bool(getattr(self, "_golem_spd_ok", False)),
            "neul_ghost_speed": bool(getattr(self, "_neul_ghost_spd_ok", False)),
            "spark_ball_speed": bool(getattr(self, "_spark_ball_spd_ok", False)),
            "spark_ball_variant": bool(getattr(self, "_spark_ball_variant_ok", False)),
            "demonhead": bool(getattr(self, "_demonhead_ok", False)),
            "clear_screen": bool(getattr(self, "_cs_ok", False)),
            "gap_fix": bool(getattr(self, "_gapfix_ok", False)),
            "dark_tempo": bool(getattr(self, "_dark_tempo_ok", False)),
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
        """JSON設定を画面値へ反映する。ROMへはまだ書き込まない。"""
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

        def set_spark_pause_digits(key, label):
            if not has(key) or not getattr(self, "_spark_ball_variant_ok", False):
                return
            old = self._selected_spark_pause_digits()
            try:
                selected = spark_ball_variant.normalize_pause_digits(settings[key])
            except (TypeError, ValueError, spark_ball_variant.SparkBallVariantError):
                return
            visible = set(selected)
            for i, chk in enumerate(self.chk_spark_pause_digits):
                chk.setChecked(i in visible)
            if self._selected_spark_pause_digits() != old:
                changed.append(label)

        def set_combo(key, combo, label):
            if has(key) and combo.isEnabled():
                old = combo.currentIndex()
                if self._set_combo_data(combo, settings[key]) and combo.currentIndex() != old:
                    changed.append(label)

        set_spin("start_stage", self.spin_stage, "開始ステージ")
        set_spin("continue_max_stage", self.spin_continue, "コンティニュー上限")
        set_spin("warp_feather_steps", self.spin_warp_feather, "ワープ羽")
        set_spin("initial_magic_max", self.spin_initial_magic_max, "初期魔法 最大数")
        if has("initial_magic_pattern") and self.edit_initial_magic.isEnabled():
            old = self.edit_initial_magic.text()
            self.edit_initial_magic.setText(str(settings["initial_magic_pattern"]))
            if self.edit_initial_magic.text() != old:
                changed.append("初期魔法 初期所持")
        set_spin("initial_lives", self.spin_initial_lives, "初期残数")
        set_spin("time_rate_fast", self.spin_time_fast, "ステージ制限時間 速い")
        set_spin("time_rate_normal", self.spin_time_normal, "ステージ制限時間 普通")
        set_spin("time_rate_slow", self.spin_time_slow, "ステージ制限時間 遅い")
        if has("wall_colors_1_48") and getattr(self, "_wall_color_ok", False):
            values = settings["wall_colors_1_48"]
            if isinstance(values, list) and len(values) == len(self.combo_wall_colors):
                wall_changed = False
                for combo, value in zip(self.combo_wall_colors, values):
                    old = self._combo_data(combo)
                    self._set_combo_data(combo, int(value) & 0x3F)
                    wall_changed = wall_changed or (self._combo_data(combo) != old)
                if wall_changed:
                    changed.append("ステージ壁色")
        if has("main_palette_hex"):
            values = settings["main_palette_hex"]
            if not isinstance(values, str):
                raise ValueError("main_palette_hex must be a hex string.")
            old = bytes(self.rom.data[0x0ED4:0x0ED4 + 32])
            new = self._parse_hex_bytes(values, 32, "main_palette_hex")
            if new != old:
                self.rom.data[0x0ED4:0x0ED4 + 32] = new
                changed.append("メインパレット")
        if has("demo_input_wait_hex"):
            values = settings["demo_input_wait_hex"]
            if not isinstance(values, str):
                raise ValueError("demo_input_wait_hex must be a hex string.")
            old = bytes(self.rom.data[demo_input.OFF_WAIT:demo_input.OFF_WAIT + demo_input.STEPS])
            new = self._parse_hex_bytes(values, demo_input.STEPS, "demo_input_wait_hex")
            if new != old:
                self.rom.data[demo_input.OFF_WAIT:demo_input.OFF_WAIT + demo_input.STEPS] = new
                changed.append("デモ操作 wait")
        if has("demo_input_joy_hex"):
            values = settings["demo_input_joy_hex"]
            if not isinstance(values, str):
                raise ValueError("demo_input_joy_hex must be a hex string.")
            old = bytes(self.rom.data[demo_input.OFF_JOY:demo_input.OFF_JOY + demo_input.STEPS])
            new = self._parse_hex_bytes(values, demo_input.STEPS, "demo_input_joy_hex")
            if new != old:
                self.rom.data[demo_input.OFF_JOY:demo_input.OFF_JOY + demo_input.STEPS] = new
                changed.append("デモ操作 joy")
        if has("enemy_drop_c278_hex"):
            values = settings["enemy_drop_c278_hex"]
            if not isinstance(values, str):
                raise ValueError("enemy_drop_c278_hex must be a hex string.")
            old = bytes(self.rom.data[enemy_drop.OFF_C278:enemy_drop.OFF_C278 + enemy_drop.LEN_C278])
            new = self._parse_hex_bytes(values, enemy_drop.LEN_C278, "enemy_drop_c278_hex")
            if new != old:
                self.rom.data[enemy_drop.OFF_C278:enemy_drop.OFF_C278 + enemy_drop.LEN_C278] = new
                changed.append("敵ドロップ C278")
        if has("enemy_drop_c293_hex"):
            values = settings["enemy_drop_c293_hex"]
            if not isinstance(values, str):
                raise ValueError("enemy_drop_c293_hex must be a hex string.")
            old = bytes(self.rom.data[enemy_drop.OFF_C293:enemy_drop.OFF_C293 + enemy_drop.LEN_C293])
            new = self._parse_hex_bytes(values, enemy_drop.LEN_C293, "enemy_drop_c293_hex")
            if new != old:
                self.rom.data[enemy_drop.OFF_C293:enemy_drop.OFF_C293 + enemy_drop.LEN_C293] = new
                changed.append("敵ドロップ C293")
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
                changed.append("クリア画面メッセージ")
        set_combo("walk_speed_multiplier", self.combo_walk, "ダーナ歩行速度")

        set_combo("salamander_xdist", self.combo_sala_x, "サラマンダーX距離")
        set_combo("salamander_ydist", self.combo_sala_y, "サラマンダーY許容")

        set_spin("panel_monster_cooldown_frames", self.spin_pm, "パネルモンスター クールダウン")
        set_check("panel_monster_snappy", self.chk_pm_snappy, "パネルモンスター キビキビ")
        set_check("panel_bullet_speed_fix_enabled", self.chk_pm_bullet_speed_fix, "パネルモンスター 弾の左右速度バグ修正")
        set_combo("panel_bullet_speed_fix_value", self.combo_pm_bullet_speed_fix, "パネルモンスター 弾速度")
        set_spin("demo_stage", self.spin_ds, "デモステージ")
        set_check("golem_snappy", self.chk_golem_snappy, "ゴーレム キビキビ")
        set_check("gargoyle_snappy", self.chk_gargoyle_snappy, "ガーゴイル キビキビ")
        set_spin("gargoyle_cooldown_frames", self.spin_gargoyle_cooldown, "ガーゴイル クールダウン")
        set_combo("gargoyle_variant_second_offset", self.combo_gargoyle_variant_offset, "強化ガーゴイル 2発目位置")
        set_check("dragon_snappy", self.chk_dragon_snappy, "ドラゴン キビキビ")
        set_combo("shared_monster_walk_multiplier", self.combo_shared_walk, "共通歩行速度")
        set_combo("neul_ghost_speed_multiplier", self.combo_neul_ghost_speed, "ゴースト＆ヌエル移動速度")
        set_combo("spark_ball_speed_multiplier", self.combo_spark_ball_speed, "スパークボール移動速度")
        set_spark_pause_digits("spark_ball_pause_digits", "強化スパークボール停止")
        set_combo("spark_ball_transparency_period", self.combo_spark_transparency, "強化スパークボール透明化")
        set_check("demonhead_snappy", self.chk_demonhead_snappy, "デーモンヘッド キビキビ")
        if has("clear_screen_preset") and self.combo_clearscreen.isEnabled():
            old = self.combo_clearscreen.currentIndex()
            self._set_combo_data(self.combo_clearscreen, str(settings["clear_screen_preset"]))
            if self.combo_clearscreen.currentIndex() != old:
                changed.append("クリア画面キャラ")
        set_check("gap_fix_enabled", self.chk_gapfix, "横穴侵入安定化")
        set_spin("dark_light_frames", self.spin_dark_light, "暗闇 明フレーム")
        set_spin("dark_dark_frames", self.spin_dark_dark, "暗闇 暗フレーム")
        return changed

    def _on_export_global_settings(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "共通設定をエクスポート",
            f"solomon_global_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_global_settings(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "エクスポート失敗", f"{type(e).__name__}: {e}")
            return
        QMessageBox.information(self, "エクスポート完了", f"共通設定を保存しました:\n{path}")

    def _on_import_global_settings(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "共通設定をインポート",
            "",
            "JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "インポート失敗", f"{type(e).__name__}: {e}")
            return
        if payload.get("format") != "solomon_customizer_global_settings":
            QMessageBox.warning(self, "形式エラー", "このファイルは共通設定JSONではありません。")
            return
        settings = payload.get("settings")
        if not isinstance(settings, dict):
            QMessageBox.warning(self, "形式エラー", "settings が見つからないか不正です。")
            return
        try:
            changed = self._apply_imported_global_settings(settings)
        except Exception as e:
            QMessageBox.critical(self, "インポート失敗", f"{type(e).__name__}: {e}")
            return
        msg = "共通設定を画面に読み込みました。\n[適用] または [OK] を押すとROMへ反映されます。"
        if changed:
            msg += "\n\n変更された項目:\n" + "\n".join(f"・{x}" for x in changed)
        else:
            msg += "\n\n現在の画面値と同じ内容でした。"
        QMessageBox.information(self, "インポート完了", msg)

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
                applied.append("開始ステージ → 1面")
            if d[0x1149] != 0x8D:
                d[0x1149] = 0x8D
            if d[0x114B] != 0x04:
                d[0x114B] = 0x04
        else:
            stage_byte = (stage_no - 1) & 0xff
            if d[0x1145] != stage_byte:
                d[0x1145] = stage_byte
                applied.append(f"開始ステージ → {stage_no}面")
            if d[0x1149] != 0xAD:
                d[0x1149] = 0xAD
            if d[0x114B] != 0x93:
                d[0x114B] = 0x93

        # コンティニュー上限ステージ
        new_cont = (self.spin_continue.value() - 1) & 0xff
        if self._continue_offset < len(d) and d[self._continue_offset] != new_cont:
            d[self._continue_offset] = new_cont
            applied.append(f"コンティニュー上限 → {self.spin_continue.value()}")

        # ワープ羽
        if getattr(self, "_warp_feather_ok", False):
            try:
                applied.extend(
                    warp_feather.apply(d, self.spin_warp_feather.value()))
            except warp_feather.WarpFeatherError as e:
                QMessageBox.warning(self, "ワープ羽 設定失敗", str(e))

        # 初期魔法 (共通)
        if getattr(self, "_initial_magic_ok", False):
            try:
                pattern = initial_magic.normalize_pattern_text(
                    self.edit_initial_magic.text())
                self.edit_initial_magic.setText(pattern)
                imch = initial_magic.apply(
                    d, self.spin_initial_magic_max.value(), pattern)
                if imch:
                    applied.append("初期魔法: " + " / ".join(imch))
            except initial_magic.InitialMagicError as e:
                QMessageBox.warning(self, "初期魔法 設定失敗", str(e))

        # 初期残数
        if getattr(self, "_initial_lives_ok", False):
            try:
                lvch = initial_lives.apply(
                    d, self.spin_initial_lives.value())
                if lvch:
                    applied.append("初期残数: " + " / ".join(lvch))
            except initial_lives.InitialLivesError as e:
                QMessageBox.warning(self, "初期残数 設定失敗", str(e))

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
                    applied.append("ステージ制限時間: " + " / ".join(tch))
            except time_decrease_hack.TimeDecreaseHackError as e:
                QMessageBox.warning(self, "ステージ制限時間 設定失敗", str(e))

        # ステージ壁色 (1-48面)
        if getattr(self, "_wall_color_ok", False):
            try:
                wch = wall_color_hack.apply(
                    d, [self._combo_data(c) for c in self.combo_wall_colors])
                if wch:
                    applied.append("ステージ壁色: " + " / ".join(wch))
            except wall_color_hack.WallColorHackError as e:
                QMessageBox.warning(self, "ステージ壁色 設定失敗", str(e))

        # ダーナ歩行速度
        if self._walk_ok:
            mult = self.combo_walk.currentData()
            try:
                changed = walk_speed.apply_multiplier(d, mult)
                if changed:
                    applied.append(f"歩行速度 → {mult:g}x ({'/'.join(changed)})")
            except walk_speed.WalkSpeedError as e:
                QMessageBox.warning(self, "歩行速度の改造失敗", str(e))

        # サラマンダー/ドラゴン反応距離
        if self._sala_ok:
            try:
                sch = salamander_hack.apply_distance(
                    d,
                    self.combo_sala_x.currentData(),
                    self.combo_sala_y.currentData(),
                )
                if sch:
                    applied.append("サラマンダー距離: " + " / ".join(sch))
            except salamander_hack.SalamanderHackError as e:
                QMessageBox.warning(self, "サラマンダー距離設定失敗", str(e))

        # パネルモンスター
        if self._pm_ok:
            try:
                pch = panel_monster_hack.apply_cooldown(
                    d, self.spin_pm.value())
                pch.extend(panel_monster_hack.apply_snappy(
                    d, self.chk_pm_snappy.isChecked()))
                if getattr(self, "_pm_bullet_speed_ok", False):
                    pch.extend(panel_bullet_speed_fix.apply(
                        d,
                        self.chk_pm_bullet_speed_fix.isChecked(),
                        self._combo_data(self.combo_pm_bullet_speed_fix),
                    ))
                if pch:
                    applied.append("パネルモンスター: " + " / ".join(pch))
            except panel_monster_hack.PanelMonsterHackError as e:
                QMessageBox.warning(self, "パネルモンスター改造失敗", str(e))
            except panel_bullet_speed_fix.PanelBulletSpeedFixError as e:
                QMessageBox.warning(self, "パネルモンスター弾速度修正失敗", str(e))

        # デモプレイのステージ
        if self._ds_ok:
            try:
                dch = demo_stage_hack.apply(d, self.spin_ds.value())
                if dch:
                    applied.append("デモプレイ: " + " / ".join(dch))
            except demo_stage_hack.DemoStageHackError as e:
                QMessageBox.warning(self, "デモステージ改造失敗", str(e))

        # ゴーレム キビキビ
        if self._golem_ok:
            try:
                gch = golem_hack.apply(d, self.chk_golem_snappy.isChecked())
                if gch:
                    applied.append("ゴーレム: " + " / ".join(gch))
            except golem_hack.GolemHackError as e:
                QMessageBox.warning(self, "ゴーレム改造失敗", str(e))

        # ガーゴイル キビキビ
        if self._gargoyle_ok:
            try:
                gych = gargoyle_hack.apply(
                    d, self.chk_gargoyle_snappy.isChecked())
                cdch = gargoyle_hack.apply_cooldown(
                    d, self.spin_gargoyle_cooldown.value())
                gych.extend(cdch)
                if gych:
                    applied.append("ガーゴイル: " + " / ".join(gych))
            except gargoyle_hack.GargoyleHackError as e:
                QMessageBox.warning(self, "ガーゴイル改造失敗", str(e))

        # 強化ガーゴイル
        if getattr(self, "_gargoyle_variant_ok", False):
            try:
                selected_offset = self.combo_gargoyle_variant_offset.currentData()
                should_apply = (
                    gargoyle_variant.is_applied(d)
                    or selected_offset != gargoyle_variant.DEFAULT_SECOND_OFFSET
                )
                if should_apply:
                    gvch = gargoyle_variant.apply(
                        d,
                        second_offset=selected_offset,
                        second_speed=gargoyle_variant.DEFAULT_SECOND_SPEED,
                    )
                    if gvch:
                        applied.append("強化ガーゴイル: " + " / ".join(gvch))
            except gargoyle_variant.GargoyleVariantError as e:
                QMessageBox.warning(self, "強化ガーゴイル設定失敗", str(e))
                return

        # ドラゴン キビキビ
        if self._dragon_ok:
            try:
                drch = dragon_hack.apply(
                    d, self.chk_dragon_snappy.isChecked())
                if drch:
                    applied.append("ドラゴン: " + " / ".join(drch))
            except dragon_hack.DragonHackError as e:
                QMessageBox.warning(self, "ドラゴン改造失敗", str(e))

        # 共通歩行速度 (Golem/Dragon/Gargoyle s0)
        if self._golem_spd_ok:
            try:
                gsch = golem_speed.apply_shared_walk(
                    d, self.combo_shared_walk.currentData())
                if gsch:
                    applied.append("共通歩行速度: " + " / ".join(gsch))
            except golem_speed.GolemSpeedError as e:
                QMessageBox.warning(self, "共通歩行速度改造失敗", str(e))

        # ゴースト＆ヌエル移動速度
        if self._neul_ghost_spd_ok:
            try:
                ngch = neul_ghost_speed.apply(
                    d, self.combo_neul_ghost_speed.currentData())
                if ngch:
                    applied.append("ゴースト＆ヌエル: " + " / ".join(ngch))
            except neul_ghost_speed.NeulGhostSpeedError as e:
                QMessageBox.warning(self, "ゴースト＆ヌエル速度改造失敗", str(e))

        # スパークボール移動速度
        if self._spark_ball_spd_ok:
            try:
                sbch = spark_ball_speed.apply(
                    d, self.combo_spark_ball_speed.currentData())
                if sbch:
                    applied.append("スパークボール: " + " / ".join(sbch))
            except spark_ball_speed.SparkBallSpeedError as e:
                QMessageBox.warning(self, "スパークボール速度改造失敗", str(e))

        # 強化スパークボール
        if getattr(self, "_spark_ball_variant_ok", False):
            try:
                selected_digits = self._selected_spark_pause_digits()
                sbvch = spark_ball_variant.apply(
                    d,
                    pause_digits=selected_digits,
                    transparency_period=self.combo_spark_transparency.currentData(),
                )
                if sbvch:
                    applied.append("強化スパークボール: " + " / ".join(sbvch))
            except spark_ball_variant.SparkBallVariantError as e:
                QMessageBox.warning(self, "強化スパークボール設定失敗", str(e))
                return

        # デーモンヘッド キビキビ
        if self._demonhead_ok:
            try:
                dhch = demonhead_hack.apply(
                    d, self.chk_demonhead_snappy.isChecked())
                if dhch:
                    applied.append("デーモンヘッド: " + " / ".join(dhch))
            except demonhead_hack.DemonheadHackError as e:
                QMessageBox.warning(self, "デーモンヘッド改造失敗", str(e))

        if getattr(self, "_cs_ok", False):
            preset_id = self._combo_data(self.combo_clearscreen)
            name = self.combo_clearscreen.currentText()
            cur = clearscreen_hack.current_preset_id(d)
            if preset_id != cur:
                try:
                    clearscreen_hack.apply_preset(d, preset_id)
                    applied.append(f"クリア画面キャラ → {name}")
                except clearscreen_hack.ClearScreenHackError as e:
                    QMessageBox.warning(self, "クリア画面改造失敗", str(e))

        # 原作バグ回避: 横穴侵入安定化
        if getattr(self, "_gapfix_ok", False):
            want = self.chk_gapfix.isChecked()
            try:
                if want != gap_fix.is_applied(d):
                    gch = gap_fix.apply(d, want)
                    if gch:
                        applied.append(
                            "横穴侵入安定化 " + ("ON" if want else "OFF"))
            except gap_fix.GapFixError as e:
                QMessageBox.warning(self, "横穴侵入安定化 失敗", str(e))

        # 暗闇テンポ (全体共通)
        if getattr(self, "_dark_tempo_ok", False):
            lf = self.spin_dark_light.value()
            df = self.spin_dark_dark.value()
            try:
                if (lf, df) != room_flags.get_tempo(d):
                    room_flags.set_tempo(d, lf, df)
                    applied.append(f"暗闇テンポ → 明{lf}/暗{df}フレーム")
            except room_flags.RoomFlagError as e:
                QMessageBox.warning(self, "暗闇テンポ設定 失敗", str(e))


        if applied:
            QMessageBox.information(
                self, "適用完了",
                "以下の項目を変更しました:\n\n" + "\n".join(f"・{a}" for a in applied)
                + "\n\n※ 改造ROMとして保存しないと永続化されません。"
            )
        else:
            QMessageBox.information(self, "変更なし", "書き換えられた箇所はありません。")
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
            self, "確認",
            "このダイアログで設定した項目を全てデフォルト（オリジナル値）に戻します。\n"
            "適用するには [適用] または [OK] を押してください。\n\n"
            "続行しますか？",
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
        if self._sala_ok:
            self.combo_sala_x.setCurrentIndex(0)
            self.combo_sala_y.setCurrentIndex(0)
        if self._pm_ok:
            self.spin_pm.setValue(panel_monster_hack.ORIG_THRESHOLD)
            self.chk_pm_snappy.setChecked(False)
            if getattr(self, "_pm_bullet_speed_ok", False):
                self.chk_pm_bullet_speed_fix.setChecked(False)
                self._set_combo_data(
                    self.combo_pm_bullet_speed_fix,
                    panel_bullet_speed_fix.SLOW_VALUE,
                )
        if self._golem_ok:
            self.chk_golem_snappy.setChecked(False)
        if self._gargoyle_ok:
            self.chk_gargoyle_snappy.setChecked(False)
            self.spin_gargoyle_cooldown.setValue(0x50)
        if getattr(self, "_gargoyle_variant_ok", False):
            self._set_combo_data(
                self.combo_gargoyle_variant_offset,
                gargoyle_variant.DEFAULT_SECOND_OFFSET,
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
            self._set_combo_data(
                self.combo_spark_transparency,
                spark_ball_variant.DEFAULT_TRANSPARENCY_PERIOD,
            )
        if self._demonhead_ok:
            self.chk_demonhead_snappy.setChecked(False)
        if getattr(self, "_cs_ok", False):
            self._set_combo_data(self.combo_clearscreen, "fairy_original")
        if getattr(self, "_gapfix_ok", False):
            self.chk_gapfix.setChecked(False)
        if getattr(self, "_dark_tempo_ok", False):
            self.spin_dark_light.setValue(45)
            self.spin_dark_dark.setValue(100)
