#!/usr/bin/env python3
"""Shared V5.3 typography-contract parsing and fail-closed validation.

The contract records visual intent that is deliberately separate from G0 text
semantics.  It is consumed by deterministic lettering and its independent
validator; neither caller is allowed to choose a fallback font or layout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class TypographyContractError(RuntimeError):
    pass


SEMANTIC_ROLES = frozenset({"dialogue", "primary_anchor", "object_label", "footer"})
ALIGNMENTS = frozenset({"left", "center"})
VERTICAL_ANCHORS = frozenset({"top", "center"})
FONT_WEIGHTS = frozenset({"regular", "medium", "bold", "heavy"})
USE_SCOPES = frozenset({"internal", "commercial"})
LICENSE_STATUSES = frozenset({"confirmed", "not_required"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypographyContractError(f"{context} must be an object")
    return value


def _string(value: Any, context: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise TypographyContractError(f"{context} must be a {'possibly empty ' if empty else 'non-empty '}string")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise TypographyContractError(f"{context} must be an integer >= {minimum}")
    return value


def _ratio(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < float(value) <= 1:
        raise TypographyContractError(f"{context} must be a number in (0, 1]")
    return float(value)


def _sha(value: Any, context: str) -> str:
    raw = _string(value, context)
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise TypographyContractError(f"{context} must be a lowercase SHA-256")
    return raw


def _color(value: Any, context: str) -> str:
    raw = _string(value, context)
    if not raw.startswith("#") or len(raw) not in {4, 7}:
        raise TypographyContractError(f"{context} must be a #RGB or #RRGGBB color")
    try:
        int(raw[1:], 16)
    except ValueError as exc:
        raise TypographyContractError(f"{context} is not a valid color") from exc
    return raw


def _offset(value: Any, context: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 2:
        raise TypographyContractError(f"{context} must be [x, y]")
    result: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, int):
            raise TypographyContractError(f"{context}[{index}] must be an integer")
        result.append(item)
    return result


def resolve_file(raw: str, contract_path: Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = contract_path.parent / candidate
    return candidate.resolve()


def load_typography_contract(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TypographyContractError(f"cannot read typography contract {path}: {exc}") from exc
    value = _object(raw, "typography contract")
    if _string(value.get("schema_version"), "typography_contract.schema_version") != "1.0":
        raise TypographyContractError("typography_contract.schema_version must be 1.0")
    profile = _string(value.get("profile"), "typography_contract.profile")
    if profile != "comic_display":
        raise TypographyContractError("typography_contract.profile must be comic_display")
    use_scope = _string(value.get("use_scope"), "typography_contract.use_scope")
    if use_scope not in USE_SCOPES:
        raise TypographyContractError("typography_contract.use_scope is invalid")
    font = _object(value.get("font"), "typography_contract.font")
    font_file = _string(font.get("file"), "typography_contract.font.file")
    font_path = resolve_file(font_file, path)
    font_sha = _sha(font.get("sha256"), "typography_contract.font.sha256")
    family = _string(font.get("family"), "typography_contract.font.family")
    declared_weight = _string(font.get("weight"), "typography_contract.font.weight")
    if declared_weight not in FONT_WEIGHTS:
        raise TypographyContractError("typography_contract.font.weight is invalid")
    license_status = _string(font.get("license_status"), "typography_contract.font.license_status")
    if license_status not in LICENSE_STATUSES:
        raise TypographyContractError("typography_contract.font.license_status is invalid")
    if use_scope == "commercial" and license_status != "confirmed":
        raise TypographyContractError("commercial typography requires a confirmed font license")
    if not font_path.is_file():
        raise TypographyContractError(f"contract font is missing: {font_path}")
    if sha256(font_path) != font_sha:
        raise TypographyContractError("contract font SHA-256 does not match the font file")

    raw_roles = _object(value.get("roles"), "typography_contract.roles")
    roles: dict[str, dict[str, Any]] = {}
    for role in SEMANTIC_ROLES:
        item = _object(raw_roles.get(role), f"typography_contract.roles.{role}")
        alignment = _string(item.get("alignment"), f"typography_contract.roles.{role}.alignment")
        if alignment not in ALIGNMENTS:
            raise TypographyContractError(f"typography_contract.roles.{role}.alignment is invalid")
        vertical_anchor = _string(item.get("vertical_anchor"), f"typography_contract.roles.{role}.vertical_anchor")
        if vertical_anchor not in VERTICAL_ANCHORS:
            raise TypographyContractError(f"typography_contract.roles.{role}.vertical_anchor is invalid")
        weight = _string(item.get("font_weight"), f"typography_contract.roles.{role}.font_weight")
        if weight not in FONT_WEIGHTS:
            raise TypographyContractError(f"typography_contract.roles.{role}.font_weight is invalid")
        roles[role] = {
            "alignment": alignment,
            "vertical_anchor": vertical_anchor,
            "font_weight": weight,
            "fill": _color(item.get("fill"), f"typography_contract.roles.{role}.fill"),
            "stroke_width": _integer(item.get("stroke_width"), f"typography_contract.roles.{role}.stroke_width"),
            "minimum_font_size": _integer(item.get("minimum_font_size"), f"typography_contract.roles.{role}.minimum_font_size", minimum=1),
            "minimum_occupancy_ratio": _ratio(item.get("minimum_occupancy_ratio"), f"typography_contract.roles.{role}.minimum_occupancy_ratio"),
            "line_spacing": _integer(item.get("line_spacing"), f"typography_contract.roles.{role}.line_spacing"),
        }
    return {
        "schema_version": "1.0",
        "profile": profile,
        "use_scope": use_scope,
        "font": {
            "file": str(font_path),
            "sha256": font_sha,
            "family": family,
            "weight": declared_weight,
            "license_status": license_status,
        },
        "roles": roles,
        "contract_sha256": sha256(path),
    }


def locked_lines(region: dict[str, Any], text: str, *, require_locked: bool) -> tuple[list[str] | None, list[int]]:
    typography = region.get("typography")
    if typography is None and not require_locked:
        return None, [0, 0]
    item = _object(typography, "region.typography")
    lines = item.get("locked_lines")
    if not isinstance(lines, list) or not lines or not all(isinstance(line, str) and line for line in lines):
        raise TypographyContractError("region.typography.locked_lines must be a non-empty string list")
    if "".join(lines) != text.replace("\n", ""):
        raise TypographyContractError("region.typography.locked_lines do not exactly cover the locked text")
    return list(lines), _offset(item.get("optical_offset_px"), "region.typography.optical_offset_px")
