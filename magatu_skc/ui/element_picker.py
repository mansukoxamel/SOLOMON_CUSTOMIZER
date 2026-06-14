"""要素選択ピッカー - キャラクター画像付き"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QButtonGroup, QRadioButton, QListWidget, QListWidgetItem,
    QListView, QAbstractItemView, QStackedWidget, QScrollArea, QSizePolicy,
    QGraphicsOpacityEffect, QGraphicsScene
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMimeData, QRectF
from PyQt5.QtGui import QPixmap, QIcon, QImage, QDrag, QColor

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
BLOCK_PASSABLE_BROWN = "passable_brown"
BLOCK_SOLID_BROWN = "solid_brown"

DEFAULT_BLOCK_PICKER_ORDER = [
    BLOCK_NONE,
    BLOCK_BROWN,
    BLOCK_WHITE,
    BLOCK_BREAKABLE_WHITE,
    BLOCK_INVISIBLE_BREAKABLE,
    BLOCK_PASSABLE_WHITE,
    BLOCK_INVISIBLE_SOLID,
    BLOCK_PASSABLE_BROWN,
    BLOCK_SOLID_BROWN,
]

BLOCK_PICKER_LABELS = {
    BLOCK_NONE: "消去 (空白)",
    BLOCK_BROWN: "茶色ブロック (壊せる)",
    BLOCK_WHITE: "白ブロック (壊せない)",
    BLOCK_BREAKABLE_WHITE: "壊せる白ブロック",
    BLOCK_INVISIBLE_BREAKABLE: "透明な茶色ブロック",
    BLOCK_PASSABLE_WHITE: "すり抜ける白ブロック",
    BLOCK_INVISIBLE_SOLID: "透明な白ブロック",
    BLOCK_PASSABLE_BROWN: "すり抜ける茶色ブロック",
    BLOCK_SOLID_BROWN: "壊せない茶色ブロック",
}


# アイテムフラグ
ITEM_FLAG_NORMAL = 0x00
ITEM_FLAG_HIDDEN = 0x40
ITEM_FLAG_IN_BLOCK = 0x80
ITEM_FLAG_WHITE_IN_BLOCK = 0xC0
ITEM_FLAG_VISIBLE_IN_BLOCK = 0x100


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
    0x04, 0x05, 0x07, 0x08, 0x0b, 0x0c,
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
    (0x41, "Panel Variant A (right)"),
    (0x43, "Panel Variant A (left)"),
    (0x45, "Panel Variant A (up)"),
    (0x47, "Panel Variant A (down)"),
    (0x49, "Panel Variant B (right)"),
    (0x4b, "Panel Variant B (left)"),
    (0x4d, "Panel Variant B (up)"),
    (0x4f, "Panel Variant B (down)"),
    (0x31, "Panel Variant C (right)"),
    (0x33, "Panel Variant C (left)"),
    (0x35, "Panel Variant C (up)"),
    (0x37, "Panel Variant C (down)"),
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
    # Saramandor #2 の $66/$67 は Panel Monster 3-way として使うため配置不可。
    0x5e: [0x5e, 0x62, None],
    0x5f: [0x5f, 0x63, None],
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
    0x31, 0x33, 0x35, 0x37,  # Panel Variant C
    0x41, 0x43, 0x45, 0x47,  # Panel Variant A
    0x49, 0x4b, 0x4d, 0x4f,  # Panel Variant B
    0x5e, 0x5f, 0x62, 0x63,  # Saramandor #2
    0x6a, 0x6b, 0x6e, 0x6f,  # Spark Ball pause
    0x72, 0x73, 0x76, 0x77,  # Spark Ball invisible
    0x7a, 0x7b, 0x7e, 0x7f,  # Gargoyle 2-shot
}


PANEL_VARIANT_VISUAL_SOURCE = {
    0x41: 0x24, 0x43: 0x25, 0x45: 0x26, 0x47: 0x27,  # A
    0x49: 0x24, 0x4b: 0x25, 0x4d: 0x26, 0x4f: 0x27,  # B
    0x31: 0x24, 0x33: 0x25, 0x35: 0x26, 0x37: 0x27,  # C
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
PICKER_ICON_MIN = 24
PICKER_ICON_MAX = 64
PICKER_ICON_STEP = 4

FAVORITES_COUNT = 10  # クイック選択スロット数（1～9, 0）

# D&D用カスタムMIMEタイプ
PICKER_MIME = "application/x-magatu-picker-item"


def clamp_picker_icon_size(value) -> int:
    try:
        size = int(value)
    except Exception:
        size = ICON_SIZE
    size = max(PICKER_ICON_MIN, min(PICKER_ICON_MAX, size))
    return max(PICKER_ICON_MIN, (size // PICKER_ICON_STEP) * PICKER_ICON_STEP)


def _picker_cell_size(icon_size: int) -> QSize:
    return QSize(icon_size + GRID_PAD * 2, icon_size + GRID_PAD * 2)


def _handle_picker_zoom_wheel(widget, event) -> bool:
    if not (event.modifiers() & Qt.ControlModifier):
        return False
    owner = getattr(widget, "_icon_zoom_owner", None)
    if owner is None:
        return False
    delta = event.angleDelta().y()
    if delta == 0:
        delta = event.pixelDelta().y()
    if delta == 0:
        return False
    owner.change_picker_icon_size(1 if delta > 0 else -1)
    event.accept()
    return True


class DraggablePickerList(QListWidget):
    """ドラッグ開始を明示実装するピッカー用QListWidget

    フレームワーク経路（startDragオーバーライド）と、
    マウスイベント直叩き経路（mouseMoveEvent）の両方を実装し、
    どちらかが必ず動くようにする。
    """

    ctrl_reorder_requested = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_pos = None
        self._ctrl_press_row = None
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
            if mode == MODE_ITEM:
                provider = getattr(self, "_item_flag_provider", None)
                if callable(provider):
                    try:
                        payload = f"{payload}|{int(provider())}"
                    except Exception:
                        pass
            elif mode == MODE_ENEMY:
                provider = getattr(self, "_enemy_speed_provider", None)
                if callable(provider):
                    try:
                        payload = f"{mode}|{apply_enemy_speed(int(val), int(provider()))}"
                    except Exception:
                        pass
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
        if e.button() == Qt.LeftButton and (e.modifiers() & Qt.ControlModifier):
            item = self.itemAt(e.pos())
            if item is not None:
                self._ctrl_press_row = self.row(item)
                self.setCurrentItem(item)
                e.accept()
                return
        if e.button() == Qt.LeftButton:
            self._press_pos = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """マウスイベント経路: フレームワークが startDrag を呼ばなくても発動させる"""
        if self._ctrl_press_row is not None and (e.buttons() & Qt.LeftButton):
            item = self.itemAt(e.pos())
            if item is not None:
                self.setCurrentItem(item)
            e.accept()
            return
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
        if self._ctrl_press_row is not None and e.button() == Qt.LeftButton:
            src_row = self._ctrl_press_row
            self._ctrl_press_row = None
            target = self.itemAt(e.pos())
            if target is not None:
                dst_row = self.row(target)
                if src_row != dst_row:
                    self.ctrl_reorder_requested.emit(src_row, dst_row)
                    e.accept()
                    return
        self._press_pos = None
        super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        if _handle_picker_zoom_wheel(self, e):
            return
        super().wheelEvent(e)


class FullWidthRadioButton(QRadioButton):
    """Radio button whose whole widget rect is clickable."""

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())


MIRROR_ENEMY_SET_MAX = 7
MIRROR_ROW_LABEL_STYLES = (
    "color:#d42020; font-weight:bold;",
    "color:#1d5fd1; font-weight:bold;",
)
MIRROR_ROW_LABEL_DISABLED_STYLE = "color:#777777; font-weight:bold;"


class _MirrorRow(QListWidget):
    """ミラー1行分（7スロット）のアイコンバー"""

    slot_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_size = ICON_SIZE
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(False)
        self.setSpacing(0)
        self.setGridSize(_picker_cell_size(self._icon_size))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._codes = [0] * MIRROR_ENEMY_SET_MAX
        item_size = _picker_cell_size(self._icon_size)
        for i in range(MIRROR_ENEMY_SET_MAX):
            it = QListWidgetItem(QIcon(), "")
            it.setToolTip(f"スロット{i + 1}: 空")
            it.setSizeHint(item_size)
            self.addItem(it)
        self.setFixedHeight(self._icon_size + GRID_PAD * 2 + 6)

    def set_icon_size_value(self, size: int):
        self._icon_size = clamp_picker_icon_size(size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        item_size = _picker_cell_size(self._icon_size)
        self.setGridSize(item_size)
        for i in range(self.count()):
            it = self.item(i)
            if it is not None:
                it.setSizeHint(item_size)
        self.setFixedHeight(self._icon_size + GRID_PAD * 2 + 6)

    def wheelEvent(self, e):
        if _handle_picker_zoom_wheel(self, e):
            return
        super().wheelEvent(e)

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
        self._row_labels = []
        self._row_effects = []
        self._label_effects = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)
        lbl = QLabel("<small>ミラー出現敵</small>")
        lbl.setToolTip("ピッカーからD&Dで登録 / Delで削除")
        layout.addWidget(lbl)
        for m in range(2):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            row_lbl = QLabel(f"<small>M{m + 1}</small>")
            row_lbl.setStyleSheet(MIRROR_ROW_LABEL_STYLES[m])
            row_lbl.setFixedWidth(18)
            row_layout.addWidget(row_lbl)
            self._row_labels.append(row_lbl)
            label_effect = QGraphicsOpacityEffect(row_lbl)
            row_lbl.setGraphicsEffect(label_effect)
            self._label_effects.append(label_effect)
            row = _MirrorRow()
            row._icon_zoom_owner = getattr(self, "_icon_zoom_owner", None)
            row_effect = QGraphicsOpacityEffect(row)
            row.setGraphicsEffect(row_effect)
            self._row_effects.append(row_effect)
            row.slot_changed.connect(self.enemies_changed.emit)
            row_layout.addWidget(row, 1)
            self._rows.append(row)
            layout.addLayout(row_layout)

    def set_icon_zoom_owner(self, owner):
        self._icon_zoom_owner = owner
        for row in self._rows:
            row._icon_zoom_owner = owner

    def set_icon_size_value(self, size: int):
        for row in self._rows:
            row.set_icon_size_value(size)

    def set_mirror_active(self, mirror_no: int, active: bool):
        if not (0 <= mirror_no < len(self._rows)):
            return
        row = self._rows[mirror_no]
        label = self._row_labels[mirror_no]
        row.setEnabled(bool(active))
        label.setEnabled(bool(active))
        opacity = 1.0 if active else 0.28
        self._row_effects[mirror_no].setOpacity(opacity)
        self._label_effects[mirror_no].setOpacity(opacity)
        label.setStyleSheet(
            MIRROR_ROW_LABEL_STYLES[mirror_no]
            if active else MIRROR_ROW_LABEL_DISABLED_STYLE
        )
        if active:
            row.setToolTip("")
            label.setToolTip("")
        else:
            tip = "ミラー詳細設定の出現タイミングが全OFFのため、この敵セットは出現しません。"
            row.setToolTip(tip)
            label.setToolTip(tip)

    def set_mirror_active_states(self, states: list):
        for mirror_no in range(min(2, len(states))):
            self.set_mirror_active(mirror_no, bool(states[mirror_no]))

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
            icon_size = self._rows[0]._icon_size if self._rows else ICON_SIZE
            bg = QImage(icon_size, icon_size, QImage.Format_ARGB32)
            bg.fill(_QC(20, 20, 20))
            painter = QPainter(bg)
            scaled = sprite.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.FastTransformation)
            ox = (icon_size - scaled.width()) // 2
            oy = (icon_size - scaled.height()) // 2
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
        self._icon_size = ICON_SIZE
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setSpacing(0)
        self.setGridSize(_picker_cell_size(self._icon_size))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # スロット内容: (mode, value) or None
        self._slots = [None] * FAVORITES_COUNT
        item_size = _picker_cell_size(self._icon_size)
        for i in range(FAVORITES_COUNT):
            it = QListWidgetItem(QIcon(), "")
            key = (i + 1) % FAVORITES_COUNT  # 1,2,3,4,5,6,7,8,9,0
            it.setToolTip(f"スロット {key}: 空 (D&Dで登録)")
            it.setSizeHint(item_size)
            self.addItem(it)
        # 高さは2行分 + マージン
        self.setFixedHeight((self._icon_size + GRID_PAD * 2) * 2 + 12)
        self.itemClicked.connect(self._on_clicked)

    def set_icon_size_value(self, size: int):
        self._icon_size = clamp_picker_icon_size(size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        item_size = _picker_cell_size(self._icon_size)
        self.setGridSize(item_size)
        for i in range(self.count()):
            it = self.item(i)
            if it is not None:
                it.setSizeHint(item_size)
        self.setFixedHeight((self._icon_size + GRID_PAD * 2) * 2 + 12)

    def wheelEvent(self, e):
        if _handle_picker_zoom_wheel(self, e):
            return
        super().wheelEvent(e)

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
        self._icon_size = ICON_SIZE
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setSpacing(0)
        self.setGridSize(_picker_cell_size(self._icon_size))
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._item_codes = [0] * BONUS_ITEM_COUNT
        item_size = _picker_cell_size(self._icon_size)
        for i in range(BONUS_ITEM_COUNT):
            it = QListWidgetItem(QIcon(), "")
            it.setToolTip(f"スロット#{i}: 空")
            it.setSizeHint(item_size)
            self.addItem(it)
        self.setFixedHeight((self._icon_size + GRID_PAD * 2) * 2 + 12)
        self._icon_maker = None
        self._name_fn = None   # code -> 名前 (item_desc 単一ソース解決)

    def set_icon_size_value(self, size: int):
        self._icon_size = clamp_picker_icon_size(size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        item_size = _picker_cell_size(self._icon_size)
        self.setGridSize(item_size)
        for i in range(self.count()):
            it = self.item(i)
            if it is not None:
                it.setSizeHint(item_size)
        self.setFixedHeight((self._icon_size + GRID_PAD * 2) * 2 + 12)
        self._refresh_icons()

    def wheelEvent(self, e):
        if _handle_picker_zoom_wheel(self, e):
            return
        super().wheelEvent(e)

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
    block_order_changed = pyqtSignal(list)
    icon_size_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = MODE_BLOCK
        self.current_value = BLOCK_BROWN
        self.tile_renderer = None
        self.config = None
        self.current_level_no = 0
        self.current_tileset_no = 0  # 現在レベルの実タイルセット番号（描画パレット決定用）
        self.current_wall_color = None
        self.current_item_flag = ITEM_FLAG_NORMAL  # アイテム配置時のフラグ
        self._block_order = list(DEFAULT_BLOCK_PICKER_ORDER)
        self._marker_colors = {}
        self._marker_shapes = {}
        self._marker_overlay_scale = 3
        self._icon_size = ICON_SIZE
        self._marker_source_tile_size = ICON_SIZE
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
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)
        self.flag_btns = QButtonGroup(self)
        self.rb_flag_normal = FullWidthRadioButton("通常")
        self.rb_flag_hidden = FullWidthRadioButton("隠し")
        self.rb_flag_in_block = FullWidthRadioButton("BL内")
        self.rb_flag_white_in_block = FullWidthRadioButton("白BL")
        self.rb_flag_visible_in_block = FullWidthRadioButton("透BL")
        for rb, flag, tooltip in [
            (self.rb_flag_normal, ITEM_FLAG_NORMAL, "通常"),
            (self.rb_flag_hidden, ITEM_FLAG_HIDDEN, "隠し"),
            (self.rb_flag_in_block, ITEM_FLAG_IN_BLOCK, "ブロック内"),
            (self.rb_flag_white_in_block, ITEM_FLAG_WHITE_IN_BLOCK, "白ブロック内"),
            (self.rb_flag_visible_in_block, ITEM_FLAG_VISIBLE_IN_BLOCK, "透明ブロック内"),
        ]:
            self.flag_btns.addButton(rb)
            rb.setToolTip(tooltip)
            rb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            rb.setMinimumWidth(0)
            rb.setMinimumHeight(40)
            fl.addWidget(rb, 1)
            rb.toggled.connect(lambda checked, f=flag: self._on_flag_changed(f) if checked else None)
        self.rb_flag_normal.setChecked(True)
        self._update_flag_controls(MODE_BLOCK, BLOCK_BROWN)

        # 敵スピード（常時表示、敵モード時のみ意味あり）
        self.speed_group = QGroupBox("敵スピード")
        sl = QHBoxLayout(self.speed_group)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        self.speed_btns = QButtonGroup(self)
        self.rb_sp1 = FullWidthRadioButton("SP1")
        self.rb_sp2 = FullWidthRadioButton("SP2")
        self.rb_sp3 = FullWidthRadioButton("SP3")
        for rb, sp in [
            (self.rb_sp1, 1),
            (self.rb_sp2, 2),
            (self.rb_sp3, 3),
        ]:
            self.speed_btns.addButton(rb)
            rb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            rb.setMinimumHeight(40)
            sl.addWidget(rb, 1)
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
            lst._icon_zoom_owner = self
            lst._enemy_speed_provider = self.get_enemy_speed
            lst._item_flag_provider = self.get_item_flag
            lst.setIconSize(QSize(self._icon_size, self._icon_size))
            lst.setViewMode(QListView.IconMode)
            lst.setMovement(QListView.Static)
            lst.setResizeMode(QListView.Adjust)
            lst.setWrapping(True)
            lst.setSpacing(0)
            lst.setGridSize(_picker_cell_size(self._icon_size))
            lst.setUniformItemSizes(True)
            lst.itemSelectionChanged.connect(self._on_item_selected)
            if cat_idx == 0:
                lst.ctrl_reorder_requested.connect(self._on_block_ctrl_reorder)
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

        self._extra_panel_slot = QVBoxLayout()
        self._extra_panel_slot.setContentsMargins(0, 4, 0, 0)
        picker_layout.addLayout(self._extra_panel_slot)
        picker_layout.addStretch()
        scroll.setWidget(picker_container)
        layout.addWidget(scroll, 1)

        self._mirror_detail_slot = QVBoxLayout()
        self._mirror_detail_slot.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._mirror_detail_slot)

        # ミラー出現敵パネル
        self.mirror_panel = MirrorEnemyPanel()
        self.mirror_panel.set_icon_zoom_owner(self)
        layout.addWidget(self.mirror_panel)

        # 下部パネル: お気に入り / ボーナスアイテム をスタック切替
        self._bottom_stack = QStackedWidget()

        # Page 0: お気に入りバー
        fav_page = QWidget()
        fav_lay = QVBoxLayout(fav_page)
        fav_lay.setContentsMargins(0, 0, 0, 0)
        fav_label = QLabel("<small>お気に入り</small>")
        fav_label.setToolTip("D&Dで登録 / 1〜0キーで選択 / Delで削除")
        fav_lay.addWidget(fav_label)
        self.favorites = FavoritesBar()
        self.favorites._icon_zoom_owner = self
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
        self.bonus_panel._icon_zoom_owner = self
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

    def set_icon_size_value(self, size: int, emit_signal: bool = False):
        new_size = clamp_picker_icon_size(size)
        if getattr(self, "_icon_size", ICON_SIZE) == new_size:
            return
        self._icon_size = new_size
        self._apply_icon_size_to_lists()
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()
        if emit_signal:
            self.icon_size_changed.emit(self._icon_size)

    def change_picker_icon_size(self, direction: int):
        self.set_icon_size_value(
            self._icon_size + PICKER_ICON_STEP * int(direction),
            emit_signal=True,
        )

    def _apply_icon_size_to_lists(self):
        item_size = _picker_cell_size(self._icon_size)
        for lst in getattr(self, "_picker_lists", []):
            lst.setIconSize(QSize(self._icon_size, self._icon_size))
            lst.setGridSize(item_size)
            for i in range(lst.count()):
                it = lst.item(i)
                if it is not None:
                    it.setSizeHint(item_size)
            self._adjust_list_height(lst)
        if hasattr(self, "favorites"):
            self.favorites.set_icon_size_value(self._icon_size)
        if hasattr(self, "bonus_panel"):
            self.bonus_panel.set_icon_size_value(self._icon_size)
        if hasattr(self, "mirror_panel"):
            self.mirror_panel.set_icon_size_value(self._icon_size)

    def set_mirror_detail_button(self, button):
        self._mirror_detail_slot.addWidget(button)

    def set_extra_panel_widget(self, widget):
        while self._extra_panel_slot.count():
            item = self._extra_panel_slot.takeAt(0)
            old = item.widget()
            if old is not None:
                old.setParent(None)
        self._extra_panel_slot.addWidget(widget)

    def set_tile_renderer(self, tile_renderer, config):
        """ROM読込後にレンダラを設定して、アイコン付きリストに更新"""
        self.tile_renderer = tile_renderer
        self.config = config
        self._populate_all()
        self.mirror_panel.set_renderers(tile_renderer, config)

    def set_marker_colors(self, colors: dict):
        self._marker_colors = dict(colors or {})
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()

    def set_marker_shapes(self, shapes: dict):
        self._marker_shapes = dict(shapes or {})
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()

    def set_marker_overlay_scale(self, scale: int):
        try:
            value = int(scale)
        except Exception:
            value = 3
        self._marker_overlay_scale = max(3, min(5, value))
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()

    def set_marker_source_tile_size(self, size):
        try:
            value = float(size)
        except Exception:
            value = ICON_SIZE
        new_size = max(float(ICON_SIZE), value)
        if abs(self._marker_source_tile_size - new_size) < 0.01:
            return
        self._marker_source_tile_size = new_size
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()

    def set_current_tileset_no(self, tileset_no: int):
        """現在レベルのタイルセット番号を設定し、アイコンを再描画"""
        if tileset_no == self.current_tileset_no:
            return
        self.current_tileset_no = tileset_no
        if self.tile_renderer is not None:
            self._populate_all()

    def set_current_level_context(self, level_no: int, tileset_no: int, wall_color):
        """現在ステージのタイルセット/背景色を設定し、アイコンを再描画"""
        try:
            level_no = int(level_no)
            tileset_no = int(tileset_no)
        except Exception:
            return
        wall_color = None if wall_color is None else (int(wall_color) & 0x3F)
        if (
            level_no == self.current_level_no and
            tileset_no == self.current_tileset_no and
            wall_color == self.current_wall_color
        ):
            return
        self.current_level_no = level_no
        self.current_tileset_no = tileset_no
        self.current_wall_color = wall_color
        if self.tile_renderer is not None:
            self._populate_all()

    # ========== Helper ==========

    def _make_icon_background(self, size: int) -> QImage:
        bg = QImage(size, size, QImage.Format_ARGB32)
        bg.fill(QColor(20, 20, 20))
        if self.tile_renderer is None or self.config is None:
            return bg
        from ..gfx.level_renderer import MD_EMPTY
        empty_anim = self.config.metadata_map.get(MD_EMPTY, 0)
        empty_img = self.tile_renderer.get_tile_image(
            empty_anim,
            self.current_tileset_no,
            transparent=False,
            bg_main_color=self.current_wall_color,
        )
        return empty_img.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)

    def _make_icon_from_tile(self, tile_no: int, apply_blue_filter: bool = False,
                             overlay_color=None, hatch_color=None,
                             block_marker=None, meta_marker_color_key=None) -> QIcon:
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

        from PyQt5.QtGui import QPainter, QColor, QPen
        from .level_view import (
            make_block_marker_graphics_items,
            marker_color,
            marker_pen_width,
            marker_shape,
            marker_shape_spec,
        )

        # tile_renderer は palette index 0 のみ透明扱いするので、そのまま使う
        sprite = self.tile_renderer.get_tile_image(
            tile_no,
            self.current_tileset_no,
            transparent=True,
            bg_main_color=self.current_wall_color,
        )

        # 現在ステージの空背景に重ね、キャンバス上の色と揃える
        icon_size = self._icon_size
        bg = self._make_icon_background(icon_size)
        painter = QPainter(bg)
        scaled = sprite.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.FastTransformation)
        ox = (icon_size - scaled.width()) // 2
        oy = (icon_size - scaled.height()) // 2
        painter.drawImage(ox, oy, scaled)
        if overlay_color is None and apply_blue_filter:
            overlay_color = (80, 130, 255, 90)
        if overlay_color is not None:
            painter.fillRect(ox, oy, scaled.width(), scaled.height(),
                             QColor(*overlay_color))
        if hatch_color is not None:
            pen = QPen(QColor(*hatch_color))
            pen.setWidth(2)
            painter.setPen(pen)
            left, top = ox, oy
            right = ox + scaled.width()
            bottom = oy + scaled.height()
            for delta in range(-scaled.height(), scaled.width() + 1, 7):
                x_start = left + max(delta, 0)
                y_start = top + max(-delta, 0)
                x_end = left + min(delta + scaled.height(), scaled.width())
                y_end = top + min(scaled.height(), scaled.height() - delta)
                painter.drawLine(x_start, y_start, x_end, y_end)
        if meta_marker_color_key is not None:
            source_size = max(icon_size, int(round(self._marker_source_tile_size)))
            output_scale = icon_size / float(source_size)
            pen = QPen(marker_color(self._marker_colors, meta_marker_color_key))
            pen.setWidth(marker_pen_width(2, self._marker_overlay_scale, output_scale))
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            inset = max(0, pen.width() // 2)
            painter.drawRect(inset, inset, icon_size - inset * 2 - 1, icon_size - inset * 2 - 1)
        if block_marker is not None:
            shape_key, color_key, width = block_marker
            shape, inset = marker_shape_spec(marker_shape(self._marker_shapes, shape_key))
            source_size = int(round(self._marker_source_tile_size))
            source_size = max(icon_size, source_size)
            source_img = self._make_icon_background(source_size)
            source_painter = QPainter(source_img)
            source_sprite = sprite.scaled(
                source_size, source_size, Qt.IgnoreAspectRatio, Qt.FastTransformation
            )
            source_painter.drawImage(0, 0, source_sprite)
            source_painter.end()

            scene = QGraphicsScene()
            scene.setSceneRect(0, 0, source_size, source_size)
            scene.addPixmap(QPixmap.fromImage(source_img))
            for item in make_block_marker_graphics_items(
                    (0, 0),
                    shape,
                    marker_color(self._marker_colors, color_key),
                    width,
                    inset,
                    self._marker_overlay_scale,
                    tile_size=source_size):
                item.setZValue(900)
                scene.addItem(item)
            rendered = QImage(source_size, source_size, QImage.Format_ARGB32)
            rendered.fill(QColor(20, 20, 20))
            render_painter = QPainter(rendered)
            render_painter.setRenderHint(QPainter.Antialiasing, True)
            scene.render(
                render_painter,
                QRectF(0, 0, source_size, source_size),
                scene.sceneRect(),
            )
            render_painter.end()
            icon_img = rendered.scaled(
                icon_size, icon_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            painter.end()
            return QIcon(QPixmap.fromImage(icon_img))
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
            BLOCK_PASSABLE_BROWN: MD_BLOCK_BROWN,
            BLOCK_SOLID_BROWN: MD_BLOCK_BROWN,
            BLOCK_BREAKABLE_WHITE: MD_BLOCK_WHITE,
            BLOCK_BROWN_WHITE: MD_BLOCK_WHITE,  # 見た目は白＋青フィルター
        }.get(block_kind)
        if meta_byte is None:
            return QIcon()
        anim = self.config.metadata_map.get(meta_byte, 0)
        from .level_view import block_marker_spec
        return self._make_icon_from_tile(anim, block_marker=block_marker_spec(block_kind))

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
        visual_enemy_no = PANEL_VARIANT_VISUAL_SOURCE.get(enemy_no, enemy_no)
        anim = self.config.enemy_map.get(visual_enemy_no, 0)
        if enemy_no in PANEL_VARIANT_VISUAL_SOURCE:
            return self._make_icon_from_tile(
                anim,
                overlay_color=(55, 135, 255, 115),
            )
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
        marker_key = {
            "mirror1": "mirror1_marker_color",
            "mirror2": "mirror2_marker_color",
        }.get(meta_kind)
        return self._make_icon_from_tile(anim, meta_marker_color_key=marker_key)

    # ========== Populate ==========

    def _populate_all(self):
        """4カテゴリに分けてグリッド表示。アイコンのみ・テキストはツールチップ。

        UserRole に (mode, value) のタプルを格納する。
        カテゴリ: [0]ブロック  [1]キャラ  [2]アイテム  [3]モンスター
        """
        restore_data = (self.current_mode, self.current_value)
        blocked_lists = []
        for lst in self._picker_lists:
            was_blocked = lst.blockSignals(True)
            blocked_lists.append((lst, was_blocked))
            lst.clear()

        try:
            # カテゴリ0: ブロック
            for val in self._block_order:
                label = BLOCK_PICKER_LABELS.get(val, str(val))
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

            if not self._select_data_silently(restore_data):
                default_row = (
                    self._block_order.index(BLOCK_BROWN)
                    if BLOCK_BROWN in self._block_order else 0
                )
                self._picker_lists[0].setCurrentRow(default_row)
                self.current_mode = MODE_BLOCK
                self.current_value = BLOCK_BROWN
                self._update_flag_controls(MODE_BLOCK, BLOCK_BROWN)
        finally:
            for lst, was_blocked in blocked_lists:
                lst.blockSignals(was_blocked)
        # お気に入りアイコンを最新パレットで再構築
        self._refresh_favorite_icons()

    def _select_data_silently(self, data) -> bool:
        """再描画後に現在選択中の項目を復元する。selection_changed は出さない。"""
        if not isinstance(data, tuple) or len(data) != 2:
            return False
        target_mode, target_value = data
        for lst in self._picker_lists:
            for i in range(lst.count()):
                it = lst.item(i)
                if it.data(Qt.UserRole) == (target_mode, target_value):
                    lst.setCurrentRow(i)
                    self.current_mode = target_mode
                    self.current_value = target_value
                    self._update_flag_controls(target_mode, target_value)
                    return True
        return False

    def set_block_order(self, order):
        """ブロックピッカー順を復元する。未知値/欠落は既定順で補完する。"""
        normalized = []
        if isinstance(order, list):
            for val in order:
                if val in DEFAULT_BLOCK_PICKER_ORDER and val not in normalized:
                    normalized.append(val)
        for val in DEFAULT_BLOCK_PICKER_ORDER:
            if val not in normalized:
                normalized.append(val)
        self._block_order = normalized
        if self.tile_renderer is not None and self.config is not None:
            self._populate_all()

    def get_block_order(self) -> list:
        return list(self._block_order)

    def _add_picker_item(self, category: int, mode: str, val, label: str, icon):
        """カテゴリ別リストにアイテムを追加"""
        it = QListWidgetItem(icon, "")
        it.setToolTip(f"[{mode}] {label}")
        it.setData(Qt.UserRole, (mode, val))
        it.setSizeHint(_picker_cell_size(self._icon_size))
        self._picker_lists[category].addItem(it)

    def _adjust_list_height(self, lst):
        """リストの高さをコンテンツ量に合わせて固定（スクロールバー不要にする）"""
        count = lst.count()
        if count == 0:
            lst.setFixedHeight(0)
            return
        grid_h = self._icon_size + GRID_PAD * 2
        # 幅からおおよその列数を推定（初期値として8列想定）
        cols = max(1, 8)
        rows = (count + cols - 1) // cols
        lst.setMinimumHeight(rows * grid_h + 4)
        lst.setMaximumHeight(rows * grid_h + 4)

    def _on_block_ctrl_reorder(self, src_row: int, dst_row: int):
        if src_row == dst_row:
            return
        block_list = self._picker_lists[0]
        src_item = block_list.item(src_row)
        dst_item = block_list.item(dst_row)
        if src_item is None or dst_item is None:
            return
        src_data = src_item.data(Qt.UserRole)
        dst_data = dst_item.data(Qt.UserRole)
        if not (
            isinstance(src_data, tuple) and src_data[0] == MODE_BLOCK and
            isinstance(dst_data, tuple) and dst_data[0] == MODE_BLOCK
        ):
            return
        source = src_data[1]
        target = dst_data[1]
        if source not in self._block_order or target not in self._block_order:
            return
        src_idx = self._block_order.index(source)
        dst_idx = self._block_order.index(target)
        self._block_order[src_idx], self._block_order[dst_idx] = (
            self._block_order[dst_idx],
            self._block_order[src_idx],
        )
        current = source if self.current_mode == MODE_BLOCK else None
        self._populate_all()
        if current in self._block_order:
            self._picker_lists[0].setCurrentRow(self._block_order.index(current))
        else:
            self._picker_lists[0].setCurrentRow(dst_row)
        self.block_order_changed.emit(self.get_block_order())

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
        self._update_flag_controls(mode, val)
        self._update_speed_controls(mode, val)
        self.selection_changed.emit(mode, val)

    def _on_flag_changed(self, flag: int):
        self.current_item_flag = flag

    def _on_speed_changed(self, speed: int):
        self.current_enemy_speed = speed

    def _update_flag_controls(self, mode, value):
        all_flags = (
            ITEM_FLAG_NORMAL,
            ITEM_FLAG_HIDDEN,
            ITEM_FLAG_IN_BLOCK,
            ITEM_FLAG_WHITE_IN_BLOCK,
            ITEM_FLAG_VISIBLE_IN_BLOCK,
        )
        if mode == MODE_META and value in ("start", "mirror1", "mirror2"):
            allowed = {ITEM_FLAG_NORMAL}
        elif mode == MODE_META and value in ("key", "door"):
            allowed = {
                ITEM_FLAG_NORMAL,
                ITEM_FLAG_HIDDEN,
                ITEM_FLAG_IN_BLOCK,
                ITEM_FLAG_WHITE_IN_BLOCK,
            }
        else:
            allowed = set(all_flags)

        buttons = (
            (self.rb_flag_normal, ITEM_FLAG_NORMAL),
            (self.rb_flag_hidden, ITEM_FLAG_HIDDEN),
            (self.rb_flag_in_block, ITEM_FLAG_IN_BLOCK),
            (self.rb_flag_white_in_block, ITEM_FLAG_WHITE_IN_BLOCK),
            (self.rb_flag_visible_in_block, ITEM_FLAG_VISIBLE_IN_BLOCK),
        )
        for rb, flag in buttons:
            rb.setEnabled(flag in allowed)

        if self.current_item_flag not in allowed:
            self.rb_flag_normal.setChecked(True)
            self.current_item_flag = ITEM_FLAG_NORMAL

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
        """アイテム配置時に付加するフラグ (0x00 / 0x40 / 0x80 / 0xC0)"""
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
