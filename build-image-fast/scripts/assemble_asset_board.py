#!/usr/bin/env python3
"""Deterministically assemble V5 annotated and clean asset boards from a JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from validate_project_state import (
    StateError,
    ASSET_TYPES,
    load_and_validate_state,
    public_report,
    validate_approval_reference,
)


V5_SCHEMA_VERSION = "5.4"
V53_SCHEMA_VERSION = "5.3"
V52_SCHEMA_VERSION = "5.2"
V51_SCHEMA_VERSION = "5.1"
V5_SCHEMA_VERSIONS = {"5.0", V51_SCHEMA_VERSION, V52_SCHEMA_VERSION, V53_SCHEMA_VERSION, V5_SCHEMA_VERSION}
HARD_MAX_CLEAN_SLOTS = 8
HARD_MAX_CLEAN_PRIMARY_ROLES = 2
HARD_MIN_CLEAN_TILE_SHORT_SIDE = 384
HARD_MIN_ANNOTATED_TILE_SHORT_SIDE = 384
HEX_DIGITS = frozenset("0123456789abcdef")
DEFAULT_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)


class BuildError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument(
        "--workflow-state",
        type=Path,
        help="V5 project-state.json; must match manifest.workflow_state_ref when both are set",
    )
    parser.add_argument(
        "--baseline-report",
        type=Path,
        help="candidate_preview build report required for a V5 release promotion",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_image(image: Image.Image) -> str:
    digest = hashlib.sha256()
    digest.update(image.mode.encode("ascii"))
    digest.update(f"{image.width}x{image.height}".encode("ascii"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and set(value) <= HEX_DIGITS
    )


def require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise BuildError(f"{context} missing required field: {key}")
    return mapping[key]


def require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildError(f"{context} must be an object")
    return value


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise BuildError(f"{context} must be a list")
    return value


def require_string(value: Any, context: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        suffix = "a string" if allow_empty else "a non-empty string"
        raise BuildError(f"{context} must be {suffix}")
    return value


def resolve_input_path(raw: str, relative_to: Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = relative_to / candidate
    return candidate.resolve()


def load_font(explicit: Path | None, size: int) -> tuple[ImageFont.FreeTypeFont, str]:
    candidates = [explicit] if explicit else [Path(item) for item in DEFAULT_FONT_CANDIDATES]
    for candidate in candidates:
        if candidate and candidate.is_file():
            try:
                font = ImageFont.truetype(str(candidate), size=size)
                signatures = set()
                for char in "资产角色":
                    mask = font.getmask(char, mode="L")
                    signatures.add((mask.size, bytes(mask)))
                missing = font.getmask("□", mode="L")
                missing_signature = (missing.size, bytes(missing))
                if len(signatures) >= 3 and any(item != missing_signature for item in signatures):
                    return font, str(candidate)
            except OSError:
                continue
    raise BuildError("no usable CJK font found; pass --font with a Chinese-capable font")


def grid_for(count: int, width: int, height: int) -> tuple[int, int]:
    if count < 1:
        raise BuildError("board cannot contain zero assets")
    aspect = width / max(height, 1)
    cols = max(1, min(count, math.ceil(math.sqrt(count * aspect))))
    rows = math.ceil(count / cols)
    return cols, rows


def tile_geometry(
    count: int, width: int, height: int, padding: int, gap: int
) -> tuple[int, int, int, int]:
    cols, rows = grid_for(count, width - 2 * padding, height - 2 * padding)
    tile_w = (width - 2 * padding - gap * (cols - 1)) // cols
    tile_h = (height - 2 * padding - gap * (rows - 1)) // rows
    if tile_w < 1 or tile_h < 1:
        raise BuildError("canvas, padding and gap produce a non-positive tile size")
    return cols, rows, tile_w, tile_h


def normalize_asset(path: Path, base: int = 1024) -> Image.Image:
    try:
        with Image.open(path) as opened:
            source = ImageOps.exif_transpose(opened).convert("RGBA")
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot decode asset image {path}: {exc}") from exc
    contained = ImageOps.contain(source, (base, base), Image.Resampling.LANCZOS)
    tile = Image.new("RGBA", (base, base), (255, 255, 255, 0))
    offset = ((base - contained.width) // 2, (base - contained.height) // 2)
    tile.alpha_composite(contained, offset)
    return tile


def paste_normalized(
    board: Image.Image,
    normalized: Image.Image,
    box: tuple[int, int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    fitted = ImageOps.contain(normalized, (x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
    x = x0 + (x1 - x0 - fitted.width) // 2
    y = y0 + (y1 - y0 - fitted.height) // 2
    board.paste(fitted, (x, y), fitted)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    width: int,
) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        box = draw.textbbox((0, 0), trial, font=font)
        if current and box[2] - box[0] > width:
            lines.append(current)
            current = char
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise BuildError("manifest root must be an object")
    schema_version = manifest.get("schema_version")
    is_v5 = schema_version in V5_SCHEMA_VERSIONS
    build_mode = require_string(require(manifest, "build_mode", "manifest"), "build_mode")
    if build_mode not in {"release", "candidate_preview"}:
        raise BuildError("build_mode must be release or candidate_preview")
    if build_mode == "release" and not is_v5:
        raise BuildError(
            "legacy V4 manifests may build candidate_preview only; V5 release requires "
            "a supported V5 schema and migration"
        )

    project_id = require_string(require(manifest, "project_id", "manifest"), "project_id")
    require_string(require(manifest, "version", "manifest"), "version")
    if is_v5:
        require_string(require(manifest, "workflow_state_ref", "manifest"),
                       "workflow_state_ref")
        require_string(
            require(manifest, "approval_event_id", "manifest"),
            "approval_event_id",
            allow_empty=True,
        )
        decision_fingerprint = require_string(
            require(manifest, "decision_fingerprint", "manifest"), "decision_fingerprint"
        ).lower()
        if not is_sha256(decision_fingerprint):
            raise BuildError("decision_fingerprint must be a lowercase SHA-256 fingerprint")
    else:
        decision_fingerprint = ""

    canvas = require_mapping(require(manifest, "canvas", "manifest"), "canvas")
    for field in (
        "width",
        "height",
        "padding",
        "gap",
        "font_size",
        "label_height",
        "max_clean_slots",
        "min_clean_tile_short_side",
        "max_clean_primary_roles",
        "min_annotated_tile_short_side",
    ):
        value = require(canvas, field, "canvas")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BuildError(f"canvas.{field} must be a non-negative integer")
    if int(canvas["width"]) < 1 or int(canvas["height"]) < 1:
        raise BuildError("canvas width and height must be positive")
    require_string(require(canvas, "background", "canvas"), "canvas.background")
    if int(canvas["max_clean_slots"]) > HARD_MAX_CLEAN_SLOTS:
        raise BuildError(
            f"canvas.max_clean_slots cannot exceed hard limit {HARD_MAX_CLEAN_SLOTS}"
        )
    if int(canvas["max_clean_primary_roles"]) > HARD_MAX_CLEAN_PRIMARY_ROLES:
        raise BuildError(
            "canvas.max_clean_primary_roles cannot exceed hard limit "
            f"{HARD_MAX_CLEAN_PRIMARY_ROLES}"
        )
    if int(canvas["min_clean_tile_short_side"]) < HARD_MIN_CLEAN_TILE_SHORT_SIDE:
        raise BuildError(
            "canvas.min_clean_tile_short_side cannot be lower than hard minimum "
            f"{HARD_MIN_CLEAN_TILE_SHORT_SIDE}px"
        )
    if int(canvas["min_annotated_tile_short_side"]) < HARD_MIN_ANNOTATED_TILE_SHORT_SIDE:
        raise BuildError(
            "canvas.min_annotated_tile_short_side cannot be lower than hard minimum "
            f"{HARD_MIN_ANNOTATED_TILE_SHORT_SIDE}px"
        )

    boards = require_mapping(require(manifest, "boards", "manifest"), "boards")
    raw_assets = require_list(require(manifest, "assets", "manifest"), "assets")
    if not raw_assets:
        raise BuildError("assets must be a non-empty list")

    asset_map: dict[str, dict[str, Any]] = {}
    normalized: dict[str, Image.Image] = {}
    asset_report: list[dict[str, Any]] = []
    registry_eligible = build_mode == "release" and is_v5
    is_v51 = schema_version in {V51_SCHEMA_VERSION, V52_SCHEMA_VERSION, V53_SCHEMA_VERSION, V5_SCHEMA_VERSION}

    for index, raw_asset in enumerate(raw_assets):
        context = f"assets[{index}]"
        asset = require_mapping(raw_asset, context)
        asset_id = require_string(require(asset, "id", context), f"{context}.id")
        if asset_id in asset_map:
            raise BuildError(f"duplicate asset id: {asset_id}")
        for field in ("file", "type", "label", "role", "owner", "rights_scope", "approval_status"):
            require_string(require(asset, field, context), f"{context}.{field}")
        for field in ("must_preserve", "forbidden", "contract_versions", "clean_groups"):
            values = require_list(require(asset, field, context), f"{context}.{field}")
            if not all(isinstance(item, str) and item for item in values):
                raise BuildError(f"{context}.{field} must contain non-empty strings")
        for field in ("contains_text", "critical"):
            if not isinstance(require(asset, field, context), bool):
                raise BuildError(f"{context}.{field} must be a boolean")
        require_string(require(asset, "dedicated_group", context), f"{context}.dedicated_group",
                       allow_empty=True)
        if is_v51:
            asset_type = str(asset["type"])
            if asset_type not in ASSET_TYPES:
                raise BuildError(f"V5.1 asset has unsupported type: {asset_id}: {asset_type}")
            for field in ("views", "coverage_tags"):
                values = require_list(require(asset, field, context), f"{context}.{field}")
                if not all(isinstance(item, str) and item for item in values):
                    raise BuildError(f"{context}.{field} must contain non-empty strings")
        status = str(asset["approval_status"])
        if status not in {"candidate", "approved", "rejected"}:
            raise BuildError(f"{asset_id} has unsupported approval_status: {status}")
        if build_mode == "release" and status != "approved":
            raise BuildError(f"release contains unapproved asset {asset_id}: {status}")
        if status != "approved":
            registry_eligible = False
        path = resolve_input_path(str(asset["file"]), manifest_path.parent)
        if not path.is_file():
            raise BuildError(f"asset file not found: {asset_id}: {path}")
        actual_sha = sha256_file(path)
        expected_sha = str(asset.get("sha256", "")).lower()
        if build_mode == "release" and not expected_sha:
            raise BuildError(f"release asset missing sha256: {asset_id}")
        if expected_sha and not is_sha256(expected_sha):
            raise BuildError(f"invalid sha256 for {asset_id}")
        if expected_sha and expected_sha != actual_sha:
            raise BuildError(f"sha256 mismatch for {asset_id}")
        tile = normalize_asset(path)
        normalized_sha = sha256_image(tile)
        asset_map[asset_id] = {**asset, "_path": path, "_sha256": actual_sha}
        normalized[asset_id] = tile
        asset_report.append({
            "id": asset_id,
            "file": str(path),
            "sha256": actual_sha,
            "normalized_sha256": normalized_sha,
            "type": asset["type"],
            "label": asset["label"],
            "role": asset["role"],
            "owner": asset["owner"],
            "must_preserve": asset["must_preserve"],
            "forbidden": asset["forbidden"],
            "contract_versions": asset["contract_versions"],
            "rights_scope": asset["rights_scope"],
            "approval_status": status,
            "contains_text": bool(asset["contains_text"]),
            "critical": bool(asset["critical"]),
            "clean_groups": asset["clean_groups"],
            "dedicated_group": asset["dedicated_group"],
        })

    annotated = require_mapping(require(boards, "annotated", "boards"), "boards.annotated")
    require_string(require(annotated, "filename", "boards.annotated"),
                   "boards.annotated.filename")
    sections = require_list(require(annotated, "sections", "boards.annotated"),
                            "boards.annotated.sections")
    if not sections:
        raise BuildError("annotated board must contain at least one section")
    annotated_ids: list[str] = []
    section_by_asset: dict[str, str] = {}
    section_snapshot: list[dict[str, Any]] = []
    for index, raw_section in enumerate(sections):
        context = f"boards.annotated.sections[{index}]"
        section = require_mapping(raw_section, context)
        section_id = require_string(section.get("id", f"section-{index + 1}"), f"{context}.id")
        title = require_string(require(section, "title", context), f"{context}.title")
        asset_ids = require_list(require(section, "asset_ids", context), f"{context}.asset_ids")
        if not asset_ids:
            raise BuildError(f"{context} must contain at least one asset")
        for asset_id in asset_ids:
            if asset_id not in asset_map:
                raise BuildError(f"annotated section references unknown asset: {asset_id}")
            if asset_id in section_by_asset:
                raise BuildError(f"annotated asset appears twice: {asset_id}")
            section_by_asset[asset_id] = title
            annotated_ids.append(asset_id)
        section_snapshot.append({"id": section_id, "title": title, "asset_ids": asset_ids})
    if set(annotated_ids) != set(asset_map):
        missing = sorted(set(asset_map) - set(annotated_ids))
        raise BuildError(f"annotated board omits assets: {missing}")

    width = int(canvas["width"])
    height = int(canvas["height"])
    padding = int(canvas["padding"])
    gap = int(canvas["gap"])
    label_height = int(canvas["label_height"])
    _, _, annotated_w, annotated_h = tile_geometry(
        len(annotated_ids), width, height, padding, gap
    )
    content_short = min(annotated_w, annotated_h - label_height)
    if content_short < int(canvas["min_annotated_tile_short_side"]):
        raise BuildError(f"annotated board too dense: content short side {content_short}px")

    clean_groups = require_list(require(boards, "clean_groups", "boards"), "boards.clean_groups")
    if not clean_groups:
        raise BuildError("boards.clean_groups must be a non-empty list")
    group_reports: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    actual_memberships: dict[str, set[str]] = {asset_id: set() for asset_id in asset_map}
    for index, raw_group in enumerate(clean_groups):
        context = f"boards.clean_groups[{index}]"
        group = require_mapping(raw_group, context)
        group_id = require_string(require(group, "id", context), f"{context}.id")
        if group_id in seen_groups:
            raise BuildError(f"duplicate clean group id: {group_id}")
        seen_groups.add(group_id)
        require_string(require(group, "filename", context), f"{context}.filename")
        asset_ids = require_list(require(group, "asset_ids", context), f"{context}.asset_ids")
        roles = require_list(require(group, "primary_roles", context), f"{context}.primary_roles")
        if not asset_ids:
            raise BuildError(f"clean group {group_id} cannot be empty")
        if len(asset_ids) != len(set(asset_ids)):
            raise BuildError(f"clean group {group_id} contains duplicate asset IDs")
        if not roles or not all(isinstance(item, str) and item for item in roles):
            raise BuildError(f"clean group {group_id} primary_roles must be non-empty strings")
        if len(asset_ids) > int(canvas["max_clean_slots"]):
            raise BuildError(f"clean group {group_id} exceeds max_clean_slots")
        if len(set(roles)) > int(canvas["max_clean_primary_roles"]):
            raise BuildError(f"clean group {group_id} exceeds max_clean_primary_roles")
        dedicated = set()
        for asset_id in asset_ids:
            if asset_id not in asset_map:
                raise BuildError(f"clean group {group_id} references unknown asset: {asset_id}")
            asset = asset_map[asset_id]
            if group_id not in asset["clean_groups"]:
                raise BuildError(f"{asset_id} does not declare clean group {group_id}")
            actual_memberships[asset_id].add(group_id)
            if bool(asset["contains_text"]):
                raise BuildError(f"clean group {group_id} contains text-bearing asset: {asset_id}")
            if str(asset["dedicated_group"]):
                dedicated.add(str(asset["dedicated_group"]))
        if len(dedicated) > 1:
            raise BuildError(f"clean group {group_id} mixes dedicated groups: {sorted(dedicated)}")
        if dedicated:
            dedicated_id = next(iter(dedicated))
            if dedicated_id != group_id:
                raise BuildError(
                    f"clean group {group_id} contains asset reserved for dedicated group {dedicated_id}"
                )
            mixed = [item for item in asset_ids
                     if str(asset_map[item]["dedicated_group"]) != group_id]
            if mixed:
                raise BuildError(f"clean group {group_id} mixes dedicated and shared assets: {mixed}")
        _, _, tile_w, tile_h = tile_geometry(len(asset_ids), width, height, padding, gap)
        if any(bool(asset_map[item]["critical"]) for item in asset_ids):
            minimum = int(canvas["min_clean_tile_short_side"])
            if min(tile_w, tile_h) < minimum:
                raise BuildError(
                    f"clean group {group_id} critical tile short side "
                    f"{min(tile_w, tile_h)}px < {minimum}px"
                )
        group_reports.append({
            "id": group_id,
            "asset_ids": asset_ids,
            "primary_roles": roles,
            "tile_width": tile_w,
            "tile_height": tile_h,
        })
    for asset_id, asset in asset_map.items():
        declared = set(asset["clean_groups"])
        if declared != actual_memberships[asset_id]:
            raise BuildError(
                f"clean group mapping mismatch for {asset_id}: "
                f"declared={sorted(declared)}, actual={sorted(actual_memberships[asset_id])}"
            )

    return {
        "schema_version": schema_version,
        "is_v5": is_v5,
        "is_v51": is_v51,
        "project_id": project_id,
        "decision_fingerprint": decision_fingerprint,
        "build_mode": build_mode,
        "registry_eligible": registry_eligible,
        "canvas": canvas,
        "boards": boards,
        "asset_map": asset_map,
        "normalized": normalized,
        "asset_report": asset_report,
        "annotated_ids": annotated_ids,
        "section_by_asset": section_by_asset,
        "section_snapshot": section_snapshot,
        "clean_group_reports": group_reports,
    }

def validate_v51_asset_coverage(requirements: dict[str, Any], assets: dict[str, dict[str, Any]]) -> None:
    if not isinstance(requirements, dict):
        raise BuildError("V5.1 workflow state is missing asset coverage requirements")

    def matching(asset_type: str, owner: str = "") -> list[dict[str, Any]]:
        return [
            asset for asset in assets.values()
            if asset["type"] == asset_type and (not owner or asset["owner"] == owner)
        ]

    for character in requirements["characters"]:
        owner = character["id"]
        identities = matching("character_identity", owner)
        required_views = set(character["identity_views"])
        if not any(required_views <= set(asset["views"]) for asset in identities):
            raise BuildError(f"V5.1 asset coverage missing identity views for {owner}")
        action_tags = set().union(*(set(asset["coverage_tags"]) for asset in matching("expression_action", owner)))
        missing_actions = set(character["expression_actions"]) - action_tags
        if missing_actions:
            raise BuildError(f"V5.1 asset coverage missing actions for {owner}: {sorted(missing_actions)}")

    if requirements["multi_character_scale"] and not matching("character_scale"):
        raise BuildError("V5.1 asset coverage missing multi-character scale asset")

    style_tags = set().union(*(set(asset["coverage_tags"]) for asset in matching("style_anchor")))
    missing_style = set(requirements["style_dimensions"]) - style_tags
    if missing_style:
        raise BuildError(f"V5.1 asset coverage missing style dimensions: {sorted(missing_style)}")

    for asset_type, required_tags in (("prop_detail", requirements["props"]), ("scene_reference", requirements["scenes"])):
        present = set().union(*(set(asset["coverage_tags"]) for asset in matching(asset_type)))
        missing = set(required_tags) - present
        if missing:

            raise BuildError(f"V5.1 asset coverage missing {asset_type}: {sorted(missing)}")
def resolve_workflow_state(
    manifest: dict[str, Any],
    manifest_path: Path,
    explicit: Path | None,
) -> Path | None:
    raw_ref = manifest.get("workflow_state_ref")
    referenced = None
    if isinstance(raw_ref, str) and raw_ref.strip():
        referenced = resolve_input_path(raw_ref, manifest_path.parent)
    explicit_resolved = explicit.resolve() if explicit is not None else None
    if explicit_resolved is not None and referenced is not None and explicit_resolved != referenced:
        raise BuildError(
            "--workflow-state does not match manifest.workflow_state_ref: "
            f"{explicit_resolved} != {referenced}"
        )
    return explicit_resolved or referenced


def validate_workflow_binding(
    manifest: dict[str, Any],
    validated: dict[str, Any],
    manifest_path: Path,
    explicit_state: Path | None,
) -> tuple[dict[str, Any] | None, Path | None]:
    state_path = resolve_workflow_state(manifest, manifest_path, explicit_state)
    if not validated["is_v5"]:
        if state_path is not None:
            raise BuildError("legacy V4 candidate_preview must migrate before binding V5 workflow state")
        return None, None
    if state_path is None:
        raise BuildError("V5 manifest requires --workflow-state or workflow_state_ref")
    try:
        state_report = load_and_validate_state(
            state_path,
            expect_project_id=validated["project_id"],
            require_release_ready=validated["build_mode"] == "release",
        )
    except StateError as exc:
        raise BuildError(f"workflow state invalid: {exc}") from exc
    if state_report["status"] == "blocked":
        # A controlled workflow is deliberately blocked while its hard fidelity
        # gate is unresolved. Its candidate preview is the evidence needed to
        # resolve that gate, so do not make the state machine circular. All
        # other blockers (especially rights) still fail closed.
        risks = state_report["_state"]["risk_modules"]
        unresolved_hard = {
            name for name, item in risks.items()
            if item["level"] == "hard" and item["status"] != "resolved"
        }
        can_build_fidelity_candidate = (
            validated["build_mode"] == "candidate_preview"
            and state_report["workflow_mode"] == "controlled"
            and unresolved_hard == {"fidelity_lock"}
            and state_report["_gates"]["G0"]["status"] == "approved"
        )
        if not can_build_fidelity_candidate:
            raise BuildError("workflow state is blocked; candidate and release generation are forbidden")

    if validated["is_v51"]:
        if state_report["schema_version"] != schema_version:
            raise BuildError("asset manifest schema must match project-state schema")
        validate_v51_asset_coverage(state_report["asset_coverage"], validated["asset_map"])

    decision_fingerprint = validated["decision_fingerprint"]
    matching = [
        decision_id
        for decision_id, decision in state_report["_decisions"].items()
        if decision["fingerprint"] == decision_fingerprint
        and state_report["_decision_validity"][decision_id]["valid"]
    ]
    if not matching:
        raise BuildError("decision_fingerprint is absent or invalid in workflow state")

    workflow_mode = state_report["workflow_mode"]
    gates = state_report["_gates"]
    if validated["build_mode"] == "candidate_preview":
        authorization = state_report["_state"]["standing_authorization"]
        if (
            authorization["generate_one_candidate"] is not True
            or authorization["max_candidates"] < 1
        ):
            raise BuildError(
                "V5 candidate_preview requires standing_authorization: "
                "generate_one_candidate=true and max_candidates>=1"
            )
        if workflow_mode in {"guided", "controlled"} and gates["G0"]["status"] != "approved":
            raise BuildError(f"{workflow_mode} candidate assets require approved G0")
    else:
        if workflow_mode != "controlled":
            raise BuildError("V5 asset-triad release requires controlled workflow")
        approval_event_id = require_string(
            require(manifest, "approval_event_id", "manifest"), "approval_event_id"
        )
        try:
            approval = validate_approval_reference(
                state_report,
                approval_event_id=approval_event_id,
                decision_fingerprint=decision_fingerprint,
                required_gate="G1",
            )
        except StateError as exc:
            raise BuildError(f"release approval invalid: {exc}") from exc
        if approval["event"]["type"] != "user_confirmed":
            raise BuildError("release visual-anchor approval must be user_confirmed")
    return state_report, state_path


def equivalence_snapshot(manifest: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
    annotated = validated["boards"]["annotated"]
    assets: list[dict[str, Any]] = []
    for item in validated["asset_report"]:
        assets.append({
            key: item[key]
            for key in (
                "id",
                "sha256",
                "normalized_sha256",
                "type",
                "label",
                "role",
                "owner",
                "must_preserve",
                "forbidden",
                "contract_versions",
                "rights_scope",
                "contains_text",
                "critical",
                "clean_groups",
                "dedicated_group",
            )
        })
    clean_groups = [
        {
            "id": item["id"],
            "primary_roles": item["primary_roles"],
            "asset_ids": item["asset_ids"],
        }
        for item in validated["clean_group_reports"]
    ]
    return {
        "snapshot_schema": "asset-triad-equivalence-1.0",
        "project_id": validated["project_id"],
        "decision_fingerprint": validated["decision_fingerprint"],
        "canvas": validated["canvas"],
        "annotated": {
            "title": annotated.get("title", ""),
            "sections": validated["section_snapshot"],
        },
        "clean_groups": clean_groups,
        "assets": assets,
    }


def first_difference(left: Any, right: Any, path: str = "snapshot") -> str | None:
    if type(left) is not type(right):
        return f"{path} type changed"
    if isinstance(left, dict):
        if set(left) != set(right):
            return f"{path} keys changed"
        for key in sorted(left):
            difference = first_difference(left[key], right[key], f"{path}.{key}")
            if difference:
                return difference
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path} length changed"
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            difference = first_difference(left_item, right_item, f"{path}[{index}]")
            if difference:
                return difference
        return None
    if left != right:
        return f"{path} changed"
    return None


def bind_baseline_to_g1_preview(
    baseline_path: Path,
    baseline_sha: str,
    validated: dict[str, Any],
    state_report: dict[str, Any],
) -> str:
    event_id = state_report["_gates"]["G1"]["approval_event_id"]
    event = state_report["_events"][event_id]
    if event["type"] != "user_confirmed":
        raise BuildError("G1 baseline must be bound by user_confirmed")
    preview_ids = [
        artifact_id for artifact_id in event["artifact_ids"]
        if artifact_id in state_report["_artifacts"]
        and state_report["_artifact_validity"][artifact_id]["valid"]
        and state_report["_artifacts"][artifact_id]["kind"] == "asset_triad_preview"
        and state_report["_artifacts"][artifact_id]["decision_fingerprint"]
        == validated["decision_fingerprint"]
    ]
    if not preview_ids:
        raise BuildError("G1 approval does not include the current asset_triad_preview")
    state_root = Path(state_report["state_path"]).parent
    path_matches = [
        artifact_id for artifact_id in preview_ids
        if resolve_input_path(str(state_report["_artifacts"][artifact_id]["file"]), state_root)
        == baseline_path
    ]
    if not path_matches:
        raise BuildError("baseline report path does not match the G1 asset_triad_preview artifact")
    hash_matches = [
        artifact_id for artifact_id in path_matches
        if str(state_report["_artifacts"][artifact_id]["fingerprint"]).lower() == baseline_sha
    ]
    if not hash_matches:
        raise BuildError("baseline report sha256 does not match the G1 asset_triad_preview artifact")
    return hash_matches[0]


def load_and_compare_baseline(
    baseline_path: Path | None,
    validated: dict[str, Any],
    snapshot: dict[str, Any],
    state_report: dict[str, Any] | None,
) -> dict[str, Any]:
    if validated["build_mode"] != "release":
        if baseline_path is not None:
            raise BuildError("--baseline-report is only valid for release promotion")
        return {
            "required": False,
            "baseline_report": None,
            "baseline_sha256": None,
            "approval_preview_artifact_id": None,
            "equivalent": None,
            "difference": None,
        }
    if baseline_path is None:
        raise BuildError("V5 release requires --baseline-report from candidate_preview")
    if state_report is None:
        raise BuildError("V5 release baseline requires workflow state")
    resolved = baseline_path.resolve()
    if not resolved.is_file():
        raise BuildError(f"baseline report not found: {resolved}")
    try:
        baseline = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read baseline report: {exc}") from exc
    if not isinstance(baseline, dict):
        raise BuildError("baseline report root must be an object")
    if baseline.get("build_mode") != "candidate_preview":
        raise BuildError("baseline report must come from candidate_preview")
    if baseline.get("manifest_schema_version") != validated["schema_version"]:
        raise BuildError("baseline report schema must match release manifest")
    if baseline.get("project_id") != validated["project_id"]:
        raise BuildError("baseline report project_id does not match release")
    if baseline.get("registry_eligible") is not False:
        raise BuildError("baseline candidate_preview must have registry_eligible=false")
    baseline_snapshot = baseline.get("equivalence_snapshot")
    if not isinstance(baseline_snapshot, dict):
        raise BuildError("baseline report lacks equivalence_snapshot")
    recorded_hash = baseline.get("equivalence_snapshot_sha256")
    actual_baseline_hash = canonical_hash(baseline_snapshot)
    if recorded_hash != actual_baseline_hash:
        raise BuildError("baseline equivalence snapshot hash is invalid")
    baseline_sha = sha256_file(resolved)
    preview_artifact_id = bind_baseline_to_g1_preview(
        resolved, baseline_sha, validated, state_report
    )
    difference = first_difference(baseline_snapshot, snapshot)
    if difference:
        raise BuildError(f"candidate_preview and release are not equivalent: {difference}")
    return {
        "required": True,
        "baseline_report": str(resolved),
        "baseline_sha256": baseline_sha,
        "approval_preview_artifact_id": preview_artifact_id,
        "equivalent": True,
        "difference": None,
    }


def render_annotated(validated: dict[str, Any], font: ImageFont.FreeTypeFont) -> Image.Image:
    canvas = validated["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    padding, gap = int(canvas["padding"]), int(canvas["gap"])
    label_height = int(canvas["label_height"])
    board = Image.new("RGB", (width, height), str(canvas["background"]))
    draw = ImageDraw.Draw(board)
    ids = validated["annotated_ids"]
    cols, _, tile_w, tile_h = tile_geometry(len(ids), width, height, padding, gap)

    for index, asset_id in enumerate(ids):
        row, col = divmod(index, cols)
        x0 = padding + col * (tile_w + gap)
        y0 = padding + row * (tile_h + gap)
        x1, y1 = x0 + tile_w, y0 + tile_h
        draw.rounded_rectangle(
            (x0, y0, x1, y1), radius=18, fill="white", outline="#B8B8B8", width=2
        )
        paste_normalized(
            board,
            validated["normalized"][asset_id],
            (x0 + 12, y0 + label_height + 8, x1 - 12, y1 - 12),
        )
        asset = validated["asset_map"][asset_id]
        section = validated["section_by_asset"][asset_id]
        text = f"{section} · {asset_id} · {asset['label']}\n{asset['role']}"
        lines: list[str] = []
        for raw_line in text.splitlines():
            lines.extend(wrap_text(draw, raw_line, font, tile_w - 28))
        line_height = int(canvas["font_size"] * 1.18)
        if len(lines) * line_height > label_height - 16:
            raise BuildError(f"label overflow for {asset_id}")
        for line_index, line in enumerate(lines):
            draw.text(
                (x0 + 14, y0 + 8 + line_index * line_height),
                line,
                fill="#202020",
                font=font,
            )
    return board


def render_clean(validated: dict[str, Any], group: dict[str, Any]) -> Image.Image:
    canvas = validated["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    padding, gap = int(canvas["padding"]), int(canvas["gap"])
    board = Image.new("RGB", (width, height), str(canvas["background"]))
    ids = list(group["asset_ids"])
    cols, _, tile_w, tile_h = tile_geometry(len(ids), width, height, padding, gap)
    for index, asset_id in enumerate(ids):
        row, col = divmod(index, cols)
        x0 = padding + col * (tile_w + gap)
        y0 = padding + row * (tile_h + gap)
        paste_normalized(
            board,
            validated["normalized"][asset_id],
            (x0, y0, x0 + tile_w, y0 + tile_h),
        )
    return board


def validate_output_names(boards: dict[str, Any]) -> tuple[list[str], str, str]:
    annotated_filename = str(require(boards["annotated"], "filename", "boards.annotated"))
    report_filename = str(require(boards, "report_filename", "boards"))
    clean_groups = list(boards["clean_groups"])
    output_names = [annotated_filename, report_filename]
    output_names.extend(str(require(group, "filename", "clean group")) for group in clean_groups)
    if len(output_names) != len(set(output_names)):
        raise BuildError("output filenames must be unique")
    for name in output_names:
        candidate = Path(name)
        if candidate.is_absolute() or candidate.name != name or name in {".", ".."}:
            raise BuildError(f"output filename must be a plain filename: {name}")
    return output_names, annotated_filename, report_filename


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        raise BuildError(f"manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read manifest: {exc}") from exc

    validated = validate_manifest(manifest, manifest_path)
    state_report, state_path = validate_workflow_binding(
        manifest, validated, manifest_path, args.workflow_state
    )
    snapshot = equivalence_snapshot(manifest, validated)
    snapshot_sha = canonical_hash(snapshot)
    equivalence = load_and_compare_baseline(
        args.baseline_report, validated, snapshot, state_report
    )

    canvas = validated["canvas"]
    font, font_path = load_font(args.font, int(canvas["font_size"]))
    boards = validated["boards"]
    output_names, annotated_filename, report_filename = validate_output_names(boards)
    clean_groups = list(boards["clean_groups"])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [args.out_dir / name for name in output_names]
    existing = [str(path) for path in output_paths if path.exists()]
    if existing:
        raise BuildError(f"refusing to overwrite existing outputs: {existing}")

    annotated = render_annotated(validated, font)
    clean_images = [(group, render_clean(validated, group)) for group in clean_groups]
    workflow_state_summary = None
    if state_report is not None and state_path is not None:
        workflow_state_summary = {
            **public_report(state_report),
            "path": str(state_path),
            "approval_event_id": manifest.get("approval_event_id", ""),
            "decision_fingerprint": validated["decision_fingerprint"],
        }
    report = {
        "project_id": manifest.get("project_id"),
        "version": manifest.get("version"),
        "manifest_schema_version": validated["schema_version"],
        "build_mode": validated["build_mode"],
        "registry_eligible": validated["registry_eligible"],
        "font": font_path,
        "canvas": canvas,
        "workflow_state": workflow_state_summary,
        "assets": validated["asset_report"],
        "clean_groups": validated["clean_group_reports"],
        "equivalence_snapshot": snapshot,
        "equivalence_snapshot_sha256": snapshot_sha,
        "promotion_equivalence": equivalence,
        "outputs": {
            "annotated": annotated_filename,
            "clean": [group["filename"] for group in clean_groups],
            "report": report_filename,
        },
        "diagnostics": {
            "missing_files": [],
            "source_hash_changes": [],
            "text_overflow": [],
            "split_result": "passed",
            "unapproved_assets": [
                item["id"]
                for item in validated["asset_report"]
                if item["approval_status"] != "approved"
            ],
        },
        "checks": {
            "manifest_references_complete": True,
            "source_hashes_verified": True,
            "same_normalized_tiles_used_for_annotated_and_clean": True,
            "no_added_text_in_clean_boards": True,
            "no_added_text_in_clean_boards_meaning": (
                "deterministic compositor added no labels to clean boards"
            ),
            "pixel_level_text_absence_verified": False,
            "verification_method": "not_run",
            "clean_source_text_flags_empty": True,
            "clean_source_text_flags_meaning": (
                "manifest declarations only; source pixels were not inspected for text"
            ),
            "ocr_or_manual_text_qa_run": False,
            "split_limits_passed": True,
            "non_overwrite": True,
            "workflow_state_valid": state_report is not None if validated["is_v5"] else None,
            "approval_reference_valid": (
                equivalence["approval_preview_artifact_id"] is not None
                if validated["build_mode"] == "release" else None
            ),
            "candidate_release_equivalent": equivalence["equivalent"],
        },
    }

    with tempfile.TemporaryDirectory(prefix="asset-board-", dir=args.out_dir) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        annotated.save(temp_dir / annotated_filename, format="PNG")
        for group, image in clean_images:
            image.save(temp_dir / str(group["filename"]), format="PNG")
        (temp_dir / report_filename).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for name in output_names:
            source = temp_dir / name
            target = args.out_dir / name
            if target.exists():
                raise BuildError(f"refusing to overwrite output during commit: {target}")
            shutil.move(str(source), str(target))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"asset-board build failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
