#!/usr/bin/env python3
"""Deterministically letter a no-text image from display and geometry contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont

from typography_contract import TypographyContractError, load_typography_contract, locked_lines


class LetteringError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LetteringError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LetteringError(f"JSON root must be an object: {path}")
    return value


def string(value: Any, context: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise LetteringError(f"{context} must be a {'possibly empty ' if empty else 'non-empty '}string")
    return value


def integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise LetteringError(f"{context} must be an integer >= {minimum}")
    return value


def object_value(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LetteringError(f"{context} must be an object")
    return value


def pixels(image: Image.Image):
    return image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()


def polygon_mask(size: tuple[int, int], points: Any, context: str) -> Image.Image:
    if not isinstance(points, list) or len(points) < 3:
        raise LetteringError(f"{context} must contain at least three points")
    normalized: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise LetteringError(f"{context}[{index}] must be [x, y]")
        x, y = integer(point[0], f"{context}[{index}][0]"), integer(point[1], f"{context}[{index}][1]")
        if x >= size[0] or y >= size[1]:
            raise LetteringError(f"{context}[{index}] is outside the canvas")
        normalized.append((x, y))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(normalized, fill=255)
    return mask


def safe_mask(size: tuple[int, int], region: dict[str, Any]) -> Image.Image:
    result = polygon_mask(size, region.get("safe_polygon"), "region.safe_polygon")
    exclusions = region.get("exclusion_polygons", [])
    if not isinstance(exclusions, list):
        raise LetteringError("region.exclusion_polygons must be a list")
    draw = ImageDraw.Draw(result)
    for index, raw in enumerate(exclusions):
        item = object_value(raw, f"region.exclusion_polygons[{index}]")
        draw.bitmap((0, 0), polygon_mask(size, item.get("points"), f"region.exclusion_polygons[{index}].points"), fill=0)
    return result


def parse_box(value: Any, size: tuple[int, int], context: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise LetteringError(f"{context} must be [left, top, right, bottom]")
    left, top, right, bottom = (integer(item, f"{context}[{index}]") for index, item in enumerate(value))
    if not (left < right <= size[0] and top < bottom <= size[1]):
        raise LetteringError(f"{context} is invalid for the canvas")
    return left, top, right, bottom


def supported_text(font: ImageFont.FreeTypeFont, text: str) -> bool:
    missing = bytes(font.getmask("□", mode="L"))
    return all(char.isspace() or (glyph := bytes(font.getmask(char, mode="L"))) and glyph != missing for char in text)


def wrapped_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    result: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if current and draw.textbbox((0, 0), current + char, font=font)[2] > width:
                result.append(current)
                current = char
            else:
                current += char
        if current:
            result.append(current)
    return result or [""]


VARIATION_WEIGHT_NAMES = {
    "regular": "Regular",
    "medium": "Medium",
    "bold": "Bold",
    "heavy": "Black",
}


def load_weighted_font(
    font_path: Path,
    size: int,
    weight: str,
    declared_weight: str,
) -> ImageFont.FreeTypeFont:
    """Load a contracted display weight, including variable-font instances.

    A static font is accepted only for the exact instance declared in the
    contract; requesting a different weight must use a named variable-font
    instance or fail closed.
    """
    font = ImageFont.truetype(str(font_path), size=size)
    target = VARIATION_WEIGHT_NAMES.get(weight)
    if target is None:
        raise LetteringError(f"unsupported contracted font weight: {weight}")
    if not hasattr(font, "get_variation_names") or not hasattr(font, "set_variation_by_name"):
        if weight == declared_weight:
            return font
        raise LetteringError(f"font cannot apply contracted weight {weight}: {font_path}")
    try:
        names = font.get_variation_names()
    except OSError as exc:
        if weight == declared_weight:
            return font
        raise LetteringError(f"font lacks contracted weight {weight}: {font_path}") from exc
    try:
        actual = next(
            name for name in names
            if (name.decode("utf-8") if isinstance(name, bytes) else str(name)).casefold() == target.casefold()
        )
    except StopIteration as exc:
        if weight == declared_weight:
            return font
        raise LetteringError(f"font lacks contracted weight {weight}: {font_path}") from exc
    try:
        font.set_variation_by_name(actual)
    except OSError as exc:
        raise LetteringError(f"font cannot apply contracted weight {weight}: {font_path}") from exc
    return font


def choose_layout(
    text: str,
    font_path: Path,
    box: tuple[int, int, int, int],
    max_lines: int,
    maximum: int,
    minimum: int,
    spacing: int,
    forced_lines: list[str] | None,
    font_weight: str = "regular",
    declared_font_weight: str = "regular",
) -> tuple[ImageFont.FreeTypeFont, list[str], list[tuple[int, int, int, int]], int]:
    left, top, right, bottom = box
    draw = ImageDraw.Draw(Image.new("L", (1, 1), 0))
    if forced_lines is not None and len(forced_lines) > max_lines:
        raise LetteringError("locked lines exceed the display contract maximum line count")
    for size in range(maximum, minimum - 1, -1):
        font = load_weighted_font(font_path, size=size, weight=font_weight, declared_weight=declared_font_weight)
        if not supported_text(font, text):
            raise LetteringError(f"font does not support every required glyph: {font_path}")
        lines = list(forced_lines) if forced_lines is not None else wrapped_lines(draw, text, font, right - left)
        line_boxes = [draw.textbbox((0, 0), line or " ", font=font) for line in lines]
        if len(lines) <= max_lines and all(item[2] - item[0] <= right - left for item in line_boxes):
            height = max(item[3] - item[1] for item in line_boxes) * len(lines) + spacing * max(0, len(lines) - 1)
            if height <= bottom - top:
                return font, lines, line_boxes, height
    raise LetteringError("locked text cannot fit the geometry contract at the required minimum font size")


def exact_elements(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = contract.get("elements")
    if not isinstance(raw, list):
        raise LetteringError("display contract elements must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        item = object_value(item, f"elements[{index}]")
        identifier = string(item.get("id"), f"elements[{index}].id")
        if identifier in result:
            raise LetteringError(f"duplicate display element id: {identifier}")
        if item.get("text_mode") not in {"exact", "none"} or item.get("container_presence") not in {"required", "forbidden"}:
            raise LetteringError(f"elements[{index}] has invalid display modes")
        result[identifier] = item
    return result


def render_element(
    base: Image.Image,
    element: dict[str, Any],
    region: dict[str, Any],
    font_path: Path,
    typography: dict[str, Any] | None,
) -> tuple[Image.Image, dict[str, Any]]:
    identifier, text = element["id"], string(element.get("text"), f"elements.{element['id']}.text")
    box = parse_box(region.get("text_box"), base.size, f"regions.{identifier}.text_box")
    maximum = integer(element.get("max_font_size", 48), f"elements.{identifier}.max_font_size", 1)
    minimum = integer(element.get("min_font_size", 12), f"elements.{identifier}.min_font_size", 1)
    max_lines = integer(element.get("max_lines", 1), f"elements.{identifier}.max_lines", 1)
    forced_lines: list[str] | None = None
    offset = [0, 0]
    if typography is None:
        style = {
            "alignment": "left", "vertical_anchor": "top", "font_weight": "regular",
            "fill": element.get("color", "#111111"), "stroke_width": 0,
            "minimum_occupancy_ratio": 0.0,
        }
        spacing = integer(element.get("line_spacing", 4), f"elements.{identifier}.line_spacing")
    else:
        role = string(element.get("semantic_role"), f"elements.{identifier}.semantic_role")
        try:
            style = typography["roles"][role]
            forced_lines, offset = locked_lines(region, text, require_locked=True)
        except (KeyError, TypographyContractError) as exc:
            raise LetteringError(f"comic typography contract error for {identifier}: {exc}") from exc
        assert forced_lines is not None
        minimum = max(minimum, int(style["minimum_font_size"]))
        spacing = int(style["line_spacing"])
    if minimum > maximum:
        raise LetteringError(f"elements.{identifier} cannot meet typography minimum_font_size")
    font, lines, line_boxes, content_height = choose_layout(
        text,
        font_path,
        box,
        max_lines,
        maximum,
        minimum,
        spacing,
        forced_lines,
        style["font_weight"],
        typography["font"]["weight"] if typography is not None else "regular",
    )
    left, top, right, bottom = box
    y = top + (bottom - top - content_height) // 2 + offset[1] if style["vertical_anchor"] == "center" else top + offset[1]
    if y < top or y + content_height > bottom:
        raise LetteringError(f"elements.{identifier} optical placement leaves the text box")
    mask = Image.new("L", base.size, 0)
    draw = ImageDraw.Draw(mask)
    line_bboxes: list[list[int]] = []
    errors: list[float] = []
    for line, source_box in zip(lines, line_boxes):
        width = source_box[2] - source_box[0]
        x = left + (right - left - width) // 2 + offset[0] if style["alignment"] == "center" else left + offset[0]
        if x < left or x + width > right:
            raise LetteringError(f"elements.{identifier} horizontal placement leaves the text box")
        line_mask = Image.new("L", base.size, 0)
        ImageDraw.Draw(line_mask).text((x - source_box[0], y - source_box[1]), line, font=font, fill=255, stroke_width=int(style["stroke_width"]), stroke_fill=255)
        draw.bitmap((0, 0), line_mask, fill=255)
        actual = line_mask.getbbox() or (0, 0, 0, 0)
        line_bboxes.append(list(actual))
        if style["alignment"] == "center":
            errors.append(abs(((actual[0] + actual[2]) / 2) - ((left + right) / 2 + offset[0])))
        y += source_box[3] - source_box[1] + spacing
    allowed = safe_mask(base.size, region)
    if any(pixel and not permit for pixel, permit in zip(pixels(mask), pixels(allowed))):
        raise LetteringError(f"rendered glyphs exceed the safe polygon: {identifier}")
    glyph_box = mask.getbbox() or (0, 0, 0, 0)
    occupancy = (glyph_box[2] - glyph_box[0]) / (right - left)
    if typography is not None and occupancy < float(style["minimum_occupancy_ratio"]):
        raise LetteringError(f"elements.{identifier} does not meet typography minimum occupancy")
    return mask, {
        "element_id": identifier, "text": text, "font_path": str(font_path), "font_sha256": sha256(font_path),
        "font_size": font.size, "lines": lines, "locked_lines": forced_lines,
        "semantic_role": element.get("semantic_role", "not_applicable"), "alignment": style["alignment"],
        "vertical_anchor": style["vertical_anchor"], "font_weight": style["font_weight"], "fill": style["fill"],
        "stroke_width": int(style["stroke_width"]), "optical_offset_px": offset, "line_bboxes": line_bboxes,
        "max_center_error_px": max(errors, default=0.0), "occupancy_ratio": occupancy,
        "glyph_bbox": list(glyph_box), "safe_polygon_verified": True,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    contract, geometry = load_json(args.display_contract), load_json(args.geometry_contract)
    elements = exact_elements(contract)
    base = Image.open(args.base).convert("RGBA")
    if isinstance(contract.get("canvas"), dict) and (contract["canvas"].get("width"), contract["canvas"].get("height")) != base.size:
        raise LetteringError("display contract canvas does not match base image")
    if isinstance(geometry.get("canvas"), dict) and (geometry["canvas"].get("width"), geometry["canvas"].get("height")) != base.size:
        raise LetteringError("geometry contract canvas does not match base image")
    if geometry.get("source_base_sha256") and geometry["source_base_sha256"] != sha256(args.base):
        raise LetteringError("geometry contract source_base_sha256 does not match base image")
    regions: dict[str, dict[str, Any]] = {}
    if not isinstance(geometry.get("regions"), list):
        raise LetteringError("geometry contract regions must be a list")
    for index, raw in enumerate(geometry["regions"]):
        item = object_value(raw, f"regions[{index}]")
        identifier = string(item.get("element_id"), f"regions[{index}].element_id")
        if identifier in regions:
            raise LetteringError(f"duplicate geometry region: {identifier}")
        regions[identifier] = item

    typography: dict[str, Any] | None = None
    if getattr(args, "typography_contract", None):
        try:
            typography = load_typography_contract(args.typography_contract)
        except TypographyContractError as exc:
            raise LetteringError(str(exc)) from exc
        font_path = Path(typography["font"]["file"])
        if args.font and args.font.resolve() != font_path:
            raise LetteringError("--font cannot override the typography-contract font")
    else:
        if not args.font:
            raise LetteringError("--font is required when no typography contract is supplied")
        font_path = args.font.resolve()
        if not font_path.is_file():
            raise LetteringError(f"font file is missing: {font_path}")
    if contract.get("typography_profile") == "comic_display" and typography is None:
        raise LetteringError("comic_display requires --typography-contract")
    if typography and contract.get("typography_profile", "comic_display") != "comic_display":
        raise LetteringError("typography contract is only valid for comic_display")

    args.mask_dir.mkdir(parents=True, exist_ok=True)
    layer, union = Image.new("RGBA", base.size, (0, 0, 0, 0)), Image.new("L", base.size, 0)
    entries: list[dict[str, Any]] = []
    for identifier, element in elements.items():
        if element["text_mode"] == "none":
            continue
        if identifier not in regions:
            raise LetteringError(f"exact text element lacks a geometry region: {identifier}")
        mask, entry = render_element(base, element, regions[identifier], font_path, typography)
        try:
            color = Image.new("RGBA", base.size, entry["fill"])
        except ValueError as exc:
            raise LetteringError(f"elements.{identifier}.color is invalid") from exc
        layer.alpha_composite(Image.composite(color, Image.new("RGBA", base.size), mask))
        union = ImageChops.lighter(union, mask)
        mask_file = (args.mask_dir / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', identifier)}.png").resolve()
        mask.save(mask_file)
        entry["mask_file"], entry["mask_sha256"] = str(mask_file), sha256(mask_file)
        entries.append(entry)
    final = Image.alpha_composite(base, layer)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    final.save(args.output)
    report = {
        "schema_version": "1.1", "base_file": str(args.base), "base_sha256": sha256(args.base),
        "output_file": str(args.output), "output_sha256": sha256(args.output),
        "display_contract_sha256": sha256(args.display_contract), "geometry_contract_sha256": sha256(args.geometry_contract),
        "typography_contract_sha256": typography["contract_sha256"] if typography else "", "font_sha256": sha256(font_path),
        "entries": entries,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--display-contract", required=True, type=Path)
    parser.add_argument("--geometry-contract", required=True, type=Path)
    parser.add_argument("--typography-contract", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mask-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        print(json.dumps(build(parse_args()), ensure_ascii=False, indent=2))
    except LetteringError as exc:
        print(f"lettering assembly failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
