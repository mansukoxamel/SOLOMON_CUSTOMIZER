"""skchain互換XML形式でのレベル入出力

skchain v1.1 のXMLフォーマット:
<skchain app_version="1.1">
  <level start_position="x,y" door_position="x,y" key_position="x,y"
         key_status="N" spawn_enemy_lifetime="N" time_decrease_rate="N"
         constellation_no="N" constellation_position="x,y" tileset="N">
    <blocks>
      <block_row no="0" value="2,2,2,..." />
      ...
    </blocks>
    <items>
      <item no="0" element_no="N" position="x,y" />
      ...
    </items>
    <enemies>
      <enemy no="0" element_no="N" position="x,y" />
      ...
    </enemies>
    <mirrors>
      <mirror no="0" position="x,y" schedule="N" enemy_set="N" />
      <mirror no="1" position="x,y" schedule="N" enemy_set="N" />
    </mirrors>
  </level>
</skchain>

ブロック値: 0=NONE, 1=BROWN(壊せる), 2=WHITE(壊せない), 3=BROWN_WHITE(壊せる白)
配置フラグ bit: 0x40=hidden(隠し) / 0x80=in_block(ブロック内) /
  0xC0=white in_block(壊せる白ブロック内) / 0=通常
鍵状態: 0x00=通常 / 0x40=ブロック内 / 0x80=隠し / 0xC0=白ブロック内
  ※実証確定 (element.py is_hidden/is_in_block が正。R178/隠し扉
    TEST_HiddenDoor 実機・エディタ画面と一致)。旧コメントは
    $40/$80 を逆記載していた (2026-05-17 Codex指摘で訂正)
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .. import __version__
from . import constants as c
from .element import LevelElement, ElementType, Wall, DemonMirror
from .level import Level


SKCHAIN_APP_VERSION = "1.1"


def _pos_str(pos: tuple) -> str:
    """位置タプル→ "x,y" 形式"""
    return f"{pos[0]},{pos[1]}"


def _parse_pos(s: str) -> tuple:
    parts = s.strip().split(",")
    return (int(parts[0]), int(parts[1]))


def level_to_xml_element(level: Level) -> ET.Element:
    """Level → XML <level> 要素"""
    lv = ET.Element("level")
    lv.set("start_position", _pos_str(level.fixed_start_pos))
    lv.set("door_position", _pos_str(level.fixed_door_pos))
    lv.set("key_position", _pos_str(level.fixed_key_pos))
    lv.set("key_status", str(level.key_status))
    lv.set("spawn_enemy_lifetime", str(level.spawn_enemy_lifetime))
    lv.set("time_decrease_rate", str(level.time_decrease_rate))
    lv.set("constellation_no", str(level.get_constellation_no()))
    lv.set("constellation_position", _pos_str(level.get_constellation_pos()))
    lv.set("tileset", str(level.tileset_no))
    lv.set("room_flags", str(int(level.room_flags) & ~0x20))
    lv.set("stage_ext_flags", str(getattr(level, "stage_ext_flags", 0)))
    lv.set("fire_reset_value", str(getattr(level, "fire_reset_value", 0)))
    lv.set("key_enemy_slot", str(getattr(level, "key_enemy_slot", 255)))
    lv.set("key_enemy_mode", str(getattr(level, "key_enemy_mode", 0)))
    lv.set("fairy_enemy_slot", str(getattr(level, "fairy_enemy_slot", 255)))
    lv.set("announce_id", str(getattr(level, "announce_id", 0)))
    lv.set("announce_flags", str(getattr(level, "announce_flags", 0)))
    lv.set("panel_variant_a_speed", str(getattr(level, "panel_variant_a_speed", 0)))
    lv.set("panel_variant_a_interval", str(getattr(level, "panel_variant_a_interval", 0xC0)))
    lv.set("panel_variant_b_speed", str(getattr(level, "panel_variant_b_speed", 1)))
    lv.set("panel_variant_b_interval", str(getattr(level, "panel_variant_b_interval", 0xC0)))
    lv.set("panel_variant_c_speed", str(getattr(level, "panel_variant_c_speed", 2)))
    lv.set("panel_variant_c_interval", str(getattr(level, "panel_variant_c_interval", 0xC0)))

    # blocks
    blocks = ET.SubElement(lv, "blocks")
    for y in range(c.LEVEL_H):
        row = ET.SubElement(blocks, "block_row")
        row.set("no", str(y))
        vals = [str(level.tiles[y][x].value) for x in range(c.LEVEL_W)]
        row.set("value", ",".join(vals))

    # items
    items = ET.SubElement(lv, "items")
    for i, it in enumerate(level.items):
        e = ET.SubElement(items, "item")
        e.set("no", str(i))
        e.set("element_no", str(it.element_no))
        e.set("position", _pos_str(it.position))

    vib_cells = sorted(getattr(level, "visible_in_block_item_cells", set()))
    if vib_cells:
        vib = ET.SubElement(lv, "visible_in_block_items")
        for i, pos in enumerate(vib_cells):
            e = ET.SubElement(vib, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    # breakable white wall markers. The actual block is still stored as Wall.WHITE.
    bw_cells = sorted(getattr(level, "breakable_white_cells", set()))
    if bw_cells:
        bw = ET.SubElement(lv, "breakable_white")
        for i, pos in enumerate(bw_cells):
            e = ET.SubElement(bw, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    cb_cells = sorted(getattr(level, "cracked_block_cells", set()))
    if cb_cells:
        cb = ET.SubElement(lv, "cracked_block")
        for i, pos in enumerate(cb_cells):
            e = ET.SubElement(cb, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    ib_cells = sorted(getattr(level, "invisible_breakable_cells", set()))
    if ib_cells:
        ib = ET.SubElement(lv, "invisible_breakable")
        for i, pos in enumerate(ib_cells):
            e = ET.SubElement(ib, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    pw_cells = sorted(getattr(level, "passable_white_cells", set()))
    if pw_cells:
        pw = ET.SubElement(lv, "passable_white")
        for i, pos in enumerate(pw_cells):
            e = ET.SubElement(pw, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    pb_cells = sorted(getattr(level, "passable_brown_cells", set()))
    if pb_cells:
        pb = ET.SubElement(lv, "passable_brown")
        for i, pos in enumerate(pb_cells):
            e = ET.SubElement(pb, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    sb_cells = sorted(getattr(level, "solid_brown_cells", set()))
    if sb_cells:
        sb = ET.SubElement(lv, "solid_brown")
        for i, pos in enumerate(sb_cells):
            e = ET.SubElement(sb, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    is_cells = sorted(getattr(level, "invisible_solid_cells", set()))
    if is_cells:
        isw = ET.SubElement(lv, "invisible_solid")
        for i, pos in enumerate(is_cells):
            e = ET.SubElement(isw, "cell")
            e.set("no", str(i))
            e.set("position", _pos_str(pos))

    # enemies
    enemies = ET.SubElement(lv, "enemies")
    for i, en in enumerate(level.enemies):
        e = ET.SubElement(enemies, "enemy")
        e.set("no", str(i))
        e.set("element_no", str(en.element_no))
        e.set("position", _pos_str(en.position))

    # mirrors
    mirrors = ET.SubElement(lv, "mirrors")
    for i, m in enumerate(level.demon_mirrors):
        e = ET.SubElement(mirrors, "mirror")
        e.set("no", str(i))
        e.set("position", _pos_str(m.position))
        e.set("schedule", str(m.schedule_no))
        e.set("enemy_set", str(m.monster_set_no))
        # 敵セット実データ（拡張ROM編集後の実際の敵コードリスト）
        if hasattr(m, "enemy_codes") and m.enemy_codes:
            e.set("enemy_codes", ",".join(str(c) for c in m.enemy_codes))
        # ドロップスケジュール実データ（8バイト）
        if hasattr(m, "schedule_data") and m.schedule_data:
            e.set("schedule_data", ",".join(str(c) for c in m.schedule_data))

    return lv


def level_to_xml_string(level: Level) -> str:
    """単一レベルをskchain互換XML文字列にシリアライズ"""
    root = ET.Element("skchain")
    root.set("app_version", SKCHAIN_APP_VERSION)
    root.set("customizer_app_version", __version__)
    root.append(level_to_xml_element(level))

    # 整形（minidom で indent）
    raw = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    pretty = minidom.parseString(raw).toprettyxml(indent="\t", encoding="utf-8")
    # 先頭にコメント挿入
    decl = '<?xml version="1.0"?>\n'
    body = pretty.decode("utf-8")
    # minidom が自動付加した宣言を取り除いて再挿入
    if body.startswith("<?xml"):
        body = body.split("?>", 1)[1].lstrip()
    return (decl
            + "<!-- Solomon's Key level file created with SOLOMON_CUSTOMIZER -->\n"
            + body)


SOLOMON_CUSTOMIZER_FORMAT_VERSION = "1.0"


def level_to_magatu_xml(level: Level, level_meta_positions=None,
                        conditional_breakable_positions=None,
                        bomb_jack_positions=None) -> str:
    """PNG埋め込み用の独自形式XML"""
    root = ET.Element("solomon_customizer")
    root.set("format_version", SOLOMON_CUSTOMIZER_FORMAT_VERSION)
    root.set("app_version", __version__)
    root.append(level_to_xml_element(level))
    if level_meta_positions:
        positions_elem = ET.SubElement(root, "level_meta_positions")
        for i, entry in enumerate(level_meta_positions):
            e = ET.SubElement(positions_elem, "meta")
            e.set("no", str(int(entry["no"])))
            e.set("level_no", str(int(entry["level_no"])))
            e.set("kind", str(entry.get("kind", "")))
            e.set("description", str(entry.get("description", "")))
            e.set("position", _pos_str(tuple(entry["position"])))
    if conditional_breakable_positions:
        positions_elem = ET.SubElement(root, "conditional_breakable_positions")
        for entry in conditional_breakable_positions:
            e = ET.SubElement(positions_elem, "marker")
            e.set("level_no", str(int(entry["level_no"])))
            e.set("group", str(entry["group"]))
            e.set("sub", str(entry["sub"]))
            e.set("position", _pos_str(tuple(entry["position"])))
    if bomb_jack_positions:
        positions_elem = ET.SubElement(root, "bomb_jack_positions")
        for entry in bomb_jack_positions:
            e = ET.SubElement(positions_elem, "marker")
            e.set("level_no", str(int(entry["level_no"])))
            e.set("sub", str(entry["sub"]))
            e.set("position", _pos_str(tuple(entry["position"])))

    raw = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    pretty = minidom.parseString(raw).toprettyxml(indent="\t", encoding="utf-8")
    body = pretty.decode("utf-8")
    if body.startswith("<?xml"):
        body = body.split("?>", 1)[1].lstrip()
    return '<?xml version="1.0"?>\n' + body


def levels_to_xml_string(levels: list) -> str:
    """53レベルまとめてskchain互換XML文字列に（独自拡張: 複数レベル束ね）"""
    root = ET.Element("skchain")
    root.set("app_version", SKCHAIN_APP_VERSION)
    root.set("customizer_app_version", __version__)
    for lv in levels:
        root.append(level_to_xml_element(lv))
    raw = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    pretty = minidom.parseString(raw).toprettyxml(indent="\t", encoding="utf-8")
    decl = '<?xml version="1.0"?>\n'
    body = pretty.decode("utf-8")
    if body.startswith("<?xml"):
        body = body.split("?>", 1)[1].lstrip()
    return (decl
            + "<!-- Solomon's Key level bundle created with SOLOMON_CUSTOMIZER -->\n"
            + body)


def xml_element_to_level(level_elem: ET.Element) -> Level:
    """XML <level> 要素 → Level オブジェクト"""
    lv = Level()
    lv.fixed_start_pos = _parse_pos(level_elem.attrib["start_position"])
    lv.fixed_door_pos = _parse_pos(level_elem.attrib["door_position"])
    lv.fixed_key_pos = _parse_pos(level_elem.attrib["key_position"])
    lv.key_status = int(level_elem.attrib.get("key_status", "0"))
    lv.spawn_enemy_lifetime = int(level_elem.attrib.get("spawn_enemy_lifetime", "0"))
    lv.time_decrease_rate = int(level_elem.attrib.get("time_decrease_rate", "0"))
    lv.tileset_no = int(level_elem.attrib.get("tileset", "0"))
    lv.room_flags = int(level_elem.attrib.get("room_flags", "0")) & ~0x20
    lv.stage_ext_flags = int(level_elem.attrib.get("stage_ext_flags", "0"))
    lv.fire_reset_value = int(level_elem.attrib.get("fire_reset_value", "0"))
    lv.key_enemy_slot = int(level_elem.attrib.get("key_enemy_slot", "255"))
    lv.key_enemy_mode = int(level_elem.attrib.get("key_enemy_mode", "0"))
    lv.fairy_enemy_slot = int(level_elem.attrib.get("fairy_enemy_slot", "255"))
    lv.announce_id = int(level_elem.attrib.get("announce_id", "0"))
    lv.announce_flags = int(level_elem.attrib.get("announce_flags", "0"))
    # Stage-local Panel Variant parameters are retained only for old-file
    # compatibility.  Current saves use global A/B/C settings instead.
    lv.panel_variant_a_speed = 0
    lv.panel_variant_a_interval = 192
    lv.panel_variant_b_speed = 1
    lv.panel_variant_b_interval = 192
    lv.panel_variant_c_speed = 2
    lv.panel_variant_c_interval = 192

    # 星座
    const_no = int(level_elem.attrib.get("constellation_no", "0"))
    if const_no >= c.ITEM_CONSTELLATION_MIN:
        cpos = _parse_pos(level_elem.attrib.get("constellation_position", "0,0"))
        lv.constellation = LevelElement(ElementType.ITEM, cpos, const_no)
    else:
        lv.constellation = None

    # blocks
    blocks_elem = level_elem.find("blocks")
    lv.tiles = [[Wall.NONE for _ in range(c.LEVEL_W)] for _ in range(c.LEVEL_H)]
    if blocks_elem is not None:
        for row in blocks_elem.findall("block_row"):
            y = int(row.attrib["no"])
            vals = [int(v) for v in row.attrib["value"].split(",")]
            for x, v in enumerate(vals):
                if 0 <= y < c.LEVEL_H and 0 <= x < c.LEVEL_W:
                    lv.tiles[y][x] = Wall(v)

    # items
    lv.items = []
    items_elem = level_elem.find("items")
    if items_elem is not None:
        for it in items_elem.findall("item"):
            element_no = int(it.attrib["element_no"])
            pos = _parse_pos(it.attrib["position"])
            lv.items.append(LevelElement(ElementType.ITEM, pos, element_no))

    lv.visible_in_block_item_cells = set()
    vib_elem = level_elem.find("visible_in_block_items")
    if vib_elem is not None:
        item_positions = {it.position for it in lv.items}
        for cell in vib_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H and pos in item_positions:
                lv.visible_in_block_item_cells.add(pos)
                lv.tiles[y][x] = Wall.NONE

    lv.breakable_white_cells = set()
    bw_elem = level_elem.find("breakable_white")
    if bw_elem is not None:
        for cell in bw_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.breakable_white_cells.add(pos)
                lv.tiles[y][x] = Wall.WHITE

    lv.cracked_block_cells = set()
    cb_elem = level_elem.find("cracked_block")
    if cb_elem is not None:
        for cell in cb_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.cracked_block_cells.add(pos)
                lv.tiles[y][x] = Wall.BROWN

    lv.invisible_breakable_cells = set()
    ib_elem = level_elem.find("invisible_breakable")
    if ib_elem is not None:
        for cell in ib_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.invisible_breakable_cells.add(pos)
                lv.tiles[y][x] = Wall.NONE

    lv.passable_white_cells = set()
    pw_elem = level_elem.find("passable_white")
    if pw_elem is not None:
        for cell in pw_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.passable_white_cells.add(pos)
                lv.tiles[y][x] = Wall.WHITE

    lv.passable_brown_cells = set()
    pb_elem = level_elem.find("passable_brown")
    if pb_elem is not None:
        for cell in pb_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.passable_brown_cells.add(pos)
                lv.tiles[y][x] = Wall.BROWN

    lv.solid_brown_cells = set()
    sb_elem = level_elem.find("solid_brown")
    if sb_elem is not None:
        for cell in sb_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.solid_brown_cells.add(pos)
                lv.tiles[y][x] = Wall.BROWN

    lv.invisible_solid_cells = set()
    is_elem = level_elem.find("invisible_solid")
    if is_elem is not None:
        for cell in is_elem.findall("cell"):
            pos = _parse_pos(cell.attrib["position"])
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                lv.invisible_solid_cells.add(pos)
                lv.tiles[y][x] = Wall.NONE

    # enemies
    lv.enemies = []
    enemies_elem = level_elem.find("enemies")
    if enemies_elem is not None:
        for en in enemies_elem.findall("enemy"):
            element_no = int(en.attrib["element_no"])
            pos = _parse_pos(en.attrib["position"])
            lv.enemies.append(LevelElement(ElementType.ENEMY, pos, element_no))

    # mirrors
    mirrors_elem = level_elem.find("mirrors")
    if mirrors_elem is not None:
        mirrors = mirrors_elem.findall("mirror")
        for i, m in enumerate(mirrors[:2]):
            pos = _parse_pos(m.attrib["position"])
            schedule = int(m.attrib.get("schedule", "0"))
            enemy_set = int(m.attrib.get("enemy_set", "0"))
            if i < len(lv.demon_mirrors):
                lv.demon_mirrors[i].position = pos
                lv.demon_mirrors[i].schedule_no = schedule
                lv.demon_mirrors[i].monster_set_no = enemy_set
                # 敵セット実データの復元
                codes_attr = m.attrib.get("enemy_codes", "")
                if codes_attr:
                    lv.demon_mirrors[i].enemy_codes = [int(c) for c in codes_attr.split(",") if c.strip()]
                # ドロップスケジュール実データの復元
                sched_attr = m.attrib.get("schedule_data", "")
                if sched_attr:
                    lv.demon_mirrors[i].schedule_data = [int(c) for c in sched_attr.split(",") if c.strip()]

    return lv


def xml_string_to_levels(xml_str: str) -> list:
    """skchain互換XML文字列 → Level のリスト

    1レベルだけでも複数レベルでも対応。
    """
    root = ET.fromstring(xml_str)
    if root.tag != "skchain":
        raise ValueError(f"ルート要素は <skchain> である必要があります（実際: <{root.tag}>）")
    return [xml_element_to_level(le) for le in root.findall("level")]


def save_level_xml(level: Level, path: str):
    """単一レベルをskchain互換XMLファイルに保存"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(level_to_xml_string(level))


def load_level_xml(path: str) -> list:
    """skchain互換XMLファイルからレベルを読み込み（リストで返す）"""
    with open(path, "r", encoding="utf-8") as f:
        return xml_string_to_levels(f.read())
