#!/usr/bin/env python3
"""Independently verify deterministic lettering, geometry, and V5.3 typography."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from typography_contract import TypographyContractError, load_typography_contract, locked_lines


class ValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def pixels(image: Image.Image):
    return image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()


def polygon_mask(size: tuple[int, int], points: Any, context: str) -> Image.Image:
    if not isinstance(points, list) or len(points) < 3:
        raise ValidationError(f"{context} must contain at least three points")
    normalized: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise ValidationError(f"{context}[{index}] must be [x, y]")
        x, y = point
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
            raise ValidationError(f"{context}[{index}] must use integer coordinates")
        if not (0 <= x < size[0] and 0 <= y < size[1]):
            raise ValidationError(f"{context}[{index}] is outside the canvas")
        normalized.append((x, y))
    result = Image.new("L", size, 0)
    ImageDraw.Draw(result).polygon(normalized, fill=255)
    return result


def allowed_mask(size: tuple[int, int], region: dict[str, Any]) -> Image.Image:
    result = polygon_mask(size, region.get("safe_polygon"), "region.safe_polygon")
    for index, exclusion in enumerate(region.get("exclusion_polygons", [])):
        if not isinstance(exclusion, dict):
            raise ValidationError(f"region.exclusion_polygons[{index}] must be an object")
        ImageDraw.Draw(result).bitmap((0, 0), polygon_mask(size, exclusion.get("points"), f"region.exclusion_polygons[{index}].points"), fill=0)
    return result


def resolve(raw: str, report_path: Path) -> Path:
    candidate = Path(raw)
    return (candidate if candidate.is_absolute() else report_path.parent / candidate).resolve()


def exact_elements(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = contract.get("elements")
    if not isinstance(raw, list):
        raise ValidationError("display contract elements must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValidationError(f"elements[{index}] has no valid id")
        if item["id"] in result:
            raise ValidationError(f"duplicate display element id: {item['id']}")
        if item.get("text_mode") == "exact":
            if not isinstance(item.get("text"), str) or not item["text"]:
                raise ValidationError(f"exact display element has no text: {item['id']}")
            result[item["id"]] = item
    return result


def merge_masks(left: Image.Image, right: Image.Image) -> Image.Image:
    return Image.frombytes("L", left.size, bytes(max(a, b) for a, b in zip(pixels(left), pixels(right))))


def typography_issues(
    element: dict[str, Any],
    region: dict[str, Any],
    entry: dict[str, Any],
    typography: dict[str, Any] | None,
) -> list[str]:
    if typography is None:
        return []
    role = element.get("semantic_role")
    if not isinstance(role, str) or role not in typography["roles"]:
        return ["missing or unsupported semantic_role"]
    style = typography["roles"][role]
    issues: list[str] = []
    if entry.get("semantic_role") != role:
        issues.append("compiled semantic_role differs from display contract")
    if entry.get("font_sha256") != typography["font"]["sha256"]:
        issues.append("compiled font hash differs from typography contract")
    for field in ("alignment", "vertical_anchor", "font_weight", "fill", "stroke_width"):
        if entry.get(field) != style[field]:
            issues.append(f"compiled {field} differs from typography contract")
    if not isinstance(entry.get("font_size"), int) or entry["font_size"] < style["minimum_font_size"]:
        issues.append("compiled font size is below the typography minimum")
    if not isinstance(entry.get("occupancy_ratio"), (int, float)) or entry["occupancy_ratio"] < style["minimum_occupancy_ratio"]:
        issues.append("compiled text does not meet minimum visual occupancy")
    try:
        expected_lines, expected_offset = locked_lines(region, element["text"], require_locked=True)
    except TypographyContractError as exc:
        issues.append(str(exc))
        return issues
    if entry.get("locked_lines") != expected_lines or entry.get("lines") != expected_lines:
        issues.append("compiled line group differs from the locked line group")
    if entry.get("optical_offset_px") != expected_offset:
        issues.append("compiled optical offset differs from geometry contract")
    if style["alignment"] == "center":
        error = entry.get("max_center_error_px")
        if not isinstance(error, (int, float)) or error > 3.0:
            issues.append("compiled text is not optically centered")
    return issues


def validate(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    contract, geometry, build = load_json(args.display_contract), load_json(args.geometry_contract), load_json(args.build_report)
    base, final = Image.open(args.base).convert("RGBA"), Image.open(args.final).convert("RGBA")
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    typography: dict[str, Any] | None = None
    comic = contract.get("typography_profile") == "comic_display"
    if comic and getattr(args, "typography_contract", None) is None:
        errors.append("comic_display requires a typography contract")
    if getattr(args, "typography_contract", None):
        try:
            typography = load_typography_contract(args.typography_contract)
        except TypographyContractError as exc:
            errors.append(str(exc))
        else:
            if not comic:
                errors.append("typography contract supplied for a non-comic display")
            elif build.get("typography_contract_sha256") != typography["contract_sha256"]:
                errors.append("build report typography contract hash does not match")
    if base.size != final.size:
        errors.append("final image dimensions do not match the base image")
    if build.get("base_sha256") != sha256(args.base):
        errors.append("build report base hash does not match the base image")
    if build.get("output_sha256") != sha256(args.final):
        errors.append("build report output hash does not match the final image")
    if geometry.get("source_base_sha256") and geometry["source_base_sha256"] != sha256(args.base):
        errors.append("geometry contract is not bound to the current base image")

    elements = exact_elements(contract)
    regions = {item.get("element_id"): item for item in geometry.get("regions", []) if isinstance(item, dict) and isinstance(item.get("element_id"), str)}
    entries = {item.get("element_id"): item for item in build.get("entries", []) if isinstance(item, dict) and isinstance(item.get("element_id"), str)}
    union = Image.new("L", base.size, 0)
    typography_checks: list[dict[str, Any]] = []
    for identifier, element in elements.items():
        issue: list[str] = []
        region, entry = regions.get(identifier), entries.get(identifier)
        if region is None:
            issue.append("missing geometry region")
        if entry is None:
            issue.append("missing lettering entry")
        if entry and entry.get("text") != element["text"]:
            issue.append("compiled text differs from locked text")
        mask = None
        if entry:
            raw_mask = entry.get("mask_file")
            if not isinstance(raw_mask, str) or not raw_mask:
                issue.append("missing glyph mask path")
            else:
                mask_path = resolve(raw_mask, args.build_report)
                if not mask_path.is_file():
                    issue.append("glyph mask file is missing")
                elif entry.get("mask_sha256") != sha256(mask_path):
                    issue.append("glyph mask hash mismatch")
                else:
                    mask = Image.open(mask_path).convert("L")
                    if mask.size != base.size or mask.getbbox() is None:
                        issue.append("glyph mask is empty or has incorrect dimensions")
        outside = None
        if mask is not None and region is not None:
            try:
                outside = sum(1 for pixel, allowed in zip(pixels(mask), pixels(allowed_mask(base.size, region))) if pixel and not allowed)
                if outside:
                    issue.append("glyph mask exceeds safe polygon")
            except ValidationError as exc:
                issue.append(str(exc))
            union = merge_masks(union, mask)
        type_issue = typography_issues(element, region, entry, typography) if entry and region and comic and typography else []
        issue.extend(type_issue)
        checks.append({"element_id": identifier, "passed": not issue, "outside_pixels": outside, "issues": issue})
        if comic:
            typography_checks.append({"element_id": identifier, "result": "passed" if not type_issue else "failed", "issues": type_issue})
        errors.extend(f"{identifier}: {message}" for message in issue)

    groups: dict[str, list[dict[str, Any]]] = {}
    for element in elements.values():
        group = element.get("repeat_group")
        if isinstance(group, str) and group:
            groups.setdefault(group, []).append(element)
    for group, members in groups.items():
        if any(item.get("repeat_rule") == "same_text" for item in members) and len({item["text"] for item in members}) != 1:
            errors.append(f"repeat group {group} violates same_text")
    if base.size == final.size:
        changed = ImageChops.difference(base, final).convert("L")
        changed_outside = sum(1 for pixel, allowed in zip(pixels(changed), pixels(union)) if pixel and not allowed)
        if changed_outside:
            errors.append(f"final image changes {changed_outside} pixels outside deterministic glyph masks")
    report = {
        "schema_version": "1.1", "passed": not errors, "base_sha256": sha256(args.base), "final_sha256": sha256(args.final),
        "display_contract_sha256": sha256(args.display_contract), "geometry_contract_sha256": sha256(args.geometry_contract),
        "typography_contract_sha256": typography["contract_sha256"] if typography else "", "checks": checks,
        "typography_checks": typography_checks, "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report, 0 if not errors else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    parser.add_argument("--display-contract", required=True, type=Path)
    parser.add_argument("--geometry-contract", required=True, type=Path)
    parser.add_argument("--typography-contract", type=Path)
    parser.add_argument("--build-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        report, code = validate(parse_args())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    except ValidationError as exc:
        print(f"lettering geometry validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
