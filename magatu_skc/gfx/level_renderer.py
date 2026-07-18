"""レベル全体の描画 - QImageでレベル1個分をレンダリング"""
import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QBrush, QPolygon
from PyQt5.QtWidgets import QGraphicsScene

from ..core import constants as c
from ..core import room_flags, stage50_book_color, stage_ext
from ..core.element import Wall, ElementType
from ..core.level import Level
from .tile_renderer import TileRenderer
from ..ui.element_picker import (
    apply_enemy_picker_overlay,
)


# メタタイル番号定数（C++ Constants_level.h より）
MD_KEY = 0x00
MD_DOOR = 0x01
MD_PLAYER_START = 0x02
MD_SPAWN01 = 0x03
MD_SPAWN02 = 0x04
MD_EMPTY = 0x05
MD_BLOCK_BROWN = 0x06
MD_BLOCK_WHITE = 0x07
MD_BLOCK_BW = 0x08
MD_PLAYER_START_LEFT = 0x09
MD_SOLOMONS_KEY = 0x10
MD_CONSTELLATION = 0x11


PANEL_VARIANT_VISUAL_SOURCE = {
    code: 0x24 + (code & 0x03)
    for code in range(0xE0, 0xF8)
}

ENEMY_VISUAL_SOURCE = {
    **PANEL_VARIANT_VISUAL_SOURCE,
    0x5E: 0x5C, 0x5F: 0x5D,
    0x62: 0x60, 0x63: 0x61,
    0x66: 0x64, 0x67: 0x65,
    0x6A: 0x68, 0x6B: 0x69,
    0x6E: 0x6C, 0x6F: 0x6D,
    0x72: 0x70, 0x73: 0x71,
    0x76: 0x74, 0x77: 0x75,
    0x9E: 0x68,
    **{code: (0x30 if (code & 1) == 0 else 0x32) for code in range(0x84, 0x88)},
    **{code: (0x36 if code & 1 else 0x34) for code in range(0xB0, 0xBC)},
    **{code: 0x20 + (code & 3) for code in range(0xA0, 0xB0)},
}

ENEMY_PALETTE_OVERRIDE = {
    0x5E: 6,
    0x5F: 6,
    0x62: 6,
    0x63: 6,
    0x66: 6,
    0x67: 6,
    0x6A: 6,
    0x6B: 6,
    0x6E: 4,
    0x6F: 4,
    0x72: 6,
    0x73: 6,
    0x76: 4,
    0x77: 4,
    **{code: 6 for code in range(0xA0, 0xB0)},
}

MARKER_RENDER_SCALE = 4
KEY_ENEMY_OVERLAY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAA70lEQVR42u3aQQ6CMBAFUC7"
    "ixkN5MteeTjdeArcGkg5NC5T2TTJLIvMWP0zrNCmlhq7H7dhu7fcBAADQF8D785xTDQAAg"
    "L4ANgy8bAAAAFy4cgcOQxAAgMEBWl9mSkPu+7rP/716HgAAAFdbZpIhF73vEgQAAABtLz"
    "OrF84MueqHogAAdAZQexkp7WjgqEqfBwBgNIAdlpFkZ19cVA5tAAAAlAFEAy5DKOoI4PQ/"
    "SAAAACAJkDswAAAA2gIoXX72DsHTCwCAzgH2PsSMBs4NwdohCQAAgLIPidJD0NyMAgAAQ"
    "FsAtS8fj76cBQBgcIAfAxxSUpWPhjkAAAAASUVORK5CYII="
)


class LevelRenderer:

    def __init__(self, tile_renderer: TileRenderer, config):
        self.tr = tile_renderer
        self.config = config
        self._marker_overlay_scale = 3
        self._marker_colors = {}
        self._marker_shapes = {}
        self._key_enemy_overlay_cache = {}
        self._darkened_sprite_cache = {}
        self.wall_color_values = None
        self.stage50_solomon_book_color = stage50_book_color.ORIGINAL_COLOR

    def _draw_marker_layer(self, painter: QPainter, width: int, height: int, draw_func):
        marker = QImage(
            width * MARKER_RENDER_SCALE,
            height * MARKER_RENDER_SCALE,
            QImage.Format_ARGB32_Premultiplied,
        )
        marker.fill(QColor(0, 0, 0, 0))
        mp = QPainter(marker)
        try:
            mp.setRenderHint(QPainter.Antialiasing, True)
            mp.scale(MARKER_RENDER_SCALE, MARKER_RENDER_SCALE)
            draw_func(mp)
        finally:
            mp.end()
        smoothed = marker.scaled(
            width,
            height,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawImage(0, 0, smoothed)

    def _key_enemy_overlay_image(self, target_size: int) -> QImage:
        cache_key = ("key_enemy_overlay", int(target_size))
        cached = self._key_enemy_overlay_cache.get(cache_key)
        if cached is not None:
            return cached
        out = QImage()
        out.loadFromData(base64.b64decode(KEY_ENEMY_OVERLAY_PNG_B64), "PNG")
        if out.width() != target_size or out.height() != target_size:
            out = out.scaled(
                target_size,
                target_size,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )
        self._key_enemy_overlay_cache[cache_key] = out
        return out

    def key_enemy_overlay_image(self, target_size: int) -> QImage:
        return self._key_enemy_overlay_image(target_size)

    def _darkened_sprite_image(self, source: QImage) -> QImage:
        cache_key = ("darkened_sprite", int(source.cacheKey()))
        cached = self._darkened_sprite_cache.get(cache_key)
        if cached is not None:
            return cached
        darkened = QImage(source.size(), QImage.Format_ARGB32_Premultiplied)
        darkened.fill(QColor(0, 0, 0, 0))
        painter = QPainter(darkened)
        try:
            painter.drawImage(0, 0, source)
            painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            painter.fillRect(darkened.rect(), QColor(0, 0, 0, 88))
        finally:
            painter.end()
        self._darkened_sprite_cache[cache_key] = darkened
        return darkened

    def set_marker_overlay_scale(self, scale: int):
        from ..ui.level_view import DEFAULT_MARKER_OVERLAY_SCALE
        try:
            value = int(scale)
        except Exception:
            value = DEFAULT_MARKER_OVERLAY_SCALE
        self._marker_overlay_scale = max(3, min(5, value))

    def set_marker_colors(self, colors: dict):
        self._marker_colors = dict(colors or {})

    def set_marker_shapes(self, shapes: dict):
        self._marker_shapes = dict(shapes or {})

    def _marker_color(self, key: str) -> QColor:
        from ..ui.level_view import marker_color
        return marker_color(self._marker_colors, key)

    def _saved_marker_output_scale(self) -> float:
        from ..ui.level_view import DEFAULT_MARKER_OVERLAY_SCALE
        return 1.0 / float(DEFAULT_MARKER_OVERLAY_SCALE)

    def _marker_pen(self, key: str, width: int, style=Qt.SolidLine, alpha=None) -> QPen:
        from ..ui.level_view import marker_pen_width
        color = self._marker_color(key)
        if alpha is not None:
            color.setAlpha(alpha)
        pen = QPen(color)
        pen.setWidth(marker_pen_width(
            width,
            self._marker_overlay_scale,
            self._saved_marker_output_scale(),
        ))
        pen.setStyle(style)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def _draw_block_marker_cells(self, painter: QPainter, img_w: int, img_h: int,
                                 marker_key: str, cells):
        if not cells:
            return
        from ..ui.level_view import (
            BLOCK_MARKER_SPECS,
            make_block_marker_graphics_items,
            marker_color,
            marker_shape,
            marker_shape_spec,
        )
        if marker_key not in BLOCK_MARKER_SPECS:
            return
        shape_key, color_key, width = BLOCK_MARKER_SPECS[marker_key]
        shape, inset = marker_shape_spec(marker_shape(self._marker_shapes, shape_key))
        color = marker_color(self._marker_colors, color_key)
        marker = QImage(
            img_w * MARKER_RENDER_SCALE,
            img_h * MARKER_RENDER_SCALE,
            QImage.Format_ARGB32_Premultiplied,
        )
        marker.fill(QColor(0, 0, 0, 0))
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, img_w * MARKER_RENDER_SCALE, img_h * MARKER_RENDER_SCALE)
        for x, y in cells:
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                continue
            for item in make_block_marker_graphics_items(
                    (x, y),
                    shape,
                    color,
                    width,
                    inset,
                    self._marker_overlay_scale,
                    tile_size=c.TILE_WIDTH * MARKER_RENDER_SCALE,
                    output_scale=MARKER_RENDER_SCALE * self._saved_marker_output_scale()):
                item.setZValue(900)
                scene.addItem(item)
        mp = QPainter(marker)
        try:
            mp.setRenderHint(QPainter.Antialiasing, True)
            scene.render(mp)
        finally:
            mp.end()
        smoothed = marker.scaled(
            img_w,
            img_h,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawImage(0, 0, smoothed)

    def set_wall_color_values(self, values):
        if values is None:
            self.wall_color_values = None
            return
        self.wall_color_values = tuple((int(v) & 0x3F) for v in values)

    def get_wall_color(self, level_no: int):
        if self.wall_color_values is None:
            return None
        idx = level_no // 4
        if 0 <= idx < len(self.wall_color_values):
            return self.wall_color_values[idx]
        return None

    def set_stage50_solomon_book_color(self, value: int):
        self.stage50_solomon_book_color = int(value) & 0x3F

    def get_metadata_animation(self, byte_no: int) -> int:
        """メタデータ番号 → tile_definitions の no"""
        return self.config.metadata_map.get(byte_no, 0)

    def get_item_animation(self, item_no: int) -> int:
        return self.config.item_map.get(item_no & 0x3f, 0)

    def get_enemy_animation(self, enemy_no: int) -> int:
        visual_enemy_no = ENEMY_VISUAL_SOURCE.get(enemy_no, enemy_no)
        return self.config.enemy_map.get(visual_enemy_no, 0)

    def get_actual_tileset_no(self, level_no: int, level_tileset_no: int) -> int:
        """level_palettes と level.tileset_no から実際のtilesetインデックスを計算

        skchain SKC_Config::get_level_tileset と同等
        """
        if 0 <= level_no < len(c.LEVEL_PALETTES):
            return c.LEVEL_PALETTES[level_no] * 3 + level_tileset_no
        return level_tileset_no

    @staticmethod
    def _is_stage50_solomon_book(level: Level, level_no: int) -> bool:
        return level_no == 49 and not level.is_door_removed() and level.is_key_removed()

    def object_labels(self, level: Level, level_no: int = 0,
                      bonus_items: list = None) -> list:
        """キャンバス注釈用の (x, y, text) を返す。

        文字は LevelView 側で描く。QImage に焼き込むとビュー拡大で
        文字まで荒れるため、ここでは内容だけを組み立てる。
        """
        labels = []

        def short(text, limit=14):
            text = str(text or "").strip()
            if not text:
                return ""
            text = text.split(" (", 1)[0].split("（", 1)[0]
            return text if len(text) <= limit else text[:limit - 1] + "…"

        def add(pos, text):
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H and text:
                labels.append((x, y, text))

        if level.has_constellation():
            name, _ = c.CONSTELLATION_NAMES.get(
                level.get_constellation_no(),
                (f"0x{level.get_constellation_no():02X}", 0))
            add(level.get_constellation_pos(), f"星座:{name}")

        if not level.is_door_removed():
            add(level.fixed_door_pos, "赤い本" if self._is_stage50_solomon_book(level, level_no) else "扉")
        if not level.is_key_removed():
            key_label = "鍵"
            if level.is_key_hidden():
                key_label += "[隠]"
            elif level.is_key_in_block():
                key_label += "[ブ]"
            elif level.is_key_white_in_block():
                key_label += "[白ブ]"
            add(level.fixed_key_pos, key_label)

        for i, mirror in enumerate(level.demon_mirrors, start=1):
            add(mirror.position, f"ミラー{i}")

        for item in level.items:
            base = item.get_item_no()
            flag = item.element_no & 0xC0
            special_item = item.position in getattr(level, "special_item_cells", set())
            display_base = base
            if special_item:
                from ..core import fire2_item_runtime as _special_items
                for pseudo, actual in _special_items.SPECIAL_ITEM_UI_TO_BASE.items():
                    if base == actual:
                        display_base = pseudo
                        break
            name = short(getattr(self.config, "item_desc", {}).get(
                display_base, f"item {display_base:02X}"))
            prefix = ""
            if special_item:
                prefix = "SP:"
            if item.position in getattr(level, "visible_in_block_item_cells", set()):
                prefix = "見:"
            elif flag == 0x40:
                prefix = "隠:"
            elif flag in (0x80, 0xC0):
                prefix = "ブ:"
            add(item.position, prefix + name)

        if bonus_items:
            for pos, item_no in bonus_items:
                name = short(getattr(self.config, "item_desc", {}).get(
                    item_no & 0x3F, f"bonus {item_no:02X}"))
                add(pos, "B:" + name)

        for i, enemy in enumerate(level.enemies, start=1):
            name = short(getattr(self.config, "enemy_desc", {}).get(
                enemy.element_no, f"enemy {enemy.element_no:02X}"))
            add(enemy.position, f"#{i}:{name}")

        for mi in getattr(self.config, "level_meta_items", []):
            if mi.level_no != level_no:
                continue
            name = short(getattr(mi, "description", "") or f"meta {mi.no:02X}")
            add(mi.position, name)

        sx, sy = level.fixed_start_pos
        if 0 <= sx < c.LEVEL_W and 0 <= sy < c.LEVEL_H:
            add(level.fixed_start_pos, "START")

        return labels

    def render(self, level: Level, level_no: int = 0,
               show_grid: bool = False,
               show_hidden_overlay: bool = True,
               hover_tile: tuple = None,
               show_col15: bool = True,
               selection_rect: tuple = None,
               special_marks: dict = None,
               show_border: bool = False,
               bonus_items: list = None,
               show_secret_elements: bool = True,
               draw_editor_markers: bool = True,
               show_enemy_variant_overlays: bool = True) -> QImage:
        """show_col15=False のとき、左に1列分の黒パディングを追加して
        左右対称な見た目にする (ホバー/クリック座標は LevelView 側で自動補正)

        selection_rect: ((x1,y1),(x2,y2)) 矩形範囲（Shift+ドラッグ選択）"""
        """レベル1個分をQImageに描画（256x192 ピクセル）

        Args:
            level: レンダリング対象のLevel
            level_no: レベル番号（0-52）
            show_grid: グリッド線を引くか
            show_hidden_overlay: 隠しアイテムを黄色枠で示すか
        """
        tw = c.TILE_WIDTH  # 16ピクセル
        img_w = c.LEVEL_W * tw
        img_h = c.LEVEL_H * tw
        img = QImage(img_w, img_h, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0))

        ts_no = self.get_actual_tileset_no(level_no, level.tileset_no)
        wall_color = self.get_wall_color(level_no)

        painter = QPainter(img)
        try:
            # 1. 空背景タイル（敷き詰め）
            empty_tile_no = self.get_metadata_animation(MD_EMPTY)
            empty_img = self.tr.get_tile_image(
                empty_tile_no, ts_no, transparent=False, bg_main_color=wall_color)
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    painter.drawImage(x * tw, y * tw, empty_img)

            # 2. 星座背景（あれば）
            if level.has_constellation():
                cn = level.get_constellation_no()
                cpos = level.get_constellation_pos()
                # 星座は 0xf0-0xfb の値を直接 metadata_map で引く（tile 53-56 の3x2メタタイル）
                const_anim = self.get_metadata_animation(cn)
                const_img = self.tr.get_tile_image(
                    const_anim, ts_no, transparent=False, bg_main_color=wall_color)
                if 0 <= cpos[0] < c.LEVEL_W and 0 <= cpos[1] < c.LEVEL_H:
                    painter.drawImage(cpos[0] * tw, cpos[1] * tw, const_img)

            # 3. ブロック描画
            brown_img = self.tr.get_tile_image(
                self.get_metadata_animation(MD_BLOCK_BROWN), ts_no,
                transparent=False, bg_main_color=wall_color)
            white_img = self.tr.get_tile_image(
                self.get_metadata_animation(MD_BLOCK_WHITE), ts_no,
                transparent=False, bg_main_color=wall_color)
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    w = level.tiles[y][x]
                    if w == Wall.BROWN:
                        painter.drawImage(x * tw, y * tw, brown_img)
                    elif w == Wall.WHITE or w == Wall.BROWN_WHITE:
                        # 注: BROWN_WHITE は実機で「壊せない白壁」と同じ挙動の冗長表現。
                        # v0.1.99以降は読込時に WHITE に正規化されるため通常ここには来ない。
                        # 既存データ互換のため一応 WHITE と同等に描画。
                        painter.drawImage(x * tw, y * tw, white_img)

            cracked_cells = {
                pos for pos in getattr(level, "cracked_block_cells", set())
                if 0 <= pos[0] < c.LEVEL_W
                and 0 <= pos[1] < c.LEVEL_H
                and level.tiles[pos[1]][pos[0]] == Wall.BROWN
            }
            cracked_img = None
            if cracked_cells:
                cracked_anim = self.get_item_animation(0x01)
                cracked_img = self.tr.get_tile_image(
                    cracked_anim, ts_no, transparent=None, bg_main_color=wall_color)
                for x, y in cracked_cells:
                    if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                        painter.drawImage(x * tw, y * tw, cracked_img)

            # Editor-only marker: white-looking blocks that become normal breakable stone.
            bw_cells = getattr(level, "breakable_white_cells", set())
            if draw_editor_markers and show_secret_elements and bw_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "breakable_white", bw_cells)

            ib_cells = getattr(level, "invisible_breakable_cells", set())
            if draw_editor_markers and show_secret_elements and ib_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "invisible_breakable", ib_cells)

            pw_cells = getattr(level, "passable_white_cells", set())
            if draw_editor_markers and show_secret_elements and pw_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "passable_white", pw_cells)

            pb_cells = getattr(level, "passable_brown_cells", set())
            if draw_editor_markers and show_secret_elements and pb_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "passable_brown", pb_cells)

            sb_cells = getattr(level, "solid_brown_cells", set())
            if draw_editor_markers and show_secret_elements and sb_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "solid_brown", sb_cells)

            is_cells = getattr(level, "invisible_solid_cells", set())
            if draw_editor_markers and show_secret_elements and is_cells:
                self._draw_block_marker_cells(painter, img_w, img_h, "invisible_solid", is_cells)

            # 4. Demon mirrors are functional even when another meta object
            # shares the cell. Draw them before door/key so the editor matches
            # the in-game priority: key > door > mirror.
            item_positions = {item.position for item in level.items}
            for mi, mirror in enumerate(level.demon_mirrors):
                mx, my = mirror.position
                if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                    continue
                if level.tiles[my][mx] != Wall.NONE or (mx, my) in item_positions:
                    continue
                anim = self.get_metadata_animation(MD_SPAWN01 if mi == 0 else MD_SPAWN02)
                m_img = self.tr.get_tile_image(
                    anim, ts_no, transparent=None, bg_main_color=wall_color)
                painter.drawImage(mx * tw, my * tw, m_img)
                if draw_editor_markers and show_secret_elements:
                    def draw_mirror_border(mp, mx=mx, my=my, mi=mi):
                        mp.setPen(self._marker_pen(
                            "mirror1_marker_color" if mi == 0 else "mirror2_marker_color",
                            2,
                        ))
                        mp.setBrush(Qt.NoBrush)
                        mp.drawRect(mx * tw, my * tw, tw - 1, tw - 1)
                    self._draw_marker_layer(painter, img_w, img_h, draw_mirror_border)

            # 5. ドア（tile_defの transparent 属性を尊重 - Noneで自動判定）
            if not level.is_door_removed():
                rf = getattr(level, "room_flags", 0)
                door_state = rf & room_flags.DOOR_STATE_MASK
                door_is_hidden = door_state == room_flags.DOOR_STATE_HIDDEN
                door_is_in_block = door_state in (
                    room_flags.DOOR_STATE_IN_BLOCK,
                    room_flags.DOOR_STATE_WHITE_IN_BLOCK,
                )
                is_stage50_solomon_book = self._is_stage50_solomon_book(level, level_no)
                door_anim = self.get_metadata_animation(
                    MD_SOLOMONS_KEY if is_stage50_solomon_book else MD_DOOR
                )
                door_ts_no = (
                    c.LEVEL_PALETTES[level_no] * 3
                    if is_stage50_solomon_book
                    else ts_no
                )
                door_img = self.tr.get_tile_image(
                    door_anim,
                    door_ts_no,
                    transparent=None,
                    bg_main_color=None if is_stage50_solomon_book else wall_color,
                    palette_no_override=2 if is_stage50_solomon_book else None,
                    pixel_color_overrides=(
                        {2: self.stage50_solomon_book_color}
                        if is_stage50_solomon_book else None
                    ),
                )
                dx, dy = level.fixed_door_pos
                if 0 <= dx < c.LEVEL_W and 0 <= dy < c.LEVEL_H:
                    if is_stage50_solomon_book:
                        painter.drawImage(dx * tw, dy * tw, door_img)
                    elif door_is_in_block:
                        block_img = (
                            white_img
                            if door_state == room_flags.DOOR_STATE_WHITE_IN_BLOCK
                            else brown_img
                        )
                        painter.drawImage(dx * tw, dy * tw, block_img)
                        if show_secret_elements:
                            painter.drawImage(dx * tw, dy * tw, door_img)
                            painter.setOpacity(0.5)
                            painter.drawImage(dx * tw, dy * tw, block_img)
                            painter.setOpacity(1.0)
                    elif show_secret_elements or not door_is_hidden:
                        if door_is_hidden and show_secret_elements:
                            painter.setOpacity(0.5)
                        painter.drawImage(dx * tw, dy * tw, door_img)
                        if door_is_hidden and show_secret_elements:
                            painter.setOpacity(1.0)

            # 6. 鍵
            if not level.is_key_removed():
                key_anim = self.get_metadata_animation(MD_KEY)
                key_img = self.tr.get_tile_image(
                    key_anim, ts_no, transparent=None, bg_main_color=wall_color)
                kx, ky = level.fixed_key_pos
                if 0 <= kx < c.LEVEL_W and 0 <= ky < c.LEVEL_H:
                    key_is_cracked = (
                        level.is_key_hidden()
                        and level.fixed_key_pos in cracked_cells
                        and cracked_img is not None
                    )
                    if key_is_cracked:
                        painter.drawImage(kx * tw, ky * tw, cracked_img)
                        if show_secret_elements:
                            painter.drawImage(kx * tw, ky * tw, key_img)
                            painter.setOpacity(0.5)
                            painter.drawImage(kx * tw, ky * tw, cracked_img)
                            painter.setOpacity(1.0)
                    elif level.is_key_in_block() or level.is_key_white_in_block():
                        # ブロック内: アイテム → 半透明ブロックの順
                        block_img = white_img if level.is_key_white_in_block() else brown_img
                        painter.drawImage(kx * tw, ky * tw, block_img)
                        if show_secret_elements:
                            painter.drawImage(kx * tw, ky * tw, key_img)
                            painter.setOpacity(0.5)
                            painter.drawImage(kx * tw, ky * tw, block_img)
                            painter.setOpacity(1.0)
                    elif level.is_key_hidden():
                        # 隠し: 半透明アイテム
                        if show_secret_elements:
                            painter.setOpacity(0.5)
                            painter.drawImage(kx * tw, ky * tw, key_img)
                            painter.setOpacity(1.0)
                    else:
                        painter.drawImage(kx * tw, ky * tw, key_img)

            # 7. アイテム
            for item in level.items:
                ix, iy = item.position
                if not (0 <= ix < c.LEVEL_W and 0 <= iy < c.LEVEL_H):
                    continue
                item_no = item.get_item_no()
                if item.position in getattr(level, "special_item_cells", set()):
                    from ..core import fire2_item_runtime as _special_items
                    for pseudo, actual in _special_items.SPECIAL_ITEM_UI_TO_BASE.items():
                        if item_no == actual:
                            item_no = pseudo
                            break
                anim = self.get_item_animation(item_no)
                item_img = self.tr.get_tile_image(
                    anim, ts_no, transparent=None, bg_main_color=wall_color)

                if item.position in cracked_cells and cracked_img is not None:
                    painter.drawImage(ix * tw, iy * tw, cracked_img)
                    if show_secret_elements:
                        painter.drawImage(ix * tw, iy * tw, item_img)
                        painter.setOpacity(0.5)
                        painter.drawImage(ix * tw, iy * tw, cracked_img)
                        painter.setOpacity(1.0)
                elif item.is_in_block():
                    # ブロック内: アイテムを下に描画 → 半透明ブロックを上に重ねて
                    # 「ブロック越しにアイテムが透けて見える」表現
                    block_img = white_img if item.is_white_in_block() else brown_img
                    painter.drawImage(ix * tw, iy * tw, block_img)
                    if show_secret_elements:
                        painter.drawImage(ix * tw, iy * tw, item_img)
                        painter.setOpacity(0.5)
                        painter.drawImage(ix * tw, iy * tw, block_img)
                        painter.setOpacity(1.0)
                elif item.is_hidden():
                    # 隠し（ブロック無し）: アイテムを半透明で描画
                    if show_secret_elements:
                        painter.setOpacity(0.4)
                        painter.drawImage(ix * tw, iy * tw, item_img)
                        painter.setOpacity(1.0)
                else:
                    painter.drawImage(ix * tw, iy * tw, item_img)

                if (draw_editor_markers and show_hidden_overlay and
                        item.position in getattr(level, "visible_in_block_item_cells", set())):
                    def draw_visible_item_overlay(mp, ix=ix, iy=iy):
                        mp.setPen(self._marker_pen("visible_in_block_marker_color", 3))
                        mp.drawRect(ix * tw, iy * tw, tw - 1, tw - 1)
                    self._draw_marker_layer(painter, img_w, img_h, draw_visible_item_overlay)
                elif draw_editor_markers and show_hidden_overlay and (item.is_hidden() or item.is_in_block()):
                    def draw_item_overlay(mp, ix=ix, iy=iy):
                        mp.setPen(self._marker_pen("hidden_marker_color", 2))
                        mp.drawRect(ix * tw + 1, iy * tw + 1, tw - 2, tw - 2)
                    self._draw_marker_layer(painter, img_w, img_h, draw_item_overlay)

            # 7.5 ボーナスステージ出現スポット（ステージ51専用、位置マーカーのみ）
            if draw_editor_markers and show_secret_elements and bonus_items:
                from PyQt5.QtCore import QPoint
                for bpos, _bitem_no in bonus_items:
                    bx, by = bpos
                    if not (0 <= bx < c.LEVEL_W and 0 <= by < c.LEVEL_H):
                        continue
                    cx = bx * tw + tw // 2
                    cy = by * tw + tw // 2
                    r = tw // 2 - 2
                    diamond = QPolygon([
                        QPoint(cx, cy - r),
                        QPoint(cx + r, cy),
                        QPoint(cx, cy + r),
                        QPoint(cx - r, cy),
                    ])
                    def draw_bonus_marker(mp, diamond=diamond):
                        mp.setPen(self._marker_pen("bonus_marker_color", 3))
                        mp.setBrush(Qt.NoBrush)
                        mp.drawPolygon(diamond)
                        mp.setBrush(Qt.NoBrush)
                    self._draw_marker_layer(painter, img_w, img_h, draw_bonus_marker)

            # 8. 敵
            key_enemy_number = stage_ext.get_key_enemy_number(level)
            fairy_enemy_number = stage_ext.get_fairy_enemy_number(level)
            key_enemy_img = None
            if show_secret_elements and key_enemy_number > 0:
                key_enemy_img = self._key_enemy_overlay_image(tw)
            fairy_enemy_img = None
            if show_secret_elements and fairy_enemy_number > 0:
                try:
                    fairy_enemy_img = self.tr.get_tile_image(
                        self.get_enemy_animation(0x1C), ts_no, transparent=True, bg_main_color=wall_color)
                except Exception:
                    fairy_enemy_img = None
            for enemy_index, enemy in enumerate(level.enemies, start=1):
                ex, ey = enemy.position
                if not (0 <= ex < c.LEVEL_W and 0 <= ey < c.LEVEL_H):
                    continue
                anim = self.get_enemy_animation(enemy.element_no)
                en_img = self.tr.get_tile_image(
                    anim, ts_no, transparent=True, bg_main_color=wall_color,
                    palette_no_override=ENEMY_PALETTE_OVERRIDE.get(enemy.element_no))
                if show_enemy_variant_overlays:
                    en_img = apply_enemy_picker_overlay(en_img, enemy.element_no)
                is_key_enemy = key_enemy_img is not None and enemy_index == key_enemy_number
                is_fairy_enemy = fairy_enemy_img is not None and enemy_index == fairy_enemy_number
                if is_key_enemy or is_fairy_enemy:
                    en_img = self._darkened_sprite_image(en_img)
                painter.drawImage(ex * tw, ey * tw, en_img)
                if is_key_enemy:
                    painter.drawImage(ex * tw, ey * tw, key_enemy_img)
                if is_fairy_enemy:
                    painter.setOpacity(0.72)
                    painter.drawImage(ex * tw, ey * tw, fairy_enemy_img)
                    painter.setOpacity(1.0)
            # 8.5 level_meta_items（ソロモンの紋章/六芒星、ボムジャック、テクモバニー、Page of Time/Space）
            #   - transparent="true" のものは隠し扱い
            #   - その位置にブロックがあれば in_block 表現（アイテム → 半透明ブロック）
            #   - ブロックなし & 隠しなら半透明アイテム
            for mi in getattr(self.config, "level_meta_items", []):
                if mi.level_no != level_no:
                    continue
                mx, my = mi.position
                if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                    continue
                meta_img = self.tr.get_tile_image(
                    mi.animation, ts_no, transparent=None, bg_main_color=wall_color)

                wall_at = level.tiles[my][mx]
                in_breakable_white = (
                    wall_at == Wall.WHITE
                    and (mx, my) in getattr(level, "breakable_white_cells", set())
                )
                in_invisible_breakable = (
                    wall_at == Wall.NONE
                    and (mx, my) in getattr(level, "invisible_breakable_cells", set())
                )
                block_img = None
                if wall_at == Wall.BROWN:
                    block_img = brown_img
                elif in_breakable_white:
                    block_img = white_img
                in_block = block_img is not None or in_invisible_breakable

                if block_img is not None:
                    painter.drawImage(mx * tw, my * tw, block_img)
                    if show_secret_elements:
                        painter.drawImage(mx * tw, my * tw, meta_img)
                        painter.setOpacity(0.5)
                        painter.drawImage(mx * tw, my * tw, block_img)
                        painter.setOpacity(1.0)
                elif in_invisible_breakable:
                    painter.drawImage(mx * tw, my * tw, meta_img)
                elif mi.transparent:
                    if show_secret_elements:
                        painter.setOpacity(0.4)
                        painter.drawImage(mx * tw, my * tw, meta_img)
                        painter.setOpacity(1.0)
                else:
                    painter.drawImage(mx * tw, my * tw, meta_img)

                if draw_editor_markers and show_hidden_overlay and in_invisible_breakable:
                    def draw_meta_visible_in_block_overlay(mp, mx=mx, my=my):
                        mp.setPen(self._marker_pen("visible_in_block_marker_color", 3))
                        mp.drawRect(mx * tw, my * tw, tw - 1, tw - 1)
                    self._draw_marker_layer(painter, img_w, img_h, draw_meta_visible_in_block_overlay)
                elif draw_editor_markers and show_hidden_overlay and (in_block or mi.transparent):
                    def draw_meta_overlay(mp, mx=mx, my=my):
                        mp.setPen(self._marker_pen("hidden_marker_color", 2))
                        mp.drawRect(mx * tw + 1, my * tw + 1, tw - 2, tw - 2)
                    self._draw_marker_layer(painter, img_w, img_h, draw_meta_overlay)

            # 9. プレイヤースタート
            sx, sy = level.fixed_start_pos
            if 0 <= sx < c.LEVEL_W and 0 <= sy < c.LEVEL_H:
                start_md = MD_PLAYER_START_LEFT if sx >= c.LEVEL_W // 2 else MD_PLAYER_START
                start_anim = self.get_metadata_animation(start_md)
                start_img = self.tr.get_tile_image(
                    start_anim, ts_no, transparent=None, bg_main_color=wall_color)
                painter.drawImage(sx * tw, sy * tw, start_img)

            # 9.4 16列目（右端列）を黒で塗りつぶす（標準は非表示）
            if not show_col15:
                painter.fillRect(15 * tw, 0, tw, img_h, QColor(0, 0, 0))

            # 9.45 矩形範囲選択ハイライト（Shift+ドラッグ）
            if draw_editor_markers and selection_rect is not None and selection_rect[0] and selection_rect[1]:
                (sx, sy), (ex, ey) = selection_rect
                x1, y1 = min(sx, ex), min(sy, ey)
                x2, y2 = max(sx, ex), max(sy, ey)
                # クリップ
                x1 = max(0, min(c.LEVEL_W - 1, x1))
                x2 = max(0, min(c.LEVEL_W - 1, x2))
                y1 = max(0, min(c.LEVEL_H - 1, y1))
                y2 = max(0, min(c.LEVEL_H - 1, y2))
                rx, ry = x1 * tw, y1 * tw
                rw, rh = (x2 - x1 + 1) * tw, (y2 - y1 + 1) * tw
                def draw_selection_marker(mp):
                    # 半透明の黄色で塗りつぶし
                    fill_color = self._marker_color("selection_marker_color")
                    fill_color.setAlpha(60)
                    mp.fillRect(rx, ry, rw, rh, fill_color)
                    # 黄色の枠線
                    mp.setPen(self._marker_pen("selection_marker_color", 2, Qt.DashLine))
                    mp.drawRect(rx, ry, rw - 1, rh - 1)
                self._draw_marker_layer(painter, img_w, img_h, draw_selection_marker)

            # 9.5 ホバーハイライト（マウス位置のタイル枠）
            if draw_editor_markers and hover_tile is not None:
                hx, hy = hover_tile
                if 0 <= hx < c.LEVEL_W and 0 <= hy < c.LEVEL_H:
                    def draw_hover_marker(mp):
                        mp.setPen(self._marker_pen("hover_marker_color", 2, alpha=220))
                        mp.drawRect(hx * tw, hy * tw, tw - 1, tw - 1)
                    self._draw_marker_layer(painter, img_w, img_h, draw_hover_marker)

            # 10. グリッド線
            if show_grid:
                pen = QPen(QColor(255, 255, 255, 60))
                pen.setWidth(1)
                painter.setPen(pen)
                for x in range(1, c.LEVEL_W):
                    painter.drawLine(x * tw, 0, x * tw, img_h)
                for y in range(1, c.LEVEL_H):
                    painter.drawLine(0, y * tw, img_w, y * tw)

            # 11. 特殊処理マーカー (Per-Room Special Process で動的配置されるマス)
            if draw_editor_markers and show_secret_elements and special_marks:
                mark_colors = {
                    "breakable":             self._marker_color("breakable_white_marker_color"),
                    "breakable_conditional": self._marker_color("breakable_white_marker_color"),
                    "empty_forced":          self._marker_color("special_empty_marker_color"),
                    "trigger":               self._marker_color("special_trigger_marker_color"),
                    "bomb_jack_trigger":      self._marker_color("special_trigger_marker_color"),
                    "hidden_bomb_jack":      self._marker_color("hidden_marker_color"),
                }

                # マイティボンジャック隠し:
                # 白壁の「奥」にMBJが隠れている表現にする
                # 順序: 既存白壁(レベルデータ通り) → MBJ を半透明で重ねる
                # こうすれば「白壁の中にうっすらMBJが透けて見える」
                bj_marks = [k for k, v in special_marks.items()
                            if k != "__links__" and v == "hidden_bomb_jack"]
                if bj_marks:
                    try:
                        bj_anim = self.get_enemy_animation(0x18)
                        bj_img = self.tr.get_tile_image(
                            bj_anim, ts_no, transparent=True, bg_main_color=wall_color)
                    except Exception:
                        bj_img = None
                    for (mx, my) in bj_marks:
                        if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                            continue
                        # その位置が白壁でない場合は MBJ を見せるため白壁を下に描く
                        w = level.tiles[my][mx]
                        if w != Wall.WHITE and w != Wall.BROWN_WHITE:
                            painter.drawImage(mx * tw, my * tw, white_img)
                        # MBJ を半透明で重ねる (隠しアイテム表現)
                        if bj_img is not None:
                            painter.setOpacity(0.55)
                            painter.drawImage(mx * tw, my * tw, bj_img)
                            painter.setOpacity(1.0)

                def draw_special_marker_frames(mp):
                    for key, kind in special_marks.items():
                        if key == "__links__":
                            continue
                        mx, my = key
                        if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                            continue
                        color = mark_colors.get(kind, QColor(255, 0, 255))
                        pen = QPen(color)
                        from ..ui.level_view import marker_pen_width
                        pen.setWidth(marker_pen_width(
                            3,
                            self._marker_overlay_scale,
                            self._saved_marker_output_scale(),
                        ))
                        pen.setStyle(Qt.DashLine if kind == "breakable_conditional" else Qt.SolidLine)
                        mp.setPen(pen)
                        mp.drawRect(mx * tw + 1, my * tw + 1, tw - 3, tw - 3)
                self._draw_marker_layer(painter, img_w, img_h, draw_special_marker_frames)

                # トリガー→ターゲット間に矢印 (細い線) を引く
                links = special_marks.get("__links__", [])
                if links:
                    def draw_special_links(mp):
                        mp.setPen(self._marker_pen("special_link_marker_color", 1, Qt.DashLine, alpha=180))
                        for (tx, ty), (gx, gy) in links:
                            cx1 = tx * tw + tw // 2
                            cy1 = ty * tw + tw // 2
                            cx2 = gx * tw + tw // 2
                            cy2 = gy * tw + tw // 2
                            mp.drawLine(cx1, cy1, cx2, cy2)
                    self._draw_marker_layer(painter, img_w, img_h, draw_special_links)

        finally:
            painter.end()

        # 装飾ボーダー（下・左に壊せない白ブロックを配置）
        if show_border:
            border_w = (c.LEVEL_W + 1) * tw
            border_h = (c.LEVEL_H + 1) * tw
            bordered = QImage(border_w, border_h, QImage.Format_ARGB32)
            bordered.fill(QColor(0, 0, 0))
            p2 = QPainter(bordered)
            try:
                p2.drawImage(tw, 0, img)
                for x in range(c.LEVEL_W + 1):
                    p2.drawImage(x * tw, c.LEVEL_H * tw, white_img)
                for y in range(c.LEVEL_H):
                    p2.drawImage(0, y * tw, white_img)
            finally:
                p2.end()
            img = bordered

        # show_col15=False なら左に1列分の黒パディングを追加して対称化
        if not show_col15:
            padded = QImage(img_w + tw, img_h, QImage.Format_ARGB32)
            padded.fill(QColor(0, 0, 0))
            p2 = QPainter(padded)
            try:
                p2.drawImage(tw, 0, img)
            finally:
                p2.end()
            return padded

        return img
