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
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Iterable

from PIL import Image, ImageDraw, ImageEnhance, ImageOps


GRID_WIDTH = 15
GRID_HEIGHT = 12
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

BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


@dataclass(frozen=True)
class CellFeatures:
    luminance: float
    detail: float


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
) -> Image.Image:
    source = image.convert("RGBA")
    matte = Image.new("RGBA", source.size, (*background, 255))
    matte.alpha_composite(source)
    rgb = matte.convert("RGB")

    if fit == "stretch":
        return rgb.resize(size, Image.Resampling.LANCZOS)
    if fit == "contain":
        contained = ImageOps.contain(rgb, size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", size, background)
        x = (size[0] - contained.width) // 2
        y = (size[1] - contained.height) // 2
        canvas.paste(contained, (x, y))
        return canvas
    return ImageOps.fit(rgb, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return 0.0
    pos = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    weight = pos - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def _normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _cell_features(
    image: Image.Image,
    sample_size: int,
    contrast: float,
) -> list[list[CellFeatures]]:
    work_size = (GRID_WIDTH * sample_size, GRID_HEIGHT * sample_size)
    gray = ImageOps.grayscale(image.resize(work_size, Image.Resampling.LANCZOS))
    gray = ImageOps.autocontrast(gray, cutoff=1)
    if contrast != 1.0:
        gray = ImageEnhance.Contrast(gray).enhance(contrast)

    result: list[list[CellFeatures]] = []
    for gy in range(GRID_HEIGHT):
        row: list[CellFeatures] = []
        for gx in range(GRID_WIDTH):
            left = gx * sample_size
            top = gy * sample_size
            cell = gray.crop((left, top, left + sample_size, top + sample_size))
            pixels = list(cell.tobytes())
            lum = sum(pixels) / (255.0 * len(pixels))

            edge_sum = 0
            edge_count = 0
            for y in range(sample_size):
                base = y * sample_size
                for x in range(sample_size):
                    current = pixels[base + x]
                    if x + 1 < sample_size:
                        edge_sum += abs(current - pixels[base + x + 1])
                        edge_count += 1
                    if y + 1 < sample_size:
                        edge_sum += abs(current - pixels[base + sample_size + x])
                        edge_count += 1
            edge = edge_sum / (255.0 * max(1, edge_count))
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            deviation = math.sqrt(variance) / 127.5
            detail = edge * 0.65 + deviation * 0.35
            row.append(CellFeatures(luminance=lum, detail=detail))
        result.append(row)
    return result


def _classify(
    features: list[list[CellFeatures]],
    air_threshold: float,
    white_threshold: float,
    crack_quantile: float,
    dither: float,
    invert: bool,
) -> list[list[int]]:
    luminances = [cell.luminance for row in features for cell in row]
    low = _percentile(luminances, 0.03)
    high = _percentile(luminances, 0.97)

    normalized: list[list[CellFeatures]] = []
    middle_details: list[float] = []
    for row in features:
        normalized_row: list[CellFeatures] = []
        for cell in row:
            lum = _normalize(cell.luminance, low, high)
            if invert:
                lum = 1.0 - lum
            normalized_cell = CellFeatures(lum, cell.detail)
            normalized_row.append(normalized_cell)
            if air_threshold <= lum < white_threshold:
                middle_details.append(cell.detail)
        normalized.append(normalized_row)

    if middle_details:
        crack_threshold = _percentile(middle_details, crack_quantile)
        detail_floor = median(middle_details) * 0.75
        crack_threshold = max(crack_threshold, detail_floor)
    else:
        crack_threshold = 1.0

    grid: list[list[int]] = []
    for y, row in enumerate(normalized):
        out_row: list[int] = []
        for x, cell in enumerate(row):
            bayer = (BAYER_4X4[y % 4][x % 4] + 0.5) / 16.0 - 0.5
            lum = max(0.0, min(1.0, cell.luminance + bayer * dither * 0.22))
            if lum < air_threshold:
                kind = AIR
            elif lum >= white_threshold:
                kind = WHITE
            elif cell.detail >= crack_threshold:
                kind = CRACKED
            else:
                kind = BROWN
            out_row.append(kind)
        grid.append(out_row)
    return grid


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
            "fit": args.fit,
            "air_threshold": args.air_threshold,
            "white_threshold": args.white_threshold,
            "crack_quantile": args.crack_quantile,
            "dither": args.dither,
            "contrast": args.contrast,
            "invert": args.invert,
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
        choices=("crop", "contain", "stretch"),
        default="stretch",
        help="how to fit the source to a 15:12 aspect ratio",
    )
    parser.add_argument("--background", type=_parse_rgb, default=(16, 18, 20))
    parser.add_argument("--sample-size", type=int, default=16)
    parser.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE)
    parser.add_argument("--air-threshold", type=float, default=0.30)
    parser.add_argument("--white-threshold", type=float, default=0.70)
    parser.add_argument("--crack-quantile", type=float, default=0.68)
    parser.add_argument("--dither", type=float, default=0.35)
    parser.add_argument("--contrast", type=float, default=1.15)
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
    if args.sample_size < 4:
        parser.error("--sample-size must be at least 4")
    if args.tile_size < 8:
        parser.error("--tile-size must be at least 8")
    if not 0.0 <= args.air_threshold < args.white_threshold <= 1.0:
        parser.error("thresholds must satisfy 0 <= air < white <= 1")
    if not 0.0 <= args.crack_quantile <= 1.0:
        parser.error("--crack-quantile must be between 0 and 1")
    if not 0.0 <= args.dither <= 1.0:
        parser.error("--dither must be between 0 and 1")
    if args.contrast <= 0.0:
        parser.error("--contrast must be greater than 0")
    for option in (args.tile_air, args.tile_brown, args.tile_white, args.tile_cracked):
        if option is not None and not option.is_file():
            parser.error(f"tile image does not exist: {option}")


def _convert_source(
    args: argparse.Namespace,
) -> tuple[Image.Image, list[list[int]]]:
    with Image.open(args.input) as source:
        fitted = _fit_image(
            source,
            (GRID_WIDTH * args.sample_size, GRID_HEIGHT * args.sample_size),
            args.fit,
            args.background,
        )
    features = _cell_features(fitted, args.sample_size, args.contrast)
    grid = _classify(
        features,
        args.air_threshold,
        args.white_threshold,
        args.crack_quantile,
        args.dither,
        args.invert,
    )
    tiles = _tile_set(args)
    preview = _render_preview(grid, tiles, args.tile_size)
    return preview, grid


def _run_cli(args: argparse.Namespace) -> int:
    preview, grid = _convert_source(args)

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
        "source": "入力画像",
        "result": "変換結果",
        "drop": "ここへ画像をドラッグ＆ドロップ",
        "fit": "画像の合わせ方",
        "stretch": "全体を15x12へ縮小",
        "crop": "中央を切り抜く",
        "contain": "全体を余白付きで収める",
        "dither": "ディザ",
        "crack": "ひび割れ感度",
        "invert": "明暗を反転",
        "ready": "画像をドロップするか、開くボタンで選択してください。",
        "loaded": "変換完了: 空気 {air} / 茶 {brown} / 白 {white} / ひび {cracked}",
        "open_title": "変換する画像を選択",
        "save_title": "変換結果PNGを保存",
        "images": "画像 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)",
        "png": "PNG画像 (*.png)",
        "error": "変換エラー",
        "saved": "保存しました: {png} / {json}",
        "no_result": "保存できる変換結果がありません。",
    },
    "en": {
        "title": "Image to 15x12 Block Grid",
        "open": "Open Image",
        "save": "Save Result",
        "source": "Source Image",
        "result": "Converted Grid",
        "drop": "Drag and drop an image here",
        "fit": "Image Fit",
        "stretch": "Scale entire image to 15x12",
        "crop": "Crop from center",
        "contain": "Fit entire image with padding",
        "dither": "Dither",
        "crack": "Crack Sensitivity",
        "invert": "Invert brightness",
        "ready": "Drop an image or select one with the Open button.",
        "loaded": "Converted: air {air} / brown {brown} / white {white} / cracked {cracked}",
        "open_title": "Select an image to convert",
        "save_title": "Save converted grid PNG",
        "images": "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)",
        "png": "PNG image (*.png)",
        "error": "Conversion Error",
        "saved": "Saved: {png} / {json}",
        "no_result": "There is no converted result to save.",
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


def _run_gui(args: argparse.Namespace) -> int:
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QFont, QFontDatabase, QKeySequence
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

    text = UI_TEXT[_ui_language()]

    class DropPreview(QLabel):
        def __init__(self, on_drop, message: str):
            super().__init__(message)
            self._on_drop = on_drop
            self.setAcceptDrops(True)
            self.setAlignment(Qt.AlignCenter)
            self.setFrameShape(QFrame.StyledPanel)
            self.setMinimumSize(360, 300)
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

    class ConverterWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.source_path: Path | None = None
            self.source_image: Image.Image | None = None
            self.result_image: Image.Image | None = None
            self.result_grid: list[list[int]] | None = None
            self.setWindowTitle(text["title"])
            self.resize(1080, 690)
            self.setAcceptDrops(True)

            root = QWidget()
            root.setStyleSheet(
                "QWidget { color: #202428; }"
                "QPushButton, QComboBox { min-height: 26px; }"
                "QGroupBox { font-weight: 600; }"
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
            toolbar.addSpacing(12)

            toolbar.addWidget(QLabel(text["fit"]))
            self.fit_combo = QComboBox()
            self.fit_combo.setMinimumWidth(220)
            for key in ("stretch", "crop", "contain"):
                self.fit_combo.addItem(text[key], key)
            self.fit_combo.setCurrentIndex(max(0, self.fit_combo.findData(args.fit)))
            self.fit_combo.currentIndexChanged.connect(self.convert)
            toolbar.addWidget(self.fit_combo)

            toolbar.addSpacing(12)
            toolbar.addWidget(QLabel(text["dither"]))
            self.dither_slider = QSlider(Qt.Horizontal)
            self.dither_slider.setRange(0, 100)
            self.dither_slider.setValue(round(args.dither * 100))
            self.dither_slider.setFixedWidth(120)
            self.dither_slider.valueChanged.connect(self.convert)
            toolbar.addWidget(self.dither_slider)

            toolbar.addSpacing(12)
            toolbar.addWidget(QLabel(text["crack"]))
            self.crack_slider = QSlider(Qt.Horizontal)
            self.crack_slider.setRange(5, 95)
            self.crack_slider.setValue(round(args.crack_quantile * 100))
            self.crack_slider.setFixedWidth(120)
            self.crack_slider.valueChanged.connect(self.convert)
            toolbar.addWidget(self.crack_slider)

            self.invert_check = QCheckBox(text["invert"])
            self.invert_check.setChecked(args.invert)
            self.invert_check.toggled.connect(self.convert)
            toolbar.addWidget(self.invert_check)
            toolbar.addStretch(1)
            outer.addLayout(toolbar)

            previews = QHBoxLayout()
            source_group = QGroupBox(text["source"])
            source_layout = QVBoxLayout(source_group)
            self.source_preview = DropPreview(self.load_image, text["drop"])
            source_layout.addWidget(self.source_preview)
            previews.addWidget(source_group, 1)

            result_group = QGroupBox(text["result"])
            result_layout = QVBoxLayout(result_group)
            self.result_preview = DropPreview(self.load_image, text["drop"])
            result_layout.addWidget(self.result_preview)
            previews.addWidget(result_group, 1)
            outer.addLayout(previews, 1)

            self.status = QLabel(text["ready"])
            self.status.setMinimumHeight(24)
            outer.addWidget(self.status)
            self.setCentralWidget(root)

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
            display = Image.new("RGB", (480, 384), (20, 22, 25))
            scaled = ImageOps.contain(source.convert("RGB"), display.size, Image.Resampling.LANCZOS)
            display.paste(scaled, ((display.width - scaled.width) // 2, (display.height - scaled.height) // 2))
            self.source_preview.setPixmap(_pil_pixmap(display))
            self.source_preview.setScaledContents(False)
            self.convert()

        def current_args(self) -> argparse.Namespace:
            current = argparse.Namespace(**vars(args))
            current.input = self.source_path
            current.fit = self.fit_combo.currentData()
            current.dither = self.dither_slider.value() / 100.0
            current.crack_quantile = self.crack_slider.value() / 100.0
            current.invert = self.invert_check.isChecked()
            current.tile_size = DEFAULT_TILE_SIZE
            return current

        def convert(self):
            if self.source_path is None:
                return
            try:
                current = self.current_args()
                result, grid = _convert_source(current)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, text["error"], str(exc))
                return
            self.result_image = result
            self.result_grid = grid
            self.result_preview.setPixmap(_pil_pixmap(result))
            self.result_preview.setScaledContents(False)
            self.save_button.setEnabled(True)
            counts = {
                TYPE_NAMES[kind]: sum(cell == kind for row in grid for cell in row)
                for kind in TYPE_NAMES
            }
            self.status.setText(text["loaded"].format(**counts))

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

    app = QApplication.instance() or QApplication([])
    language = _ui_language()
    if not QFontDatabase().families() and os.name == "nt":
        for font_path in (
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "meiryo.ttc",
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        ):
            if font_path.is_file():
                QFontDatabase.addApplicationFont(str(font_path))
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
    return app.exec_()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.gui or args.input is None:
        return _run_gui(args)
    _validate_args(args, parser)
    return _run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
