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
    "main.compare.group": {
        "ja": "比較",
        "en": "Compare",
    },
    "main.compare.current": {
        "ja": "現在",
        "en": "Current",
    },
    "main.compare.diff": {
        "ja": "差分",
        "en": "Diff",
    },
    "main.compare.rom_diff": {
        "ja": "ROM比較",
        "en": "Compare ROMs",
    },
    "main.compare.rom_diff.tooltip": {
        "ja": "ROM/ZIP同士のステージ差分を比較します。PNGとの比較は比較編集を使います。",
        "en": "Compare stage differences between ROM/ZIP files. Use Compare Edit for PNG comparison.",
    },
    "main.compare.edit_start": {
        "ja": "比較編集",
        "en": "Compare Edit",
    },
    "main.compare.edit_start.tooltip": {
        "ja": "現在ステージのスナップショットを横に表示して比較編集モードを開始します。(Ctrl+Q)",
        "en": "Start compare-edit mode by showing a snapshot of the current stage beside it. (Ctrl+Q)",
    },
    "main.compare.edit_end": {
        "ja": "比較編集終了",
        "en": "End Compare Edit",
    },
    "main.compare.edit_end.tooltip": {
        "ja": "比較編集モードを終了して通常表示に戻します。(Ctrl+Q)",
        "en": "End compare-edit mode and return to the normal view. (Ctrl+Q)",
    },
    "main.compare.orientation": {
        "ja": "縦横(Q)",
        "en": "Layout (Q)",
    },
    "main.compare.orientation.tooltip": {
        "ja": "比較しながら編集の表示方向を横並び/縦並びで切り替えます。(Q)",
        "en": "Switch compare-edit layout between side-by-side and stacked. (Q)",
    },
    "main.compare.end": {
        "ja": "終了",
        "en": "End",
    },
    "main.compare.end.tooltip": {
        "ja": "比較編集モードを終了して通常表示に戻します。",
        "en": "End compare-edit mode and return to the normal view.",
    },
    "main.view.group": {
        "ja": "表示オプション",
        "en": "View Options",
    },
    "main.view.grid": {
        "ja": "グリッド表示",
        "en": "Show Grid",
    },
    "main.view.hidden": {
        "ja": "隠し要素強調 (黄色枠)",
        "en": "Highlight Hidden Elements (Yellow)",
    },
    "main.view.special_marks": {
        "ja": "特殊処理マーカー表示",
        "en": "Show Special Process Markers",
    },
    "main.view.special_marks.tooltip": {
        "ja": (
            "ROMのハードコード特殊処理が動的に配置するマスを枠で表示。\n"
            "緑=壊せるブロック / 水色=強制クリア\n"
            "例: Stage 50 SOLOMON の (7,1) (12,7) (3,3) は壊せる隠しブロックとして配置される"
        ),
        "en": (
            "Show cells dynamically placed by hard-coded ROM special processes.\n"
            "Green = breakable block / Cyan = forced clear\n"
            "Example: Stage 50 SOLOMON cells (7,1), (12,7), and (3,3) are placed as hidden breakable blocks."
        ),
    },
    "main.view.stage_selector": {
        "ja": "ステージ選択ペイン表示",
        "en": "Show Stage Selector",
    },
    "main.view.stage_selector.tooltip": {
        "ja": "右端のサムネイル付きステージ選択ペインを表示/非表示にします。",
        "en": "Show or hide the thumbnail stage selector pane on the right.",
    },
    "main.view.edit_col15": {
        "ja": "16列目を編集",
        "en": "Edit Column 16",
    },
    "main.view.edit_col15.tooltip": {
        "ja": "右端列(16列目)はデータ上常に壁。通常は編集不可。\nONにすると編集できる。",
        "en": "The rightmost column (column 16) is always wall data. It is normally locked.\nTurn this on to edit it.",
    },
    "main.tools.group": {
        "ja": "編集ツール",
        "en": "Edit Tools",
    },
    "main.tools.clear": {
        "ja": "オブジェクト削除 ▼",
        "en": "Delete Objects ▼",
    },
    "main.tools.clear.tooltip": {
        "ja": "現在のステージから要素を削除（Undo可能）",
        "en": "Delete elements from the current stage. Undo is available.",
    },
    "main.tools.clear_all": {
        "ja": "すべて削除（鍵/扉/スタート/ミラーは保持）",
        "en": "Delete All (Keep Key / Door / Start / Mirrors)",
    },
    "main.tools.clear_blocks": {
        "ja": "ブロックのみ削除",
        "en": "Delete Blocks Only",
    },
    "main.tools.clear_items": {
        "ja": "アイテムのみ削除",
        "en": "Delete Items Only",
    },
    "main.tools.clear_enemies": {
        "ja": "モンスターのみ削除",
        "en": "Delete Monsters Only",
    },
    "main.tools.stats": {
        "ja": "全ステージ統計",
        "en": "All Stage Stats",
    },
    "main.tools.stats.tooltip": {
        "ja": "53ステージのアイテム/敵/隠し配置を一覧表示します。(Ctrl+I)",
        "en": "List items, enemies, and hidden placements across all 53 stages. (Ctrl+I)",
    },
    "main.tools.game_hack": {
        "ja": "ゲーム挙動改造",
        "en": "Game Behavior Mods",
    },
    "main.tools.game_hack.tooltip": {
        "ja": "開始ライフ・開始ステージ等の既知ROMアドレスを書き換え",
        "en": "Edit known ROM addresses such as starting lives and starting stage.",
    },
    "main.tools.enemy_hack": {
        "ja": "敵改造",
        "en": "Enemy Mods",
    },
    "main.tools.enemy_hack.tooltip": {
        "ja": "敵AI・敵速度など、敵に関係するROM挙動を編集",
        "en": "Edit enemy-related ROM behavior such as enemy AI and speed.",
    },
    "main.tools.palette": {
        "ja": "パレット編集",
        "en": "Palette Editor",
    },
    "main.tools.palette.tooltip": {
        "ja": "背景・スプライトのパレット (8パレット x 3色) を編集",
        "en": "Edit background and sprite palettes (8 palettes x 3 colors).",
    },
    "main.tools.sprite_viewer": {
        "ja": "スプライトビューア",
        "en": "Sprite Viewer",
    },
    "main.tools.sprite_viewer.tooltip": {
        "ja": "CHR-ROM の全キャラクタータイル (8x8) を一覧表示。\nバンク・パレット・拡大率を切替可能。読込専用。",
        "en": "View all CHR-ROM character tiles (8x8).\nBank, palette, and zoom can be changed. Read-only.",
    },
    "main.tools.title_screen": {
        "ja": "タイトル画面編集",
        "en": "Title Screen Editor",
    },
    "main.tools.title_screen.tooltip": {
        "ja": "タイトル画面を編集/移植: 配置(nametable)+色区分(attribute)+絵(CHR bank3)をピース単位で扱います。コード非改変・JP/US自動判定・CRC不要・双方向。",
        "en": "Edit or port the title screen: layout (nametable), color groups (attributes), and graphics (CHR bank3) are handled piece by piece. Code is not modified; JP/US is auto-detected; CRC is not required; changes are bidirectional.",
    },
    "main.tools.pixel_editor": {
        "ja": "16x16ピクセル編集",
        "en": "16x16 Pixel Editor",
    },
    "main.tools.pixel_editor.tooltip": {
        "ja": "ROMフレーム由来の16x16スプライトを1ピクセル単位で編集。16x16画像の取り込みにも対応。",
        "en": "Edit ROM-frame-based 16x16 sprites pixel by pixel. 16x16 image import is also supported.",
    },
    "main.tools.sound_viewer": {
        "ja": "音楽データ表示",
        "en": "Sound Data Viewer",
    },
    "main.tools.sound_viewer.tooltip": {
        "ja": "ROM内サウンドデータをC/D/E表記のテキストで表示（読取専用）",
        "en": "Show ROM sound data as C/D/E-style text. Read-only.",
    },
    "main.tools.special_process": {
        "ja": "特殊処理ビューア",
        "en": "Special Process Viewer",
    },
    "main.tools.special_process.tooltip": {
        "ja": "各ステージにハードコードされた特殊処理を表示します（読取専用）。",
        "en": "Show hard-coded special processes for each stage. Read-only.",
    },
    "main.tools.batch_replace": {
        "ja": "オブジェクト一括置換",
        "en": "Batch Replace Objects",
    },
    "main.tools.batch_replace.tooltip": {
        "ja": "指定したブロック、アイテム、モンスターを同じ種別内で一括置換。選択範囲、現在ステージ、全ステージを対象にできます。",
        "en": "Batch-replace specified blocks, items, or monsters within the same category. Scope can be the selection, current stage, or all stages.",
    },
    "main.stage.group": {
        "ja": "ステージ設定",
        "en": "Stage Settings",
    },
    "main.stage.tileset": {
        "ja": "タイルセット:",
        "en": "Tileset:",
    },
    "main.stage.time_limit": {
        "ja": "制限時間:",
        "en": "Time Limit:",
    },
    "main.stage.restrictions": {
        "ja": "制限:",
        "en": "Restrictions:",
    },
    "main.stage.no_bfire": {
        "ja": "Bボタン（ファイア）禁止",
        "en": "Disable B Button (Fire)",
    },
    "main.stage.no_bfire.tooltip": {
        "ja": (
            "この部屋だけBボタンの火球(魔法)を無効化。Aボタンの石生成は使えます。\n"
            "ROM保存時に bank0 のコードケーブへ注入 (位置+署名 検証付き)"
        ),
        "en": (
            "Disable B-button fireballs only in this room. A-button stone creation still works.\n"
            "Injected into a bank0 code cave when saving the ROM, with position and signature checks."
        ),
    },
    "main.stage.no_astone": {
        "ja": "Aボタン(換石)禁止",
        "en": "Disable A Button (Stone)",
    },
    "main.stage.no_astone.tooltip": {
        "ja": (
            "この部屋だけAボタンの石生成を無効化 (Bファイアとは独立)。\n"
            "※石で階段が作れず進行不能になり得ます。意図して使う設定です"
        ),
        "en": (
            "Disable A-button stone creation only in this room, independently from B fire.\n"
            "This can make the stage impossible if stairs must be made from stones. Use intentionally."
        ),
    },
    "main.stage.dark": {
        "ja": "暗闇モード",
        "en": "Darkness Mode",
    },
    "main.stage.dark.tooltip": {
        "ja": (
            "この面のプレイ中だけ背景(地形/HUD)を明滅で消し、敵とDana\n"
            "だけ見えるようにします。明の瞬間に地形/鍵/扉が見えるので\n"
            "記憶して進む暗闇面。明/暗の長さは全体共通(ゲーム挙動改造\n"
            "の『暗闇テンポ』)。タイトル/紹介/クリアは通常表示・必ず明から"
        ),
        "en": (
            "During this stage, blink the background, terrain, and HUD off so only enemies and Dana remain visible.\n"
            "Terrain, keys, and doors are visible during lit moments, so the stage must be navigated from memory.\n"
            "Light/dark timing is global and set by the Darkness Tempo game behavior mod. Title, intro, and clear screens stay normal and always start lit."
        ),
    },
    "main.stage.fire_reset": {
        "ja": "開始時にファイヤー所持をリセット",
        "en": "Reset Fire Power on Start",
    },
    "main.stage.fire_reset.tooltip": {
        "ja": "この面を開始した時に、前の面から持ち越したファイヤー/スーパーの所持を0にします。",
        "en": "When this stage starts, reset fire/super fire carried over from the previous stage.",
    },
    "main.stage.none": {
        "ja": "(なし)",
        "en": "(None)",
    },
    "main.stage.enemy_number.tooltip": {
        "ja": "0=なし。1から15は、このステージの初期配置敵リスト順です。",
        "en": "0 = none. 1 through 15 refer to the initial enemy placement order in this stage.",
    },
    "main.stage.fairy_enemy.tooltip": {
        "ja": "0=なし。1から15は、このステージの初期配置敵リスト順です。鍵持ち敵と同じ番号は指定できません。",
        "en": "0 = none. 1 through 15 refer to the initial enemy placement order in this stage. This cannot match the key-carrying enemy.",
    },
    "main.stage.key_enemy": {
        "ja": "鍵持ち敵 (#):",
        "en": "Key Enemy (#):",
    },
    "main.stage.fairy_enemy": {
        "ja": "妖精化敵 (#):",
        "en": "Fairy Enemy (#):",
    },
    "main.stage.constellation": {
        "ja": "星座:",
        "en": "Constellation:",
    },
    "main.stage.position_x": {
        "ja": "位置 X:",
        "en": "Position X:",
    },
    "main.stage_ops.copy": {
        "ja": "面コピー",
        "en": "Copy Stage",
    },
    "main.stage_ops.copy.tooltip": {
        "ja": "現在のステージデータ一式を内部クリップボードへコピー",
        "en": "Copy all current stage data to the internal clipboard.",
    },
    "main.stage_ops.paste": {
        "ja": "貼り付け",
        "en": "Paste",
    },
    "main.stage_ops.paste.tooltip": {
        "ja": "コピーしたステージデータ一式で現在のステージを上書き",
        "en": "Overwrite the current stage with the copied stage data.",
    },
    "main.stage_ops.swap": {
        "ja": "面入れ替え",
        "en": "Swap Stages",
    },
    "main.stage_ops.swap.tooltip": {
        "ja": "現在のステージと指定ステージのデータ一式を入れ替え",
        "en": "Swap all data between the current stage and the selected stage.",
    },
    "main.stage_ops.swap_execute": {
        "ja": "入替実行",
        "en": "Run Swap",
    },
    "main.stage_ops.copy_source.none": {
        "ja": "コピー元: なし",
        "en": "Copy Source: None",
    },
    "main.stage_ops.copy_source": {
        "ja": "コピー元: {stage}",
        "en": "Copy Source: {stage}",
    },
    "main.stage_ops.swap_source": {
        "ja": "入れ替え元: {stage}",
        "en": "Swap Source: {stage}",
    },
    "main.action.restart_app": {
        "ja": "アプリを再起動します",
        "en": "The application will restart",
    },
    "main.rom.unsupported.title": {
        "ja": "非対応ROM",
        "en": "Unsupported ROM",
    },
    "main.rom.unsupported.readonly_reject": {
        "ja": (
            "このROMは通常編集入口にも、閲覧/ステージ出力専用入口にも該当しません。\n"
            "読み取り専用で受け入れるのは skchain US66 mapper66 ROM、"
            "または US/JP mapper3 ROM だけです。\n"
            "Region: {region}\nCRC32: {crc}"
        ),
        "en": (
            "This ROM does not match either the normal editing input or the read-only stage export input.\n"
            "Read-only loading accepts only skchain US66 mapper66 ROMs, or US/JP mapper3 ROMs.\n"
            "Region: {region}\nCRC32: {crc}"
        ),
    },
    "main.rom.unsupported.jp66_no_metadata": {
        "ja": (
            "日本版 mapper66 拡張ROMは、本アプリで保存したROMだけ読み込めます。\n"
            "SOLOMON_CUSTOMIZERのメタデータが見つかりません。\n"
            "CRC32: {crc}"
        ),
        "en": (
            "JP mapper66 expanded ROMs can only be loaded if they were saved by this application.\n"
            "SOLOMON_CUSTOMIZER metadata was not found.\n"
            "CRC32: {crc}"
        ),
    },
    "main.rom.unsupported.editor_target": {
        "ja": (
            "このアプリの通常編集対象は日本版 Solomon no Kagi のROM、"
            "または本アプリで保存した日本版 mapper66 拡張ROMだけです。\n"
            "CRC32: {crc}"
        ),
        "en": (
            "This application's normal editing target is the Japanese Solomon no Kagi ROM, "
            "or a JP mapper66 expanded ROM saved by this application.\n"
            "CRC32: {crc}"
        ),
    },
    "main.rom.load_aborted.unsupported": {
        "ja": "ROM読込を中止: 非対応ROM",
        "en": "ROM load canceled: unsupported ROM",
    },
    "main.rom.load_aborted.jp66_unknown": {
        "ja": "ROM読込を中止: 未確認JP66拡張ROMは非対応",
        "en": "ROM load canceled: unverified JP66 expanded ROM is unsupported",
    },
    "main.rom.load_failed": {
        "ja": "ロード失敗",
        "en": "Load Failed",
    },
    "main.rom.save_dialog.title": {
        "ja": "改造ROMの保存先",
        "en": "Save Modified ROM",
    },
    "main.rom.project_save_failed.title": {
        "ja": "制作データ保存失敗",
        "en": "Project Data Save Failed",
    },
    "main.rom.project_save_failed.body": {
        "ja": "ROMは保存されましたが、共通設定JSONまたはステージPNGの保存に失敗しました。\n\n{error}",
        "en": "The ROM was saved, but saving the common settings JSON or stage PNGs failed.\n\n{error}",
    },
    "main.rom.save_complete": {
        "ja": "ROM保存完了: {path}{suffix}",
        "en": "ROM saved: {path}{suffix}",
    },
    "main.rom.save_failed": {
        "ja": "保存失敗",
        "en": "Save Failed",
    },
    "main.rom.save_failed.log": {
        "ja": "ROM保存失敗",
        "en": "ROM save failed",
    },
    "main.testplay.emulator_unset.title": {
        "ja": "エミュレータ未設定",
        "en": "Emulator Not Configured",
    },
    "main.testplay.emulator_unset.body": {
        "ja": "F9 設定画面でテストプレイ用エミュレータを登録し、既定にしてください",
        "en": "Register a test-play emulator in Settings (F9) and set it as the default.",
    },
    "main.testplay.prepare_failed.title": {
        "ja": "テストプレイ準備失敗",
        "en": "Test Play Preparation Failed",
    },
    "main.testplay.prepare_failed.extra": {
        "ja": (
            "通常の「改造ROMとして保存」でも同じエラーが出る場合、"
            "保存前チェックまたはROM容量の制約です。"
        ),
        "en": (
            "If the same error also appears when saving as a modified ROM, "
            "it is caused by pre-save validation or ROM capacity limits."
        ),
    },
    "main.testplay.launched": {
        "ja": "テストプレイ起動: Stage {stage} / {emulator} / {path}{suffix}",
        "en": "Test play launched: Stage {stage} / {emulator} / {path}{suffix}",
    },
    "main.testplay.emulator_launch_failed": {
        "ja": "エミュ起動失敗",
        "en": "Emulator Launch Failed",
    },
    "main.ips.base_dialog.title": {
        "ja": "原本ROM（市販吸出し）を選択",
        "en": "Select Original Dumped ROM",
    },
    "main.ips.base_read_failed": {
        "ja": "原本ROM読込失敗",
        "en": "Original ROM Read Failed",
    },
    "main.ips.generate_failed": {
        "ja": "IPS生成失敗",
        "en": "IPS Generation Failed",
    },
    "main.ips.save_failed.log": {
        "ja": "IPS保存失敗",
        "en": "IPS save failed",
    },
    "main.ips.save_dialog.title": {
        "ja": "IPSパッチ保存",
        "en": "Save IPS Patch",
    },
    "main.ips.save_complete": {
        "ja": "IPS保存完了: {path}{suffix}",
        "en": "IPS saved: {path}{suffix}",
    },
    "main.stage_png.save_dialog.title": {
        "ja": "ステージデータPNGの保存先",
        "en": "Save Stage Data PNG",
    },
    "main.stage_png.save_current.complete": {
        "ja": "保存: {path} (XML埋込)",
        "en": "Saved: {path} (XML embedded)",
    },
    "main.stage_png.save_all.progress": {
        "ja": "保存中: {current}/{total} (XML埋込)",
        "en": "Saving: {current}/{total} (XML embedded)",
    },
    "main.stage_png.save_all.status": {
        "ja": "全 {total} ステージ保存完了 (XML埋込) → {path}",
        "en": "Saved all {total} stages (XML embedded) -> {path}",
    },
    "main.stage_png.save_all.complete.title": {
        "ja": "完了",
        "en": "Complete",
    },
    "main.stage_png.save_all.complete.body": {
        "ja": "全 {total} ステージを保存しました (XML埋込)\n\n保存先:\n{path}",
        "en": "Saved all {total} stages (XML embedded).\n\nFolder:\n{path}",
    },
    "main.stage_png.load_failed.title": {
        "ja": "読込失敗",
        "en": "Load Failed",
    },
    "main.stage_png.error.no_data": {
        "ja": "このPNGにはステージデータが埋め込まれていません",
        "en": "This PNG does not contain embedded stage data.",
    },
    "main.stage_png.error.wrong_root": {
        "ja": "このPNGはSOLOMON_CUSTOMIZERのステージPNGではありません",
        "en": "This PNG is not a SOLOMON_CUSTOMIZER stage PNG.",
    },
    "main.stage_png.error.parse_failed": {
        "ja": "ステージデータの解析に失敗しました",
        "en": "Failed to parse the stage data.",
    },
    "main.stage_png.load_current.status": {
        "ja": "ステージデータ読込: L{stage} に上書き ({name})",
        "en": "Stage data loaded: overwrote L{stage} ({name})",
    },
    "main.stage_png.open_current.title": {
        "ja": "ステージデータPNGを選択",
        "en": "Select Stage Data PNG",
    },
    "main.stage_png.open_all.title": {
        "ja": "ステージデータPNGフォルダを選択",
        "en": "Select Stage Data PNG Folder",
    },
    "main.stage_png.load_all.complete.body": {
        "ja": "{loaded}/{total} ステージをPNGから読み込みました",
        "en": "Loaded {loaded}/{total} stages from PNG.",
    },
    "main.compare.stage_png.open.title": {
        "ja": "比較するステージPNGを選択",
        "en": "Select Stage PNG to Compare",
    },
    "main.compare.stage_png.failed.title": {
        "ja": "比較失敗",
        "en": "Compare Failed",
    },
    "main.compare.stage_png.image_load_failed": {
        "ja": "PNG画像の読み込みに失敗しました",
        "en": "Failed to load the PNG image.",
    },
    "main.compare.stage_png.status": {
        "ja": "PNG比較: L{stage} と {name}",
        "en": "PNG compare: L{stage} with {name}",
    },
    "main.compare.edit.title": {
        "ja": "比較編集",
        "en": "Compare Edit",
    },
    "main.compare.edit.snapshot_failed": {
        "ja": "比較編集用スナップショットを保存できませんでした。\n{error}",
        "en": "Could not save the compare-edit snapshot.\n{error}",
    },
    "main.compare.edit.status": {
        "ja": "比較しながら編集: L{stage} と {name}",
        "en": "Compare editing: L{stage} with {name}",
    },
    "main.compare.edit.label.horizontal": {
        "ja": "横",
        "en": "Horizontal",
    },
    "main.compare.edit.label.vertical": {
        "ja": "縦",
        "en": "Vertical",
    },
    "main.compare.edit.label": {
        "ja": "比較編集({direction}): {name}",
        "en": "Compare Edit ({direction}): {name}",
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
