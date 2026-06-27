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
    "settings.group.colors_markers": {"ja": "色・マーカー", "en": "Colors / Markers"},
    "settings.theme_gray.label": {"ja": "黒テーマ明度:", "en": "Dark theme brightness:"},
    "settings.theme_gray.tooltip": {
        "ja": "黒テーマの明るさです。小さいほど黒く、大きいほど明るくなります。",
        "en": "Brightness of the dark theme. Smaller values are darker; larger values are brighter.",
    },
    "settings.marker_overlay_scale.label": {"ja": "編集用マーカー線幅:", "en": "Edit marker line width:"},
    "settings.marker_overlay_scale.option": {"ja": "{value}倍", "en": "{value}x"},
    "settings.marker_overlay_scale.tooltip": {
        "ja": "キャンバス上の隠し要素枠や特殊処理マーカーなどの線幅倍率です。",
        "en": "Line-width multiplier for hidden-element frames, special-process markers, and similar canvas markers.",
    },
    "settings.marker_color.bonus_marker_color": {"ja": "ボーナス菱形色:", "en": "Bonus diamond color:"},
    "settings.marker_color.hidden_marker_color": {"ja": "隠し要素色:", "en": "Hidden element color:"},
    "settings.marker_color.visible_in_block_marker_color": {"ja": "透明ブロック内アイテム色:", "en": "Visible in-block item color:"},
    "settings.marker_color.breakable_white_marker_color": {"ja": "壊せる白ブロック色:", "en": "Breakable white block color:"},
    "settings.marker_color.invisible_breakable_marker_color": {"ja": "透明壊せるブロック色:", "en": "Invisible breakable block color:"},
    "settings.marker_color.passable_marker_color": {"ja": "すり抜けブロック色:", "en": "Passable block color:"},
    "settings.marker_color.solid_marker_color": {"ja": "壊せない特殊ブロック色:", "en": "Solid special block color:"},
    "settings.marker_color.mirror1_marker_color": {"ja": "ミラー1色:", "en": "Mirror 1 color:"},
    "settings.marker_color.mirror2_marker_color": {"ja": "ミラー2色:", "en": "Mirror 2 color:"},
    "settings.marker_color.special_empty_marker_color": {"ja": "特殊処理: 強制空色:", "en": "Special process: forced empty color:"},
    "settings.marker_color.special_trigger_marker_color": {"ja": "特殊処理: トリガー色:", "en": "Special process: trigger color:"},
    "settings.marker_color.special_link_marker_color": {"ja": "特殊処理: リンク線色:", "en": "Special process: link line color:"},
    "settings.marker_color.selection_marker_color": {"ja": "選択範囲色:", "en": "Selection color:"},
    "settings.marker_color.hover_marker_color": {"ja": "ホバー枠色:", "en": "Hover frame color:"},
    "settings.marker_shape.rect_large": {"ja": "四角 大", "en": "Rectangle Large"},
    "settings.marker_shape.rect_small": {"ja": "四角 小", "en": "Rectangle Small"},
    "settings.marker_shape.cross_large": {"ja": "× 大", "en": "Cross Large"},
    "settings.marker_shape.cross_medium": {"ja": "× 中", "en": "Cross Medium"},
    "settings.marker_shape.cross_small": {"ja": "× 小", "en": "Cross Small"},
    "settings.marker_shape.ellipse_large": {"ja": "丸 大", "en": "Circle Large"},
    "settings.marker_shape.ellipse_small": {"ja": "丸 小", "en": "Circle Small"},
    "settings.marker_shape.triangle_large": {"ja": "三角 大", "en": "Triangle Large"},
    "settings.marker_shape.triangle_small": {"ja": "三角 小", "en": "Triangle Small"},
    "settings.marker_shape.plus_large": {"ja": "十字 大", "en": "Plus Large"},
    "settings.marker_shape.plus_small": {"ja": "十字 小", "en": "Plus Small"},
    "settings.icon.label": {"ja": "アイコン:", "en": "Icon:"},
    "settings.icon.open_title": {"ja": "アイコンを選択", "en": "Select Icon"},
    "settings.group.external": {"ja": "外部連携", "en": "External Integration"},
    "settings.emulator.list.label": {"ja": "登録:", "en": "Registered:"},
    "settings.emulator.set_default": {"ja": "既定にする", "en": "Set Default"},
    "settings.emulator.name.label": {"ja": "表示名:", "en": "Display name:"},
    "settings.emulator.name.placeholder": {"ja": "例: Mesen 0.9.9", "en": "Example: Mesen 0.9.9"},
    "settings.emulator.path.label": {"ja": "実行ファイル:", "en": "Executable:"},
    "settings.emulator.path.placeholder": {"ja": "例: D:/emu/fceux/fceux.exe", "en": "Example: D:/emu/fceux/fceux.exe"},
    "settings.emulator.open_title": {"ja": "エミュレータを選択", "en": "Select Emulator"},
    "settings.emulator.default_name": {"ja": "エミュレータ {index}", "en": "Emulator {index}"},
    "settings.group.workflow": {"ja": "テストプレイ・PNG出力", "en": "Test Play / PNG Export"},
    "settings.quick_test.label": {"ja": "クイックテストプレイ:", "en": "Quick test play:"},
    "settings.quick_test.checkbox": {"ja": "タイトル画面と開始待ちを省略する", "en": "Skip title screen and start wait"},
    "settings.quick_test.tooltip": {
        "ja": "ON: テストプレイ時に現在ステージをすぐ起動します。\nOFF: タイトル画面から通常どおり起動します。",
        "en": "ON: Immediately starts the current stage during test play.\nOFF: Starts normally from the title screen.",
    },
    "settings.stage_png_show_secrets.label": {"ja": "ステージPNGで隠し要素表示:", "en": "Show secrets in stage PNG:"},
    "settings.stage_png_show_secrets.checkbox": {
        "ja": "隠し要素や敵バリエーション表示をPNGに含める",
        "en": "Include hidden elements and enemy-variant markers in PNG",
    },
    "settings.stage_png_show_secrets.tooltip": {
        "ja": (
            "ON: 制作者確認用として隠しアイテムや特殊ブロックを画像にも表示します。\n"
            "OFF: 友人へ渡すプレイ用として隠し要素を画像から隠します。\n"
            "PNG内のステージデータXMLはON/OFFに関係なく保持されます。"
        ),
        "en": (
            "ON: Shows hidden items and special blocks in the image for author review.\n"
            "OFF: Hides secret elements from the image for player-facing sharing.\n"
            "Embedded stage-data XML is kept regardless of this setting."
        ),
    },
    "settings.group.history": {"ja": "履歴・自動保存", "en": "History / Autosave"},
    "settings.autosave_keep_count.label": {"ja": "作業状態自動保存:", "en": "Autosaved work states:"},
    "settings.autosave_keep_count.suffix": {"ja": " 世代", "en": " generations"},
    "settings.autosave_keep_count.tooltip": {
        "ja": "終了時に保存する作業状態の保持数です。既定は10世代です。",
        "en": "Number of work-state autosaves kept on exit. Default is 10 generations.",
    },
    "settings.undo_limit.label": {"ja": "Undo履歴上限:", "en": "Undo history limit:"},
    "settings.undo_limit.suffix": {"ja": " 件", "en": " entries"},
    "settings.undo_limit.tooltip": {
        "ja": "ステージ編集のUndo/Redo履歴上限です。既定は200件、最大999件です。",
        "en": "Undo/Redo history limit for stage editing. Default is 200; maximum is 999.",
    },
    "settings.group.todo": {"ja": "今後追加予定の項目", "en": "Planned Items"},
    "settings.todo.notification": {"ja": "・通知音ファイル + 音量", "en": "- Notification sound file + volume"},
    "settings.todo.cloud_backup": {"ja": "・クラウドバックアップ先フォルダ", "en": "- Cloud backup destination folder"},
    "settings.group.shortcuts": {"ja": "ショートカット", "en": "Shortcuts"},
    "settings.shortcut.key.label": {"ja": "キー", "en": "Key"},
    "settings.shortcut.pad.label": {"ja": "パッド", "en": "Pad"},
    "settings.shortcut.default": {"ja": "既定", "en": "Default"},
    "settings.shortcut.conflict.key": {
        "ja": "キー {shortcut}: {left} / {right}",
        "en": "Key {shortcut}: {left} / {right}",
    },
    "settings.shortcut.conflict.pad": {
        "ja": "パッド {shortcut}: {left} / {right}",
        "en": "Pad {shortcut}: {left} / {right}",
    },
    "settings.shortcut.conflict.title": {"ja": "ショートカット重複", "en": "Shortcut Conflict"},
    "settings.shortcut.conflict.body": {
        "ja": "同じショートカットが複数の操作に割り当てられています。\n重複を解消してから適用してください。\n\n",
        "en": "The same shortcut is assigned to multiple actions.\nResolve the conflict before applying.\n\n",
    },
    "settings.color.choose": {"ja": "色選択...", "en": "Choose Color..."},
    "settings.marker_color.dialog_title": {"ja": "マーカー色", "en": "Marker Color"},
    "common.browse": {"ja": "参照...", "en": "Browse..."},
    "common.add": {"ja": "追加", "en": "Add"},
    "common.delete": {"ja": "削除", "en": "Delete"},
    "common.file_filter.images": {
        "ja": "Images (*.png *.ico *.jpg *.bmp);;All files (*)",
        "en": "Images (*.png *.ico *.jpg *.bmp);;All files (*)",
    },
    "common.file_filter.executables": {
        "ja": "Executables (*.exe);;All files (*)",
        "en": "Executables (*.exe);;All files (*)",
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
    "main.stage_ops.read_only": {
        "ja": "編集不可: 閲覧/ステージ出力専用ROMです",
        "en": "Read-only: this ROM is for viewing/stage export only.",
    },
    "main.stage_ops.copy_complete": {
        "ja": "{stage} をコピーしました",
        "en": "Copied {stage}.",
    },
    "main.stage_ops.paste.title": {
        "ja": "ステージ貼り付け",
        "en": "Paste Stage",
    },
    "main.stage_ops.paste.confirm": {
        "ja": "{source} のデータを {target} へ貼り付けます。\n\n{target} の現在の内容は上書きされます。",
        "en": "Paste data from {source} into {target}.\n\nThe current contents of {target} will be overwritten.",
    },
    "main.stage_ops.paste_complete": {
        "ja": "{source} を {target} へ貼り付けました",
        "en": "Pasted {source} into {target}.",
    },
    "main.stage_ops.swap_same": {
        "ja": "同じステージは入れ替え不要です",
        "en": "The same stage does not need to be swapped.",
    },
    "main.stage_ops.swap.title": {
        "ja": "ステージ入れ替え",
        "en": "Swap Stages",
    },
    "main.stage_ops.swap.confirm": {
        "ja": "{source} と {target} のデータ一式を入れ替えます。",
        "en": "Swap all data between {source} and {target}.",
    },
    "main.stage_ops.swap_complete": {
        "ja": "{source} と {target} を入れ替えました",
        "en": "Swapped {source} and {target}.",
    },
    "main.edit.diff_view_blocked": {
        "ja": "差分表示中は編集できません。「現在」に戻すと編集できます",
        "en": "Editing is disabled while the diff view is active. Switch back to Current to edit.",
    },
    "main.edit.diff_eyedropper_blocked": {
        "ja": "差分表示中はスポイトできません。「現在」に戻すと使えます",
        "en": "The eyedropper is disabled while the diff view is active. Switch back to Current to use it.",
    },
    "main.edit.col15_locked": {
        "ja": "16列目は編集不可です（「16列目を編集」をONにしてください）",
        "en": "Column 16 is locked. Turn on Edit Column 16 to edit it.",
    },
    "main.edit.col15_move_locked": {
        "ja": "16列目へは移動できません（「16列目を編集」をONにしてください）",
        "en": "Cannot move into column 16. Turn on Edit Column 16 first.",
    },
    "main.edit.col15_select_locked": {
        "ja": "16列目は範囲選択不可です（「16列目を編集」をONにしてください）",
        "en": "Column 16 cannot be selected. Turn on Edit Column 16 first.",
    },
    "main.edit.block_on_seal": {
        "ja": "ソロモンの紋章位置に置けるブロックは茶色/壊せる白/透明壊せるのみです {tile}",
        "en": "Only brown, breakable white, or invisible breakable blocks can be placed on Solomon's Seal {tile}",
    },
    "main.edit.block_on_enemy": {
        "ja": "敵がいる位置にはブロックを置けません {tile}",
        "en": "Cannot place a block on an enemy {tile}",
    },
    "main.edit.block_on_start": {
        "ja": "スタート位置にブロックは置けません {tile}",
        "en": "Cannot place a block on the start position {tile}",
    },
    "main.edit.block_on_door": {
        "ja": "扉位置にブロックは置けません {tile}",
        "en": "Cannot place a block on the door position {tile}",
    },
    "main.edit.special_wall_on_item": {
        "ja": "アイテムがある位置に特殊壁は置けません（取れなくなる） {tile}",
        "en": "Cannot place this special wall on an item; the item would become unreachable {tile}",
    },
    "main.edit.item_on_invisible_wall": {
        "ja": "透明な白壁にはアイテムを配置できません {tile}",
        "en": "Cannot place an item on an invisible white wall {tile}",
    },
    "main.edit.item_on_special_wall": {
        "ja": "特殊壁にはアイテムを配置できません {tile}",
        "en": "Cannot place an item on a special wall {tile}",
    },
    "main.edit.item_on_key_or_door": {
        "ja": "鍵・扉の位置にはアイテムを置けません {tile}",
        "en": "Cannot place an item on the key or door position {tile}",
    },
    "main.edit.item_on_seal": {
        "ja": "ソロモンの紋章位置には通常アイテムを置けません {tile}",
        "en": "Cannot place a normal item on Solomon's Seal {tile}",
    },
    "main.edit.item_in_solid_white": {
        "ja": "白ブロック内にはアイテムを配置できません {tile}",
        "en": "Cannot place an item inside a solid white block {tile}",
    },
    "main.edit.enemy_on_block": {
        "ja": "ブロックがある位置には敵を置けません {tile}",
        "en": "Cannot place an enemy on a block {tile}",
    },
    "main.edit.enemy_on_start": {
        "ja": "スタート位置には敵を置けません（開始直後に死亡します） {tile}",
        "en": "Cannot place an enemy on the start position; the player would die immediately {tile}",
    },
    "main.edit.enemy_limit": {
        "ja": "敵は1ステージ {count} 体まで（拡張ROM形式の制限）",
        "en": "Each stage can have up to {count} enemies (expanded ROM format limit).",
    },
    "main.edit.start_on_enemy": {
        "ja": "敵がいる位置にはスタートを置けません（開始直後に死亡します） {tile}",
        "en": "Cannot place the start position on an enemy; the player would die immediately {tile}",
    },
    "main.edit.key_without_door": {
        "ja": "扉が削除されているステージには鍵を置けません",
        "en": "Cannot place a key in a stage where the door is deleted.",
    },
    "main.edit.key_on_item": {
        "ja": "アイテムがある位置には鍵を置けません {tile}",
        "en": "Cannot place the key on an item {tile}",
    },
    "main.selection.none": {
        "ja": "選択範囲がありません",
        "en": "No selection.",
    },
    "main.selection.copy_complete": {
        "ja": "コピー: {width}×{height} 範囲 ({count}要素)",
        "en": "Copied: {width}x{height} area ({count} elements)",
    },
    "main.selection.clipboard_empty": {
        "ja": "クリップボードが空です",
        "en": "Clipboard is empty.",
    },
    "main.selection.paste_target_missing": {
        "ja": "ペースト先が不明（選択 or ホバーが必要）",
        "en": "Paste target is unknown. Select an area or hover a tile.",
    },
    "main.selection.paste_complete": {
        "ja": "ペースト: ({x},{y}) 起点",
        "en": "Pasted at origin ({x},{y})",
    },
    "main.selection.delete_key_enemy_blocked": {
        "ja": "鍵メタが無いため、鍵持ち敵に影響する敵は範囲削除できません",
        "en": "Range delete cannot remove enemies that affect the key-carrier enemy because key metadata is missing.",
    },
    "main.selection.delete_complete": {
        "ja": "範囲削除: ({x1},{y1})-({x2},{y2})",
        "en": "Range deleted: ({x1},{y1})-({x2},{y2})",
    },
    "main.selection.flip_horizontal": {
        "ja": "左右反転",
        "en": "Flipped horizontally",
    },
    "main.selection.flip_vertical": {
        "ja": "上下反転",
        "en": "Flipped vertically",
    },
    "main.selection.flip_horizontal_skip_shared": {
        "ja": "左右反転: Stage 52/53共有の条件付き壊せるブロックマーカーは対象外です",
        "en": "Flipped horizontally: shared Stage 52/53 conditional breakable-block markers were skipped.",
    },
    "main.selection.flip_vertical_skip_shared": {
        "ja": "上下反転: Stage 52/53共有の条件付き壊せるブロックマーカーは対象外です",
        "en": "Flipped vertically: shared Stage 52/53 conditional breakable-block markers were skipped.",
    },
    "main.item_state.no_target": {
        "ja": "状態を切り替える対象がありません",
        "en": "No target for state switching.",
    },
    "main.item_state.no_item": {
        "ja": "状態を切り替えるアイテムがありません",
        "en": "No item available for state switching.",
    },
    "main.item_state.unsupported": {
        "ja": "このアイテム形式は状態変更できません",
        "en": "This item format does not support state changes.",
    },
    "main.action.restart_failed": {
        "ja": "再起動失敗",
        "en": "Restart Failed",
    },
    "main.autosave.complete.title": {
        "ja": "作業状態の自動保存",
        "en": "Work State Autosaved",
    },
    "main.autosave.complete.body": {
        "ja": (
            "作業状態を自動保存しました。\n安全に終了します。\n\n"
            "次回、ROMを指定せずに起動した場合は、この作業状態を自動的に復元します。\n\n"
            "{path}"
        ),
        "en": (
            "The work state was autosaved. The app will close safely.\n\n"
            "If you start without specifying a ROM next time, this work state will be restored automatically.\n\n"
            "{path}"
        ),
    },
    "main.autosave.failed.title": {
        "ja": "作業状態の自動保存に失敗",
        "en": "Autosave Failed",
    },
    "main.autosave.failed.body": {
        "ja": (
            "作業状態を自動保存できませんでした。\n"
            "このまま終了すると、今回の変更が失われる可能性があります。\n\n"
            "{detail}\n\n"
            "自動保存せずに終了しますか？"
        ),
        "en": (
            "Could not autosave the work state.\n"
            "If you close now, your changes from this session may be lost.\n\n"
            "{detail}\n\n"
            "Close without autosaving?"
        ),
    },
    "main.replace.scope.selection": {
        "ja": "選択範囲",
        "en": "Selection",
    },
    "main.replace.scope.current": {
        "ja": "現在ステージ",
        "en": "Current Stage",
    },
    "main.replace.scope.all": {
        "ja": "全ステージ",
        "en": "All Stages",
    },
    "main.replace.scope.default": {
        "ja": "対象範囲",
        "en": "Target Scope",
    },
    "main.replace.none": {
        "ja": "置換対象はありませんでした。",
        "en": "No matching targets were found.",
    },
    "main.replace.confirm": {
        "ja": "{scope}で {count} 件の{kind}を置換します。\n\n実行後も Undo で戻せます。続行しますか？",
        "en": "Replace {count} {kind} in {scope}.\n\nYou can still undo this after it runs. Continue?",
    },
    "main.replace.complete": {
        "ja": "{title}: {count} 件 / {stages} ステージ",
        "en": "{title}: {count} replacements / {stages} stages",
    },
    "main.replace.block.title": {
        "ja": "ブロック一括置換",
        "en": "Batch Replace Blocks",
    },
    "main.replace.block.kind": {
        "ja": "ブロック",
        "en": "blocks",
    },
    "main.replace.enemy.title": {
        "ja": "モンスター一括置換",
        "en": "Batch Replace Monsters",
    },
    "main.replace.enemy.kind": {
        "ja": "モンスター",
        "en": "monsters",
    },
    "main.replace.item.title": {
        "ja": "アイテム一括置換",
        "en": "Batch Replace Items",
    },
    "main.replace.item.kind": {
        "ja": "アイテム",
        "en": "items",
    },
    "main.replace.item.white_in_block_unsupported": {
        "ja": "このアイテムは白ブロック内アイテムとして保存できません。",
        "en": "This item cannot be saved as a white-block item.",
    },
    "main.undo.empty": {
        "ja": "Undo履歴なし",
        "en": "No undo history.",
    },
    "main.redo.empty": {
        "ja": "Redo履歴なし",
        "en": "No redo history.",
    },
    "main.undo.status": {
        "ja": "Undo: {label} (履歴 {count} 件)",
        "en": "Undo: {label} ({count} history entries)",
    },
    "main.redo.status": {
        "ja": "Redo: {label} (履歴 {count} 件)",
        "en": "Redo: {label} ({count} history entries)",
    },
    "item_replace.state.normal": {
        "ja": "通常",
        "en": "Normal",
    },
    "item_replace.state.hidden": {
        "ja": "隠し",
        "en": "Hidden",
    },
    "item_replace.state.in_block": {
        "ja": "ブロック内",
        "en": "In Block",
    },
    "item_replace.state.white_in_block": {
        "ja": "白ブロック内",
        "en": "In White Block",
    },
    "item_replace.state.visible_in_block": {
        "ja": "透明ブロック内",
        "en": "In Transparent Block",
    },
    "item_replace.state.cracked_in_block": {
        "ja": "ひび割れブロック内",
        "en": "In Cracked Block",
    },
    "item_replace.unspecified": {
        "ja": "未指定",
        "en": "Not specified",
    },
    "item_replace.drop_hint": {
        "ja": "ピッカーからここへドラッグすると変更できます",
        "en": "Drag here from the picker to change this.",
    },
    "item_replace.title": {
        "ja": "オブジェクト一括置換",
        "en": "Batch Replace Objects",
    },
    "item_replace.note": {
        "ja": (
            "検索元と置換先は、開いた時点のピッカー状態で初期化されます。"
            "変更する場合はピッカーからドラッグしてください。"
            "ブロック、アイテム、モンスターは同じ種別内でのみ置換できます。"
        ),
        "en": (
            "The search target and replacement target are initialized from the picker state when opened. "
            "Drag from the picker to change them. "
            "Blocks, items, and monsters can only be replaced within the same type."
        ),
    },
    "item_replace.from": {
        "ja": "検索する対象",
        "en": "Search Target",
    },
    "item_replace.to": {
        "ja": "置換後の対象",
        "en": "Replacement Target",
    },
    "item_replace.ignore_state": {
        "ja": "検索時は状態を無視する",
        "en": "Ignore state when searching",
    },
    "item_replace.ignore_state.tooltip": {
        "ja": (
            "ONの場合、検索元が隠し/ブロック内などでもアイテム番号だけで検索します。"
            "置換後は上で指定した状態になります。"
        ),
        "en": (
            "When enabled, matching uses only the item number even if the source is hidden or in-block. "
            "The replacement uses the state specified above."
        ),
    },
    "item_replace.scope.label": {
        "ja": "対象範囲:",
        "en": "Scope:",
    },
    "item_replace.replace": {
        "ja": "置換",
        "en": "Replace",
    },
    "rom_diff.title": {
        "ja": "ROM比較",
        "en": "ROM Compare",
    },
    "rom_diff.note": {
        "ja": (
            "ROM/ZIPを2つ選んで、ロード後のステージデータとして比較します。"
            "バイナリ差分ではなく、面ごとのブロック/アイテム/敵/メタ差分を表示します。"
            "ファイルはこの画面へドラッグ&ドロップできます。"
        ),
        "en": (
            "Select two ROM/ZIP files and compare them as loaded stage data. "
            "This shows per-stage block/item/enemy/meta differences, not binary differences. "
            "You can drag and drop files onto this window."
        ),
    },
    "rom_diff.left.placeholder": {
        "ja": "比較元 ROM/ZIP",
        "en": "Source ROM/ZIP",
    },
    "rom_diff.right.placeholder": {
        "ja": "比較先 ROM/ZIP",
        "en": "Target ROM/ZIP",
    },
    "rom_diff.browse": {
        "ja": "参照...",
        "en": "Browse...",
    },
    "rom_diff.left.label": {
        "ja": "比較元:",
        "en": "Source:",
    },
    "rom_diff.right.label": {
        "ja": "比較先:",
        "en": "Target:",
    },
    "rom_diff.compare": {
        "ja": "再比較",
        "en": "Compare Again",
    },
    "rom_diff.compare.tooltip": {
        "ja": "同じ2ファイルをもう一度読み直して比較します。",
        "en": "Reload and compare the same two files again.",
    },
    "rom_diff.details.placeholder": {
        "ja": "表の行を選択すると、ここに詳細差分を表示します。",
        "en": "Select a table row to show detailed differences here.",
    },
    "rom_diff.preview.group": {
        "ja": "選択ステージの画像",
        "en": "Selected Stage Images",
    },
    "rom_diff.preview.empty": {
        "ja": "比較後、変更ステージを選択すると表示します",
        "en": "After comparing, select a changed stage to show the preview.",
    },
    "rom_diff.open.title": {
        "ja": "比較するROM/ZIPを選択",
        "en": "Select ROM/ZIP to Compare",
    },
    "rom_diff.error.need_both": {
        "ja": "比較元と比較先を両方選択してください。",
        "en": "Select both the source and target files.",
    },
    "rom_diff.error.same_file": {
        "ja": "別々のファイルを選択してください。",
        "en": "Select two different files.",
    },
    "rom_diff.error.rom_zip_only": {
        "ja": "ROM/ZIP同士を選択してください。PNG比較はメイン画面の比較編集を使ってください。",
        "en": "Select ROM/ZIP files. Use Compare Edit on the main screen for PNG comparison.",
    },
    "rom_diff.status.comparing": {
        "ja": "比較中...",
        "en": "Comparing...",
    },
    "rom_diff.status.failed": {
        "ja": "比較失敗",
        "en": "Compare Failed",
    },
    "rom_diff.error.failed": {
        "ja": "比較に失敗しました。\n{error}",
        "en": "Comparison failed.\n{error}",
    },
    "rom_diff.column.meta": {
        "ja": "メタ",
        "en": "Meta",
    },
    "rom_diff.column.summary": {
        "ja": "概要",
        "en": "Summary",
    },
    "rom_diff.stage.all": {
        "ja": "全体",
        "en": "Overall",
    },
    "rom_diff.result.changed_stages": {
        "ja": "変更ステージ",
        "en": "changed stages",
    },
    "rom_diff.result.diffs": {
        "ja": "差分",
        "en": "differences",
    },
    "rom_diff.no_stage_diff": {
        "ja": "ステージデータ差分はありません。",
        "en": "No stage data differences were found.",
    },
    "rom_diff.preview.no_image": {
        "ja": "画像なし",
        "en": "No image",
    },
    "main.compare.summary.total": {
        "ja": "合計",
        "en": "Total",
    },
    "rom_validation.title": {
        "ja": "ROM不整合",
        "en": "ROM Inconsistencies",
    },
    "rom_validation.status.ok": {
        "ja": "問題なし",
        "en": "No issues",
    },
    "rom_validation.status.warning_count": {
        "ja": "不整合 {count} 件",
        "en": "{count} inconsistencies",
    },
    "rom_validation.column.content": {
        "ja": "内容",
        "en": "Details",
    },
    "rom_validation.copy": {
        "ja": "結果コピー",
        "en": "Copy Results",
    },
    "rom_validation.no_issues": {
        "ja": "不整合は見つかりませんでした。",
        "en": "No inconsistencies were found.",
    },
    "palette.title": {
        "ja": "パレット編集",
        "en": "Palette Editor",
    },
    "palette.info": {
        "ja": "<b>主人公の色は SPR #0〜#3 のどれかにあります</b>。色ボタンをクリックして選択 → 下の64色パレットで変更。",
        "en": "<b>The player colors are in one of SPR #0-#3</b>. Click a color button, then change it with the 64-color palette below.",
    },
    "palette.wall_group": {
        "ja": "ステージ壁色 (1-48面)",
        "en": "Stage Wall Colors (Stages 1-48)",
    },
    "palette.book_group": {
        "ja": "Stage 50 ソロモンの書の色",
        "en": "Stage 50 Solomon Book Color",
    },
    "palette.color": {
        "ja": "色",
        "en": "Color",
    },
    "palette.bg_group": {
        "ja": "背景パレット",
        "en": "Background Palettes",
    },
    "palette.sprite_group": {
        "ja": "スプライトパレット (主人公・敵・アイテム)",
        "en": "Sprite Palettes (Player / Enemies / Items)",
    },
    "palette.nes_color_group": {
        "ja": "NESカラー選択",
        "en": "NES Color Picker",
    },
    "palette.picker_hint": {
        "ja": "↑ 色ボタンをクリックして編集対象を選択",
        "en": "Click a color button above to choose what to edit.",
    },
    "palette.save_image": {
        "ja": "設定を画像保存...",
        "en": "Save Settings Image...",
    },
    "palette.save_image.tooltip": {
        "ja": "現在のパレット設定をPNG画像とメタデータとして保存",
        "en": "Save the current palette settings as a PNG image with metadata.",
    },
    "palette.load_image": {
        "ja": "画像から読込...",
        "en": "Load from Image...",
    },
    "palette.load_image.tooltip": {
        "ja": "PNG画像のメタデータからパレット設定を読み込み",
        "en": "Load palette settings from PNG metadata.",
    },
    "palette.reset": {
        "ja": "編集開始時に戻す",
        "en": "Reset to Opened State",
    },
    "palette.reset.tooltip": {
        "ja": "このパレット編集を開いた時点の値に戻す",
        "en": "Restore the values from when this palette editor was opened.",
    },
    "palette.random3": {
        "ja": "ランダム3色",
        "en": "Random 3 Colors",
    },
    "palette.random3.tooltip": {
        "ja": "選択中のパレット3色をランダムなNES色に変更",
        "en": "Change the selected palette's three colors to random NES colors.",
    },
    "palette.shift3": {
        "ja": "色相ずらし",
        "en": "Shift Hue",
    },
    "palette.shift3.tooltip": {
        "ja": "選択中パレットの色付き3色だけを同じ明度のまま色相方向へずらす",
        "en": "Shift only the selected palette's three colored entries along the hue direction while keeping brightness.",
    },
    "palette.not_applicable.title": {
        "ja": "対象外",
        "en": "Not Applicable",
    },
    "palette.not_applicable.wall": {
        "ja": "ステージ壁色は1色なので、この操作の対象外です。",
        "en": "Stage wall color has only one color, so this operation does not apply.",
    },
    "palette.not_applicable.book": {
        "ja": "Stage 50 ソロモンの書の色は1色なので、この操作の対象外です。",
        "en": "The Stage 50 Solomon Book color has only one color, so this operation does not apply.",
    },
    "palette.no_target.title": {
        "ja": "対象未選択",
        "en": "No Target Selected",
    },
    "palette.no_target.body": {
        "ja": "先に変更したいパレットの色ボタンを選択してください。",
        "en": "Select the palette color button you want to change first.",
    },
    "palette.save_dialog.title": {
        "ja": "パレット設定を画像保存",
        "en": "Save Palette Settings Image",
    },
    "palette.save_failed": {
        "ja": "PNG保存に失敗しました。",
        "en": "Failed to save the PNG.",
    },
    "palette.save_complete.title": {
        "ja": "保存完了",
        "en": "Save Complete",
    },
    "palette.save_complete.body": {
        "ja": "パレット設定画像を保存しました:\n{path}",
        "en": "Saved the palette settings image:\n{path}",
    },
    "palette.save_failed.title": {
        "ja": "保存失敗",
        "en": "Save Failed",
    },
    "palette.format_error": {
        "ja": "形式エラー",
        "en": "Format Error",
    },
    "palette.error.not_palette": {
        "ja": "このファイルはパレット設定ではありません。",
        "en": "This file is not palette settings data.",
    },
    "palette.error.palette_count": {
        "ja": "パレット数が不正です（{actual}、期待値: {expected}）。",
        "en": "Invalid palette count ({actual}; expected {expected}).",
    },
    "palette.error.color_count": {
        "ja": "パレット {palette} の色数が不正です。",
        "en": "Palette {palette} has an invalid color count.",
    },
    "palette.error.wall_count": {
        "ja": "壁色数が不正です（{actual}、期待値: {expected}）。",
        "en": "Invalid wall color count ({actual}; expected {expected}).",
    },
    "palette.load_dialog.title": {
        "ja": "パレット設定を読み込み",
        "en": "Load Palette Settings",
    },
    "palette.load_failed.title": {
        "ja": "読込失敗",
        "en": "Load Failed",
    },
    "palette.error.image_load": {
        "ja": "画像として読み込めません。",
        "en": "Could not load this as an image.",
    },
    "palette.error.no_metadata": {
        "ja": "このPNGにはパレット設定メタデータがありません。",
        "en": "This PNG does not contain palette settings metadata.",
    },
    "palette.load_complete.title": {
        "ja": "読込完了",
        "en": "Load Complete",
    },
    "palette.load_complete.body": {
        "ja": "パレット設定を読み込みました:\n{name}",
        "en": "Loaded palette settings:\n{name}",
    },
    "pixel.title": {
        "ja": "16x16ピクセル編集",
        "en": "16x16 Pixel Editor",
    },
    "pixel.frame": {
        "ja": "フレーム:",
        "en": "Frame:",
    },
    "pixel.show_duplicates": {
        "ja": "重複参照も表示",
        "en": "Show duplicate references",
    },
    "pixel.show_duplicates.tooltip": {
        "ja": "同じleft/right/attrを参照するROMフレームも個別に表示",
        "en": "Also show ROM frames that reference the same left/right/attr individually.",
    },
    "pixel.chr_bank": {
        "ja": "CHRバンク:",
        "en": "CHR Bank:",
    },
    "pixel.palette": {
        "ja": "表示パレット:",
        "en": "Display Palette:",
    },
    "pixel.palette.auto": {
        "ja": "属性から自動",
        "en": "Auto from Attr",
    },
    "pixel.zoom": {
        "ja": "拡大:",
        "en": "Zoom:",
    },
    "pixel.pen": {
        "ja": "ペン:",
        "en": "Pen:",
    },
    "pixel.undo": {
        "ja": "元に戻す",
        "en": "Undo",
    },
    "pixel.undo.tooltip": {
        "ja": "直前の編集を戻す (Ctrl+Z)",
        "en": "Undo the previous edit (Ctrl+Z).",
    },
    "pixel.redo": {
        "ja": "やり直し",
        "en": "Redo",
    },
    "pixel.redo.tooltip": {
        "ja": "戻した編集をやり直す (Ctrl+Y / Ctrl+Shift+Z)",
        "en": "Redo the reverted edit (Ctrl+Y / Ctrl+Shift+Z).",
    },
    "pixel.flip_h.tooltip": {
        "ja": "選択範囲があれば範囲内、なければ16x16全体を左右反転",
        "en": "Flip the selection horizontally, or the full 16x16 image if there is no selection.",
    },
    "pixel.flip_v.tooltip": {
        "ja": "選択範囲があれば範囲内、なければ16x16全体を上下反転",
        "en": "Flip the selection vertically, or the full 16x16 image if there is no selection.",
    },
    "pixel.import": {
        "ja": "画像取込...",
        "en": "Import Image...",
    },
    "pixel.import.tooltip": {
        "ja": "画像を16x16へ縮小し、現在の表示パレットの最寄り色へ変換",
        "en": "Scale an image to 16x16 and convert it to the nearest colors in the current display palette.",
    },
    "pixel.export": {
        "ja": "PNG保存...",
        "en": "Save PNG...",
    },
    "pixel.export.tooltip": {
        "ja": "現在の16x16作業内容をPNGで保存",
        "en": "Save the current 16x16 work image as PNG.",
    },
    "pixel.clear": {
        "ja": "クリア",
        "en": "Clear",
    },
    "pixel.clear.tooltip": {
        "ja": "作業中の16x16をパレットインデックス0で消去",
        "en": "Clear the current 16x16 work image with palette index 0.",
    },
    "pixel.reload": {
        "ja": "ROMから再読込",
        "en": "Reload from ROM",
    },
    "pixel.reload.tooltip": {
        "ja": "選択フレームの現在のROM内容を読み直す",
        "en": "Reload the selected frame from the current ROM data.",
    },
    "pixel.apply": {
        "ja": "ROMへ書込",
        "en": "Write to ROM",
    },
    "pixel.apply.tooltip": {
        "ja": "作業中の16x16を対応CHRタイルへ書き込む",
        "en": "Write the current 16x16 work image to the corresponding CHR tiles.",
    },
    "pixel.no_frames": {
        "ja": "編集できる16x16 ROMフレームが見つかりません。",
        "en": "No editable 16x16 ROM frames were found.",
    },
    "pixel.pending.title": {
        "ja": "未書込の編集",
        "en": "Unsaved Pixel Edit",
    },
    "pixel.pending.frame": {
        "ja": "現在の作業内容はまだROMへ書き込まれていません。破棄してフレームを切り替えますか？",
        "en": "The current work has not been written to the ROM yet. Discard it and switch frames?",
    },
    "pixel.pending.view_mode": {
        "ja": "現在の作業内容はまだROMへ書き込まれていません。破棄して表示形式を切り替えますか？",
        "en": "The current work has not been written to the ROM yet. Discard it and switch display mode?",
    },
    "pixel.pending.bank": {
        "ja": "現在の作業内容はまだROMへ書き込まれていません。破棄してCHRバンクを切り替えますか？",
        "en": "The current work has not been written to the ROM yet. Discard it and switch CHR banks?",
    },
    "pixel.reload.title": {
        "ja": "再読込",
        "en": "Reload",
    },
    "pixel.reload.confirm": {
        "ja": "現在の作業内容を破棄してROMから読み直しますか？",
        "en": "Discard the current work and reload it from ROM?",
    },
    "pixel.import_dialog.title": {
        "ja": "16x16画像を取り込み",
        "en": "Import 16x16 Image",
    },
    "pixel.import_failed.title": {
        "ja": "画像取込失敗",
        "en": "Image Import Failed",
    },
    "pixel.import_failed.body": {
        "ja": "画像を読み込めませんでした。",
        "en": "Could not load the image.",
    },
    "pixel.export_dialog.title": {
        "ja": "16x16 PNGを保存",
        "en": "Save 16x16 PNG",
    },
    "pixel.export_failed.title": {
        "ja": "PNG保存失敗",
        "en": "PNG Save Failed",
    },
    "pixel.export_failed.body": {
        "ja": "PNGを書き出せませんでした。",
        "en": "Could not write the PNG.",
    },
    "pixel.apply_failed.title": {
        "ja": "書込失敗",
        "en": "Write Failed",
    },
    "pixel.close.title": {
        "ja": "閉じる",
        "en": "Close",
    },
    "pixel.close.confirm": {
        "ja": "ROMへ書き込んでいない作業内容があります。破棄して閉じますか？",
        "en": "The current work has not been written to the ROM yet. Discard it and close?",
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
    "main.rom.verify.known": {
        "ja": "✓ 正規",
        "en": "Verified",
    },
    "main.rom.verify.unknown": {
        "ja": "? 不明/改造版",
        "en": "Unknown / Modified",
    },
    "main.rom.info.auto_expanded": {
        "ja": "⚙ 拡張ROMに自動変換 (mapper 66)",
        "en": "Auto-converted to expanded ROM (mapper 66)",
    },
    "main.rom.info.expanded": {
        "ja": "拡張ROM (mapper 66)",
        "en": "Expanded ROM (mapper 66)",
    },
    "main.rom.info.read_only": {
        "ja": "編集不可: 閲覧/ステージ出力専用 ({reason})",
        "en": "Read-only: view/stage export only ({reason})",
    },
    "main.rom.info.workstate_restored": {
        "ja": "作業状態復元: {saved_at}",
        "en": "Work state restored: {saved_at}",
    },
    "main.rom.load_complete": {
        "ja": "読み込み完了: {count}ステージ",
        "en": "Loaded: {count} stages",
    },
    "main.rom.thumbnail_generating": {
        "ja": "サムネイル生成中...",
        "en": "Generating thumbnails...",
    },
    "main.rom.read_only_suffix": {
        "ja": " (編集不可)",
        "en": " (read-only)",
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
    "main.migration.title": {
        "ja": "データ移行",
        "en": "Data Migration",
    },
    "main.migration.failed.title": {
        "ja": "データ移行失敗",
        "en": "Data Migration Failed",
    },
    "main.migration.unavailable.status": {
        "ja": "データ移行は編集不可ROMを読み込んだ時だけ使えます",
        "en": "Data migration is available only after loading a non-editable ROM.",
    },
    "main.migration.source_prepare_failed": {
        "ja": "移行元データを準備できませんでした。\n{error}",
        "en": "Could not prepare the source data.\n{error}",
    },
    "main.migration.error.source_state": {
        "ja": "データ移行は編集不可ROMを読み込んだ状態で実行してください。",
        "en": "Run data migration after loading a non-editable ROM.",
    },
    "main.migration.error.target_not_ready": {
        "ja": "移行先の編集可能ROMを準備できませんでした。",
        "en": "Could not prepare the editable target ROM.",
    },
    "main.migration.warning.auxiliary_failed": {
        "ja": "L{stage}: 補助情報の一部を移行できませんでした ({error_type})",
        "en": "L{stage}: Some auxiliary data could not be migrated ({error_type})",
    },
    "main.migration.warning.bonus_failed": {
        "ja": "51面ボーナススポットを移行できませんでした ({error_type})",
        "en": "Could not migrate the stage 51 bonus spot ({error_type})",
    },
    "main.migration.target_dialog.title": {
        "ja": "移行先の編集可能ROMを選択",
        "en": "Select Editable Target ROM",
    },
    "main.migration.target_read_failed": {
        "ja": "移行先ROMを読み込めませんでした。\n{error}",
        "en": "Could not load the target ROM.\n{error}",
    },
    "main.migration.target_not_supported": {
        "ja": (
            "移行先にできるROMではありません。\n"
            "確認済みの日本版オリジナルROM、またはこのアプリで保存した編集可能ROMを選んでください。"
        ),
        "en": (
            "This ROM cannot be used as the migration target.\n"
            "Select a verified original Japanese ROM or an editable ROM saved by this app."
        ),
    },
    "main.migration.target_prepared.status": {
        "ja": "移行先ROMを編集可能形式で準備しました",
        "en": "Prepared the target ROM in editable format.",
    },
    "main.migration.target_open_failed": {
        "ja": "移行先ROMを編集可能状態で開けませんでした。",
        "en": "Could not open the target ROM in editable mode.",
    },
    "main.migration.default_source_name": {
        "ja": "編集不可ROM",
        "en": "Non-editable ROM",
    },
    "main.migration.warning_more": {
        "ja": "...ほか{count}件",
        "en": "...and {count} more",
    },
    "main.migration.warning_header": {
        "ja": "\n\n一部補助情報は移行できませんでした:\n",
        "en": "\n\nSome auxiliary data could not be migrated:\n",
    },
    "main.migration.complete.title": {
        "ja": "データ移行完了",
        "en": "Data Migration Complete",
    },
    "main.migration.complete.body": {
        "ja": (
            "{source_name} から {count}/{total} ステージを移行しました。\n"
            "移行後のROMはまだ保存されていません。必要ならROM保存してください。"
            "{warning_text}"
        ),
        "en": (
            "Migrated {count}/{total} stages from {source_name}.\n"
            "The migrated ROM has not been saved yet. Save the ROM if needed."
            "{warning_text}"
        ),
    },
    "main.migration.complete.status": {
        "ja": "データ移行完了: {count}/{total} ステージ",
        "en": "Data migration complete: {count}/{total} stages",
    },
    "main.stage_jump.title": {
        "ja": "ステージ番号ジャンプ",
        "en": "Jump to Stage",
    },
    "main.stage_jump.label": {
        "ja": "ステージ番号:",
        "en": "Stage number:",
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
    "bonus_dialog.title": {
        "ja": "ボーナスステージ (Stage 51) 出現位置編集",
        "en": "Bonus Stage (Stage 51) Spawn Position Editor",
    },
    "bonus_dialog.positions.group": {
        "ja": "出現位置 ({count}箇所)",
        "en": "Spawn Positions ({count})",
    },
    "bonus_dialog.position.tooltip": {
        "ja": "位置{index}: アイテム#{item}を配置",
        "en": "Position {index}: places item #{item}",
    },
    "mirror_dialog.title": {
        "ja": "ミラー詳細設定 - Stage {stage}",
        "en": "Mirror Detail Settings - Stage {stage}",
    },
    "mirror_dialog.ttl.label": {
        "ja": "スポーン敵の生存時間:",
        "en": "Spawned enemy lifetime:",
    },
    "mirror_dialog.ttl.tooltip": {
        "ja": (
            "Saramander / DemonHead 系のスポーン敵に使われます。\n"
            "目安: 約0.5秒 × 値 (例: 16=約8秒、30=約16秒)"
        ),
        "en": (
            "Used for spawned enemies such as Saramander and Demon Head.\n"
            "Guide: about 0.5 seconds x value (for example, 16=about 8 seconds, 30=about 16 seconds)"
        ),
    },
    "mirror_dialog.ttl.seconds": {
        "ja": "約{seconds}秒",
        "en": "about {seconds}s",
    },
    "mirror_dialog.overview.button": {
        "ja": "ミラー出現一覧",
        "en": "Mirror Spawn List",
    },
    "mirror_dialog.overview.tooltip": {
        "ja": "全ステージのミラー敵セットと出現タイミングを読取専用で一覧表示します。",
        "en": "Shows every stage's mirror enemy sets and spawn timing as a read-only list.",
    },
    "mirror_dialog.mirror.group": {
        "ja": "ミラー {mirror}  (位置: {position})",
        "en": "Mirror {mirror}  (Position: {position})",
    },
    "mirror_dialog.schedule.label_html": {
        "ja": (
            "<b>出現タイミング</b> (左から順に時間経過)"
            "　<span style='color:gray;'>※先頭2tickはゲーム側で無視される</span>"
        ),
        "en": (
            "<b>Spawn Timing</b> (time runs left to right) "
            "<span style='color:gray;'>First 2 ticks are ignored by the game</span>"
        ),
    },
    "mirror_dialog.phase2.label": {
        "ja": "Phase 2 (ループ):",
        "en": "Phase 2 (loop):",
    },
    "mirror_dialog.tick.ignored.tooltip": {
        "ja": "tick {tick} (ゲーム側で無視される)",
        "en": "tick {tick} (ignored by the game)",
    },
    "mirror_dialog.all_on.button": {
        "ja": "全ON",
        "en": "All On",
    },
    "mirror_dialog.all_on.tooltip": {
        "ja": "有効tickをすべてONにします。",
        "en": "Turns all valid ticks on.",
    },
    "mirror_dialog.all_off.button": {
        "ja": "全OFF",
        "en": "All Off",
    },
    "mirror_dialog.all_off.tooltip": {
        "ja": "出現タイミングをすべてOFFにします。",
        "en": "Turns all spawn timing off.",
    },
    "mirror_dialog.gap.tooltip": {
        "ja": "tick {start} から、{gap}個空けて出現タイミングをONにします。",
        "en": "Starting from tick {start}, turns timing on after every {gap} skipped ticks.",
    },
    "mirror_dialog.gap.button.1": {
        "ja": "1空け",
        "en": "Skip 1",
    },
    "mirror_dialog.gap.button.2": {
        "ja": "2空け",
        "en": "Skip 2",
    },
    "mirror_dialog.gap.button.3": {
        "ja": "3空け",
        "en": "Skip 3",
    },
    "mirror_dialog.gap.button.4": {
        "ja": "4空け",
        "en": "Skip 4",
    },
    "mirror_dialog.gap.button.5": {
        "ja": "5空け",
        "en": "Skip 5",
    },
    "mirror_dialog.gap.button.6": {
        "ja": "6空け",
        "en": "Skip 6",
    },
    "mirror_overview.title": {
        "ja": "ミラー出現パターン一覧",
        "en": "Mirror Spawn Pattern List",
    },
    "mirror_overview.info": {
        "ja": (
            "全ステージのミラー敵セットと64tick出現パターンを表示します。"
            "X=出現、.=なし、-=ゲーム側で無視される先頭tick。"
        ),
        "en": (
            "Shows mirror enemy sets and 64-tick spawn patterns for every stage. "
            "X=spawn, .=none, -=initial tick ignored by the game."
        ),
    },
    "mirror_overview.column.level": {
        "ja": "Lv",
        "en": "Lv",
    },
    "mirror_overview.column.ttl": {
        "ja": "TTL",
        "en": "TTL",
    },
    "mirror_overview.column.m1_pos": {
        "ja": "M1位置",
        "en": "M1 Pos",
    },
    "mirror_overview.column.m1_enemy": {
        "ja": "M1敵",
        "en": "M1 Enemy",
    },
    "mirror_overview.column.m1_count": {
        "ja": "M1数",
        "en": "M1 Count",
    },
    "mirror_overview.column.m2_pos": {
        "ja": "M2位置",
        "en": "M2 Pos",
    },
    "mirror_overview.column.m2_enemy": {
        "ja": "M2敵",
        "en": "M2 Enemy",
    },
    "mirror_overview.column.m2_count": {
        "ja": "M2数",
        "en": "M2 Count",
    },
    "sprite_viewer.title": {
        "ja": "スプライト/キャラクタービューア",
        "en": "Sprite/Character Viewer",
    },
    "sprite_viewer.mode.label": {
        "ja": "表示モード:",
        "en": "View mode:",
    },
    "sprite_viewer.mode.rom_frames": {
        "ja": "★ROMフレームデータ (全網羅 16x16)",
        "en": "ROM Frame Data (complete 16x16)",
    },
    "sprite_viewer.mode.characters": {
        "ja": "キャラクター (組み立て)",
        "en": "Characters (assembled)",
    },
    "sprite_viewer.mode.raw_chr": {
        "ja": "生CHRタイル (8x8)",
        "en": "Raw CHR Tiles (8x8)",
    },
    "sprite_viewer.chr_bank.label": {
        "ja": "CHRバンク:",
        "en": "CHR bank:",
    },
    "sprite_viewer.palette.label": {
        "ja": "パレット:",
        "en": "Palette:",
    },
    "sprite_viewer.palette.auto_attr": {
        "ja": "attr&3で自動",
        "en": "Auto from attr&3",
    },
    "sprite_viewer.palette.option.0": {
        "ja": "BG #0",
        "en": "BG #0",
    },
    "sprite_viewer.palette.option.1": {
        "ja": "BG #1",
        "en": "BG #1",
    },
    "sprite_viewer.palette.option.2": {
        "ja": "BG #2",
        "en": "BG #2",
    },
    "sprite_viewer.palette.option.3": {
        "ja": "BG #3",
        "en": "BG #3",
    },
    "sprite_viewer.palette.option.4": {
        "ja": "SPR #0 主人公",
        "en": "SPR #0 Dana",
    },
    "sprite_viewer.palette.option.5": {
        "ja": "SPR #1 サラマンダー",
        "en": "SPR #1 Saramander",
    },
    "sprite_viewer.palette.option.6": {
        "ja": "SPR #2 ガーゴイル",
        "en": "SPR #2 Gargoyle",
    },
    "sprite_viewer.palette.option.7": {
        "ja": "SPR #3 ゴブリン",
        "en": "SPR #3 Goblin",
    },
    "sprite_viewer.duplicates.checkbox": {
        "ja": "重複参照も表示",
        "en": "Show duplicate refs",
    },
    "sprite_viewer.duplicates.tooltip": {
        "ja": "同じleft/right/attrを参照するROMフレームも個別に表示",
        "en": "Also shows ROM frames that reference the same left/right/attr separately.",
    },
    "sprite_viewer.zoom.label": {
        "ja": "拡大:",
        "en": "Zoom:",
    },
    "sprite_viewer.category.label": {
        "ja": "カテゴリ:",
        "en": "Category:",
    },
    "sprite_viewer.category.items": {
        "ja": "アイテム",
        "en": "Items",
    },
    "sprite_viewer.category.enemies": {
        "ja": "敵",
        "en": "Enemies",
    },
    "sprite_viewer.category.meta": {
        "ja": "メタ",
        "en": "Meta",
    },
    "sprite_viewer.category.all_metatiles": {
        "ja": "全メタタイル",
        "en": "All Metatiles",
    },
    "sprite_viewer.category.all_tiledefs": {
        "ja": "★全網羅 (全tile_def×全tileset)",
        "en": "Complete (all tile_def x all tileset)",
    },
    "sprite_viewer.tileset.label": {
        "ja": "タイルセット:",
        "en": "Tileset:",
    },
    "sprite_viewer.tileset.all": {
        "ja": "全部(網羅)",
        "en": "All (complete)",
    },
    "sprite_viewer.opaque.checkbox": {
        "ja": "背景不透明",
        "en": "Opaque background",
    },
    "sprite_viewer.bank.label": {
        "ja": "バンク:",
        "en": "Bank:",
    },
    "sprite_viewer.grid.checkbox": {
        "ja": "グリッド線",
        "en": "Grid lines",
    },
    "sprite_viewer.characters.status": {
        "ja": "{count} 枚表示 / tile_def {tile_defs}種 × tileset {tilesets}種 / フィルタなし全網羅可",
        "en": "{count} shown / {tile_defs} tile_def types x {tilesets} tilesets / complete unfiltered view available",
    },
    "sprite_viewer.raw.status": {
        "ja": "Bank {bank}: タイル {first}-{last} / CHR開始 0x{chr_start:X}",
        "en": "Bank {bank}: tiles {first}-{last} / CHR start 0x{chr_start:X}",
    },
    "sprite_viewer.raw.hover": {
        "ja": (
            "Bank {bank}: タイル {tile_no} (0x{tile_no:03X}) / "
            "bank内 {bank_tile} (0x{bank_tile:03X}) / "
            "CHR+0x{chr_offset:04X} / ROM 0x{file_start:X}-0x{file_end:X}"
        ),
        "en": (
            "Bank {bank}: tile {tile_no} (0x{tile_no:03X}) / "
            "in-bank {bank_tile} (0x{bank_tile:03X}) / "
            "CHR+0x{chr_offset:04X} / ROM 0x{file_start:X}-0x{file_end:X}"
        ),
    },
    "sprite_viewer.romframe.tooltip": {
        "ja": "ダブルクリックでこのフレームを16x16ピクセル編集で開く",
        "en": "Double-click this frame to open it in the 16x16 pixel editor.",
    },
    "sprite_viewer.romframe.count.references": {
        "ja": "{count} フレーム参照",
        "en": "{count} frame refs",
    },
    "sprite_viewer.romframe.count.targets": {
        "ja": "{targets} 編集対象 / {references} フレーム参照",
        "en": "{targets} edit targets / {references} frame refs",
    },
    "sprite_viewer.romframe.status": {
        "ja": (
            "{count_text} / $D0E8機構由来 / Bank {bank} / "
            "16x16(8x16スプライト) / ROM直読み・configに依存しない"
        ),
        "en": (
            "{count_text} / from $D0E8 mechanism / Bank {bank} / "
            "16x16 (8x16 sprites) / direct ROM read, independent of config"
        ),
    },
    "stats_dialog.title": {
        "ja": "全ステージ統計 ({count}ステージ)",
        "en": "All Stage Statistics ({count} stages)",
    },
    "stats_dialog.info_html": {
        "ja": (
            "「主要」列はWarp/星座パネル/Solomon's Seal/Pageを集計。「重要アイテム」列は"
            "Origami Swan/Demonhead Coin/"
            "Sphinx/Egyptian Head/Magic Lamp/E-bottle/Tecmo Bunny と、"
            "特殊扱いの Mighty Bomb Jack/Fairy/Fairy Princess を集計(コイン/宝石/"
            "Bell/Scroll/タイマー系などは除外)。「全アイテム」列は"
            "主要/重要アイテム列に出したものを除き、通常/隠し/ブロック内を"
            "区別せずベースアイテム別に集計。「配置敵」=面に置かれた敵"
            "(実数 ×N)、「ミラー敵」=デーモンミラーから出る敵(種類のみ・"
            "無スケジュールのミラーは除外)。「ブロック」=空気以外の通常/特殊"
            "ブロック内訳。<br>"
            "「妖精化」=落下死で妖精化する敵が設定されているステージ。<br>"
            "「理論得点」=配置されているアイテムをすべて取得した場合の取得時得点"
            "(到達可否、残りTIME換算、スコア倍率の副作用は除外)。<br>"
            "セルをダブルクリックでそのステージへジャンプ。"
        ),
        "en": (
            "The Featured column counts Warp, constellation panels, Solomon's Seal, and Page. "
            "The Important Items column counts Origami Swan, Demonhead Coin, Sphinx, Egyptian Head, "
            "Magic Lamp, E-bottle, Tecmo Bunny, and special entities Mighty Bomb Jack, Fairy, "
            "and Fairy Princess. Coins, jewels, Bell, Scroll, timer items, and similar items are excluded. "
            "The All Items column aggregates base items that are not already shown in Featured or Important Items, "
            "without separating normal, hidden, and in-block placement. Placed Enemies means enemies placed on the stage "
            "(actual count xN). Mirror Enemies means enemy types spawned by demon mirrors; unscheduled mirrors are excluded. "
            "Blocks shows the breakdown of non-air normal/special blocks.<br>"
            "Fairy Transform marks stages where an enemy is configured to become a fairy after falling death.<br>"
            "Theoretical Score is the pickup score if all placed items are collected. Reachability, remaining TIME conversion, "
            "and score multiplier side effects are excluded.<br>"
            "Double-click a cell to jump to that stage."
        ),
    },
    "stats_dialog.column.0": {"ja": "Lv", "en": "Lv"},
    "stats_dialog.column.1": {"ja": "通常", "en": "Normal"},
    "stats_dialog.column.2": {"ja": "隠し", "en": "Hidden"},
    "stats_dialog.column.3": {"ja": "in_blk", "en": "in_blk"},
    "stats_dialog.column.4": {"ja": "敵数", "en": "Enemies"},
    "stats_dialog.column.5": {"ja": "タイル", "en": "Tileset"},
    "stats_dialog.column.6": {"ja": "時間減少", "en": "Time Drain"},
    "stats_dialog.column.7": {"ja": "敵寿命\n約0.5秒x値", "en": "Enemy Life\nabout 0.5s x value"},
    "stats_dialog.column.8": {"ja": "鍵", "en": "Key"},
    "stats_dialog.column.9": {"ja": "星座", "en": "Constellation"},
    "stats_dialog.column.10": {"ja": "A禁止", "en": "No A"},
    "stats_dialog.column.11": {"ja": "B禁止", "en": "No B"},
    "stats_dialog.column.12": {"ja": "火リセット", "en": "Fire Reset"},
    "stats_dialog.column.13": {"ja": "鍵敵#", "en": "Key Enemy #"},
    "stats_dialog.column.14": {"ja": "暗闇", "en": "Dark"},
    "stats_dialog.column.15": {"ja": "特殊扉", "en": "Special Door"},
    "stats_dialog.column.16": {"ja": "妖精化", "en": "Fairy Transform"},
    "stats_dialog.column.17": {"ja": "配置敵", "en": "Placed Enemies"},
    "stats_dialog.column.18": {"ja": "ミラー敵", "en": "Mirror Enemies"},
    "stats_dialog.column.19": {"ja": "主要", "en": "Featured"},
    "stats_dialog.column.20": {"ja": "重要アイテム", "en": "Important Items"},
    "stats_dialog.column.21": {"ja": "全アイテム", "en": "All Items"},
    "stats_dialog.column.22": {"ja": "理論得点", "en": "Theoretical Score"},
    "stats_dialog.column.23": {"ja": "ブロック", "en": "Blocks"},
    "stats_dialog.tooltip.featured": {
        "ja": "Warp / 星座パネル / Solomon's Seal / Page を専用表示します。",
        "en": "Shows Warp, constellation panels, Solomon's Seal, and Page separately.",
    },
    "stats_dialog.tooltip.important_items": {
        "ja": (
            "重要アイテム列の枠色:\n"
            "黄 = 隠し / 緑 = ブロック内 / 灰 = 通常\n"
            "右下の数字は同種アイテムの合計数です。"
        ),
        "en": (
            "Important Items border colors:\n"
            "yellow = hidden / green = in block / gray = normal\n"
            "The lower-right number is the total count for the same item type."
        ),
    },
    "stats_dialog.tooltip.all_items": {
        "ja": (
            "全アイテム列は通常/隠し/ブロック内を区別せず、"
            "主要/重要アイテム列に出したものを除いてベースアイテム別に合算します。\n"
            "表示順はピッカー順です。右下の数字は同種アイテムの合計数です。"
        ),
        "en": (
            "All Items aggregates by base item without separating normal, hidden, and in-block placement, "
            "excluding items already shown in Featured or Important Items.\n"
            "Order follows the picker. The lower-right number is the total count for the same item type."
        ),
    },
    "stats_dialog.tooltip.blocks": {
        "ja": (
            "空気以外の通常/特殊ブロック内訳です。\n"
            "茶/白/壊白/透壊/通白/通茶/透固/固茶 などを集計します。"
        ),
        "en": (
            "Breakdown of normal/special blocks except air.\n"
            "Counts brown, white, breakable white, transparent breakable, passable white/brown, transparent solid, solid brown, and similar blocks."
        ),
    },
    "stats_dialog.tooltip.score": {
        "ja": (
            "配置されているアイテムをすべて取った場合の取得時得点です。\n"
            "到達可否、残りTIMEのクリア時換算、スコア倍率の副作用は含めません。"
        ),
        "en": (
            "Pickup score if all placed items are collected.\n"
            "Reachability, remaining TIME conversion at clear, and score multiplier side effects are not included."
        ),
    },
    "stats_dialog.csv.button": {
        "ja": "CSV出力",
        "en": "Export CSV",
    },
    "stats_dialog.csv.save_title": {
        "ja": "CSV出力先",
        "en": "Export CSV",
    },
    "stats_dialog.csv.complete": {
        "ja": "CSV出力完了\n{path}",
        "en": "CSV export complete.\n{path}",
    },
    "stats_dialog.csv.failed.title": {
        "ja": "CSV出力失敗",
        "en": "CSV Export Failed",
    },
    "stats_dialog.count_part.normal": {
        "ja": "通{count}",
        "en": "N{count}",
    },
    "stats_dialog.count_part.hidden": {
        "ja": "隠{count}",
        "en": "H{count}",
    },
    "stats_dialog.count_part.in_block": {
        "ja": "内{count}",
        "en": "B{count}",
    },
    "stats_dialog.key_state.normal": {
        "ja": "通常",
        "en": "Normal",
    },
    "stats_dialog.key_state.removed": {
        "ja": "削除",
        "en": "Removed",
    },
    "stats_dialog.key_state.hidden": {
        "ja": "hidden",
        "en": "Hidden",
    },
    "stats_dialog.key_state.in_block": {
        "ja": "in_block",
        "en": "In Block",
    },
    "stats_dialog.key_state.visible_in_block": {
        "ja": "visible_in_block",
        "en": "Visible In Block",
    },
    "stats_dialog.key_state.white_in_block": {
        "ja": "white_in_block",
        "en": "White In Block",
    },
    "stats_dialog.door_state.removed": {
        "ja": "削除",
        "en": "Removed",
    },
    "stats_dialog.door_state.hidden": {
        "ja": "隠",
        "en": "Hidden",
    },
    "stats_dialog.door_state.in_block": {
        "ja": "内",
        "en": "In Block",
    },
    "stats_dialog.door_state.white_in_block": {
        "ja": "白内",
        "en": "White In Block",
    },
    "stats_dialog.total": {
        "ja": "合計",
        "en": "Total",
    },
    "stats_dialog.jump.status": {
        "ja": "L{level} に移動",
        "en": "Moved to L{level}",
    },
    "special_process_dialog.title": {
        "ja": "特殊処理ビューア (Phase 1 - 読込専用)",
        "en": "Special Process Viewer (Phase 1 - Read Only)",
    },
    "special_process_dialog.region_html": {
        "ja": "<b>リージョン:</b> {region}",
        "en": "<b>Region:</b> {region}",
    },
    "special_process_dialog.unsupported_html": {
        "ja": (
            "<span style='color:#ef4444'><b>⚠ 未対応リージョン</b>: "
            "このリージョンの特殊処理テーブル位置は未確認です。</span>"
        ),
        "en": (
            "<span style='color:#ef4444'><b>Unsupported region</b>: "
            "The special-process table location for this region is not confirmed.</span>"
        ),
    },
    "special_process_dialog.dispatch_html": {
        "ja": "<b>ディスパッチテーブル:</b> 0x{offset:04X}",
        "en": "<b>Dispatch table:</b> 0x{offset:04X}",
    },
    "special_process_dialog.source_html": {
        "ja": (
            "<span style='color:#888;font-size:11px'>"
            "出典: BESK (Binary Editor for Solomon's Key) を逆コンパイル + JP/USA ROM 直接検証"
            "</span>"
        ),
        "en": (
            "<span style='color:#888;font-size:11px'>"
            "Source: decompiled BESK (Binary Editor for Solomon's Key) plus direct JP/USA ROM verification"
            "</span>"
        ),
    },
    "special_process_dialog.bytes.group": {
        "ja": "生バイト (ROM)",
        "en": "Raw Bytes (ROM)",
    },
    "special_process_dialog.asm.group": {
        "ja": "擬似アセンブラ + 注釈",
        "en": "Pseudo Assembly + Notes",
    },
    "special_process_dialog.level.unsupported": {
        "ja": "L{level:2d}  (未対応)",
        "en": "L{level:2d}  (unsupported)",
    },
    "special_process_dialog.kind.short": {
        "ja": "短い",
        "en": "short",
    },
    "special_process_dialog.kind.medium": {
        "ja": "中",
        "en": "medium",
    },
    "special_process_dialog.kind.large": {
        "ja": "★大規模",
        "en": "large",
    },
    "special_process_dialog.unsupported_text": {
        "ja": "(リージョン未対応のため表示できません)",
        "en": "(Cannot display because this region is unsupported)",
    },
    "special_process_dialog.bytes.stage_comment": {
        "ja": "; Stage {stage} 特殊処理",
        "en": "; Stage {stage} special process",
    },
    "keyboard_map.category.navigation": {
        "ja": "ナビゲーション",
        "en": "Navigation",
    },
    "keyboard_map.category.display": {
        "ja": "表示切替",
        "en": "Display",
    },
    "keyboard_map.category.file_op": {
        "ja": "ファイル操作",
        "en": "File",
    },
    "keyboard_map.category.ui": {
        "ja": "ブラウザ/UI",
        "en": "Browser/UI",
    },
    "keyboard_map.category.system": {
        "ja": "システム",
        "en": "System",
    },
    "keyboard_map.category.other": {
        "ja": "その他",
        "en": "Other",
    },
    "keyboard_map.numpad.suffix": {
        "ja": " [テンキー]",
        "en": " [numpad]",
    },
    "keyboard_map.font.label": {
        "ja": "フォント:",
        "en": "Font:",
    },
    "keyboard_map.size.label": {
        "ja": "サイズ:",
        "en": "Size:",
    },
    "keyboard_map.save_png.button": {
        "ja": "PNG保存",
        "en": "Save PNG",
    },
    "keyboard_map.notes.title": {
        "ja": "操作メモ",
        "en": "Notes",
    },
    "keyboard_map.save_png.folder_title": {
        "ja": "保存先フォルダを選択",
        "en": "Select Save Folder",
    },
    "keyboard_map.save_png.complete.title": {
        "ja": "保存完了",
        "en": "Save Complete",
    },
    "keyboard_map.save_png.complete.body": {
        "ja": "保存しました:\n{path}",
        "en": "Saved:\n{path}",
    },
    "keyboard_map.default_title": {
        "ja": "ショートカットMAP",
        "en": "Shortcut Map",
    },
    "common.complete": {
        "ja": "完了",
        "en": "Complete",
    },
    "common.file_filter.csv": {
        "ja": "CSV files (*.csv);;All files (*)",
        "en": "CSV files (*.csv);;All files (*)",
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
