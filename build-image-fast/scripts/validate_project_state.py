#!/usr/bin/env python3
"""Validate the build-image-fast V5 project-state contract.

`validate_state` checks the in-memory contract. `load_and_validate_state` is the
production entry point and additionally verifies current artifact paths and
SHA-256 values against files on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:  # pragma: no cover - exercised by a targeted fail-closed test
    Image = None
    UnidentifiedImageError = OSError


SCHEMA_VERSION = "5.3"
V52_SCHEMA_VERSION = "5.2"
V51_SCHEMA_VERSION = "5.1"
LEGACY_SCHEMA_VERSION = "5.0"
SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, V51_SCHEMA_VERSION, V52_SCHEMA_VERSION, SCHEMA_VERSION}
WORKFLOWS = {"atomic", "direct", "guided", "controlled", "edit"}
GENERATION_ROUTES = {"fast", "stable", "edit"}
REVIEW_MODES = {"adaptive", "full_review"}
RISK_NAMES = {
    "semantic_lock", "fidelity_lock", "rights_lock", "layout_lock", "reuse_audit"
}
RISK_LEVELS = {"none", "low", "medium", "hard"}
RISK_STATUSES = {"resolved", "unresolved", "not_applicable"}
PROJECT_STATUSES = {"active", "blocked", "completed"}
GATE_STATUSES = {"not_required", "pending", "approved", "delivered"}
EVENT_TYPES = {"user_confirmed", "delegated_decision", "system_validation"}
DECISION_SOURCES = {
    "user_input", "user_confirmed", "delegated_decision", "agent_recommendation",
    "agent_decision", "assumption", "system",
}
ARTIFACT_LIFECYCLES = {"planned", "candidate", "approved", "delivered", "invalidated"}
GENERATED_ARTIFACT_KINDS = {
    "candidate_asset", "asset_triad_preview", "fidelity_test", "asset_triad_release",
    "lettering_base_image", "formal_image", "production_image",
}
ROLE_DELIVERABLE_KIND = "role_deliverable"
ROLE_NAMES = {"content_character_director", "art_director", "execution_scribe"}
ROLE_DELIVERABLE_TYPES = {
    "content_pack", "character_contract", "role_matrix", "visual_bible",
    "style_contract", "asset_plan", "reference_map", "asset_board_spec",
    "prompt_route", "prompt_pack", "generation_log", "display_contract",
    "layout_capacity_spec", "layout_geometry_contract", "typography_contract", "lettering_build_report",
}
ASSET_TYPES = {
    "character_identity", "expression_action", "character_scale", "style_anchor",
    "prop_detail", "scene_reference", "fidelity_test",
}
REQUIRED_EXPRESSION_ACTIONS = {"neutral", "common_emotion", "max_allowed_action"}
REQUIRED_CHARACTER_VIEWS = {"front", "three_quarter"}
FORMAL_ARTIFACT_KINDS = {"formal_image", "production_image"}
FILE_VERIFIED_KINDS = GENERATED_ARTIFACT_KINDS | {
    "qa_report", "lettering_fit_report", "build_pack", ROLE_DELIVERABLE_KIND,
}
RIGHTS_FORBIDDEN_SOURCES = {
    "delegated_decision", "agent_recommendation", "agent_decision", "assumption", "system"
}
USER_EVIDENCE_SOURCES = {"user_input", "user_confirmed"}
USER_AUTHORIZATION_SOURCES = {
    "user_request", "user_confirmed", "migrated_user_confirmation"
}
ASSET_BOARD_EXCLUDABLE_TEXT_FIELDS = {
    "exact_text",
    "exact_copy",
    "dialogue_text",
    "caption_text",
    "lettering_text",
    "title_text",
    "body_copy",
}
DISPLAY_TEXT_FIELDS = ASSET_BOARD_EXCLUDABLE_TEXT_FIELDS
DISPLAY_PROFILES = {"simple_rect", "actual_shape"}
DISPLAY_CONTAINER_PRESENCE = {"required", "forbidden"}
DISPLAY_TEXT_MODES = {"exact", "none"}
DISPLAY_REPEAT_RULES = {"same_text", "same_presence", "independent"}
DISPLAY_SEMANTIC_ROLES = {"dialogue", "primary_anchor", "object_label", "footer"}
TYPOGRAPHY_PROFILES = {"standard", "comic_display"}
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class StateError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--expect-project-id")
    parser.add_argument("--require-release-ready", action="store_true")
    return parser.parse_args()


def require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise StateError(f"{context} missing required field: {key}")
    return mapping[key]


def object_value(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StateError(f"{context} must be an object")
    return value


def list_value(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise StateError(f"{context} must be a list")
    return value


def string_value(value: Any, context: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        kind = "string" if empty else "non-empty string"
        raise StateError(f"{context} must be a {kind}")
    return value


def bool_value(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise StateError(f"{context} must be a boolean")
    return value


def int_value(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise StateError(f"{context} must be an integer >= {minimum}")
    return value


def sha_value(value: Any, context: str, *, empty: bool = False) -> str:
    result = string_value(value, context, empty=empty).lower()
    if result or not empty:
        if not HEX_64.fullmatch(result):
            raise StateError(f"{context} must be a lowercase SHA-256 fingerprint")
    return result


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def decision_record_fingerprint(
    record_id: str,
    gate: str,
    field: str,
    source: str,
    value_fingerprint: str,
    dependencies: list[str],
    dependency_fingerprints: dict[str, str],
) -> str:
    return canonical_fingerprint(
        {
            "id": record_id,
            "gate": gate,
            "field": field,
            "source": source,
            "value_fingerprint": value_fingerprint,
            "depends_on": sorted(dependencies),
            "dependency_fingerprints": {
                key: dependency_fingerprints[key] for key in sorted(dependency_fingerprints)
            },
        }
    )


def dependency_closure(
    decisions: dict[str, dict[str, Any]], seed_ids: set[str]
) -> set[str]:
    result: set[str] = set()
    pending = list(seed_ids)
    while pending:
        record_id = pending.pop()
        if record_id in result:
            continue
        result.add(record_id)
        pending.extend(
            dependency for dependency in decisions[record_id]["depends_on"]
            if dependency in decisions
        )
    return result


def field_can_be_excluded_from_asset_board(field: str) -> bool:
    normalized = field.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in ASSET_BOARD_EXCLUDABLE_TEXT_FIELDS


def validate_display_semantics(value: Any, *, require_v53: bool = False) -> dict[str, Any]:
    spec = object_value(value, "display_semantics.value")
    profile = string_value(require(spec, "profile", "display_semantics.value"), "display_semantics.value.profile")
    if profile not in DISPLAY_PROFILES:
        raise StateError("display_semantics.profile is invalid")
    elements = list_value(require(spec, "elements", "display_semantics.value"), "display_semantics.value.elements")
    if not elements:
        raise StateError("display_semantics.elements must not be empty")
    result: dict[str, dict[str, Any]] = {}
    repeat_groups: dict[str, str] = {}
    for index, raw in enumerate(elements):
        context = f"display_semantics.elements[{index}]"
        item = object_value(raw, context)
        element_id = string_value(require(item, "id", context), f"{context}.id")
        if element_id in result:
            raise StateError(f"duplicate display element id: {element_id}")
        string_value(require(item, "panel_id", context), f"{context}.panel_id")
        string_value(require(item, "target_object", context), f"{context}.target_object")
        presence = string_value(require(item, "container_presence", context), f"{context}.container_presence")
        text_mode = string_value(require(item, "text_mode", context), f"{context}.text_mode")
        if presence not in DISPLAY_CONTAINER_PRESENCE or text_mode not in DISPLAY_TEXT_MODES:
            raise StateError(f"{context} has invalid container_presence or text_mode")
        max_lines = int_value(require(item, "max_lines", context), f"{context}.max_lines", minimum=1)
        semantic_role = string_value(item.get("semantic_role", ""), f"{context}.semantic_role", empty=not require_v53)
        reading_priority = int_value(item.get("reading_priority", 0), f"{context}.reading_priority", minimum=1 if require_v53 else 0)
        if semantic_role and semantic_role not in DISPLAY_SEMANTIC_ROLES:
            raise StateError(f"{context}.semantic_role is invalid")
        text_key = string_value(item.get("text_key", ""), f"{context}.text_key", empty=True)
        blank_allowed = bool_value(item.get("blank_container_allowed", False), f"{context}.blank_container_allowed")
        blank_reason = string_value(item.get("blank_reason", ""), f"{context}.blank_reason", empty=True)
        if text_mode == "exact" and (not text_key or blank_allowed or blank_reason):
            raise StateError(f"{context} exact text requires text_key and cannot allow a blank container")
        if text_mode == "none" and presence == "required" and (not blank_allowed or not blank_reason):
            raise StateError(f"{context} required blank container needs explicit allowance and reason")
        if text_mode == "none" and text_key:
            raise StateError(f"{context} text_mode none cannot have text_key")
        group = string_value(item.get("repeat_group", ""), f"{context}.repeat_group", empty=True)
        rule = string_value(item.get("repeat_rule", ""), f"{context}.repeat_rule", empty=True)
        if bool(group) != bool(rule):
            raise StateError(f"{context} repeat_group and repeat_rule must be specified together")
        if rule and rule not in DISPLAY_REPEAT_RULES:
            raise StateError(f"{context}.repeat_rule is invalid")
        if group:
            previous = repeat_groups.get(group)
            if previous and previous != rule:
                raise StateError(f"repeat group {group} has conflicting rules")
            repeat_groups[group] = rule
        result[element_id] = {
            "id": element_id,
            "text_mode": text_mode,
            "text_key": text_key,
            "container_presence": presence,
            "max_lines": max_lines,
            "semantic_role": semantic_role,
            "reading_priority": reading_priority,
            "repeat_group": group,
            "repeat_rule": rule,
        }
    return {"profile": profile, "elements": result}


def validate_exact_text(value: Any, display: dict[str, Any]) -> dict[str, str]:
    payload = object_value(value, "exact_text.value")
    strings = object_value(require(payload, "strings", "exact_text.value"), "exact_text.value.strings")
    normalized = {
        string_value(key, "exact_text key"): string_value(text, f"exact_text.strings.{key}")
        for key, text in strings.items()
    }
    expected = {
        item["text_key"] for item in display["elements"].values()
        if item["text_mode"] == "exact"
    }
    if set(normalized) != expected:
        raise StateError("exact_text.strings must exactly cover display_semantics exact text keys")
    return normalized

def unique_string_set(value: Any, context: str) -> set[str]:
    values = list_value(value, context)
    if not values or not all(isinstance(item, str) and item.strip() for item in values):
        raise StateError(f"{context} must contain non-empty strings")
    result = {item.strip() for item in values}
    if len(result) != len(values):
        raise StateError(f"{context} must not contain duplicates")
    return result


def validate_asset_coverage_spec(spec: dict[str, Any]) -> dict[str, Any]:
    coverage = object_value(require(spec, "coverage", "asset_board_spec.value"), "asset_board_spec.value.coverage")
    characters = list_value(require(coverage, "characters", "asset_board_spec.coverage"), "asset_board_spec.coverage.characters")
    if not characters:
        raise StateError("asset_board_spec.coverage.characters must not be empty")
    resolved_characters: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(characters):
        item = object_value(raw, f"asset_board_spec.coverage.characters[{index}]")
        character_id = string_value(require(item, "id", "asset character"), "asset character.id")
        if character_id in seen:
            raise StateError(f"asset_board_spec.coverage has duplicate character: {character_id}")
        seen.add(character_id)
        views = unique_string_set(require(item, "identity_views", "asset character"), f"{character_id}.identity_views")
        if not REQUIRED_CHARACTER_VIEWS <= views or not ({"side", "back"} & views):
            raise StateError(f"{character_id}.identity_views must include front, three_quarter, and side or back")
        actions = unique_string_set(require(item, "expression_actions", "asset character"), f"{character_id}.expression_actions")
        if not REQUIRED_EXPRESSION_ACTIONS <= actions:
            raise StateError(f"{character_id}.expression_actions must include {sorted(REQUIRED_EXPRESSION_ACTIONS)}")
        resolved_characters.append({"id": character_id, "identity_views": sorted(views), "expression_actions": sorted(actions)})
    scale = bool_value(require(coverage, "multi_character_scale", "asset_board_spec.coverage"), "asset_board_spec.coverage.multi_character_scale")
    if len(resolved_characters) > 1 and not scale:
        raise StateError("asset_board_spec.coverage requires multi_character_scale for two or more characters")
    styles = unique_string_set(require(coverage, "style_dimensions", "asset_board_spec.coverage"), "asset_board_spec.coverage.style_dimensions")
    props = unique_string_set(require(coverage, "props", "asset_board_spec.coverage"), "asset_board_spec.coverage.props")
    scenes = unique_string_set(require(coverage, "scenes", "asset_board_spec.coverage"), "asset_board_spec.coverage.scenes")
    if require(coverage, "forbid_narrative_substitution", "asset_board_spec.coverage") is not True:
        raise StateError("asset_board_spec.coverage.forbid_narrative_substitution must be true")
    return {"characters": resolved_characters, "multi_character_scale": scale, "style_dimensions": sorted(styles), "props": sorted(props), "scenes": sorted(scenes)}


def validate_frontstage(value: Any) -> dict[str, Any]:
    item = object_value(value, "frontstage")
    for field in ("current_stage", "completed_this_round", "pending_user_decision", "next_action", "after_confirmation"):
        string_value(require(item, field, "frontstage"), f"frontstage.{field}")
    item["remaining_confirmations"] = int_value(require(item, "remaining_confirmations", "frontstage"), "frontstage.remaining_confirmations")
    return item


def validity_map(
    effective: dict[str, Any], key: str, expected_ids: set[str]
) -> dict[str, dict[str, Any]]:
    raw = object_value(require(effective, key, "effective_validity"), f"effective_validity.{key}")
    if set(raw) != expected_ids:
        raise StateError(
            f"effective_validity.{key} must exactly cover current records; "
            f"missing={sorted(expected_ids - set(raw))}, extra={sorted(set(raw) - expected_ids)}"
        )
    result: dict[str, dict[str, Any]] = {}
    for record_id, raw_entry in raw.items():
        entry = object_value(raw_entry, f"effective_validity.{key}.{record_id}")
        valid = bool_value(require(entry, "valid", record_id), f"{record_id}.valid")
        reason = string_value(require(entry, "reason", record_id), f"{record_id}.reason", empty=True)
        if not valid and not reason.strip():
            raise StateError(f"invalid {record_id} requires a non-empty validity reason")
        result[record_id] = {"valid": valid, "reason": reason}
    return result


def minimum_workflow(risks: dict[str, dict[str, Any]]) -> str:
    levels = [item["level"] for item in risks.values()]
    if "hard" in levels or levels.count("medium") >= 2:
        return "controlled"
    if levels.count("medium") == 1:
        return "guided"
    return "direct"


def gate_floor(workflow: str) -> dict[str, bool]:
    return {
        "G0": workflow in {"guided", "controlled"},
        "G1": workflow == "controlled",
        "G2": workflow != "atomic",
    }


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    active: set[str] = set()
    done: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in active:
            return path[path.index(node):] + [node]
        if node in done:
            return None
        active.add(node)
        path.append(node)
        for dependency in graph[node]:
            cycle = visit(dependency)
            if cycle:
                return cycle
        path.pop()
        active.remove(node)
        done.add(node)
        return None

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def validate_state(
    state: dict[str, Any],
    *,
    expect_project_id: str | None = None,
    require_release_ready: bool = False,
) -> dict[str, Any]:
    state = object_value(state, "project state")
    schema_version = string_value(require(state, "schema_version", "project state"), "schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise StateError(f"project state schema_version must be one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}")
    is_v51 = schema_version in {V51_SCHEMA_VERSION, V52_SCHEMA_VERSION, SCHEMA_VERSION}
    is_v52 = schema_version in {V52_SCHEMA_VERSION, SCHEMA_VERSION}
    is_v53 = schema_version == SCHEMA_VERSION
    project_id = string_value(require(state, "project_id", "project state"), "project_id")
    revision = int_value(require(state, "state_revision", "project state"), "state_revision", minimum=1)
    internal_stage = int_value(
        require(state, "current_internal_stage", "project state"),
        "current_internal_stage", minimum=1,
    )
    if internal_stage > 8:
        raise StateError("current_internal_stage must be between 1 and 8")
    if expect_project_id is not None and project_id != expect_project_id:
        raise StateError(f"project_id mismatch: state={project_id!r}, expected={expect_project_id!r}")
    status = string_value(require(state, "status", "project state"), "status")
    workflow = string_value(require(state, "workflow_mode", "project state"), "workflow_mode")
    route = string_value(require(state, "generation_route", "project state"), "generation_route")
    review = string_value(require(state, "review_mode", "project state"), "review_mode")
    if status not in PROJECT_STATUSES:
        raise StateError(f"status must be one of {sorted(PROJECT_STATUSES)}")
    if workflow not in WORKFLOWS:
        raise StateError(f"workflow_mode must be one of {sorted(WORKFLOWS)}")
    if route not in GENERATION_ROUTES:
        raise StateError(f"generation_route must be one of {sorted(GENERATION_ROUTES)}")
    if review not in REVIEW_MODES:
        raise StateError(f"review_mode must be one of {sorted(REVIEW_MODES)}")

    for key in ("assumptions", "tool_calls", "handoff_events"):
        values = list_value(require(state, key, "project state"), key)
        if not all(isinstance(item, dict) for item in values):
            raise StateError(f"{key} entries must be objects")

    raw_risks = object_value(require(state, "risk_modules", "project state"), "risk_modules")
    if set(raw_risks) != RISK_NAMES:
        raise StateError(f"risk_modules must contain exactly {sorted(RISK_NAMES)}")
    risks: dict[str, dict[str, Any]] = {}
    for name in RISK_NAMES:
        item = object_value(raw_risks[name], f"risk_modules.{name}")
        level = string_value(require(item, "level", name), f"{name}.level")
        risk_status = string_value(require(item, "status", name), f"{name}.status")
        evidence = list_value(require(item, "evidence", name), f"{name}.evidence")
        if level not in RISK_LEVELS or risk_status not in RISK_STATUSES:
            raise StateError(f"risk_modules.{name} has invalid level or status")
        if level == "none" and risk_status == "unresolved":
            raise StateError(f"risk_modules.{name} cannot be unresolved at level none")
        if risk_status == "not_applicable" and level != "none":
            raise StateError(f"risk_modules.{name} not_applicable requires level none")
        if not all(isinstance(record_id, str) and record_id for record_id in evidence):
            raise StateError(f"risk_modules.{name}.evidence must contain non-empty IDs")
        risks[name] = {"level": level, "status": risk_status, "evidence": evidence}

    floor = minimum_workflow(risks)
    ranks = {"direct": 0, "guided": 1, "controlled": 2}
    if workflow == "atomic":
        below_floor = floor != "direct"
    elif workflow == "edit":
        below_floor = any(item["level"] == "hard" for item in risks.values())
    else:
        below_floor = ranks[workflow] < ranks[floor]
    if below_floor:
        raise StateError(f"workflow_mode {workflow} is below risk floor {floor}")
    blockers = list_value(require(state, "blockers", "project state"), "blockers")
    hard_unresolved = any(
        item["level"] == "hard" and item["status"] != "resolved" for item in risks.values()
    )
    rights = risks["rights_lock"]
    rights_unresolved = rights["level"] != "none" and rights["status"] != "resolved"
    if (hard_unresolved or rights_unresolved) and status != "blocked":
        raise StateError("unresolved hard risk or rights risk requires project status blocked")
    if status == "blocked" and not blockers:
        raise StateError("blocked project requires at least one blocker")

    raw_gates = object_value(require(state, "gates", "project state"), "gates")
    if set(raw_gates) != {"G0", "G1", "G2"}:
        raise StateError("gates must contain exactly G0, G1 and G2")
    floor_gates = gate_floor(workflow)
    gates: dict[str, dict[str, Any]] = {}
    for gate_id in ("G0", "G1", "G2"):
        item = object_value(raw_gates[gate_id], f"gates.{gate_id}")
        required_flag = bool_value(require(item, "required", gate_id), f"{gate_id}.required")
        gate_status = string_value(require(item, "status", gate_id), f"{gate_id}.status")
        decision_ids = list_value(require(item, "decision_ids", gate_id), f"{gate_id}.decision_ids")
        approval = string_value(
            require(item, "approval_event_id", gate_id), f"{gate_id}.approval_event_id", empty=True
        )
        if gate_status not in GATE_STATUSES:
            raise StateError(f"{gate_id}.status must be one of {sorted(GATE_STATUSES)}")
        if review == "adaptive" and required_flag != floor_gates[gate_id]:
            raise StateError(f"adaptive {workflow} has incorrect {gate_id}.required")
        if review == "full_review" and floor_gates[gate_id] and not required_flag:
            raise StateError(f"full_review cannot disable required gate {gate_id}")
        if required_flag == (gate_status == "not_required"):
            raise StateError(f"gate {gate_id} required/status values conflict")
        if gate_id in {"G0", "G1"} and gate_status == "delivered":
            raise StateError(f"{gate_id} is a decision gate and cannot be delivered")
        if gate_id == "G2" and gate_status == "approved":
            raise StateError("G2 is automatic QA/delivery and must use delivered, not approved")
        if gate_status in {"approved", "delivered"} and not approval:
            raise StateError(f"completed gate {gate_id} requires approval_event_id")
        if gate_status in {"pending", "not_required"} and approval:
            raise StateError(f"gate {gate_id} cannot reference approval while {gate_status}")
        gates[gate_id] = {
            "required": required_flag, "status": gate_status,
            "decision_ids": decision_ids, "approval_event_id": approval,
        }
    if (status == "completed") != (gates["G2"]["status"] == "delivered"):
        raise StateError("project status completed if and only if G2 is delivered")

    team = object_value(require(state, "team", "project state"), "team")
    if require(team, "execution_mode", "team") not in {"physical_subagents", "serial_roles"}:
        raise StateError("team.execution_mode is invalid")
    if require(team, "client_window", "team") != "图片总编":
        raise StateError("team.client_window must be 图片总编")
    string_value(require(team, "current_lead", "team"), "team.current_lead")
    bool_value(require(team, "team_intro_shown", "team"), "team.team_intro_shown")
    string_value(
        require(team, "last_handoff_announced_version", "team"),
        "team.last_handoff_announced_version", empty=True,
    )

    frontstage = validate_frontstage(require(state, "frontstage", "project state")) if is_v51 else None
    auth = object_value(require(state, "standing_authorization", "project state"), "standing_authorization")
    generation_authorized = bool_value(
        require(auth, "generate_one_candidate", "authorization"),
        "authorization.generate_one_candidate",
    )
    max_candidates = int_value(require(auth, "max_candidates", "authorization"), "authorization.max_candidates")
    bool_value(require(auth, "external_publish", "authorization"), "authorization.external_publish")
    authorization_source = string_value(
        require(auth, "source", "authorization"), "authorization.source"
    )
    if authorization_source not in USER_AUTHORIZATION_SOURCES:
        raise StateError("standing_authorization.source must be a user authorization source")

    delegation = object_value(require(state, "delegation_scope", "project state"), "delegation_scope")
    delegation_enabled = bool_value(require(delegation, "enabled", "delegation_scope"), "delegation_scope.enabled")
    allowed = set(list_value(require(delegation, "allowed_fields", "delegation_scope"), "delegation_scope.allowed_fields"))
    excluded = set(list_value(require(delegation, "excluded_fields", "delegation_scope"), "delegation_scope.excluded_fields"))
    authorized_by = string_value(
        require(delegation, "authorized_by", "delegation_scope"),
        "delegation_scope.authorized_by",
        empty=True,
    )
    delegation_source = string_value(
        require(delegation, "source", "delegation_scope"),
        "delegation_scope.source",
        empty=True,
    )
    if not all(isinstance(item, str) and item for item in allowed | excluded) or allowed & excluded:
        raise StateError("delegation field lists are invalid")
    if "rights_scope" not in excluded:
        raise StateError("delegation_scope must always exclude rights_scope")
    if delegation_enabled and (
        authorized_by != "user" or delegation_source not in USER_AUTHORIZATION_SOURCES
    ):
        raise StateError("enabled delegation_scope requires explicit user authorization")

    decisions: dict[str, dict[str, Any]] = {}
    idempotency: set[tuple[str, str]] = set()
    for index, raw in enumerate(list_value(require(state, "decisions", "project state"), "decisions")):
        context = f"decisions[{index}]"
        item = object_value(raw, context)
        record_id = string_value(require(item, "id", context), f"{context}.id")
        if record_id in decisions:
            raise StateError(f"duplicate decision id: {record_id}")
        gate = string_value(require(item, "gate", context), f"{context}.gate")
        field = string_value(require(item, "field", context), f"{context}.field")
        source = string_value(require(item, "source", context), f"{context}.source")
        fingerprint = sha_value(require(item, "fingerprint", context), f"{context}.fingerprint")
        dependencies = list_value(require(item, "depends_on", context), f"{context}.depends_on")
        dep_fps_raw = object_value(
            require(item, "dependency_fingerprints", context),
            f"{context}.dependency_fingerprints",
        )
        dep_fps = {
            string_value(dep_id, f"{context}.dependency_fingerprints key"):
            sha_value(dep_fp, f"{context}.dependency_fingerprints.{dep_id}")
            for dep_id, dep_fp in dep_fps_raw.items()
        }
        record_fingerprint = sha_value(
            require(item, "record_fingerprint", context), f"{context}.record_fingerprint"
        )
        if gate not in {"G0", "G1", "G2", "internal"} or source not in DECISION_SOURCES:
            raise StateError(f"{context} has invalid gate or source")
        if fingerprint != canonical_fingerprint(require(item, "value", context)):
            raise StateError(f"decision fingerprint mismatch for {record_id}")
        expected_record = decision_record_fingerprint(
            record_id,
            gate,
            field,
            source,
            fingerprint,
            dependencies,
            dep_fps,
        )
        if record_fingerprint != expected_record:
            raise StateError(f"decision record_fingerprint mismatch for {record_id}")
        key = (field, fingerprint)
        if key in idempotency:
            raise StateError(f"idempotency violation: repeated value for field {field}")
        idempotency.add(key)
        decisions[record_id] = {
            **item,
            "fingerprint": fingerprint,
            "depends_on": dependencies,
            "dependency_fingerprints": dep_fps,
            "record_fingerprint": record_fingerprint,
        }

    artifacts: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(list_value(require(state, "artifacts", "project state"), "artifacts")):
        context = f"artifacts[{index}]"
        item = object_value(raw, context)
        record_id = string_value(require(item, "id", context), f"{context}.id")
        if record_id in decisions or record_id in artifacts:
            raise StateError(f"duplicate decision/artifact id: {record_id}")
        kind = string_value(require(item, "kind", context), f"{context}.kind")
        for field_name in ("version", "file"):
            string_value(require(item, field_name, context), f"{context}.{field_name}")
        fingerprint = sha_value(require(item, "fingerprint", context), f"{context}.fingerprint")
        decision_fingerprint = sha_value(
            require(item, "decision_fingerprint", context), f"{context}.decision_fingerprint", empty=True
        )
        dependencies = list_value(require(item, "depends_on", context), f"{context}.depends_on")
        lifecycle = string_value(require(item, "lifecycle", context), f"{context}.lifecycle")
        if lifecycle not in ARTIFACT_LIFECYCLES:
            raise StateError(f"{context}.lifecycle is invalid")
        approval = string_value(require(item, "approval_event_id", context), f"{context}.approval_event_id", empty=True)
        candidate_set_id = string_value(
            item.get("candidate_set_id", ""), f"{context}.candidate_set_id", empty=True
        )
        if kind in GENERATED_ARTIFACT_KINDS and lifecycle not in {"planned", "invalidated"} and not candidate_set_id:
            raise StateError(f"{context} current generated artifact requires candidate_set_id")
        deliverable_slot_id = string_value(
            item.get("deliverable_slot_id", ""), f"{context}.deliverable_slot_id", empty=True
        )
        if kind in FORMAL_ARTIFACT_KINDS and not deliverable_slot_id:
            raise StateError(f"{context} formal artifact requires deliverable_slot_id")
        dep_fps_raw = object_value(item.get("dependency_fingerprints", {}), f"{context}.dependency_fingerprints")
        dep_fps = {
            string_value(dep_id, f"{context}.dependency_fingerprints key"):
            sha_value(dep_fp, f"{context}.dependency_fingerprints.{dep_id}")
            for dep_id, dep_fp in dep_fps_raw.items()
        }
        if kind == ROLE_DELIVERABLE_KIND:
            role = string_value(require(item, "role", context), f"{context}.role")
            deliverable_type = string_value(require(item, "deliverable_type", context), f"{context}.deliverable_type")
            if role not in ROLE_NAMES:
                raise StateError(f"{context}.role is not a supported specialist role")
            if deliverable_type not in ROLE_DELIVERABLE_TYPES:
                raise StateError(f"{context}.deliverable_type is invalid")
            self_check = object_value(require(item, "self_check", context), f"{context}.self_check")
            string_value(require(self_check, "result", context), f"{context}.self_check.result")
            string_value(require(self_check, "summary", context), f"{context}.self_check.summary")
        artifacts[record_id] = {
            **item,
            "kind": kind,
            "fingerprint": fingerprint,
            "decision_fingerprint": decision_fingerprint,
            "depends_on": dependencies,
            "approval_event_id": approval,
            "candidate_set_id": candidate_set_id,
            "deliverable_slot_id": deliverable_slot_id,
            "dependency_fingerprints": dep_fps,
        }

    entities = {**decisions, **artifacts}
    graph = {record_id: list(item["depends_on"]) for record_id, item in entities.items()}
    for record_id, dependencies in graph.items():
        missing = [dependency for dependency in dependencies if dependency not in entities]
        if missing:
            raise StateError(f"{record_id} has unknown dependencies: {missing}")
    cycle = find_cycle(graph)
    if cycle:
        raise StateError(f"decision/artifact dependency cycle: {' -> '.join(cycle)}")
    for decision_id, decision_item in decisions.items():
        dep_fps = decision_item["dependency_fingerprints"]
        if set(dep_fps) != set(decision_item["depends_on"]):
            raise StateError(f"decision {decision_id} must snapshot every dependency edge")
    for artifact_id, artifact in artifacts.items():
        dep_fps = artifact["dependency_fingerprints"]
        if set(dep_fps) != set(artifact["depends_on"]):
            raise StateError(f"artifact {artifact_id} must snapshot every dependency edge")
    effective = object_value(require(state, "effective_validity", "project state"), "effective_validity")
    decision_validity = validity_map(effective, "decisions", set(decisions))
    artifact_validity = validity_map(effective, "artifacts", set(artifacts))
    validity = {**decision_validity, **artifact_validity}
    for record_id, item in entities.items():
        if not validity[record_id]["valid"]:
            continue
        for dependency_id, fingerprint in item["dependency_fingerprints"].items():
            if entities[dependency_id]["fingerprint"] != fingerprint:
                kind = "decision" if record_id in decisions else "artifact"
                raise StateError(
                    f"{kind} {record_id} has stale dependency fingerprint for {dependency_id}"
                )
    for record_id, dependencies in graph.items():
        if validity[record_id]["valid"]:
            invalid = [dependency for dependency in dependencies if not validity[dependency]["valid"]]
            if invalid:
                raise StateError(
                    f"invalidation closure violation: valid {record_id} depends on invalid {invalid}"
                )
    current_fields: dict[str, list[str]] = {}
    for record_id, item in decisions.items():
        if decision_validity[record_id]["valid"]:
            current_fields.setdefault(item["field"], []).append(record_id)
    duplicate_fields = {field: ids for field, ids in current_fields.items() if len(ids) > 1}
    if duplicate_fields:
        raise StateError(f"multiple currently valid decisions for one field: {duplicate_fields}")
    if workflow == "edit" and any(item["level"] == "medium" for item in risks.values()):
        if "edit_contract" not in current_fields:
            raise StateError("edit workflow with medium risk requires a current edit_contract decision")

    events: dict[str, dict[str, Any]] = {}
    signatures: set[tuple[Any, ...]] = set()
    previous_expected_revision = -1
    history = list_value(require(state, "confirmation_history", "project state"), "confirmation_history")
    for index, raw in enumerate(history):
        context = f"confirmation_history[{index}]"
        item = object_value(raw, context)
        event_id = string_value(require(item, "id", context), f"{context}.id")
        if event_id in events:
            raise StateError(f"duplicate confirmation event id: {event_id}")
        gate = string_value(require(item, "gate", context), f"{context}.gate")
        event_type = string_value(require(item, "type", context), f"{context}.type")
        actor = string_value(require(item, "actor", context), f"{context}.actor")
        string_value(require(item, "recorded_at", context), f"{context}.recorded_at")
        expected_revision = int_value(
            require(item, "expected_revision", context), f"{context}.expected_revision"
        )
        if expected_revision <= previous_expected_revision or expected_revision >= revision:
            raise StateError(
                "confirmation_history expected_revision must increase and precede state_revision"
            )
        previous_expected_revision = expected_revision
        decision_ids = list_value(
            require(item, "decision_ids", context), f"{context}.decision_ids"
        )
        artifact_ids = list_value(item.get("artifact_ids", []), f"{context}.artifact_ids")
        decision_fps = list_value(
            require(item, "decision_fingerprints", context), f"{context}.decision_fingerprints"
        )
        decision_record_fps = list_value(
            require(item, "decision_record_fingerprints", context),
            f"{context}.decision_record_fingerprints",
        )
        artifact_fps_raw = object_value(
            require(item, "artifact_fingerprints", context),
            f"{context}.artifact_fingerprints",
        )
        artifact_fps = {
            string_value(artifact_id, f"{context}.artifact_fingerprints key"):
            sha_value(value, f"{context}.artifact_fingerprints.{artifact_id}")
            for artifact_id, value in artifact_fps_raw.items()
        }
        if gate not in {"G0", "G1", "G2"} or event_type not in EVENT_TYPES:
            raise StateError(f"{context} has invalid gate or type")
        if event_type == "user_confirmed" and actor != "user":
            raise StateError(f"{context} user_confirmed actor must be user")
        if event_type == "delegated_decision" and actor != "user":
            raise StateError(f"{context} delegated_decision actor must be user")
        if event_type == "system_validation" and actor not in {"qa_system", "system"}:
            raise StateError(f"{context} system_validation actor must be qa_system or system")
        if not decision_ids and not artifact_ids:
            raise StateError(f"{context} must reference a decision or artifact")
        if len(decision_ids) != len(decision_fps) or len(decision_ids) != len(decision_record_fps):
            raise StateError(f"{context} decision/fingerprint length mismatch")
        for decision_id, fingerprint, record_fingerprint in zip(
            decision_ids, decision_fps, decision_record_fps
        ):
            if decision_id not in decisions:
                raise StateError(f"{context} references unknown decision {decision_id}")
            if sha_value(
                fingerprint, f"{context}.decision_fingerprint"
            ) != decisions[decision_id]["fingerprint"]:
                raise StateError(f"{context} fingerprint is stale for decision {decision_id}")
            if sha_value(
                record_fingerprint, f"{context}.decision_record_fingerprint"
            ) != decisions[decision_id]["record_fingerprint"]:
                raise StateError(
                    f"{context} record_fingerprint is stale for decision {decision_id}"
                )
        if any(artifact_id not in artifacts for artifact_id in artifact_ids):
            raise StateError(f"{context} references unknown artifact")
        if set(artifact_fps) != set(artifact_ids):
            raise StateError(f"{context} artifact_fingerprints must exactly cover artifact_ids")
        for artifact_id, fingerprint in artifact_fps.items():
            if artifacts[artifact_id]["fingerprint"] != fingerprint:
                raise StateError(f"{context} artifact fingerprint is stale for {artifact_id}")
        signature = (
            gate,
            event_type,
            tuple(decision_ids),
            tuple(decision_fps),
            tuple(decision_record_fps),
            tuple(artifact_ids),
            tuple(sorted(artifact_fps.items())),
        )
        if signature in signatures:
            raise StateError("idempotency violation: repeated confirmation must reuse its event")
        signatures.add(signature)
        if event_type == "delegated_decision":
            fields = {decisions[decision_id]["field"] for decision_id in decision_ids}
            if not delegation_enabled or fields & excluded or not fields <= allowed:
                raise StateError(f"{context} exceeds delegation scope")
        events[event_id] = {
            **item,
            "gate": gate,
            "type": event_type,
            "actor": actor,
            "decision_ids": decision_ids,
            "decision_fingerprints": decision_fps,
            "decision_record_fingerprints": decision_record_fps,
            "artifact_ids": artifact_ids,
            "artifact_fingerprints": artifact_fps,
        }

    approval_validity = validity_map(effective, "approval_events", set(events))
    for event_id, event in events.items():
        if approval_validity[event_id]["valid"]:
            invalid_decisions = [
                record_id for record_id in event["decision_ids"]
                if not decision_validity[record_id]["valid"]
            ]
            invalid_artifacts = [
                record_id for record_id in event["artifact_ids"]
                if not artifact_validity[record_id]["valid"]
            ]
            if invalid_decisions or invalid_artifacts:
                raise StateError(f"approval {event_id} references invalid current records")

    evidence_validity = {**validity, **approval_validity}
    for name, risk in risks.items():
        missing = [
            record_id for record_id in risk["evidence"]
            if record_id not in evidence_validity
        ]
        if missing:
            raise StateError(f"risk_modules.{name} references unknown evidence: {missing}")
        stale = [
            record_id for record_id in risk["evidence"]
            if not evidence_validity[record_id]["valid"]
        ]
        if stale:
            raise StateError(f"risk_modules.{name} references invalid evidence: {stale}")
        needs_evidence = risk["status"] == "resolved" and (
            risk["level"] == "hard"
            or (name == "rights_lock" and risk["level"] != "none")
        )
        if needs_evidence and not risk["evidence"]:
            raise StateError(f"resolved {name} requires current effective evidence")

    if rights["status"] == "resolved" and rights["level"] != "none":
        rights_decisions = [
            record_id for record_id in rights["evidence"]
            if record_id in decisions
            and decision_validity[record_id]["valid"]
            and decisions[record_id]["field"] == "rights_scope"
        ]
        if not rights_decisions:
            raise StateError("resolved rights_lock requires a current rights_scope decision")
        forbidden = [
            record_id for record_id in rights_decisions
            if decisions[record_id]["source"] in RIGHTS_FORBIDDEN_SOURCES
            or decisions[record_id]["source"] not in USER_EVIDENCE_SOURCES
        ]
        if forbidden:
            raise StateError("resolved rights_lock rights_scope source must come from the user")

    for gate_id, gate in gates.items():
        for decision_id in gate["decision_ids"]:
            if decision_id not in decisions or decisions[decision_id]["gate"] != gate_id:
                raise StateError(f"gate {gate_id} references an unknown or mismatched decision")
        if gate["status"] in {"approved", "delivered"}:
            event_id = gate["approval_event_id"]
            if event_id not in events:
                raise StateError(f"gate {gate_id} references unknown approval event")
            event = events[event_id]
            if event["gate"] != gate_id or not approval_validity[event_id]["valid"]:
                raise StateError(f"gate {gate_id} approval event is incompatible or invalid")
            if gate_id in {"G0", "G1"}:
                if event["type"] not in {"user_confirmed", "delegated_decision"}:
                    raise StateError(f"gate {gate_id} requires user or delegated approval")
                if not set(gate["decision_ids"]) <= set(event["decision_ids"]):
                    raise StateError(f"gate {gate_id} approval omits current decisions")
            elif event["type"] != "system_validation":
                raise StateError("G2 delivered requires system_validation, not user confirmation")
    for artifact_id, item in artifacts.items():
        event_id = item["approval_event_id"]
        if event_id and (event_id not in events or not approval_validity[event_id]["valid"]):
            raise StateError(f"artifact {artifact_id} has an invalid approval reference")


    valid_artifacts = {
        record_id: item for record_id, item in artifacts.items() if artifact_validity[record_id]["valid"]
    }
    current_generated = {
        record_id: item for record_id, item in valid_artifacts.items()
        if item["kind"] in GENERATED_ARTIFACT_KINDS
        and item["lifecycle"] not in {"planned", "invalidated"}
    }
    if current_generated:
        if workflow == "atomic" or not generation_authorized or max_candidates < 1:
            raise StateError("generated artifact lacks standing authorization")
        candidate_sets = {item["candidate_set_id"] for item in current_generated.values()}
        if len(candidate_sets) > max_candidates:
            raise StateError(
                f"generated candidate sets exceed max_candidates: {len(candidate_sets)} > {max_candidates}"
            )
    else:
        candidate_sets = set()
    if status == "blocked" and current_generated:
        # Candidate assets are the evidence that resolves a controlled hard
        # fidelity gate. Permit only that pre-G1 evidence to coexist with the
        # fidelity-only block; every other generated artifact still fails closed.
        unresolved_hard = {
            name for name, item in risks.items()
            if item["level"] == "hard" and item["status"] != "resolved"
        }
        candidate_only = all(
            item["kind"] in {"candidate_asset", "asset_triad_preview", "fidelity_test"}
            for item in current_generated.values()
        )
        can_retain_fidelity_evidence = (
            workflow == "controlled"
            and gates["G0"]["status"] == "approved"
            and unresolved_hard == {"fidelity_lock"}
            and candidate_only
        )
        if not can_retain_fidelity_evidence:
            raise StateError("blocked project cannot retain a currently valid generation artifact")

    required_gate_decisions: dict[str, set[str]] = {}
    for gate_id in ("G0", "G1"):
        required_gate_decisions[gate_id] = {
            decision_id for decision_id in gates[gate_id]["decision_ids"]
            if decision_id in decisions and decision_validity[decision_id]["valid"]
        } if gates[gate_id]["required"] else set()
    required_g0 = required_gate_decisions["G0"]
    required_g1 = required_gate_decisions["G1"]
    g0_by_field = {decisions[item]["field"]: item for item in required_g0}
    display_contract: dict[str, Any] | None = None
    exact_text_values: dict[str, str] = {}
    typography_profile = "not_applicable"
    typography_decision_id = ""
    if is_v52:
        text_fields = set(g0_by_field).intersection(DISPLAY_TEXT_FIELDS)
        if text_fields and "display_semantics" not in g0_by_field:
            raise StateError("V5.2+ exact text requires a G0 display_semantics decision")
        if "display_semantics" in g0_by_field:
            display_id = g0_by_field["display_semantics"]
            display_contract = validate_display_semantics(decisions[display_id]["value"], require_v53=is_v53)
            exact_id = g0_by_field.get("exact_text")
            if any(item["text_mode"] == "exact" for item in display_contract["elements"].values()):
                if not exact_id:
                    raise StateError("display_semantics exact elements require a G0 exact_text decision")
                exact_text_values = validate_exact_text(decisions[exact_id]["value"], display_contract)
            elif exact_id:
                raise StateError("exact_text cannot exist when display_semantics has no exact elements")
            if is_v53:
                typography_decision_id = g0_by_field.get("typography_profile", "")
                if not typography_decision_id:
                    raise StateError("V5.3 display semantics require a G0 typography_profile decision")
                typography_profile = string_value(decisions[typography_decision_id]["value"], "typography_profile.value")
                if typography_profile not in TYPOGRAPHY_PROFILES:
                    raise StateError("typography_profile.value is invalid")
        elif is_v53 and "typography_profile" in g0_by_field:
            raise StateError("typography_profile requires display_semantics")
    g1_anchor_floor: set[str] = set()
    if workflow == "controlled":
        if len(required_g1) != 1:
            raise StateError("controlled G1 must bind exactly one current asset_board_spec decision")
        g1_decision_id = next(iter(required_g1))
        g1_decision = decisions[g1_decision_id]
        if g1_decision["field"] != "asset_board_spec":
            raise StateError("controlled G1 decision field must be asset_board_spec")
        spec = object_value(g1_decision["value"], "asset_board_spec.value")
        dependency_fields = list_value(
            require(spec, "dependency_fields", "asset_board_spec.value"),
            "asset_board_spec.value.dependency_fields",
        )
        excluded_g0_fields = list_value(
            require(spec, "excluded_g0_fields", "asset_board_spec.value"),
            "asset_board_spec.value.excluded_g0_fields",
        )
        if not all(isinstance(item, str) and item for item in dependency_fields + excluded_g0_fields):
            raise StateError("asset_board_spec field partition must contain non-empty field names")
        if len(set(dependency_fields)) != len(dependency_fields) or len(set(excluded_g0_fields)) != len(excluded_g0_fields):
            raise StateError("asset_board_spec field partition contains duplicates")
        included_fields = set(dependency_fields)
        excluded_fields = set(excluded_g0_fields)
        if included_fields & excluded_fields:
            raise StateError("asset_board_spec dependency_fields and excluded_g0_fields overlap")
        g0_by_field = {decisions[item]["field"]: item for item in required_g0}
        current_g0_fields = set(g0_by_field)
        if included_fields | excluded_fields != current_g0_fields:
            raise StateError("asset_board_spec must completely partition current G0 fields")
        unsafe_exclusions = {
            field for field in excluded_fields
            if not field_can_be_excluded_from_asset_board(field)
        }
        if unsafe_exclusions:
            raise StateError(
                f"asset_board_spec cannot exclude fidelity/rights/unknown G0 fields: {sorted(unsafe_exclusions)}"
            )
        included_ids = {g0_by_field[field] for field in included_fields}
        if set(g1_decision["depends_on"]) != included_ids:
            raise StateError(
                "asset_board_spec depends_on must exactly bind included current G0 decisions"
            )
        if set(g1_decision["dependency_fingerprints"]) != included_ids:
            raise StateError(
                "asset_board_spec dependency_fingerprints must bind included G0 decisions"
            )
        g1_anchor_floor = {g1_decision_id} | dependency_closure(decisions, included_ids)
        asset_coverage = validate_asset_coverage_spec(spec) if is_v51 else None
        if is_v51 and risks["fidelity_lock"]["level"] == "hard":
            if gates["G1"]["status"] != "approved" and risks["fidelity_lock"]["status"] == "resolved":
                raise StateError("hard fidelity_lock cannot resolve before approved G1 coverage")
            if gates["G1"]["status"] == "approved" and risks["fidelity_lock"]["status"] != "resolved":
                raise StateError("approved G1 coverage must resolve hard fidelity_lock")
    else:
        g1_decision_id = ""
        asset_coverage = None
    if workflow == "controlled":
        anchor_floor = g1_anchor_floor
    else:
        anchor_floor = required_g0
    non_text_g0 = {
        decision_id for decision_id in required_g0
        if decisions[decision_id]["field"] not in DISPLAY_TEXT_FIELDS
    }
    generated_dependency_floor = {
        "candidate_asset": anchor_floor,
        "asset_triad_preview": anchor_floor,
        "fidelity_test": anchor_floor,
        "asset_triad_release": anchor_floor,
        "lettering_base_image": non_text_g0 | required_g1,
        "formal_image": required_g0 | required_g1,
        "production_image": required_g0 | required_g1,
    }
    for artifact_id, artifact in current_generated.items():
        missing = generated_dependency_floor[artifact["kind"]] - set(artifact["depends_on"])
        if missing:
            raise StateError(
                f"generated artifact {artifact_id} lacks current required decision dependencies: {sorted(missing)}"
            )
        unsnapshotted = generated_dependency_floor[artifact["kind"]] - set(
            artifact["dependency_fingerprints"]
        )
        if unsnapshotted:
            raise StateError(
                f"generated artifact {artifact_id} lacks current decision fingerprint bindings: "
                f"{sorted(unsnapshotted)}"
            )

    g1_previews: set[str] = set()
    g1_fidelity_tests: set[str] = set()
    anchor_fingerprints: set[str] = set()
    if workflow == "controlled" and gates["G1"]["status"] == "approved":
        g1_event_id = gates["G1"]["approval_event_id"]
        g1_event = events[g1_event_id]
        if g1_event["type"] != "user_confirmed":
            raise StateError("controlled visual-anchor G1 requires user_confirmed")
        if g1_decision_id not in g1_event["decision_ids"]:
            raise StateError("controlled G1 approval must bind asset_board_spec")
        g1_fp = decisions[g1_decision_id]["fingerprint"]
        approved = {
            artifact_id: valid_artifacts[artifact_id]
            for artifact_id in g1_event["artifact_ids"] if artifact_id in valid_artifacts
        }
        g1_previews = {
            artifact_id for artifact_id, artifact in approved.items()
            if artifact["kind"] == "asset_triad_preview"
            and artifact["lifecycle"] == "approved"
            and artifact["decision_fingerprint"] == g1_fp
            and artifact["approval_event_id"] == g1_event_id
            and g1_decision_id in artifact["depends_on"]
        }
        if not g1_previews:
            raise StateError("G1 user confirmation must include the current asset_triad_preview")
        if risks["fidelity_lock"]["level"] != "none":
            g1_fidelity_tests = {
                artifact_id for artifact_id, artifact in approved.items()
                if artifact["kind"] == "fidelity_test"
                and artifact["lifecycle"] == "approved"
                and artifact["decision_fingerprint"] == g1_fp
                and artifact["approval_event_id"] == g1_event_id
                and g1_decision_id in artifact["depends_on"]
                and artifact.get("result") == "passed"
                and artifact.get("hard_failures") == []
            }
            if not g1_fidelity_tests:
                raise StateError("G1 user confirmation must include a passed applicable fidelity_test")
        anchor_fingerprints = {valid_artifacts[item]["decision_fingerprint"] for item in g1_previews}
        if g1_fidelity_tests:
            anchor_fingerprints &= {
                valid_artifacts[item]["decision_fingerprint"] for item in g1_fidelity_tests
            }
        if not anchor_fingerprints:
            raise StateError("G1 preview and fidelity test must share one current decision_fingerprint")

    if workflow == "controlled" and any(
        item["kind"] in {"candidate_asset", "asset_triad_preview", "fidelity_test"}
        for item in current_generated.values()
    ) and gates["G0"]["status"] != "approved":
        raise StateError("controlled candidate assets and pressure tests require approved G0")

    valid_releases: set[str] = set()
    if workflow == "controlled" and gates["G1"]["status"] == "approved":
        g1_event_id = gates["G1"]["approval_event_id"]
        g1_fp = decisions[g1_decision_id]["fingerprint"]
        for artifact_id, artifact in valid_artifacts.items():
            if artifact["kind"] != "asset_triad_release":
                continue
            matching_previews = {
                item for item in g1_previews
                if valid_artifacts[item]["decision_fingerprint"] == artifact["decision_fingerprint"]
            }
            matching_tests = {
                item for item in g1_fidelity_tests
                if valid_artifacts[item]["decision_fingerprint"] == artifact["decision_fingerprint"]
            }
            if artifact["lifecycle"] not in {"approved", "delivered"}:
                raise StateError(f"effective asset_triad_release {artifact_id} has invalid lifecycle")
            if artifact["approval_event_id"] != g1_event_id:
                raise StateError(f"effective asset_triad_release {artifact_id} has stale approval")
            if artifact["decision_fingerprint"] != g1_fp or g1_fp not in anchor_fingerprints:
                raise StateError(f"effective asset_triad_release {artifact_id} has stale decision_fingerprint")
            if g1_fp not in events[g1_event_id]["decision_fingerprints"]:
                raise StateError(f"effective asset_triad_release {artifact_id} is outside G1 approval")
            if g1_decision_id not in artifact["depends_on"]:
                raise StateError(f"effective asset_triad_release {artifact_id} lacks direct asset_board_spec dependency")
            if not matching_previews.intersection(artifact["depends_on"]):
                raise StateError(f"effective asset_triad_release {artifact_id} lacks preview dependency")
            if g1_fidelity_tests and not matching_tests.intersection(artifact["depends_on"]):
                raise StateError(f"effective asset_triad_release {artifact_id} lacks fidelity dependency")
            valid_releases.add(artifact_id)

    lettering_bases = {
        artifact_id: artifact for artifact_id, artifact in valid_artifacts.items()
        if artifact["kind"] == "lettering_base_image"
        and artifact["lifecycle"] not in {"planned", "invalidated"}
    }
    geometry_contracts = {
        artifact_id: artifact for artifact_id, artifact in valid_artifacts.items()
        if artifact["kind"] == ROLE_DELIVERABLE_KIND
        and artifact.get("deliverable_type") == "layout_geometry_contract"
        and artifact.get("role") == "art_director"
        and artifact["lifecycle"] not in {"planned", "invalidated"}
    }
    lettering_builds = {
        artifact_id: artifact for artifact_id, artifact in valid_artifacts.items()
        if artifact["kind"] == ROLE_DELIVERABLE_KIND
        and artifact.get("deliverable_type") == "lettering_build_report"
        and artifact.get("role") == "execution_scribe"
        and artifact["lifecycle"] not in {"planned", "invalidated"}
    }
    typography_contracts = {
        artifact_id: artifact for artifact_id, artifact in valid_artifacts.items()
        if artifact["kind"] == ROLE_DELIVERABLE_KIND
        and artifact.get("deliverable_type") == "typography_contract"
        and artifact.get("role") == "art_director"
        and artifact["lifecycle"] not in {"planned", "invalidated"}
    }
    lettering_fits = {
        artifact_id: artifact for artifact_id, artifact in valid_artifacts.items()
        if artifact["kind"] == "lettering_fit_report"
        and artifact["lifecycle"] not in {"planned", "invalidated"}
    }

    formal_artifacts = {
        record_id: item for record_id, item in valid_artifacts.items()
        if item["kind"] in FORMAL_ARTIFACT_KINDS
        and item["lifecycle"] not in {"planned", "invalidated"}
    }
    formal_slots: dict[tuple[str, str], str] = {}
    for artifact_id, artifact in formal_artifacts.items():
        slot_key = (artifact["deliverable_slot_id"], artifact["candidate_set_id"])
        if slot_key in formal_slots:
            raise StateError(
                f"duplicate effective formal image for deliverable slot/candidate set: {slot_key}"
            )
        formal_slots[slot_key] = artifact_id
    if formal_artifacts:
        if workflow == "atomic" or status == "blocked" or not generation_authorized or max_candidates < 1:
            raise StateError("formal image lacks a valid workflow or standing authorization")
        for gate_id in ("G0", "G1"):
            if gates[gate_id]["required"] and gates[gate_id]["status"] != "approved":
                raise StateError(f"formal image was created before required {gate_id} approval")
        for artifact_id, artifact in formal_artifacts.items():
            required = required_g0 | required_g1
            missing = required - set(artifact["depends_on"])
            if workflow in {"guided", "controlled"} and missing:
                raise StateError(
                    f"formal image {artifact_id} must directly depend on all current required G0/G1 decisions"
                )
        if workflow == "controlled":
            if not valid_releases:
                raise StateError("controlled fidelity/reuse formal image requires an effective asset_triad_release")
            for artifact_id, artifact in formal_artifacts.items():
                if not valid_releases.intersection(artifact["depends_on"]):
                    raise StateError(f"formal image {artifact_id} must depend on an effective asset_triad_release")

        if display_contract is not None:
            comic_contract_ids: set[str] = set()
            if typography_profile == "comic_display":
                comic_contract_ids = {
                    artifact_id for artifact_id, artifact in typography_contracts.items()
                    if typography_decision_id in artifact["depends_on"]
                    and artifact["dependency_fingerprints"].get(typography_decision_id) == decisions[typography_decision_id]["fingerprint"]
                }
                if not comic_contract_ids:
                    raise StateError("comic_display formal image requires an art-director typography_contract bound to G0")
            if not lettering_bases or not geometry_contracts or not lettering_builds or not lettering_fits:
                raise StateError("text-bearing formal image requires base, geometry, build and fit artifacts")
            for artifact_id, artifact in formal_artifacts.items():
                base_ids = set(artifact["depends_on"]).intersection(lettering_bases)
                geometry_ids = set(artifact["depends_on"]).intersection(geometry_contracts)
                build_ids = set(artifact["depends_on"]).intersection(lettering_builds)
                if not base_ids or not geometry_ids or not build_ids:
                    raise StateError(f"text-bearing formal image {artifact_id} lacks required lettering dependencies")
                if typography_profile == "comic_display":
                    if not comic_contract_ids.intersection(artifact["depends_on"]):
                        raise StateError(f"comic_display formal image {artifact_id} lacks typography_contract dependency")
                    for geometry_id in geometry_ids:
                        if not comic_contract_ids.intersection(geometry_contracts[geometry_id]["depends_on"]):
                            raise StateError(f"comic geometry {geometry_id} lacks typography_contract dependency")
                    for build_id in build_ids:
                        if not comic_contract_ids.intersection(lettering_builds[build_id]["depends_on"]):
                            raise StateError(f"comic lettering build {build_id} lacks typography_contract dependency")
                fit_ids = {
                    fit_id for fit_id, fit in lettering_fits.items()
                    if artifact_id in fit["depends_on"]
                    and set(fit["depends_on"]).intersection(geometry_ids)
                    and set(fit["depends_on"]).intersection(build_ids)
                }
                if not fit_ids:
                    raise StateError(f"text-bearing formal image {artifact_id} lacks a bound lettering_fit_report")
                if workflow == "controlled":
                    for base_id in base_ids:
                        if not valid_releases.intersection(lettering_bases[base_id]["depends_on"]):
                            raise StateError(f"lettering base {base_id} must depend on an effective asset_triad_release")

    if gates["G2"]["status"] == "delivered":
        g2_event = events[gates["G2"]["approval_event_id"]]
        referenced = {
            artifact_id: valid_artifacts[artifact_id]
            for artifact_id in g2_event["artifact_ids"] if artifact_id in valid_artifacts
        }
        unfinished = [
            artifact_id for artifact_id, item in referenced.items()
            if item["kind"] in FORMAL_ARTIFACT_KINDS | {"qa_report", "lettering_fit_report", "build_pack"}
            and item["lifecycle"] != "delivered"
        ]
        if unfinished:
            raise StateError(f"G2 system_validation references non-delivered artifacts: {unfinished}")
        formal_ids = {
            artifact_id for artifact_id, item in referenced.items()
            if item["kind"] in FORMAL_ARTIFACT_KINDS
        }
        if not formal_ids:
            raise StateError("G2 system_validation must reference a valid formal_image")
        formal_fingerprints = {referenced[item]["decision_fingerprint"] for item in formal_ids if referenced[item]["decision_fingerprint"]}
        if len(formal_fingerprints) > 1:
            raise StateError("G2 formal images must share one decision_fingerprint")
        qa_ids = {artifact_id for artifact_id, item in referenced.items() if item["kind"] == "qa_report"}
        if not qa_ids:
            raise StateError("G2 system_validation must reference a valid qa_report")
        fit_ids = {artifact_id for artifact_id, item in referenced.items() if item["kind"] == "lettering_fit_report"}
        if display_contract is not None and not fit_ids:
            raise StateError("text-bearing G2 must reference a valid lettering_fit_report")
        qa_coverage: set[str] = set()
        for qa_id in qa_ids:
            qa_report = referenced[qa_id]
            score = qa_report.get("qa_score", qa_report.get("score"))
            hard_failures = qa_report.get("hard_failures")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or score < 85:
                raise StateError("G2 qa_report score must be >= 85")
            if not isinstance(hard_failures, list) or hard_failures:
                raise StateError("G2 qa_report hard_failures must be an empty list")
            covered_formals = formal_ids.intersection(qa_report["depends_on"])
            if not covered_formals:
                raise StateError(f"G2 qa_report {qa_id} is not bound to a delivered formal image")
            if not covered_formals <= set(qa_report["dependency_fingerprints"]):
                raise StateError(f"G2 qa_report {qa_id} lacks formal artifact fingerprint bindings")
            if display_contract is not None:
                bound_fits = {
                    fit_id for fit_id in fit_ids
                    if fit_id in qa_report["depends_on"]
                    and fit_id in qa_report["dependency_fingerprints"]
                    and set(referenced[fit_id]["depends_on"]).intersection(covered_formals)
                }
                if not bound_fits:
                    raise StateError(f"G2 qa_report {qa_id} lacks lettering_fit_report coverage")
            qa_coverage.update(covered_formals)
            qa_fingerprint = qa_report["decision_fingerprint"]
            if qa_fingerprint and formal_fingerprints and qa_fingerprint not in formal_fingerprints:
                raise StateError(f"G2 qa_report {qa_id} has a mismatched decision_fingerprint")
        missing_qa_coverage = formal_ids - qa_coverage
        if missing_qa_coverage:
            raise StateError(f"G2 delivered formal images lack QA coverage: {sorted(missing_qa_coverage)}")
        build_pack_ids = {artifact_id for artifact_id, item in referenced.items() if item["kind"] == "build_pack"}
        if not build_pack_ids:
            raise StateError("G2 system_validation must reference a valid build_pack")
        for build_pack_id in build_pack_ids:
            build_pack = referenced[build_pack_id]
            dependencies = set(build_pack["depends_on"])
            required_artifacts = formal_ids | qa_ids | fit_ids
            if not required_artifacts <= dependencies:
                raise StateError(
                    f"G2 build_pack {build_pack_id} is not bound to all delivered formal images and QA reports"
                )
            if not required_artifacts <= set(build_pack["dependency_fingerprints"]):
                raise StateError(f"G2 build_pack {build_pack_id} lacks artifact fingerprint bindings")
            build_fingerprint = build_pack["decision_fingerprint"]
            if build_fingerprint and formal_fingerprints and build_fingerprint not in formal_fingerprints:
                raise StateError(f"G2 build_pack {build_pack_id} has a mismatched decision_fingerprint")

    required_pre = [gate_id for gate_id in ("G0", "G1") if gates[gate_id]["required"]]
    approved_pre = [gate_id for gate_id in required_pre if gates[gate_id]["status"] == "approved"]
    if require_release_ready:
        if not is_v52:
            raise StateError("production resume requires migration to project-state schema 5.2")
        if status == "blocked":
            raise StateError("project is blocked and is not release-ready")
        missing = [gate_id for gate_id in required_pre if gate_id not in approved_pre]
        if missing:
            raise StateError(f"project is not release-ready; pending gates: {missing}")

    if is_v51:
        completed_calls = [
            item for item in state["tool_calls"]
            if item.get("status") == "completed" and item.get("role") in ROLE_NAMES
        ]
        valid_role_deliverables = {
            (item.get("role"), item.get("deliverable_type"))
            for artifact_id, item in artifacts.items()
            if item["kind"] == ROLE_DELIVERABLE_KIND
            and artifact_validity[artifact_id]["valid"]
            and item["lifecycle"] not in {"planned", "invalidated"}
        }
        for tool_call in completed_calls:
            deliverable_type = string_value(
                require(tool_call, "deliverable_type", "completed tool_call"),
                "completed tool_call.deliverable_type",
            )
            if (tool_call["role"], deliverable_type) not in valid_role_deliverables:
                raise StateError("completed specialist tool_call lacks a current persisted role_deliverable")
    return {
        "valid": True,
        "schema_version": schema_version,
        "current_schema_version": SCHEMA_VERSION,
        "migration_required": not is_v52,
        "project_id": project_id,
        "state_revision": revision,
        "status": status,
        "current_internal_stage": internal_stage,
        "workflow_mode": workflow,
        "generation_route": route,
        "review_mode": review,
        "minimum_workflow": floor,
        "required_pre_generation_gates": required_pre,
        "approved_pre_generation_gates": approved_pre,
        "frontstage": frontstage,
        "asset_coverage": asset_coverage,
        "text_contract": {
            "active": display_contract is not None,
            "profile": display_contract["profile"] if display_contract else "not_applicable",
            "exact_text_count": len(exact_text_values),
            "typography_profile": typography_profile,
        },
        "candidate_set_count": len(candidate_sets),
        "checks": {
            "schema": True,
            "risk_floor": True,
            "gate_contract": True,
            "dependency_dag": True,
            "invalidation_closure": True,
            "idempotency": True,
            "approval_references": True,
            "artifact_snapshots": True,
            "standing_authorization": True,
        },
        "_state": state,
        "_decisions": decisions,
        "_artifacts": artifacts,
        "_events": events,
        "_decision_validity": decision_validity,
        "_artifact_validity": artifact_validity,
        "_approval_validity": approval_validity,
        "_gates": gates,
    }


def _resolve_artifact_path(state_root: Path, raw_value: str, artifact_id: str) -> Path:
    raw_path = Path(raw_value)
    candidate = raw_path if raw_path.is_absolute() else state_root / raw_path
    resolved = candidate.resolve(strict=False)
    root = state_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise StateError(f"artifact {artifact_id} file path escapes project root") from exc
    return resolved


def verify_artifact_files(report: dict[str, Any], state_path: Path) -> list[dict[str, Any]]:
    root = state_path.parent.resolve()
    verified: list[dict[str, str]] = []
    for artifact_id, artifact in report["_artifacts"].items():
        if not report["_artifact_validity"][artifact_id]["valid"]:
            continue
        if artifact["kind"] not in FILE_VERIFIED_KINDS:
            continue
        if artifact["lifecycle"] in {"planned", "invalidated"}:
            continue
        file_path = _resolve_artifact_path(root, artifact["file"], artifact_id)
        if not file_path.is_file():
            raise StateError(f"artifact {artifact_id} file is missing: {file_path}")
        try:
            fingerprint = hashlib.sha256(file_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise StateError(f"cannot read artifact {artifact_id}: {exc}") from exc
        if fingerprint != artifact["fingerprint"]:
            raise StateError(f"artifact {artifact_id} file SHA-256 does not match fingerprint")
        verified_item: dict[str, Any] = {
            "id": artifact_id,
            "file": str(file_path),
            "sha256": fingerprint,
        }
        if artifact["kind"] in FORMAL_ARTIFACT_KINDS:
            if Image is None:
                raise StateError("Pillow is required to verify formal image deliverables")
            try:
                with Image.open(file_path) as image:
                    image_format = image.format
                    width, height = image.size
                    image.verify()
            except (OSError, ValueError, UnidentifiedImageError) as exc:
                raise StateError(
                    f"formal artifact {artifact_id} is not a decodable image: {exc}"
                ) from exc
            if not image_format or width < 1 or height < 1:
                raise StateError(f"formal artifact {artifact_id} has invalid image metadata")
            verified_item.update(
                {"format": image_format, "width": width, "height": height}
            )
        verified.append(verified_item)
    if report["_gates"]["G2"]["status"] == "delivered":
        g2 = report["_events"][report["_gates"]["G2"]["approval_event_id"]]
        verified_ids = {item["id"] for item in verified}
        terminal = {
            artifact_id for artifact_id in g2["artifact_ids"]
            if report["_artifacts"][artifact_id]["kind"] in FORMAL_ARTIFACT_KINDS | {"qa_report", "lettering_fit_report", "build_pack"}
        }
        if not terminal <= verified_ids:
            raise StateError("G2 formal/QA/Build Pack files must all exist and match fingerprints")
    return verified


def verify_text_evidence(report: dict[str, Any], state_path: Path) -> list[dict[str, Any]]:
    text_contract = report.get("text_contract", {})
    if not text_contract.get("active") or report["_gates"]["G2"]["status"] != "delivered":
        return []
    root = state_path.parent.resolve()
    g2 = report["_events"][report["_gates"]["G2"]["approval_event_id"]]
    artifacts = report["_artifacts"]
    display_id = next(
        decision_id for decision_id, decision in report["_decisions"].items()
        if decision["field"] == "display_semantics" and report["_decision_validity"][decision_id]["valid"]
    )
    display = validate_display_semantics(report["_decisions"][display_id]["value"])
    expected_elements = set(display["elements"])
    comic_display = text_contract.get("typography_profile") == "comic_display"
    evidence: list[dict[str, Any]] = []
    fit_ids = [artifact_id for artifact_id in g2["artifact_ids"] if artifacts[artifact_id]["kind"] == "lettering_fit_report"]
    if not fit_ids:
        raise StateError("text-bearing G2 lacks a lettering_fit_report file")
    for fit_id in fit_ids:
        fit_path = _resolve_artifact_path(root, artifacts[fit_id]["file"], fit_id)
        try:
            payload = json.loads(fit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"cannot parse lettering_fit_report {fit_id}: {exc}") from exc
        if payload.get("passed") is not True:
            raise StateError(f"lettering_fit_report {fit_id} is not passed")
        failed = [item for item in payload.get("checks", []) if not isinstance(item, dict) or item.get("passed") is not True]
        if failed:
            raise StateError(f"lettering_fit_report {fit_id} contains failed element checks")
        evidence.append({"id": fit_id, "kind": "lettering_fit_report", "passed": True})
    qa_ids = [artifact_id for artifact_id in g2["artifact_ids"] if artifacts[artifact_id]["kind"] == "qa_report"]
    for qa_id in qa_ids:
        qa_path = _resolve_artifact_path(root, artifacts[qa_id]["file"], qa_id)
        try:
            payload = json.loads(qa_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"cannot parse qa_report {qa_id}: {exc}") from exc
        checks = payload.get("display_checks")
        if not isinstance(checks, list):
            raise StateError(f"qa_report {qa_id} lacks display_checks")
        observed: set[str] = set()
        for index, item in enumerate(checks):
            if not isinstance(item, dict):
                raise StateError(f"qa_report {qa_id} display_checks[{index}] must be an object")
            element_id = string_value(item.get("element_id"), f"qa_report {qa_id} display_checks[{index}].element_id")
            if element_id not in expected_elements or element_id in observed:
                raise StateError(f"qa_report {qa_id} has invalid or duplicate display evidence: {element_id}")
            observed.add(element_id)
            if item.get("result") != "passed":
                raise StateError(f"qa_report {qa_id} has a failed display check: {element_id}")
            crop = string_value(item.get("crop_file"), f"qa_report {qa_id} display_checks[{index}].crop_file")
            expected_sha = sha_value(item.get("crop_sha256"), f"qa_report {qa_id} display_checks[{index}].crop_sha256")
            crop_path = _resolve_artifact_path(root, crop, f"{qa_id}:{element_id}")
            if not crop_path.is_file() or hashlib.sha256(crop_path.read_bytes()).hexdigest() != expected_sha:
                raise StateError(f"qa_report {qa_id} has missing or stale crop evidence: {element_id}")
        if observed != expected_elements:
            raise StateError(f"qa_report {qa_id} display evidence does not cover the display contract")
        if comic_display:
            typography_checks = payload.get("typography_checks")
            if not isinstance(typography_checks, list):
                raise StateError(f"qa_report {qa_id} lacks comic typography evidence")
            typography_observed: set[str] = set()
            for index, item in enumerate(typography_checks):
                if not isinstance(item, dict):
                    raise StateError(f"qa_report {qa_id} typography_checks[{index}] must be an object")
                element_id = string_value(item.get("element_id"), f"qa_report {qa_id} typography_checks[{index}].element_id")
                if element_id not in expected_elements or element_id in typography_observed:
                    raise StateError(f"qa_report {qa_id} has invalid or duplicate comic typography evidence: {element_id}")
                typography_observed.add(element_id)
                if item.get("result") != "passed":
                    raise StateError(f"qa_report {qa_id} has a failed comic typography check: {element_id}")
            if typography_observed != expected_elements:
                raise StateError(f"qa_report {qa_id} comic typography evidence does not cover the display contract")
        evidence.append({"id": qa_id, "kind": "qa_report", "display_elements": sorted(observed)})
    return evidence

def load_and_validate_state(
    path: Path,
    *,
    expect_project_id: str | None = None,
    require_release_ready: bool = False,
) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise StateError(f"project state not found: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"cannot read project state: {exc}") from exc
    report = validate_state(
        state,
        expect_project_id=expect_project_id,
        require_release_ready=require_release_ready,
    )
    report["verified_artifact_files"] = verify_artifact_files(report, path)
    report["verified_text_evidence"] = verify_text_evidence(report, path)
    report["checks"]["artifact_files"] = True
    report["checks"]["text_evidence"] = True
    report["state_path"] = str(path)
    report["state_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return report


def validate_approval_reference(
    state_report: dict[str, Any],
    *,
    approval_event_id: str,
    decision_fingerprint: str,
    required_gate: str,
) -> dict[str, Any]:
    fingerprint = sha_value(decision_fingerprint, "decision_fingerprint")
    events = state_report["_events"]
    if approval_event_id not in events:
        raise StateError(f"unknown approval_event_id: {approval_event_id}")
    event = events[approval_event_id]
    gate = state_report["_gates"].get(required_gate)
    if gate is None or event["gate"] != required_gate:
        raise StateError(f"approval_event_id does not belong to {required_gate}")
    if gate["status"] != "approved" or gate["approval_event_id"] != approval_event_id:
        raise StateError(f"gate {required_gate} does not have this effective approval")
    if not state_report["_approval_validity"][approval_event_id]["valid"]:
        raise StateError(f"approval_event_id {approval_event_id} is not effectively valid")
    matching = [
        decision_id for decision_id in event["decision_ids"]
        if state_report["_decisions"][decision_id]["fingerprint"] == fingerprint
        and state_report["_decision_validity"][decision_id]["valid"]
    ]
    if not matching:
        raise StateError("approval event does not cover the current decision_fingerprint")
    return {"event": event, "matching_decision_ids": matching}


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


def main() -> int:
    args = parse_args()
    report = load_and_validate_state(
        args.state,
        expect_project_id=args.expect_project_id,
        require_release_ready=args.require_release_ready,
    )
    print(json.dumps(public_report(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StateError as exc:
        print(f"project-state validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
