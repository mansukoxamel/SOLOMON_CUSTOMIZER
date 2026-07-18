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
SORT_ROLE = Qt.UserRole + 1
CSV_ROLE = Qt.UserRole + 2
TOTAL_ROW_ROLE = Qt.UserRole + 3

from ..core import constants as c
from ..core.element import Wall
from ..core import room_flags as _rf
from ..core import stage_ext as _se
from ..core.i18n import t
from .element_picker import (
    ENEMY_PICKER_PALETTE_OVERRIDE,
    ENEMY_VISUAL_SOURCE,
    ITEMS_LIST,
    apply_enemy_picker_overlay,
)


# ★重要アイテムの「コード一覧」のみ(=どれを集計するか・順序)。
#   名前は持たない=2重管理しない。表示名は skc_config.xml item_desc
#   (self.config.item_desc) 単一ソースから解決する。
IMPORTANT_ITEMS = [
    0x20, 0x22, 0x1c, 0x1d, 0x1e, 0x1f,
    0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x21,
]

# Item pickup scores confirmed against the original JP ROM score routines:
# $C803/$C80A/$C7B5 direct calls and $C571-$C595 high-score item ladder.
# Non-score/effect-only items are intentionally omitted and default to 0.
ITEM_SCORE_TABLE = {
    0x08: 500,
    0x0A: 2000,
    0x0C: 2000,
    0x1B: 200,
    0x25: 100,
    0x26: 200,
    0x27: 500,
    0x28: 1000,
    0x29: 2000,
    0x2A: 5000,
    0x2B: 10000,
    0x2C: 20000,
    0x2D: 50000,
    0x2E: 100000,
    0x2F: 200000,
    0x30: 500000,
    0x31: 1000000,
    0x32: 500000,
    0x38: 500000,
    0x39: 500000,
}

FEATURED_ENTITY_ORDER = [
    ("item", 0x22),          # Warp Item
    ("item", 0x1c),          # Shrine #1
    ("item", 0x1d),          # Shrine #2
    ("item", 0x1e),          # Shrine #3
    ("item", 0x1f),          # Shrine #4
    ("item", 0x20),          # Solomon's Seal
    ("item", 0x21),          # Page of Time / Space
]
FEATURED_ENTITY_SET = set(FEATURED_ENTITY_ORDER)

IMPORTANT_ENTITY_ORDER = (
    [
        ("item", code) for code in IMPORTANT_ITEMS
        if ("item", code) not in FEATURED_ENTITY_SET
    ] +
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


def _level_meta_all_item_code(meta_item) -> int | None:
    """level_meta_items のうち、全アイテム列へ合算する item code を返す。"""
    key = _level_meta_important_key(meta_item)
    if key is not None and key[0] == "item":
        return key[1]
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


class StatsTableItem(QTableWidgetItem):
    """ソート用データを優先して比較するテーブルセル。"""

    @staticmethod
    def _sort_key(value):
        if value is None:
            return (2, "")
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, (int, float)):
            return (0, value)
        return (1, str(value))

    def __lt__(self, other):
        left_total = bool(self.data(TOTAL_ROW_ROLE))
        right_total = bool(other.data(TOTAL_ROW_ROLE)) if other is not None else False
        if left_total != right_total:
            return (not left_total) and right_total
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE) if other is not None else None
        if left is not None and right is not None:
            return self._sort_key(left) < self._sort_key(right)
        return super().__lt__(other)


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
        ("特殊扉", 60),     # door state bits
        ("妖精化", 64),     # special process: first enemy falling-death -> Fairy
        ("配置敵", 300),    # 配置された敵 スプライト
        ("ミラー敵", 240),  # ミラーから出る敵 スプライト
        ("主要", 180),      # Warp/星座パネル/Solomon/Page スプライト
        ("重要アイテム", 380),  # スプライト
        ("全アイテム", 520),    # ピッカー順の全アイテム集計 スプライト
        ("理論得点", 100),      # 配置アイテムを全取得した場合の取得時得点
        ("ブロック", 360),
    ]
    # ヘッダ名 → 列インデックス (ハードコード排除)
    _HDR = [h for h, _ in COLUMNS]
    LV_COL = 0
    NORMAL_COL = _HDR.index("通常")
    HIDDEN_COL = _HDR.index("隠し")
    INBLK_COL = _HDR.index("in_blk")
    ENEMY_COUNT_COL = _HDR.index("敵数")
    BLOCK_COL = _HDR.index("ブロック")
    TS_COL = _HDR.index("タイル")
    TIME_COL = _HDR.index("時間減少")
    LIFE_COL = _HDR.index("敵寿命\n約0.5秒x値")
    KEY_COL = _HDR.index("鍵")
    ASTONE_COL = _HDR.index("A禁止")
    BFIRE_COL = _HDR.index("B禁止")
    FIRE_RESET_COL = _HDR.index("火リセット")
    KEY_ENEMY_COL = _HDR.index("鍵敵#")
    DARK_COL = _HDR.index("暗闇")
    DOOR_COL = _HDR.index("特殊扉")
    FAIRY_DROP_COL = _HDR.index("妖精化")
    PLACED_COL = _HDR.index("配置敵")
    MIRROR_COL = _HDR.index("ミラー敵")
    FEATURED_COL = _HDR.index("主要")
    ITEM_COL = _HDR.index("重要アイテム")
    ALL_ITEM_COL = _HDR.index("全アイテム")
    SCORE_COL = _HDR.index("理論得点")
    FLAG_COLS = (ASTONE_COL, BFIRE_COL, FIRE_RESET_COL, DARK_COL, DOOR_COL, FAIRY_DROP_COL)
    NUM_COLS = (TS_COL, TIME_COL, LIFE_COL, SCORE_COL)  # 中央寄せする数値メタ列

    @staticmethod
    def _count_part(kind: str, count: int) -> str:
        return t(f"stats_dialog.count_part.{kind}", "{count}").format(count=count)

    def _state_count_parts(self, bucket) -> list:
        parts = []
        if bucket["normal"]:
            parts.append(self._count_part("normal", bucket["normal"]))
        if bucket["hidden"]:
            parts.append(self._count_part("hidden", bucket["hidden"]))
        if bucket["in_block"]:
            parts.append(self._count_part("in_block", bucket["in_block"]))
        return parts

    @staticmethod
    def _key_state_label(state: str) -> str:
        return t(f"stats_dialog.key_state.{state}", state)

    @staticmethod
    def _door_state_label(state: str) -> str:
        return t(f"stats_dialog.door_state.{state}", state)

    def __init__(self, levels, item_desc=None, config=None,
                 tile_renderer=None, app_config=None, rom=None, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t(
            "stats_dialog.title",
            "全ステージ統計 ({count}ステージ)",
        ).format(count=len(levels)))
        self.setModal(False)
        self.resize(1280, 720)
        self.levels = levels
        self.item_desc = item_desc or {}
        self.config = config
        self.tile_renderer = tile_renderer
        self.rom = rom                  # ミラー実データ読出用 (m66 layout)
        self._app_config = app_config   # サイズ/位置 復元用 (None=保存しない)
        self._sprite_cache = {}   # (item base_code, tileset_no) -> QPixmap
        self._enemy_cache = {}    # (enemy code, tileset_no) -> QPixmap
        self._block_cache = {}    # (block key, tileset_no) -> QPixmap
        self._item_col_w = 0      # 重要アイテム列の最大ピクセル幅
        self._all_item_col_w = 0  # 全アイテム列の最大ピクセル幅
        self._featured_col_w = 0  # 主要列の最大ピクセル幅
        self._placed_col_w = 0    # 配置敵列の最大ピクセル幅
        self._mirror_col_w = 0    # ミラー敵列の最大ピクセル幅
        self._block_col_w = 0     # ブロック列の最大ピクセル幅
        self._csv_featured_text = {} # row -> 主要内訳 (CSV用)
        self._csv_item_text = {}   # row -> 重要アイテム内訳 (CSV用)
        self._csv_all_item_text = {} # row -> 全アイテム内訳 (CSV用)
        self._csv_placed_text = {} # row -> 配置敵内訳 (CSV用)
        self._csv_mirror_text = {} # row -> ミラー敵内訳 (CSV用)
        self._csv_block_text = {} # row -> ブロック内訳 (CSV用)

        layout = QVBoxLayout(self)

        # 説明
        info = QLabel(t(
            "stats_dialog.info_html",
            "「主要」列はWarp/星座パネル/Solomon's Seal/Pageを集計。「重要アイテム」列は"
            "Origami Swan/Demonhead Coin/"
            "Sphinx/Egyptian Head/Magic Lamp/E-bottle/Tecmo Bunny と、"
            "特殊扱いの Mighty Bomb Jack/Fairy/Fairy Princess を集計(コイン/宝石/"
            "Bell/Scroll/タイマー系などは除外)。「全アイテム」列は"
            "主要/重要アイテム列に出したものを除き、通常/隠し/ブロック内を"
            "区別せずベースアイテム別に集計。「配置敵」=面に置かれた敵"
            "(実数 ×N)、「ミラー敵」=デーモンミラーから出る敵(種類のみ・"
            "無スケジュールのミラーは除外)。「ブロック」=空気以外の通常/特殊"
            "ブロック内訳。<br>"
            "「妖精化」=落下死で妖精化する敵が設定されているステージ。<br>"
            "「理論得点」=配置されているアイテムをすべて取得した場合の取得時得点"
            "(到達可否、残りTIME換算、スコア倍率の副作用は除外)。<br>"
            "セルをダブルクリックでそのステージへジャンプ。",
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        # テーブル
        self.table = QTableWidget(len(levels) + 1, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels([
            t(f"stats_dialog.column.{i}", h)
            for i, (h, _width) in enumerate(self.COLUMNS)
        ])
        featured_header = self.table.horizontalHeaderItem(self.FEATURED_COL)
        if featured_header is not None:
            featured_header.setToolTip(
                t(
                    "stats_dialog.tooltip.featured",
                    "Warp / 星座パネル / Solomon's Seal / Page を専用表示します。",
                )
            )
        item_header = self.table.horizontalHeaderItem(self.ITEM_COL)
        if item_header is not None:
            item_header.setToolTip(
                t(
                    "stats_dialog.tooltip.important_items",
                    "重要アイテム列の枠色:\n"
                    "黄 = 隠し / 緑 = ブロック内 / 灰 = 通常\n"
                    "右下の数字は同種アイテムの合計数です。",
                )
            )
        all_item_header = self.table.horizontalHeaderItem(self.ALL_ITEM_COL)
        if all_item_header is not None:
            all_item_header.setToolTip(
                t(
                    "stats_dialog.tooltip.all_items",
                    "全アイテム列は通常/隠し/ブロック内を区別せず、"
                    "主要/重要アイテム列に出したものを除いてベースアイテム別に合算します。\n"
                    "表示順はピッカー順です。右下の数字は同種アイテムの合計数です。",
                )
            )
        block_header = self.table.horizontalHeaderItem(self.BLOCK_COL)
        if block_header is not None:
            block_header.setToolTip(
                t(
                    "stats_dialog.tooltip.blocks",
                    "空気以外の通常/特殊ブロック内訳です。\n"
                    "茶/白/壊白/透壊/通白/通茶/透固/固茶 などを集計します。",
                )
            )
        score_header = self.table.horizontalHeaderItem(self.SCORE_COL)
        if score_header is not None:
            score_header.setToolTip(
                t(
                    "stats_dialog.tooltip.score",
                    "配置されているアイテムをすべて取った場合の取得時得点です。\n"
                    "到達可否、残りTIMEのクリア時換算、スコア倍率の副作用は含めません。",
                )
            )
        for i, (_, w) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(i, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        # 「…」省略をやめ全文表示。列幅はユーザーが調整可(保存対象)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        self._populate()
        self.table.setSortingEnabled(True)
        self.table.sortItems(self.LV_COL, Qt.AscendingOrder)
        layout.addWidget(self.table)

        # ボタン行
        btn_row = QHBoxLayout()
        self.btn_csv = QPushButton(t("stats_dialog.csv.button", "CSV出力"))
        self.btn_csv.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self.btn_csv)
        btn_row.addStretch()
        self.btn_close = QPushButton(t("common.close", "閉じる"))
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

    def _ordered_featured_buckets(self, featured_buckets):
        """主要列を Warp / 星座パネル / Solomon's Seal / Page の順に並べる。"""
        ordered = []
        for key in FEATURED_ENTITY_ORDER:
            if key in featured_buckets:
                ordered.append((key, self._important_label(key), featured_buckets[key]))
        return ordered

    def _ordered_all_item_buckets(self, item_counts):
        """全アイテム列をピッカー順優先で並べる。状態は区別せず合算済み。"""
        ordered = []
        seen = set()
        for code in ITEMS_LIST:
            if item_counts.get(code, 0) <= 0:
                continue
            seen.add(code)
            ordered.append((
                ("item", code),
                self._important_label(("item", code)),
                {"normal": item_counts[code], "hidden": 0, "in_block": 0},
            ))
        for code in sorted(k for k in item_counts if k not in seen):
            ordered.append((
                ("item", code),
                self._important_label(("item", code)),
                {"normal": item_counts[code], "hidden": 0, "in_block": 0},
            ))
        return ordered

    def _enemy_pixmap(self, code: int, tileset_no: int) -> QPixmap:
        """敵 element_no の ITEM_THUMB スプライト。
        element_picker._make_enemy_icon と同じルート (enemy_map)。"""
        cache_key = (code, tileset_no)
        if cache_key in self._enemy_cache:
            return self._enemy_cache[cache_key]
        if self.tile_renderer is None or self.config is None:
            return QPixmap()
        try:
            visual_code = ENEMY_VISUAL_SOURCE.get(code, code)
            anim = self.config.enemy_map.get(visual_code, 0)
            sprite = self.tile_renderer.get_tile_image(
                anim,
                tileset_no,
                transparent=True,
                palette_no_override=ENEMY_PICKER_PALETTE_OVERRIDE.get(code),
            )
            sprite = apply_enemy_picker_overlay(sprite, code)
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

    def _block_pixmap(self, key: str, tileset_no: int) -> QPixmap:
        cache_key = (key, tileset_no)
        if cache_key in self._block_cache:
            return self._block_cache[cache_key]
        if self.tile_renderer is None or self.config is None:
            return QPixmap()
        from ..gfx.level_renderer import MD_EMPTY, MD_BLOCK_BROWN, MD_BLOCK_WHITE
        meta = {
            "茶": MD_BLOCK_BROWN,
            "ひび": None,
            "白": MD_BLOCK_WHITE,
            "茶白": MD_BLOCK_WHITE,
            "壊白": MD_BLOCK_WHITE,
            "透壊": MD_EMPTY,
            "通白": MD_BLOCK_WHITE,
            "通茶": MD_BLOCK_BROWN,
            "透固": MD_EMPTY,
            "固茶": MD_BLOCK_BROWN,
        }.get(key, MD_EMPTY)
        colors = {
            "茶": QColor(120, 80, 40),
            "ひび": QColor(255, 210, 80),
            "白": QColor(150, 150, 150),
            "茶白": QColor(80, 150, 255),
            "壊白": QColor(80, 230, 90),
            "透壊": QColor(255, 220, 40),
            "通白": QColor(80, 190, 255),
            "通茶": QColor(80, 190, 255),
            "透固": QColor(255, 120, 220),
            "固茶": QColor(255, 120, 220),
        }
        try:
            if key == "ひび":
                anim = self.config.item_map.get(0x01, 0)
            else:
                anim = self.config.metadata_map.get(meta, 0)
            sprite = self.tile_renderer.get_tile_image(anim, tileset_no, transparent=False)
            bg = QImage(ITEM_THUMB, ITEM_THUMB, QImage.Format_ARGB32)
            bg.fill(QColor(20, 20, 20))
            p = QPainter(bg)
            scaled = sprite.scaled(ITEM_THUMB, ITEM_THUMB,
                                   Qt.KeepAspectRatio, Qt.FastTransformation)
            ox = (ITEM_THUMB - scaled.width()) // 2
            oy = (ITEM_THUMB - scaled.height()) // 2
            p.drawImage(ox, oy, scaled)
            pen = colors.get(key, QColor(90, 90, 90))
            p.setPen(pen)
            p.drawRect(1, 1, ITEM_THUMB - 3, ITEM_THUMB - 3)
            p.end()
            pm = QPixmap.fromImage(bg)
        except Exception:
            pm = QPixmap()
        self._block_cache[cache_key] = pm
        return pm

    def _compose_block_strip(self, counts: dict, tileset_no: int,
                             wrap_width: int = 0, show_text: bool = False) -> QPixmap:
        order = ["茶", "ひび", "白", "茶白", "壊白", "透壊", "通白", "通茶", "透固", "固茶"]
        entries = [(key, counts[key]) for key in order if counts.get(key, 0) > 0]
        entries.extend((key, counts[key]) for key in sorted(counts) if key not in order and counts.get(key, 0) > 0)
        if not entries:
            return None
        label_w = 34 if show_text else 0
        cell_w = ITEM_THUMB + 2 + label_w
        cell_h = ITEM_THUMB + 2
        max_cells = len(entries)
        if wrap_width > 0:
            max_cells = max(1, wrap_width // (cell_w + ITEM_GAP))
        rows = (len(entries) + max_cells - 1) // max_cells
        cols = min(max_cells, len(entries))
        strip_w = cols * cell_w + max(0, cols - 1) * ITEM_GAP
        strip_h = rows * cell_h + max(0, rows - 1) * ITEM_GAP
        strip = QImage(strip_w, strip_h, QImage.Format_ARGB32)
        strip.fill(QColor(0, 0, 0, 0))
        p = QPainter(strip)
        p.setRenderHint(QPainter.Antialiasing, False)
        for idx, (key, count) in enumerate(entries):
            row = idx // max_cells
            col = idx % max_cells
            x = col * (cell_w + ITEM_GAP)
            y = row * (cell_h + ITEM_GAP)
            pm = self._block_pixmap(key, tileset_no)
            p.drawPixmap(x + 1, y + 1, pm)
            p.setPen(QColor(255, 255, 255))
            p.fillRect(x + ITEM_THUMB - 11, y + ITEM_THUMB - 10, 13, 11,
                       QColor(0, 0, 0, 170))
            p.drawText(x + ITEM_THUMB - 10, y + ITEM_THUMB - 1, str(count))
            if show_text:
                p.drawText(x + ITEM_THUMB + 5, y + 18, key)
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

    @staticmethod
    def _add_count(target: dict, key: str, amount: int = 1):
        target[key] = target.get(key, 0) + int(amount)

    @staticmethod
    def _merge_counts(target: dict, source: dict):
        for key, value in source.items():
            target[key] = target.get(key, 0) + int(value)

    def _block_counts(self, lv) -> dict:
        counts = {}
        breakable_white = set(getattr(lv, "breakable_white_cells", set()) or [])
        cracked_block = set(getattr(lv, "cracked_block_cells", set()) or [])
        invisible_breakable = set(getattr(lv, "invisible_breakable_cells", set()) or [])
        passable_white = set(getattr(lv, "passable_white_cells", set()) or [])
        invisible_solid = set(getattr(lv, "invisible_solid_cells", set()) or [])
        passable_brown = set(getattr(lv, "passable_brown_cells", set()) or [])
        solid_brown = set(getattr(lv, "solid_brown_cells", set()) or [])
        for y, row in enumerate(getattr(lv, "tiles", []) or []):
            for x, wall in enumerate(row):
                pos = (x, y)
                if pos in breakable_white:
                    key = "壊白"
                elif pos in cracked_block:
                    key = "ひび"
                elif pos in invisible_breakable:
                    key = "透壊"
                elif pos in passable_white:
                    key = "通白"
                elif pos in invisible_solid:
                    key = "透固"
                elif pos in passable_brown:
                    key = "通茶"
                elif pos in solid_brown:
                    key = "固茶"
                elif wall == Wall.BROWN:
                    key = "茶"
                elif wall == Wall.WHITE:
                    key = "白"
                elif wall == Wall.BROWN_WHITE:
                    key = "茶白"
                else:
                    continue
                self._add_count(counts, key)
        return counts

    @staticmethod
    def _counts_text(counts: dict, order: list = None) -> str:
        if not counts:
            return "-"
        keys = []
        if order:
            keys.extend([key for key in order if counts.get(key, 0) > 0])
        keys.extend(sorted(key for key in counts if key not in keys and counts.get(key, 0) > 0))
        return " / ".join(f"{key}×{counts[key]}" for key in keys) if keys else "-"

    def _populate(self):
        grand_score = 0
        grand_normal = 0
        grand_hidden = 0
        grand_in_block = 0
        grand_enemy_count = 0
        grand_all_item_counts = {}
        grand_placed_enemy_counts = {}
        grand_block_counts = {}
        for row, lv in enumerate(self.levels):
            tileset_no = int(getattr(lv, "tileset_no", 0) or 0)
            # アイテム集計
            normal_count = 0
            hidden_count = 0
            in_block_count = 0
            level_score = 0
            featured_buckets = {}   # (source, code) -> {state: count}
            important_buckets = {}  # (source, code) -> {state: count}
            all_item_counts = {}     # base item code -> count, state ignored
            for it in lv.items:
                flag = it.element_no & 0xC0
                base = it.element_no & 0x3F
                level_score += self._item_score(base)
                if it.position in getattr(lv, "visible_in_block_item_cells", set()):
                    state = "in_block"
                else:
                    state = "hidden" if flag == 0x40 else ("in_block" if flag in (0x80, 0xC0) else "normal")
                normal_count, hidden_count, in_block_count = self._add_item_state_count(
                    normal_count, hidden_count, in_block_count, state)
                # 重要アイテム
                key = _item_important_key(base)
                if key in FEATURED_ENTITY_SET:
                    self._add_important_item(featured_buckets, key, state)
                elif key in IMPORTANT_ENTITY_SET:
                    self._add_important_item(important_buckets, key, state)
                else:
                    all_item_counts[base] = all_item_counts.get(base, 0) + 1

            meta_items = getattr(self.config, "level_meta_items", []) if self.config else []
            for mi in meta_items:
                if getattr(mi, "level_no", -1) != row:
                    continue
                key = _level_meta_important_key(mi)
                if key not in FEATURED_ENTITY_SET and key not in IMPORTANT_ENTITY_SET:
                    continue
                state = _level_meta_item_state(lv, mi)
                normal_count, hidden_count, in_block_count = self._add_item_state_count(
                    normal_count, hidden_count, in_block_count, state)
                all_code = _level_meta_all_item_code(mi)
                if all_code is not None:
                    level_score += self._item_score(all_code)
                    all_key = _item_important_key(all_code)
                    if all_key not in FEATURED_ENTITY_SET and all_key not in IMPORTANT_ENTITY_SET:
                        all_item_counts[all_code] = all_item_counts.get(all_code, 0) + 1
                if key in FEATURED_ENTITY_SET:
                    self._add_important_item(featured_buckets, key, state)
                else:
                    self._add_important_item(important_buckets, key, state)

            for en in lv.enemies:
                key = _enemy_important_key(en, self.config)
                if key in IMPORTANT_ENTITY_SET:
                    self._add_important_item(important_buckets, key, "normal")

            key_enemy_no = _se.get_key_enemy_number(lv)
            key_enemy_text = str(key_enemy_no) if key_enemy_no > 0 else ""

            # 鍵状態 (座標は表示しない)
            if lv.is_key_removed():
                key_state = self._key_state_label("removed")
            elif lv.fixed_key_pos in getattr(lv, "visible_in_block_item_cells", set()):
                key_state = self._key_state_label("visible_in_block")
            elif lv.is_key_white_in_block():
                key_state = self._key_state_label("white_in_block")
            elif lv.is_key_in_block():
                key_state = self._key_state_label("in_block")
            elif lv.is_key_hidden():
                key_state = self._key_state_label("hidden")
            else:
                key_state = self._key_state_label("normal")

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
            door_state = rf & _rf.DOOR_STATE_MASK
            if lv.is_door_removed():
                f_door = self._door_state_label("removed")
            else:
                f_door = {
                    _rf.DOOR_STATE_HIDDEN: self._door_state_label("hidden"),
                    _rf.DOOR_STATE_IN_BLOCK: self._door_state_label("in_block"),
                    _rf.DOOR_STATE_WHITE_IN_BLOCK: self._door_state_label("white_in_block"),
                }.get(door_state, "")
            f_fire_reset = "●" if _se.fire_reset_enabled(lv) else ""
            f_fairy_drop = "●" if self._falling_fairy_enabled(row) else ""

            # 主要列文字列 + スプライト用 featured_ordered_buckets
            featured_ordered_buckets = self._ordered_featured_buckets(featured_buckets)
            featured_strs = []
            for key, label, b in featured_ordered_buckets:
                parts = self._state_count_parts(b)
                featured_strs.append(f"{label}[{','.join(parts)}]")
            featured_text = " / ".join(featured_strs) if featured_strs else "-"
            self._csv_featured_text[row] = featured_text

            # 重要アイテム文字列 + スプライト用 ordered_buckets
            important_strs = []
            ordered_buckets = []
            for key in IMPORTANT_ENTITY_ORDER:
                if key in important_buckets:
                    label = self._important_label(key)
                    b = important_buckets[key]
                    parts = self._state_count_parts(b)
                    important_strs.append(f"{label}[{','.join(parts)}]")
                    ordered_buckets.append((key, label, b))
            important_text = " / ".join(important_strs) if important_strs else "-"
            self._csv_item_text[row] = important_text  # CSV出力用に保持

            all_item_ordered_buckets = self._ordered_all_item_buckets(all_item_counts)
            all_item_strs = []
            for key, label, b in all_item_ordered_buckets:
                total = b["normal"] + b["hidden"] + b["in_block"]
                all_item_strs.append(f"{label}×{total}" if total > 1 else label)
            all_item_text = " / ".join(all_item_strs) if all_item_strs else "-"
            self._csv_all_item_text[row] = all_item_text
            self._merge_counts(grand_all_item_counts, all_item_counts)

            block_counts = self._block_counts(lv)
            block_text = self._counts_text(
                block_counts,
                ["茶", "白", "茶白", "壊白", "透壊", "通白", "通茶", "透固", "固茶"],
            )
            self._csv_block_text[row] = block_text
            self._merge_counts(grand_block_counts, block_counts)

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
            for en in placed_enemies:
                self._add_count(grand_placed_enemy_counts, self._enemy_base(en.element_no))

            # ミラー敵 (基底名で重複排除し各 1)
            mbases = {}
            for ec in self._mirror_spawn_codes(row):
                b = self._enemy_base(ec)
                if b not in mbases or ec < mbases[b]:
                    mbases[b] = ec
            mirror_ordered, mirror_text = _group(
                [(ec, 1) for ec in mbases.values()])
            self._csv_mirror_text[row] = mirror_text
            grand_score += level_score
            grand_normal += normal_count
            grand_hidden += hidden_count
            grand_in_block += in_block_count
            grand_enemy_count += len(placed_enemies)

            # セル設定 (COLUMNS と同じ並び。スプライト列はテキスト空)
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
                f_door,                           # 特殊扉
                f_fairy_drop,                     # 妖精化
                "",                               # 配置敵(sprite)
                "",                               # ミラー敵(sprite)
                "",                               # 主要(sprite)
                "",                               # 重要アイテム(sprite)
                "",                               # 全アイテム(sprite)
                self._score_text(level_score),    # 理論得点
                block_text,                       # ブロック
            ]
            sort_values = [
                row + 1,                          # Lv
                normal_count,                     # 通常
                hidden_count,                     # 隠し
                in_block_count,                   # in_blk
                len(placed_enemies),              # 敵数
                tileset_no,                       # タイル
                int(getattr(lv, "time_decrease_rate", 0)),    # 時間減少
                int(getattr(lv, "spawn_enemy_lifetime", 0)),  # 敵寿命
                key_state,                        # 鍵
                const_state,                      # 星座
                1 if f_astone else 0,             # A禁止
                1 if f_bfire else 0,              # B禁止
                1 if f_fire_reset else 0,         # 火リセット
                key_enemy_no,                     # 鍵敵#
                1 if f_dark else 0,               # 暗闇
                1 if f_door else 0,               # 特殊扉
                1 if f_fairy_drop else 0,         # 妖精化
                "",                              # 配置敵: ソート対象外
                "",                              # ミラー敵: ソート対象外
                "",                              # 主要: ソート対象外
                "",                              # 重要アイテム: ソート対象外
                sum(all_item_counts.values()),   # 全アイテム
                level_score,                     # 理論得点
                sum(block_counts.values()),       # ブロック
            ]
            csv_values = {
                self.BLOCK_COL: block_text,
                self.PLACED_COL: placed_text,
                self.MIRROR_COL: mirror_text,
                self.FEATURED_COL: featured_text,
                self.ITEM_COL: important_text,
                self.ALL_ITEM_COL: all_item_text,
            }
            for col, txt in enumerate(cells):
                item = StatsTableItem(txt)
                if col == self.SCORE_COL:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif col in self.FLAG_COLS or col in self.NUM_COLS or col == self.KEY_ENEMY_COL:
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, row)  # レベル番号(0-indexed)
                item.setData(SORT_ROLE, sort_values[col])
                item.setData(TOTAL_ROW_ROLE, False)
                if col in csv_values:
                    item.setData(CSV_ROLE, csv_values[col])
                self.table.setItem(row, col, item)

            # 主要列: スプライト帯のみ表示(文字は出さない)。
            fstrip = self._compose_item_strip(featured_ordered_buckets, tileset_no)
            if fstrip is not None and not fstrip.isNull():
                flbl = QLabel()
                flbl.setPixmap(fstrip)
                flbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                flbl.setContentsMargins(3, 0, 3, 0)
                flbl.setToolTip(featured_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.FEATURED_COL, flbl)
                fw = fstrip.width() + 8
                if fw > self._featured_col_w:
                    self._featured_col_w = fw

            # 重要アイテム列: スプライト帯のみ表示(文字は出さない)。
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

            # 全アイテム列: 状態を無視したベースアイテム別スプライト帯。
            all_strip = self._compose_item_strip(all_item_ordered_buckets, tileset_no)
            if all_strip is not None and not all_strip.isNull():
                albl = QLabel()
                albl.setPixmap(all_strip)
                albl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                albl.setContentsMargins(3, 0, 3, 0)
                albl.setToolTip(all_item_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.ALL_ITEM_COL, albl)
                aw = all_strip.width() + 8
                if aw > self._all_item_col_w:
                    self._all_item_col_w = aw

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

            bstrip = self._compose_block_strip(block_counts, tileset_no)
            if bstrip is not None and not bstrip.isNull():
                blbl = QLabel()
                blbl.setPixmap(bstrip)
                blbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                blbl.setContentsMargins(3, 0, 3, 0)
                blbl.setToolTip(block_text.replace(" / ", "\n"))
                self.table.setCellWidget(row, self.BLOCK_COL, blbl)
                bw = bstrip.width() + 8
                if bw > self._block_col_w:
                    self._block_col_w = bw

            self.table.setRowHeight(row, max(36, ITEM_THUMB + 8))

        grand_all_item_strs = []
        seen_items = set()
        for code in ITEMS_LIST:
            if grand_all_item_counts.get(code, 0) > 0:
                grand_all_item_strs.append(
                    f"{self._important_label(('item', code))}×{grand_all_item_counts[code]}"
                )
                seen_items.add(code)
        for code in sorted(k for k in grand_all_item_counts if k not in seen_items):
            grand_all_item_strs.append(
                f"{self._important_label(('item', code))}×{grand_all_item_counts[code]}"
            )
        grand_all_item_text = " / ".join(grand_all_item_strs) if grand_all_item_strs else "-"
        grand_placed_text = self._counts_text(grand_placed_enemy_counts)
        grand_block_text = self._counts_text(
            grand_block_counts,
            ["茶", "白", "茶白", "壊白", "透壊", "通白", "通茶", "透固", "固茶"],
        )
        self._populate_total_row(
            len(self.levels),
            grand_score,
            {
                self.NORMAL_COL: grand_normal,
                self.HIDDEN_COL: grand_hidden,
                self.INBLK_COL: grand_in_block,
                self.ENEMY_COUNT_COL: grand_enemy_count,
                self.BLOCK_COL: grand_block_text,
                self.PLACED_COL: grand_placed_text,
                self.ALL_ITEM_COL: grand_all_item_text,
            },
        )
        self._populate_total_widgets(
            len(self.levels),
            grand_placed_text,
            grand_all_item_text,
            grand_block_counts,
        )
        self.table.resizeColumnsToContents()
        # スプライト帯の列はそれぞれの最大幅に合わせる
        self.table.setColumnWidth(self.PLACED_COL, max(260, self._placed_col_w))
        self.table.setColumnWidth(self.MIRROR_COL, max(200, self._mirror_col_w))
        self.table.setColumnWidth(self.FEATURED_COL, max(180, self._featured_col_w))
        self.table.setColumnWidth(self.ITEM_COL, max(380, self._item_col_w))
        self.table.setColumnWidth(self.ALL_ITEM_COL, max(420, self._all_item_col_w))
        self.table.setColumnWidth(self.BLOCK_COL, max(360, self._block_col_w))
        self.table.setColumnWidth(self.SCORE_COL, max(100, self.table.columnWidth(self.SCORE_COL)))

    @staticmethod
    def _item_score(base_code: int) -> int:
        return ITEM_SCORE_TABLE.get(base_code & 0x3F, 0)

    @staticmethod
    def _score_text(score: int) -> str:
        return f"{int(score):,}"

    def _populate_total_row(self, row: int, grand_score: int, totals: dict = None):
        totals = totals or {}
        for col in range(self.table.columnCount()):
            if col == self.LV_COL:
                text = t("stats_dialog.total", "合計")
                sort_value = 9999
            elif col == self.SCORE_COL:
                text = self._score_text(grand_score)
                sort_value = grand_score
            elif col in totals:
                value = totals[col]
                text = str(value)
                sort_value = value if isinstance(value, int) else text
            else:
                text = ""
                sort_value = ""
            item = StatsTableItem(text)
            item.setData(Qt.UserRole, -1)
            item.setData(SORT_ROLE, sort_value)
            item.setData(TOTAL_ROW_ROLE, True)
            item.setData(CSV_ROLE, text)
            item.setBackground(QColor(18, 52, 24))
            item.setForeground(QColor(120, 255, 90))
            if col in self.NUM_COLS or col in (
                self.NORMAL_COL, self.HIDDEN_COL, self.INBLK_COL, self.ENEMY_COUNT_COL
            ):
                item.setTextAlignment(Qt.AlignCenter)
            elif col == self.SCORE_COL:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, item)
        self.table.setRowHeight(row, 32)

    def _populate_total_widgets(self, row: int, placed_text: str,
                                all_item_text: str, block_counts: dict):
        for col, text in (
            (self.PLACED_COL, placed_text),
            (self.ALL_ITEM_COL, all_item_text),
        ):
            if not text or text == "-":
                continue
            lbl = QLabel(text.replace(" / ", "\n"))
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            lbl.setContentsMargins(3, 3, 3, 3)
            lbl.setToolTip(text.replace(" / ", "\n"))
            self.table.setCellWidget(row, col, lbl)

        bstrip = self._compose_block_strip(
            block_counts,
            0,
            wrap_width=max(360, self._block_col_w),
            show_text=True,
        )
        if bstrip is not None and not bstrip.isNull():
            lbl = QLabel()
            lbl.setPixmap(bstrip)
            lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            lbl.setContentsMargins(3, 3, 3, 3)
            lbl.setToolTip(self._counts_text(
                block_counts,
                ["茶", "白", "茶白", "壊白", "透壊", "通白", "通茶", "透固", "固茶"],
            ).replace(" / ", "\n"))
            self.table.setCellWidget(row, self.BLOCK_COL, lbl)
            self._block_col_w = max(self._block_col_w, bstrip.width() + 8)
            self.table.setRowHeight(row, max(72, bstrip.height() + 10))
        else:
            self.table.setRowHeight(row, 72)

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

    def _falling_fairy_enabled(self, level_no: int) -> bool:
        if not (0 <= level_no < len(self.levels)):
            return False
        return _se.get_fairy_enemy_number(self.levels[level_no]) > 0

    def _on_double_click(self, item):
        row = item.row()
        lv_item = self.table.item(row, self.LV_COL)
        level_no = lv_item.data(Qt.UserRole) if lv_item is not None else row
        try:
            level_no = int(level_no)
        except Exception:
            level_no = row
        if level_no < 0:
            return
        # 親のレベル切替
        parent = self.parent()
        if parent and hasattr(parent, "spin_level"):
            parent.spin_level.setValue(level_no + 1)
            self.statusbar_message(t(
                "stats_dialog.jump.status",
                "L{level} に移動",
            ).format(level=level_no + 1))

    def statusbar_message(self, msg):
        parent = self.parent()
        if parent and hasattr(parent, "statusBar"):
            parent.statusBar().showMessage(msg, 3000)

    def _on_export_csv(self):
        from .file_dialog_compat import get_path
        path = get_path(
            self,
            title=t("stats_dialog.csv.save_title", "CSV出力先"),
            directory="level_stats.csv",
            filter=t("common.file_filter.csv", "CSV files (*.csv);;All files (*)"),
            mode="save",
            app_config=self._app_config,
            config_key="stats_csv_export",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                # ヘッダ
                headers = [
                    t(f"stats_dialog.column.{i}", h)
                    for i, (h, _width) in enumerate(self.COLUMNS)
                ]
                f.write(",".join(headers) + "\n")
                for row in range(self.table.rowCount()):
                    cells = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if col in (
                            self.ITEM_COL, self.ALL_ITEM_COL, self.FEATURED_COL,
                            self.PLACED_COL, self.MIRROR_COL,
                        ):
                            text = item.data(CSV_ROLE) if item else ""
                        else:
                            text = item.text() if item else ""
                        if text is None:
                            text = ""
                        # CSV-safe: replace newlines, escape quotes
                        text = text.replace("\n", " / ").replace('"', '""')
                        if "," in text:
                            text = f'"{text}"'
                        cells.append(text)
                    f.write(",".join(cells) + "\n")
            QMessageBox.information(
                self,
                t("common.complete", "完了"),
                t("stats_dialog.csv.complete", "CSV出力完了\n{path}").format(path=path),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                t("stats_dialog.csv.failed.title", "CSV出力失敗"),
                f"{type(e).__name__}: {e}",
            )
