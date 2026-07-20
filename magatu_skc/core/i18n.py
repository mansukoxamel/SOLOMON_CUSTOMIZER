"""Small runtime language registry for UI text.

This module intentionally keeps translation state outside save data, XML
schemas, ROM metadata, and other stable internal keys.
"""
from functools import lru_cache

DEFAULT_LANGUAGE = "ja"
LANGUAGE_OPTIONS = (
    ("ja", "日本語"),
    ("en", "English"),
)
SUPPORTED_LANGUAGES = {key for key, _label in LANGUAGE_OPTIONS}

_current_language = DEFAULT_LANGUAGE

_TRANSLATIONS = {
    "hack_dialog.spark_ball_variant.hint24": {
        "ja": "停止型($C0-$C7)は停止ポイント、透明型($C8-$CF)は透明化周期、停止後反転型($D0-$D7)は反転ポイントを個別に設定します。",
        "en": "Configure pause points for $C0-$C7, the transparency cycle for $C8-$CF, and reversal points for $D0-$D7 independently.",
    },
    "hack_dialog.spark_ball_variant.reverse_digits.label": {
        "ja": "反転するLIFE百の位:",
        "en": "Reverse on LIFE hundreds digit:",
    },
    "hack_dialog.spark_ball_variant.max_reverse_digits": {
        "ja": "反転するLIFE百の位は最大4個までです。",
        "en": "Select at most four LIFE hundreds digits for reversal.",
    },
    "hack_dialog.setting.spark_ball_reverse": {
        "ja": "強化スパークボール反転",
        "en": "Enhanced Spark Ball reversal",
    },
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
    "settings.favorites_visible.label": {
        "ja": "お気に入り欄:",
        "en": "Favorites bar:",
    },
    "settings.favorites_visible.checkbox": {
        "ja": "表示する",
        "en": "Show",
    },
    "settings.favorites_visible.tooltip": {
        "ja": "OFFにすると通常ステージのピッカー下部にあるお気に入り欄を隠します。登録内容とショートカットは保持されます。",
        "en": "When off, hides the favorites bar below the picker on normal stages. Saved favorites and shortcuts are preserved.",
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
    "settings.binary_editor.path.label": {"ja": "バイナリエディタ:", "en": "Binary editor:"},
    "settings.binary_editor.path.placeholder": {
        "ja": "例: D:/tools/MAGATU_BINARY_EDITOR/MAGATU_BINARY_EDITOR.py",
        "en": "Example: D:/tools/MAGATU_BINARY_EDITOR/MAGATU_BINARY_EDITOR.py",
    },
    "settings.binary_editor.open_title": {"ja": "バイナリエディタを選択", "en": "Select Binary Editor"},
    "settings.binary_editor.file_filter": {
        "ja": "Applications / Python (*.exe *.py *.pyw);;All files (*)",
        "en": "Applications / Python (*.exe *.py *.pyw);;All files (*)",
    },
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
    "shortcut.label.help": {"ja": "ショートカットヘルプ", "en": "Shortcut Help"},
    "shortcut.label.open_rom": {"ja": "ROMを開く", "en": "Open ROM"},
    "shortcut.label.save_rom": {"ja": "ROM保存", "en": "Save ROM"},
    "shortcut.label.save_stage_png": {
        "ja": "現在ステージのステージデータPNG保存",
        "en": "Save Current Stage Data PNG",
    },
    "shortcut.label.stage_jump": {"ja": "ステージ番号ジャンプ", "en": "Jump to Stage Number"},
    "shortcut.label.show_stats": {"ja": "全ステージ統計", "en": "All-Stage Statistics"},
    "shortcut.label.open_binary_editor": {"ja": "バイナリエディタで開く", "en": "Open in Binary Editor"},
    "shortcut.label.test_play": {"ja": "テストプレイ", "en": "Test Play"},
    "shortcut.label.stage_prev": {"ja": "前のステージ", "en": "Previous Stage"},
    "shortcut.label.stage_next": {"ja": "次のステージ", "en": "Next Stage"},
    "shortcut.label.stage_compare_edit_start": {
        "ja": "比較編集開始",
        "en": "Start Compare Editing",
    },
    "shortcut.label.stage_compare_edit_orientation": {
        "ja": "比較編集の縦横切替",
        "en": "Toggle Compare Orientation",
    },
    "shortcut.label.settings": {"ja": "設定", "en": "Settings"},
    "shortcut.label.grid": {"ja": "グリッド表示切替", "en": "Toggle Grid"},
    "shortcut.label.undo": {"ja": "Undo", "en": "Undo"},
    "shortcut.label.redo": {"ja": "Redo", "en": "Redo"},
    "shortcut.label.redo_alt": {"ja": "Redo代替", "en": "Alternate Redo"},
    "shortcut.label.select_all": {"ja": "編集エリア全体を選択", "en": "Select Entire Edit Area"},
    "shortcut.label.clear_selection": {"ja": "選択解除", "en": "Clear Selection"},
    "shortcut.label.copy_selection": {"ja": "コピー", "en": "Copy"},
    "shortcut.label.paste_selection": {"ja": "ペースト", "en": "Paste"},
    "shortcut.label.cut_selection": {"ja": "切り取り", "en": "Cut"},
    "shortcut.label.item_replace": {"ja": "オブジェクト一括置換", "en": "Bulk Replace Objects"},
    "shortcut.label.item_flag_toggle": {
        "ja": "ホバー位置のアイテム状態切替",
        "en": "Cycle Hovered Item State",
    },
    "shortcut.label.item_flag_toggle_reverse": {
        "ja": "ホバー位置のアイテム状態逆切替",
        "en": "Cycle Hovered Item State Backward",
    },
    "shortcut.label.delete_hover_or_selection": {
        "ja": "ホバー/選択範囲を削除",
        "en": "Delete Hovered Cell or Selection",
    },
    "shortcut.label.delete_hover_or_selection_alt": {
        "ja": "ホバー/選択範囲を削除 代替",
        "en": "Delete Hovered Cell or Selection (Alternate)",
    },
    "shortcut.label.clear_selection_escape": {"ja": "選択解除(Esc)", "en": "Clear Selection (Esc)"},
    "shortcut.label.flip_horizontal": {"ja": "選択範囲を左右反転", "en": "Flip Selection Horizontally"},
    "shortcut.label.flip_vertical": {"ja": "選択範囲を上下反転", "en": "Flip Selection Vertically"},
    "shortcut.label.favorite_1": {"ja": "お気に入りスロット1", "en": "Favorite Slot 1"},
    "shortcut.label.favorite_2": {"ja": "お気に入りスロット2", "en": "Favorite Slot 2"},
    "shortcut.label.favorite_3": {"ja": "お気に入りスロット3", "en": "Favorite Slot 3"},
    "shortcut.label.favorite_4": {"ja": "お気に入りスロット4", "en": "Favorite Slot 4"},
    "shortcut.label.favorite_5": {"ja": "お気に入りスロット5", "en": "Favorite Slot 5"},
    "shortcut.label.favorite_6": {"ja": "お気に入りスロット6", "en": "Favorite Slot 6"},
    "shortcut.label.favorite_7": {"ja": "お気に入りスロット7", "en": "Favorite Slot 7"},
    "shortcut.label.favorite_8": {"ja": "お気に入りスロット8", "en": "Favorite Slot 8"},
    "shortcut.label.favorite_9": {"ja": "お気に入りスロット9", "en": "Favorite Slot 9"},
    "shortcut.label.favorite_0": {"ja": "お気に入りスロット0", "en": "Favorite Slot 0"},
    "shortcut.label.hover_enemy_left": {"ja": "ホバー敵を左向きに変更", "en": "Face Hovered Enemy Left"},
    "shortcut.label.hover_enemy_right": {"ja": "ホバー敵を右向きに変更", "en": "Face Hovered Enemy Right"},
    "shortcut.label.hover_enemy_up": {"ja": "ホバー敵を上向きに変更", "en": "Face Hovered Enemy Up"},
    "shortcut.label.hover_enemy_down": {"ja": "ホバー敵を下向きに変更", "en": "Face Hovered Enemy Down"},
    "shortcut.label.hover_enemy_speed": {"ja": "ホバー敵スピード循環", "en": "Cycle Hovered Enemy Speed"},
    "shortcut.label.hover_enemy_enhance": {
        "ja": "ホバー敵の強化/別版切替",
        "en": "Toggle Hovered Enemy Enhancement/Variant",
    },
    "shortcut.label.hover_info": {"ja": "ホバー情報表示切替", "en": "Toggle Hover Info"},
    "shortcut.label.hover_item_normal": {"ja": "ホバー位置を通常に変更", "en": "Set Hovered Item to Normal"},
    "shortcut.label.hover_item_hidden": {"ja": "ホバー位置を隠しに変更", "en": "Set Hovered Item to Hidden"},
    "shortcut.label.hover_item_in_block": {"ja": "ホバー位置をブロック内に変更", "en": "Set Hovered Item In Block"},
    "shortcut.label.hover_item_white_in_block": {
        "ja": "ホバー位置を白ブロック内に変更",
        "en": "Set Hovered Item In White Block",
    },
    "shortcut.label.hover_item_visible_in_block": {
        "ja": "ホバー位置を透明ブロック内に変更",
        "en": "Set Hovered Item In Transparent Block",
    },
    "shortcut.label.hover_item_cracked_in_block": {
        "ja": "ホバー位置をひび割れブロック内に変更",
        "en": "Set Hovered Item In Cracked Block",
    },
    "settings.color.choose": {"ja": "色選択...", "en": "Choose Color..."},
    "settings.marker_color.dialog_title": {"ja": "マーカー色", "en": "Marker Color"},
    "common.browse": {"ja": "参照...", "en": "Browse..."},
    "common.add": {"ja": "追加", "en": "Add"},
    "common.delete": {"ja": "削除", "en": "Delete"},
    "common.clear": {"ja": "クリア", "en": "Clear"},
    "common.file_filter.images": {
        "ja": "Images (*.png *.ico *.jpg *.bmp);;All files (*)",
        "en": "Images (*.png *.ico *.jpg *.bmp);;All files (*)",
    },
    "common.file_filter.executables": {
        "ja": "Executables (*.exe);;All files (*)",
        "en": "Executables (*.exe);;All files (*)",
    },
    "config.load_error.title": {"ja": "設定ファイルを読み込めません", "en": "Could not load settings"},
    "config.load_error.message": {
        "ja": "設定ファイルのJSON構文エラーのため、今回は既定値で起動します。\n\nファイル: {path}\n行: {line} / 列: {column}\n\n元の設定ファイルを守るため、この起動中は設定ファイルを上書き保存しません。\nファイルを修正してからアプリを再起動してください。",
        "en": "The settings JSON has a syntax error, so the app will start with defaults for this session.\n\nFile: {path}\nLine: {line} / Column: {column}\n\nTo protect the original settings file, this session will not overwrite it.\nFix the file and restart the app.",
    },
    "element_picker.slot.empty": {"ja": "スロット{slot}: 空", "en": "Slot {slot}: empty"},
    "element_picker.slot.value": {"ja": "スロット{slot}: {text}", "en": "Slot {slot}: {text}"},
    "element_picker.mirror_enemies.html": {"ja": "<small>ミラー出現敵</small>", "en": "<small>Mirror Enemies</small>"},
    "element_picker.mirror_enemies.tooltip": {
        "ja": "ピッカーからD&Dで登録 / Delで削除",
        "en": "Drop from the picker to register / Del to delete",
    },
    "element_picker.toggle.button": {"ja": "切替", "en": "Toggle"},
    "element_picker.mirror_disabled.tooltip": {
        "ja": "ミラー詳細設定の出現タイミングが全OFFのため、この敵セットは出現しません。",
        "en": "This enemy set will not spawn because all timing is off in mirror detail settings.",
    },
    "element_picker.mirror_toggle.tooltip": {
        "ja": "M{mirror} の出現状態を切り替えます。",
        "en": "Toggle the spawn state for M{mirror}.",
    },
    "element_picker.favorite.slot.empty": {
        "ja": "スロット {key}: 空 (D&Dで登録)",
        "en": "Slot {key}: empty (drop to register)",
    },
    "element_picker.favorite.slot.value": {
        "ja": "スロット {key}: {text}",
        "en": "Slot {key}: {text}",
    },
    "element_picker.bonus.slot.empty": {"ja": "スロット#{slot}: 空", "en": "Slot #{slot}: empty"},
    "element_picker.item_state.group": {"ja": "アイテム状態", "en": "Item State"},
    "element_picker.item_state.normal": {"ja": "通常", "en": "Normal"},
    "element_picker.item_state.hidden": {"ja": "隠し", "en": "Hidden"},
    "element_picker.item_state.in_block.short": {"ja": "BL内", "en": "In BL"},
    "element_picker.item_state.white_in_block.short": {"ja": "白BL", "en": "White BL"},
    "element_picker.item_state.visible_in_block.short": {"ja": "透BL", "en": "Visible BL"},
    "element_picker.item_state.cracked_in_block.short": {"ja": "ひびBL", "en": "Cracked BL"},
    "element_picker.item_state.in_block": {"ja": "ブロック内", "en": "In Block"},
    "element_picker.item_state.white_in_block": {"ja": "白ブロック内", "en": "In White Block"},
    "element_picker.item_state.visible_in_block": {"ja": "透明ブロック内", "en": "In Visible Block"},
    "element_picker.item_state.cracked_in_block": {"ja": "ひび割れブロック内", "en": "In Cracked Block"},
    "element_picker.enemy_speed.group": {"ja": "敵スピード", "en": "Enemy Speed"},
    "element_picker.category.blocks": {"ja": "ブロック", "en": "Blocks"},
    "element_picker.category.meta_items": {"ja": "メタアイテム", "en": "Meta Items"},
    "element_picker.category.items": {"ja": "アイテム", "en": "Items"},
    "element_picker.category.monsters": {"ja": "モンスター", "en": "Monsters"},
    "element_picker.favorites.html": {"ja": "<small>お気に入り</small>", "en": "<small>Favorites</small>"},
    "element_picker.favorites.tooltip": {
        "ja": "D&Dで登録 / 1〜0キーで選択 / Delで削除",
        "en": "Drop to register / press 1-0 to select / Del to delete",
    },
    "element_picker.bonus_items.html": {
        "ja": "<small>ボーナスステージ アイテム16種 (ピッカーからD&Dで入替)</small>",
        "en": "<small>Bonus Stage 16 Items (drop from picker to replace)</small>",
    },
    "element_picker.block.none": {"ja": "消去 (空白)", "en": "Erase (empty)"},
    "element_picker.block.brown": {"ja": "茶色ブロック (壊せる)", "en": "Brown Block (breakable)"},
    "element_picker.block.cracked": {"ja": "ひび割れブロック", "en": "Cracked Block"},
    "element_picker.block.white": {"ja": "白ブロック (壊せない)", "en": "White Block (solid)"},
    "element_picker.block.breakable_white": {"ja": "壊せる白ブロック", "en": "Breakable White Block"},
    "element_picker.block.invisible_breakable": {"ja": "透明な茶色ブロック", "en": "Invisible Brown Block"},
    "element_picker.block.passable_white": {"ja": "すり抜ける白ブロック", "en": "Passable White Block"},
    "element_picker.block.invisible_solid": {"ja": "透明な白ブロック", "en": "Invisible White Block"},
    "element_picker.block.passable_brown": {"ja": "すり抜ける茶色ブロック", "en": "Passable Brown Block"},
    "element_picker.block.solid_brown": {"ja": "壊せない茶色ブロック", "en": "Solid Brown Block"},
    "element_picker.meta.start": {"ja": "プレイヤースタート", "en": "Player Start"},
    "element_picker.meta.key": {"ja": "鍵", "en": "Key"},
    "element_picker.meta.door": {"ja": "扉", "en": "Door"},
    "element_picker.meta.mirror1": {"ja": "ミラー1 (Spawn1)", "en": "Mirror 1 (Spawn1)"},
    "element_picker.meta.mirror2": {"ja": "ミラー2 (Spawn2)", "en": "Mirror 2 (Spawn2)"},
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
        "ja": "Dragon s2 / Goblin s1",
        "en": "Dragon s2 / Goblin s1",
    },
    "enemy_drop.users.golem2_gargoyle1": {
        "ja": "Goblin s2 / Gargoyle s1",
        "en": "Goblin s2 / Gargoyle s1",
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
    "main.status.ready": {
        "ja": "準備完了 (F1: ヘルプ / F9: 設定)",
        "en": "Ready (F1: Help / F9: Settings)",
    },
    "main.enemy_count.tooltip": {
        "ja": "敵配置数 0/15",
        "en": "Enemy placements 0/15",
    },
    "main.enemy_count.tooltip_count": {
        "ja": "敵配置数 {count}/{maximum}",
        "en": "Enemy placements {count}/{maximum}",
    },
    "main.enemy_count.tooltip_key": {
        "ja": "鍵持ち敵: #{number}",
        "en": "Key enemy: #{number}",
    },
    "main.enemy_count.tooltip_fairy": {
        "ja": "落下死で妖精化: #{number}",
        "en": "Fairy on fall death: #{number}",
    },
    "main.file.action.open_another": {
        "ja": "別のROMを開きます",
        "en": "Another ROM will be opened",
    },
    "main.file.action.open_dropped": {
        "ja": "ドロップされたROMを開きます",
        "en": "The dropped ROM will be opened",
    },
    "main.file.action.load_another": {
        "ja": "別のROMを読み込みます",
        "en": "Another ROM will be loaded",
    },
    "main.file.action.open_history": {
        "ja": "履歴からROM/作業状態を開きます",
        "en": "A ROM/work state will be opened from history",
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
        "ja": "タイトル画面の配置(nametable)・色区分(attribute)・絵(CHR bank3)・文字・キャラクター・パレットを編集します。",
        "en": "Edit the title screen layout (nametable), color groups (attributes), graphics (CHR bank3), text, characters, and palette.",
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
    "main.tools.image_block_grid": {
        "ja": "画像からブロック配置…",
        "en": "Place Blocks from Image…",
    },
    "main.tools.image_block_grid.tooltip": {
        "ja": "画像を15×12の空気・茶壁・白壁・ひび壁へ変換し、現在のステージへ配置します。",
        "en": "Convert an image into a 15x12 grid of air, brown, white, and cracked blocks and apply it to the current stage.",
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
        "ja": "ファイアリセットモード",
        "en": "Fire Reset Mode",
    },
    "main.stage.fire_reset.tooltip": {
        "ja": "この面を開始した時に、前の面から持ち越したファイヤー/スーパーの所持を0にします。",
        "en": "When this stage starts, reset fire/super fire carried over from the previous stage.",
    },
    "main.stage.warp_mirror": {
        "ja": "ワープミラーモード",
        "en": "Warp Mirror Mode",
    },
    "main.stage.warp_mirror.tooltip": {
        "ja": "この面の鏡に触れた時、もう一方の鏡へワープします。",
        "en": "When Dana touches a mirror in this stage, warp to the other mirror.",
    },
    "main.stage.enemy_clear_key_open": {
        "ja": "オールキルモード",
        "en": "Kill-All Mode",
    },
    "main.stage.enemy_clear_key_open.tooltip": {
        "ja": "この面で敵が全滅すると、鍵取得と同じ演出で扉がオープンします。",
        "en": "When all enemies are defeated in this stage, the door opens with the same effect as picking up the key.",
    },
    "main.status.enemy_clear_key_open_blocked": {
        "ja": "オールキルモードは、画面上に初期配置敵が1体以上必要です",
        "en": "Kill-All Mode requires at least one initially placed enemy on the screen.",
    },
    "main.status.enemy_clear_key_open_key_enemy_blocked": {
        "ja": "オールキルモードと鍵持ち敵は同時にONにできません",
        "en": "Kill-All Mode and a key-carrying enemy cannot both be enabled.",
    },
    "main.status.enemy_clear_key_open_apply_all_skipped": {
        "ja": "オールキルモードを適用しました（{count}面変更 / 条件不成立 {skipped}面はOFF）",
        "en": "Applied Kill-All Mode ({count} changed / {skipped} invalid stages were turned off).",
    },
    "main.stage.restrictions.apply_one_all": {
        "ja": "現在の状態を全53面に適用（{name}）",
        "en": "Apply current state to all 53 stages ({name})",
    },
    "main.stage.restrictions.apply_all_no_change": {
        "ja": "全53面はすでに同じ設定です",
        "en": "All 53 stages already have the same setting.",
    },
    "main.stage.restrictions.apply_all_done": {
        "ja": "{name}を全53面へ適用しました（{count}面変更 / Ctrl+Zで戻せます）",
        "en": "Applied {name} to all 53 stages ({count} changed / Ctrl+Z to undo).",
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
    "main.stage.constellation_locked": {
        "ja": "星座固定",
        "en": "Constellation locked",
    },
    "main.stage_info.title": {
        "ja": "ステージ {stage:02d}",
        "en": "Stage {stage:02d}",
    },
    "main.stage_info.item_enemy": {
        "ja": "アイテム: {items}個 / 敵: {enemies}体",
        "en": "Items: {items} / Enemies: {enemies}",
    },
    "main.stage_info.key_door": {
        "ja": "鍵: {key} / 扉: {door}",
        "en": "Key: {key} / Door: {door}",
    },
    "main.stage_info.mirrors": {
        "ja": "ミラー1: {mirror1} / ミラー2: {mirror2}",
        "en": "Mirror 1: {mirror1} / Mirror 2: {mirror2}",
    },
    "main.hover.item_fallback": {"ja": "item 0x{code:02X}", "en": "Item 0x{code:02X}"},
    "main.hover.enemy_fallback": {"ja": "enemy 0x{code:02X}", "en": "Enemy 0x{code:02X}"},
    "main.hover.item": {
        "ja": "アイテム:{code} {desc}{tag}",
        "en": "Item: {code} {desc}{tag}",
    },
    "main.hover.enemy": {
        "ja": "敵#{number}:{desc}",
        "en": "Enemy #{number}: {desc}",
    },
    "main.hover.popup.enemy": {
        "ja": "敵#{number} ID 0x{code:02X}: {desc}{suffix}",
        "en": "Enemy #{number} ID 0x{code:02X}: {desc}{suffix}",
    },
    "main.hover.popup.meta_with_state": {
        "ja": "{name} [{state}]",
        "en": "{name} [{state}]",
    },
    "main.hover.meta.start": {"ja": "スタート", "en": "Start"},
    "main.hover.meta.key": {"ja": "鍵", "en": "Key"},
    "main.hover.meta.key_state": {"ja": "鍵:{state}", "en": "Key: {state}"},
    "main.hover.meta.door": {"ja": "扉", "en": "Door"},
    "main.hover.meta.door_state": {"ja": "扉:{state}", "en": "Door: {state}"},
    "main.hover.meta.mirror": {"ja": "ミラー{number}", "en": "Mirror {number}"},
    "main.hover.meta.constellation": {"ja": "星座:{name}", "en": "Constellation: {name}"},
    "main.hover.meta.solomon_seal": {"ja": "ソロモンの紋章", "en": "Solomon's Seal"},
    "main.hover.block.none": {"ja": "空白", "en": "Empty"},
    "main.hover.block.passable_brown": {"ja": "すり抜ける茶色ブロック", "en": "Passable brown block"},
    "main.hover.block.solid_brown": {"ja": "壊せない茶色ブロック", "en": "Solid brown block"},
    "main.hover.block.cracked": {"ja": "ひび割れブロック", "en": "Cracked block"},
    "main.hover.block.brown": {"ja": "茶色ブロック", "en": "Brown block"},
    "main.hover.block.breakable_white": {"ja": "壊せる白ブロック", "en": "Breakable white block"},
    "main.hover.block.passable_white": {"ja": "すり抜ける白ブロック", "en": "Passable white block"},
    "main.hover.block.white": {"ja": "白ブロック", "en": "White block"},
    "main.hover.block.invisible_breakable": {"ja": "壊せる透明ブロック", "en": "Breakable invisible block"},
    "main.hover.block.invisible_solid": {"ja": "壊せない透明ブロック", "en": "Solid invisible block"},
    "main.hover.key_state.current": {"ja": "ホバー位置の鍵状態: {state}", "en": "Hovered key state: {state}"},
    "main.hover.key_state.changed": {"ja": "ホバー位置の鍵状態を{state}に変更", "en": "Changed hovered key state to {state}"},
    "main.hover.door_state.current": {"ja": "ホバー位置の扉状態: {state}", "en": "Hovered door state: {state}"},
    "main.hover.door_state.changed": {"ja": "ホバー位置の扉状態を{state}に変更", "en": "Changed hovered door state to {state}"},
    "main.hover.door_state.cracked_blocked": {"ja": "扉はひび割れブロック内状態にできません", "en": "Doors cannot be set to the in-cracked-block state."},
    "main.hover.demon_mirror.hidden_item_exists": {"ja": "デーモンミラー上の隠しアイテムは設定済みです", "en": "A hidden item is already set on the demon mirror."},
    "main.hover.demon_mirror.hidden_item_action": {"ja": "デーモンミラー上に隠しアイテム 0x48 を{action}", "en": "{action} hidden item 0x48 on the demon mirror"},
    "main.hover.action.changed": {"ja": "変更", "en": "Changed"},
    "main.hover.action.added": {"ja": "追加", "en": "Added"},
    "main.hover.item_state.current": {"ja": "ホバー位置のアイテム状態: {state}", "en": "Hovered item state: {state}"},
    "main.hover.item_state.changed": {"ja": "ホバー位置のアイテム状態を{state}に変更", "en": "Changed hovered item state to {state}"},
    "main.hover.item_state.removed_backing": {"ja": "（元ブロックも削除）", "en": " (backing block also removed)"},
    "main.hover.item_state.no_target": {"ja": "ホバー位置に状態変更できるアイテム/鍵/扉がありません", "en": "There is no item/key/door at the hovered position whose state can be changed."},
    "main.hover.item_state.visible_blocked": {"ja": "このアイテムは透明ブロック内に入れられません: 0x{code:02X}", "en": "This item cannot be placed inside a visible block: 0x{code:02X}"},
    "main.hover.item_state.cracked_blocked": {"ja": "このアイテムはひび割れブロック内に入れられません: 0x{code:02X}", "en": "This item cannot be placed inside a cracked block: 0x{code:02X}"},
    "main.hover.item_state.white_blocked": {"ja": "このアイテムは白い壊せるブロック内に入れられません: 0x{code:02X}", "en": "This item cannot be placed inside a breakable white block: 0x{code:02X}"},
    "main.hover.popup.on": {"ja": "ホバー情報ポップアップ: ON", "en": "Hover info popup: ON"},
    "main.hover.popup.off": {"ja": "ホバー情報ポップアップ: OFF", "en": "Hover info popup: OFF"},
    "main.hover.enemy_speed.unsupported": {"ja": "この敵はスピード変更に対応していません", "en": "This enemy does not support speed changes."},
    "main.hover.enemy_speed.current": {"ja": "この敵はSP{speed}です", "en": "This enemy is SP{speed}."},
    "main.hover.enemy_speed.changed": {"ja": "ホバー位置の敵スピードをSP{speed}へ変更: {desc}", "en": "Changed hovered enemy speed to SP{speed}: {desc}"},
    "main.hover.enemy_enhance.unsupported": {"ja": "この敵は強化/別版切替に対応していません", "en": "This enemy does not support enhanced/alternate variant switching."},
    "main.hover.enemy_enhance.no_more": {"ja": "この敵はこれ以上切り替えできません", "en": "This enemy has no further variant to switch to."},
    "main.hover.enemy_enhance.changed": {"ja": "ホバー位置の敵を切替: {desc}", "en": "Switched hovered enemy: {desc}"},
    "main.hover.direction.left": {"ja": "左", "en": "left"},
    "main.hover.direction.right": {"ja": "右", "en": "right"},
    "main.hover.direction.up": {"ja": "上", "en": "up"},
    "main.hover.direction.down": {"ja": "下", "en": "down"},
    "main.hover.enemy_direction.unsupported": {"ja": "この敵は{direction}向きに変更できません", "en": "This enemy cannot face {direction}."},
    "main.hover.enemy_direction.current": {"ja": "この敵はすでに{direction}向きです", "en": "This enemy is already facing {direction}."},
    "main.hover.enemy_direction.changed": {"ja": "ホバー位置の敵を{direction}向きに変更: {desc}", "en": "Changed hovered enemy to face {direction}: {desc}"},
    "main.status.auto_key_in_block": {"ja": "鍵をブロック内状態に自動変換 {tile}", "en": "Auto-converted key to in-block state {tile}"},
    "main.status.auto_door_in_block": {"ja": "扉をブロック内状態に自動変換 {tile}", "en": "Auto-converted door to in-block state {tile}"},
    "main.status.auto_item_in_block": {"ja": "アイテムを in_block フラグ付きに自動変換 {tile}", "en": "Auto-converted item with in_block flag {tile}"},
    "main.status.auto_item_cracked": {"ja": "アイテムをひび割れブロック内に自動変換 {tile}", "en": "Auto-converted item into cracked block {tile}"},
    "main.status.auto_key_white": {"ja": "鍵を白ブロック内状態に自動変換 {tile}", "en": "Auto-converted key to in-white-block state {tile}"},
    "main.status.auto_door_white": {"ja": "扉を白ブロック内状態に自動変換 {tile}", "en": "Auto-converted door to in-white-block state {tile}"},
    "main.status.auto_item_white": {"ja": "アイテムを白い壊せるブロック内に自動変換 {tile}", "en": "Auto-converted item into breakable white block {tile}"},
    "main.status.auto_key_visible": {"ja": "鍵を透明ブロック内状態に自動変換 {tile}", "en": "Auto-converted key to visible-in-block state {tile}"},
    "main.status.auto_item_visible": {"ja": "アイテムを透明ブロック内に自動変換 {tile}", "en": "Auto-converted item into visible block {tile}"},
    "main.status.replace_existing_item": {"ja": "既存アイテムを置換 {tile}", "en": "Replaced existing item {tile}"},
    "main.status.auto_visible_flag": {"ja": "透明な壊せるブロック内のため自動で透BL ON {tile}", "en": "Auto-enabled visible-block item state because the target is a breakable invisible block {tile}"},
    "main.status.auto_white_flag": {"ja": "白い壊せるブロック内のため自動で白ブロック内フラグON {tile}", "en": "Auto-enabled white-in-block flag because the target is a breakable white block {tile}"},
    "main.status.auto_normal_for_cracked": {"ja": "ひび割れブロック内のため通常item_idで保存 {tile}", "en": "Saved as a normal item ID because the target is a cracked block {tile}"},
    "main.status.auto_in_block_flag": {"ja": "ブロック内のため自動で in_block フラグON {tile}", "en": "Auto-enabled in_block flag because the target is inside a block {tile}"},
    "main.eyedropper.enemy": {"ja": "スポイト: 敵 0x{code:02X} (base 0x{base:02X}, SP{speed}) を選択", "en": "Eyedropper: selected enemy 0x{code:02X} (base 0x{base:02X}, SP{speed})"},
    "main.eyedropper.item": {"ja": "スポイト: アイテム 0x{code:02X} を選択", "en": "Eyedropper: selected item 0x{code:02X}"},
    "main.eyedropper.meta": {"ja": "スポイト: {name} を選択", "en": "Eyedropper: selected {name}"},
    "main.eyedropper.block": {"ja": "スポイト: {name} を選択", "en": "Eyedropper: selected {name}"},
    "main.eyedropper.empty": {"ja": "スポイト: {tile} に何もありません", "en": "Eyedropper: nothing at {tile}"},
    "main.status.favorite_empty": {"ja": "お気に入りスロット {slot} は空です", "en": "Favorite slot {slot} is empty"},
    "main.status.favorite_selected": {"ja": "お気に入りスロット {slot} を選択", "en": "Selected favorite slot {slot}"},
    "main.status.validation_jump": {"ja": "不整合: Stage {stage}へ移動", "en": "Validation issue: moved to Stage {stage}"},
    "main.status.validation_jump_out_of_range": {"ja": "不整合: Stage {stage}へ移動（座標は範囲外: {pos}）", "en": "Validation issue: moved to Stage {stage} (position out of range: {pos})"},
    "main.status.validation_select": {"ja": "不整合: Stage {stage} ({x}, {y})を選択", "en": "Validation issue: selected Stage {stage} ({x}, {y})"},
    "main.status.language_changed": {"ja": "表示言語を切り替えました", "en": "Display language changed"},
    "main.status.solomon_seal_block_overlap": {"ja": "ソロモンの封印は {label} には重ねられません {tile}", "en": "Solomon's Seal cannot overlap {label} {tile}"},
    "main.status.solomon_seal_door_overlap": {"ja": "ソロモンの封印は扉には重ねられません {tile}", "en": "Solomon's Seal cannot overlap the door {tile}"},
    "main.status.actor_block_overlap": {"ja": "主人公・敵とブロックは同じ位置にできません {tile}", "en": "Dana/enemies and blocks cannot share the same position {tile}"},
    "main.status.block_absorb_rejected": {"ja": "このブロックとはアイテム/鍵/扉を重ねられません {tile}", "en": "Items/keys/doors cannot overlap this block {tile}"},
    "main.status.mirror_real_block_warning": {"ja": "警告: ミラー上の実体ブロック配置はドラゴン/ガーゴイル/ゴブリンが落下して死にます", "en": "Warning: placing a solid block on a mirror makes dragons/gargoyles/goblins fall and die."},
    "main.status.selection_moving": {"ja": "選択範囲を移動中…", "en": "Moving selection..."},
    "main.status.drag_grab_with_block": {"ja": "{name} + ブロックを掴み中 → ドラッグで移動", "en": "Grabbed {name} + block -> drag to move"},
    "main.status.drag_item": {"ja": "アイテムを掴み中 → ドラッグで移動", "en": "Grabbed item -> drag to move"},
    "main.status.drag_enemy": {"ja": "敵を掴み中 → ドラッグで移動", "en": "Grabbed enemy -> drag to move"},
    "main.status.drag_bonus": {"ja": "ボーナススポット[{index}] を掴み中 → ドラッグで移動", "en": "Grabbed bonus spot [{index}] -> drag to move"},
    "main.status.drag_conditional_breakable": {"ja": "{group} 条件付き壊せる白ブロック[{label}]を掴み中 → ドラッグで移動", "en": "Grabbed {group} conditional breakable white block [{label}] -> drag to move"},
    "main.status.drag_bomb_jack": {"ja": "Mighty Bomb Jack [{label}] を掴み中 → ドラッグで移動", "en": "Grabbed Mighty Bomb Jack [{label}] -> drag to move"},
    "main.status.drag_named": {"ja": "{name} を掴み中 → ドラッグで移動", "en": "Grabbed {name} -> drag to move"},
    "main.status.bomb_jack.trigger": {"ja": "頭突き判定", "en": "headbutt trigger"},
    "main.status.bomb_jack.spawn": {"ja": "出現先", "en": "spawn target"},
    "main.status.block": {"ja": "ブロック", "en": "Block"},
    "main.status.selection_move_complete": {"ja": "選択範囲の移動完了", "en": "Selection move complete"},
    "main.status.bonus_move_complete": {"ja": "ボーナススポット移動完了", "en": "Bonus spot move complete"},
    "main.status.move_named_complete": {"ja": "{name} 移動完了 → {pos}", "en": "{name} move complete -> {pos}"},
    "main.status.move_named_block_complete": {"ja": "{name} + ブロック移動完了 → {pos}", "en": "{name} + block move complete -> {pos}"},
    "main.status.move_conditional_breakable_complete": {"ja": "{group} 条件付き壊せる白ブロック[{label}]移動完了 → {pos}", "en": "{group} conditional breakable white block [{label}] move complete -> {pos}"},
    "main.status.move_bomb_jack_complete": {"ja": "Mighty Bomb Jack [{label}] 移動完了 → {pos}", "en": "Mighty Bomb Jack [{label}] move complete -> {pos}"},
    "main.status.item_move_complete": {"ja": "アイテム移動完了", "en": "Item move complete"},
    "main.status.move_complete": {"ja": "移動完了", "en": "Move complete"},
    "main.status.delete_door_key_enemy_blocked": {"ja": "扉を削除する前に鍵持ち敵を解除してください", "en": "Clear the key enemy before deleting the door."},
    "main.status.delete_door_key_meta_blocked": {"ja": "扉を削除する前に鍵メタを削除してください", "en": "Delete the key meta before deleting the door."},
    "main.status.delete_required_key_enemy_blocked": {"ja": "鍵メタが無いため、この鍵持ち敵に影響する敵は削除できません", "en": "The key meta is missing, so enemies affecting this key enemy cannot be deleted."},
    "main.status.deleted": {"ja": "削除: {tile} ({items})", "en": "Deleted: {tile} ({items})"},
    "main.deleted_kind.item": {"ja": "アイテム", "en": "item"},
    "main.deleted_kind.enemy": {"ja": "敵", "en": "enemy"},
    "main.deleted_kind.block": {"ja": "ブロック", "en": "block"},
    "main.emulator.none_registered": {"ja": "エミュレータ未登録", "en": "No emulators registered"},
    "main.emulator.settings": {"ja": "エミュレータ設定...", "en": "Emulator Settings..."},
    "main.emulator.generic": {"ja": "エミュレータ", "en": "Emulator"},
    "main.status.default_emulator": {"ja": "既定エミュレータ: {name}", "en": "Default emulator: {name}"},
    "main.status.enemy_added_multi": {"ja": "敵を追加 {tile} (このマスに{count}体)", "en": "Added enemy {tile} ({count} enemies on this cell)"},
    "main.status.start_enemy_overlap": {"ja": "主人公と敵は同じ位置にできません（開始直後に死亡します） {tile}", "en": "Dana and an enemy cannot share the same position (instant death after start) {tile}"},
    "main.status.key_door_item_overlap": {"ja": "鍵・扉・ソロモンの紋章とアイテムは同じ位置にできません {tile}", "en": "Keys, doors, Solomon's Seal, and items cannot share the same position {tile}"},
    "main.status.selection_rect": {"ja": "選択範囲: ({x1},{y1})-({x2},{y2})  {w}×{h}", "en": "Selection: ({x1},{y1})-({x2},{y2})  {w}x{h}"},
    "main.status.key_enemy_clear_blocked_no_key": {"ja": "鍵メタが無いため、この鍵持ち敵は解除できません", "en": "The key meta is missing, so this key enemy cannot be cleared."},
    "main.status.key_enemy_set_blocked_no_door": {"ja": "扉が削除されているステージには鍵持ち敵を設定できません", "en": "A key enemy cannot be set on a stage where the door has been removed."},
    "main.status.key_enemy_set_blocked_no_key": {"ja": "鍵メタが無いステージには鍵持ち敵を設定できません", "en": "A key enemy cannot be set on a stage with no key meta."},
    "main.status.warp_mirror_blocked": {"ja": "ワープミラーモードは、別々の位置にある可視ミラー2個が必要です", "en": "Warp Mirror Mode requires two visible mirrors at different positions."},
    "main.status.warp_mirror_apply_all_skipped": {"ja": "ワープミラーモードを適用しました（{count}面変更 / 条件不成立 {skipped}面はOFF）", "en": "Applied Warp Mirror Mode ({count} changed / {skipped} invalid stages left off)."},
    "main.status.replace_picker_required": {"ja": "ピッカーでブロック、アイテム、モンスターを選択してから指定してください", "en": "Select a block, item, or monster in the picker first."},
    "main.status.pixel_editor_chr_written": {"ja": "16x16ピクセル編集: CHRを書き換えました", "en": "16x16 pixel editor: CHR was rewritten"},
    "main.status.sprite_viewer_chr_written": {"ja": "スプライトビューア経由: CHRを書き換えました", "en": "Sprite viewer: CHR was rewritten"},
    "main.status.door_on_item": {"ja": "アイテムがある位置には扉を置けません {tile}", "en": "A door cannot be placed where an item exists {tile}"},
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
    "main.edit.white_block_on_key": {
        "ja": "鍵の位置に白ブロックは置けません {tile}",
        "en": "Cannot place a white block on the key position {tile}",
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
    "main.autosave.failed.migration_offer": {
        "ja": (
            "旧runtime形式が原因の可能性があります。\n"
            "データ移行を選ぶと終了を中止し、現在認識できているステージや設定を"
            "現行形式のROMへ移します。移行元ROMは変更しません。"
        ),
        "en": (
            "An older runtime layout may be the cause.\n"
            "Choose Data Migration to cancel closing and move the stages and settings "
            "currently recognized by this app into a current-format ROM. "
            "The source ROM will not be modified."
        ),
    },
    "main.autosave.failed.migrate": {
        "ja": "データ移行…",
        "en": "Data Migration...",
    },
    "main.autosave.failed.exit_without_save": {
        "ja": "保存せず終了",
        "en": "Close Without Saving",
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
    "main.undo_history.button": {
        "ja": "Undo一覧",
        "en": "Undo List",
    },
    "main.undo_history.button.tooltip": {
        "ja": "Undo/Redo履歴を一覧表示し、ダブルクリックで履歴位置へジャンプ",
        "en": "Show Undo/Redo history and double-click to jump to a history position.",
    },
    "main.undo.button.tooltip": {
        "ja": "1つ前の編集状態へ戻る",
        "en": "Undo one edit.",
    },
    "main.redo.button.tooltip": {
        "ja": "Undoした編集状態へ進む",
        "en": "Redo one edit.",
    },
    "main.undo_history.title": {
        "ja": "Undo/Redo履歴",
        "en": "Undo/Redo History",
    },
    "main.undo_history.summary": {
        "ja": "現在位置: {current} / {total}  （ダブルクリックでその履歴位置へ移動）",
        "en": "Current position: {current} / {total}  (Double-click to jump to that history position)",
    },
    "main.undo_history.col.state": {
        "ja": "状態",
        "en": "State",
    },
    "main.undo_history.col.no": {
        "ja": "No.",
        "en": "No.",
    },
    "main.undo_history.col.time": {
        "ja": "時刻",
        "en": "Time",
    },
    "main.undo_history.col.stage": {
        "ja": "面",
        "en": "Stage",
    },
    "main.undo_history.col.action": {
        "ja": "操作",
        "en": "Action",
    },
    "main.undo_history.col.detail": {
        "ja": "座標/詳細",
        "en": "Position / Detail",
    },
    "main.undo_history.jump": {
        "ja": "選択位置へ移動",
        "en": "Jump to Selection",
    },
    "main.undo_history.state.applied": {
        "ja": "適用済み",
        "en": "Applied",
    },
    "main.undo_history.state.redo": {
        "ja": "Redo可能",
        "en": "Redo",
    },
    "main.undo_history.state.current_after": {
        "ja": "現在位置",
        "en": "Current",
    },
    "main.undo_history.state.initial": {
        "ja": "初期状態",
        "en": "Initial",
    },
    "main.undo_history.action.initial": {
        "ja": "初期状態",
        "en": "Initial state",
    },
    "main.undo_history.action.generic": {
        "ja": "編集",
        "en": "Edit",
    },
    "main.undo_history.action.place": {
        "ja": "配置",
        "en": "Place",
    },
    "main.undo_history.action.continuous_place": {
        "ja": "連続配置",
        "en": "Paint",
    },
    "main.undo_history.action.place_block": {
        "ja": "ブロック配置",
        "en": "Place block",
    },
    "main.undo_history.action.place_item": {
        "ja": "アイテム配置",
        "en": "Place item",
    },
    "main.undo_history.action.place_enemy": {
        "ja": "敵配置",
        "en": "Place enemy",
    },
    "main.undo_history.action.place_meta": {
        "ja": "メタ配置",
        "en": "Place meta object",
    },
    "main.undo_history.action.delete": {
        "ja": "削除",
        "en": "Delete",
    },
    "main.undo_history.action.continuous_delete": {
        "ja": "連続削除",
        "en": "Erase",
    },
    "main.undo_history.action.move": {
        "ja": "移動",
        "en": "Move",
    },
    "main.undo_history.action.paste": {
        "ja": "貼り付け",
        "en": "Paste",
    },
    "main.undo_history.action.stage_png_load": {
        "ja": "ステージPNG読込",
        "en": "Load stage PNG",
    },
    "main.undo_history.action.image_block_grid": {
        "ja": "画像からブロック配置",
        "en": "Place blocks from image",
    },
    "main.undo_history.action.clear_level": {
        "ja": "ステージクリア",
        "en": "Clear stage",
    },
    "main.undo_history.detail.tile": {
        "ja": "座標 {tile}",
        "en": "Position {tile}",
    },
    "main.undo_history.detail.origin": {
        "ja": "起点",
        "en": "Origin",
    },
    "main.undo_history.detail.target": {
        "ja": "対象: {target}",
        "en": "Target: {target}",
    },
    "main.undo_history.detail.count": {
        "ja": "{count}個",
        "en": "{count} items",
    },
    "main.undo_history.detail.move": {
        "ja": "{target}: {src} -> {dst}",
        "en": "{target}: {src} -> {dst}",
    },
    "main.undo_history.detail.initial": {
        "ja": "ROM読込直後",
        "en": "After ROM load",
    },
    "main.undo_history.positions": {
        "ja": "座標: {positions}",
        "en": "Positions: {positions}",
    },
    "main.undo_history.already_here": {
        "ja": "すでに選択した履歴位置です",
        "en": "Already at the selected history position.",
    },
    "main.undo_history.jump.done": {
        "ja": "Undo履歴位置へ移動しました: {current} / {total}",
        "en": "Jumped to Undo history position: {current} / {total}",
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
    "palette.stage_range": {
        "ja": "{range}面",
        "en": "Stages {range}",
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
    "pixel.copy": {
        "ja": "16x16コピー",
        "en": "Copy 16x16",
    },
    "pixel.copy.tooltip": {
        "ja": "現在の16x16全体をコピー (Ctrl+C)",
        "en": "Copy the full current 16x16 image (Ctrl+C).",
    },
    "pixel.paste": {
        "ja": "16x16貼り付け",
        "en": "Paste 16x16",
    },
    "pixel.paste.tooltip": {
        "ja": "コピーした16x16全体を貼り付け (Ctrl+V)",
        "en": "Paste the full copied 16x16 image (Ctrl+V).",
    },
    "pixel.copy_all_banks": {
        "ja": "全CHRバンクへコピー",
        "en": "Copy to All CHR Banks",
    },
    "pixel.copy_all_banks.tooltip": {
        "ja": "現在の16x16を同じキャラクター位置へ全CHRバンク一括書込",
        "en": "Write the current 16x16 image to the same character position in every CHR bank.",
    },
    "pixel.copy_all_banks_failed.title": {
        "ja": "全バンクコピー失敗",
        "en": "Copy to All Banks Failed",
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
    "main.log.restart_app": {
        "ja": "アプリ再起動",
        "en": "Application restart",
    },
    "main.history.empty": {
        "ja": "(履歴なし)",
        "en": "(No history)",
    },
    "main.history.clear": {
        "ja": "履歴をクリア",
        "en": "Clear History",
    },
    "main.history.cleared": {
        "ja": "履歴をクリアしました（前回の作業状態は保持）",
        "en": "History cleared (previous work state kept)",
    },
    "main.save_preflight.more": {
        "ja": "- ...ほか {count} 件",
        "en": "- ... and {count} more",
    },
    "main.save_preflight.log_prefix": {
        "ja": "保存前不整合: ",
        "en": "Pre-save inconsistencies: ",
    },
    "main.save_preflight.title": {
        "ja": "保存前チェック",
        "en": "Pre-save Check",
    },
    "main.save_preflight.body": {
        "ja": (
            "保存前チェックで不整合らしき項目が見つかりました。\n"
            "エラーではありませんが、見落としの可能性があります。\n\n"
            "{body}\n\n"
            "このまま保存を続行しますか？"
        ),
        "en": (
            "The pre-save check found possible inconsistencies.\n"
            "This is not an error, but something may have been missed.\n\n"
            "{body}\n\n"
            "Continue saving anyway?"
        ),
    },
    "main.autosave.restore_status": {
        "ja": "{name} の作業状態を復元しました: {saved_at} / Stage {stage}",
        "en": "Restored work state for {name}: {saved_at} / Stage {stage}",
    },
    "main.autosave.restore_log": {
        "ja": "前回の作業状態を復元: {name} / {saved_at} / {path} / Stage {stage}",
        "en": "Restored previous work state: {name} / {saved_at} / {path} / Stage {stage}",
    },
    "main.autosave.restore_failed.title": {
        "ja": "前回の作業状態を復元できません",
        "en": "Could Not Restore Previous Work State",
    },
    "main.autosave.restore_failed.log": {
        "ja": "前回の作業状態を復元失敗: {error}",
        "en": "Failed to restore previous work state: {error}",
    },
    "main.readonly_restore.status_short": {
        "ja": "前回の閲覧専用ROMを復元しました",
        "en": "Restored the previous read-only ROM",
    },
    "main.readonly_restore.status": {
        "ja": "前回の閲覧専用ROMを復元しました: Stage {stage}",
        "en": "Restored the previous read-only ROM: Stage {stage}",
    },
    "main.readonly_restore.log": {
        "ja": "前回の閲覧専用ROMを復元: {path} / Stage {stage}",
        "en": "Restored previous read-only ROM: {path} / Stage {stage}",
    },
    "main.readonly_restore.failed.title": {
        "ja": "前回の閲覧専用ROMを復元できません",
        "en": "Could Not Restore Previous Read-only ROM",
    },
    "main.readonly_restore.failed.log": {
        "ja": "前回の閲覧専用ROMを復元失敗: {error}",
        "en": "Failed to restore previous read-only ROM: {error}",
    },
    "main.key_enemy.reset.title": {
        "ja": "鍵持ち敵設定を解除",
        "en": "Key Enemy Setting Cleared",
    },
    "main.key_enemy.reset.body": {
        "ja": "鍵持ち敵に指定していた番号が、このステージの敵数を超えたため解除しました。",
        "en": "The selected key enemy number exceeded this stage's enemy count, so it was cleared.",
    },
    "main.key_enemy.tooltip": {
        "ja": "0=なし。1から{max_enemy}は初期配置敵の順番です。Blue Burn系（$81/$83）、熾天の眩光（$9D）、妖精化敵と同じ番号は指定できません。",
        "en": "0 = none. 1 through {max_enemy} are the initial enemy placement order. Blue Burn variants ($81/$83), Seraphic Radiance ($9D), and the fairy enemy cannot use the same number.",
    },
    "main.fairy_enemy.reset.title": {
        "ja": "妖精化敵設定を解除",
        "en": "Fairy Enemy Setting Cleared",
    },
    "main.fairy_enemy.reset.body": {
        "ja": "妖精化敵に指定していた番号が、このステージで使えないため解除しました。",
        "en": "The selected fairy enemy number cannot be used in this stage, so it was cleared.",
    },
    "main.fairy_enemy.tooltip": {
        "ja": "0=なし。Dragon/Goblin/Gargoyle系のみ。Flame系と鍵持ち敵と同じ番号は指定できません。",
        "en": "0 = none. Dragon/Goblin/Gargoyle types only. Flame-type enemies and the key enemy cannot use the same number.",
    },
    "main.time_decrease.stopped": {"ja": "停止", "en": "Stopped"},
    "main.time_decrease.seconds": {"ja": "{seconds}秒", "en": "{seconds} sec"},
    "main.time_decrease.default_hint": {
        "ja": "0=24秒 / 1=32秒 / 2=44秒",
        "en": "0=24 sec / 1=32 sec / 2=44 sec",
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
            "このアプリの通常編集対象は確認済みの日本版/US版オリジナルROM、"
            "または本アプリで保存した日本版 mapper66 拡張ROMだけです。\n"
            "CRC32: {crc}"
        ),
        "en": (
            "This application's normal editing targets are verified original JP/US ROMs, "
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
    "main.binary_editor.unset.title": {
        "ja": "バイナリエディタ未設定",
        "en": "Binary Editor Not Configured",
    },
    "main.binary_editor.unset.body": {
        "ja": "F9 設定画面でバイナリエディタの実行ファイルまたはPythonファイルを登録してください。",
        "en": "Register a binary editor executable or Python file in Settings (F9).",
    },
    "main.binary_editor.missing.title": {
        "ja": "バイナリエディタが見つかりません",
        "en": "Binary Editor Not Found",
    },
    "main.binary_editor.prepare_failed.title": {
        "ja": "バイナリエディタ用ROM作成失敗",
        "en": "Binary Editor ROM Preparation Failed",
    },
    "main.binary_editor.launched": {
        "ja": "バイナリエディタで開きました: {path}{suffix}",
        "en": "Opened in binary editor: {path}{suffix}",
    },
    "main.binary_editor.launch_failed.title": {
        "ja": "バイナリエディタ起動失敗",
        "en": "Binary Editor Launch Failed",
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
        "ja": "データ移行を開始できる移行元ROMが読み込まれていません。",
        "en": "No source ROM eligible for data migration is loaded.",
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
    "main.migration.warning.global_capture_failed": {
        "ja": "共通設定を読み取れませんでした ({error_type})",
        "en": "Could not read global settings ({error_type})",
    },
    "main.migration.warning.title_capture_failed": {
        "ja": "タイトル編集データを読み取れませんでした ({error_type})",
        "en": "Could not read title editing data ({error_type})",
    },
    "main.migration.warning.chr_capture_failed": {
        "ja": "CHR画像データを読み取れませんでした ({error_type})",
        "en": "Could not read CHR graphics data ({error_type})",
    },
    "main.migration.warning.chr_apply_failed": {
        "ja": "CHR画像データを移行できませんでした ({error_type}: {error})",
        "en": "Could not migrate CHR graphics data ({error_type}: {error})",
    },
    "main.migration.warning.global_apply_incomplete": {
        "ja": "共通設定の一部は現行runtimeへ反映できませんでした。",
        "en": "Some global settings could not be applied to the current runtime.",
    },
    "main.migration.warning.global_apply_failed": {
        "ja": "共通設定を現行形式へ反映できませんでした ({error_type})",
        "en": "Could not apply global settings to the current format ({error_type})",
    },
    "main.migration.warning.title_apply_failed": {
        "ja": "タイトル編集データを移行できませんでした ({error_type}: {error})",
        "en": "Could not migrate title editing data ({error_type}: {error})",
    },
    "main.migration.save_error.offer": {
        "ja": (
            "このROMは旧runtime形式の可能性があります。データ移行を使うと、"
            "現在認識できているステージや設定を現行形式のROMへ移せます。"
            "元のROMは変更しません。"
        ),
        "en": (
            "This ROM may use an older runtime layout. Data Migration can move the "
            "stages and settings currently recognized by this app into a current-format ROM. "
            "The source ROM will not be modified."
        ),
    },
    "main.migration.save_error.action": {
        "ja": "データ移行…",
        "en": "Data Migration...",
    },
    "main.migration.target_dialog.title": {
        "ja": "原作のオリジナルROMを選択してください",
        "en": "Select an Original Game ROM",
    },
    "main.migration.target_read_failed": {
        "ja": "移行先ROMを読み込めませんでした。\n{error}",
        "en": "Could not load the target ROM.\n{error}",
    },
    "main.migration.target_not_supported": {
        "ja": (
            "移行先にできるROMではありません。\n"
            "確認済みの日本版/US版オリジナルROM、またはこのアプリで保存した編集可能ROMを選んでください。"
        ),
        "en": (
            "This ROM cannot be used as the migration target.\n"
            "Select a verified original JP/US ROM or an editable ROM saved by this app."
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
        "ja": "\n\n一部データは移行できませんでした:\n",
        "en": "\n\nSome data could not be migrated:\n",
    },
    "main.migration.complete.title": {
        "ja": "データ移行完了",
        "en": "Data Migration Complete",
    },
    "main.migration.checkpoint_failed.title": {
        "ja": "移行後の再読込失敗",
        "en": "Post-Migration Reload Failed",
    },
    "main.migration.checkpoint_failed.body": {
        "ja": (
            "データ移行後の作業状態を自動保存して再読込できませんでした。\n"
            "移行元ROMは変更していません。\n\n{error}"
        ),
        "en": (
            "The migrated work state could not be autosaved and reloaded.\n"
            "The source ROM was not modified.\n\n{error}"
        ),
    },
    "main.migration.complete.body": {
        "ja": (
            "{source_name} から {count}/{total} ステージを移行しました。\n"
            "現在のアプリが認識した設定グループ: {recognized}\n"
            "認識できず現行既定値になった設定グループ: {defaulted}\n"
            "移行元ROMは変更していません。\n"
            "移行後の作業状態を自動保存し、その保存データを再読込しました。"
            "{warning_text}"
        ),
        "en": (
            "Migrated {count}/{total} stages from {source_name}.\n"
            "Setting groups recognized by the current app: {recognized}\n"
            "Unrecognized setting groups left at current defaults: {defaulted}\n"
            "The source ROM was not modified.\n"
            "The migrated work state was autosaved and reloaded."
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
    "main.stage_png.error.invalid_embedded_data": {
        "ja": "埋め込みステージデータが壊れているため、通常画像としては扱いません。",
        "en": "The embedded stage data is invalid, so this PNG will not be treated as an ordinary image.",
    },
    "main.image_block_grid.invalid.title": {
        "ja": "画像変換エラー",
        "en": "Image Conversion Error",
    },
    "main.image_block_grid.invalid.grid": {
        "ja": "変換結果が15×12の4種類グリッドではありません。",
        "en": "The converted result is not a 15x12 four-type grid.",
    },
    "main.image_block_grid.applied": {
        "ja": "画像から15×12へブロック配置しました（16列目は保持）: {name}",
        "en": "Placed a 15x12 block grid from the image (column 16 preserved): {name}",
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
    "main.mirror_detail.button": {
        "ja": "ミラー詳細設定",
        "en": "Mirror Details",
    },
    "main.mirror_detail.tooltip": {
        "ja": "現在ステージの2つのミラーについて、出現タイミング(64ビット)とTTLを編集",
        "en": "Edit spawn timing (64 bits) and TTL for the two mirrors in the current stage.",
    },
    "main.stage_nav.prev.tooltip": {
        "ja": "前のステージ",
        "en": "Previous stage",
    },
    "main.stage_nav.next.tooltip": {
        "ja": "次のステージ",
        "en": "Next stage",
    },
    "main.stage_nav.current_stage.tooltip": {
        "ja": "現在のステージ: {stage}\nマウスホイールでステージ切替",
        "en": "Current stage: {stage}\nUse the mouse wheel to switch stages",
    },
    "main.stage_compare.diff_count": {
        "ja": "差分 {count}",
        "en": "Diff {count}",
    },
    "title_screen.open_failed": {
        "ja": "タイトル画面操作不可",
        "en": "Title Screen Operation Unavailable",
    },
    "title_screen.revert_initial": {"ja": "開いた時点へ戻す", "en": "Restore Initial"},
    "title_screen.revert.title": {"ja": "取り消し", "en": "Revert"},
    "title_screen.revert.complete": {
        "ja": "開いた時点の ROM に戻しました。",
        "en": "Restored the ROM to the state from when this dialog was opened.",
    },
    "title_screen.label.color": {"ja": "色:", "en": "Color:"},
    "title_screen.zoom.label": {"ja": "拡大:", "en": "Zoom:"},
    "title_screen.grid_lines": {"ja": "グリッド線", "en": "Grid Lines"},
    "title_screen.input_error": {"ja": "入力エラー: {error}", "en": "Input error: {error}"},
    "title_screen.preview.unavailable": {"ja": "プレビュー不可: {error}", "en": "Preview unavailable: {error}"},
    "title_screen.tile_editor.pen": {"ja": "ペン:", "en": "Pen:"},
    "title_screen.tile_editor.brush.tooltip": {
        "ja": "パレットインデックス {index} で描く。Alt+クリックでスポイト。",
        "en": "Draw with palette index {index}. Alt-click to pick a color.",
    },
    "title_screen.tile_editor.clear.tooltip": {
        "ja": "8x8タイルをパレットインデックス0で消去",
        "en": "Clear the 8x8 tile with palette index 0.",
    },
    "title_screen.tile_editor.group": {
        "ja": "8x8 CHR編集 bank内 0x{bank:03X}",
        "en": "8x8 CHR Edit in bank 0x{bank:03X}",
    },
    "title_screen.tile_editor.info_suffix": {
        "ja": "色グループ {group} / 使用箇所: {count}",
        "en": "Color group {group} / references: {count}",
    },
    "title_screen.tile_editor.status": {
        "ja": "8x8編集: cell ({col}, {row}) / bank内 0x{bank:03X}",
        "en": "8x8 edit: cell ({col}, {row}) / in-bank 0x{bank:03X}",
    },
    "title_screen.tile_editor.editing_status": {
        "ja": "8x8編集中: cell ({col}, {row}) / bank内 0x{bank:03X}",
        "en": "Editing 8x8: cell ({col}, {row}) / in-bank 0x{bank:03X}",
    },
    "title_screen.tile.edit_unavailable": {"ja": "8x8編集不可", "en": "8x8 Edit Unavailable"},
    "title_screen.tile.place_unavailable": {"ja": "タイル配置不可", "en": "Tile Placement Unavailable"},
    "title_screen.tile.place_failed": {"ja": "タイル配置失敗", "en": "Tile Placement Failed"},
    "title_screen.palette_dialog.title": {"ja": "タイトル色編集", "en": "Title Color Edit"},
    "title_screen.palette_dialog.note": {
        "ja": "タイトル画面のBGパレット16色を編集します。各値はROMに書かれるNES色番号($00-$3F)です。",
        "en": "Edit the 16 BG palette colors for the title screen. Each value is the NES color number ($00-$3F) written to the ROM.",
    },
    "title_screen.palette.group": {"ja": "タイトルパレット $3F00-$3F0F", "en": "Title Palette $3F00-$3F0F"},
    "title_screen.palette.index": {"ja": "パレット {index}", "en": "Palette {index}"},
    "title_screen.palette.nes64": {"ja": "NES 64色", "en": "NES 64 Colors"},
    "title_screen.palette.slot.tooltip": {
        "ja": "パレット {palette} / slot {slot} = ${value:02X}",
        "en": "Palette {palette} / slot {slot} = ${value:02X}",
    },
    "title_screen.palette_panel.title": {"ja": "パレット変更", "en": "Change Palette"},
    "title_screen.palette_panel.target_block": {
        "ja": "対象: x={x}, y={y} の16x16区画",
        "en": "Target: 16x16 block at x={x}, y={y}",
    },
    "title_screen.palette_panel.no_target": {
        "ja": "対象区画なし: 色番号だけ変更できます。パレット番号の割当はキャンバスを右クリック。",
        "en": "No target block: only color numbers can be changed. Right-click the canvas to assign a palette number.",
    },
    "title_screen.palette_panel.block_changed": {
        "ja": "16x16色変更: x={x}, y={y} / パレット {palette}",
        "en": "16x16 color changed: x={x}, y={y} / palette {palette}",
    },
    "title_screen.palette_panel.block_target": {
        "ja": "16x16色対象: x={x}, y={y} / パレット {palette}",
        "en": "16x16 color target: x={x}, y={y} / palette {palette}",
    },
    "title_screen.palette_panel.change_unavailable": {"ja": "パレット変更不可", "en": "Palette Change Unavailable"},
    "title_screen.palette_panel.write_failed": {
        "ja": "タイトルパレットを書き換えられませんでした:\n{error}",
        "en": "Could not rewrite the title palette:\n{error}",
    },
    "title_screen.palette_panel.slot_changed": {
        "ja": "パレット変更: パレット {palette} / slot {slot} = ${value:02X}",
        "en": "Palette changed: palette {palette} / slot {slot} = ${value:02X}",
    },
    "title_screen.palette_group_replace.title": {"ja": "色グループ置換", "en": "Replace Color Group"},
    "title_screen.palette_group_replace.same": {
        "ja": "置換元と置換先が同じです。変更はありません。",
        "en": "The source and destination are the same. Nothing changed.",
    },
    "title_screen.palette_group_replace.none": {
        "ja": "色グループ {group} を使う16x16区画はありません。",
        "en": "No 16x16 blocks use color group {group}.",
    },
    "title_screen.palette_group_replace.status": {
        "ja": "色グループ置換: {src} -> {dst} / {count}区画",
        "en": "Color group replace: {src} -> {dst} / {count} blocks",
    },
    "title_screen.character_picker.title": {"ja": "タイトルキャラクター追加", "en": "Add Title Character"},
    "title_screen.character_picker.note": {
        "ja": "一覧をクリックして選択、ダブルクリックで確定。OK後、タイトルプレビューをクリックして配置します。最大 {max} 体。",
        "en": "Click the list to select, double-click to confirm. After OK, click the title preview to place it. Maximum {max} characters.",
    },
    "title_screen.character_picker.no_frames": {"ja": "ROMフレームが見つかりません。", "en": "No ROM frames were found."},
    "title_screen.character_picker.selection": {
        "ja": "選択: g{group:02X} s{state:02X} f{frame} / tile ${tile1:02X},${tile2:02X} attr ${attr:02X}",
        "en": "Selected: g{group:02X} s{state:02X} f{frame} / tile ${tile1:02X},${tile2:02X} attr ${attr:02X}",
    },
    "title_screen.character_panel.title": {"ja": "キャラクター", "en": "Characters"},
    "title_screen.character.count": {
        "ja": "キャラクター {count}/{maximum}",
        "en": "Characters {count}/{maximum}",
    },
    "title_screen.character.placed": {
        "ja": "配置済み: {count}/{maximum}",
        "en": "Placed: {count}/{maximum}",
    },
    "title_screen.character_panel.selection_status": {
        "ja": "選択: g{group:02X} s{state:02X} f{frame} / {count_text} / キャンバスをクリックして配置",
        "en": "Selected: g{group:02X} s{state:02X} f{frame} / {count_text} / click the canvas to place",
    },
    "title_screen.character.clear_all": {"ja": "全削除", "en": "Clear All"},
    "title_screen.character.clear_all.tooltip": {
        "ja": "タイトル上に配置した静止キャラを全て消します。",
        "en": "Remove all static characters placed on the title screen.",
    },
    "title_screen.character.clear_all.title": {"ja": "キャラ全削除", "en": "Clear All Characters"},
    "title_screen.character.clear_all.confirm": {
        "ja": "タイトル上に配置した静止キャラを全て消します。",
        "en": "Remove all static characters placed on the title screen?",
    },
    "title_screen.character.place_unavailable": {"ja": "キャラクター配置不可", "en": "Character Placement Unavailable"},
    "title_screen.character.place_failed": {"ja": "キャラクター配置失敗", "en": "Character Placement Failed"},
    "title_screen.character.move_failed": {"ja": "キャラクター移動失敗", "en": "Character Move Failed"},
    "title_screen.character.moving_status": {"ja": "キャラスロット {slot} を移動中", "en": "Moving character slot {slot}"},
    "title_screen.character.moved_status": {"ja": "キャラスロット {slot} を移動しました", "en": "Moved character slot {slot}"},
    "title_screen.character.delete_unavailable": {"ja": "キャラ削除不可", "en": "Character Delete Unavailable"},
    "title_screen.character.delete_failed": {"ja": "キャラ削除失敗", "en": "Character Delete Failed"},
    "title_screen.character.deleted_status": {
        "ja": "選択キャラを削除しました / {count_text}",
        "en": "Deleted the selected character / {count_text}",
    },
    "title_screen.tile_picker.title": {"ja": "タイル配置", "en": "Tile Placement"},
    "title_screen.tile_picker.display_mode": {"ja": "表示モード:", "en": "Display Mode:"},
    "title_screen.tile_picker.raw_chr": {"ja": "生CHRタイル (8x8)", "en": "Raw CHR Tiles (8x8)"},
    "title_screen.tile_picker.palette": {"ja": "パレット:", "en": "Palette:"},
    "title_screen.tile_picker.status": {
        "ja": "タイル配置: stream ${stream:02X} / bank内 0x{bank:03X}",
        "en": "Tile placement: stream ${stream:02X} / in-bank 0x{bank:03X}",
    },
    "title_screen.tile_picker.selection_status": {
        "ja": "選択: stream ${stream:02X} / bank内 0x{bank:03X}\nキャンバス上の8x8マスをクリックすると配置します。",
        "en": "Selected: stream ${stream:02X} / in-bank 0x{bank:03X}\nClick an 8x8 cell on the canvas to place it.",
    },
    "title_screen.tile_picker.hover_status": {
        "ja": "選択: stream ${selected:02X}\nカーソル: stream ${stream:02X} / bank内 0x{bank:03X}",
        "en": "Selected: stream ${selected:02X}\nCursor: stream ${stream:02X} / in-bank 0x{bank:03X}",
    },
    "title_screen.preview.pending_stamp": {
        "ja": "貼り付け待ち: {width}x{height}px ({tile_w}x{tile_h} tiles) / クリック位置 ({col}, {row})",
        "en": "Pending paste: {width}x{height}px ({tile_w}x{tile_h} tiles) / click position ({col}, {row})",
    },
    "title_screen.preview.pending_character": {
        "ja": "キャラ配置待ち: g{group:02X} s{state:02X} f{frame} / x={x}, y={y}",
        "en": "Pending character: g{group:02X} s{state:02X} f{frame} / x={x}, y={y}",
    },
    "title_screen.preview.pending_tile": {
        "ja": "タイル配置待ち: cell ({col}, {row}) / stream ${stream:02X} / bank内 0x{bank:03X}",
        "en": "Pending tile: cell ({col}, {row}) / stream ${stream:02X} / in-bank 0x{bank:03X}",
    },
    "title_screen.preview.character_hit": {
        "ja": "キャラスロット {slot}/{max} / x={x}, y={y}",
        "en": "Character slot {slot}/{max} / x={x}, y={y}",
    },
    "title_screen.stamp.unavailable": {"ja": "貼り付け不可", "en": "Paste Unavailable"},
    "title_screen.stamp.failed": {"ja": "貼り付け失敗", "en": "Paste Failed"},
    "title_screen.stamp.out_of_bounds": {
        "ja": "貼り付け先が画面外にはみ出します。\nクリック位置: x={x}, y={y}\n画像サイズ: {tile_w}x{tile_h} tiles",
        "en": "The paste target extends outside the screen.\nClick position: x={x}, y={y}\nImage size: {tile_w}x{tile_h} tiles",
    },
    "title_screen.png_guard.title": {"ja": "PNG取り込み不可", "en": "PNG Import Unavailable"},
    "title_screen.png_guard.block": {"ja": "attr ({x},{y}) / {count}色", "en": "attr ({x},{y}) / {count} colors"},
    "title_screen.top_png.paste_complete.title": {"ja": "Top PNG貼り付け完了", "en": "Top PNG Paste Complete"},
    "title_screen.save.failed.title": {"ja": "保存失敗", "en": "Save Failed"},
    "title_screen.save.complete.title": {"ja": "保存完了", "en": "Save Complete"},
    "title_screen.save_image.dialog_title": {"ja": "タイトル画面を画像保存", "en": "Save Title Screen Image"},
    "title_screen.save_image.failed": {"ja": "画像を保存できませんでした:\n{path}", "en": "Could not save the image:\n{path}"},
    "title_screen.save_image.complete": {
        "ja": "タイトル画面 ({width}x{height}, 4階調) を保存:\n{path}",
        "en": "Saved title screen ({width}x{height}, 4 shades):\n{path}",
    },
    "title_screen.save_top.dialog_title": {"ja": "タイトル上部PNGを保存", "en": "Save Title Top PNG"},
    "title_screen.save_top.failed": {"ja": "タイトル上部画像を保存できませんでした:\n{path}", "en": "Could not save the title top image:\n{path}"},
    "title_screen.save_top.complete": {
        "ja": "タイトル上部画像 ({width}x{height}, 4階調) を保存:\n{path}",
        "en": "Saved title top image ({width}x{height}, 4 shades):\n{path}",
    },
    "title_screen.clear_screen.apply_failed": {"ja": "クリア画面改造失敗", "en": "Clear Screen Mod Failed"},
    "title_screen.clear_screen.character_changed": {"ja": "表示キャラを {name} に変更しました", "en": "Changed display character to {name}"},
    "title_screen.clear_message.updated": {"ja": "クリア画面メッセージを更新しました", "en": "Updated clear screen message"},
    "title_screen.clear_message.applied": {"ja": "クリア画面メッセージを反映しました", "en": "Applied clear screen message"},
    "title_screen.ending_text.applied": {"ja": "エンディング文字を反映しました", "en": "Applied ending text"},
    "title_screen.png_import.title": {"ja": "PNG取り込み", "en": "PNG Import"},
    "title_screen.png_import.disabled": {
        "ja": "全体PNG取り込みは現在停止しています。\nタイトル画像の読み込みは「Top PNG読み込み...」から、最大256x64の画像を指定してください。",
        "en": "Full PNG import is currently disabled.\nTo load a title image, use \"Load Top PNG...\" and choose an image up to 256x64.",
    },
    "title_screen.load.unavailable": {"ja": "読み込み不可", "en": "Load Unavailable"},
    "title_screen.load.failed": {"ja": "読み込み失敗", "en": "Load Failed"},
    "title_screen.load.image_failed": {"ja": "画像を読み込めません:\n{path}", "en": "Could not load the image:\n{path}"},
    "title_screen.load.image_open_failed.title": {"ja": "画像読み込み失敗", "en": "Image Load Failed"},
    "title_screen.load.image_open_failed": {"ja": "画像を開けません:\n{path}", "en": "Could not open the image:\n{path}"},
    "title_screen.top_png.load_complete.title": {"ja": "Top PNG読み込み完了", "en": "Top PNG Load Complete"},
    "title_screen.top_png.load_complete.scope": {
        "ja": "対象: x=0..255, y=49..112。下半分の山/神殿側は触りません。",
        "en": "Target: x=0..255, y=49..112. The lower mountain/temple area is not touched.",
    },
    "title_screen.top_png.import_failed.title": {"ja": "Top PNG取り込み失敗", "en": "Top PNG Import Failed"},
    "title_screen.top_png.import_complete.title": {"ja": "Top PNG取り込み完了", "en": "Top PNG Import Complete"},
    "title_screen.top_png.invalid_size": {"ja": "画像サイズが不正です: {width}x{height}", "en": "Invalid image size: {width}x{height}"},
    "title_screen.top_png.size_not_multiple": {
        "ja": "Top PNGとして読み込める画像は、幅と高さが8の倍数である必要があります。\n指定画像: {width}x{height}",
        "en": "Images loaded as Top PNG must have width and height that are multiples of 8.\nSelected image: {width}x{height}",
    },
    "title_screen.top_png.pending_stamp_status": {
        "ja": "貼り付け待ち: {width}x{height}px ({tile_w}x{tile_h} tiles) / プレビュー上の貼り付け開始位置をクリック",
        "en": "Pending paste: {width}x{height}px ({tile_w}x{tile_h} tiles) / click the paste start position in the preview",
    },
    "title_screen.top_png.pick_paste_position.title": {"ja": "貼り付け位置を指定", "en": "Choose Paste Position"},
    "title_screen.top_png.pick_paste_position.body": {
        "ja": "読み込んだ画像は256x64より小さいため、まだROMへ適用していません。\nタイトルプレビュー上で貼り付け開始位置をクリックしてください。",
        "en": "The loaded image is smaller than 256x64, so it has not been applied to the ROM yet.\nClick the paste start position in the title preview.",
    },
    "title_screen.apply.title": {"ja": "適用", "en": "Apply"},
    "title_screen.apply.changed": {
        "ja": "変更は ROM に反映済みです (このまま編集を続けられます)。",
        "en": "Changes have already been applied to the ROM. You can continue editing.",
    },
    "title_screen.apply.no_changes": {"ja": "変更はありません。", "en": "There are no changes."},
    "title_screen.text.edit_unavailable": {"ja": "文字編集不可", "en": "Text Edit Unavailable"},
    "title_screen.text.push_read_failed": {"ja": "PUSH START文字読込失敗", "en": "PUSH START Text Read Failed"},
    "title_screen.text.dialog_title": {"ja": "タイトル文字編集", "en": "Edit Title Text"},
    "title_screen.text.input_note": {
        "ja": "A-Z / 0-9 / スペース / , . \" が使えます。最大32文字。",
        "en": "You can use A-Z, 0-9, spaces, commas, periods, and quotation marks. Maximum 32 characters.",
    },
    "title_screen.text.extra_short_label": {"ja": "追加文字", "en": "Extra text"},
    "title_screen.text.push_short_label": {
        "ja": "PUSH START位置の固定文字",
        "en": "Fixed text at the PUSH START position",
    },
    "title_screen.text.extra_label": {
        "ja": "追加文字 (A-Z / 0-9 / スペース / , . \"、最大32文字)",
        "en": "Extra text (A-Z / 0-9 / space / , . \"; max 32 characters)",
    },
    "title_screen.text.push_label": {
        "ja": "PUSH START位置の固定文字 (A-Z / 0-9 / スペース / , . \"、最大32文字)",
        "en": "Fixed text at the PUSH START position (A-Z / 0-9 / space / , . \"; max 32 characters)",
    },
    "title_screen.text.previewing": {"ja": "プレビュー反映中", "en": "Preview Applied"},
    "title_screen.text.updated": {"ja": "タイトル文字を更新しました", "en": "Updated title text"},
    "title_screen.text.push_unavailable": {"ja": "PUSH START文字不可", "en": "PUSH START Text Unavailable"},
    "title_screen.text.push_input_title": {"ja": "PUSH START文字", "en": "PUSH START Text"},
    "title_screen.text.push_input_label": {
        "ja": "PUSH START BUTTON位置の固定文字 (A-Z / 0-9 / スペース / , . \"、最大32文字):",
        "en": "Fixed text at the PUSH START BUTTON position (A-Z / 0-9 / space / , . \"; max 32 characters):",
    },
    "title_screen.text.push_change_failed": {"ja": "PUSH START文字変更失敗", "en": "PUSH START Text Change Failed"},
    "hack_dialog.title.enemy": {"ja": "敵", "en": "Enemies"},
    "hack_dialog.title.game": {"ja": "ゲーム挙動改造", "en": "Game Behavior Tweaks"},
    "hack_dialog.info.enemy_html": {
        "ja": (
            "敵の挙動に関係する既知アドレスを書き換えます。<br>"
            "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
            "保存ボタンを押すまでは元に戻せます（再読込で復元可）。"
        ),
        "en": (
            "Changes known addresses related to enemy behavior.<br>"
            "Applying changes <b>modifies the ROM binary directly</b>.<br>"
            "You can still undo the changes until you save the ROM; reloading restores the original state."
        ),
    },
    "hack_dialog.info.game_html": {
        "ja": (
            "ROMの既知アドレスを書き換えてゲーム挙動を変更します。<br>"
            "適用すると <b>ROMバイナリが直接変更されます</b>。<br>"
            "保存ボタンを押すまでは元に戻せます（再読込で復元可）。"
        ),
        "en": (
            "Changes game behavior by writing known ROM addresses.<br>"
            "Applying changes <b>modifies the ROM binary directly</b>.<br>"
            "You can still undo the changes until you save the ROM; reloading restores the original state."
        ),
    },
    "hack_dialog.group.start_stage": {"ja": "開始ステージ", "en": "Starting Stage"},
    "hack_dialog.group.continue_limit": {"ja": "コンティニュー上限", "en": "Continue Limit"},
    "hack_dialog.group.final_stage": {"ja": "最終ステージ", "en": "Final Stage"},
    "hack_dialog.final_stage.option": {"ja": "{stage}面をクリアした後", "en": "After clearing stage {stage}"},
    "hack_dialog.original_suffix": {"ja": "（原作）", "en": " (original)"},
    "hack_dialog.final_stage.tooltip": {
        "ja": "選んだ面をクリアした後、次の面を原作最終面に差し替えます。48面は原作相当なので追加フラグを書きません。",
        "en": "After clearing the selected stage, replaces the next stage with the original final stage. Stage 48 is equivalent to the original, so no extra flag is written.",
    },
    "hack_dialog.group.warp_feather": {"ja": "ワープの羽", "en": "Warp Feather"},
    "hack_dialog.warp_feather.suffix": {"ja": " 面分ワープ", "en": " stages warped"},
    "hack_dialog.validation_failed_disabled": {"ja": "⚠ 検証失敗のため無効: {error}", "en": "Validation failed; disabled: {error}"},
    "hack_dialog.warp_feather.hint": {
        "ja": "原作は6面分。実コードは $C69F の #$05 と通常クリアの +1 で合計6。この値は $28 bit6 ルートのクリア進行数を変えます。",
        "en": "The original warps 6 stages. The real code combines #$05 at $C69F with the normal clear +1 for a total of 6. This value changes the clear progression count on the $28 bit6 route.",
    },
    "hack_dialog.group.solomon_seal_stage": {"ja": "ソロモンの封印 出現面", "en": "Solomon's Seal Stages"},
    "hack_dialog.stage.option": {"ja": "{stage}面", "en": "Stage {stage}"},
    "hack_dialog.solomon_seal.slot.label": {"ja": "封印{slot}:", "en": "Seal {slot}:"},
    "hack_dialog.solomon_seal.hint": {
        "ja": "1面につき封印1個まで。20面までに4個以上、44面までに6個以上、48面までに8個配置される必要があります。ROM保存できる候補だけ表示します。",
        "en": "Only one seal can appear per stage. At least 4 must be placed by stage 20, 6 by stage 44, and 8 by stage 48. Only ROM-saveable candidates are shown.",
    },
    "hack_dialog.solomon_seal.unsupported": {
        "ja": "⚠ JP ROM以外、または特殊処理テーブル検証失敗のため無効です。",
        "en": "Disabled because this is not a JP ROM or the special-process table validation failed.",
    },
    "hack_dialog.group.initial_magic": {"ja": "初期魔法（共通）", "en": "Initial Magic (Common)"},
    "hack_dialog.initial_magic.max.tooltip": {
        "ja": "持てる巻物の最大数。原作は3。0にすると巻物を持てません。",
        "en": "Maximum number of scrolls Dana can hold. Original is 3. Set to 0 to disable scroll possession.",
    },
    "hack_dialog.initial_magic.placeholder": {"ja": "例: FFF / SSS / FSFS", "en": "Example: FFF / SSS / FSFS"},
    "hack_dialog.initial_magic.pattern.tooltip": {
        "ja": "開始時に持っている巻物。F=通常ファイヤー、S=スーパー。最大8文字。空欄で原作(所持なし)。",
        "en": "Scrolls held at start. F=normal fire, S=super fire. Up to 8 characters. Empty restores the original no-scroll start.",
    },
    "hack_dialog.initial_magic.max.label": {"ja": "最大数:", "en": "Max count:"},
    "hack_dialog.initial_magic.pattern.label": {"ja": "初期所持:", "en": "Initial scrolls:"},
    "hack_dialog.initial_magic.hint": {
        "ja": "原作は最大3・初期所持なし。例: FFF=通常火球3つ、SSS=超火球3つ。原作値(最大3・空欄)に戻すと追加フックも復元します。",
        "en": "Original is max 3 with no initial scrolls. Example: FFF=3 normal fireballs, SSS=3 super fireballs. Restoring original values (max 3 and empty) also restores the added hook.",
    },
    "hack_dialog.group.initial_lives": {"ja": "初期残数", "en": "Initial Lives"},
    "hack_dialog.initial_lives.tooltip": {
        "ja": "開始時のダーナ残数。原作は3。$0452だけを書き換え、初期魔法の$042Bには影響させません。",
        "en": "Dana lives at start. Original is 3. Only $0452 is changed; initial magic at $042B is not affected.",
    },
    "hack_dialog.initial_lives.label": {"ja": "開始時の残数:", "en": "Starting lives:"},
    "hack_dialog.initial_lives.hint": {
        "ja": "原作は3。単純な #$03 変更では巻物最大数にも漏れるため、専用フックで残数だけ変更します。",
        "en": "Original is 3. A simple #$03 edit also leaks into max scroll count, so a dedicated hook changes only lives.",
    },
    "hack_dialog.disabled": {"ja": "⚠ 無効: {error}", "en": "Disabled: {error}"},
    "hack_dialog.standard_suffix": {"ja": "（標準）", "en": " (standard)"},
    "hack_dialog.frame.suffix": {"ja": " フレーム", "en": " frames"},
    "hack_dialog.stage.suffix": {"ja": " 面", "en": " stage"},
    "hack_dialog.group.time_decrease": {"ja": "ステージ制限時間", "en": "Stage Time Limit"},
    "hack_dialog.time_decrease.tooltip": {
        "ja": "CPU $9942 のステージ制限時間テーブル値。値が大きいほど短くなります。",
        "en": "Stage time-decrease table value at CPU $9942. Larger values make time run out faster.",
    },
    "hack_dialog.time_decrease.fast.label": {"ja": "0=速い:", "en": "0=Fast:"},
    "hack_dialog.time_decrease.normal.label": {"ja": "1=普通:", "en": "1=Normal:"},
    "hack_dialog.time_decrease.slow.label": {"ja": "2=遅い:", "en": "2=Slow:"},
    "hack_dialog.time_decrease.hint": {
        "ja": "原作値は 速い=$2D / 普通=$22 / 遅い=$19。目安は開始LIFE 10000が0になるまでの時間です。",
        "en": "Original values are Fast=$2D / Normal=$22 / Slow=$19. The estimate is the time until starting LIFE 10000 reaches 0.",
    },
    "hack_dialog.group.wall_color": {"ja": "ステージ壁色 (1-48面)", "en": "Stage Wall Colors (Stages 1-48)"},
    "hack_dialog.wall_color.tooltip": {
        "ja": "CPU $9122 の4面単位壁色テーブル値。NESパレット番号です。",
        "en": "Four-stage wall-color table value at CPU $9122. This is a NES palette index.",
    },
    "hack_dialog.wall_color.stage_range": {"ja": "{range}面", "en": "Stages {range}"},
    "hack_dialog.wall_color.hint": {
        "ja": "4面ごとの壁の基調色です。ROM $9122 の先頭12バイトだけを変更します。49面以降の特殊値 $80/$80 は触りません。",
        "en": "Base wall color for each four-stage range. Only the first 12 bytes of ROM $9122 are changed; special values $80/$80 for stages 49+ are left untouched.",
    },
    "hack_dialog.group.walk_speed": {"ja": "ダーナ歩行速度", "en": "Dana Walk Speed"},
    "hack_dialog.walk_speed.label": {"ja": "移動速度:", "en": "Move speed:"},
    "hack_dialog.walk_speed.hint": {
        "ja": "原作 1.0x = 0.75 px/frame（4コマ歩行アニメと同期した精密値）。地上・空中の左右4方向すべてに適用。JP/US 共通。",
        "en": "Original 1.0x = 0.75 px/frame, the exact value synchronized with the 4-frame walk animation. Applies to left/right movement on ground and in air. Common to JP/US.",
    },
    "hack_dialog.group.panel_monster": {"ja": "パネルモンスター", "en": "Panel Monster"},
    "hack_dialog.panel_monster.bullet_fix": {"ja": "弾の左右速度バグ修正", "en": "Fix bullet left/right speed bug"},
    "hack_dialog.panel_monster.bullet_speed.slow": {"ja": "$30/$50（右下$30・左上$50）", "en": "$30/$50 (down-right $30 / up-left $50)"},
    "hack_dialog.panel_monster.bullet_speed.fast": {"ja": "$3F/$41（右下$3F・左上$41）", "en": "$3F/$41 (down-right $3F / up-left $41)"},
    "hack_dialog.panel_monster.cooldown.label": {"ja": "クールダウン:", "en": "Cooldown:"},
    "hack_dialog.panel_monster.fixed_speed.label": {"ja": "修正後の速度:", "en": "Fixed speed:"},
    "hack_dialog.panel_monster.hint": {
        "ja": "判定: {region} / 原作 クールダウン192F。値を小さくすると連射化します。下限32F。短すぎる値は複数パネル面で17個のsub-slotを使い切りやすく、発射失敗や弾抜けの原因になります。 弾の左右速度バグ修正は共有Bullet速度テーブルを補正するため、バレットを使う敵すべてに影響します。",
        "en": "Detected: {region} / Original cooldown is 192F. Smaller values fire more rapidly. Minimum is 32F. Too-small values can exhaust the 17 sub-slots on stages with multiple panels, causing failed shots or missing bullets. The left/right bullet speed fix changes the shared Bullet speed table, so it affects every enemy that uses Bullet.",
    },
    "hack_dialog.panel_variant.note": {
        "ja": "A/B/C/Dパネルモンスターはステージ別ではなく、全ステージ共通の固定値を使います。既存ステージデータ内の旧A/B/C個別値は読み込み互換のみで、保存時には使いません。",
        "en": "A/B/C/D Panel Monsters use fixed values shared by all stages, not per-stage values. Old per-stage A/B/C values in existing stage data are read only for compatibility and are not used when saving.",
    },
    "hack_dialog.panel_variant.speed": {"ja": "速度", "en": "Speed"},
    "hack_dialog.panel_variant.interval": {"ja": "間隔", "en": "Interval"},
    "hack_dialog.group.demo_stage": {"ja": "デモプレイのステージ", "en": "Demo Play Stage"},
    "hack_dialog.demo_stage.label": {"ja": "デモの面:", "en": "Demo stage:"},
    "hack_dialog.demo_stage.hint": {
        "ja": "判定: {region} / 原作の既定は3面。3面以上のみ(内部のX連鎖制約)。録画入力は3面用なので別面ではDanaが録画通り動く=見た目で別面と分かる。正規プレイには影響なし。",
        "en": "Detected: {region} / Original default is stage 3. Stage 3 or later only, due to internal X-chain constraints. The recorded input is for stage 3, so on other stages Dana still follows that input and the demo visibly differs. Normal play is unaffected.",
    },
    "hack_dialog.group.golem": {"ja": "ゴブリン", "en": "Goblin"},
    "hack_dialog.golem.snappy": {
        "ja": "キビキビ動作（視認後復帰・方向転換の待ちを最小化）",
        "en": "Snappy behavior (minimize post-detection recovery and turn-around waits)",
    },
    "hack_dialog.group.shared_walk": {"ja": "ゴブリン/ドラゴン/ガーゴイル移動速度", "en": "Goblin / Dragon / Gargoyle Move Speed"},
    "hack_dialog.shared_walk.label": {"ja": "移動速度:", "en": "Move speed:"},
    "hack_dialog.shared_walk.hint": {
        "ja": "Goblin/Dragon/Gargoyle の移動速度が同じ倍率で変わります。",
        "en": "Goblin, Dragon, and Gargoyle movement speeds change by the same multiplier.",
    },
    "hack_dialog.group.neul_ghost_speed": {"ja": "ゴースト＆ヌエル移動速度", "en": "Ghost & Neul Move Speed"},
    "hack_dialog.move_speed.label": {"ja": "移動速度:", "en": "Move speed:"},
    "hack_dialog.neul_ghost_speed.hint": {
        "ja": "GhostはX方向、NeulはY方向の速度を変更します。SP1/SP2と通常/noslow版がまとめて同じ倍率で変わります。",
        "en": "Changes Ghost X speed and Neul Y speed. SP1/SP2 and normal/noslow variants all use the same multiplier.",
    },
    "hack_dialog.group.spark_ball_speed": {"ja": "スパークボール移動速度", "en": "Spark Ball Move Speed"},
    "hack_dialog.spark_ball_speed.hint": {
        "ja": "Spark Ball専用の $A9DF/$A9E7 移動差分テーブルを倍率変更します。通常スパークボールと強化スパークボール(6A/6B/6E/6F)の両方に効きます。",
        "en": "Changes the Spark Ball-specific $A9DF/$A9E7 movement delta table by multiplier. Applies to both normal Spark Ball and enhanced Spark Ball (6A/6B/6E/6F).",
    },
    "hack_dialog.group.spark_ball_variant": {"ja": "強化スパークボール", "en": "Enhanced Spark Ball"},
    "hack_dialog.spark_ball_variant.pause_digits.label": {"ja": "停止するLIFE百の位:", "en": "Pause on LIFE hundreds digit:"},
    "hack_dialog.spark_ball_variant.transparency.label": {"ja": "透明化周期:", "en": "Transparency cycle:"},
    "hack_dialog.spark_ball_variant.hint": {
        "ja": "停止型(6A/6B/6E/6F)は選択したLIFE百の位で停止します。透明型(72/73/76/77)はフレームカウンタのANDマスクで透明化周期を変えます。",
        "en": "Pause variants (6A/6B/6E/6F) stop on the selected LIFE hundreds digits. Transparency variants (72/73/76/77) change their transparency cycle through the frame-counter AND mask.",
    },
    "hack_dialog.group.demonhead": {"ja": "デーモンヘッド", "en": "Demon Head"},
    "hack_dialog.demonhead.snappy": {"ja": "キビキビ動作（方向転換の待ちを最小化）", "en": "Snappy behavior (minimize the turn-around wait)"},
    "hack_dialog.demonhead.hint": {"ja": "Demonheadの方向転換待ち $0F を $01 にします。", "en": "Changes Demon Head's $0F turn-around wait to $01."},
    "hack_dialog.group.saramandor_variant": {"ja": "強化サラマンダー", "en": "Enhanced Saramandor"},
    "hack_dialog.saramandor_variant.flame_speed.label": {"ja": "炎の速度:", "en": "Flame speed:"},
    "hack_dialog.saramandor_variant.speed.normal": {"ja": "通常", "en": "Normal"},
    "hack_dialog.saramandor_variant.speed.half": {"ja": "1/2", "en": "1/2"},
    "hack_dialog.saramandor_variant.speed.quarter": {"ja": "1/4", "en": "1/4"},
    "hack_dialog.saramandor_variant.movement_speed.1": {"ja": "速度1", "en": "Speed 1"},
    "hack_dialog.saramandor_variant.movement_speed.2": {"ja": "速度2", "en": "Speed 2"},
    "hack_dialog.saramandor_variant.movement_speed.3": {"ja": "速度3", "en": "Speed 3"},
    "hack_dialog.saramandor_variant.movement.short": {"ja": "移動速度", "en": "Move speed"},
    "hack_dialog.saramandor_variant.flame.short": {"ja": "炎速度", "en": "Flame speed"},
    "hack_dialog.saramandor_variant.refire.short": {"ja": "最低歩行", "en": "Min. walk"},
    "hack_dialog.saramandor_variant.stop.short": {"ja": "発射後停止", "en": "Post-fire stop"},
    "hack_dialog.saramandor_variant.refire_wait.label": {"ja": "最低歩行時間:", "en": "Minimum walk time:"},
    "hack_dialog.saramandor_variant.post_fire_stop.label": {"ja": "発射後停止時間:", "en": "Post-fire stop:"},
    "hack_dialog.saramandor_variant.hint": {
        "ja": "移動速度、炎速度、最低歩行時間、発射後停止時間をA/B/Cごとに設定します。最低歩行時間は1～255、原作32です。初回発射は原作32のまま、発射後停止を終えて歩き始めた後の2回目以降だけ設定値を適用します。ダーナが範囲外なら設定時間を過ぎても歩き続けます。発射後停止時間は炎が口元に出てから歩き出すまでの時間で、28～231、原作28です。",
        "en": "Movement speed, flame speed, minimum walk time, and post-fire stop are configured independently for A/B/C. Minimum walk time ranges from 1 to 255, with stock at 32. The first attack keeps the stock wait; the setting applies to later attacks after post-fire stopping ends and walking begins. If Dana is outside the attack range, it keeps walking after the configured time. Post-fire stop is measured from the flame appearing at the mouth until walking resumes; its range is 28-231 and stock is 28.",
    },
    "hack_dialog.group.gargoyle": {"ja": "ガーゴイル", "en": "Gargoyle"},
    "hack_dialog.gargoyle.snappy": {"ja": "キビキビ動作（検知後・発射直前・復帰待ちを最小化）", "en": "Snappy behavior (minimize detection, pre-shot, and recovery waits)"},
    "hack_dialog.gargoyle.cooldown.tooltip": {
        "ja": "発射後に通常行動へ戻るまでの待ち。原作は80F。1F化は危険なので下限を設けています。",
        "en": "Wait after firing before returning to normal behavior. Original is 80F. A 1F value is risky, so the lower limit is restricted.",
    },
    "hack_dialog.gargoyle.cooldown.label": {"ja": "発射後クールダウン:", "en": "Post-shot cooldown:"},
    "hack_dialog.gargoyle.hint": {
        "ja": "ONでガーゴイル固有の待ち3箇所を$01にします。弾の連射強化とは別軸で併用できます。",
        "en": "When ON, changes Gargoyle's three unique waits to $01. This can be combined with the enhanced multi-shot variant because it is a separate setting.",
    },
    "hack_dialog.group.gargoyle_variant": {"ja": "強化ガーゴイル", "en": "Enhanced Gargoyle"},
    "hack_dialog.gargoyle_variant.row.a": {"ja": "A (7A/7B):", "en": "A (7A/7B):"},
    "hack_dialog.gargoyle_variant.row.b": {"ja": "B (7E/7F):", "en": "B (7E/7F):"},
    "hack_dialog.gargoyle_variant.movement.label": {"ja": "移動速度", "en": "Move speed"},
    "hack_dialog.gargoyle_variant.movement_speed.1": {"ja": "速度1", "en": "Speed 1"},
    "hack_dialog.gargoyle_variant.movement_speed.2": {"ja": "速度2", "en": "Speed 2"},
    "hack_dialog.gargoyle_variant.speed.label": {"ja": "弾速", "en": "Bullet speed"},
    "hack_dialog.gargoyle_variant.speed.normal": {"ja": "通常", "en": "Normal"},
    "hack_dialog.gargoyle_variant.inter_shot.label": {"ja": "発射間隔", "en": "Shot interval"},
    "hack_dialog.gargoyle_variant.cooldown.label": {"ja": "クールダウン", "en": "Cooldown"},
    "hack_dialog.gargoyle_variant.hint": {
        "ja": "A/Bとも移動速度1・2を選べます。どちらもLIFE百の位が偶数なら2発、奇数なら3発撃ちます。移動速度・弾速・発射間隔・発射後クールダウンはA/B別に設定できます。",
        "en": "Movement speed 1 or 2 can be selected independently for A and B. Each fires twice when the LIFE hundreds digit is even and three times when it is odd. Movement speed, bullet speed, shot interval, and post-shot cooldown are configured independently for A and B.",
    },
    "hack_dialog.group.dragon": {"ja": "ドラゴン", "en": "Dragon"},
    "hack_dialog.dragon.snappy": {"ja": "キビキビ動作（方向転換の待ちを最小化）", "en": "Snappy behavior (minimize the turn-around wait)"},
    "hack_dialog.dragon.hint": {
        "ja": "ONでドラゴン固有の方向転換待ち1箇所を$01にします。サラマンダー共有の火吐き開始waitは変更しません。",
        "en": "When ON, changes Dragon's unique turn-around wait to $01. The fire-breath start wait shared with Saramandor is not changed.",
    },
    "hack_dialog.group.shared_flame_wait": {"ja": "ドラゴン/サラマンダー 火吐き開始待ち", "en": "Dragon / Saramandor Flame Startup Wait"},
    "hack_dialog.shared_flame_wait.label": {"ja": "待ち時間:", "en": "Wait:"},
    "hack_dialog.shared_flame_wait.hint": {
        "ja": "ドラゴン/サラマンダーが火炎を出し始めるまでの待ち時間です。原作は24F。小さいほど早く吐き、255Fにすると大きく遅れます。",
        "en": "Wait time before Dragon/Saramandor starts emitting flame. Original is 24F. Smaller values start faster; 255F delays it heavily.",
    },
    "hack_dialog.group.clear_screen_char": {"ja": "クリア画面のキャラ (おめでとう画面の2体)", "en": "Clear Screen Characters (Two Congratulations-Screen Sprites)"},
    "hack_dialog.clear_screen_char.label": {"ja": "表示キャラ:", "en": "Displayed character:"},
    "hack_dialog.clear_screen_char.hint": {
        "ja": "ステージクリア画面で左右に出る2体を差し替え。全プリセットは速度ゼロ=落下せず置物表示 (ROM解析確定)。",
        "en": "Replaces the two sprites shown on the left and right of the stage-clear screen. All presets have zero velocity, so they stay in place without falling (confirmed by ROM analysis).",
    },
    "hack_dialog.group.stage_frame": {"ja": "ステージ外枠", "en": "Stage Border"},
    "hack_dialog.stage_frame.checkbox": {"ja": "ゲーム画面の外枠を白ブロック柄にする", "en": "Use white-block graphics for the gameplay border"},
    "hack_dialog.stage_frame.tooltip": {
        "ja": "ステージ外枠テーブルを外枠用白ブロック反復へ変更し、4つのCHRバンクすべてで対応CHRを白ブロック柄へ差し替えます。\n境界セル$F8や衝突判定、ステージデータ形式は変更しません。",
        "en": "Changes the stage-border table to repeated border white blocks, and replaces the corresponding CHR in all four CHR banks with white-block graphics.\nBoundary cell $F8, collision, and the stage data format are not changed.",
    },
    "hack_dialog.stage_frame.hint": {
        "ja": "ONにすると保存ROM/テストプレイROMの左右・下外枠が白ブロック柄になります。OFFに戻して適用すると外枠テーブルとハードコード済み原作CHRを復元します。",
        "en": "When ON, saved ROMs and test-play ROMs use white-block graphics on the left, right, and bottom borders. Turning it OFF and applying restores the border table and hardcoded original CHR.",
    },
    "hack_dialog.stage_frame.unknown": {
        "ja": "外枠タイル列またはCHRが既知値と一致しないため、このROMでは変更を無効化しています。",
        "en": "This ROM cannot edit the border because the border tile sequence or CHR does not match known values.",
    },
    "hack_dialog.jp_base_only": {"ja": "日本版ベースROM専用です。", "en": "Only JP-based ROMs are supported."},
    "hack_dialog.group.gap_fix": {"ja": "原作バグ回避", "en": "Original Bug Workaround"},
    "hack_dialog.gap_fix.checkbox": {"ja": "横穴侵入を安定させる", "en": "Stabilize side-gap entry"},
    "hack_dialog.gap_fix.tooltip": {
        "ja": "左/右の新規入力から設定フレーム中、上側角が壁・下側角が空間の時だけ上側の位相拒否bitを消します。\n上下とも壁の普通の壁では原作結果を変更しません。",
        "en": "During the configured window after a new Left/Right press, clears the upper phase-rejection bit only when the upper corner is solid and the lower corner is open.\nNormal walls with both corners solid remain unchanged.",
    },
    "hack_dialog.gap_fix.hint": {
        "ja": "横穴の少し上から、穴へ向かって入力し直すと入れます。押しっぱなしは原作どおりです。",
        "en": "Press toward the gap again shortly above it to enter. Holding the direction behaves as in the original game.",
    },
    "hack_dialog.gap_fix.frames": {"ja": "押し直し後の受付フレーム数:", "en": "Input window after a new press:"},
    "hack_dialog.group.dark_tempo": {"ja": "暗闇テンポ (全体共通・必ず明から開始)", "en": "Darkness Tempo (Global, Always Starts Bright)"},
    "hack_dialog.dark_tempo.light.label": {"ja": "明るい (見える):", "en": "Bright (visible):"},
    "hack_dialog.dark_tempo.dark.label": {"ja": "暗い (見えない):", "en": "Dark (hidden):"},
    "hack_dialog.dark_tempo.hint": {
        "ja": "60フレーム≒1秒。既定: 明45/暗100。暗闇面を1つでも設定して保存すると有効。",
        "en": "60 frames is about 1 second. Default: bright 45 / dark 100. Takes effect after saving with at least one darkness stage configured.",
    },
    "hack_dialog.spark_ball_variant.max_digits": {
        "ja": "停止するLIFE百の位は最大4個までです。",
        "en": "You can select up to four LIFE hundreds digits.",
    },
    "hack_dialog.time_estimate.never": {"ja": "目安: 減らない", "en": "Estimate: does not decrease"},
    "hack_dialog.time_estimate.minutes": {"ja": "目安: 約{minutes}分{seconds:02d}秒", "en": "Estimate: about {minutes}m {seconds:02d}s"},
    "hack_dialog.time_estimate.seconds": {"ja": "目安: 約{seconds}秒", "en": "Estimate: about {seconds}s"},
    "hack_dialog.setting.start_stage": {"ja": "開始ステージ", "en": "Starting Stage"},
    "hack_dialog.setting.continue_limit": {"ja": "コンティニュー上限", "en": "Continue Limit"},
    "hack_dialog.setting.final_stage_redirect": {"ja": "最終面への移行", "en": "Final-stage transition"},
    "hack_dialog.setting.warp_feather": {"ja": "ワープ羽", "en": "Warp Feather"},
    "hack_dialog.setting.initial_magic_max": {"ja": "初期魔法 最大数", "en": "Initial Magic max count"},
    "hack_dialog.setting.initial_magic_pattern": {"ja": "初期魔法 初期所持", "en": "Initial Magic starting scrolls"},
    "hack_dialog.setting.initial_lives": {"ja": "初期残数", "en": "Initial Lives"},
    "hack_dialog.setting.time_fast": {"ja": "ステージ制限時間 速い", "en": "Stage time limit fast"},
    "hack_dialog.setting.time_normal": {"ja": "ステージ制限時間 普通", "en": "Stage time limit normal"},
    "hack_dialog.setting.time_slow": {"ja": "ステージ制限時間 遅い", "en": "Stage time limit slow"},
    "hack_dialog.setting.solomon_seal_stage": {"ja": "ソロモンの封印 出現面", "en": "Solomon's Seal stages"},
    "hack_dialog.setting.wall_color": {"ja": "ステージ壁色", "en": "Stage wall colors"},
    "hack_dialog.setting.main_palette": {"ja": "メインパレット", "en": "Main palette"},
    "hack_dialog.setting.demo_wait": {"ja": "デモ操作 wait", "en": "Demo input wait"},
    "hack_dialog.setting.demo_joy": {"ja": "デモ操作 joy", "en": "Demo input joy"},
    "hack_dialog.setting.enemy_drop_c278": {"ja": "敵ドロップ C278", "en": "Enemy drop C278"},
    "hack_dialog.setting.enemy_drop_c293": {"ja": "敵ドロップ C293", "en": "Enemy drop C293"},
    "hack_dialog.setting.clear_message": {"ja": "クリア画面メッセージ", "en": "Clear-screen message"},
    "hack_dialog.setting.bonus_positions": {"ja": "ボーナスステージ配置", "en": "Bonus stage positions"},
    "hack_dialog.setting.bonus_items": {"ja": "ボーナスステージアイテム", "en": "Bonus stage items"},
    "hack_dialog.setting.meta_position": {"ja": "メタ項目座標: {name}", "en": "Meta object position: {name}"},
    "hack_dialog.setting.walk_speed": {"ja": "ダーナ歩行速度", "en": "Dana walk speed"},
    "hack_dialog.setting.panel_cooldown": {"ja": "パネルモンスター クールダウン", "en": "Panel Monster cooldown"},
    "hack_dialog.setting.panel_bullet_fix": {"ja": "パネルモンスター 弾の左右速度バグ修正", "en": "Panel Monster bullet left/right speed fix"},
    "hack_dialog.setting.panel_bullet_speed": {"ja": "パネルモンスター 弾速度", "en": "Panel Monster bullet speed"},
    "hack_dialog.setting.panel_variant": {"ja": "パネルモンスター A/B/C/D共通値", "en": "Panel Monster A/B/C/D shared values"},
    "hack_dialog.setting.demo_stage": {"ja": "デモステージ", "en": "Demo stage"},
    "hack_dialog.setting.golem_snappy": {"ja": "ゴブリン キビキビ", "en": "Goblin snappy behavior"},
    "hack_dialog.setting.saramandor_variant_speed": {"ja": "強化サラマンダー 炎の速度", "en": "Enhanced Saramandor flame speed"},
    "hack_dialog.setting.saramandor_variant_refire_wait": {"ja": "強化サラマンダー 最低歩行時間", "en": "Enhanced Saramandor minimum walk time"},
    "hack_dialog.setting.saramandor_variant_post_fire_stop": {"ja": "強化サラマンダー 発射後停止時間", "en": "Enhanced Saramandor post-fire stop"},
    "hack_dialog.setting.saramandor_variant_abc": {"ja": "強化サラマンダーA/B/C", "en": "Enhanced Saramandor A/B/C"},
    "hack_dialog.setting.gargoyle_snappy": {"ja": "ガーゴイル キビキビ", "en": "Gargoyle snappy behavior"},
    "hack_dialog.setting.gargoyle_cooldown": {"ja": "ガーゴイル クールダウン", "en": "Gargoyle cooldown"},
    "hack_dialog.setting.gargoyle_variant_a": {"ja": "強化ガーゴイルA", "en": "Enhanced Gargoyle A"},
    "hack_dialog.setting.gargoyle_variant_b": {"ja": "強化ガーゴイルB", "en": "Enhanced Gargoyle B"},
    "hack_dialog.setting.dragon_snappy": {"ja": "ドラゴン キビキビ", "en": "Dragon snappy behavior"},
    "hack_dialog.setting.shared_flame_wait": {"ja": "火吐き開始待ち", "en": "Flame startup wait"},
    "hack_dialog.setting.shared_walk": {"ja": "共通移動速度", "en": "Shared move speed"},
    "hack_dialog.setting.neul_ghost_speed": {"ja": "ゴースト＆ヌエル移動速度", "en": "Ghost & Neul move speed"},
    "hack_dialog.setting.spark_ball_speed": {"ja": "スパークボール移動速度", "en": "Spark Ball move speed"},
    "hack_dialog.setting.spark_ball_pause": {"ja": "強化スパークボール停止", "en": "Enhanced Spark Ball pause"},
    "hack_dialog.setting.spark_ball_transparency": {"ja": "強化スパークボール透明化", "en": "Enhanced Spark Ball transparency"},
    "hack_dialog.setting.demonhead_snappy": {"ja": "デーモンヘッド キビキビ", "en": "Demon Head snappy behavior"},
    "hack_dialog.setting.clear_screen_char": {"ja": "クリア画面キャラ", "en": "Clear-screen character"},
    "hack_dialog.setting.stage_frame": {"ja": "ステージ外枠", "en": "Stage border"},
    "hack_dialog.setting.gap_fix": {"ja": "横穴侵入安定化", "en": "Side-gap entry stabilization"},
    "hack_dialog.setting.gap_fix_frames": {"ja": "横穴侵入 許可フレーム", "en": "Side-gap entry window"},
    "hack_dialog.setting.dark_light": {"ja": "暗闇 明フレーム", "en": "Darkness bright frames"},
    "hack_dialog.setting.dark_dark": {"ja": "暗闇 暗フレーム", "en": "Darkness dark frames"},
    "hack_dialog.applied.start_stage.default": {"ja": "開始ステージ → 1面", "en": "Starting stage -> Stage 1"},
    "hack_dialog.applied.start_stage": {"ja": "開始ステージ → {stage}面", "en": "Starting stage -> Stage {stage}"},
    "hack_dialog.applied.continue_limit": {"ja": "コンティニュー上限 → {stage}", "en": "Continue limit -> {stage}"},
    "hack_dialog.applied.final_stage.original": {"ja": "最終ステージ → {stage}面をクリアした後（原作）", "en": "Final stage -> after clearing Stage {stage} (original)"},
    "hack_dialog.applied.final_stage": {"ja": "最終ステージ → {stage}面をクリアした後", "en": "Final stage -> after clearing Stage {stage}"},
    "hack_dialog.log.final_stage_changed": {"ja": "最終ステージ設定を変更", "en": "Changed final-stage setting"},
    "hack_dialog.log.enemy_drop_changed": {"ja": "敵ドロップ効果表 $C293 書換", "en": "Changed enemy drop effect table $C293"},
    "hack_dialog.log.demo_input_changed": {"ja": "デモ操作データ ($CF9A/$CFBC) 書換", "en": "Changed demo input data ($CF9A/$CFBC)"},
    "hack_dialog.log.clear_message_changed": {"ja": "クリア画面メッセージ ($94DB/$94ED/$9507) 書換", "en": "Changed clear-screen message ($94DB/$94ED/$9507)"},
    "hack_dialog.solomon_seal.no_clear_air": {
        "ja": "封印{seal}: {stage}面に配置可能な空気マスがありません。",
        "en": "Seal {seal}: Stage {stage} has no air cell where it can be placed.",
    },
    "hack_dialog.solomon_seal.relocation_note": {
        "ja": "封印{seal}: {stage}面 {old_pos} -> {new_pos}",
        "en": "Seal {seal}: Stage {stage} {old_pos} -> {new_pos}",
    },
    "hack_dialog.applied.solomon_seal_stage": {"ja": "ソロモンの封印 出現面: {changes}", "en": "Solomon's Seal stages: {changes}"},
    "hack_dialog.applied.solomon_seal_relocation": {"ja": "ソロモンの封印 位置補正: {changes}", "en": "Solomon's Seal position adjustment: {changes}"},
    "hack_dialog.applied.initial_magic": {"ja": "初期魔法: {changes}", "en": "Initial Magic: {changes}"},
    "hack_dialog.applied.initial_lives": {"ja": "初期残数: {changes}", "en": "Initial Lives: {changes}"},
    "hack_dialog.applied.time_decrease": {"ja": "ステージ制限時間: {changes}", "en": "Stage time limit: {changes}"},
    "hack_dialog.applied.wall_color": {"ja": "ステージ壁色: {changes}", "en": "Stage wall colors: {changes}"},
    "hack_dialog.applied.walk_speed": {"ja": "歩行速度 → {mult:g}x ({changes})", "en": "Walk speed -> {mult:g}x ({changes})"},
    "hack_dialog.applied.panel_monster": {"ja": "パネルモンスター: {changes}", "en": "Panel Monster: {changes}"},
    "hack_dialog.applied.demo_stage": {"ja": "デモプレイ: {changes}", "en": "Demo play: {changes}"},
    "hack_dialog.applied.golem": {"ja": "ゴブリン: {changes}", "en": "Goblin: {changes}"},
    "hack_dialog.applied.saramandor_variant": {"ja": "強化サラマンダー: {changes}", "en": "Enhanced Saramandor: {changes}"},
    "hack_dialog.applied.gargoyle": {"ja": "ガーゴイル: {changes}", "en": "Gargoyle: {changes}"},
    "hack_dialog.applied.gargoyle_variant": {"ja": "強化ガーゴイル: {changes}", "en": "Enhanced Gargoyle: {changes}"},
    "hack_dialog.applied.dragon": {"ja": "ドラゴン: {changes}", "en": "Dragon: {changes}"},
    "hack_dialog.applied.shared_flame_wait": {"ja": "火吐き開始待ち: {changes}", "en": "Flame startup wait: {changes}"},
    "hack_dialog.applied.shared_walk": {"ja": "共通移動速度: {changes}", "en": "Shared move speed: {changes}"},
    "hack_dialog.applied.neul_ghost": {"ja": "ゴースト＆ヌエル: {changes}", "en": "Ghost & Neul: {changes}"},
    "hack_dialog.applied.spark_ball": {"ja": "スパークボール: {changes}", "en": "Spark Ball: {changes}"},
    "hack_dialog.applied.spark_ball_variant": {"ja": "強化スパークボール: {changes}", "en": "Enhanced Spark Ball: {changes}"},
    "hack_dialog.applied.demonhead": {"ja": "デーモンヘッド: {changes}", "en": "Demon Head: {changes}"},
    "hack_dialog.applied.clear_screen_char": {"ja": "クリア画面キャラ → {name}", "en": "Clear-screen character -> {name}"},
    "hack_dialog.applied.stage_frame": {"ja": "ステージ外枠: {changes}", "en": "Stage border: {changes}"},
    "hack_dialog.applied.gap_fix": {"ja": "横穴侵入安定化 {state}", "en": "Side-gap entry stabilization {state}"},
    "hack_dialog.applied.dark_tempo": {"ja": "暗闇テンポ → 明{light}/暗{dark}フレーム", "en": "Darkness tempo -> bright {light} / dark {dark} frames"},
    "hack_dialog.error.warp_feather": {"ja": "ワープ羽 設定失敗", "en": "Warp Feather Setting Failed"},
    "hack_dialog.error.solomon_seal_stage": {"ja": "ソロモンの封印 出現面 設定失敗", "en": "Solomon's Seal Stage Setting Failed"},
    "hack_dialog.error.initial_magic": {"ja": "初期魔法 設定失敗", "en": "Initial Magic Setting Failed"},
    "hack_dialog.error.initial_lives": {"ja": "初期残数 設定失敗", "en": "Initial Lives Setting Failed"},
    "hack_dialog.error.time_decrease": {"ja": "ステージ制限時間 設定失敗", "en": "Stage Time Limit Setting Failed"},
    "hack_dialog.error.wall_color": {"ja": "ステージ壁色 設定失敗", "en": "Stage Wall Color Setting Failed"},
    "hack_dialog.error.walk_speed": {"ja": "歩行速度の改造失敗", "en": "Walk Speed Tweak Failed"},
    "hack_dialog.error.panel_monster": {"ja": "パネルモンスター改造失敗", "en": "Panel Monster Tweak Failed"},
    "hack_dialog.error.panel_bullet_speed": {"ja": "パネルモンスター弾速度修正失敗", "en": "Panel Monster Bullet Speed Fix Failed"},
    "hack_dialog.error.demo_stage": {"ja": "デモステージ改造失敗", "en": "Demo Stage Tweak Failed"},
    "hack_dialog.error.golem": {"ja": "ゴブリン改造失敗", "en": "Goblin Tweak Failed"},
    "hack_dialog.error.saramandor_variant": {"ja": "強化サラマンダー設定失敗", "en": "Enhanced Saramandor Setting Failed"},
    "hack_dialog.error.gargoyle": {"ja": "ガーゴイル改造失敗", "en": "Gargoyle Tweak Failed"},
    "hack_dialog.error.gargoyle_variant": {"ja": "強化ガーゴイル設定失敗", "en": "Enhanced Gargoyle Setting Failed"},
    "hack_dialog.error.dragon": {"ja": "ドラゴン改造失敗", "en": "Dragon Tweak Failed"},
    "hack_dialog.error.shared_flame_wait": {"ja": "火吐き開始待ち設定失敗", "en": "Flame Startup Wait Setting Failed"},
    "hack_dialog.error.shared_walk": {"ja": "共通移動速度改造失敗", "en": "Shared Move Speed Tweak Failed"},
    "hack_dialog.error.neul_ghost": {"ja": "ゴースト＆ヌエル速度改造失敗", "en": "Ghost & Neul Speed Tweak Failed"},
    "hack_dialog.error.spark_ball": {"ja": "スパークボール速度改造失敗", "en": "Spark Ball Speed Tweak Failed"},
    "hack_dialog.error.spark_ball_variant": {"ja": "強化スパークボール設定失敗", "en": "Enhanced Spark Ball Setting Failed"},
    "hack_dialog.error.demonhead": {"ja": "デーモンヘッド改造失敗", "en": "Demon Head Tweak Failed"},
    "hack_dialog.error.clear_screen": {"ja": "クリア画面改造失敗", "en": "Clear Screen Tweak Failed"},
    "hack_dialog.error.stage_frame": {"ja": "ステージ外枠 設定失敗", "en": "Stage Border Setting Failed"},
    "hack_dialog.error.gap_fix": {"ja": "横穴侵入安定化 失敗", "en": "Side-gap Entry Stabilization Failed"},
    "hack_dialog.error.dark_tempo": {"ja": "暗闇テンポ設定 失敗", "en": "Darkness Tempo Setting Failed"},
    "hack_dialog.revert.confirm.body": {
        "ja": "このダイアログで設定した項目を全てデフォルト（オリジナル値）に戻します。\n適用するには [適用] または [OK] を押してください。\n\n続行しますか？",
        "en": "Restore every item in this dialog to its default original value.\nPress Apply or OK to apply the restored values.\n\nContinue?",
    },
    "hack_dialog.group.related_edit": {"ja": "関連編集", "en": "Related Editors"},
    "hack_dialog.related.enemy_drop.button": {"ja": "敵ドロップ編集", "en": "Enemy Drop Editor"},
    "hack_dialog.related.enemy_drop.tooltip": {
        "ja": "敵を炎で倒した時に出る効果(スコア/1UP/特殊等)と確率をグローバルに編集 ($C293)。通常アイテムIDではない点に注意",
        "en": "Globally edits effects and odds when enemies are defeated by fire, such as score, 1UP, and special effects ($C293). These are not normal item IDs.",
    },
    "hack_dialog.related.demo_input.button": {"ja": "デモ操作編集", "en": "Demo Input Editor"},
    "hack_dialog.related.demo_input.tooltip": {
        "ja": "タイトル放置で流れるデモの操作(34ステップ固定)を編集。各ステップ=入力を何フレーム続けるか。録画不要・原作方式手入力($CF9A/$CFBC、JP専用)",
        "en": "Edits the title idle demo input sequence (fixed 34 steps). Each step controls how many frames an input is held. Manual original-format input; no recording required ($CF9A/$CFBC, JP only).",
    },
    "hack_dialog.related.clear_message.button": {"ja": "クリア画面メッセージ編集", "en": "Clear Message Editor"},
    "hack_dialog.related.clear_message.tooltip": {
        "ja": "ステージクリア後の『おめでとう画面』3行を編集。英大文字+スペース、原作と同字数まで(JP専用・同字数置換)",
        "en": "Edits the three lines on the stage-clear congratulations screen. Uppercase English letters and spaces only, up to the original character counts (JP only, same-length replacement).",
    },
    "hack_dialog.export.button": {"ja": "共通設定をエクスポート...", "en": "Export Common Settings..."},
    "hack_dialog.export.tooltip": {
        "ja": "このダイアログの共通設定をJSONファイルに保存します",
        "en": "Saves this dialog's common settings to a JSON file.",
    },
    "hack_dialog.import.button": {"ja": "共通設定をインポート...", "en": "Import Common Settings..."},
    "hack_dialog.import.tooltip": {
        "ja": "JSONファイルから共通設定を読み込み、画面の値に反映します",
        "en": "Loads common settings from a JSON file and applies them to the on-screen values.",
    },
    "hack_dialog.revert.button": {"ja": "オリジナル値に戻す", "en": "Restore Original Values"},
    "hack_dialog.revert.tooltip": {
        "ja": "このダイアログで設定した項目を全てデフォルトに戻します",
        "en": "Restores all items in this dialog to their default values.",
    },
    "hack_dialog.export.title": {"ja": "共通設定をエクスポート", "en": "Export Common Settings"},
    "hack_dialog.export.failed": {"ja": "エクスポート失敗", "en": "Export Failed"},
    "hack_dialog.export.complete.title": {"ja": "エクスポート完了", "en": "Export Complete"},
    "hack_dialog.export.complete.body": {"ja": "共通設定を保存しました:\n{path}", "en": "Saved common settings:\n{path}"},
    "hack_dialog.import.confirm.title": {"ja": "共通設定インポートの確認", "en": "Confirm Common Settings Import"},
    "hack_dialog.import.confirm.body": {
        "ja": (
            "これから選択する共通設定を読み込むと、メインパレット、ステージ壁色、デモ操作、敵ドロップ、"
            "クリア画面メッセージ、ボーナスステージ、ソロモンの紋章/Page座標などROMデータは"
            "読み込み時点で反映されます。\n\n"
            "この操作はUndoできません。元に戻す可能性がある場合は、先に現在の共通設定を"
            "エクスポートしてください。\n\n"
            "共通設定ファイルを選択しますか？"
        ),
        "en": (
            "When you load the selected common settings, ROM data such as the main palette, stage wall colors, "
            "demo input, enemy drops, clear-screen messages, bonus stage, and Solomon's Seal/Page positions "
            "will be applied immediately at load time.\n\n"
            "This operation cannot be undone. Export the current common settings first if you may need to restore them.\n\n"
            "Select a common settings file?"
        ),
    },
    "hack_dialog.import.title": {"ja": "共通設定をインポート", "en": "Import Common Settings"},
    "hack_dialog.import.failed": {"ja": "インポート失敗", "en": "Import Failed"},
    "hack_dialog.import.format_error.title": {"ja": "形式エラー", "en": "Format Error"},
    "hack_dialog.import.format_error.not_global": {
        "ja": "このファイルは共通設定JSONではありません。",
        "en": "This file is not a common settings JSON file.",
    },
    "hack_dialog.import.format_error.no_settings": {
        "ja": "settings が見つからないか不正です。",
        "en": "settings is missing or invalid.",
    },
    "hack_dialog.import.complete.title": {"ja": "インポート完了", "en": "Import Complete"},
    "hack_dialog.import.complete.body": {
        "ja": "共通設定を読み込みました。\n一部のROMデータは読み込み時点で反映済みです。\n画面上の設定値は [適用] または [OK] で反映されます。",
        "en": "Loaded common settings.\nSome ROM data has already been applied at load time.\nOn-screen setting values are applied with Apply or OK.",
    },
    "hack_dialog.import.changed_header": {"ja": "\n\n変更された項目:\n", "en": "\n\nChanged items:\n"},
    "hack_dialog.import.no_changes": {"ja": "\n\n現在の画面値と同じ内容でした。", "en": "\n\nThe contents matched the current on-screen values."},
    "hack_dialog.apply.complete.title": {"ja": "適用完了", "en": "Apply Complete"},
    "hack_dialog.apply.complete.header": {"ja": "以下の項目を変更しました:\n\n", "en": "Changed the following items:\n\n"},
    "hack_dialog.apply.complete.footer": {
        "ja": "\n\n※ 改造ROMとして保存しないと永続化されません。",
        "en": "\n\nThese changes are not permanent until you save as a modified ROM.",
    },
    "hack_dialog.apply.no_changes.title": {"ja": "変更なし", "en": "No Changes"},
    "hack_dialog.apply.no_changes.body": {"ja": "書き換えられた箇所はありません。", "en": "No locations were changed."},
    "common.file_filter.json": {"ja": "JSON (*.json);;All Files (*)", "en": "JSON (*.json);;All Files (*)"},
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
    "mirror_dialog.phase1.label": {
        "ja": "Phase 1:",
        "en": "Phase 1:",
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
            "Shows mirror enemy sets, enemy lifetime, and 64-tick spawn patterns for every stage. "
            "X=spawn, .=none, -=initial tick ignored by the game."
        ),
    },
    "mirror_overview.column.level": {
        "ja": "Lv",
        "en": "Lv",
    },
    "mirror_overview.column.ttl": {
        "ja": "\u6575\u751f\u5b58\u6642\u9593",
        "en": "Enemy Lifetime",
    },
    "mirror_overview.lifetime.value": {
        "ja": "{value}\uff08\u7d04{seconds}\u79d2\uff09",
        "en": "{value} (about {seconds}s)",
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
    "main.expanded_rom_required": {
        "ja": "拡張ROMを読み込んだ状態で使用できます。",
        "en": "Available after loading an expanded ROM.",
    },
    "main.mirror_off.unavailable.title": {
        "ja": "ミラーOFF",
        "en": "Mirror Off",
    },
    "main.mirror_off.confirm.title": {
        "ja": "ミラー出現タイミングをOFF",
        "en": "Turn Mirror Spawn Timing Off",
    },
    "main.mirror_off.confirm.body": {
        "ja": "Stage {stage} のミラー1/2の出現タイミングをすべてOFFにしますか？",
        "en": "Turn off all Mirror 1/2 spawn timings for Stage {stage}?",
    },
    "main.mirror_off.already": {
        "ja": "ミラー1/2はすでに全OFFです",
        "en": "Mirror 1/2 spawn timings are already all off.",
    },
    "main.mirror_off.done": {
        "ja": "ミラー1/2の出現タイミングを全OFFにしました",
        "en": "Turned off all Mirror 1/2 spawn timings.",
    },
    "main.mirror_toggle.state.on_gap6": {
        "ja": "ON（6空け）",
        "en": "ON (6-gap)",
    },
    "main.mirror_toggle.done": {
        "ja": "ミラー{mirror}の出現タイミングを{state}にしました",
        "en": "Set Mirror {mirror} spawn timing to {state}.",
    },
    "main.mirror_toggle.done_lifetime_raised": {
        "ja": "\u30df\u30e9\u30fc{mirror}\u306e\u51fa\u73fe\u30bf\u30a4\u30df\u30f3\u30b0\u3092{state}\u306b\u3057\u3001\u6575\u751f\u5b58\u6642\u9593\u30928\u306b\u3057\u307e\u3057\u305f",
        "en": "Set Mirror {mirror} spawn timing to {state} and raised enemy lifetime to 8.",
    },
    "main.clear_level.mode.all": {
        "ja": "すべての編集対象（ブロック/アイテム/敵）",
        "en": "all editable objects (blocks/items/enemies)",
    },
    "main.clear_level.mode.blocks": {
        "ja": "ブロック",
        "en": "blocks",
    },
    "main.clear_level.mode.items": {
        "ja": "アイテム",
        "en": "items",
    },
    "main.clear_level.mode.enemies": {
        "ja": "モンスター",
        "en": "monsters",
    },
    "main.clear_level.confirm": {
        "ja": "L{level} の{label}を削除します。よろしいですか？\n（Undo可能）",
        "en": "Delete {label} from L{level}?\nYou can undo this.",
    },
    "main.clear_level.key_enemy_blocked": {
        "ja": "鍵メタが無いため、鍵持ち敵を含むモンスター削除はできません",
        "en": "Cannot delete monsters containing the key carrier because key metadata is missing.",
    },
    "main.clear_level.done": {
        "ja": "L{level}: {label}をクリア（Ctrl+Zで戻せます）",
        "en": "L{level}: cleared {label} (Ctrl+Z to undo)",
    },
    "main.undo.levels.more": {
        "ja": "{first} ほか{count}面",
        "en": "{first} and {count} more",
    },
    "main.keyboard_map.title": {
        "ja": "{app} v{version} ショートカットMAP",
        "en": "{app} v{version} Shortcut Map",
    },
    "main.keyboard_map.notes_html": {
        "ja": (
            "<b>マウス操作</b><br>\n"
            "左クリック: 選択中の要素を配置<br>\n"
            "右クリック: そのマスの要素を削除<br>\n"
            "左ドラッグ: 連続配置<br>\n"
            "右ドラッグ: 連続削除<br>\n"
            "Ctrl+左ドラッグ: 既存要素を移動<br>\n"
            "Ctrl+ホイール: 前/次ステージへ移動<br>\n"
            "Shift+左ドラッグ: 範囲選択<br>\n"
            "Alt+左クリック: スポイト（そのマスの要素をピッカーに取り込む）<br>\n"
            "<br>\n"
            "<b>範囲編集</b><br>\n"
            "ペーストは、選択範囲またはホバー位置を起点にします。<br>\n"
            "Delete/Backspaceは、選択範囲がある場合は範囲内削除、なければホバー位置削除です。<br>\n"
            "左右反転は、地形・アイテム・敵・敵の左右向き・スタート・鍵・扉・星座パネル・ミラー・六芒星などのメタ項目も反転します。<br>\n"
            "<br>\n"
            "<b>アイテム状態</b><br>\n"
            "Tab/Shift+Tab系は、ホバー位置のアイテム/鍵/扉状態を順送り/逆送りします。<br>\n"
            "隠しに変更した時、デーモンミラー上では隠しアイテム0x48を配置します。<br>\n"
            "<br>\n"
            "<b>ファイル読込</b><br>\n"
            ".nes / .zip はウィンドウへドラッグ&ドロップで読込できます。<br>\n"
            "コマンドライン例: python SOLOMON_CUSTOMIZER.py path/to/rom.nes<br>\n"
            "<br>\n"
            "<b>ゲームパッド</b><br>\n"
            "テストプレイ: {test_play}<br>\n"
            "前/次ステージ: {stage_prev} / {stage_next}<br>\n"
        ),
        "en": (
            "<b>Mouse</b><br>\n"
            "Left click: place the selected object<br>\n"
            "Right click: delete the object on that cell<br>\n"
            "Left drag: continuous placement<br>\n"
            "Right drag: continuous deletion<br>\n"
            "Ctrl+left drag: move an existing object<br>\n"
            "Ctrl+wheel: move to the previous/next stage<br>\n"
            "Shift+left drag: select a range<br>\n"
            "Alt+left click: eyedropper (load that cell's object into the picker)<br>\n"
            "<br>\n"
            "<b>Range Editing</b><br>\n"
            "Paste starts from the selection or the hovered cell.<br>\n"
            "Delete/Backspace deletes inside the selection if one exists, otherwise the hovered cell.<br>\n"
            "Horizontal/vertical flip also flips terrain, items, enemies, enemy facing, start, key, door, constellation panel, mirror, hexagram, and other meta objects.<br>\n"
            "<br>\n"
            "<b>Item State</b><br>\n"
            "Tab/Shift+Tab shortcuts cycle the hovered item/key/door state forward or backward.<br>\n"
            "When changing to hidden on a demon mirror, hidden item 0x48 is placed.<br>\n"
            "<br>\n"
            "<b>File Loading</b><br>\n"
            "Drag and drop .nes / .zip files onto the window to load them.<br>\n"
            "Command-line example: python SOLOMON_CUSTOMIZER.py path/to/rom.nes<br>\n"
            "<br>\n"
            "<b>Gamepad</b><br>\n"
            "Test play: {test_play}<br>\n"
            "Previous/next stage: {stage_prev} / {stage_next}<br>\n"
        ),
    },
    "common.confirm": {
        "ja": "確認",
        "en": "Confirm",
    },
    "common.unassigned": {
        "ja": "未割当",
        "en": "Unassigned",
    },
    "common.bullet_item": {
        "ja": "・{item}",
        "en": "- {item}",
    },
    "app.single_instance.activated": {
        "ja": "既に起動中のSOLOMON_CUSTOMIZERを前面に表示しました",
        "en": "Brought the already-running SOLOMON_CUSTOMIZER window to the front.",
    },
    "file_dialog.select_file": {
        "ja": "ファイルを選択",
        "en": "Select File",
    },
    "file_dialog.select_folder": {
        "ja": "フォルダを選択",
        "en": "Select Folder",
    },
    "file_dialog.select_save_path": {
        "ja": "保存先を選択",
        "en": "Select Save Destination",
    },
    "common.none": {"ja": "なし", "en": "None"},
    "title_screen_dialog.title": {"ja": "タイトル画面編集", "en": "Title Screen Editor"},
    "title_screen_dialog.tab.title": {"ja": "タイトル", "en": "Title"},
    "title_screen_dialog.tab.ending": {"ja": "エンディング", "en": "Ending"},
    "title_screen_dialog.tab.clear_screen": {"ja": "クリア画面", "en": "Clear Screen"},
    "title_screen_dialog.title_tab.info_html": {
        "ja": (
            "タイトル画面の<b>配置(nametable)・色区分(attribute)・絵(CHR bank3)・文字・キャラクター・パレット</b>を編集します。"
            "<br>下のプレビューではCHRタイルと色区分を確認でき、上部ロゴ領域は画像として保存・読み込みできます。"
        ),
        "en": (
            "Edit the title screen <b>layout (nametable), color regions (attribute), graphics (CHR bank3), text, characters, and palette</b>."
            "<br>The preview shows CHR tiles and color regions, and the upper logo area can be saved to or loaded from an image."
        ),
    },
    "title_screen_dialog.zoom.label": {"ja": "表示倍率:", "en": "Zoom:"},
    "title_screen_dialog.bank_offset.label": {"ja": "bank内:", "en": "Bank offset:"},
    "title_screen_dialog.highlight_tile.tooltip": {"ja": "指定したCHR bank3内タイルをタイトルプレビュー上でピンク表示", "en": "Highlights the selected CHR bank3 tile in pink on the title preview."},
    "title_screen_dialog.color_group_overlay.label": {"ja": "色グループ表示:", "en": "Color group overlay:"},
    "title_screen_dialog.color_group_overlay.tooltip": {"ja": "選択した色グループに属する16x16区画をプレビュー上で表示", "en": "Shows 16x16 regions that use the selected color group on the preview."},
    "title_screen_dialog.color_group_from.tooltip": {"ja": "一括置換元の色グループ", "en": "Source color group for batch replacement."},
    "title_screen_dialog.color_group_to.tooltip": {"ja": "一括置換先の色グループ", "en": "Destination color group for batch replacement."},
    "title_screen_dialog.color_group_replace.button": {"ja": "色G置換", "en": "Replace Color G"},
    "title_screen_dialog.color_group_replace.tooltip": {"ja": "選択した色グループを使う16x16区画を、別の色グループへ一括変更", "en": "Batch changes all 16x16 regions using the selected color group to another color group."},
    "title_screen_dialog.canvas.tooltip": {"ja": "左クリック: 8x8 CHRタイル編集 / 右クリック: 16x16色グループ変更", "en": "Left click: edit 8x8 CHR tile / Right click: change 16x16 color group"},
    "title_screen_dialog.save_top_png.button": {"ja": "Top PNG保存...", "en": "Save Top PNG..."},
    "title_screen_dialog.save_top_png.tooltip": {"ja": "タイトル上部ロゴ領域だけを256x64/4階調PNGで保存", "en": "Saves only the upper title-logo area as a 256x64 four-color PNG."},
    "title_screen_dialog.load_top_png.button": {"ja": "Top PNG読み込み...", "en": "Load Top PNG..."},
    "title_screen_dialog.load_top_png.tooltip": {"ja": "上部ロゴ領域のPNG/BMP/JPEGを読み込みます。256x64を超える画像は縮小し、4色へ減色します。", "en": "Loads a PNG/BMP/JPEG for the upper logo area. Images larger than 256x64 are scaled down and reduced to four colors."},
    "title_screen_dialog.text_edit.button": {"ja": "文字編集...", "en": "Edit Text..."},
    "title_screen_dialog.text_edit.tooltip": {"ja": "タイトル中央付近の追加文字とPUSH START位置の固定文字を編集します。A-Z / 0-9 / スペース / , . \" が使えます。入力中にプレビューへ反映します。", "en": "Edits the added text near the center of the title and fixed text at the PUSH START position. A-Z / 0-9 / space / , . \" can be used. The preview updates while editing."},
    "title_screen_dialog.tile_place.button": {"ja": "タイル配置...", "en": "Tile Placement..."},
    "title_screen_dialog.tile_place.tooltip": {"ja": "CHR bank3の8x8タイルを選び、タイトル背景の32x30マスへ配置します。", "en": "Choose 8x8 tiles from CHR bank3 and place them on the 32x30 title background grid."},
    "title_screen_dialog.character.button": {"ja": "キャラクター...", "en": "Characters..."},
    "title_screen_dialog.character.tooltip": {"ja": "$D0E8由来の16x16キャラを選び、タイトル上へ最大{count}体配置します。", "en": "Choose 16x16 characters from $D0E8 data and place up to {count} of them on the title screen."},
    "title_screen_dialog.palette.button": {"ja": "パレット変更...", "en": "Edit Palette..."},
    "title_screen_dialog.palette.tooltip": {"ja": "タイトル画面のBGパレット16色($3F00-$3F0F)を編集します。", "en": "Edits the 16 BG palette colors for the title screen ($3F00-$3F0F)."},
    "title_screen_dialog.revert.button": {"ja": "変更を取り消す", "en": "Revert Changes"},
    "title_screen_dialog.revert.tooltip": {"ja": "このダイアログを開いた時点の ROM に戻す", "en": "Restore the ROM to the state it had when this dialog was opened."},
    "title_screen_dialog.clear_tab.info": {"ja": "ステージクリア後の『おめでとう画面』に関係する設定です。ここでは既存のクリア画面キャラ差し替えとメッセージ編集を扱います。プレビューは実機エミュレーションではなく、文字位置確認用の簡易表示です。", "en": "Settings related to the congratulations screen after clearing a stage. This tab handles the existing clear-screen character replacement and message editing. The preview is a simple text-position check, not hardware emulation."},
    "title_screen_dialog.clear_message.group": {"ja": "クリア画面メッセージ", "en": "Clear Screen Message"},
    "title_screen_dialog.clear_message.hint": {"ja": "THANK YOU DANA / YOU RELEASED THIS ROOM / TRY NEXT ROOM の3行を編集します。英大文字 A-Z とスペースのみ、同字数置換です。", "en": "Edits the three lines THANK YOU DANA / YOU RELEASED THIS ROOM / TRY NEXT ROOM. Uppercase A-Z and spaces only, same-length replacement."},
    "title_screen_dialog.clear_message.column.line": {"ja": "行", "en": "Line"},
    "title_screen_dialog.clear_message.column.text": {"ja": "文字", "en": "Text"},
    "title_screen_dialog.clear_message.column.count": {"ja": "字数", "en": "Count"},
    "title_screen_dialog.clear_message.unavailable": {"ja": "編集不可: {error}", "en": "Cannot edit: {error}"},
    "title_screen_dialog.clear_screen_char.group": {"ja": "クリア画面のキャラ (おめでとう画面の2体)", "en": "Clear Screen Characters (Two Congratulations-Screen Sprites)"},
    "title_screen_dialog.clear_screen_char.unavailable": {"ja": "使用不可: {type}: {error}", "en": "Unavailable: {type}: {error}"},
    "title_screen_dialog.clear_screen_char.label": {"ja": "表示キャラ:", "en": "Displayed character:"},
    "title_screen_dialog.clear_screen_char.hint": {"ja": "ステージクリア画面で左右に出る2体を差し替えます。既存のゲーム挙動改造にあった設定と同じ処理です。", "en": "Replaces the two sprites shown on the left and right of the stage-clear screen. This is the same setting that previously existed in Game Behavior Tweaks."},
    "title_screen_dialog.ending_tab.info": {"ja": "エンディングの文字列だけを編集します。表示位置や改行などの制御データは維持します。英大文字 A-Z / スペース / , ' \" のみ使用できます。", "en": "Edits only the ending text strings. Control data such as positions and line breaks is preserved. Only uppercase A-Z / space / , ' \" can be used."},
    "title_screen_dialog.ending_tab.unavailable": {"ja": "エンディング文字列を編集できません: {error}", "en": "Cannot edit ending text: {error}"},
    "title_screen_dialog.ending.view": {"ja": "表示:", "en": "View:"},
    "title_screen_dialog.ending.true": {"ja": "真エンディング", "en": "True Ending"},
    "title_screen_dialog.ending.good_a": {"ja": "グッドエンディング A", "en": "Good Ending A"},
    "title_screen_dialog.ending.good_b": {"ja": "グッドエンディング B", "en": "Good Ending B"},
    "title_screen_dialog.ending.bad_a": {"ja": "バッドエンディング A", "en": "Bad Ending A"},
    "title_screen_dialog.ending.bad_b": {"ja": "バッドエンディング B", "en": "Bad Ending B"},
    "title_screen_dialog.ending.worst": {"ja": "ワーストエンディング", "en": "Worst Ending"},
    "title_screen_dialog.ending.column.line": {"ja": "行", "en": "Line"},
    "title_screen_dialog.ending.column.text": {"ja": "文字", "en": "Text"},
    "title_screen_dialog.ending.column.count": {"ja": "字数", "en": "Count"},
    "title_screen_dialog.ending.condition.princess_both": {"ja": "条件: 王女あり / 両方取得", "en": "Condition: Princess / both items"},
    "title_screen_dialog.ending.condition.princess_one": {"ja": "条件: 王女あり / 片方取得", "en": "Condition: Princess / one item"},
    "title_screen_dialog.ending.condition.princess_none": {"ja": "条件: 王女あり / 取得なし", "en": "Condition: Princess / no items"},
    "title_screen_dialog.ending.condition.no_princess_both": {"ja": "条件: 王女なし / 両方取得", "en": "Condition: No princess / both items"},
    "title_screen_dialog.ending.condition.no_princess_one": {"ja": "条件: 王女なし / 片方取得", "en": "Condition: No princess / one item"},
    "title_screen_dialog.ending.condition.no_princess_none": {"ja": "条件: 王女なし / 取得なし", "en": "Condition: No princess / no items"},
    "pixel.status.eyedropper": {
        "ja": "スポイト: ペン{value}を選択",
        "en": "Eyedropper: selected pen {value}",
    },
    "pixel.status.undo": {"ja": "元に戻しました。", "en": "Undid the edit."},
    "pixel.status.redo": {"ja": "やり直しました。", "en": "Redid the edit."},
    "pixel.status.flip_h": {"ja": "左右反転しました。", "en": "Flipped horizontally."},
    "pixel.status.flip_v": {"ja": "上下反転しました。", "en": "Flipped vertically."},
    "pixel.status.clear": {"ja": "クリアしました。", "en": "Cleared."},
    "pixel.status.imported": {"ja": "画像を取り込みました。", "en": "Imported the image."},
    "pixel.status.wrote_rom": {"ja": "ROMへ書き込みました。", "en": "Wrote to ROM."},
    "pixel.status.copied": {"ja": "16x16全体をコピーしました。", "en": "Copied the full 16x16 image."},
    "pixel.status.pasted": {"ja": "16x16全体を貼り付けました。", "en": "Pasted the full 16x16 image."},
    "pixel.status.copied_all_banks": {
        "ja": "全{count}個のCHRバンクへ書き込みました。",
        "en": "Wrote to all {count} CHR banks.",
    },
    "pixel.info.dirty_suffix": {"ja": " / 未書込", "en": " / pending"},
    "pixel.info.selection": {
        "ja": "選択範囲: ({x1},{y1})-({x2},{y2}) {width}x{height}<br>",
        "en": "Selection: ({x1},{y1})-({x2},{y2}) {width}x{height}<br>",
    },
    "pixel.info.chr_pair": {
        "ja": "左CHR: {left0}, {left1} / 右CHR: {right0}, {right1}<br>",
        "en": "Left CHR: {left0}, {left1} / Right CHR: {right0}, {right1}<br>",
    },
    "pixel.info.palette_attr": {
        "ja": "表示SPRパレット: 左#{left_pal} 右#{right_pal} / attr=${attr:02X} / 参照数:{refs}{dirty}<br>",
        "en": "Displayed SPR palette: left #{left_pal}, right #{right_pal} / attr=${attr:02X} / refs: {refs}{dirty}<br>",
    },
    "pixel.info.hint": {
        "ja": "右クリックまたはペン0で透明色。CHR共有タイルを使う別フレームも同時に見た目が変わります。",
        "en": "Right-click or use pen 0 for transparency. Other frames using the same shared CHR tiles will visually change too.",
    },
    "element_picker.enemy.phantom_preset.right": {
        "ja": "ファントムプリセット（右）",
        "en": "Phantom Preset (right)",
    },
    "element_picker.enemy.phantom_preset.left": {
        "ja": "ファントムプリセット（左）",
        "en": "Phantom Preset (left)",
    },
    "element_picker.enemy.phantom_preset.up": {
        "ja": "ファントムプリセット（上）",
        "en": "Phantom Preset (up)",
    },
    "element_picker.enemy.phantom_preset.down": {
        "ja": "ファントムプリセット（下）",
        "en": "Phantom Preset (down)",
    },
    "element_picker.enemy.phantom_preset.group_direction": {
        "ja": "ファントムバレット{group}（{direction}）",
        "en": "Phantom Bullet {group} ({direction})",
    },
    "element_picker.enemy.ghost_preset.group_direction": {
        "ja": "強化ゴースト{group}（{direction}）",
        "en": "Enhanced Ghost {group} ({direction})",
    },
    "element_picker.enemy.neul_preset.group_direction": {
        "ja": "強化ヌエル{group}（{direction}）",
        "en": "Enhanced Neul {group} ({direction})",
    },
    "element_picker.direction.right": {
        "ja": "右",
        "en": "right",
    },
    "element_picker.direction.left": {
        "ja": "左",
        "en": "left",
    },
    "element_picker.direction.up": {
        "ja": "上",
        "en": "up",
    },
    "element_picker.direction.down": {
        "ja": "下",
        "en": "down",
    },
    "hack_dialog.group.phantom_preset": {
        "ja": "ファントムバレット プリセット A-D",
        "en": "Phantom Bullet Presets A-D",
    },
    "hack_dialog.phantom_preset.speed.label": {
        "ja": "速度値:",
        "en": "Velocity byte:",
    },
    "hack_dialog.phantom_preset.amplitude.label": {
        "ja": "振幅:",
        "en": "Amplitude:",
    },
    "hack_dialog.phantom_preset.phase.label": {
        "ja": "サインテーブル開始位置:",
        "en": "Sine table start:",
    },
    "hack_dialog.phantom_preset.speed.short": {
        "ja": "速度",
        "en": "Speed",
    },
    "hack_dialog.phantom_preset.amplitude.short": {
        "ja": "振幅",
        "en": "Amplitude",
    },
    "hack_dialog.phantom_preset.phase.short": {
        "ja": "開始位置",
        "en": "Start",
    },
    "hack_dialog.setting.phantom_preset_speed": {
        "ja": "ファントム{group} 速度値",
        "en": "Phantom group {group} velocity byte",
    },
    "hack_dialog.setting.phantom_preset_amplitude": {
        "ja": "ファントム{group} 振幅",
        "en": "Phantom group {group} amplitude",
    },
    "hack_dialog.setting.phantom_preset_phase": {
        "ja": "ファントム{group} サインテーブル開始位置",
        "en": "Phantom group {group} sine table start",
    },
    "hack_dialog.applied.phantom_preset": {
        "ja": "ファントムプリセット: {settings}",
        "en": "Phantom presets: {settings}",
    },
    "hack_dialog.applied.phantom_preset.group": {
        "ja": "{group}: 速度=${speed:02X}、振幅={amplitude}%、開始位置={phase}",
        "en": "{group}: speed=${speed:02X}, amplitude={amplitude}%, start={phase}",
    },
    "hack_dialog.error.phantom_preset": {
        "ja": "ファントムプリセット設定失敗",
        "en": "Phantom Preset settings failed",
    },
    "hack_dialog.group.ghost_ab": {
        "ja": "ゴースト強化版 A-F",
        "en": "Enhanced Ghost A-F",
    },
    "hack_dialog.group.neul_ab": {
        "ja": "ヌエル強化版 A/B",
        "en": "Enhanced Neul A/B",
    },
    "hack_dialog.neul_ab.body_speed.short": {
        "ja": "本体速度",
        "en": "Body speed",
    },
    "hack_dialog.neul_ab.fire_interval.short": {
        "ja": "発射間隔",
        "en": "Fire interval",
    },
    "hack_dialog.neul_ab.bullet_speed.short": {
        "ja": "弾速度",
        "en": "Bullet speed",
    },
    "hack_dialog.neul_ab.body_speed.normal": {
        "ja": "通常",
        "en": "Normal",
    },
    "hack_dialog.neul_ab.body_speed.fast": {
        "ja": "高速",
        "en": "Fast",
    },
    "hack_dialog.neul_ab.bullet_speed.stock": {
        "ja": "原作",
        "en": "Stock",
    },
    "hack_dialog.neul_ab.bullet_speed.quarter": {
        "ja": "1/4",
        "en": "1/4",
    },
    "hack_dialog.neul_ab.bullet_speed.half": {
        "ja": "1/2",
        "en": "1/2",
    },
    "hack_dialog.neul_ab.bullet_speed.double": {
        "ja": "2倍",
        "en": "2x",
    },
    "hack_dialog.neul_ab.bullet_speed.triple": {
        "ja": "3倍",
        "en": "3x",
    },
    "hack_dialog.ghost_ab.body_speed.short": {
        "ja": "本体速度",
        "en": "Body speed",
    },
    "hack_dialog.ghost_ab.fire_interval.short": {
        "ja": "発射間隔",
        "en": "Fire interval",
    },
    "hack_dialog.ghost_ab.bullet_speed.short": {
        "ja": "弾速度",
        "en": "Bullet speed",
    },
    "hack_dialog.ghost_ab.fire_direction.short": {
        "ja": "発射方向",
        "en": "Fire direction",
    },
    "hack_dialog.ghost_ab.fire_direction.backward": {
        "ja": "後方",
        "en": "Backward",
    },
    "hack_dialog.ghost_ab.fire_direction.up": {
        "ja": "上",
        "en": "Up",
    },
    "hack_dialog.ghost_ab.fire_direction.down": {
        "ja": "下",
        "en": "Down",
    },
    "hack_dialog.ghost_ab.body_speed.normal": {
        "ja": "通常",
        "en": "Normal",
    },
    "hack_dialog.ghost_ab.body_speed.fast": {
        "ja": "高速",
        "en": "Fast",
    },
    "hack_dialog.ghost_ab.bullet_speed.stock": {
        "ja": "原作",
        "en": "Stock",
    },
    "hack_dialog.ghost_ab.bullet_speed.quarter": {
        "ja": "1/4",
        "en": "1/4",
    },
    "hack_dialog.ghost_ab.bullet_speed.half": {
        "ja": "1/2",
        "en": "1/2",
    },
    "hack_dialog.ghost_ab.bullet_speed.double": {
        "ja": "2倍",
        "en": "2x",
    },
    "hack_dialog.ghost_ab.bullet_speed.triple": {
        "ja": "3倍",
        "en": "3x",
    },
    "hack_dialog.frames_suffix": {
        "ja": " フレーム",
        "en": " frames",
    },
    "hack_dialog.setting.ghost_ab_body_speed": {
        "ja": "ゴースト{group} 本体速度",
        "en": "Ghost {group} body speed",
    },
    "hack_dialog.setting.neul_ab_body_speed": {
        "ja": "ヌエル{group} 本体速度",
        "en": "Neul {group} body speed",
    },
    "hack_dialog.setting.neul_ab_fire_interval": {
        "ja": "ヌエル{group} 発射間隔",
        "en": "Neul {group} fire interval",
    },
    "hack_dialog.setting.neul_ab_bullet_speed": {
        "ja": "ヌエル{group} 弾速度",
        "en": "Neul {group} bullet speed",
    },
    "hack_dialog.setting.ghost_ab_fire_interval": {
        "ja": "ゴースト{group} 発射間隔",
        "en": "Ghost {group} fire interval",
    },
    "hack_dialog.setting.ghost_ab_bullet_speed": {
        "ja": "ゴースト{group} 弾速度",
        "en": "Ghost {group} bullet speed",
    },
    "hack_dialog.setting.ghost_ab_fire_direction": {
        "ja": "ゴースト{group} 発射方向",
        "en": "Ghost {group} fire direction",
    },
    "hack_dialog.applied.ghost_ab": {
        "ja": "ゴースト強化版: {settings}",
        "en": "Enhanced Ghost: {settings}",
    },
    "hack_dialog.applied.ghost_ab.group": {
        "ja": "{group}: 本体=${body:02X}、間隔={interval}、弾=${bullet:02X}、方向={direction}",
        "en": "{group}: body=${body:02X}, interval={interval}, bullet=${bullet:02X}, direction={direction}",
    },
    "hack_dialog.error.ghost_ab": {
        "ja": "ゴースト強化版設定失敗",
        "en": "Enhanced Ghost settings failed",
    },
    "hack_dialog.applied.neul_ab": {
        "ja": "ヌエル強化版: {settings}",
        "en": "Enhanced Neul: {settings}",
    },
    "hack_dialog.applied.neul_ab.group": {
        "ja": "{group}: 本体=${body:02X}、間隔={interval}、弾=${bullet:02X}",
        "en": "{group}: body=${body:02X}, interval={interval}, bullet=${bullet:02X}",
    },
    "hack_dialog.error.neul_ab": {
        "ja": "ヌエル強化版設定失敗",
        "en": "Enhanced Neul settings failed",
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
    "config.save_error.title": {
        "ja": "設定を保存できません",
        "en": "Could not save settings",
    },
    "config.save_error.message": {
        "ja": "設定は現在の画面には反映されましたが、設定ファイルへ保存できませんでした。\n書き込み権限とディスクの空き容量を確認してください。",
        "en": "The settings were applied to the current session, but could not be saved to the settings file.\nCheck write permissions and available disk space.",
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


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def _existing_text_lookup(language: str) -> dict:
    lookup = {}
    for entry in _TRANSLATIONS.values():
        if not isinstance(entry, dict):
            continue
        translated = entry.get(language) or entry.get(DEFAULT_LANGUAGE)
        if not translated:
            continue
        for source_language in SUPPORTED_LANGUAGES:
            source = entry.get(source_language)
            if source:
                lookup.setdefault(source, translated)
    return lookup


def translate_existing_text(value: str) -> str:
    """Translate an already-created static UI string by exact dictionary match."""
    text = str(value or "")
    if not text:
        return text
    lookup = _existing_text_lookup(_current_language)
    translated = lookup.get(text)
    if translated:
        return translated
    if text.endswith(":"):
        translated = lookup.get(text[:-1])
        if translated:
            return translated + ":"
    return text
