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
