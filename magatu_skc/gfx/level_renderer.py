"""レベル全体の描画 - QImageでレベル1個分をレンダリング"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QBrush, QPolygon

from ..core import constants as c
from ..core import room_flags
from ..core.element import Wall, ElementType
from ..core.level import Level
from .tile_renderer import TileRenderer


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
    0x41: 0x24, 0x43: 0x25, 0x45: 0x26, 0x47: 0x27,
    0x49: 0x24, 0x4B: 0x25, 0x4D: 0x26, 0x4F: 0x27,
    0x31: 0x24, 0x33: 0x25, 0x35: 0x26, 0x37: 0x27,
}

MARKER_RENDER_SCALE = 4


class LevelRenderer:

    def __init__(self, tile_renderer: TileRenderer, config):
        self.tr = tile_renderer
        self.config = config

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
        self.wall_color_values = None

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

    def get_metadata_animation(self, byte_no: int) -> int:
        """メタデータ番号 → tile_definitions の no"""
        return self.config.metadata_map.get(byte_no, 0)

    def get_item_animation(self, item_no: int) -> int:
        return self.config.item_map.get(item_no & 0x3f, 0)

    def get_enemy_animation(self, enemy_no: int) -> int:
        visual_enemy_no = PANEL_VARIANT_VISUAL_SOURCE.get(enemy_no, enemy_no)
        return self.config.enemy_map.get(visual_enemy_no, 0)

    def get_actual_tileset_no(self, level_no: int, level_tileset_no: int) -> int:
        """level_palettes と level.tileset_no から実際のtilesetインデックスを計算

        skchain SKC_Config::get_level_tileset と同等
        """
        if 0 <= level_no < len(c.LEVEL_PALETTES):
            return c.LEVEL_PALETTES[level_no] * 3 + level_tileset_no
        return level_tileset_no

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
            add(level.fixed_door_pos, "扉")
        if not level.is_key_removed():
            key_label = "鍵"
            if level.is_key_hidden():
                key_label += "[隠]"
            elif level.is_key_in_block():
                key_label += "[ブ]"
            add(level.fixed_key_pos, key_label)

        for i, mirror in enumerate(level.demon_mirrors, start=1):
            add(mirror.position, f"ミラー{i}")

        for item in level.items:
            base = item.element_no & 0x3F
            flag = item.element_no & 0xC0
            name = short(getattr(self.config, "item_desc", {}).get(
                base, f"item {base:02X}"))
            prefix = ""
            if flag == 0x40:
                prefix = "隠:"
            elif flag == 0x80:
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
               draw_editor_markers: bool = True) -> QImage:
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

            # Editor-only marker: white-looking blocks that become normal breakable stone.
            bw_cells = getattr(level, "breakable_white_cells", set())
            if draw_editor_markers and show_secret_elements and bw_cells:
                def draw_bw_marks(mp):
                    pen = QPen(QColor(80, 230, 90, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in bw_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawRect(x * tw + 1, y * tw + 1, tw - 3, tw - 3)
                self._draw_marker_layer(painter, img_w, img_h, draw_bw_marks)

            ib_cells = getattr(level, "invisible_breakable_cells", set())
            if draw_editor_markers and show_secret_elements and ib_cells:
                def draw_ib_marks(mp):
                    pen = QPen(QColor(255, 220, 40, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in ib_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawRect(x * tw + 4, y * tw + 4, tw - 9, tw - 9)
                self._draw_marker_layer(painter, img_w, img_h, draw_ib_marks)

            pw_cells = getattr(level, "passable_white_cells", set())
            if draw_editor_markers and show_secret_elements and pw_cells:
                def draw_pw_marks(mp):
                    pen = QPen(QColor(80, 190, 255, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in pw_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawLine(x * tw + 3, y * tw + 3, x * tw + tw - 4, y * tw + tw - 4)
                            mp.drawLine(x * tw + tw - 4, y * tw + 3, x * tw + 3, y * tw + tw - 4)
                self._draw_marker_layer(painter, img_w, img_h, draw_pw_marks)

            pb_cells = getattr(level, "passable_brown_cells", set())
            if draw_editor_markers and show_secret_elements and pb_cells:
                def draw_pb_marks(mp):
                    pen = QPen(QColor(80, 190, 255, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in pb_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawLine(x * tw + 3, y * tw + 3, x * tw + tw - 4, y * tw + tw - 4)
                            mp.drawLine(x * tw + tw - 4, y * tw + 3, x * tw + 3, y * tw + tw - 4)
                self._draw_marker_layer(painter, img_w, img_h, draw_pb_marks)

            sb_cells = getattr(level, "solid_brown_cells", set())
            if draw_editor_markers and show_secret_elements and sb_cells:
                def draw_sb_marks(mp):
                    pen = QPen(QColor(255, 120, 220, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in sb_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawEllipse(x * tw + 4, y * tw + 4, tw - 9, tw - 9)
                self._draw_marker_layer(painter, img_w, img_h, draw_sb_marks)

            is_cells = getattr(level, "invisible_solid_cells", set())
            if draw_editor_markers and show_secret_elements and is_cells:
                def draw_is_marks(mp):
                    pen = QPen(QColor(255, 120, 220, 255))
                    pen.setWidth(3)
                    mp.setPen(pen)
                    mp.setBrush(Qt.NoBrush)
                    for x, y in is_cells:
                        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                            mp.drawEllipse(x * tw + 4, y * tw + 4, tw - 9, tw - 9)
                self._draw_marker_layer(painter, img_w, img_h, draw_is_marks)

            # 4. ドア（tile_defの transparent 属性を尊重 - Noneで自動判定）
            if not level.is_door_removed():
                door_is_hidden = bool(
                    getattr(level, "room_flags", 0) & room_flags.BIT_HIDDEN_DOOR
                )
                if show_secret_elements or not door_is_hidden:
                    door_anim = self.get_metadata_animation(MD_DOOR)
                    door_img = self.tr.get_tile_image(
                        door_anim, ts_no, transparent=None, bg_main_color=wall_color)
                    dx, dy = level.fixed_door_pos
                    if 0 <= dx < c.LEVEL_W and 0 <= dy < c.LEVEL_H:
                        painter.drawImage(dx * tw, dy * tw, door_img)

            # 5. 鍵
            if not level.is_key_removed():
                key_anim = self.get_metadata_animation(MD_KEY)
                key_img = self.tr.get_tile_image(
                    key_anim, ts_no, transparent=None, bg_main_color=wall_color)
                kx, ky = level.fixed_key_pos
                if 0 <= kx < c.LEVEL_W and 0 <= ky < c.LEVEL_H:
                    if level.is_key_in_block():
                        # ブロック内: アイテム → 半透明ブロックの順
                        painter.drawImage(kx * tw, ky * tw, brown_img)
                        if show_secret_elements:
                            painter.drawImage(kx * tw, ky * tw, key_img)
                            painter.setOpacity(0.5)
                            painter.drawImage(kx * tw, ky * tw, brown_img)
                            painter.setOpacity(1.0)
                    elif level.is_key_hidden():
                        # 隠し: 半透明アイテム
                        if show_secret_elements:
                            painter.setOpacity(0.5)
                            painter.drawImage(kx * tw, ky * tw, key_img)
                            painter.setOpacity(1.0)
                    else:
                        painter.drawImage(kx * tw, ky * tw, key_img)

            # 6. ミラー（色枠で識別: 1=赤, 2=青）
            # ブロックやアイテムで隠されたミラーは描画しない
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
                # ミラー識別: 1=赤枠, 2=青枠
                if draw_editor_markers and show_secret_elements:
                    def draw_mirror_border(mp, mx=mx, my=my, mi=mi):
                        border_color = QColor(255, 60, 60) if mi == 0 else QColor(60, 120, 255)
                        mp.setPen(QPen(border_color, 1))
                        mp.setBrush(Qt.NoBrush)
                        mp.drawRect(mx * tw, my * tw, tw - 1, tw - 1)
                    self._draw_marker_layer(painter, img_w, img_h, draw_mirror_border)

            # 7. アイテム
            for item in level.items:
                ix, iy = item.position
                if not (0 <= ix < c.LEVEL_W and 0 <= iy < c.LEVEL_H):
                    continue
                anim = self.get_item_animation(item.element_no)
                item_img = self.tr.get_tile_image(
                    anim, ts_no, transparent=None, bg_main_color=wall_color)

                if item.is_in_block():
                    # ブロック内: アイテムを下に描画 → 半透明ブロックを上に重ねて
                    # 「ブロック越しにアイテムが透けて見える」表現
                    painter.drawImage(ix * tw, iy * tw, brown_img)
                    if show_secret_elements:
                        painter.drawImage(ix * tw, iy * tw, item_img)
                        painter.setOpacity(0.5)
                        painter.drawImage(ix * tw, iy * tw, brown_img)
                        painter.setOpacity(1.0)
                elif item.is_hidden():
                    # 隠し（ブロック無し）: アイテムを半透明で描画
                    if show_secret_elements:
                        painter.setOpacity(0.4)
                        painter.drawImage(ix * tw, iy * tw, item_img)
                        painter.setOpacity(1.0)
                else:
                    painter.drawImage(ix * tw, iy * tw, item_img)

                if draw_editor_markers and show_hidden_overlay and (item.is_hidden() or item.is_in_block()):
                    def draw_item_overlay(mp, ix=ix, iy=iy):
                        pen = QPen(QColor(255, 220, 0))
                        pen.setWidth(2)
                        mp.setPen(pen)
                        mp.drawRect(ix * tw + 1, iy * tw + 1, tw - 2, tw - 2)
                    self._draw_marker_layer(painter, img_w, img_h, draw_item_overlay)

            # 7.5 ボーナスステージ出現スポット（ステージ51専用、位置マーカーのみ）
            if draw_editor_markers and bonus_items:
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
                        mp.setPen(QPen(QColor(255, 200, 0), 2))
                        mp.setBrush(QBrush(QColor(255, 200, 0, 80)))
                        mp.drawPolygon(diamond)
                        mp.setBrush(Qt.NoBrush)
                    self._draw_marker_layer(painter, img_w, img_h, draw_bonus_marker)

            # 8. 敵
            for enemy in level.enemies:
                ex, ey = enemy.position
                if not (0 <= ex < c.LEVEL_W and 0 <= ey < c.LEVEL_H):
                    continue
                anim = self.get_enemy_animation(enemy.element_no)
                en_img = self.tr.get_tile_image(
                    anim, ts_no, transparent=None, bg_main_color=wall_color)
                painter.drawImage(ex * tw, ey * tw, en_img)
                if enemy.element_no in PANEL_VARIANT_VISUAL_SOURCE:
                    painter.fillRect(
                        ex * tw, ey * tw, tw, tw,
                        QColor(55, 135, 255, 80)
                    )

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
                in_block = wall_at == Wall.BROWN

                if in_block:
                    painter.drawImage(mx * tw, my * tw, brown_img)
                    if show_secret_elements:
                        painter.drawImage(mx * tw, my * tw, meta_img)
                        painter.setOpacity(0.5)
                        painter.drawImage(mx * tw, my * tw, brown_img)
                        painter.setOpacity(1.0)
                elif mi.transparent:
                    if show_secret_elements:
                        painter.setOpacity(0.4)
                        painter.drawImage(mx * tw, my * tw, meta_img)
                        painter.setOpacity(1.0)
                else:
                    painter.drawImage(mx * tw, my * tw, meta_img)

                if draw_editor_markers and show_hidden_overlay and (in_block or mi.transparent):
                    def draw_meta_overlay(mp, mx=mx, my=my):
                        pen = QPen(QColor(255, 220, 0))
                        pen.setWidth(2)
                        mp.setPen(pen)
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
                    mp.fillRect(rx, ry, rw, rh, QColor(255, 230, 0, 60))
                    # 黄色の枠線
                    pen = QPen(QColor(255, 230, 0))
                    pen.setWidth(2)
                    pen.setStyle(Qt.DashLine)
                    mp.setPen(pen)
                    mp.drawRect(rx, ry, rw - 1, rh - 1)
                self._draw_marker_layer(painter, img_w, img_h, draw_selection_marker)

            # 9.5 ホバーハイライト（マウス位置のタイル枠）
            if draw_editor_markers and hover_tile is not None:
                hx, hy = hover_tile
                if 0 <= hx < c.LEVEL_W and 0 <= hy < c.LEVEL_H:
                    def draw_hover_marker(mp):
                        pen = QPen(QColor(255, 255, 255, 220))
                        pen.setWidth(2)
                        mp.setPen(pen)
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
                    "breakable":             QColor(80, 230, 90, 255),    # 緑実線: 即壊せる
                    "breakable_conditional": QColor(80, 230, 90, 255),    # 緑点線: 条件付き
                    "empty_forced":          QColor(180, 200, 255, 255),  # 水色: 強制空
                    "trigger":               QColor(255, 100, 200, 255),  # ピンク: トリガー
                    "hidden_bomb_jack":      QColor(255, 220, 0, 255),    # 黄: 隠しMBJ
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
                        pen.setWidth(3)
                        if kind == "breakable_conditional":
                            pen.setStyle(Qt.DashLine)
                        else:
                            pen.setStyle(Qt.SolidLine)
                        mp.setPen(pen)
                        mp.drawRect(mx * tw + 1, my * tw + 1, tw - 3, tw - 3)
                self._draw_marker_layer(painter, img_w, img_h, draw_special_marker_frames)

                # トリガー→ターゲット間に矢印 (細い線) を引く
                links = special_marks.get("__links__", [])
                if links:
                    def draw_special_links(mp):
                        pen = QPen(QColor(255, 200, 100, 180))
                        pen.setWidth(1)
                        pen.setStyle(Qt.DashLine)
                        mp.setPen(pen)
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
