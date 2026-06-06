"""全ステージ統計ダイアログ - 重要アイテム/敵の配置状況を一覧表で表示"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QImage, QPixmap, QPainter

# 重要アイテム列のスプライト1個あたりのピクセルサイズ
ITEM_THUMB = 28
ITEM_GAP = 3

from ..core import constants as c
from ..core.element import Wall
from ..core import room_flags as _rf
from ..core import stage_ext as _se


# ★重要アイテムの「コード一覧」のみ(=どれを集計するか・順序)。
#   名前は持たない=2重管理しない。表示名は skc_config.xml item_desc
#   (self.config.item_desc) 単一ソースから解決する。
IMPORTANT_ITEMS = [
    0x20, 0x22, 0x1c, 0x1d, 0x1e, 0x1f,
    0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x21,
]

IMPORTANT_ENTITY_ORDER = (
    [("item", code) for code in IMPORTANT_ITEMS] +
    [
        ("enemy", 0x18),  # Mighty Bomb Jack
        ("item", 0x39),   # Tecmo Bunny
        ("enemy", 0x1c),  # Fairy
        ("enemy", 0x1d),  # Fairy Princess
    ]
)
IMPORTANT_ENTITY_SET = set(IMPORTANT_ENTITY_ORDER)


def _level_meta_important_key(meta_item) -> tuple[str, int] | None:
    """level_meta_items のうち、重要アイテム列へ合算するものを返す。"""
    desc = (getattr(meta_item, "description", "") or "").lower()
    if "solomon" in desc and "seal" in desc:
        return ("item", 0x20)
    if "page of " in desc:
        return ("item", 0x21)
    if "bomb jack" in desc:
        return ("enemy", 0x18)
    if "tecmo bunny" in desc:
        return ("item", 0x39)
    return None


def _level_meta_item_state(level, meta_item) -> str:
    """キャンバス/PNG描画と同じ基準で meta item の状態を分類する。"""
    if bool(getattr(meta_item, "transparent", False)):
        return "hidden"
    x, y = getattr(meta_item, "position", (0, 0))
    if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
        if level.tiles[y][x] == Wall.BROWN:
            return "in_block"
    return "normal"


def _item_important_key(base_code: int) -> tuple[str, int] | None:
    """通常アイテムを重要アイテム列の代表キーへ正規化する。"""
    if base_code in IMPORTANT_ITEMS:
        return ("item", base_code)
    if base_code in (0x38, 0x39):
        return ("item", 0x39)
    return None


def _enemy_important_key(enemy, config) -> tuple[str, int] | None:
    """特別に重要アイテム列へ載せる敵を代表コードへ正規化する。"""
    code = getattr(enemy, "element_no", 0)
    desc = ""
    if config is not None:
        desc = (getattr(config, "enemy_desc", {}) or {}).get(code, "")
    desc = desc.lower()
    if "mighty bomb jack" in desc:
        return ("enemy", 0x18)
    base = desc.split("(", 1)[0].strip()
    if "#" in base:
        head, _, tail = base.rpartition("#")
        if tail.strip().isdigit():
            base = head.strip()
    if base == "fairy":
        return ("enemy", 0x1c)
    if base == "fairy princess":
        return ("enemy", 0x1d)
    return None


class StatsDialog(QDialog):
    """全ステージ統計表示ダイアログ"""

    # 列構成 (ミラー位置列・座標は撤去)。
    # ★列インデックスは下で COLUMNS のヘッダ名から解決する
    #   (列追加/並べ替えで他箇所が壊れないようにするための堅牢化)。
    COLUMNS = [
        ("Lv", 36),
        ("通常", 50),
        ("隠し", 50),
        ("in_blk", 60),
        ("敵数", 50),
        ("タイル", 52),     # tileset_no (0-2)
        ("時間減少", 66),   # time_decrease_rate (0=速い / 1=普通 / 2=遅い)
        ("敵寿命\n約0.5秒x値", 78),  # spawn_enemy_lifetime (0-255)
        ("鍵", 64),
        ("星座", 84),
        ("A禁止", 56),      # BIT_NO_ASTONE
        ("B禁止", 56),      # BIT_NO_BFIRE
        ("火リセット", 76),  # stage_ext FLAG_FIRE_RESET
        ("鍵敵#", 54),      # stage_ext key enemy number
        ("暗闇", 52),       # BIT_DARK
        ("隠し扉", 60),     # BIT_HIDDEN_DOOR
        ("配置敵", 300),    # 配置された敵 スプライト
        ("ミラー敵", 240),  # ミラーから出る敵 スプライト
        ("重要アイテム", 380),  # スプライト
    ]
    # ヘッダ名 → 列インデックス (ハードコード排除)
    _HDR = [h for h, _ in COLUMNS]
    LV_COL = 0
    HIDDEN_COL = _HDR.index("隠し")
    INBLK_COL = _HDR.index("in_blk")
    TS_COL = _HDR.index("タイル")
    TIME_COL = _HDR.index("時間減少")
    LIFE_COL = _HDR.index("敵寿命\n約0.5秒x値")
    KEY_COL = _HDR.index("鍵")
    ASTONE_COL = _HDR.index("A禁止")
    BFIRE_COL = _HDR.index("B禁止")
    FIRE_RESET_COL = _HDR.index("火リセット")
    KEY_ENEMY_COL = _HDR.index("鍵敵#")
    DARK_COL = _HDR.index("暗闇")
    DOOR_COL = _HDR.index("隠し扉")
    PLACED_COL = _HDR.index("配置敵")
    MIRROR_COL = _HDR.index("ミラー敵")
    ITEM_COL = _HDR.index("重要アイテム")
    FLAG_COLS = (ASTONE_COL, BFIRE_COL, FIRE_RESET_COL, DARK_COL, DOOR_COL)
    NUM_COLS = (TS_COL, TIME_COL, LIFE_COL)  # 中央寄せする数値メタ列

    def __init__(self, levels, item_desc=None, config=None,
                 tile_renderer=None, app_config=None, rom=None, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(f"全ステージ統計 ({len(levels)}ステージ)")
        self.resize(1100, 720)
        self.levels = levels
        self.item_desc = item_desc or {}
        self.config = config
        self.tile_renderer = tile_renderer
        self.rom = rom                  # ミラー実データ読出用 (m66 layout)
        self._app_config = app_config   # サイズ/位置 復元用 (None=保存しない)
        self._sprite_cache = {}   # (item base_code, tileset_no) -> QPixmap
        self._enemy_cache = {}    # (enemy code, tileset_no) -> QPixmap
        self._item_col_w = 0      # 重要アイテム列の最大ピクセル幅
        self._placed_col_w = 0    # 配置敵列の最大ピクセル幅
        self._mirror_col_w = 0    # ミラー敵列の最大ピクセル幅
        self._csv_item_text = {}   # row -> 重要アイテム内訳 (CSV用)
        self._csv_placed_text = {} # row -> 配置敵内訳 (CSV用)
        self._csv_mirror_text = {} # row -> ミラー敵内訳 (CSV用)

        layout = QVBoxLayout(self)

        # 説明
        info = QLabel(
            "「重要アイテム」列は紋章/Warp/Shrine/Origami Swan/Demonhead Coin/"
            "Sphinx/Egyptian Head/Magic Lamp/E-bottle/Page/Tecmo Bunny と、"
            "特殊扱いの Mighty Bomb Jack/Fairy/Fairy Princess を集計(コイン/宝石/"
            "Bell/Scroll/タイマー系などは除外)。「配置敵」=面に置かれた敵"
            "(実数 ×N)、「ミラー敵」=デーモンミラーから出る敵(種類のみ・"
            "無スケジュールのミラーは除外)。<br>"
            "セルをダブルクリックでそのステージへジャンプ。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # テーブル
        self.table = QTableWidget(len(levels), len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels([h for h, _ in self.COLUMNS])
        item_header = self.table.horizontalHeaderItem(self.ITEM_COL)
        if item_header is not None:
            item_header.setToolTip(
                "重要アイテム列の枠色:\n"
                "黄 = 隠し / 緑 = ブロック内 / 灰 = 通常\n"
                "右下の数字は同種アイテムの合計数です。"
            )
        for i, (_, w) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(i, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        # 「…」省略をやめ全文表示。列幅はユーザーが調整可(保存対象)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self._populate()
        layout.addWidget(self.table)

        # ボタン行
        btn_row = QHBoxLayout()
        self.btn_csv = QPushButton("CSV出力")
        self.btn_csv.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self.btn_csv)
        btn_row.addStretch()
        self.btn_close = QPushButton("閉じる")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self._restore_geometry()

    # ---- ウィンドウ サイズ/位置 復元 (HackDialog と同一パターン) ----

    def _restore_geometry(self):
        cfg = self._app_config
        if not cfg:
            return
        w = int(cfg.get("stats_dlg_w", -1))
        h = int(cfg.get("stats_dlg_h", -1))
        x = int(cfg.get("stats_dlg_x", -1))
        y = int(cfg.get("stats_dlg_y", -1))
        if w > 100 and h > 100:
            self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)
        # 列幅 (保存済なら _populate の自動幅を上書き)
        col_w = cfg.get("stats_dlg_col_w", [])
        if isinstance(col_w, list) and len(col_w) == self.table.columnCount():
            for i, cw in enumerate(col_w):
                try:
                    if int(cw) > 0:
                        self.table.setColumnWidth(i, int(cw))
                except (TypeError, ValueError):
                    pass

    def _save_geometry(self):
        cfg = self._app_config
        if cfg is None:
            return
        try:
            from ..core.config import save_config
            cfg["stats_dlg_x"] = max(0, self.x())
            cfg["stats_dlg_y"] = max(0, self.y())
            cfg["stats_dlg_w"] = self.width()
            cfg["stats_dlg_h"] = self.height()
            cfg["stats_dlg_col_w"] = [
                self.table.columnWidth(i)
                for i in range(self.table.columnCount())
            ]
            save_config(cfg)
        except Exception:
            pass   # 設定保存失敗でダイアログ閉鎖を妨げない

    def done(self, r):
        # OK/閉じる/Esc/×ボタン すべて経由する。閉じる直前に保存。
        self._save_geometry()
        super().done(r)

    # ---- スプライト描画 (element_picker と同一ルート: item_map→TileRenderer) ----

    def _item_pixmap(self, base_code: int, tileset_no: int) -> QPixmap:
        """アイテム base_code (element_no & 0x3f) の ITEM_THUMB スプライト。
        element_picker._make_icon_from_tile と同じ描画ロジック。"""
        cache_key = (base_code, tileset_no)
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
        if self.tile_renderer is None or self.config is None:
            return QPixmap()
        try:
            anim = self.config.item_map.get(base_code & 0x3f, 0)
            sprite = self.tile_renderer.get_tile_image(anim, tileset_no, transparent=True)
            bg = QImage(ITEM_THUMB, ITEM_THUMB, QImage.Format_ARGB32)
            bg.fill(QColor(20, 20, 20))
            p = QPainter(bg)
            scaled = sprite.scaled(ITEM_THUMB, ITEM_THUMB,
                                   Qt.KeepAspectRatio, Qt.FastTransformation)
            ox = (ITEM_THUMB - scaled.width()) // 2
            oy = (ITEM_THUMB - scaled.height()) // 2
            p.drawImage(ox, oy, scaled)
            p.end()
            pm = QPixmap.fromImage(bg)
        except Exception:
            pm = QPixmap()
        self._sprite_cache[cache_key] = pm
        return pm

    def _compose_item_strip(self, ordered_buckets, tileset_no: int):
        """ordered_buckets = [(code, label, {normal,hidden,in_block})] を
        横一列のスプライト帯 QPixmap に合成。状態は枠色、複数は ×N。"""
        n = len(ordered_buckets)
        if n == 0:
            return None
        cell_w = ITEM_THUMB + 2
        strip_w = n * cell_w + (n - 1) * ITEM_GAP
        strip = QImage(strip_w, ITEM_THUMB + 2, QImage.Format_ARGB32)
        strip.fill(QColor(0, 0, 0, 0))
        p = QPainter(strip)
        x = 0
        for key, _label, b in ordered_buckets:
            pm = self._important_pixmap(key, tileset_no)
            fx = x + 1
            if not pm.isNull():
                p.drawPixmap(fx, 1, pm)
            # 状態枠: 隠し=黄 / in_block=緑 / 通常のみ=灰
            if b["hidden"]:
                pen = QColor(230, 200, 40)
            elif b["in_block"]:
                pen = QColor(70, 190, 90)
            else:
                pen = QColor(90, 90, 90)
            p.setPen(pen)
            p.drawRect(fx, 1, ITEM_THUMB - 1, ITEM_THUMB - 1)
            total = b["normal"] + b["hidden"] + b["in_block"]
            if total > 1:
                p.setPen(QColor(255, 255, 255))
                p.fillRect(fx + ITEM_THUMB - 11, ITEM_THUMB - 10, 11, 11,
                           QColor(0, 0, 0, 170))
                p.drawText(fx + ITEM_THUMB - 10, ITEM_THUMB - 1, str(total))
            x += cell_w + ITEM_GAP
        p.end()
        return QPixmap.fromImage(strip)

    def _enemy_pixmap(self, code: int, tileset_no: int) -> QPixmap:
        """敵 element_no の ITEM_THUMB スプライト。
        element_picker._make_enemy_icon と同じルート (enemy_map)。"""
        cache_key = (code, tileset_no)
        if cache_key in self._enemy_cache:
            return self._enemy_cache[cache_key]
        if self.tile_renderer is None or self.config is None:
            return QPixmap()
        try:
            anim = self.config.enemy_map.get(code, 0)
            sprite = self.tile_renderer.get_tile_image(anim, tileset_no, transparent=True)
            bg = QImage(ITEM_THUMB, ITEM_THUMB, QImage.Format_ARGB32)
            bg.fill(QColor(20, 20, 20))
            p = QPainter(bg)
            scaled = sprite.scaled(ITEM_THUMB, ITEM_THUMB,
                                   Qt.KeepAspectRatio, Qt.FastTransformation)
            ox = (ITEM_THUMB - scaled.width()) // 2
            oy = (ITEM_THUMB - scaled.height()) // 2
            p.drawImage(ox, oy, scaled)
            p.end()
            pm = QPixmap.fromImage(bg)
        except Exception:
            pm = QPixmap()
        self._enemy_cache[cache_key] = pm
        return pm

    def _important_pixmap(self, key, tileset_no: int) -> QPixmap:
        source, code = key
        if source == "enemy":
            return self._enemy_pixmap(code, tileset_no)
        return self._item_pixmap(code, tileset_no)

    def _important_label(self, key) -> str:
        source, code = key
        if source == "enemy":
            desc = (getattr(self.config, "enemy_desc", {}) or {}) if self.config else {}
            return desc.get(code, f"0x{code:02x}")
        desc = (getattr(self.config, "item_desc", {}) or {}) if self.config else {}
        return desc.get(code, f"0x{code:02x}")

    def _compose_enemy_strip(self, ordered, tileset_no: int):
        """ordered = [(code, name, count)] を横一列のスプライト帯に合成。
        状態枠は無し(灰枠のみ)、複数は ×N。"""
        n = len(ordered)
        if n == 0:
            return None
        cell_w = ITEM_THUMB + 2
        strip_w = n * cell_w + (n - 1) * ITEM_GAP
        strip = QImage(strip_w, ITEM_THUMB + 2, QImage.Format_ARGB32)
        strip.fill(QColor(0, 0, 0, 0))
        p = QPainter(strip)
        x = 0
        for code, _name, cnt in ordered:
            pm = self._enemy_pixmap(code, tileset_no)
            fx = x + 1
            if not pm.isNull():
                p.drawPixmap(fx, 1, pm)
            p.setPen(QColor(90, 90, 90))
            p.drawRect(fx, 1, ITEM_THUMB - 1, ITEM_THUMB - 1)
            if cnt > 1:
                p.fillRect(fx + ITEM_THUMB - 11, ITEM_THUMB - 10, 11, 11,
                           QColor(0, 0, 0, 170))
                p.setPen(QColor(255, 255, 255))
                p.drawText(fx + ITEM_THUMB - 10, ITEM_THUMB - 1, str(cnt))
            x += cell_w + ITEM_GAP
        p.end()
        return QPixmap.fromImage(strip)

    # ---- 敵 基底名 / デーモンミラー spawn 読出 ----

    def _enemy_base(self, code: int) -> str:
        """enemy_desc の基底名 (括弧 "(...)" 以降 と 末尾 " #N" を除去)。
        方向/速度/サブスロット違いを同一モンスター扱いするためのキー。"""
        full = (self.config.enemy_desc.get(code, f"0x{code:02x}")
                if self.config else f"0x{code:02x}")
        base = full.split("(", 1)[0].strip()
        if "#" in base:
            head, _, tail = base.rpartition("#")
            if tail.strip().isdigit():
                base = head.strip()
        return base or full

    def _preferred_enemy_code(self, base: str, fallback_code: int) -> int:
        """敵一覧用の代表スプライト。左向き定義があればそれを優先する。"""
        if self.config is None:
            return fallback_code
        candidates = []
        for code, desc in (getattr(self.config, "enemy_desc", {}) or {}).items():
            if self._enemy_base(code) != base:
                continue
            desc_l = desc.lower()
            priority = 0 if "(left" in desc_l else 1
            candidates.append((priority, code))
        if not candidates:
            return fallback_code
        candidates.sort()
        return candidates[0][1]

    def _mirror_spawn_codes(self, level_no: int) -> list:
        """デーモンミラーから実際に出てくる敵コード一覧を返す。

        - ミラーは2基。各々: 敵セット(最大7、$90終端) + 64bitスケジュール。
        - ★スケジュールに1つもチェックが無いミラーは何も出ない →
          そのミラーの敵セットは無視 (画面に出ない=載せない)。
          (先頭2tick はゲーム側で無視されるので除外して判定)
        - 読出経路は main_window._sync_enemy_codes_from_rom /
          MirrorDialog._read_schedule と同一 (m66 layout)。
        """
        if self.rom is None:
            return []
        try:
            from ..core import m66
        except Exception:
            return []
        out = []
        data = self.rom.data
        for mirror_no in range(2):
            local = (m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA if mirror_no == 0
                     else m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA)
            off = m66.OFFSET_M66_LVL_DATA + 256 * level_no + local
            codes = []
            for i in range(7):
                b = data[off + i]
                if b == 0x90:
                    break
                if b != 0x00:
                    codes.append(b)
            if not codes:
                continue
            # スケジュール 8byte → 64bit。先頭2tick(byte0 b7,b6)は無視。
            sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (2 * level_no + mirror_no) * 8
            active = False
            for i in range(8):
                byte = data[sched_off + i]
                if i == 0:
                    byte &= 0x3F   # 先頭2tick(=b7,b6)を除外
                if byte:
                    active = True
                    break
            if active:
                out.extend(codes)
        return out

    def _populate(self):
        for row, lv in enumerate(self.levels):
            tileset_no = int(getattr(lv, "tileset_no", 0) or 0)
            # アイテム集計
            normal_count = 0
            hidden_count = 0
            in_block_count = 0
            important_buckets = {}  # (source, code) -> {state: count}
            for it in lv.items:
                flag = it.element_no & 0xC0
                base = it.element_no & 0x3F
                state = "hidden" if flag == 0x40 else ("in_block" if flag == 0x80 else "normal")
                normal_count, hidden_count, in_block_count = self._add_item_state_count(
                    normal_count, hidden_count, in_block_count, state)
                # 重要アイテム
                key = _item_important_key(base)
                if key in IMPORTANT_ENTITY_SET:
                    self._add_important_item(important_buckets, key, state)

            meta_items = getattr(self.config, "level_meta_items", []) if self.config else []
            for mi in meta_items:
                if getattr(mi, "level_no", -1) != row:
                    continue
                key = _level_meta_important_key(mi)
                if key not in IMPORTANT_ENTITY_SET:
                    continue
                state = _level_meta_item_state(lv, mi)
                normal_count, hidden_count, in_block_count = self._add_item_state_count(
                    normal_count, hidden_count, in_block_count, state)
                self._add_important_item(important_buckets, key, state)

            for en in lv.enemies:
                key = _enemy_important_key(en, self.config)
                if key in IMPORTANT_ENTITY_SET:
                    self._add_important_item(important_buckets, key, "normal")

            key_enemy_no = _se.get_key_enemy_number(lv)
            key_enemy_text = str(key_enemy_no) if key_enemy_no > 0 else ""

            # 鍵状態 (座標は表示しない)
            if lv.is_key_removed():
                key_state = "削除"
            elif lv.is_key_in_block():
                key_state = "in_block"
            elif lv.is_key_hidden():
                key_state = "hidden"
            else:
                key_state = "通常"

            # 星座 (座標は表示しない)
            if lv.has_constellation():
                cn = lv.get_constellation_no()
                from ..core.constants import CONSTELLATION_NAMES
                name, _ = CONSTELLATION_NAMES.get(cn, (f"0x{cn:02x}", 0))
                const_state = name
            else:
                const_state = "-"

            # 部屋フラグ (lv.room_flags = bitfield。main_window と同一)
            rf = getattr(lv, "room_flags", 0) or 0
            f_astone = "●" if rf & _rf.BIT_NO_ASTONE else ""
            f_bfire = "●" if rf & _rf.BIT_NO_BFIRE else ""
            f_dark = "●" if rf & _rf.BIT_DARK else ""
            f_door = "●" if rf & _rf.BIT_HIDDEN_DOOR else ""
            f_fire_reset = "●" if _se.fire_reset_enabled(lv) else ""

            # 重要アイテム文字列 + スプライト用 ordered_buckets
            important_strs = []
            ordered_buckets = []
            for key in IMPORTANT_ENTITY_ORDER:
                if key in important_buckets:
                    label = self._important_label(key)
                    b = important_buckets[key]
                    parts = []
                    if b["normal"]: parts.append(f"通{b['normal']}")
                    if b["hidden"]: parts.append(f"隠{b['hidden']}")
                    if b["in_block"]: parts.append(f"内{b['in_block']}")
                    important_strs.append(f"{label}[{','.join(parts)}]")
                    ordered_buckets.append((key, label, b))
            important_text = " / ".join(important_strs) if important_strs else "-"
            self._csv_item_text[row] = important_text  # CSV出力用に保持

            # 敵集計 (★方向/速度違いは同一モンスターとして合算。
            #  グループキー=enemy_desc の基底名 _enemy_base)
            #  ・「配置敵」= lv.enemies を実数 ×N。
            #  ・「ミラー敵」= デーモンミラーから出る敵。何匹出るか不明
            #    なので種類ごと 1 (presence)。スケジュール無チェックの
            #    ミラーは出ないので対象外 (_mirror_spawn_codes)。
            #  ・代表スプライトは、左向き定義があれば左向きを優先。
            def _group(codes_counts):
                grp = {}
                for ec, n in codes_counts:
                    base = self._enemy_base(ec)
                    g = grp.get(base)
                    if g is None:
                        grp[base] = {"count": n, "code": ec}
                    else:
                        g["count"] += n
                        if ec < g["code"]:
                            g["code"] = ec
                ordered, strs = [], []
                for base in sorted(grp, key=lambda b: grp[b]["code"]):
                    g = grp[base]
                    code = self._preferred_enemy_code(base, g["code"])
                    ordered.append((code, base, g["count"]))
                    strs.append(f"{base}×{g['count']}"
                                if g["count"] > 1 else base)
                return ordered, (" / ".join(strs) if strs else "-")

            # 配置敵
            placed_enemies = [
                en for en in lv.enemies
                if _enemy_important_key(en, self.config) is None
            ]
            placed_ordered, placed_text = _group(
                [(en.element_no, 1) for en in placed_enemies])
            self._csv_placed_text[row] = placed_text

            # ミラー敵 (基底名で重複排除し各 1)
            mbases = {}
            for ec in self._mirror_spawn_codes(row):
                b = self._enemy_base(ec)
                if b not in mbases or ec < mbases[b]:
                    mbases[b] = ec
            mirror_ordered, mirror_text = _group(
                [(ec, 1) for ec in mbases.values()])
            self._csv_mirror_text[row] = mirror_text

            # セル設定 (COLUMNS と同じ並び。スプライト3列はテキスト空)
            cells = [
                str(row + 1),                     # Lv
                str(normal_count),                # 通常
                str(hidden_count),                # 隠し
                str(in_block_count),              # in_blk
                str(len(placed_enemies)),         # 敵数
                str(tileset_no),                  # タイル
                str(getattr(lv, "time_decrease_rate", 0)),    # 時間減少
                str(getattr(lv, "spawn_enemy_lifetime", 0)),  # 敵寿命
                key_state,                        # 鍵
                const_state,                      # 星座
                f_astone,                         # A禁止
                f_bfire,                          # B禁止
                f_fire_reset,                     # 火リセット
                key_enemy_text,                   # 鍵敵#
                f_dark,                           # 暗闇
                f_door,                           # 隠し扉
                "",                               # 配置敵(sprite)
                "",                               # ミラー敵(sprite)
                "",                               # 重要アイテム(sprite)
            ]
            for col, txt in enumerate(cells):
                item = QTableWidgetItem(txt)
                if col in self.FLAG_COLS or col in self.NUM_COLS or col == self.KEY_ENEMY_COL:
                    item.setTextAlignment(Qt.AlignCenter)
                if col == self.LV_COL:
                    item.setData(Qt.UserRole, row)  # レベル番号(0-indexed)
                self.table.setItem(row, col, item)

            # 重要アイテム列(col 8): スプライト帯のみ表示(文字は出さない)。
            # 内訳テキストは hover ツールチップ + CSV出力(self._csv_item_text)。
            strip = self._compose_item_strip(ordered_buckets, tileset_no)
            if strip is not None and not strip.isNull():
                lbl = QLabel()
                lbl.setPixmap(strip)
                lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                lbl.setContentsMargins(3, 0, 3, 0)
                lbl.setToolTip(important_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.ITEM_COL, lbl)
                w = strip.width() + 8
                if w > self._item_col_w:
                    self._item_col_w = w

            # 配置敵列: スプライト帯。内訳は tooltip + CSV。
            pstrip = self._compose_enemy_strip(placed_ordered, tileset_no)
            if pstrip is not None and not pstrip.isNull():
                plbl = QLabel()
                plbl.setPixmap(pstrip)
                plbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                plbl.setContentsMargins(3, 0, 3, 0)
                plbl.setToolTip(placed_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.PLACED_COL, plbl)
                pw = pstrip.width() + 8
                if pw > self._placed_col_w:
                    self._placed_col_w = pw

            # ミラー敵列: スプライト帯。内訳は tooltip + CSV。
            mstrip = self._compose_enemy_strip(mirror_ordered, tileset_no)
            if mstrip is not None and not mstrip.isNull():
                mlbl = QLabel()
                mlbl.setPixmap(mstrip)
                mlbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                mlbl.setContentsMargins(3, 0, 3, 0)
                mlbl.setToolTip(mirror_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.MIRROR_COL, mlbl)
                mw = mstrip.width() + 8
                if mw > self._mirror_col_w:
                    self._mirror_col_w = mw

            self.table.setRowHeight(row, max(36, ITEM_THUMB + 8))

        self.table.resizeColumnsToContents()
        # スプライト帯の列はそれぞれの最大幅に合わせる
        self.table.setColumnWidth(self.PLACED_COL, max(260, self._placed_col_w))
        self.table.setColumnWidth(self.MIRROR_COL, max(200, self._mirror_col_w))
        self.table.setColumnWidth(self.ITEM_COL, max(380, self._item_col_w))

    @staticmethod
    def _add_item_state_count(normal_count, hidden_count, in_block_count, state):
        if state == "normal":
            normal_count += 1
        elif state == "hidden":
            hidden_count += 1
        else:
            in_block_count += 1
        return normal_count, hidden_count, in_block_count

    @staticmethod
    def _add_important_item(important_buckets, base, state):
        if base not in important_buckets:
            important_buckets[base] = {"normal": 0, "hidden": 0, "in_block": 0}
        important_buckets[base][state] += 1

    def _on_double_click(self, item):
        row = item.row()
        # 親のレベル切替
        parent = self.parent()
        if parent and hasattr(parent, "spin_level"):
            parent.spin_level.setValue(row + 1)
            self.statusbar_message(f"L{row + 1} に移動")

    def statusbar_message(self, msg):
        parent = self.parent()
        if parent and hasattr(parent, "statusBar"):
            parent.statusBar().showMessage(msg, 3000)

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV出力先", "level_stats.csv", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                # ヘッダ
                headers = [h for h, _ in self.COLUMNS]
                f.write(",".join(headers) + "\n")
                for row in range(self.table.rowCount()):
                    cells = []
                    for col in range(self.table.columnCount()):
                        if col == self.ITEM_COL:
                            text = self._csv_item_text.get(row, "")
                        elif col == self.PLACED_COL:
                            text = self._csv_placed_text.get(row, "")
                        elif col == self.MIRROR_COL:
                            text = self._csv_mirror_text.get(row, "")
                        else:
                            item = self.table.item(row, col)
                            text = item.text() if item else ""
                        # CSV-safe: replace newlines, escape quotes
                        text = text.replace("\n", " / ").replace('"', '""')
                        if "," in text:
                            text = f'"{text}"'
                        cells.append(text)
                    f.write(",".join(cells) + "\n")
            QMessageBox.information(self, "完了", f"CSV出力完了\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "CSV出力失敗", f"{type(e).__name__}: {e}")
