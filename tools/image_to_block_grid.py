#!/usr/bin/env python3
"""GUI and CLI converter for a 15x12 grid of four Solomon block types.

Run without arguments to open the drag-and-drop GUI. The tool emits a preview
PNG and a JSON grid with these stable values:

    0 = air
    1 = brown wall
    2 = white wall
    3 = cracked wall

The GUI uses PyQt5 and image conversion uses Pillow.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


GRID_WIDTH = 15
GRID_HEIGHT = 12
GRID_CELL_COUNT = GRID_WIDTH * GRID_HEIGHT
MANUAL_COUNT_MAX = GRID_CELL_COUNT - 3
DEFAULT_TILE_SIZE = 32
ASSET_DIR = Path(__file__).with_name("image_to_block_grid_assets")

AIR = 0
BROWN = 1
WHITE = 2
CRACKED = 3

TYPE_NAMES = {
    AIR: "air",
    BROWN: "brown",
    WHITE: "white",
    CRACKED: "cracked",
}
TYPE_SYMBOLS = {
    AIR: ".",
    BROWN: "B",
    WHITE: "W",
    CRACKED: "C",
}


def _apportion_counts(weights, total: int, minimum=0) -> list[int]:
    """Distribute an integer total proportionally without a rounding remainder."""
    weights = [max(0.0, float(value)) for value in weights]
    if isinstance(minimum, (list, tuple)):
        minimums = [max(0, int(value)) for value in minimum]
        if len(minimums) != len(weights):
            raise ValueError("minimum count must match weight count")
    else:
        minimums = [max(0, int(minimum))] * len(weights)
    if total < sum(minimums):
        raise ValueError("total is too small for the requested minimum")
    if total == sum(minimums):
        return minimums
    weight_total = sum(weights)
    if weight_total <= 0:
        weights = [1.0] * len(weights)
        weight_total = float(len(weights))
    raw = [value * total / weight_total for value in weights]
    result = [max(minimums[i], int(value)) for i, value in enumerate(raw)]
    while sum(result) < total:
        index = max(
            range(len(result)),
            key=lambda i: (raw[i] - result[i], -i),
        )
        result[index] += 1
    while sum(result) > total:
        candidates = [
            i for i, value in enumerate(result) if value > minimums[i]
        ]
        index = max(candidates, key=lambda i: (result[i] - raw[i], -i))
        result[index] -= 1
    return result


def _thresholds_to_counts(
    air_end: float,
    crack_end: float,
    brown_end: float,
) -> list[int]:
    weights = [
        air_end,
        crack_end - air_end,
        brown_end - crack_end,
        1.0 - brown_end,
    ]
    return _apportion_counts(weights, GRID_CELL_COUNT, minimum=1)


def _counts_to_thresholds(counts) -> tuple[float, float, float]:
    values = [int(value) for value in counts]
    if len(values) != 4 or min(values) < 0 or sum(values) != GRID_CELL_COUNT:
        raise ValueError("four nonnegative counts must cover the full grid")
    return (
        values[0] / GRID_CELL_COUNT,
        (values[0] + values[1]) / GRID_CELL_COUNT,
        (values[0] + values[1] + values[2]) / GRID_CELL_COUNT,
    )


def _redistribute_counts(
    counts,
    changed_index: int,
    new_value: int,
) -> list[int]:
    values = [int(value) for value in counts]
    if len(values) != 4 or sum(values) != GRID_CELL_COUNT or min(values) < 0:
        raise ValueError("four nonnegative counts must cover the full grid")
    if changed_index not in range(4):
        raise IndexError(changed_index)
    new_value = max(0, min(MANUAL_COUNT_MAX, int(new_value)))
    other_indices = [index for index in range(4) if index != changed_index]
    redistributed = _apportion_counts(
        [values[index] for index in other_indices],
        GRID_CELL_COUNT - new_value,
        minimum=[1 if values[index] > 0 else 0 for index in other_indices],
    )
    result = list(values)
    result[changed_index] = new_value
    for index, value in zip(other_indices, redistributed):
        result[index] = value
    return result


def _parse_rgb(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise argparse.ArgumentTypeError("RGB color must be RRGGBB or #RRGGBB")
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid RGB color: {value}") from exc


def _fit_image(
    image: Image.Image,
    size: tuple[int, int],
    fit: str,
    background: tuple[int, int, int],
    selection_box: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    source = image.convert("RGBA")
    matte = Image.new("RGBA", source.size, (*background, 255))
    matte.alpha_composite(source)
    rgb = matte.convert("RGB")

    if fit == "stretch":
        return rgb.resize(size, Image.Resampling.LANCZOS)
    if fit == "selection":
        if selection_box is None:
            raise ValueError("selection mode requires a selection box")
        left, top, right, bottom = selection_box
        left = max(0, min(rgb.width - 1, int(left)))
        top = max(0, min(rgb.height - 1, int(top)))
        right = max(left + 1, min(rgb.width, int(right)))
        bottom = max(top + 1, min(rgb.height, int(bottom)))
        return rgb.crop((left, top, right, bottom)).resize(
            size, Image.Resampling.LANCZOS)
    return ImageOps.fit(rgb, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _four_level_grid(
    gray: Image.Image,
    invert: bool,
    air_end: float,
    crack_end: float,
    brown_end: float,
    source_rgb: Image.Image | None = None,
    target_counts=None,
    normalize_range: bool = True,
) -> tuple[Image.Image, list[list[int]]]:
    pixels = list(gray.tobytes())
    kind_values = (AIR, CRACKED, BROWN, WHITE)
    tone_by_kind = {AIR: 0, CRACKED: 85, BROWN: 170, WHITE: 255}

    if target_counts is not None:
        counts = [int(value) for value in target_counts]
        if len(counts) != 4 or min(counts) < 0 or sum(counts) != len(pixels):
            raise ValueError("target block counts must cover every grid cell")
        if source_rgb is not None and source_rgb.size == gray.size:
            rgb_bytes = source_rgb.convert("RGB").tobytes()
            rgb_pixels = [
                tuple(rgb_bytes[index:index + 3])
                for index in range(0, len(rgb_bytes), 3)
            ]
        else:
            rgb_pixels = [(value, value, value) for value in pixels]

        def rank_key(index):
            red, green, blue = rgb_pixels[index]
            fine_luma = 299 * red + 587 * green + 114 * blue
            brightness = -fine_luma if invert else fine_luma
            # RGB and row-major position provide a stable, non-random tie break.
            return (brightness, red, green, blue, index)

        ranked_indices = sorted(range(len(pixels)), key=rank_key)
        kinds = [AIR] * len(pixels)
        cursor = 0
        for kind, count in zip(kind_values, counts):
            for index in ranked_indices[cursor:cursor + count]:
                kinds[index] = kind
            cursor += count
        tones = [tone_by_kind[kind] for kind in kinds]
        four_tone = Image.new("L", gray.size)
        four_tone.putdata(tones)
        grid = [
            kinds[y * GRID_WIDTH:(y + 1) * GRID_WIDTH]
            for y in range(GRID_HEIGHT)
        ]
        return four_tone, grid

    low = min(pixels)
    high = max(pixels)
    span = high - low
    kinds: list[int] = []
    normalized_values: list[float] = []

    for value in pixels:
        if normalize_range:
            normalized = 0.5 if span == 0 else (value - low) / span
        else:
            normalized = value / 255.0
        if invert:
            normalized = 1.0 - normalized
        # Keep the maximum sample inside the last non-zero half-open band.
        normalized = min(normalized, 1.0 - 1e-12)
        normalized_values.append(normalized)
        if normalized < air_end:
            level = 0
        elif normalized < crack_end:
            level = 1
        elif normalized < brown_end:
            level = 2
        else:
            level = 3
        kinds.append(kind_values[level])

    bounds = (0.0, air_end, crack_end, brown_end, 1.0)
    positive = [bounds[i + 1] - bounds[i] > 1e-12 for i in range(4)]
    counts = {kind: kinds.count(kind) for kind in kind_values}
    for level, kind in enumerate(kind_values):
        if not positive[level] or counts[kind] > 0:
            continue
        midpoint = (bounds[level] + bounds[level + 1]) / 2.0
        candidates = []
        for index, current_kind in enumerate(kinds):
            current_level = kind_values.index(current_kind)
            donor_minimum = 1 if positive[current_level] else 0
            if counts[current_kind] > donor_minimum:
                candidates.append(index)
        if not candidates:
            continue
        selected = min(
            candidates,
            key=lambda index: (abs(normalized_values[index] - midpoint), index),
        )
        old_kind = kinds[selected]
        counts[old_kind] -= 1
        kinds[selected] = kind
        counts[kind] += 1

    tones = [tone_by_kind[kind] for kind in kinds]

    four_tone = Image.new("L", gray.size)
    four_tone.putdata(tones)
    grid = [
        kinds[y * GRID_WIDTH:(y + 1) * GRID_WIDTH]
        for y in range(GRID_HEIGHT)
    ]
    return four_tone, grid


def _enlarge_stage(image: Image.Image, size: tuple[int, int] = (240, 192)) -> Image.Image:
    return image.convert("RGB").resize(size, Image.Resampling.NEAREST)


def _brick_tile(
    size: int,
    fill: tuple[int, int, int],
    mortar: tuple[int, int, int],
) -> Image.Image:
    tile = Image.new("RGB", (size, size), fill)
    draw = ImageDraw.Draw(tile)
    unit = max(4, size // 4)
    width = max(1, size // 24)
    for y in range(0, size + 1, unit):
        draw.line((0, y, size, y), fill=mortar, width=width)
        row = y // unit
        offset = unit if row % 2 else 0
        for x in range(-offset, size + unit * 2, unit * 2):
            draw.line((x, y, x, min(size, y + unit)), fill=mortar, width=width)
    return tile


def _default_tiles(size: int) -> dict[int, Image.Image]:
    air = _brick_tile(size, (20, 22, 25), (31, 34, 38))
    brown = _brick_tile(size, (126, 52, 10), (77, 30, 7))
    white = _brick_tile(size, (207, 210, 207), (141, 146, 145))
    cracked = brown.copy()
    draw = ImageDraw.Draw(cracked)
    scale = size / 32.0
    points = [
        (int(8 * scale), 0),
        (int(13 * scale), int(7 * scale)),
        (int(10 * scale), int(13 * scale)),
        (int(19 * scale), int(19 * scale)),
        (int(15 * scale), int(25 * scale)),
        (int(23 * scale), size - 1),
    ]
    draw.line(points, fill=(245, 224, 174), width=max(1, size // 16))
    draw.line(
        (int(11 * scale), int(12 * scale), int(3 * scale), int(17 * scale)),
        fill=(245, 224, 174),
        width=max(1, size // 20),
    )
    return {AIR: air, BROWN: brown, WHITE: white, CRACKED: cracked}


def _load_tile(path: Path, size: int) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.fit(image.convert("RGB"), (size, size), Image.Resampling.NEAREST)


def _tile_set(args: argparse.Namespace) -> dict[int, Image.Image]:
    tiles = _default_tiles(args.tile_size)
    bundled = {
        AIR: ASSET_DIR / "air.png",
        BROWN: ASSET_DIR / "brown.png",
        WHITE: ASSET_DIR / "white.png",
        CRACKED: ASSET_DIR / "cracked.png",
    }
    for kind, path in bundled.items():
        if path.is_file():
            tiles[kind] = _load_tile(path, args.tile_size)
    custom = {
        AIR: args.tile_air,
        BROWN: args.tile_brown,
        WHITE: args.tile_white,
        CRACKED: args.tile_cracked,
    }
    for kind, path in custom.items():
        if path is not None:
            tiles[kind] = _load_tile(path, args.tile_size)
    return tiles


def _render_preview(
    grid: list[list[int]],
    tiles: dict[int, Image.Image],
    tile_size: int,
) -> Image.Image:
    width = GRID_WIDTH * tile_size
    height = GRID_HEIGHT * tile_size
    preview = Image.new("RGB", (width, height))
    for y, row in enumerate(grid):
        for x, kind in enumerate(row):
            preview.paste(tiles[kind], (x * tile_size, y * tile_size))
    draw = ImageDraw.Draw(preview)
    grid_color = (65, 69, 74)
    for x in range(GRID_WIDTH + 1):
        draw.line((x * tile_size, 0, x * tile_size, height), fill=grid_color, width=1)
    for y in range(GRID_HEIGHT + 1):
        draw.line((0, y * tile_size, width, y * tile_size), fill=grid_color, width=1)
    return preview


def _available_paths(
    output_dir: Path,
    stem: str,
    overwrite: bool,
) -> tuple[Path, Path]:
    png = output_dir / f"{stem}_block_grid.png"
    data = output_dir / f"{stem}_block_grid.json"
    if overwrite or (not png.exists() and not data.exists()):
        return png, data
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        output_dir / f"{stem}_block_grid_{stamp}.png",
        output_dir / f"{stem}_block_grid_{stamp}.json",
    )


def _write_json(
    path: Path,
    source: Path,
    grid: list[list[int]],
    args: argparse.Namespace,
) -> None:
    counts = {
        TYPE_NAMES[kind]: sum(cell == kind for row in grid for cell in row)
        for kind in TYPE_NAMES
    }
    payload = {
        "source": str(source),
        "width": GRID_WIDTH,
        "height": GRID_HEIGHT,
        "encoding": {
            "0": "air",
            "1": "brown",
            "2": "white",
            "3": "cracked",
        },
        "settings": {
            "method": (
                "ranked_exact_counts"
                if getattr(args, "target_counts", None) is not None
                else "resize_then_grayscale_4level"
            ),
            "fit": args.fit,
            "invert": args.invert,
            "air_end": args.air_end,
            "crack_end": args.crack_end,
            "brown_end": args.brown_end,
            "target_counts": getattr(args, "target_counts", None),
            "selection_box": (
                list(args.selection_box)
                if getattr(args, "selection_box", None) else None
            ),
        },
        "counts": counts,
        "symbols": ["".join(TYPE_SYMBOLS[cell] for cell in row) for row in grid],
        "cells": grid,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an image into a 15x12 four-type Solomon block grid."
    )
    parser.add_argument("input", type=Path, nargs="?", help="source image")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="open the GUI, optionally with the input image preloaded",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("exports/image_to_block_grid"),
        help="output directory (default: exports/image_to_block_grid)",
    )
    parser.add_argument("--name", help="output name stem (default: input stem)")
    parser.add_argument(
        "--fit",
        choices=("crop", "selection", "stretch"),
        default="stretch",
        help="how to fit the source to a 15:12 aspect ratio",
    )
    parser.add_argument("--background", type=_parse_rgb, default=(16, 18, 20))
    parser.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE)
    parser.add_argument("--air-end", type=float, default=0.25)
    parser.add_argument("--crack-end", type=float, default=0.50)
    parser.add_argument("--brown-end", type=float, default=0.75)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--tile-air", type=Path)
    parser.add_argument("--tile-brown", type=Path)
    parser.add_argument("--tile-white", type=Path)
    parser.add_argument("--tile-cracked", type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing existing output files",
    )
    return parser


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.input is None:
        parser.error("an input image is required in CLI mode")
    if not args.input.is_file():
        parser.error(f"input image does not exist: {args.input}")
    if args.tile_size < 8:
        parser.error("--tile-size must be at least 8")
    if not 0.0 < args.air_end < args.crack_end < args.brown_end < 1.0:
        parser.error("brightness boundaries must satisfy 0 < air < crack < brown < 1")
    if args.fit == "selection" and not getattr(args, "selection_box", None):
        parser.error("selection fit is available in GUI mode")
    for option in (args.tile_air, args.tile_brown, args.tile_white, args.tile_cracked):
        if option is not None and not option.is_file():
            parser.error(f"tile image does not exist: {option}")


def _convert_source(
    args: argparse.Namespace,
) -> tuple[Image.Image, list[list[int]], dict[str, Image.Image]]:
    with Image.open(args.input) as source:
        fitted = _fit_image(
            source,
            (GRID_WIDTH, GRID_HEIGHT),
            args.fit,
            args.background,
            getattr(args, "selection_box", None),
        )
    gray = ImageOps.grayscale(fitted)
    four_tone, grid = _four_level_grid(
        gray,
        args.invert,
        args.air_end,
        args.crack_end,
        args.brown_end,
        source_rgb=fitted,
        target_counts=getattr(args, "target_counts", None),
    )
    tiles = _tile_set(args)
    preview = _render_preview(grid, tiles, args.tile_size)
    stages = {
        "resized": _enlarge_stage(fitted),
        "grayscale": _enlarge_stage(gray),
        "four_tone": _enlarge_stage(four_tone),
    }
    return preview, grid, stages


def _run_cli(args: argparse.Namespace) -> int:
    preview, grid, _stages = _convert_source(args)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or args.input.stem
    png_path, json_path = _available_paths(args.output_dir, stem, args.overwrite)
    preview.save(png_path, "PNG")
    _write_json(json_path, args.input, grid, args)

    print(f"preview: {png_path}")
    print(f"grid:    {json_path}")
    return 0


UI_TEXT = {
    "ja": {
        "title": "画像から15x12ブロック変換",
        "open": "画像を開く",
        "save": "結果を保存",
        "source": "0. 入力画像",
        "resized": "1. 15×12へ縮小（カラー）",
        "grayscale": "2. グレースケール",
        "four_tone": "3. 明るさを4段階化",
        "result": "4. ブロック割当",
        "drop": "ここへ画像をドラッグ＆ドロップ",
        "fit": "画像の合わせ方",
        "stretch": "全体を15x12へ縮小",
        "crop": "中央を切り抜く",
        "selection": "赤枠で任意範囲を選択",
        "thresholds": "ブロック個数（合計180個）",
        "air_count": "空気",
        "cracked_count": "ひび",
        "brown_count": "茶",
        "white_count": "白",
        "count_value": "{name}: {count}個",
        "equal_counts": "各45個に均等化",
        "reload_image": "画像を読み直す",
        "air_end": "空気 / ひび",
        "crack_end": "ひび / 茶",
        "brown_end": "茶 / 白",
        "selection_help": "カーソル形状が変わる位置で移動・拡大縮小。通常モードでも元画像をドラッグすると範囲選択へ切り替わります。",
        "invert": "明暗を反転",
        "ready": "画像をドロップするか、開くボタンで選択してください。",
        "loaded": "変換完了",
        "open_title": "変換する画像を選択",
        "save_title": "変換結果PNGを保存",
        "images": "画像 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)",
        "png": "PNG画像 (*.png)",
        "error": "変換エラー",
        "saved": "保存しました: {png} / {json}",
        "no_result": "保存できる変換結果がありません。",
        "apply": "現在のステージへ適用",
    },
    "en": {
        "title": "Image to 15x12 Block Grid",
        "open": "Open Image",
        "save": "Save Result",
        "source": "0. Source Image",
        "resized": "1. Resize to 15x12 (Color)",
        "grayscale": "2. Grayscale",
        "four_tone": "3. Four Brightness Levels",
        "result": "4. Assign Block Types",
        "drop": "Drag and drop an image here",
        "fit": "Image Fit",
        "stretch": "Scale entire image to 15x12",
        "crop": "Crop from center",
        "selection": "Select any area with red frame",
        "thresholds": "Block Counts (Total 180)",
        "air_count": "Air",
        "cracked_count": "Cracked",
        "brown_count": "Brown",
        "white_count": "White",
        "count_value": "{name}: {count}",
        "equal_counts": "Set 45 Each",
        "reload_image": "Reload Image",
        "air_end": "Air / Cracked",
        "crack_end": "Cracked / Brown",
        "brown_end": "Brown / White",
        "selection_help": "The cursor changes where the frame can be moved or resized. Dragging the source image in another fit mode switches to selection mode.",
        "invert": "Invert brightness",
        "ready": "Drop an image or select one with the Open button.",
        "loaded": "Conversion complete",
        "open_title": "Select an image to convert",
        "save_title": "Save converted grid PNG",
        "images": "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)",
        "png": "PNG image (*.png)",
        "error": "Conversion Error",
        "saved": "Saved: {png} / {json}",
        "no_result": "There is no converted result to save.",
        "apply": "Apply to Current Stage",
    },
}


def _ui_language() -> str:
    forced = os.environ.get("IMAGE_TO_BLOCK_GRID_LANGUAGE")
    if forced in UI_TEXT:
        return forced
    config_path = Path(__file__).resolve().parents[1] / "config" / "magatu_skc_config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return "en" if data.get("language") == "en" else "ja"
    except (OSError, ValueError, TypeError):
        return "ja"


def _pil_pixmap(image: Image.Image):
    from PyQt5.QtGui import QPixmap

    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap


def _run_gui(
    args: argparse.Namespace,
    apply_callback=None,
    parent=None,
    run_event_loop: bool = True,
    language: str | None = None,
):
    from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
    from PyQt5.QtGui import (
        QColor, QFont, QFontDatabase, QFontMetrics, QKeySequence, QPainter, QPen,
    )
    from PyQt5.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QShortcut,
        QSizePolicy,
        QSlider,
        QStyle,
        QVBoxLayout,
        QWidget,
    )

    language = language if language in UI_TEXT else _ui_language()
    text = UI_TEXT[language]

    class DropPreview(QLabel):
        def __init__(self, on_drop, message: str):
            super().__init__(message)
            self._on_drop = on_drop
            self.setAcceptDrops(True)
            self.setAlignment(Qt.AlignCenter)
            self.setFrameShape(QFrame.StyledPanel)
            self.setMinimumSize(220, 176)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setWordWrap(True)

        def dragEnterEvent(self, event):
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if any(url.isLocalFile() for url in urls):
                event.acceptProposedAction()

        def dropEvent(self, event):
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self._on_drop(Path(url.toLocalFile()))
                    event.acceptProposedAction()
                    return

    class BlockCountSlider(QSlider):
        def __init__(self, index, on_begin, on_end):
            super().__init__(Qt.Horizontal)
            self.setObjectName("blockCountSlider")
            self._index = index
            self._on_begin = on_begin
            self._on_end = on_end

        def mousePressEvent(self, event):
            self._on_begin(self._index)
            super().mousePressEvent(event)

        def mouseReleaseEvent(self, event):
            super().mouseReleaseEvent(event)
            self._on_end()

        def keyPressEvent(self, event):
            self._on_begin(self._index)
            super().keyPressEvent(event)
            self._on_end()

        def wheelEvent(self, event):
            self._on_begin(self._index)
            super().wheelEvent(event)
            self._on_end()

    class SourceSelection(QWidget):
        HANDLE = 10.0
        MIN_SIZE = 0.02

        def __init__(self, on_drop, on_changed, on_selection_requested):
            super().__init__()
            self._on_drop = on_drop
            self._on_changed = on_changed
            self._on_selection_requested = on_selection_requested
            self._pixmap = None
            self._source_size = (1, 1)
            self._selection = QRectF(0.0, 0.0, 1.0, 1.0)
            self._selection_enabled = False
            self._drag_mode = None
            self._drag_start = QPointF()
            self._drag_original = QRectF()
            self.setAcceptDrops(True)
            self.setMouseTracking(True)
            self.setMinimumSize(560, 360)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def set_source(self, image: Image.Image):
            self._pixmap = _pil_pixmap(image.convert("RGB"))
            self._source_size = image.size
            source_aspect = image.width / max(1, image.height)
            target_aspect = GRID_WIDTH / GRID_HEIGHT
            if source_aspect > target_aspect:
                width = target_aspect / source_aspect
                self._selection = QRectF((1.0 - width) / 2.0, 0.0, width, 1.0)
            else:
                height = source_aspect / target_aspect
                self._selection = QRectF(0.0, (1.0 - height) / 2.0, 1.0, height)
            self.update()

        def set_selection_enabled(self, enabled: bool):
            self._selection_enabled = bool(enabled)
            self.update()

        def selection_box(self) -> tuple[int, int, int, int]:
            width, height = self._source_size
            left = round(self._selection.left() * width)
            top = round(self._selection.top() * height)
            right = round(self._selection.right() * width)
            bottom = round(self._selection.bottom() * height)
            left = max(0, min(width - 1, left))
            top = max(0, min(height - 1, top))
            return (
                left,
                top,
                max(left + 1, min(width, right)),
                max(top + 1, min(height, bottom)),
            )

        def _image_rect(self) -> QRectF:
            area = QRectF(self.rect()).adjusted(8.0, 8.0, -8.0, -8.0)
            if self._pixmap is None:
                return area
            scale = min(
                area.width() / max(1, self._pixmap.width()),
                area.height() / max(1, self._pixmap.height()),
            )
            width = self._pixmap.width() * scale
            height = self._pixmap.height() * scale
            return QRectF(
                area.center().x() - width / 2.0,
                area.center().y() - height / 2.0,
                width,
                height,
            )

        def _selection_rect(self) -> QRectF:
            image_rect = self._image_rect()
            return QRectF(
                image_rect.left() + self._selection.left() * image_rect.width(),
                image_rect.top() + self._selection.top() * image_rect.height(),
                self._selection.width() * image_rect.width(),
                self._selection.height() * image_rect.height(),
            )

        def _normalized_point(self, point) -> QPointF:
            image_rect = self._image_rect()
            x = (point.x() - image_rect.left()) / max(1.0, image_rect.width())
            y = (point.y() - image_rect.top()) / max(1.0, image_rect.height())
            return QPointF(max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))

        def _hit_test(self, point) -> str:
            rect = self._selection_rect()
            near_left = abs(point.x() - rect.left()) <= self.HANDLE
            near_right = abs(point.x() - rect.right()) <= self.HANDLE
            near_top = abs(point.y() - rect.top()) <= self.HANDLE
            near_bottom = abs(point.y() - rect.bottom()) <= self.HANDLE
            within_x = rect.left() - self.HANDLE <= point.x() <= rect.right() + self.HANDLE
            within_y = rect.top() - self.HANDLE <= point.y() <= rect.bottom() + self.HANDLE
            parts = []
            if within_y and near_left:
                parts.append("left")
            elif within_y and near_right:
                parts.append("right")
            if within_x and near_top:
                parts.append("top")
            elif within_x and near_bottom:
                parts.append("bottom")
            if parts:
                return "_".join(parts)
            if rect.contains(point):
                return "move"
            return "new"

        def _cursor_for_mode(self, mode: str):
            if mode in ("left", "right"):
                return Qt.SizeHorCursor
            if mode in ("top", "bottom"):
                return Qt.SizeVerCursor
            if mode in ("left_top", "right_bottom"):
                return Qt.SizeFDiagCursor
            if mode in ("right_top", "left_bottom"):
                return Qt.SizeBDiagCursor
            if mode == "move":
                return Qt.SizeAllCursor
            return Qt.CrossCursor

        def _update_hover_cursor(self, point):
            if self._pixmap is None or not self._image_rect().contains(point):
                self.unsetCursor()
                return
            mode = self._hit_test(point) if self._selection_enabled else "new"
            self.setCursor(self._cursor_for_mode(mode))

        def _bounded_rect(self, rect: QRectF) -> QRectF:
            left = max(0.0, min(1.0, rect.left()))
            top = max(0.0, min(1.0, rect.top()))
            right = max(left + self.MIN_SIZE, min(1.0, rect.right()))
            bottom = max(top + self.MIN_SIZE, min(1.0, rect.bottom()))
            if right > 1.0:
                left = max(0.0, 1.0 - max(self.MIN_SIZE, rect.width()))
                right = 1.0
            if bottom > 1.0:
                top = max(0.0, 1.0 - max(self.MIN_SIZE, rect.height()))
                bottom = 1.0
            return QRectF(left, top, right - left, bottom - top)

        def mousePressEvent(self, event):
            if (
                event.button() != Qt.LeftButton
                or self._pixmap is None
                or not self._image_rect().contains(event.pos())
            ):
                return
            auto_started = not self._selection_enabled
            if auto_started:
                self._on_selection_requested()
                self._selection_enabled = True
            self._drag_mode = "new" if auto_started else self._hit_test(event.pos())
            self._drag_start = self._normalized_point(event.pos())
            self._drag_original = QRectF(self._selection)
            self.setCursor(self._cursor_for_mode(self._drag_mode))
            event.accept()

        def mouseMoveEvent(self, event):
            if self._drag_mode is None:
                self._update_hover_cursor(event.pos())
                return
            current = self._normalized_point(event.pos())
            original = self._drag_original
            if self._drag_mode == "new":
                rect = QRectF(self._drag_start, current).normalized()
            elif self._drag_mode == "move":
                dx = current.x() - self._drag_start.x()
                dy = current.y() - self._drag_start.y()
                x = max(0.0, min(1.0 - original.width(), original.x() + dx))
                y = max(0.0, min(1.0 - original.height(), original.y() + dy))
                rect = QRectF(x, y, original.width(), original.height())
            else:
                left, top = original.left(), original.top()
                right, bottom = original.right(), original.bottom()
                if "left" in self._drag_mode:
                    left = min(current.x(), right - self.MIN_SIZE)
                if "right" in self._drag_mode:
                    right = max(current.x(), left + self.MIN_SIZE)
                if "top" in self._drag_mode:
                    top = min(current.y(), bottom - self.MIN_SIZE)
                if "bottom" in self._drag_mode:
                    bottom = max(current.y(), top + self.MIN_SIZE)
                rect = QRectF(left, top, right - left, bottom - top)
            self._selection = self._bounded_rect(rect)
            self.update()
            event.accept()

        def mouseReleaseEvent(self, event):
            if self._drag_mode is None:
                return
            self._drag_mode = None
            self._on_changed()
            self._update_hover_cursor(event.pos())
            event.accept()

        def leaveEvent(self, event):
            if self._drag_mode is None:
                self.unsetCursor()
            super().leaveEvent(event)

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(24, 27, 30))
            if self._pixmap is None:
                painter.setPen(QColor(220, 220, 220))
                painter.drawText(self.rect(), Qt.AlignCenter, text["drop"])
                return
            image_rect = self._image_rect()
            painter.drawPixmap(image_rect.toRect(), self._pixmap)
            if not self._selection_enabled:
                return
            selection_rect = self._selection_rect()
            painter.setPen(QPen(QColor(255, 35, 35), 3))
            painter.drawRect(selection_rect)
            painter.setBrush(QColor(255, 35, 35))
            painter.setPen(Qt.NoPen)
            for point in (
                selection_rect.topLeft(), selection_rect.topRight(),
                selection_rect.bottomLeft(), selection_rect.bottomRight(),
            ):
                painter.drawRect(QRectF(point.x() - 4, point.y() - 4, 8, 8))

        def dragEnterEvent(self, event):
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if any(url.isLocalFile() for url in urls):
                event.acceptProposedAction()

        def dropEvent(self, event):
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self._on_drop(Path(url.toLocalFile()))
                    event.acceptProposedAction()
                    return

    class ConverterWindow(QMainWindow):
        def __init__(self):
            super().__init__(parent)
            self.source_path: Path | None = None
            self.source_image: Image.Image | None = None
            self.result_image: Image.Image | None = None
            self.result_grid: list[list[int]] | None = None
            self._natural_thresholds = (args.air_end, args.crack_end, args.brown_end)
            self.setWindowTitle(text["title"])
            self.resize(1320, 900)
            self.setAcceptDrops(True)

            root = QWidget()
            root.setStyleSheet(
                "QPushButton, QComboBox { min-height: 26px; }"
                "QGroupBox { font-weight: 600; }"
                "QSlider#blockCountSlider::groove:horizontal {"
                "  height: 6px; background: #0b210f; border: 1px solid #398944;"
                "  border-radius: 3px;"
                "}"
                "QSlider#blockCountSlider::sub-page:horizontal {"
                "  background: #18b82a; border-radius: 3px;"
                "}"
                "QSlider#blockCountSlider::handle:horizontal {"
                "  width: 16px; margin: -6px 0; border-radius: 8px;"
                "  background: #f5fff5; border: 2px solid #18ff2a;"
                "}"
                "QSlider#blockCountSlider::handle:horizontal:hover {"
                "  background: #fff36a; border-color: #ffffff;"
                "}"
                "QSlider#blockCountSlider::handle:horizontal:pressed {"
                "  background: #ffffff; border-color: #fff36a;"
                "}"
            )
            outer = QVBoxLayout(root)
            outer.setContentsMargins(14, 14, 14, 12)
            outer.setSpacing(10)

            toolbar = QHBoxLayout()
            self.open_button = QPushButton(text["open"])
            self.open_button.setMinimumWidth(132)
            self.open_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
            self.open_button.clicked.connect(self.open_image)
            toolbar.addWidget(self.open_button)

            self.save_button = QPushButton(text["save"])
            self.save_button.setMinimumWidth(132)
            self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
            self.save_button.clicked.connect(self.save_result)
            self.save_button.setEnabled(False)
            toolbar.addWidget(self.save_button)
            if apply_callback is not None:
                self.apply_button = QPushButton(text["apply"])
                self.apply_button.setMinimumWidth(168)
                self.apply_button.clicked.connect(self.apply_result)
                self.apply_button.setEnabled(False)
                toolbar.addWidget(self.apply_button)
            toolbar.addSpacing(12)

            toolbar.addWidget(QLabel(text["fit"]))
            self.fit_combo = QComboBox()
            self.fit_combo.setMinimumWidth(220)
            for key in ("stretch", "crop", "selection"):
                self.fit_combo.addItem(text[key], key)
            self.fit_combo.setCurrentIndex(max(0, self.fit_combo.findData(args.fit)))
            self.fit_combo.currentIndexChanged.connect(self.fit_changed)
            toolbar.addWidget(self.fit_combo)

            self.invert_check = QCheckBox(text["invert"])
            self.invert_check.setChecked(args.invert)
            self.invert_check.toggled.connect(self.convert)
            toolbar.addWidget(self.invert_check)
            toolbar.addStretch(1)
            outer.addLayout(toolbar)

            threshold_group = QGroupBox(text["thresholds"])
            threshold_layout = QHBoxLayout(threshold_group)
            self._block_counts = _thresholds_to_counts(
                args.air_end, args.crack_end, args.brown_end
            )
            self._updating_block_counts = False
            self._count_drag_index = None
            self._count_drag_baseline = None
            self.block_count_labels = []
            self.block_count_sliders = []
            count_keys = ("air_count", "cracked_count", "brown_count", "white_count")
            metrics = QFontMetrics(self.font())
            count_label_width = max(
                metrics.horizontalAdvance(text["count_value"].format(
                    name=text[key], count=888
                ))
                for key in count_keys
            ) + 10
            for index, key in enumerate(count_keys):
                label = QLabel()
                label.setFixedWidth(count_label_width)
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                slider = BlockCountSlider(
                    index, self.begin_count_drag, self.end_count_drag
                )
                # Automatic redistribution may reach 180 when the other three
                # counts were explicitly set to zero. User changes are clamped
                # to 177 by _redistribute_counts().
                slider.setRange(0, GRID_CELL_COUNT)
                slider.setValue(self._block_counts[index])
                slider.setMinimumWidth(100)
                slider.valueChanged.connect(
                    lambda value, i=index: self.block_count_changed(i, value)
                )
                self.block_count_labels.append((label, key))
                self.block_count_sliders.append(slider)
                threshold_layout.addWidget(label)
                threshold_layout.addWidget(slider, 1)
            self.equal_counts_button = QPushButton(text["equal_counts"])
            self.equal_counts_button.clicked.connect(self.equalize_block_counts)
            threshold_layout.addWidget(self.equal_counts_button)
            self.reload_image_button = QPushButton(text["reload_image"])
            self.reload_image_button.clicked.connect(self.reload_source_image)
            self.reload_image_button.setEnabled(False)
            threshold_layout.addWidget(self.reload_image_button)
            outer.addWidget(threshold_group)
            self.update_block_count_labels()

            large_previews = QHBoxLayout()
            source_group = QGroupBox(text["source"])
            source_layout = QVBoxLayout(source_group)
            self.source_preview = SourceSelection(
                self.load_image,
                self.selection_changed,
                self.request_selection_mode,
            )
            source_layout.addWidget(self.source_preview)
            selection_help = QLabel(text["selection_help"])
            selection_help.setWordWrap(True)
            source_layout.addWidget(selection_help)
            large_previews.addWidget(source_group, 1)

            result_group = QGroupBox(text["result"])
            result_layout = QVBoxLayout(result_group)
            self.result_preview = DropPreview(self.load_image, text["drop"])
            self.result_preview.setMinimumSize(560, 360)
            result_layout.addWidget(self.result_preview)
            large_previews.addWidget(result_group, 1)
            outer.addLayout(large_previews, 3)

            stages = QHBoxLayout()
            resized_group = QGroupBox(text["resized"])
            resized_layout = QVBoxLayout(resized_group)
            self.resized_preview = DropPreview(self.load_image, text["drop"])
            resized_layout.addWidget(self.resized_preview)
            stages.addWidget(resized_group, 1)

            grayscale_group = QGroupBox(text["grayscale"])
            grayscale_layout = QVBoxLayout(grayscale_group)
            self.grayscale_preview = DropPreview(self.load_image, text["drop"])
            grayscale_layout.addWidget(self.grayscale_preview)
            stages.addWidget(grayscale_group, 1)

            four_tone_group = QGroupBox(text["four_tone"])
            four_tone_layout = QVBoxLayout(four_tone_group)
            self.four_tone_preview = DropPreview(self.load_image, text["drop"])
            four_tone_layout.addWidget(self.four_tone_preview)
            stages.addWidget(four_tone_group, 1)
            outer.addLayout(stages, 1)

            self.status = QLabel(text["ready"])
            self.status.setMinimumHeight(24)
            outer.addWidget(self.status)
            self.setCentralWidget(root)
            self.source_preview.set_selection_enabled(
                self.fit_combo.currentData() == "selection")

            QShortcut(QKeySequence.Open, self, activated=self.open_image)
            QShortcut(QKeySequence.Save, self, activated=self.save_result)

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dropEvent(self, event):
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self.load_image(Path(url.toLocalFile()))
                    event.acceptProposedAction()
                    return

        def open_image(self):
            start = str(self.source_path.parent if self.source_path else Path.cwd())
            path, _ = QFileDialog.getOpenFileName(
                self, text["open_title"], start, text["images"]
            )
            if path:
                self.load_image(Path(path))

        def load_image(self, path: Path):
            try:
                with Image.open(path) as image:
                    source = image.convert("RGBA")
                    source.load()
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, text["error"], str(exc))
                return
            self.source_path = path
            self.source_image = source
            self.source_preview.set_source(source)
            self.initialize_counts_from_source()
            self.convert()
            self.reload_image_button.setEnabled(True)

        def initialize_counts_from_source(self):
            if self.source_image is None:
                return
            current = self.current_args()
            fitted = _fit_image(
                self.source_image,
                (GRID_WIDTH, GRID_HEIGHT),
                current.fit,
                current.background,
                current.selection_box,
            )
            gray = ImageOps.grayscale(fitted)
            _tone, grid = _four_level_grid(
                gray,
                current.invert,
                *self._natural_thresholds,
                source_rgb=fitted,
                target_counts=None,
                normalize_range=False,
            )
            counts = [
                sum(cell == kind for row in grid for cell in row)
                for kind in (AIR, CRACKED, BROWN, WHITE)
            ]
            self.set_block_counts(counts, convert=False)

        def update_block_count_labels(self):
            for index, (label, key) in enumerate(self.block_count_labels):
                label.setText(text["count_value"].format(
                    name=text[key], count=self._block_counts[index]
                ))

        def begin_count_drag(self, changed_index: int):
            self._count_drag_index = changed_index
            self._count_drag_baseline = list(self._block_counts)

        def end_count_drag(self):
            self._count_drag_index = None
            self._count_drag_baseline = None

        def set_block_counts(self, counts, convert: bool = True):
            values = [int(value) for value in counts]
            if len(values) != 4 or min(values) < 0 or sum(values) != GRID_CELL_COUNT:
                raise ValueError("four block counts must total 180")
            self._block_counts = values
            self._updating_block_counts = True
            try:
                for slider, value in zip(self.block_count_sliders, values):
                    slider.blockSignals(True)
                    slider.setValue(value)
                    slider.blockSignals(False)
            finally:
                self._updating_block_counts = False
            self.update_block_count_labels()
            if convert:
                self.convert()

        def equalize_block_counts(self):
            self.set_block_counts([GRID_CELL_COUNT // 4] * 4)

        def reload_source_image(self):
            if self.source_path is not None:
                self.load_image(Path(self.source_path))

        def block_count_changed(self, changed_index: int, new_value: int):
            if self._updating_block_counts:
                return
            baseline = self._block_counts
            if (
                self._count_drag_index == changed_index
                and self._count_drag_baseline is not None
            ):
                baseline = self._count_drag_baseline
            values = _redistribute_counts(
                baseline, changed_index, new_value
            )
            self.set_block_counts(values)

        def fit_changed(self):
            self.source_preview.set_selection_enabled(
                self.fit_combo.currentData() == "selection")
            self.convert()

        def selection_changed(self):
            if self.fit_combo.currentData() == "selection":
                self.convert()

        def request_selection_mode(self):
            index = self.fit_combo.findData("selection")
            if index >= 0 and self.fit_combo.currentIndex() != index:
                self.fit_combo.setCurrentIndex(index)

        def current_args(self) -> argparse.Namespace:
            current = argparse.Namespace(**vars(args))
            current.input = self.source_path
            current.fit = self.fit_combo.currentData()
            current.invert = self.invert_check.isChecked()
            current.tile_size = DEFAULT_TILE_SIZE
            current.air_end, current.crack_end, current.brown_end = (
                _counts_to_thresholds(self._block_counts)
            )
            current.target_counts = list(self._block_counts)
            current.selection_box = (
                self.source_preview.selection_box()
                if current.fit == "selection" else None
            )
            return current

        def convert(self):
            if self.source_path is None:
                return
            try:
                current = self.current_args()
                result, grid, stages = _convert_source(current)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, text["error"], str(exc))
                return
            self.result_image = result
            self.result_grid = grid
            self.resized_preview.setPixmap(_pil_pixmap(stages["resized"]))
            self.grayscale_preview.setPixmap(_pil_pixmap(stages["grayscale"]))
            self.four_tone_preview.setPixmap(_pil_pixmap(stages["four_tone"]))
            result_display = result.resize((480, 384), Image.Resampling.LANCZOS)
            self.result_preview.setPixmap(_pil_pixmap(result_display))
            self.result_preview.setScaledContents(False)
            self.save_button.setEnabled(True)
            if hasattr(self, "apply_button"):
                self.apply_button.setEnabled(True)
            counts = {
                TYPE_NAMES[kind]: sum(cell == kind for row in grid for cell in row)
                for kind in TYPE_NAMES
            }
            self.status.setText(text["loaded"].format(**counts))

        def apply_result(self):
            if self.result_grid is None or self.source_path is None:
                self.status.setText(text["no_result"])
                return
            if apply_callback([list(row) for row in self.result_grid], self.source_path):
                self.close()

        def save_result(self):
            if self.result_image is None or self.result_grid is None or self.source_path is None:
                self.status.setText(text["no_result"])
                return
            args.output_dir.mkdir(parents=True, exist_ok=True)
            suggested = args.output_dir / f"{self.source_path.stem}_block_grid.png"
            selected, _ = QFileDialog.getSaveFileName(
                self, text["save_title"], str(suggested), text["png"]
            )
            if not selected:
                return
            png_path = Path(selected)
            if png_path.suffix.lower() != ".png":
                png_path = png_path.with_suffix(".png")
            json_path = png_path.with_suffix(".json")
            if png_path.exists() or json_path.exists():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                png_path = png_path.with_name(f"{png_path.stem}_{stamp}.png")
                json_path = png_path.with_suffix(".json")
            self.result_image.save(png_path, "PNG")
            _write_json(json_path, self.source_path, self.result_grid, self.current_args())
            self.status.setText(text["saved"].format(png=png_path, json=json_path))

    existing_app = QApplication.instance()
    app = existing_app or QApplication([])
    if not QFontDatabase().families() and os.name == "nt":
        for font_path in (
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "meiryo.ttc",
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        ):
            if font_path.is_file():
                QFontDatabase.addApplicationFont(str(font_path))
    if existing_app is None:
        app.setFont(QFont("Meiryo UI" if language == "ja" else "Segoe UI", 10))
    window = ConverterWindow()
    if args.input is not None:
        window.load_image(args.input)
    window.show()

    if os.environ.get("IMAGE_TO_BLOCK_GRID_SMOKE_TEST") == "1":
        def finish_smoke_test():
            screenshot = os.environ.get("IMAGE_TO_BLOCK_GRID_SCREENSHOT")
            if screenshot:
                window.grab().save(screenshot, "PNG")
            app.quit()

        QTimer.singleShot(300, finish_smoke_test)
    if not run_event_loop:
        return window
    return app.exec_()


def open_converter_window(input_path=None, apply_callback=None, parent=None, language=None):
    """Open the converter inside an existing Qt application without a subprocess."""
    args = _build_parser().parse_args(["--gui"])
    args.input = Path(input_path) if input_path else None
    return _run_gui(
        args,
        apply_callback=apply_callback,
        parent=parent,
        run_event_loop=False,
        language=language,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.gui or args.input is None:
        return _run_gui(args)
    _validate_args(args, parser)
    return _run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
