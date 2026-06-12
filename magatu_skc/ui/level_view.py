"""レベル表示ウィジェット - クリック編集対応"""
from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsItem,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont, QPolygonF
from PyQt5.QtCore import Qt, pyqtSignal, QPointF

from ..core import constants as c

DEFAULT_MARKER_COLORS = {
    "bonus_marker_color": "#FFC800",
    "hidden_marker_color": "#FFDC00",
    "visible_in_block_marker_color": "#00E5FF",
    "breakable_white_marker_color": "#50E65A",
    "invisible_breakable_marker_color": "#FFDC28",
    "passable_marker_color": "#50BEFF",
    "solid_marker_color": "#FF78DC",
    "mirror1_marker_color": "#FF3C3C",
    "mirror2_marker_color": "#3C78FF",
    "special_empty_marker_color": "#B4C8FF",
    "special_trigger_marker_color": "#FF64C8",
    "special_link_marker_color": "#FFC864",
    "selection_marker_color": "#FFE600",
    "hover_marker_color": "#FFFFFF",
}

DEFAULT_MARKER_OVERLAY_SCALE = 3

MARKER_SHAPE_OPTIONS = [
    ("rect_large", "四角 大"),
    ("rect_small", "四角 小"),
    ("cross_large", "× 大"),
    ("cross_medium", "× 中"),
    ("cross_small", "× 小"),
    ("ellipse_large", "丸 大"),
    ("ellipse_small", "丸 小"),
    ("triangle_large", "三角 大"),
    ("triangle_small", "三角 小"),
    ("plus_large", "十字 大"),
    ("plus_small", "十字 小"),
]

MARKER_SHAPE_SPECS = {
    "rect_large": ("rect", 1),
    "rect_small": ("rect", 4),
    "cross_large": ("cross", 1),
    "cross_medium": ("cross", 3),
    "cross_small": ("cross", 4),
    "ellipse_large": ("ellipse", 1),
    "ellipse_small": ("ellipse", 4),
    "triangle_large": ("triangle", 1),
    "triangle_small": ("triangle", 4),
    "plus_large": ("plus", 1),
    "plus_small": ("plus", 4),
}

DEFAULT_MARKER_SHAPES = {
    "breakable_white_marker_shape": "rect_large",
    "invisible_breakable_marker_shape": "rect_small",
    "passable_marker_shape": "cross_medium",
    "solid_marker_shape": "ellipse_small",
}

BLOCK_MARKER_SPECS = {
    "breakable_white": ("breakable_white_marker_shape", "breakable_white_marker_color", 3),
    "invisible_breakable": ("invisible_breakable_marker_shape", "invisible_breakable_marker_color", 3),
    "passable_white": ("passable_marker_shape", "passable_marker_color", 3),
    "passable_brown": ("passable_marker_shape", "passable_marker_color", 3),
    "solid_brown": ("solid_marker_shape", "solid_marker_color", 3),
    "invisible_solid": ("solid_marker_shape", "solid_marker_color", 3),
}


def marker_color(colors: dict, key: str) -> QColor:
    color = QColor(str((colors or {}).get(key, DEFAULT_MARKER_COLORS[key])))
    return color if color.isValid() else QColor(DEFAULT_MARKER_COLORS[key])


def marker_shape(shapes: dict, key: str) -> str:
    default = DEFAULT_MARKER_SHAPES[key]
    value = str((shapes or {}).get(key, default))
    return value if value in MARKER_SHAPE_SPECS else default


def marker_shape_spec(shape_key: str):
    return MARKER_SHAPE_SPECS.get(shape_key, MARKER_SHAPE_SPECS["rect_large"])


def marker_pen_width(width: int, overlay_scale: int, output_scale: float = 1.0) -> int:
    return max(1, int(round(width * overlay_scale * output_scale)))


def block_marker_pen(color: QColor, width: int, overlay_scale: int,
                     output_scale: float = 1.0) -> QPen:
    pen = QPen(color)
    pen.setWidth(marker_pen_width(width, overlay_scale, output_scale))
    pen.setStyle(Qt.SolidLine)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    pen.setCosmetic(True)
    return pen


def block_marker_rect(pos, tile_size: float, inset: int, offset=(0, 0)):
    x, y = pos
    ox, oy = offset
    scale = tile_size / float(c.TILE_WIDTH)
    px = (x + ox) * tile_size + inset * scale
    py = (y + oy) * tile_size + inset * scale
    size = max(1.0, tile_size - inset * 2 * scale)
    return px, py, size, size


def make_block_marker_graphics_items(
        pos, shape: str, color: QColor, width: int, inset: int,
        overlay_scale: int, tile_size: float = c.TILE_WIDTH, offset=(0, 0),
        output_scale: float = 1.0):
    x, y, w, h = block_marker_rect(pos, tile_size, inset, offset)
    pen = block_marker_pen(color, width, overlay_scale, output_scale)
    if shape == "rect":
        item = QGraphicsRectItem(x, y, w, h)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        return [item]
    if shape == "cross":
        a = QGraphicsLineItem(x, y, x + w, y + h)
        b = QGraphicsLineItem(x + w, y, x, y + h)
        a.setPen(pen)
        b.setPen(pen)
        return [a, b]
    if shape == "ellipse":
        item = QGraphicsEllipseItem(x, y, w, h)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        return [item]
    if shape == "triangle":
        polygon = QGraphicsPolygonItem(QPolygonF([
            QPointF(x + w / 2, y),
            QPointF(x + w, y + h),
            QPointF(x, y + h),
        ]))
        polygon.setPen(pen)
        polygon.setBrush(QBrush(Qt.NoBrush))
        return [polygon]
    if shape == "plus":
        cx = x + w / 2
        cy = y + h / 2
        a = QGraphicsLineItem(cx, y, cx, y + h)
        b = QGraphicsLineItem(x, cy, x + w, cy)
        a.setPen(pen)
        b.setPen(pen)
        return [a, b]
    return []


def block_marker_spec(block_kind: str):
    aliases = {
        "brown_white": "breakable_white",
        "breakable_white": "breakable_white",
        "invisible_breakable": "invisible_breakable",
        "passable_white": "passable_white",
        "passable_brown": "passable_brown",
        "invisible_solid": "invisible_solid",
        "solid_brown": "solid_brown",
    }
    marker_kind = aliases.get(block_kind)
    return BLOCK_MARKER_SPECS.get(marker_kind)


class LevelView(QGraphicsView):
    """レベル画像表示 + クリック検出 + D&D"""

    # マウスイベント: ボタン, タイル座標(x, y), modifiers
    tile_clicked = pyqtSignal(int, tuple, int)
    tile_right_clicked = pyqtSignal(tuple)
    # ROM ファイルが drop された
    rom_dropped = pyqtSignal(str)
    # ステージデータPNGが単体でdropされた
    stage_png_dropped = pyqtSignal(str)
    # Ctrl+左ドラッグ用シグナル
    drag_start = pyqtSignal(tuple)   # 開始タイル
    drag_move = pyqtSignal(tuple)    # 移動先タイル（変化時のみ）
    drag_end = pyqtSignal()          # 解放
    # ホバー: マウスカーソルの真下のタイル（None で領域外）
    tile_hovered = pyqtSignal(object)
    # キャンバス上で押された方向キー
    direction_key_pressed = pyqtSignal(str)
    # ドラッグ塗り（左ボタン押しっぱなし移動）/ ドラッグ消し（右ボタン押しっぱなし移動）
    tile_painted = pyqtSignal(int, tuple, int)  # tile_clicked と同じシグネチャ
    tile_erased = pyqtSignal(tuple)              # tile_right_clicked と同じシグネチャ
    # スポイト: Alt+左クリックでその位置の要素をピッカーへ
    tile_picked = pyqtSignal(tuple)
    # Shift+左ドラッグで矩形範囲選択（更新時 / 解除時 / 確定時）
    selection_updated = pyqtSignal(object, object)  # (start_tile, end_tile) どちらも tuple or None
    selection_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        # QGraphicsScene の drag-drop も無効化（こちらで処理）
        self.scene().setBackgroundBrush(Qt.black)

        self._pixmap_item: QGraphicsPixmapItem = None
        # Ctrl+左ドラッグ中の状態
        self._dragging = False
        self._last_drag_tile = None
        # ホバー追跡用
        self.setMouseTracking(True)
        self._last_hover_tile = None
        # ドラッグ塗り / 消し
        self._painting = False
        self._erasing = False
        self._last_paint_tile = None
        self._last_erase_tile = None
        # Shift+左ドラッグの矩形選択
        self._selecting = False
        self._select_start = None
        self._select_end = None
        self._label_items = []
        self._overlay_items = []
        self._marker_overlay_scale = 3
        self._marker_colors = {
            key: QColor(value) for key, value in DEFAULT_MARKER_COLORS.items()
        }
        self._marker_shapes = dict(DEFAULT_MARKER_SHAPES)

    def set_image(self, qimage):
        scene = self.scene()
        scene.clear()
        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item = scene.addPixmap(pixmap)
        scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self._label_items = []
        self._overlay_items = []
        self.fit_to_view()

    def _tile_offsets(self):
        x_offset = 0
        y_offset = 0
        if self._pixmap_item is not None:
            img_w = self._pixmap_item.pixmap().width()
            img_h = self._pixmap_item.pixmap().height()
            extra_cols = (img_w // c.TILE_WIDTH) - c.LEVEL_W
            extra_rows = (img_h // c.TILE_WIDTH) - c.LEVEL_H
            if extra_cols > 0:
                x_offset = extra_cols
            if extra_rows >= 2:
                y_offset = 1
        return x_offset, y_offset

    def clear_editor_overlays(self):
        scene = self.scene()
        for item in self._overlay_items:
            scene.removeItem(item)
        self._overlay_items = []

    def _overlay_pen(self, color, width=2, style=Qt.SolidLine):
        pen = QPen(color)
        pen.setWidth(marker_pen_width(width, self._marker_overlay_scale))
        pen.setStyle(style)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        pen.setCosmetic(True)
        return pen

    def set_marker_overlay_scale(self, scale: int):
        try:
            value = int(scale)
        except Exception:
            value = DEFAULT_MARKER_OVERLAY_SCALE
        self._marker_overlay_scale = max(3, min(5, value))

    def set_bonus_marker_color(self, color_value):
        self.set_marker_colors({"bonus_marker_color": color_value})

    def set_marker_colors(self, colors: dict):
        for key, default in DEFAULT_MARKER_COLORS.items():
            if key not in colors:
                continue
            color = QColor(str(colors.get(key) or default))
            self._marker_colors[key] = color if color.isValid() else QColor(default)

    def set_marker_shapes(self, shapes: dict):
        for key, default in DEFAULT_MARKER_SHAPES.items():
            value = str((shapes or {}).get(key, default))
            self._marker_shapes[key] = value if value in MARKER_SHAPE_SPECS else default

    def _marker_color(self, key: str) -> QColor:
        return QColor(self._marker_colors.get(key, QColor(DEFAULT_MARKER_COLORS[key])))

    def _marker_shape(self, key: str) -> str:
        return marker_shape(self._marker_shapes, key)

    def set_editor_overlays(self, overlays, with_border: bool = True):
        self.clear_editor_overlays()
        if not overlays:
            return
        scene = self.scene()
        tw = c.TILE_WIDTH
        ox, oy = self._tile_offsets() if with_border else (0, 0)

        def add(item):
            item.setZValue(900)
            scene.addItem(item)
            self._overlay_items.append(item)
            return item

        def rect_for_tile(pos, inset=1):
            x, y = pos
            return (
                (x + ox) * tw + inset,
                (y + oy) * tw + inset,
                tw - inset * 2,
                tw - inset * 2,
            )

        def add_rect(pos, color, width=2, inset=1, style=Qt.SolidLine):
            item = QGraphicsRectItem(*rect_for_tile(pos, inset))
            item.setPen(self._overlay_pen(color, width, style))
            item.setBrush(QBrush(Qt.NoBrush))
            add(item)

        def add_cross(pos, color, width=2, inset=3):
            x, y, w, h = rect_for_tile(pos, inset)
            add(QGraphicsLineItem(x, y, x + w, y + h)).setPen(
                self._overlay_pen(color, width)
            )
            add(QGraphicsLineItem(x + w, y, x, y + h)).setPen(
                self._overlay_pen(color, width)
            )

        def add_ellipse(pos, color, width=2, inset=4):
            item = QGraphicsEllipseItem(*rect_for_tile(pos, inset))
            item.setPen(self._overlay_pen(color, width))
            item.setBrush(QBrush(Qt.NoBrush))
            add(item)

        def add_diamond(pos, color, width=2, inset=2):
            x, y, w, h = rect_for_tile(pos, inset)
            cx = x + w / 2
            cy = y + h / 2
            polygon = self.scene().addPolygon(
                QPolygonF([
                    QPointF(cx, y),
                    QPointF(x + w, cy),
                    QPointF(cx, y + h),
                    QPointF(x, cy),
                ]),
                self._overlay_pen(color, width),
                QBrush(Qt.NoBrush),
            )
            polygon.setZValue(900)
            self._overlay_items.append(polygon)

        for marker_key, (shape_key, color_key, width) in BLOCK_MARKER_SPECS.items():
            for pos in overlays.get(marker_key, ()):
                shape, inset = marker_shape_spec(self._marker_shape(shape_key))
                for item in make_block_marker_graphics_items(
                        pos,
                        shape,
                        self._marker_color(color_key),
                        width,
                        inset,
                        self._marker_overlay_scale,
                        tile_size=tw,
                        offset=(ox, oy)):
                    add(item)
        for pos in overlays.get("hidden_item", ()):
            add_rect(pos, self._marker_color("hidden_marker_color"), width=2, inset=1)
        for pos in overlays.get("visible_in_block_item", ()):
            add_rect(pos, self._marker_color("visible_in_block_marker_color"), width=3, inset=0)
        for pos in overlays.get("hidden_meta", ()):
            add_rect(pos, self._marker_color("hidden_marker_color"), width=2, inset=1)

        for mi, pos in overlays.get("mirrors", ()):
            color = self._marker_color(
                "mirror1_marker_color" if mi == 0 else "mirror2_marker_color"
            )
            add_rect(pos, color, width=2, inset=0)

        for pos in overlays.get("bonus", ()):
            add_diamond(pos, self._marker_color("bonus_marker_color"), width=3, inset=2)

        special = overlays.get("special_marks") or {}
        mark_colors = {
            "breakable": self._marker_color("breakable_white_marker_color"),
            "breakable_conditional": self._marker_color("breakable_white_marker_color"),
            "empty_forced": self._marker_color("special_empty_marker_color"),
            "trigger": self._marker_color("special_trigger_marker_color"),
            "bomb_jack_trigger": self._marker_color("special_trigger_marker_color"),
            "hidden_bomb_jack": self._marker_color("hidden_marker_color"),
        }
        for key, kind in special.items():
            if key == "__links__":
                continue
            style = Qt.DashLine if kind == "breakable_conditional" else Qt.SolidLine
            add_rect(key, mark_colors.get(kind, QColor(255, 0, 255)), width=3, inset=1, style=style)

        for (tx, ty), (gx, gy) in special.get("__links__", []):
            x1 = (tx + ox) * tw + tw // 2
            y1 = (ty + oy) * tw + tw // 2
            x2 = (gx + ox) * tw + tw // 2
            y2 = (gy + oy) * tw + tw // 2
            item = QGraphicsLineItem(x1, y1, x2, y2)
            link_color = self._marker_color("special_link_marker_color")
            link_color.setAlpha(180)
            item.setPen(self._overlay_pen(link_color, 1, Qt.DashLine))
            add(item)

        selection = overlays.get("selection_rect")
        if selection and selection[0] and selection[1]:
            (sx, sy), (ex, ey) = selection
            x1, y1 = min(sx, ex), min(sy, ey)
            x2, y2 = max(sx, ex), max(sy, ey)
            item = QGraphicsRectItem(
                (x1 + ox) * tw,
                (y1 + oy) * tw,
                (x2 - x1 + 1) * tw,
                (y2 - y1 + 1) * tw,
            )
            selection_color = self._marker_color("selection_marker_color")
            fill_color = QColor(selection_color)
            fill_color.setAlpha(60)
            item.setPen(self._overlay_pen(selection_color, 2, Qt.DashLine))
            item.setBrush(QBrush(fill_color))
            add(item)

        hover = overlays.get("hover_tile")
        if hover is not None:
            hover_color = self._marker_color("hover_marker_color")
            hover_color.setAlpha(220)
            add_rect(hover, hover_color, width=2, inset=0)

    def set_object_labels(self, labels, with_border: bool = True):
        """キャンバス注釈をビュー上の通常フォントで重ねる。

        labels: [(x, y, text), ...]。x/y はゲーム内16x12座標。
        """
        scene = self.scene()
        for item in self._label_items:
            scene.removeItem(item)
        self._label_items = []
        if not labels:
            return

        tw = c.TILE_WIDTH
        ox = 1 if with_border else 0
        oy = 0
        if with_border and self._pixmap_item is not None:
            img_h = self._pixmap_item.pixmap().height()
            extra_rows = (img_h // c.TILE_WIDTH) - c.LEVEL_H
            if extra_rows >= 2:
                oy = 1
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        per_tile = {}
        line_step = 13

        for x, y, text in labels:
            text = str(text)
            n = per_tile.get((x, y), 0)
            per_tile[(x, y)] = n + 1
            sx = (x + ox) * tw
            sy = (y + oy) * tw + n * line_step

            txt = QGraphicsSimpleTextItem(text)
            txt.setFont(font)
            txt.setBrush(QBrush(QColor(255, 255, 255)))
            txt.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            txt.setZValue(1001)
            txt.setPos(sx + 2, sy + 1)

            br = txt.boundingRect()
            bg = QGraphicsRectItem(0, 0, br.width() + 4, br.height() + 2)
            bg.setBrush(QBrush(QColor(0, 0, 0, 185)))
            bg.setPen(QPen(Qt.NoPen))
            bg.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            bg.setZValue(1000)
            bg.setPos(sx, sy)

            scene.addItem(bg)
            scene.addItem(txt)
            self._label_items.extend([bg, txt])

    def fit_to_view(self):
        if self._pixmap_item is None:
            return
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def display_tile_size(self) -> float:
        return max(1.0, c.TILE_WIDTH * float(self.transform().m11()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_view()

    def _scene_to_tile(self, scene_pos: QPointF):
        """シーン座標 → タイル座標(x, y)

        画像サイズが LEVEL_W*TILE_WIDTH / LEVEL_H*TILE_WIDTH より大きい場合、
        パディング分を差し引く（16列目非表示モード・装飾ボーダー対応）。
        """
        x_offset, y_offset = self._tile_offsets()
        tx = int(scene_pos.x() // c.TILE_WIDTH) - x_offset
        ty = int(scene_pos.y() // c.TILE_WIDTH) - y_offset
        if 0 <= tx < c.LEVEL_W and 0 <= ty < c.LEVEL_H:
            return (tx, ty)
        return None

    # ====== Drag & Drop ======

    @staticmethod
    def _single_local_path(md):
        if not md.hasUrls() or len(md.urls()) != 1:
            return None
        url = md.urls()[0]
        if not url.isLocalFile():
            return None
        return url.toLocalFile()

    @staticmethod
    def _is_supported_drop_path(path: str) -> bool:
        lower = str(path).lower()
        return lower.endswith('.nes') or lower.endswith('.zip') or lower.endswith('.png')

    def dragEnterEvent(self, event):
        """D&D 開始時 - .nes/.zip または単体 .png なら受け入れ"""
        md = event.mimeData()
        path = self._single_local_path(md)
        if path and self._is_supported_drop_path(path):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        path = self._single_local_path(event.mimeData())
        if path and self._is_supported_drop_path(path):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        md = event.mimeData()
        if not md.hasUrls():
            event.ignore()
            return

        path = self._single_local_path(md)
        if not path:
            event.ignore()
            return
        lower = path.lower()
        if lower.endswith('.nes') or lower.endswith('.zip'):
            event.acceptProposedAction()
            self.rom_dropped.emit(path)
            return
        if lower.endswith('.png'):
            event.acceptProposedAction()
            self.stage_png_dropped.emit(path)
            return

        event.ignore()

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        tile = self._scene_to_tile(scene_pos)
        if tile is None:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl+左クリックでドラッグ開始
                self._dragging = True
                self._last_drag_tile = tile
                self.drag_start.emit(tile)
            elif event.modifiers() & Qt.AltModifier:
                # Alt+左クリックでスポイト
                self.tile_picked.emit(tile)
            elif event.modifiers() & Qt.ShiftModifier:
                # Shift+左ドラッグで矩形範囲選択
                self._selecting = True
                self._select_start = tile
                self._select_end = tile
                self.selection_updated.emit(tile, tile)
            else:
                # 通常の左クリック → 配置 + ドラッグ塗り開始
                # 既存の選択範囲があればクリア
                if self._select_start is not None:
                    self._select_start = None
                    self._select_end = None
                    self.selection_cleared.emit()
                self.tile_clicked.emit(int(event.button()), tile, int(event.modifiers()))
                self._painting = True
                self._last_paint_tile = tile
        elif event.button() == Qt.RightButton:
            # 右クリック → 削除 + ドラッグ消し開始
            self.tile_right_clicked.emit(tile)
            self._erasing = True
            self._last_erase_tile = tile
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        tile = self._scene_to_tile(scene_pos)

        # Ctrl+ドラッグ（要素移動）
        if self._dragging and (event.modifiers() & Qt.ControlModifier):
            if tile is not None and tile != self._last_drag_tile:
                self._last_drag_tile = tile
                self.drag_move.emit(tile)
        elif self._dragging:
            # Ctrl が離されたらドラッグ終了
            self._dragging = False
            self._last_drag_tile = None
            self.drag_end.emit()

        # 左ドラッグ塗り
        if self._painting and tile is not None and tile != self._last_paint_tile:
            self._last_paint_tile = tile
            self.tile_painted.emit(int(Qt.LeftButton), tile, int(event.modifiers()))

        # 右ドラッグ消し
        if self._erasing and tile is not None and tile != self._last_erase_tile:
            self._last_erase_tile = tile
            self.tile_erased.emit(tile)

        # Shift+左ドラッグの矩形選択更新
        if self._selecting and tile is not None and tile != self._select_end:
            self._select_end = tile
            self.selection_updated.emit(self._select_start, self._select_end)

        # ホバー通知（タイル変化時のみ）
        if tile != self._last_hover_tile:
            self._last_hover_tile = tile
            self.tile_hovered.emit(tile)
        if tile is not None and not self.hasFocus():
            self.setFocus(Qt.MouseFocusReason)

        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.NoModifier:
            direction_by_key = {
                Qt.Key_Left: "left",
                Qt.Key_Right: "right",
                Qt.Key_Up: "up",
                Qt.Key_Down: "down",
            }
            direction = direction_by_key.get(event.key())
            if direction is not None:
                self.direction_key_pressed.emit(direction)
                event.accept()
                return
        super().keyPressEvent(event)

    def leaveEvent(self, event):
        if self._last_hover_tile is not None:
            self._last_hover_tile = None
            self.tile_hovered.emit(None)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self._last_drag_tile = None
            self.drag_end.emit()
        if event.button() == Qt.LeftButton:
            self._painting = False
            self._last_paint_tile = None
            if self._selecting:
                # 選択確定
                self._selecting = False
                self.selection_updated.emit(self._select_start, self._select_end)
        elif event.button() == Qt.RightButton:
            self._erasing = False
            self._last_erase_tile = None
        super().mouseReleaseEvent(event)

    def keyReleaseEvent(self, event):
        # Ctrl を離した瞬間にドラッグ終了
        if self._dragging and not (event.modifiers() & Qt.ControlModifier):
            self._dragging = False
            self._last_drag_tile = None
            self.drag_end.emit()
        super().keyReleaseEvent(event)
