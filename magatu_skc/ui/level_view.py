"""レベル表示ウィジェット - クリック編集対応"""
from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsItem,
    QGraphicsLineItem, QGraphicsEllipseItem,
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QPointF

from ..core import constants as c


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
        pen.setWidth(max(1, int(round(width * self._marker_overlay_scale))))
        pen.setStyle(style)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        pen.setCosmetic(True)
        return pen

    def set_marker_overlay_scale(self, scale: int):
        try:
            value = int(scale)
        except Exception:
            value = 3
        self._marker_overlay_scale = max(3, min(5, value))

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

        for pos in overlays.get("breakable_white", ()):
            add_rect(pos, QColor(80, 230, 90), width=3, inset=1)
        for pos in overlays.get("invisible_breakable", ()):
            add_rect(pos, QColor(255, 220, 40), width=3, inset=4)
        for pos in overlays.get("passable_white", ()):
            add_cross(pos, QColor(80, 190, 255), width=3, inset=3)
        for pos in overlays.get("passable_brown", ()):
            add_cross(pos, QColor(80, 190, 255), width=3, inset=3)
        for pos in overlays.get("solid_brown", ()):
            add_ellipse(pos, QColor(255, 120, 220), width=3, inset=4)
        for pos in overlays.get("invisible_solid", ()):
            add_ellipse(pos, QColor(255, 120, 220), width=3, inset=4)
        for pos in overlays.get("hidden_item", ()):
            add_rect(pos, QColor(255, 220, 0), width=2, inset=1)
        for pos in overlays.get("hidden_meta", ()):
            add_rect(pos, QColor(255, 220, 0), width=2, inset=1)

        for mi, pos in overlays.get("mirrors", ()):
            color = QColor(255, 60, 60) if mi == 0 else QColor(60, 120, 255)
            add_rect(pos, color, width=2, inset=0)

        for pos in overlays.get("bonus", ()):
            add_rect(pos, QColor(255, 200, 0), width=2, inset=3)

        special = overlays.get("special_marks") or {}
        mark_colors = {
            "breakable": QColor(80, 230, 90),
            "breakable_conditional": QColor(80, 230, 90),
            "empty_forced": QColor(180, 200, 255),
            "trigger": QColor(255, 100, 200),
            "hidden_bomb_jack": QColor(255, 220, 0),
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
            item.setPen(self._overlay_pen(QColor(255, 200, 100, 180), 1, Qt.DashLine))
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
            item.setPen(self._overlay_pen(QColor(255, 230, 0), 2, Qt.DashLine))
            item.setBrush(QBrush(QColor(255, 230, 0, 60)))
            add(item)

        hover = overlays.get("hover_tile")
        if hover is not None:
            add_rect(hover, QColor(255, 255, 255, 220), width=2, inset=0)

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

        super().mouseMoveEvent(event)

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
