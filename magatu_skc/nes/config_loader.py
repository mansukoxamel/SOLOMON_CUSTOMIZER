"""skc_config.xml ローダー - skchain設定ファイル互換"""
import xml.etree.ElementTree as ET
from pathlib import Path

from . import palette as pal


def parse_int(s: str) -> int:
    """0x で始まる場合は16進、それ以外は10進"""
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s)


class TileDef:
    """1つのメタタイル定義（NES 8x8 タイル4つで構成）"""
    def __init__(self, no: int, palette_no: int, nes_tile_strs: list,
                 width: int = 0, transparent: bool = False):
        self.no = no
        self.palette_no = palette_no
        self.transparent = transparent
        # nes_tile_strs は "300" or "300:v" 等の文字列リスト
        self.nes_tiles = []  # list of (tile_no, flip_v, flip_h)
        for s in nes_tile_strs:
            s = s.strip()
            flip_v = ":v" in s
            flip_h = ":h" in s
            num_str = s.replace(":v", "").replace(":h", "")
            self.nes_tiles.append((int(num_str), flip_v, flip_h))

        if width == 0:
            self.width = 2 if len(self.nes_tiles) == 4 else len(self.nes_tiles)
        else:
            self.width = width

    @property
    def height(self) -> int:
        return (len(self.nes_tiles) + self.width - 1) // self.width


class TilesetDef:
    """1つのタイルセット = (palette_offset, tile_offset)"""
    def __init__(self, palette_offset: int, tile_offset: int):
        self.palette_offset = palette_offset
        self.tile_offset = tile_offset


class MetaItemDef:
    """level_meta_item: ソロモンの紋章（六芒星）、ボムジャック、テクモバニー、Page of Time/Space 等

    Solomon's seal / JP Tecmo bunny / JP Page は1バイトのROMオフセット指定（位置エンコード byte）。
    offset 未特定のリージョンは静的位置 (position 属性)。
    """
    def __init__(self, no: int, level_no: int, animation: int,
                 transparent: bool, position: tuple, description: str,
                 rom_offset: int = -1):
        self.no = no
        self.level_no = level_no
        self.animation = animation
        self.transparent = transparent
        self.position = position  # (x, y)
        self.description = description
        self.rom_offset = rom_offset  # ROM内の位置バイトのオフセット (-1 = 静的配置、書き換え不可)


class SkcConfig:
    """skc_config.xml の主要情報を保持"""

    def __init__(self):
        self.palettes = []           # list[list[int]] (raw)
        self.tile_defs = {}          # no -> TileDef
        self.tilesets = []           # list[TilesetDef]
        self.metadata_map = {}       # byte (0-255) -> tile_no
        self.item_map = {}           # byte -> tile_no
        self.enemy_map = {}          # byte -> tile_no
        self.metadata_desc = {}      # byte -> description
        self.item_desc = {}          # byte -> description
        self.enemy_desc = {}         # byte -> description
        self.enemy_direction_bundles = []  # list[tuple[int, ...]]
        self.level_meta_items = []   # list[MetaItemDef] (region で絞り込み済み)
        # item_bitmasks: 16x12 bitmap で同種アイテムを一括配置する仕組み
        # (Level 20 の Bat Symbol、Level 30 の Opal 等)
        # 要素は dict: {"level_no": int(0-indexed), "item_no": int, "offset": int (ROM)}
        self.item_bitmasks = []

    @classmethod
    def load(cls, path: str, rom_data: bytes = None, region: str = "") -> "SkcConfig":
        cfg = cls()
        tree = ET.parse(path)
        root = tree.getroot()

        gfx_meta = root.find("gfx_metadata")
        if gfx_meta is None:
            raise ValueError("gfx_metadata not found")

        # palettes
        pal_node = gfx_meta.find("palettes")
        for pn in pal_node.findall("palette"):
            offset_attr = pn.attrib["offset"]
            parts = [s.strip() for s in offset_attr.split(",")]
            if len(parts) == 1:
                # ROM オフセット指定
                if rom_data is not None:
                    off = parse_int(parts[0])
                    cfg.palettes.append([rom_data[off + i] for i in range(4)])
                else:
                    cfg.palettes.append([0x0f, 0x0f, 0x0f, 0x0f])
            else:
                vals = [parse_int(s) for s in parts]
                cfg.palettes.append(vals)

        # tilesets
        ts_node = gfx_meta.find("tilesets")
        for tn in ts_node.findall("tileset"):
            cfg.tilesets.append(TilesetDef(
                palette_offset=parse_int(tn.attrib["palette_offset"]),
                tile_offset=parse_int(tn.attrib["tile_offset"]),
            ))

        # tile definitions
        td_node = gfx_meta.find("tile_definitions")
        for tn in td_node.findall("tile"):
            no = parse_int(tn.attrib["no"])
            palette_no = parse_int(tn.attrib.get("palette_no", "0"))
            nes_tiles = tn.attrib["nes_tiles"].replace("\n", "").replace("\r", "").split(",")
            nes_tiles = [s for s in nes_tiles if s.strip()]
            width = parse_int(tn.attrib.get("w", "0"))
            transp_attr = tn.attrib.get("transparent", "")
            transparent = transp_attr.lower() in ("true", "1")
            cfg.tile_defs[no] = TileDef(no, palette_no, nes_tiles, width, transparent)

        # element type definitions（メタデータ・アイテム・敵）
        for tag, target_map, desc_map in (
            ("metadata_definitions", cfg.metadata_map, cfg.metadata_desc),
            ("item_definitions", cfg.item_map, cfg.item_desc),
            ("enemy_definitions", cfg.enemy_map, cfg.enemy_desc),
        ):
            node = root.find(tag)
            if node is None:
                continue

            child_tag = tag.split("_")[0]  # "metadata", "item", "enemy"
            for elem in node.findall(child_tag):
                no = parse_int(elem.attrib["no"])
                anim = elem.attrib.get("animation", "0")
                first_anim = parse_int(anim.split(",")[0])
                target_map[no] = first_anim
                desc = elem.attrib.get("description", "")
                desc_map[no] = desc

        enemy_editor = root.find("enemy_editor")
        if enemy_editor is not None:
            directions_node = enemy_editor.find("enemy_directions")
            if directions_node is not None:
                for bundle in directions_node.findall("bundle"):
                    enemies = [
                        parse_int(part.strip())
                        for part in bundle.attrib.get("enemies", "").split(",")
                        if part.strip()
                    ]
                    if enemies:
                        cfg.enemy_direction_bundles.append(tuple(enemies))

        # level_meta_items（ソロモンの紋章 等）
        # rom_metadata > level_meta_items > level_meta_item
        rom_meta = root.find("rom_metadata")
        if rom_meta is not None:
            lmi_node = rom_meta.find("level_meta_items")
            if lmi_node is not None:
                cfg._load_meta_items(lmi_node, rom_data, region)

            # item_bitmasks (Level 20/30 のアイテム一括配置 bitmap)
            ib_node = rom_meta.find("item_bitmasks")
            if ib_node is not None:
                cfg._load_item_bitmasks(ib_node, region)

        return cfg

    def _load_item_bitmasks(self, ib_node, region: str):
        """item_bitmask をロード。region でフィルタ。
        各エントリ: level_no (0-indexed), item_no, offset (ROM)"""
        from ..core.region import base_region as _base
        base = _base(region) if region else ""
        for elem in ib_node.findall("item_bitmask"):
            region_attr = elem.attrib.get("region", "")
            if region_attr:
                regions = [r.strip() for r in region_attr.split(",")]
                if region not in regions and base not in regions:
                    continue
            try:
                level_no = parse_int(elem.attrib["level_no"])
                item_no = parse_int(elem.attrib["item_no"])
                offset = parse_int(elem.attrib["offset"])
            except (KeyError, ValueError):
                continue
            self.item_bitmasks.append({
                "level_no": level_no,
                "item_no": item_no,
                "offset": offset,
            })

    def _load_meta_items(self, lmi_node, rom_data: bytes, region: str):
        """level_meta_item をロード。region でフィルタしつつ、
        offset 指定があれば rom_data から位置をデコード"""
        from ..core.element import position_from_byte
        from ..core.region import base_region as _base
        base = _base(region) if region else ""

        for elem in lmi_node.findall("level_meta_item"):
            # region 属性が指定されていたら一致するもののみ採用
            region_attr = elem.attrib.get("region", "")
            if region_attr:
                regions = [r.strip() for r in region_attr.split(",")]
                if region not in regions and base not in regions:
                    continue

            no = parse_int(elem.attrib["no"])
            level_no = parse_int(elem.attrib["level_no"])
            anim = parse_int(elem.attrib.get("animation", "0"))
            transp_attr = elem.attrib.get("transparent", "")
            transparent = transp_attr.lower() in ("true", "1")
            description = elem.attrib.get("description", "")

            # 位置: offset 属性があれば ROM から読む、なければ position 属性
            offset_attr = elem.attrib.get("offset", "")
            pos_attr = elem.attrib.get("position", "")

            rom_off = -1
            if offset_attr and rom_data is not None:
                off = parse_int(offset_attr)
                if 0 <= off < len(rom_data):
                    position = position_from_byte(rom_data[off])
                    rom_off = off
                else:
                    continue
            elif pos_attr:
                parts = [s.strip() for s in pos_attr.split(",")]
                position = (parse_int(parts[0]), parse_int(parts[1]))
            else:
                continue

            self.level_meta_items.append(
                MetaItemDef(no, level_no, anim, transparent, position, description,
                            rom_offset=rom_off)
            )

    def get_palette(self, palette_no: int) -> "pal.SubPalette":
        """サブパレット取得"""
        return pal.SubPalette(self.palettes[palette_no])

    def get_tileset(self, tileset_no: int) -> TilesetDef:
        return self.tilesets[tileset_no]
