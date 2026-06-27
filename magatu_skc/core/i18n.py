"""Small runtime language registry for UI text.

This module intentionally keeps translation state outside save data, XML
schemas, ROM metadata, and other stable internal keys.
"""

DEFAULT_LANGUAGE = "ja"
LANGUAGE_OPTIONS = (
    ("ja", "日本語"),
    ("en", "English"),
)
SUPPORTED_LANGUAGES = {key for key, _label in LANGUAGE_OPTIONS}

_current_language = DEFAULT_LANGUAGE

_TRANSLATIONS = {
    "settings.title": {
        "ja": "設定 (F9)",
        "en": "Settings (F9)",
    },
    "settings.tab.general": {
        "ja": "一般",
        "en": "General",
    },
    "settings.tab.colors": {
        "ja": "色・表示",
        "en": "Colors / Display",
    },
    "settings.tab.shortcuts": {
        "ja": "ショートカット",
        "en": "Shortcuts",
    },
    "settings.group.display": {
        "ja": "表示",
        "en": "Display",
    },
    "settings.dirty_mark.label": {
        "ja": "未保存マーク:",
        "en": "Unsaved mark:",
    },
    "settings.language.label": {
        "ja": "表示言語:",
        "en": "Language:",
    },
    "settings.language.tooltip": {
        "ja": (
            "表示言語です。英語化は段階的に対応します。"
            "保存データや内部キーは変更しません。"
        ),
        "en": (
            "Display language. English UI coverage will be added gradually. "
            "Save data and internal keys are not changed."
        ),
    },
    "settings.font.label": {
        "ja": "フォント:",
        "en": "Font:",
    },
    "settings.font.reset": {
        "ja": "既定に戻す",
        "en": "Reset",
    },
    "settings.font_size.label": {
        "ja": "フォントサイズ:",
        "en": "Font size:",
    },
    "settings.default": {
        "ja": "デフォルト",
        "en": "Default",
    },
    "settings.hover_info_font_size.label": {
        "ja": "ホバー情報文字サイズ:",
        "en": "Hover info font size:",
    },
    "settings.hover_info_font_size.tooltip": {
        "ja": "Iキーで表示するホバー情報ポップアップだけの文字サイズです。",
        "en": "Font size used only by the hover info popup toggled with I.",
    },
    "settings.enemy_meter_slot.label": {
        "ja": "敵数メーター1マス:",
        "en": "Enemy meter cell:",
    },
    "settings.enemy_meter_slot.tooltip": {
        "ja": (
            "キャンバス上部の敵数メーターの1マスサイズです。"
            "鍵持ち敵/妖精化敵の表示画像も同じ大きさで拡大縮小します。"
        ),
        "en": (
            "Cell size for the enemy-count meter at the top of the canvas. "
            "Key-carrier and fairy-target icons use the same scale."
        ),
    },
    "settings.bold.label": {
        "ja": "太字:",
        "en": "Bold:",
    },
    "settings.bold.checkbox": {
        "ja": "太字",
        "en": "Bold",
    },
    "demo_input.title": {
        "ja": "デモ操作編集 (34ステップ固定)",
        "en": "Demo Input Editor (Fixed 34 Steps)",
    },
    "demo_input.description": {
        "ja": (
            "タイトル放置で流れるデモの操作を編集します。各行＝入力を"
            "何フレーム続けるか。60フレーム≒1秒。34ステップ固定で、"
            "Start/Selectはデモが中断するため使えません。"
            "最後に死ぬ動きは不要(34ステップ使い切りで終了)。"
        ),
        "en": (
            "Edit the attract-mode input sequence shown after the title screen is left idle. "
            "Each row sets which buttons are held and for how many frames. "
            "60 frames is about 1 second. The sequence is fixed at 34 steps. "
            "Start and Select cannot be used because they interrupt the demo. "
            "No final death movement is needed; the demo ends after all 34 steps are consumed."
        ),
    },
    "demo_input.column.step": {
        "ja": "#",
        "en": "#",
    },
    "demo_input.column.frames": {
        "ja": "フレーム",
        "en": "Frames",
    },
    "demo_input.button.up": {
        "ja": "上",
        "en": "Up",
    },
    "demo_input.button.down": {
        "ja": "下",
        "en": "Down",
    },
    "demo_input.button.left": {
        "ja": "左",
        "en": "Left",
    },
    "demo_input.button.right": {
        "ja": "右",
        "en": "Right",
    },
    "demo_input.restore_original": {
        "ja": "原作に戻す",
        "en": "Restore Original",
    },
    "demo_input.apply_failed": {
        "ja": "デモ操作編集失敗",
        "en": "Demo Input Edit Failed",
    },
    "demo_input.open_failed": {
        "ja": "デモ操作編集不可",
        "en": "Demo Input Edit Unavailable",
    },
    "demo_input.error.rom_too_small": {
        "ja": "",
        "en": "The ROM is too small. Demo input editing was canceled.",
    },
    "demo_input.error.signature": {
        "ja": "",
        "en": (
            "The $CBEC signature does not match. The ROM may be modified, "
            "extended, US-region, or corrupted, so demo input editing was canceled. "
            "This feature is JP-only."
        ),
    },
    "demo_input.error.step_count": {
        "ja": "",
        "en": (
            "The $CBF6 step count does not match the expected 34 steps. "
            "The ROM may be modified or corrupted, so demo input editing was canceled."
        ),
    },
    "demo_input.error.invalid_step_count": {
        "ja": "",
        "en": "The number of demo input steps is invalid.",
    },
    "clear_message.title": {
        "ja": "クリア画面メッセージ編集 (同字数・JP)",
        "en": "Clear Screen Message Editor (JP Fixed Length)",
    },
    "clear_message.description": {
        "ja": (
            "ステージクリア後の『おめでとう画面』3行を編集します。"
            "英大文字 A-Z とスペースのみ。<b>原作と同じ文字数まで</b>"
            "(長くはできません。短い分はスペースで埋まります)。"
            "原作は THANK YOU DANA / YOU RELEASED THIS ROOM / "
            "TRY NEXT ROOM。"
        ),
        "en": (
            "Edit the three lines shown on the stage-clear congratulations screen. "
            "Only uppercase A-Z and spaces are allowed. "
            "<b>Each line must stay within the original character limit</b>; "
            "shorter text is padded with spaces. "
            "The original lines are THANK YOU DANA / YOU RELEASED THIS ROOM / "
            "TRY NEXT ROOM."
        ),
    },
    "clear_message.column.line": {
        "ja": "行",
        "en": "Line",
    },
    "clear_message.column.text": {
        "ja": "文字",
        "en": "Text",
    },
    "clear_message.column.count": {
        "ja": "字数",
        "en": "Count",
    },
    "clear_message.column.original": {
        "ja": "原作",
        "en": "Original",
    },
    "clear_message.line_label": {
        "ja": "{index}行目",
        "en": "Line {index}",
    },
    "clear_message.count_suffix": {
        "ja": "{count}字",
        "en": "{count} chars",
    },
    "clear_message.restore_original": {
        "ja": "原作に戻す",
        "en": "Restore Original",
    },
    "clear_message.apply_failed": {
        "ja": "クリア画面メッセージ編集失敗",
        "en": "Clear Screen Message Edit Failed",
    },
    "clear_message.open_failed": {
        "ja": "クリア画面メッセージ編集不可",
        "en": "Clear Screen Message Edit Unavailable",
    },
    "clear_message.error.rom_too_small": {
        "ja": "",
        "en": "The ROM is too small. Clear screen message editing was canceled.",
    },
    "clear_message.error.header": {
        "ja": "",
        "en": (
            "A message header signature does not match. The ROM may be US-region, "
            "mapped differently, modified, or corrupted, so editing was canceled. "
            "This feature is JP-only and fixed-length."
        ),
    },
    "clear_message.error.terminator": {
        "ja": "",
        "en": (
            "A message terminator does not match $00. The ROM may be modified "
            "or corrupted, so editing was canceled."
        ),
    },
    "clear_message.error.unknown_tile": {
        "ja": "",
        "en": (
            "A message contains an unknown character tile. The ROM may be modified "
            "or corrupted, so editing was canceled."
        ),
    },
    "clear_message.error.invalid_char": {
        "ja": "",
        "en": "Only uppercase A-Z and spaces can be used.",
    },
    "clear_message.error.too_long": {
        "ja": "",
        "en": "The text is too long for this fixed-length message line.",
    },
    "clear_message.error.invalid_line_count": {
        "ja": "",
        "en": "The number of clear screen message lines is invalid.",
    },
    "enemy_drop.title": {
        "ja": "敵ドロップ効果表 編集",
        "en": "Enemy Drop Effect Table Editor",
    },
    "enemy_drop.title.applied": {
        "ja": "敵ドロップ効果表 編集  (適用済)",
        "en": "Enemy Drop Effect Table Editor (Applied)",
    },
    "enemy_drop.description": {
        "ja": (
            "敵を炎で倒した時に出る効果を行ごとに編集します。確率＝8枠中の"
            "出現数。<b>値は効果値であり通常アイテムIDではありません</b>"
            "（$06=1UP で鍵ではない）。行は複数の敵で共有されます。"
        ),
        "en": (
            "Edit the effect dropped when an enemy is defeated by fire. "
            "Probability is based on how many of the 8 slots contain each effect. "
            "<b>These values are drop effects, not normal item IDs</b> "
            "($06 is 1UP, not a key). Rows are shared by multiple enemies."
        ),
    },
    "enemy_drop.row_header": {
        "ja": "行 {row} - 使用: {users}",
        "en": "Row {row} - Used by: {users}",
    },
    "enemy_drop.users.none": {
        "ja": "Bomb Jack系/Fairy系/Bullet/Gargoyle s2/Flame (ドロップ無)",
        "en": "Bomb Jack types / Fairy types / Bullet / Gargoyle s2 / Flame (no drop)",
    },
    "enemy_drop.users.fireball": {
        "ja": "Fireball s1・s2",
        "en": "Fireball s1 / s2",
    },
    "enemy_drop.users.ghost": {
        "ja": "Ghost 各系",
        "en": "Ghost types",
    },
    "enemy_drop.users.neul": {
        "ja": "Neul 各系",
        "en": "Neul types",
    },
    "enemy_drop.users.demonhead12": {
        "ja": "Demonhead s1・s2",
        "en": "Demonhead s1 / s2",
    },
    "enemy_drop.users.demonhead3_saramandor12": {
        "ja": "Demonhead s3 / Saramandor s1・s2",
        "en": "Demonhead s3 / Saramandor s1 / s2",
    },
    "enemy_drop.users.saramandor3_dragon1": {
        "ja": "Saramandor s3 / Dragon s1",
        "en": "Saramandor s3 / Dragon s1",
    },
    "enemy_drop.users.dragon2_golem1": {
        "ja": "Dragon s2 / Golem s1",
        "en": "Dragon s2 / Golem s1",
    },
    "enemy_drop.users.golem2_gargoyle1": {
        "ja": "Golem s2 / Gargoyle s1",
        "en": "Golem s2 / Gargoyle s1",
    },
    "enemy_drop.users.panel_monster": {
        "ja": "Panel Monster",
        "en": "Panel Monster",
    },
    "enemy_drop.probability": {
        "ja": "確率: {parts}",
        "en": "Probability: {parts}",
    },
    "enemy_drop.restore_original": {
        "ja": "原作に戻す",
        "en": "Restore Original",
    },
    "enemy_drop.clear_all": {
        "ja": "すべて未設定にする",
        "en": "Set All to None",
    },
    "enemy_drop.apply_failed": {
        "ja": "敵ドロップ改造失敗",
        "en": "Enemy Drop Edit Failed",
    },
    "enemy_drop.open_failed": {
        "ja": "敵ドロップ編集不可",
        "en": "Enemy Drop Edit Unavailable",
    },
    "enemy_drop.error.rom_too_small": {
        "ja": "",
        "en": "The ROM is too small. Enemy drop editing was canceled.",
    },
    "enemy_drop.error.signature": {
        "ja": "",
        "en": (
            "A code signature does not match. The ROM may be modified, extended, "
            "or corrupted, so enemy drop editing was canceled."
        ),
    },
    "enemy_drop.error.shape": {
        "ja": "",
        "en": "The enemy drop table shape is invalid.",
    },
    "enemy_drop.error.value": {
        "ja": "",
        "en": "The enemy drop table contains an unsupported value.",
    },
    "enemy_drop.effect.00": {"ja": "なし", "en": "None"},
    "enemy_drop.effect.01": {"ja": "未確定$01", "en": "Unknown $01"},
    "enemy_drop.effect.02": {"ja": "マガドラの壺", "en": "Magdra Pot"},
    "enemy_drop.effect.03": {"ja": "ライラックの鐘", "en": "Lilac Bell"},
    "enemy_drop.effect.04": {"ja": "ファイア距離+", "en": "Fire Range+"},
    "enemy_drop.effect.05": {"ja": "妖精予約", "en": "Fairy Queue"},
    "enemy_drop.effect.06": {"ja": "1UP", "en": "1UP"},
    "enemy_drop.effect.07": {"ja": "未確定$07", "en": "Unknown $07"},
    "enemy_drop.effect.08": {"ja": "スコア+10", "en": "Score +10"},
    "enemy_drop.effect.09": {"ja": "スコア+20", "en": "Score +20"},
    "enemy_drop.effect.0A": {"ja": "スコア+50", "en": "Score +50"},
    "enemy_drop.effect.0B": {"ja": "スコア+100", "en": "Score +100"},
    "enemy_drop.effect.0C": {"ja": "スコア+200", "en": "Score +200"},
    "enemy_drop.effect.0D": {"ja": "スコア+500", "en": "Score +500"},
    "enemy_drop.effect.0E": {"ja": "スコア+1000", "en": "Score +1000"},
    "enemy_drop.effect.0F": {"ja": "スコア+2000", "en": "Score +2000"},
    "sound_viewer.title": {
        "ja": "音楽データ表示",
        "en": "Sound Data Viewer",
    },
    "sound_viewer.song.label": {
        "ja": "曲:",
        "en": "Song:",
    },
    "sound_viewer.expand_calls": {
        "ja": "CALL先を展開",
        "en": "Expand CALL targets",
    },
    "sound_viewer.copy": {
        "ja": "コピー",
        "en": "Copy",
    },
    "sound_viewer.info": {
        "ja": "読取専用。raw byte と ASM解釈を並べて表示します。",
        "en": "Read-only. Shows raw bytes alongside the interpreted ASM.",
    },
    "sound_viewer.open_failed": {
        "ja": "音楽データ表示不可",
        "en": "Sound Data View Unavailable",
    },
    "main.file.group": {
        "ja": "ファイル",
        "en": "File",
    },
    "main.file.open_rom": {
        "ja": "ROM読込",
        "en": "Open ROM",
    },
    "main.file.open_rom.tooltip": {
        "ja": "ROMを開きます。(Ctrl+O)",
        "en": "Open a ROM. (Ctrl+O)",
    },
    "main.file.restart": {
        "ja": "再起動",
        "en": "Restart",
    },
    "main.file.restart.tooltip": {
        "ja": "アプリを再起動",
        "en": "Restart the application",
    },
    "main.file.history": {
        "ja": "履歴",
        "en": "History",
    },
    "main.file.history.tooltip": {
        "ja": "最近開いたROMから選択",
        "en": "Choose from recently opened ROMs",
    },
    "main.file.no_rom": {
        "ja": "(未読込)",
        "en": "(No ROM loaded)",
    },
    "main.file.validation": {
        "ja": "不整合",
        "en": "Issues",
    },
    "main.file.validation.tooltip": {
        "ja": "読み込んだROMの不整合らしき配置を一覧表示",
        "en": "List placements that look inconsistent in the loaded ROM",
    },
    "main.file.migrate": {
        "ja": "データ移行",
        "en": "Migrate Data",
    },
    "main.file.migrate.tooltip": {
        "ja": (
            "このROMのステージを編集可能ROMへ移します。"
            "全てを完全に移行できるとは限りません。"
        ),
        "en": (
            "Move this ROM's stages into an editable ROM. "
            "Some data may not migrate perfectly."
        ),
    },
    "main.file.save_rom": {
        "ja": "ROM保存",
        "en": "Save ROM",
    },
    "main.file.save_rom.tooltip": {
        "ja": "現在の編集内容をROMとして保存します。(Ctrl+S)",
        "en": "Save the current edits as a ROM. (Ctrl+S)",
    },
    "main.file.save_ips": {
        "ja": "IPSパッチ出力",
        "en": "Export IPS Patch",
    },
    "main.file.test_play": {
        "ja": "▶ テストプレイ",
        "en": "▶ Test Play",
    },
    "main.file.test_play.tooltip": {
        "ja": "左クリック: 既定エミュレータで起動 / 右クリック: エミュレータを選んで起動",
        "en": "Left click: launch with the default emulator / Right click: choose an emulator",
    },
    "main.file.scope.current": {
        "ja": "現在のステージ",
        "en": "Current Stage",
    },
    "main.file.scope.all": {
        "ja": "すべてのステージ",
        "en": "All Stages",
    },
    "main.file.stage_load": {
        "ja": "ステージデータ読込",
        "en": "Load Stage Data",
    },
    "main.file.stage_save": {
        "ja": "ステージデータ保存",
        "en": "Save Stage Data",
    },
    "main.file.stage_save.tooltip": {
        "ja": "選択した範囲のステージデータPNGを保存します。Ctrl+Eは現在ステージを保存します。",
        "en": "Save stage-data PNGs for the selected scope. Ctrl+E saves the current stage.",
    },
    "main.file.open_dialog.title": {
        "ja": "NES ROM を選択",
        "en": "Select NES ROM",
    },
    "main.file.action.open_another": {
        "ja": "別のROMを開きます",
        "en": "Another ROM will be opened",
    },
    "main.file.action.open_dropped": {
        "ja": "ドロップされたROMを開きます",
        "en": "The dropped ROM will be opened",
    },
    "main.unsaved.title": {
        "ja": "未保存の変更",
        "en": "Unsaved Changes",
    },
    "main.unsaved.text": {
        "ja": "現在の編集内容はまだ保存されていません。",
        "en": "The current edits have not been saved yet.",
    },
    "main.unsaved.informative": {
        "ja": "{action}。\n保存せずに続行すると、現在の編集内容は破棄されます。",
        "en": "{action}.\nIf you continue without saving, the current edits will be discarded.",
    },
    "main.unsaved.save_continue": {
        "ja": "保存して続行",
        "en": "Save and Continue",
    },
    "main.unsaved.discard_continue": {
        "ja": "破棄して続行",
        "en": "Discard and Continue",
    },
    "common.close": {
        "ja": "閉じる",
        "en": "Close",
    },
    "common.ok": {
        "ja": "OK",
        "en": "OK",
    },
    "common.cancel": {
        "ja": "キャンセル",
        "en": "Cancel",
    },
    "common.apply": {
        "ja": "適用",
        "en": "Apply",
    },
}


def normalize_language(value) -> str:
    key = str(value or "").strip().lower()
    if key in SUPPORTED_LANGUAGES:
        return key
    return DEFAULT_LANGUAGE


def set_language(value) -> str:
    global _current_language
    _current_language = normalize_language(value)
    return _current_language


def get_language() -> str:
    return _current_language


def language_label(value) -> str:
    key = normalize_language(value)
    for lang_key, label in LANGUAGE_OPTIONS:
        if lang_key == key:
            return label
    return key


def t(key: str, default: str = "") -> str:
    entry = _TRANSLATIONS.get(key)
    if not entry:
        return default
    return entry.get(_current_language) or entry.get(DEFAULT_LANGUAGE) or default
