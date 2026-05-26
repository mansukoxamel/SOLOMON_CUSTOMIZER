"""要素選択ピッカー - キャラクター画像付き"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QButtonGroup, QRadioButton, QListWidget, QListWidgetItem,
    QListView, QAbstractItemView, QStackedWidget, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt5.QtGui import QPixmap, QIcon, QImage, QDrag


# 選択モード
MODE_BLOCK = "block"
MODE_ITEM = "item"
MODE_ENEMY = "enemy"
MODE_META = "meta"


# ブロックの種類
BLOCK_NONE = "none"
BLOCK_BROWN = "brown"
BLOCK_WHITE = "white"
BLOCK_BROWN_WHITE = "brown_white"  # 見た目=白、実体=壊せる（茶＋白の両ビット）
BLOCK_BREAKABLE_WHITE = "breakable_white"
BLOCK_INVISIBLE_BREAKABLE = "invisible_breakable"
BLOCK_PASSABLE_WHITE = "passable_white"
BLOCK_INVISIBLE_SOLID = "invisible_solid"


# アイテムフラグ
ITEM_FLAG_NORMAL = 0x00
ITEM_FLAG_HIDDEN = 0x40
ITEM_FLAG_IN_BLOCK = 0x80


# 配置レギュレーション: 必ず隠し で配置すべきアイテムコード（USA ROM 検証済）
# 選択時に自動的に hidden ラジオに切り替える
HIDDEN_ONLY_ITEMS = {0x22, 0x2e, 0x2f, 0x30, 0x31, 0x32}


# アイテム一覧（コード, 表示名）
# ★出典: skc_config.xml <item_definitions> を正本に自前抽出した
#   「配置可能(normal/modifiable)」46件 (2026-05-17、PRG_SPRITE_USAGE
#   と相互検証済 / output/PICKER_EXTRACT_20260517)。glitch/garbage/
#   Nothing 18件は配置で壊れ得るため除外（従来どおり非表示）。
#   旧36件版は $05/$09/$0A/$0B/$0D/$0F/$21/$37/$38/$39 が欠落していた。
# ★アイテム名の正本は skc_config.xml の item_definitions(=cfg.item_desc)
#   ★のみ★。ここはピッカーに出す「どのコードを・どの順で」だけを持つ
#   (=キュレーション。名前は持たない=2重管理しない)。表示名は必ず
#   item_name(code, config) 経由で item_desc から解決すること。
ITEMS_LIST = [
    0x04, 0x05, 0x08, 0x0b, 0x0c,
    0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a,
    0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x25, 0x26,
    0x27, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x30,
    0x31, 0x32, 0x33, 0x37, 0x38, 0x39,
]


def item_name(code, config):
    """アイテム名の唯一の解決経路。正本 = skc_config.xml item_desc。
    config未設定/未登録コードは 0xXX 表記にフォールバック。"""
    if config is not None:
        d = getattr(config, "item_desc", None)
        if d:
            n = d.get(code)
            if n:
                return n
    return f"0x{code:02x}"


# 主要敵一覧（コード=sp1基準, 表示名）
# スピードバリアントは ENEMY_SPEED_TABLE で動的に決まるため、ここには sp1 のみ載せる
ENEMIES_LIST = [
    # 大型敵（sp1/sp2、Demonhead/Saramandor は sp3 もあり）
    (0x68, "Dragon (right)"),
    (0x69, "Dragon (left)"),
    (0x70, "Golem (right)"),
    (0x71, "Golem (left)"),
    (0x78, "Gargoyle (right)"),
    (0x79, "Gargoyle (left)"),
    (0x7a, "Gargoyle 2-shot (right)"),
    (0x7b, "Gargoyle 2-shot (left)"),
    (0x50, "Demonhead (R)"),
    (0x51, "Demonhead (L)"),
    (0x5c, "Saramandor (R)"),
    (0x5d, "Saramandor (L)"),
    (0x5e, "Saramandor #2 (R)"),
    (0x5f, "Saramandor #2 (L)"),
    # 中型敵
    (0x34, "Ghost (right)"),
    (0x36, "Ghost (left)"),
    (0x30, "Neul (up)"),
    (0x32, "Neul (down)"),
    # 中型敵 noslow版（壁反転で減速しない凶悪版）
    (0x44, "Ghost (right, noslow)"),
    (0x46, "Ghost (left, noslow)"),
    (0x40, "Neul (up, noslow)"),
    (0x42, "Neul (down, noslow)"),
    # 小型/弾系
    (0x28, "Fireball (right)"),
    (0x29, "Fireball (left)"),
    (0x2a, "Fireball (up)"),
    (0x2b, "Fireball (down)"),
    (0x6a, "Spark Ball pause (up)"),
    (0x6b, "Spark Ball pause (down)"),
    (0x72, "Spark Ball invisible (up)"),
    (0x73, "Spark Ball invisible (down)"),
    (0x20, "Bullet (right)"),
    (0x21, "Bullet (left)"),
    (0x22, "Bullet (up)"),
    (0x23, "Bullet (down)"),
    # スピード非対応
    (0x80, "Red Flame"),
    (0x81, "White Flame"),
    (0x24, "Panel Monster (right)"),
    (0x25, "Panel Monster (left)"),
    (0x26, "Panel Monster (up)"),
    (0x27, "Panel Monster (down)"),
    (0x52, "Panel Monster 2-way (right)"),
    (0x53, "Panel Monster 2-way (left)"),
    (0x56, "Panel Monster 2-way (up)"),
    (0x57, "Panel Monster 2-way (down)"),
    (0x5a, "Panel Monster 3-way (right)"),
    (0x5b, "Panel Monster 3-way (left)"),
    (0x66, "Panel Monster 3-way (up)"),
    (0x67, "Panel Monster 3-way (down)"),
    (0x1c, "Fairy"),
    (0x1d, "Fairy Princess"),
    (0x18, "Mighty Bomb Jack (R)"),
    (0x19, "Mighty Bomb Jack (L)"),
]


# 敵コード → スピードバリアントの対応表
# キー: sp1 のコード、値: [sp1, sp2, sp3] (None = 該当 sp 無し)
ENEMY_SPEED_TABLE = {
    # Fireball: +4 で sp2
    0x28: [0x28, 0x2c, None],
    0x29: [0x29, 0x2d, None],
    0x2a: [0x2a, 0x2e, None],
    0x2b: [0x2b, 0x2f, None],
    # Neul (up/down): +8 で sp2
    0x30: [0x30, 0x38, None],
    0x32: [0x32, 0x3a, None],
    # Ghost (right/left): +8 で sp2
    0x34: [0x34, 0x3c, None],
    0x36: [0x36, 0x3e, None],
    # Neul noslow (up/down): +8 で sp2
    0x40: [0x40, 0x48, None],
    0x42: [0x42, 0x4a, None],
    # Ghost noslow (right/left): +8 で sp2
    0x44: [0x44, 0x4c, None],
    0x46: [0x46, 0x4e, None],
    # Demonhead: +4 ずつで sp2/sp3
    0x50: [0x50, 0x54, 0x58],
    0x51: [0x51, 0x55, 0x59],
    # Saramandor: +4 ずつで sp2/sp3
    0x5c: [0x5c, 0x60, 0x64],
    0x5d: [0x5d, 0x61, 0x65],
    0x5e: [0x5e, 0x62, 0x66],
    0x5f: [0x5f, 0x63, 0x67],
    # Dragon: +4 で sp2
    0x68: [0x68, 0x6c, None],
    0x69: [0x69, 0x6d, None],
    # Spark Ball pause variants borrowed from Dragon #2.
    0x6a: [0x6a, 0x6e, None],
    0x6b: [0x6b, 0x6f, None],
    # Spark Ball invisible variants borrowed from Golem #2.
    0x72: [0x72, 0x76, None],
    0x73: [0x73, 0x77, None],
    # Golem: +4 で sp2
    0x70: [0x70, 0x74, None],
    0x71: [0x71, 0x75, None],
    # Gargoyle: +4 で sp2
    0x78: [0x78, 0x7c, None],
    0x79: [0x79, 0x7d, None],
    0x7a: [0x7a, 0x7e, None],
    0x7b: [0x7b, 0x7f, None],
}


ENHANCED_ENEMY_CODES = {
    0x52, 0x53, 0x56, 0x57,  # Panel Monster 2-way
    0x5a, 0x5b, 0x66, 0x67,  # Panel Monster 3-way
    0x5e, 0x5f, 0x62, 0x63,  # Saramandor #2
    0x6a, 0x6b, 0x6e, 0x6f,  # Spark Ball pause
    0x72, 0x73, 0x76, 0x77,  # Spark Ball invisible
    0x7a, 0x7b, 0x7e, 0x7f,  # Gargoyle 2-shot
}


def apply_enemy_speed(base_code: int, speed: int) -> int:
    """sp1 ベースコードに speed (1/2/3) を適用して実コードを返す。
    対応がない場合は base_code をそのまま返す。"""
    table = ENEMY_SPEED_TABLE.get(base_code)
    if not table:
        return base_code
    idx = max(1, min(3, speed)) - 1
    val = table[idx]
    if val is None:
        # 該当 sp が無い → 一段下のスピードへフォールバック
        for i in range(idx - 1, -1, -1):
            if table[i] is not None:
                return table[i]
        return base_code
    return val


def base_code_from_actual(code: int) -> tuple:
    """実コードから (base_code, speed) を逆引き。見つからなければ (code, 1)"""
    for base, table in ENEMY_SPEED_TABLE.items():
        for sp_idx, c in enumerate(table):
            if c == code:
                return base, sp_idx + 1
    return code, 1


ICON_SIZE = 36  # アイコン表示サイズ（メタタイル16x16の約2.25倍）
GRID_PAD = 2    # IconModeグリッドの余白（小さくして詰める）

FAVORITES_COUNT = 10  # クイック選択スロット数（1～9, 0）

# D&D用カスタムMIMEタイプ
PICKER_MIME = "application/x-magatu-picker-item"


class DraggablePickerList(QListWidget):
    """ドラッグ開始を明示実装するピッカー用QListWidget

    フレームワーク経路（startDragオーバーライド）と、
    マウスイベント直叩き経路（mouseMoveEvent）の両方を実装し、
    どちらかが必ず動くようにする。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_pos = None
        self._dragging = False
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setDefaultDropAction(Qt.CopyAction)

    def _begin_custom_drag(self, item):
        if self._dragging:
            return
        data = item.data(Qt.UserRole)
        if not (isinstance(data, tuple) and len(data) == 2):
            return
        self._dragging = True
        try:
            drag = QDrag(self)
            mime = QMimeData()
            mode, val = data
            payload = f"{mode}|{val}"
            mime.setData(PICKER_MIME, payload.encode("utf-8"))
            mime.setText(payload)
            drag.setMimeData(mime)
            pix = item.icon().pixmap(self.iconSize())
            if not pix.isNull():
                drag.setPixmap(pix)
                drag.setHotSpot(pix.rect().center())
            drag.exec_(Qt.CopyAction)
        finally:
            self._dragging = False
            self._press_pos = None

    def startDrag(self, supportedActions):
        """フレームワーク経路: QAbstractItemView 標準のドラッグ開始"""
        item = self.currentItem()
        if item is None:
            sel = self.selectedItems()
            if sel:
                item = sel[0]
        if item is None:
            return
        self._begin_custom_drag(item)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """マウスイベント経路: フレームワークが startDrag を呼ばなくても発動させる"""
        if (
            self._press_pos is not None
            and (e.buttons() & Qt.LeftButton)
            and not self._dragging
        ):
            from PyQt5.QtWidgets import QApplication
            if (e.pos() - self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                item = self.itemAt(self._press_pos)
                if item is not None:
                    self._begin_custom_drag(item)
                    return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_pos = None
        super().mouseReleaseEvent(e)


MIRROR_ENEMY_SET_MAX = 7


class _MirrorRow(QListWidget):
    """ミラー1行分（7スロット）のアイコンバー"""

    slot_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(False)
        self.setSpacing(0)
        self.setGridSize(QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._codes = [0] * MIRROR_ENEMY_SET_MAX
        item_size = QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2)
        for i in range(MIRROR_ENEMY_SET_MAX):
            it = QListWidgetItem(QIcon(), "")
            it.setToolTip(f"スロット{i + 1}: 空")
            it.setSizeHint(item_size)
            self.addItem(it)
        self.setFixedHeight(ICON_SIZE + GRID_PAD * 2 + 6)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(PICKER_MIME):
            e.ignore()
            return
        self.handle_drop(e.mimeData(), e.pos(), e.source())
        e.acceptProposedAction()

    def handle_drop(self, mime, pos, src):
        if not mime.hasFormat(PICKER_MIME):
            return
        try:
            payload = bytes(mime.data(PICKER_MIME)).decode("utf-8")
            mode, val_str = payload.split("|", 1)
            if mode != MODE_ENEMY:
                return
            code = int(val_str)
        except Exception:
            return
        base_code = code
        speed = 1
        provider = getattr(src, "_enemy_speed_provider", None)
        if callable(provider):
            try:
                speed = int(provider())
            except Exception:
                speed = 1
        code = apply_enemy_speed(base_code, speed)
        icon = QIcon()
        tooltip_text = f"0x{code:02x}"
        if isinstance(src, QListWidget):
            for i in range(src.count()):
                it = src.item(i)
                d = it.data(Qt.UserRole)
                if isinstance(d, tuple) and d == (mode, base_code):
                    icon = it.icon()
                    tooltip_text = it.toolTip()
                    break
        if code != base_code:
            tooltip_text = f"0x{code:02x} SP{speed} ({tooltip_text})"
        idx = self.indexAt(pos).row()
        if idx < 0:
            try:
                idx = self._codes.index(0)
            except ValueError:
                idx = 0
        self.set_slot(idx, code, icon, tooltip_text)

    def set_slot(self, idx: int, code: int, icon: QIcon, tooltip: str):
        if not (0 <= idx < MIRROR_ENEMY_SET_MAX):
            return
        self._codes[idx] = code
        it = self.item(idx)
        it.setIcon(icon)
        it.setToolTip(f"スロット{idx + 1}: {tooltip}")
        self.slot_changed.emit()

    def clear_slot(self, idx: int):
        if not (0 <= idx < MIRROR_ENEMY_SET_MAX):
            return
        self._codes[idx] = 0
        it = self.item(idx)
        it.setIcon(QIcon())
        it.setToolTip(f"スロット{idx + 1}: 空")
        self.slot_changed.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            row = self.currentRow()
            if row >= 0:
                self.clear_slot(row)
                return
        super().keyPressEvent(e)

    def get_codes(self) -> list:
        return list(self._codes)


class MirrorEnemyPanel(QWidget):
    """ミラー敵セットパネル — ミラー1/2 各7体のアイコンスロット（D&D対応）"""

    enemies_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tile_renderer = None
        self._config = None
        self._rows = []  # [_MirrorRow, _MirrorRow]
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)
        lbl = QLabel("<small>ミラー出現敵 (ピッカーからD&Dで登録 / Delで削除)</small>")
        layout.addWidget(lbl)
        for m in range(2):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            row_lbl = QLabel(f"<small>M{m + 1}</small>")
            row_lbl.setStyleSheet(
                "color:#d42020; font-weight:bold;" if m == 0
                else "color:#1d5fd1; font-weight:bold;")
            row_lbl.setFixedWidth(18)
            row_layout.addWidget(row_lbl)
            row = _MirrorRow()
            row.slot_changed.connect(self.enemies_changed.emit)
            row_layout.addWidget(row, 1)
            self._rows.append(row)
            layout.addLayout(row_layout)

    def set_renderers(self, tile_renderer, config):
        self._tile_renderer = tile_renderer
        self._config = config

    def _make_enemy_icon(self, enemy_code: int) -> QIcon:
        if self._tile_renderer is None or self._config is None:
            return QIcon()
        from PyQt5.QtGui import QPainter, QColor as _QC
        anim = self._config.enemy_map.get(enemy_code, 0)
        try:
            sprite = self._tile_renderer.get_tile_image(anim, 0, transparent=True)
            bg = QImage(ICON_SIZE, ICON_SIZE, QImage.Format_ARGB32)
            bg.fill(_QC(20, 20, 20))
            painter = QPainter(bg)
            scaled = sprite.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.FastTransformation)
            ox = (ICON_SIZE - scaled.width()) // 2
            oy = (ICON_SIZE - scaled.height()) // 2
            painter.drawImage(ox, oy, scaled)
            painter.end()
            return QIcon(QPixmap.fromImage(bg))
        except Exception:
            return QIcon()

    def load_enemies(self, codes_m1: list, codes_m2: list):
        """ROM から読み出した敵コードリスト(各7要素)をセット"""
        for m, codes in enumerate([codes_m1, codes_m2]):
            row = self._rows[m]
            for i in range(MIRROR_ENEMY_SET_MAX):
                code = codes[i] if i < len(codes) else 0
                if code != 0:
                    icon = self._make_enemy_icon(code)
                    name = ""
                    for ec, en in ENEMIES_LIST:
                        if ec == code:
                            name = en
                            break
                    tooltip = f"0x{code:02x} {name}" if name else f"0x{code:02x}"
                    row.set_slot(i, code, icon, tooltip)
                else:
                    row.clear_slot(i)

    def get_enemies(self, mirror_no: int) -> list:
        """指定ミラーの敵コードリスト(7要素、空=0)を返す"""
        return self._rows[mirror_no].get_codes()


class FavoritesBar(QListWidget):
    """お気に入りバー: ピッカーからD&Dで登録、1～0キーでクイック選択"""

    favorite_chosen = pyqtSignal(str, object)  # (mode, value)
    favorites_changed = pyqtSignal(list)       # 永続化通知 [(mode, value) or None] x 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setSpacing(0)
        self.setGridSize(QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # スロット内容: (mode, value) or None
        self._slots = [None] * FAVORITES_COUNT
        item_size = QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2)
        for i in range(FAVORITES_COUNT):
            it = QListWidgetItem(QIcon(), "")
            key = (i + 1) % FAVORITES_COUNT  # 1,2,3,4,5,6,7,8,9,0
            it.setToolTip(f"スロット {key}: 空 (D&Dで登録)")
            it.setSizeHint(item_size)
            self.addItem(it)
        # 高さは2行分 + マージン
        self.setFixedHeight((ICON_SIZE + GRID_PAD * 2) * 2 + 12)
        self.itemClicked.connect(self._on_clicked)

    def dragEnterEvent(self, e):
        print(f"[favorites] dragEnter formats={e.mimeData().formats()}")  # DEBUG
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(PICKER_MIME):
            e.ignore()
            return
        self.handle_drop(e.mimeData(), e.pos(), e.source())
        e.acceptProposedAction()

    def handle_drop(self, mime, pos, src):
        """親(ElementPicker)経由でドロップを受けるためのヘルパ。
        位置はFavoritesBar座標系で受け取る。"""
        if not mime.hasFormat(PICKER_MIME):
            return
        try:
            payload = bytes(mime.data(PICKER_MIME)).decode("utf-8")
            mode, val_str = payload.split("|", 1)
            try:
                val = int(val_str)
            except ValueError:
                val = val_str
        except Exception:
            return

        icon = QIcon()
        tooltip_text = f"[{mode}] {val}"
        if isinstance(src, QListWidget):
            for i in range(src.count()):
                it = src.item(i)
                d = it.data(Qt.UserRole)
                if isinstance(d, tuple) and d == (mode, val):
                    icon = it.icon()
                    tooltip_text = it.toolTip()
                    break

        idx = self.indexAt(pos).row()
        if idx < 0:
            try:
                idx = self._slots.index(None)
            except ValueError:
                idx = 0
        self.set_slot(idx, (mode, val), icon, tooltip_text)

    def set_slot(self, idx: int, data, icon: QIcon, tooltip_text: str):
        if not (0 <= idx < FAVORITES_COUNT):
            return
        self._slots[idx] = data
        it = self.item(idx)
        it.setIcon(icon)
        key = (idx + 1) % FAVORITES_COUNT
        it.setToolTip(f"スロット {key}: {tooltip_text}")
        self.favorites_changed.emit(list(self._slots))

    def clear_slot(self, idx: int):
        if not (0 <= idx < FAVORITES_COUNT):
            return
        self._slots[idx] = None
        it = self.item(idx)
        it.setIcon(QIcon())
        key = (idx + 1) % FAVORITES_COUNT
        it.setToolTip(f"スロット {key}: 空 (D&Dで登録)")
        self.favorites_changed.emit(list(self._slots))

    def get_slot(self, idx: int):
        if 0 <= idx < FAVORITES_COUNT:
            return self._slots[idx]
        return None

    def trigger_slot(self, idx: int):
        """キーボードショートカットから呼ばれる"""
        data = self.get_slot(idx)
        if data is None:
            return False
        mode, val = data
        self.favorite_chosen.emit(mode, val)
        return True

    def _on_clicked(self, item):
        idx = self.row(item)
        self.trigger_slot(idx)

    def keyPressEvent(self, e):
        # Delete/Backspace で選択スロットをクリア
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            row = self.currentRow()
            if row >= 0:
                self.clear_slot(row)
                return
        super().keyPressEvent(e)


BONUS_ITEM_COUNT = 16


class BonusItemPanel(QListWidget):
    """ボーナスステージ(Level 51)専用: 16個のアイテムをグラフィカル表示。
    ピッカーからD&Dでアイテムを入れ替え可能。"""

    items_changed = pyqtSignal(list)  # [item_code x 16]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setSpacing(0)
        self.setGridSize(QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._item_codes = [0] * BONUS_ITEM_COUNT
        item_size = QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2)
        for i in range(BONUS_ITEM_COUNT):
            it = QListWidgetItem(QIcon(), "")
            it.setToolTip(f"スロット#{i}: 空")
            it.setSizeHint(item_size)
            self.addItem(it)
        self.setFixedHeight((ICON_SIZE + GRID_PAD * 2) * 2 + 12)
        self._icon_maker = None
        self._name_fn = None   # code -> 名前 (item_desc 単一ソース解決)

    def set_icon_maker(self, fn):
        self._icon_maker = fn

    def set_name_fn(self, fn):
        self._name_fn = fn

    def load_items(self, item_bytes):
        self._item_codes = list(item_bytes[:BONUS_ITEM_COUNT])
        while len(self._item_codes) < BONUS_ITEM_COUNT:
            self._item_codes.append(0)
        self._refresh_icons()

    def get_item_codes(self):
        return list(self._item_codes)

    def _refresh_icons(self):
        for i, code in enumerate(self._item_codes):
            it = self.item(i)
            name = self._name_fn(code) if self._name_fn else f"0x{code:02X}"
            it.setToolTip(f"#{i}: 0x{code:02X} {name}")
            if self._icon_maker:
                it.setIcon(self._icon_maker(code))
            else:
                it.setIcon(QIcon())

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(PICKER_MIME):
            e.ignore()
            return
        try:
            payload = bytes(e.mimeData().data(PICKER_MIME)).decode("utf-8")
            mode, val_str = payload.split("|", 1)
        except Exception:
            e.ignore()
            return
        if mode != MODE_ITEM:
            e.ignore()
            return
        try:
            item_code = int(val_str)
        except ValueError:
            e.ignore()
            return
        idx = self.indexAt(e.pos()).row()
        if idx < 0 or idx >= BONUS_ITEM_COUNT:
            e.ignore()
            return
        self._item_codes[idx] = item_code
        self._refresh_icons()
        self.items_changed.emit(list(self._item_codes))
        e.acceptProposedAction()

    def handle_drop(self, mime, pos, src):
        if not mime.hasFormat(PICKER_MIME):
            return
        try:
            payload = bytes(mime.data(PICKER_MIME)).decode("utf-8")
            mode, val_str = payload.split("|", 1)
        except Exception:
            return
        if mode != MODE_ITEM:
            return
        try:
            item_code = int(val_str)
        except ValueError:
            return
        idx = self.indexAt(pos).row()
        if idx < 0 or idx >= BONUS_ITEM_COUNT:
            return
        self._item_codes[idx] = item_code
        self._refresh_icons()
        self.items_changed.emit(list(self._item_codes))


class ElementPicker(QWidget):
    """要素選択 + 編集モード切替（キャラクター画像付き）"""

    selection_changed = pyqtSignal(str, object)  # mode, selected_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = MODE_BLOCK
        self.current_value = BLOCK_BROWN
        self.tile_renderer = None
        self.config = None
        self.current_tileset_no = 0  # 現在レベルの実タイルセット番号（描画パレット決定用）
        self.current_item_flag = ITEM_FLAG_NORMAL  # アイテム配置時のフラグ
        self._build_ui()

    def dragEnterEvent(self, e):
        """親で受けて、ドロップ位置に応じて子(FavoritesBar)に手動振り分け"""
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(PICKER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        """ドロップ位置がお気に入りバー/ボーナスパネル上なら手動で渡す"""
        if not e.mimeData().hasFormat(PICKER_MIME):
            e.ignore()
            return
        # ボーナスパネルが表示中ならそちらへ
        if (hasattr(self, "bonus_panel") and self.bonus_panel is not None
                and self._bottom_stack.currentIndex() == 1):
            bp_pos = self.bonus_panel.mapFrom(self, e.pos())
            if self.bonus_panel.rect().contains(bp_pos):
                self.bonus_panel.handle_drop(e.mimeData(), bp_pos, e.source())
                e.acceptProposedAction()
                return
        # ElementPicker座標 → MirrorPanel の各行に変換
        if hasattr(self, "mirror_panel") and self.mirror_panel is not None:
            for row in self.mirror_panel._rows:
                row_pos = row.mapFrom(self, e.pos())
                if row.rect().contains(row_pos):
                    row.handle_drop(e.mimeData(), row_pos, e.source())
                    e.acceptProposedAction()
                    return
        # ElementPicker座標 → FavoritesBar座標に変換
        if hasattr(self, "favorites") and self.favorites is not None:
            fav_pos = self.favorites.mapFrom(self, e.pos())
            if self.favorites.rect().contains(fav_pos):
                self.favorites.handle_drop(e.mimeData(), fav_pos, e.source())
                e.acceptProposedAction()
                return
        e.ignore()

    def _build_ui(self):
        # 親ウィジェットでもドロップを許可しないと子へ伝播しない場合がある
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)

        # 配置フラグ（常時表示）
        self.flag_group = QGroupBox("アイテム状態")
        fl = QHBoxLayout(self.flag_group)
        self.flag_btns = QButtonGroup(self)
        self.rb_flag_normal = QRadioButton("通常")
        self.rb_flag_hidden = QRadioButton("隠し")
        self.rb_flag_in_block = QRadioButton("ブロック内")
        for rb, flag in [
            (self.rb_flag_normal, ITEM_FLAG_NORMAL),
            (self.rb_flag_hidden, ITEM_FLAG_HIDDEN),
            (self.rb_flag_in_block, ITEM_FLAG_IN_BLOCK),
        ]:
            self.flag_btns.addButton(rb)
            fl.addWidget(rb)
            rb.toggled.connect(lambda checked, f=flag: self._on_flag_changed(f) if checked else None)
        self.rb_flag_normal.setChecked(True)

        # 敵スピード（常時表示、敵モード時のみ意味あり）
        self.speed_group = QGroupBox("敵スピード")
        sl = QHBoxLayout(self.speed_group)
        self.speed_btns = QButtonGroup(self)
        self.rb_sp1 = QRadioButton("SP1")
        self.rb_sp2 = QRadioButton("SP2")
        self.rb_sp3 = QRadioButton("SP3")
        for rb, sp in [
            (self.rb_sp1, 1),
            (self.rb_sp2, 2),
            (self.rb_sp3, 3),
        ]:
            self.speed_btns.addButton(rb)
            sl.addWidget(rb)
            rb.toggled.connect(
                lambda checked, s=sp: self._on_speed_changed(s) if checked else None
            )
        self.rb_sp1.setChecked(True)
        self.current_enemy_speed = 1
        self._update_speed_controls(MODE_BLOCK, None)

        # 選択リスト（4カテゴリに分割: ブロック / キャラ / アイテム / モンスター）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        picker_container = QWidget()
        picker_layout = QVBoxLayout(picker_container)
        picker_layout.setContentsMargins(0, 0, 0, 0)
        picker_layout.setSpacing(2)

        self._picker_lists = []
        self._category_labels = []
        categories = ["ブロック", "メタ", "アイテム", "モンスター"]
        for cat_idx, cat_name in enumerate(categories):
            lbl = QLabel(f"<small><b>{cat_name}</b></small>")
            lbl.setContentsMargins(2, 2, 0, 0)
            picker_layout.addWidget(lbl)
            self._category_labels.append(lbl)

            lst = DraggablePickerList()
            lst._enemy_speed_provider = self.get_enemy_speed
            lst.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            lst.setViewMode(QListView.IconMode)
            lst.setMovement(QListView.Static)
            lst.setResizeMode(QListView.Adjust)
            lst.setWrapping(True)
            lst.setSpacing(0)
            lst.setGridSize(QSize(ICON_SIZE + GRID_PAD * 2, ICON_SIZE + GRID_PAD * 2))
            lst.setUniformItemSizes(True)
            lst.itemSelectionChanged.connect(self._on_item_selected)
            lst.setDragEnabled(True)
            lst.setDragDropMode(QAbstractItemView.DragOnly)
            # 高さはコンテンツに合わせる（固定スクロールなし）
            lst.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            picker_layout.addWidget(lst)
            self._picker_lists.append(lst)
            if cat_idx == 1:
                picker_layout.addWidget(self.flag_group)
            elif cat_idx == 2:
                picker_layout.addWidget(self.speed_group)

        picker_layout.addStretch()
        scroll.setWidget(picker_container)
        layout.addWidget(scroll, 1)

        self._mirror_detail_slot = QVBoxLayout()
        self._mirror_detail_slot.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._mirror_detail_slot)

        # ミラー出現敵パネル
        self.mirror_panel = MirrorEnemyPanel()
        layout.addWidget(self.mirror_panel)

        # 下部パネル: お気に入り / ボーナスアイテム をスタック切替
        self._bottom_stack = QStackedWidget()

        # Page 0: お気に入りバー
        fav_page = QWidget()
        fav_lay = QVBoxLayout(fav_page)
        fav_lay.setContentsMargins(0, 0, 0, 0)
        fav_label = QLabel("<small>お気に入り (D&Dで登録 / 1〜0キーで選択 / Delで削除)</small>")
        fav_lay.addWidget(fav_label)
        self.favorites = FavoritesBar()
        self.favorites.favorite_chosen.connect(self._on_favorite_chosen)
        fav_lay.addWidget(self.favorites)
        self._bottom_stack.addWidget(fav_page)  # index 0

        # Page 1: ボーナスアイテムパネル (Level 51専用)
        bonus_page = QWidget()
        bonus_lay = QVBoxLayout(bonus_page)
        bonus_lay.setContentsMargins(0, 0, 0, 0)
        bonus_label = QLabel("<small>ボーナスステージ アイテム16種 (ピッカーからD&Dで入替)</small>")
        bonus_lay.addWidget(bonus_label)
        self.bonus_panel = BonusItemPanel()
        bonus_lay.addWidget(self.bonus_panel)
        self._bottom_stack.addWidget(bonus_page)  # index 1

        self._bottom_stack.setCurrentIndex(0)
        layout.addWidget(self._bottom_stack)

        # 後方互換: 旧UI参照を保持（None で残す）
        self.rb_block = None
        self.rb_item = None
        self.rb_enemy = None
        self.rb_meta = None

        # 初期ポピュレート（tile_renderer 未設定なので空アイコンになる）
        self._populate_all()

    def set_mirror_detail_button(self, button):
        self._mirror_detail_slot.addWidget(button)

    def set_tile_renderer(self, tile_renderer, config):
        """ROM読込後にレンダラを設定して、アイコン付きリストに更新"""
        self.tile_renderer = tile_renderer
        self.config = config
        self._populate_all()
        self.mirror_panel.set_renderers(tile_renderer, config)

    def set_current_tileset_no(self, tileset_no: int):
        """現在レベルのタイルセット番号を設定し、アイコンを再描画"""
        if tileset_no == self.current_tileset_no:
            return
        self.current_tileset_no = tileset_no
        if self.tile_renderer is not None:
            self._populate_all()

    # ========== Helper ==========

    def _make_icon_from_tile(self, tile_no: int, apply_blue_filter: bool = False,
                             overlay_color=None) -> QIcon:
        """tile_definitions の tile_no から QIcon 生成

        skchain互換: 現在レベルのタイルセット番号を使って描画。これにより
        配置時とピッカーで色が完全一致する。palette index 1（スプライト本体色）
        は透明化しない（スプライト本体が消えてしまう）。

        Args:
            tile_no: tile_definitions の番号
            apply_blue_filter: True なら青フィルターを上から重ねる（壊せる白ブロック用）
        """
        if self.tile_renderer is None or self.config is None:
            return QIcon()

        from PyQt5.QtGui import QPainter, QColor

        # tile_renderer は palette index 0 のみ透明扱いするので、そのまま使う
        sprite = self.tile_renderer.get_tile_image(
            tile_no, self.current_tileset_no, transparent=True
        )

        # 黒背景に重ねて見やすくする
        bg = QImage(ICON_SIZE, ICON_SIZE, QImage.Format_ARGB32)
        bg.fill(QColor(20, 20, 20))
        painter = QPainter(bg)
        scaled = sprite.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.FastTransformation)
        ox = (ICON_SIZE - scaled.width()) // 2
        oy = (ICON_SIZE - scaled.height()) // 2
        painter.drawImage(ox, oy, scaled)
        if overlay_color is None and apply_blue_filter:
            overlay_color = (80, 130, 255, 90)
        if overlay_color is not None:
            painter.fillRect(ox, oy, scaled.width(), scaled.height(),
                             QColor(*overlay_color))
        painter.end()
        return QIcon(QPixmap.fromImage(bg))

    def _make_block_icon(self, block_kind: str) -> QIcon:
        """ブロック種別からアイコン取得"""
        if self.tile_renderer is None or self.config is None:
            return QIcon()

        from ..gfx.level_renderer import (
            MD_EMPTY, MD_BLOCK_BROWN, MD_BLOCK_WHITE
        )
        meta_byte = {
            BLOCK_NONE: MD_EMPTY,
            BLOCK_BROWN: MD_BLOCK_BROWN,
            BLOCK_WHITE: MD_BLOCK_WHITE,
            BLOCK_INVISIBLE_BREAKABLE: MD_EMPTY,
            BLOCK_PASSABLE_WHITE: MD_BLOCK_WHITE,
            BLOCK_INVISIBLE_SOLID: MD_EMPTY,
            BLOCK_BREAKABLE_WHITE: MD_BLOCK_WHITE,
            BLOCK_BROWN_WHITE: MD_BLOCK_WHITE,  # 見た目は白＋青フィルター
        }.get(block_kind)
        if meta_byte is None:
            return QIcon()
        anim = self.config.metadata_map.get(meta_byte, 0)
        # 壊せる白ブロックは青フィルターをかける
        overlay_color = {
            BLOCK_BROWN_WHITE: (80, 130, 255, 90),
            BLOCK_BREAKABLE_WHITE: (80, 130, 255, 90),
            BLOCK_INVISIBLE_BREAKABLE: (120, 190, 255, 85),
            BLOCK_PASSABLE_WHITE: (90, 210, 120, 95),
            BLOCK_INVISIBLE_SOLID: (220, 60, 70, 100),
        }.get(block_kind)
        return self._make_icon_from_tile(anim, overlay_color=overlay_color)

    def _make_item_icon(self, item_no: int) -> QIcon:
        """アイテムコード → アイコン"""
        if self.config is None:
            return QIcon()
        anim = self.config.item_map.get(item_no & 0x3f, 0)
        return self._make_icon_from_tile(anim)

    def _make_enemy_icon(self, enemy_no: int) -> QIcon:
        """敵コード → アイコン"""
        if self.config is None:
            return QIcon()
        anim = self.config.enemy_map.get(enemy_no, 0)
        overlay = (245, 220, 80, 80) if enemy_no in ENHANCED_ENEMY_CODES else None
        return self._make_icon_from_tile(anim, overlay_color=overlay)

    def _make_meta_icon(self, meta_kind: str) -> QIcon:
        """メタ種別（鍵/扉/スタート/ミラー）からアイコン"""
        if self.config is None:
            return QIcon()
        from ..gfx.level_renderer import (
            MD_KEY, MD_DOOR, MD_PLAYER_START, MD_SPAWN01, MD_SPAWN02
        )
        meta_byte = {
            "start": MD_PLAYER_START,
            "key": MD_KEY,
            "door": MD_DOOR,
            "mirror1": MD_SPAWN01,
            "mirror2": MD_SPAWN02,
        }.get(meta_kind)
        if meta_byte is None:
            return QIcon()
        anim = self.config.metadata_map.get(meta_byte, 0)
        return self._make_icon_from_tile(anim)

    # ========== Populate ==========

    def _populate_all(self):
        """4カテゴリに分けてグリッド表示。アイコンのみ・テキストはツールチップ。

        UserRole に (mode, value) のタプルを格納する。
        カテゴリ: [0]ブロック  [1]キャラ  [2]アイテム  [3]モンスター
        """
        for lst in self._picker_lists:
            lst.clear()

        # カテゴリ0: ブロック
        for label, val in [
            ("消去 (空白)", BLOCK_NONE),
            ("茶色ブロック (壊せる)", BLOCK_BROWN),
            ("白ブロック (壊せない)", BLOCK_WHITE),
            ("Breakable white wall", BLOCK_BREAKABLE_WHITE),
            ("Invisible breakable wall", BLOCK_INVISIBLE_BREAKABLE),
            ("Passable white wall", BLOCK_PASSABLE_WHITE),
            ("Invisible solid wall", BLOCK_INVISIBLE_SOLID),
        ]:
            self._add_picker_item(0, MODE_BLOCK, val, label, self._make_block_icon(val))

        # カテゴリ1: キャラ（プレイヤー / 鍵 / 扉 / ミラー）
        for label, val in [
            ("プレイヤースタート", "start"),
            ("鍵", "key"),
            ("扉", "door"),
            ("ミラー1 (Spawn1)", "mirror1"),
            ("ミラー2 (Spawn2)", "mirror2"),
        ]:
            self._add_picker_item(1, MODE_META, val, label, self._make_meta_icon(val))

        # カテゴリ2: アイテム (名前は item_desc 単一ソースから解決)
        for code in ITEMS_LIST:
            label = f"0x{code:02x} {item_name(code, self.config)}"
            self._add_picker_item(2, MODE_ITEM, code, label, self._make_item_icon(code))

        # カテゴリ3: モンスター
        for code, name in ENEMIES_LIST:
            label = f"0x{code:02x} {name}"
            self._add_picker_item(3, MODE_ENEMY, code, label, self._make_enemy_icon(code))

        # 各リストの高さをコンテンツに合わせる
        for lst in self._picker_lists:
            self._adjust_list_height(lst)

        # 茶色ブロック (index 1) を初期選択
        self._picker_lists[0].setCurrentRow(1)
        # お気に入りアイコンを最新パレットで再構築
        self._refresh_favorite_icons()

    def _add_picker_item(self, category: int, mode: str, val, label: str, icon):
        """カテゴリ別リストにアイテムを追加"""
        it = QListWidgetItem(icon, "")
        it.setToolTip(f"[{mode}] {label}")
        it.setData(Qt.UserRole, (mode, val))
        self._picker_lists[category].addItem(it)

    def _adjust_list_height(self, lst):
        """リストの高さをコンテンツ量に合わせて固定（スクロールバー不要にする）"""
        count = lst.count()
        if count == 0:
            lst.setFixedHeight(0)
            return
        grid_h = ICON_SIZE + GRID_PAD * 2
        # 幅からおおよその列数を推定（初期値として8列想定）
        cols = max(1, 8)
        rows = (count + cols - 1) // cols
        lst.setMinimumHeight(rows * grid_h + 4)
        lst.setMaximumHeight(rows * grid_h + 4)

    def _refresh_favorite_icons(self):
        """タイルセット変更時など、お気に入りのアイコンを最新色で再描画"""
        if not hasattr(self, "favorites"):
            return
        for i in range(FAVORITES_COUNT):
            data = self.favorites._slots[i]
            if data is None:
                continue
            found = False
            for lst in self._picker_lists:
                if found:
                    break
                for j in range(lst.count()):
                    it = lst.item(j)
                    d = it.data(Qt.UserRole)
                    if isinstance(d, tuple) and d == data:
                        fav_it = self.favorites.item(i)
                        fav_it.setIcon(it.icon())
                        key = (i + 1) % FAVORITES_COUNT
                        fav_it.setToolTip(f"スロット {key}: {it.toolTip()}")
                        found = True
                        break

    def _on_item_selected(self):
        # どのリストで選択が発生したか特定
        sender = self.sender()
        if sender is None:
            return
        items = sender.selectedItems()
        if not items:
            return
        data = items[0].data(Qt.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            return
        # 他リストの選択をクリア（クロスリスト排他選択）
        for lst in self._picker_lists:
            if lst is not sender:
                lst.blockSignals(True)
                lst.clearSelection()
                lst.blockSignals(False)
        mode, val = data
        self.current_mode = mode
        self.current_value = val
        # 配置レギュレーション: 隠し専用アイテムを選んだら自動で hidden に切替
        if mode == MODE_ITEM and isinstance(val, int):
            if val in HIDDEN_ONLY_ITEMS:
                self.rb_flag_hidden.setChecked(True)
        self._update_speed_controls(mode, val)
        self.selection_changed.emit(mode, val)

    def _on_flag_changed(self, flag: int):
        self.current_item_flag = flag

    def _on_speed_changed(self, speed: int):
        self.current_enemy_speed = speed

    def _update_speed_controls(self, mode, value):
        if mode != MODE_ENEMY or not isinstance(value, int):
            self.speed_group.setEnabled(False)
            return

        table = ENEMY_SPEED_TABLE.get(value)
        if not table:
            self.speed_group.setEnabled(False)
            return

        self.speed_group.setEnabled(True)
        buttons = (self.rb_sp1, self.rb_sp2, self.rb_sp3)
        for rb, code in zip(buttons, table):
            rb.setEnabled(code is not None)

        current_idx = max(1, min(3, self.current_enemy_speed)) - 1
        if table[current_idx] is None:
            for i, code in enumerate(table):
                if code is not None:
                    target = buttons[i]
                    target.blockSignals(True)
                    target.setChecked(True)
                    target.blockSignals(False)
                    self.current_enemy_speed = i + 1
                    break

    def get_current(self):
        return self.current_mode, self.current_value

    def get_selected_items(self):
        """全カテゴリリストから選択中アイテムを返す（外部互換用）"""
        for lst in self._picker_lists:
            items = lst.selectedItems()
            if items:
                return items
        return []

    def find_and_select(self, value, mode=None):
        """全カテゴリリストから value 一致のアイテムを探して選択"""
        for lst in self._picker_lists:
            for i in range(lst.count()):
                it = lst.item(i)
                data = it.data(Qt.UserRole)
                if isinstance(data, tuple) and len(data) == 2:
                    m, v = data
                    if v == value and (mode is None or m == mode):
                        lst.setCurrentRow(i)
                        return True
        return False

    def get_item_flag(self) -> int:
        """アイテム配置時に付加するフラグ (0x00 / 0x40 / 0x80)"""
        return self.current_item_flag

    def get_enemy_speed(self) -> int:
        """敵配置時のスピード (1/2/3)"""
        return self.current_enemy_speed

    def set_enemy_speed(self, speed: int):
        """敵配置時のスピードを外部からセット (スポイト時等)"""
        speed = max(1, min(3, speed))
        if speed == 1:
            self.rb_sp1.setChecked(True)
        elif speed == 2:
            self.rb_sp2.setChecked(True)
        else:
            self.rb_sp3.setChecked(True)

    # ========== お気に入り ==========

    def _on_favorite_chosen(self, mode: str, value):
        """お気に入りクリック / キー押下 → メインリスト側を選択状態にする"""
        self._select_in_main_list(mode, value)

    def _select_in_main_list(self, mode: str, value):
        for lst in self._picker_lists:
            for i in range(lst.count()):
                it = lst.item(i)
                data = it.data(Qt.UserRole)
                if isinstance(data, tuple) and data == (mode, value):
                    lst.setCurrentRow(i)
                    return

    def trigger_favorite_key(self, key_digit: int):
        """1..9, 0 のキー入力に応じてスロット選択

        key_digit: 1〜9 はそのままスロット idx-1、0 はスロット 9 (10番目)
        """
        if key_digit == 0:
            idx = 9
        elif 1 <= key_digit <= 9:
            idx = key_digit - 1
        else:
            return False
        return self.favorites.trigger_slot(idx)

    def get_favorites(self) -> list:
        """[(mode, value) or None] x 10 を返す（永続化用）"""
        return list(self.favorites._slots)

    def restore_favorites(self, slots: list):
        """保存された [(mode,value) or None] x 10 をUIに復元"""
        if not slots:
            return
        for i, data in enumerate(slots[:FAVORITES_COUNT]):
            if data is None:
                continue
            if isinstance(data, (list, tuple)) and len(data) == 2:
                mode, val = data[0], data[1]
                # メインリストから該当アイコンとツールチップを引く
                found = False
                for lst in self._picker_lists:
                    if found:
                        break
                    for j in range(lst.count()):
                        it = lst.item(j)
                        d = it.data(Qt.UserRole)
                        if isinstance(d, tuple) and d == (mode, val):
                            self.favorites.set_slot(i, (mode, val), it.icon(), it.toolTip())
                            found = True
                            break

    # ========== ボーナスアイテムパネル (Level 51) ==========

    def set_bonus_mode(self, enabled: bool, item_bytes=None):
        """Level 51 のとき下部をボーナスアイテムパネルに切替"""
        if enabled:
            self.bonus_panel.set_icon_maker(self._make_item_icon)
            self.bonus_panel.set_name_fn(lambda c: item_name(c, self.config))
            if item_bytes is not None:
                self.bonus_panel.load_items(item_bytes)
            self._bottom_stack.setCurrentIndex(1)
        else:
            self._bottom_stack.setCurrentIndex(0)
