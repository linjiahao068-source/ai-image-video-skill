#!/usr/bin/env python3
"""Contract tests for the hardened build-image-fast V5 state gate."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image
import validate_project_state as state_validator
from validate_project_state import (
    StateError,
    canonical_fingerprint,
    decision_record_fingerprint,
    load_and_validate_state,
    validate_state,
)


GENERATED_KINDS = {
    "candidate_asset", "asset_triad_preview", "fidelity_test", "asset_triad_release",
    "formal_image", "production_image",
}


def decision(
    record_id: str,
    gate: str,
    field: str,
    value: object,
    source: str = "user_input",
) -> dict:
    return {
        "id": record_id,
        "gate": gate,
        "field": field,
        "value": value,
        "fingerprint": canonical_fingerprint(value),
        "source": source,
        "depends_on": [],
        "dependency_fingerprints": {},
        "record_fingerprint": decision_record_fingerprint(
            record_id,
            gate,
            field,
            source,
            canonical_fingerprint(value),
            [],
            {},
        ),
    }


def bind_decision_dependencies(item: dict, dependencies: list[dict]) -> None:
    item["depends_on"] = [dependency["id"] for dependency in dependencies]
    item["dependency_fingerprints"] = {
        dependency["id"]: dependency["fingerprint"] for dependency in dependencies
    }
    item["record_fingerprint"] = decision_record_fingerprint(
        item["id"],
        item["gate"],
        item["field"],
        item["source"],
        item["fingerprint"],
        item["depends_on"],
        item["dependency_fingerprints"],
    )


def refresh_decision_record(item: dict) -> None:
    item["record_fingerprint"] = decision_record_fingerprint(
        item["id"],
        item["gate"],
        item["field"],
        item["source"],
        item["fingerprint"],
        item["depends_on"],
        item["dependency_fingerprints"],
    )


def artifact(
    record_id: str,
    kind: str,
    *,
    decision_fingerprint: str = "",
    depends_on: list[str] | None = None,
    dependency_fingerprints: dict[str, str] | None = None,
    approval_event_id: str = "",
    fingerprint: str = "a" * 64,
    lifecycle: str = "approved",
    candidate_set_id: str = "CAND-01",
    deliverable_slot_id: str = "page-01",
    **extra: object,
) -> dict:
    result = {
        "id": record_id,
        "kind": kind,
        "version": "v0.1",
        "file": f"{record_id}.json",
        "fingerprint": fingerprint,
        "decision_fingerprint": decision_fingerprint,
        "depends_on": depends_on or [],
        "dependency_fingerprints": dependency_fingerprints or {},
        "lifecycle": lifecycle,
        "approval_event_id": approval_event_id,
        **extra,
    }
    if kind in GENERATED_KINDS:
        result["candidate_set_id"] = candidate_set_id
    if kind in {"formal_image", "production_image"}:
        result["deliverable_slot_id"] = deliverable_slot_id
    return result


def base_shell() -> dict:
    return {
        "schema_version": "5.0",
        "project_id": "state-contract-test",
        "state_revision": 5,
        "status": "active",
        "current_internal_stage": 6,
        "workflow_mode": "controlled",
        "generation_route": "stable",
        "review_mode": "adaptive",
        "risk_modules": {},
        "gates": {},
        "team": {
            "execution_mode": "serial_roles",
            "client_window": "图片总编",
            "current_lead": "art_director",
            "team_intro_shown": True,
            "last_handoff_announced_version": "handoff-v0.1",
        },
        "standing_authorization": {
            "generate_one_candidate": True,
            "max_candidates": 1,
            "external_publish": False,
            "source": "user_request",
        },
        "delegation_scope": {
            "enabled": True,
            "allowed_fields": ["reversible_detail"],
            "excluded_fields": ["asset_board_spec", "rights_scope"],
            "authorized_by": "user",
            "source": "user_request",
        },
        "decisions": [],
        "artifacts": [],
        "confirmation_history": [],
        "effective_validity": {"decisions": {}, "artifacts": {}, "approval_events": {}},
        "assumptions": [],
        "tool_calls": [],
        "handoff_events": [],
        "blockers": [],
    }


def mark_valid(state: dict, section: str, record_id: str) -> None:
    state["effective_validity"][section][record_id] = {"valid": True, "reason": ""}


def fingerprints(records: list[dict], ids: list[str]) -> dict[str, str]:
    by_id = {item["id"]: item for item in records}
    return {record_id: by_id[record_id]["fingerprint"] for record_id in ids}


def controlled_state() -> dict:
    state = base_shell()
    g0 = decision("DEC-G0", "G0", "creative_contract", {"story": "locked"})
    rights = decision(
        "DEC-RIGHTS", "G0", "rights_scope", {"scope": "project generation only"}
    )
    exact_text = decision(
        "DEC-TEXT", "G0", "exact_text", {"title": "exact locked title"}
    )
    g1 = decision(
        "DEC-G1",
        "G1",
        "asset_board_spec",
        {
            "assets": "locked",
            "dependency_fields": ["creative_contract", "rights_scope"],
            "excluded_g0_fields": ["exact_text"],
        },
    )
    bind_decision_dependencies(g1, [g0, rights])
    decision_fps = {
        g0["id"]: g0["fingerprint"],
        rights["id"]: rights["fingerprint"],
        g1["id"]: g1["fingerprint"],
    }
    anchor_dependencies = [g0["id"], rights["id"], g1["id"]]
    preview = artifact(
        "ART-PREVIEW",
        "asset_triad_preview",
        decision_fingerprint=g1["fingerprint"],
        depends_on=anchor_dependencies,
        dependency_fingerprints=decision_fps,
        approval_event_id="CONF-G1",
        fingerprint="1" * 64,
    )
    fidelity = artifact(
        "ART-FIDELITY",
        "fidelity_test",
        decision_fingerprint=g1["fingerprint"],
        depends_on=anchor_dependencies,
        dependency_fingerprints=decision_fps,
        approval_event_id="CONF-G1",
        fingerprint="2" * 64,
        result="passed",
        hard_failures=[],
    )
    state["risk_modules"] = {
        "semantic_lock": {"level": "medium", "status": "resolved", "evidence": []},
        "fidelity_lock": {"level": "hard", "status": "resolved", "evidence": [g1["id"]]},
        "rights_lock": {"level": "hard", "status": "resolved", "evidence": [rights["id"]]},
        "layout_lock": {"level": "low", "status": "resolved", "evidence": []},
        "reuse_audit": {"level": "medium", "status": "resolved", "evidence": []},
    }
    state["gates"] = {
        "G0": {
            "required": True,
            "status": "approved",
            "decision_ids": [g0["id"], rights["id"], exact_text["id"]],
            "approval_event_id": "CONF-G0",
        },
        "G1": {
            "required": True,
            "status": "approved",
            "decision_ids": [g1["id"]],
            "approval_event_id": "CONF-G1",
        },
        "G2": {
            "required": True,
            "status": "pending",
            "decision_ids": [],
            "approval_event_id": "",
        },
    }
    # Keep G1 at index 1 for the shared assembler fixture.
    state["decisions"] = [g0, g1, rights, exact_text]
    state["artifacts"] = [preview, fidelity]
    state["confirmation_history"] = [
        {
            "id": "CONF-G0",
            "gate": "G0",
            "type": "user_confirmed",
            "actor": "user",
            "recorded_at": "2026-08-07T10:00:00+08:00",
            "expected_revision": 1,
            "decision_ids": [g0["id"], rights["id"], exact_text["id"]],
            "decision_fingerprints": [
                g0["fingerprint"], rights["fingerprint"], exact_text["fingerprint"]
            ],
            "decision_record_fingerprints": [
                g0["record_fingerprint"],
                rights["record_fingerprint"],
                exact_text["record_fingerprint"],
            ],
            "artifact_ids": [],
            "artifact_fingerprints": {},
        },
        {
            "id": "CONF-G1",
            "gate": "G1",
            "type": "user_confirmed",
            "actor": "user",
            "recorded_at": "2026-08-07T10:05:00+08:00",
            "expected_revision": 2,
            "decision_ids": [g1["id"]],
            "decision_fingerprints": [g1["fingerprint"]],
            "decision_record_fingerprints": [g1["record_fingerprint"]],
            "artifact_ids": [preview["id"], fidelity["id"]],
            "artifact_fingerprints": {
                preview["id"]: preview["fingerprint"],
                fidelity["id"]: fidelity["fingerprint"],
            },
        },
    ]
    for item in state["decisions"]:
        mark_valid(state, "decisions", item["id"])
    for item in state["artifacts"]:
        mark_valid(state, "artifacts", item["id"])
    mark_valid(state, "approval_events", "CONF-G0")
    mark_valid(state, "approval_events", "CONF-G1")
    return state


def direct_state() -> dict:
    state = base_shell()
    state["state_revision"] = 1
    state["current_internal_stage"] = 2
    state["workflow_mode"] = "direct"
    state["generation_route"] = "fast"
    state["risk_modules"] = {
        name: {
            "level": "low" if name == "layout_lock" else "none",
            "status": "resolved" if name == "layout_lock" else "not_applicable",
            "evidence": [],
        }
        for name in (
            "semantic_lock", "fidelity_lock", "rights_lock", "layout_lock", "reuse_audit"
        )
    }
    state["gates"] = {
        "G0": {"required": False, "status": "not_required", "decision_ids": [], "approval_event_id": ""},
        "G1": {"required": False, "status": "not_required", "decision_ids": [], "approval_event_id": ""},
        "G2": {"required": True, "status": "pending", "decision_ids": [], "approval_event_id": ""},
    }
    return state


def _entity_fingerprints(state: dict, ids: list[str]) -> dict[str, str]:
    records = {item["id"]: item for item in state["decisions"] + state["artifacts"]}
    return {record_id: records[record_id]["fingerprint"] for record_id in ids}


def add_release_and_formal(state: dict) -> tuple[dict, dict]:
    decisions = {item["id"]: item for item in state["decisions"]}
    g0_ids = state["gates"]["G0"]["decision_ids"]
    g1_id = state["gates"]["G1"]["decision_ids"][0]
    g1 = decisions[g1_id]
    anchor_ids = list(g1["depends_on"]) + [g1_id]
    release_deps = anchor_ids + ["ART-PREVIEW", "ART-FIDELITY"]
    release = artifact(
        "ART-RELEASE",
        "asset_triad_release",
        decision_fingerprint=g1["fingerprint"],
        depends_on=release_deps,
        dependency_fingerprints=_entity_fingerprints(state, release_deps),
        approval_event_id="CONF-G1",
        fingerprint="3" * 64,
    )
    state["artifacts"].append(release)
    formal_deps = g0_ids + [g1_id, release["id"]]
    formal = artifact(
        "ART-FORMAL",
        "formal_image",
        decision_fingerprint=g1["fingerprint"],
        depends_on=formal_deps,
        dependency_fingerprints=_entity_fingerprints(state, formal_deps),
        fingerprint="4" * 64,
        deliverable_slot_id="page-01",
    )
    state["artifacts"].append(formal)
    mark_valid(state, "artifacts", release["id"])
    mark_valid(state, "artifacts", formal["id"])
    return release, formal


def complete_state() -> dict:
    state = controlled_state()
    _, formal = add_release_and_formal(state)
    formal["lifecycle"] = "delivered"
    qa = artifact(
        "ART-QA",
        "qa_report",
        decision_fingerprint=formal["decision_fingerprint"],
        depends_on=[formal["id"]],
        dependency_fingerprints={formal["id"]: formal["fingerprint"]},
        fingerprint="5" * 64,
        lifecycle="delivered",
        qa_score=91,
        hard_failures=[],
    )
    pack = artifact(
        "ART-PACK",
        "build_pack",
        decision_fingerprint=formal["decision_fingerprint"],
        depends_on=[formal["id"], qa["id"]],
        dependency_fingerprints={
            formal["id"]: formal["fingerprint"],
            qa["id"]: qa["fingerprint"],
        },
        fingerprint="6" * 64,
        lifecycle="delivered",
    )
    state["artifacts"].extend([qa, pack])
    mark_valid(state, "artifacts", qa["id"])
    mark_valid(state, "artifacts", pack["id"])
    event = {
        "id": "CONF-G2",
        "gate": "G2",
        "type": "system_validation",
        "actor": "qa_system",
        "recorded_at": "2026-08-07T10:10:00+08:00",
        "expected_revision": 3,
        "decision_ids": [],
        "decision_fingerprints": [],
        "decision_record_fingerprints": [],
        "artifact_ids": [formal["id"], qa["id"], pack["id"]],
        "artifact_fingerprints": {
            formal["id"]: formal["fingerprint"],
            qa["id"]: qa["fingerprint"],
            pack["id"]: pack["fingerprint"],
        },
    }
    state["confirmation_history"].append(event)
    mark_valid(state, "approval_events", event["id"])
    state["gates"]["G2"].update(status="delivered", approval_event_id=event["id"])
    state["status"] = "completed"
    state["current_internal_stage"] = 8
    return state


def sync_g1_change(state: dict, *, update_event_record: bool = True) -> None:
    decisions = {item["id"]: item for item in state["decisions"]}
    g1 = decisions[state["gates"]["G1"]["decision_ids"][0]]
    anchor_ids = list(g1["depends_on"]) + [g1["id"]]
    anchor_fps = {record_id: decisions[record_id]["fingerprint"] for record_id in anchor_ids}
    for item in state["artifacts"]:
        if item["kind"] in {"asset_triad_preview", "fidelity_test"}:
            item["decision_fingerprint"] = g1["fingerprint"]
            item["depends_on"] = list(anchor_ids)
            item["dependency_fingerprints"] = dict(anchor_fps)
    event = next(
        item for item in state["confirmation_history"] if item["id"] == "CONF-G1"
    )
    event["decision_fingerprints"] = [g1["fingerprint"]]
    if update_event_record:
        event["decision_record_fingerprints"] = [g1["record_fingerprint"]]


def refresh_fingerprint_bindings(state: dict) -> None:
    entities = {item["id"]: item for item in state["decisions"] + state["artifacts"]}
    for item in state["decisions"]:
        if "dependency_fingerprints" in item:
            item["dependency_fingerprints"] = {
                record_id: entities[record_id]["fingerprint"]
                for record_id in item["dependency_fingerprints"]
            }
            refresh_decision_record(item)
    for item in state["artifacts"]:
        if "dependency_fingerprints" in item:
            item["dependency_fingerprints"] = {
                record_id: entities[record_id]["fingerprint"]
                for record_id in item["dependency_fingerprints"]
            }
    for event in state["confirmation_history"]:
        event["decision_fingerprints"] = [
            entities[record_id]["fingerprint"] for record_id in event["decision_ids"]
        ]
        event["decision_record_fingerprints"] = [
            entities[record_id]["record_fingerprint"] for record_id in event["decision_ids"]
        ]
        event["artifact_fingerprints"] = {
            record_id: entities[record_id]["fingerprint"] for record_id in event["artifact_ids"]
        }


def materialize_state(project_root: Path, state: dict) -> Path:
    for item in state["artifacts"]:
        if item["kind"] in {"formal_image", "production_image"}:
            path = project_root / f"{item['id']}.png"
            Image.new("RGB", (32, 24), (40, 90, 180)).save(path, format="PNG")
            data = path.read_bytes()
        else:
            path = project_root / f"{item['id']}.bin"
            data = f"physical artifact {item['id']}".encode("utf-8")
            path.write_bytes(data)
        item["file"] = path.name
        item["fingerprint"] = hashlib.sha256(data).hexdigest()
    refresh_fingerprint_bindings(state)
    state_path = project_root / "project-state.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state_path



class ProjectStateTests(unittest.TestCase):
    def assert_invalid(self, state: dict, text: str) -> None:
        with self.assertRaisesRegex(StateError, text):
            validate_state(state)

    def test_controlled_state_and_low_risk_direct_are_valid(self) -> None:
        report = validate_state(controlled_state())
        self.assertEqual(report["candidate_set_count"], 1)
        self.assertEqual(validate_state(direct_state())["minimum_workflow"], "direct")

    def test_edit_medium_requires_current_edit_contract(self) -> None:
        state = direct_state()
        state["workflow_mode"] = "edit"
        state["generation_route"] = "edit"
        state["risk_modules"]["semantic_lock"] = {"level": "medium", "status": "resolved", "evidence": []}
        self.assert_invalid(state, "edit_contract")
        edit = decision("DEC-EDIT", "internal", "edit_contract", {"change": "background only"}, source="agent_decision")
        state["decisions"].append(edit)
        mark_valid(state, "decisions", edit["id"])
        self.assertTrue(validate_state(state)["valid"])

    def test_agent_sources_remain_valid_for_non_rights_decisions(self) -> None:
        state = direct_state()
        for index, source in enumerate(("agent_decision", "assumption"), 1):
            item = decision(f"DEC-{index}", "internal", f"field-{index}", index, source=source)
            state["decisions"].append(item)
            mark_valid(state, "decisions", item["id"])
        state["assumptions"] = [{"id": "ASM-1"}]
        self.assertTrue(validate_state(state)["valid"])

    def test_confirmation_artifact_snapshot_blocks_replacement(self) -> None:
        state = controlled_state()
        state["artifacts"][0]["fingerprint"] = "f" * 64
        self.assert_invalid(state, "artifact fingerprint is stale")

        missing = controlled_state()
        missing["confirmation_history"][1].pop("artifact_fingerprints")
        self.assert_invalid(missing, "missing required field: artifact_fingerprints")

        incomplete = controlled_state()
        incomplete["confirmation_history"][1]["artifact_fingerprints"].pop("ART-FIDELITY")
        self.assert_invalid(incomplete, "must exactly cover artifact_ids")

    def test_confirmation_actor_is_bound_to_event_type(self) -> None:
        user = controlled_state()
        user["confirmation_history"][0]["actor"] = "image_editor"
        self.assert_invalid(user, "user_confirmed actor must be user")

        system = complete_state()
        system["confirmation_history"][-1]["actor"] = "user"
        self.assert_invalid(system, "system_validation actor must be qa_system or system")

    def test_resolved_rights_requires_current_user_rights_scope(self) -> None:
        wrong_field = controlled_state()
        rights = next(item for item in wrong_field["decisions"] if item["id"] == "DEC-RIGHTS")
        rights["field"] = "creative_contract_rights_note"
        refresh_decision_record(rights)
        event = wrong_field["confirmation_history"][0]
        index = event["decision_ids"].index(rights["id"])
        event["decision_record_fingerprints"][index] = rights["record_fingerprint"]
        self.assert_invalid(wrong_field, "requires a current rights_scope")

        for source in (
            "delegated_decision", "agent_recommendation", "agent_decision", "assumption", "system"
        ):
            state = controlled_state()
            rights = next(item for item in state["decisions"] if item["id"] == "DEC-RIGHTS")
            rights["source"] = source
            refresh_decision_record(rights)
            event = state["confirmation_history"][0]
            index = event["decision_ids"].index(rights["id"])
            event["decision_record_fingerprints"][index] = rights["record_fingerprint"]
            self.assert_invalid(state, "rights_scope source must come from the user")

        stale = controlled_state()
        stale["effective_validity"]["decisions"]["DEC-RIGHTS"] = {"valid": False, "reason": "superseded"}
        self.assert_invalid(stale, "invalid current records|invalid evidence|invalidation closure")

    def test_controlled_g1_is_user_confirmed_asset_board_spec(self) -> None:
        delegated = controlled_state()
        delegated["confirmation_history"][1]["type"] = "delegated_decision"
        delegated["delegation_scope"] = {
            "enabled": True,
            "allowed_fields": ["asset_board_spec"],
            "excluded_fields": ["rights_scope"],
            "authorized_by": "user",
            "source": "user_request",
        }
        self.assert_invalid(delegated, "requires user_confirmed")

        wrong_field = controlled_state()
        wrong_field["decisions"][1]["field"] = "visual_anchor"
        refresh_decision_record(wrong_field["decisions"][1])
        wrong_field["confirmation_history"][1]["decision_record_fingerprints"] = [
            wrong_field["decisions"][1]["record_fingerprint"]
        ]
        self.assert_invalid(wrong_field, "field must be asset_board_spec")

        indirect = controlled_state()
        indirect["artifacts"][0]["depends_on"].remove("DEC-G1")
        indirect["artifacts"][0]["dependency_fingerprints"].pop("DEC-G1")
        self.assert_invalid(indirect, "required decision dependencies|asset_triad_preview")

    def test_g1_requires_preview_passed_fidelity_and_snapshot(self) -> None:
        empty = controlled_state()
        empty["confirmation_history"][1]["artifact_ids"] = []
        empty["confirmation_history"][1]["artifact_fingerprints"] = {}
        self.assert_invalid(empty, "asset_triad_preview")

        failed = controlled_state()
        failed["artifacts"][1]["result"] = "failed"
        failed["artifacts"][1]["hard_failures"] = ["identity drift"]
        self.assert_invalid(failed, "passed applicable fidelity_test")

    def test_standing_authorization_covers_all_generation_and_candidate_sets(self) -> None:
        state = controlled_state()
        state["standing_authorization"]["generate_one_candidate"] = False
        self.assert_invalid(state, "standing authorization")

        state = controlled_state()
        g1 = state["decisions"][1]
        deps = list(g1["depends_on"]) + [g1["id"]]
        second = artifact(
            "ART-CANDIDATE-B", "candidate_asset", candidate_set_id="CAND-02",
            depends_on=deps, dependency_fingerprints=_entity_fingerprints(state, deps),
        )
        state["artifacts"].append(second)
        mark_valid(state, "artifacts", second["id"])
        self.assert_invalid(state, "exceed max_candidates")

        same_set = controlled_state()
        g1 = same_set["decisions"][1]
        deps = list(g1["depends_on"]) + [g1["id"]]
        for suffix in ("A", "B"):
            item = artifact(
                f"ART-CAND-{suffix}", "candidate_asset", candidate_set_id="CAND-01",
                depends_on=deps, dependency_fingerprints=_entity_fingerprints(same_set, deps),
            )
            same_set["artifacts"].append(item)
            mark_valid(same_set, "artifacts", item["id"])
        self.assertEqual(validate_state(same_set)["candidate_set_count"], 1)

        release_formal = controlled_state()
        add_release_and_formal(release_formal)
        release_formal["standing_authorization"]["generate_one_candidate"] = False
        self.assert_invalid(release_formal, "standing authorization")

    def test_generated_artifacts_snapshot_required_decisions(self) -> None:
        state = controlled_state()
        state["artifacts"][0]["dependency_fingerprints"].pop("DEC-G0")
        self.assert_invalid(state, "snapshot every dependency edge|decision fingerprint bindings")

        stale = controlled_state()
        creative = stale["decisions"][0]
        creative["value"] = {"story": "changed copy"}
        creative["fingerprint"] = canonical_fingerprint(creative["value"])
        refresh_decision_record(creative)
        stale["confirmation_history"][0]["decision_fingerprints"][0] = creative["fingerprint"]
        stale["confirmation_history"][0]["decision_record_fingerprints"][0] = creative["record_fingerprint"]
        self.assert_invalid(stale, "stale dependency fingerprint")

    def test_release_and_formal_have_direct_decision_dependencies(self) -> None:
        state = controlled_state()
        release, formal = add_release_and_formal(state)
        self.assertTrue(validate_state(state)["valid"])

        release["depends_on"].remove("DEC-G1")
        release["dependency_fingerprints"].pop("DEC-G1")
        self.assert_invalid(state, "required decision dependencies|asset_board_spec")

        state = controlled_state()
        _, formal = add_release_and_formal(state)
        formal["depends_on"].remove("DEC-G0")
        formal["dependency_fingerprints"].pop("DEC-G0")
        self.assert_invalid(state, "required decision dependencies|all current required")

    def test_release_requires_preview_fidelity_and_effective_g1(self) -> None:
        state = controlled_state()
        release, _ = add_release_and_formal(state)
        release["depends_on"].remove("ART-PREVIEW")
        release["dependency_fingerprints"].pop("ART-PREVIEW")
        self.assert_invalid(state, "lacks preview dependency")

        state = controlled_state()
        release, _ = add_release_and_formal(state)
        release["approval_event_id"] = ""
        self.assert_invalid(state, "stale approval")

    def test_g2_requires_snapshots_qa_and_pack_bindings(self) -> None:
        self.assertTrue(validate_state(complete_state())["valid"])

        event_stale = complete_state()
        event_stale["confirmation_history"][-1]["artifact_fingerprints"]["ART-FORMAL"] = "f" * 64
        self.assert_invalid(event_stale, "artifact fingerprint is stale")

        qa_unbound = complete_state()
        qa = next(item for item in qa_unbound["artifacts"] if item["id"] == "ART-QA")
        qa["dependency_fingerprints"] = {}
        self.assert_invalid(
            qa_unbound, "snapshot every dependency edge|lacks formal artifact fingerprint bindings"
        )

        pack_unbound = complete_state()
        pack = next(item for item in pack_unbound["artifacts"] if item["id"] == "ART-PACK")
        pack["dependency_fingerprints"].pop("ART-QA")
        self.assert_invalid(
            pack_unbound, "snapshot every dependency edge|lacks artifact fingerprint bindings"
        )

        hard = complete_state()
        next(item for item in hard["artifacts"] if item["id"] == "ART-QA")["hard_failures"] = ["text mismatch"]
        self.assert_invalid(hard, "hard_failures")

        low = complete_state()
        next(item for item in low["artifacts"] if item["id"] == "ART-QA")["qa_score"] = 84
        self.assert_invalid(low, "score must be >= 85")

    def test_authorization_and_delegation_must_come_from_user(self) -> None:
        for source in ("agent_decision", "assumption", "system"):
            state = direct_state()
            state["standing_authorization"]["source"] = source
            self.assert_invalid(state, "user authorization source")

        state = controlled_state()
        state["confirmation_history"][0]["type"] = "delegated_decision"
        state["confirmation_history"][0]["actor"] = "image_editor"
        self.assert_invalid(state, "delegated_decision actor must be user")

        state = direct_state()
        state["delegation_scope"]["authorized_by"] = "agent"
        self.assert_invalid(state, "explicit user authorization")

        state = direct_state()
        state["delegation_scope"]["excluded_fields"].remove("rights_scope")
        self.assert_invalid(state, "always exclude rights_scope")

    def test_formal_slot_and_candidate_set_pair_is_unique(self) -> None:
        state = controlled_state()
        _, formal = add_release_and_formal(state)
        duplicate = copy.deepcopy(formal)
        duplicate["id"] = "ART-FORMAL-DUP"
        duplicate["file"] = "ART-FORMAL-DUP.png"
        state["artifacts"].append(duplicate)
        mark_valid(state, "artifacts", duplicate["id"])
        self.assert_invalid(state, "duplicate effective formal image")

        state = controlled_state()
        _, formal = add_release_and_formal(state)
        page_two = copy.deepcopy(formal)
        page_two["id"] = "ART-FORMAL-PAGE-02"
        page_two["file"] = "ART-FORMAL-PAGE-02.png"
        page_two["deliverable_slot_id"] = "page-02"
        state["artifacts"].append(page_two)
        mark_valid(state, "artifacts", page_two["id"])
        self.assertTrue(validate_state(state)["valid"])

        missing_slot = controlled_state()
        _, formal = add_release_and_formal(missing_slot)
        formal.pop("deliverable_slot_id")
        self.assert_invalid(missing_slot, "requires deliverable_slot_id")

    def test_decision_record_fingerprint_binds_confirmed_metadata(self) -> None:
        for attribute, replacement in (
            ("field", "visual_anchor"),
            ("source", "agent_decision"),
            ("gate", "G0"),
        ):
            with self.subTest(attribute=attribute):
                state = controlled_state()
                g1 = state["decisions"][1]
                g1[attribute] = replacement
                refresh_decision_record(g1)
                self.assert_invalid(state, "record_fingerprint is stale")

        renamed = controlled_state()
        g1 = renamed["decisions"][1]
        old_id = g1["id"]
        new_id = "DEC-G1-RENAMED"
        g1["id"] = new_id
        refresh_decision_record(g1)
        renamed["gates"]["G1"]["decision_ids"] = [new_id]
        renamed["risk_modules"]["fidelity_lock"]["evidence"] = [new_id]
        renamed["effective_validity"]["decisions"][new_id] = (
            renamed["effective_validity"]["decisions"].pop(old_id)
        )
        for artifact_item in renamed["artifacts"]:
            artifact_item["depends_on"] = [
                new_id if record_id == old_id else record_id
                for record_id in artifact_item["depends_on"]
            ]
            artifact_item["dependency_fingerprints"] = {
                new_id if record_id == old_id else record_id: fingerprint
                for record_id, fingerprint in artifact_item["dependency_fingerprints"].items()
            }
        renamed["confirmation_history"][1]["decision_ids"] = [new_id]
        self.assert_invalid(renamed, "record_fingerprint is stale")

    def test_asset_board_exclusion_uses_explicit_text_only_allowlist(self) -> None:
        for unsafe_field in ("copy_character_identity", "character_copy"):
            with self.subTest(field=unsafe_field):
                state = controlled_state()
                text_decision = next(
                    item for item in state["decisions"] if item["id"] == "DEC-TEXT"
                )
                text_decision["field"] = unsafe_field
                refresh_decision_record(text_decision)
                g0_event = state["confirmation_history"][0]
                text_index = g0_event["decision_ids"].index(text_decision["id"])
                g0_event["decision_record_fingerprints"][text_index] = (
                    text_decision["record_fingerprint"]
                )

                g1 = state["decisions"][1]
                g1["value"]["excluded_g0_fields"] = [unsafe_field]
                g1["fingerprint"] = canonical_fingerprint(g1["value"])
                refresh_decision_record(g1)
                sync_g1_change(state)
                self.assert_invalid(state, "cannot exclude")

    def test_asset_board_partition_and_record_snapshot_fail_closed(self) -> None:
        missing_partition = controlled_state()
        missing_partition["decisions"][1]["value"].pop("excluded_g0_fields")
        missing_partition["decisions"][1]["fingerprint"] = canonical_fingerprint(
            missing_partition["decisions"][1]["value"]
        )
        refresh_decision_record(missing_partition["decisions"][1])
        sync_g1_change(missing_partition)
        self.assert_invalid(missing_partition, "excluded_g0_fields")

        unsafe = controlled_state()
        g1 = unsafe["decisions"][1]
        g1["value"]["dependency_fields"].remove("rights_scope")
        g1["value"]["excluded_g0_fields"].append("rights_scope")
        g1["fingerprint"] = canonical_fingerprint(g1["value"])
        bind_decision_dependencies(g1, [unsafe["decisions"][0]])
        sync_g1_change(unsafe)
        self.assert_invalid(unsafe, "cannot exclude")

        changed_edge = controlled_state()
        g1 = changed_edge["decisions"][1]
        g1["value"]["dependency_fields"].remove("creative_contract")
        g1["value"]["excluded_g0_fields"].append("creative_contract")
        g1["fingerprint"] = canonical_fingerprint(g1["value"])
        bind_decision_dependencies(g1, [changed_edge["decisions"][2]])
        sync_g1_change(changed_edge, update_event_record=False)
        self.assert_invalid(changed_edge, "record_fingerprint is stale")

    def test_exact_text_change_preserves_g1_and_release_but_not_formal(self) -> None:
        state = controlled_state()
        release, formal = add_release_and_formal(state)
        text_qa_deps = [formal["id"], "DEC-TEXT"]
        text_qa = artifact(
            "ART-TEXT-QA",
            "qa_report",
            decision_fingerprint=formal["decision_fingerprint"],
            depends_on=text_qa_deps,
            dependency_fingerprints=_entity_fingerprints(state, text_qa_deps),
            fingerprint="7" * 64,
        )
        state["artifacts"].append(text_qa)
        mark_valid(state, "artifacts", text_qa["id"])
        text_decision = next(item for item in state["decisions"] if item["id"] == "DEC-TEXT")
        text_decision["value"] = {"title": "new exact locked title"}
        text_decision["fingerprint"] = canonical_fingerprint(text_decision["value"])
        refresh_decision_record(text_decision)
        g0_event = state["confirmation_history"][0]
        text_index = g0_event["decision_ids"].index("DEC-TEXT")
        g0_event["decision_fingerprints"][text_index] = text_decision["fingerprint"]
        g0_event["decision_record_fingerprints"][text_index] = text_decision["record_fingerprint"]

        state["effective_validity"]["artifacts"][formal["id"]] = {
            "valid": False,
            "reason": "exact text changed; formal must regenerate",
        }
        state["effective_validity"]["artifacts"][text_qa["id"]] = {
            "valid": False,
            "reason": "exact text changed; text QA must rerun",
        }
        self.assertTrue(validate_state(state)["valid"])
        self.assertTrue(state["effective_validity"]["artifacts"][release["id"]]["valid"])
        self.assertFalse(state["effective_validity"]["artifacts"][formal["id"]]["valid"])
        self.assertFalse(state["effective_validity"]["artifacts"][text_qa["id"]]["valid"])

        stale_formal = controlled_state()
        add_release_and_formal(stale_formal)
        text_decision = next(
            item for item in stale_formal["decisions"] if item["id"] == "DEC-TEXT"
        )
        text_decision["value"] = {"title": "new exact locked title"}
        text_decision["fingerprint"] = canonical_fingerprint(text_decision["value"])
        refresh_decision_record(text_decision)
        event = stale_formal["confirmation_history"][0]
        index = event["decision_ids"].index("DEC-TEXT")
        event["decision_fingerprints"][index] = text_decision["fingerprint"]
        event["decision_record_fingerprints"][index] = text_decision["record_fingerprint"]
        self.assert_invalid(stale_formal, "stale dependency fingerprint")

    def test_included_character_or_rights_change_invalidates_old_g1(self) -> None:
        state = controlled_state()
        creative = state["decisions"][0]
        creative["value"] = {"story": "changed character role"}
        creative["fingerprint"] = canonical_fingerprint(creative["value"])
        refresh_decision_record(creative)
        event = state["confirmation_history"][0]
        event["decision_fingerprints"][0] = creative["fingerprint"]
        event["decision_record_fingerprints"][0] = creative["record_fingerprint"]
        self.assert_invalid(state, "stale dependency fingerprint")

    def test_load_rejects_fake_formal_bytes_and_missing_pillow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v5-state-image-gate-") as temp:
            project = Path(temp)
            state = complete_state()
            path = materialize_state(project, state)
            formal = next(item for item in state["artifacts"] if item["id"] == "ART-FORMAL")
            fake = project / "fake-formal.bin"
            fake.write_bytes(b"not an image")
            formal["file"] = fake.name
            formal["fingerprint"] = hashlib.sha256(fake.read_bytes()).hexdigest()
            refresh_fingerprint_bindings(state)
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "not a decodable image"):
                load_and_validate_state(path)

            valid = complete_state()
            valid_path = materialize_state(project, valid)
            with mock.patch.object(state_validator, "Image", None):
                with self.assertRaisesRegex(StateError, "Pillow is required"):
                    load_and_validate_state(valid_path)

    def test_fidelity_only_block_can_retain_candidate_evidence(self) -> None:
        state = controlled_state()
        state["status"] = "blocked"
        state["blockers"] = ["fidelity candidate pending"]
        g1_id = state["gates"]["G1"]["decision_ids"][0]
        state["risk_modules"]["fidelity_lock"] = {
            "level": "hard", "status": "unresolved", "evidence": [g1_id]
        }
        state["gates"]["G1"].update(status="pending", approval_event_id="")
        state["confirmation_history"] = state["confirmation_history"][:1]
        state["effective_validity"]["approval_events"].pop("CONF-G1")
        for item in state["artifacts"]:
            if item["kind"] in {"asset_triad_preview", "fidelity_test"}:
                item["lifecycle"] = "candidate"
                item["approval_event_id"] = ""
        self.assertTrue(validate_state(state)["valid"])

    def test_blocked_state_cannot_retain_generated_artifacts(self) -> None:
        state = controlled_state()
        state["status"] = "blocked"
        state["blockers"] = ["rights unresolved"]
        state["risk_modules"]["rights_lock"] = {"level": "hard", "status": "unresolved", "evidence": []}
        self.assert_invalid(state, "blocked project cannot retain")

    def test_completed_and_g2_delivered_are_bidirectionally_bound(self) -> None:
        state = controlled_state()
        state["status"] = "completed"
        self.assert_invalid(state, "if and only if G2 is delivered")

        state = complete_state()
        state["status"] = "active"
        self.assert_invalid(state, "if and only if G2 is delivered")

    def test_unknown_dependency_and_stage_bounds_fail_closed(self) -> None:
        state = controlled_state()
        state["artifacts"][0]["depends_on"] = ["UNKNOWN"]
        state["artifacts"][0]["dependency_fingerprints"] = {}
        self.assert_invalid(state, "unknown dependencies")

        low = direct_state()
        low["current_internal_stage"] = 0
        self.assert_invalid(low, "current_internal_stage")

        high = direct_state()
        high["current_internal_stage"] = 9
        self.assert_invalid(high, "current_internal_stage")

    def test_load_verifies_real_files_paths_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v5-state-file-gate-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            state = complete_state()
            path = materialize_state(project, state)
            report = load_and_validate_state(path)
            self.assertEqual(len(report["verified_artifact_files"]), len(state["artifacts"]))
            formal_info = next(
                item for item in report["verified_artifact_files"] if item["id"] == "ART-FORMAL"
            )
            self.assertEqual(
                (formal_info["format"], formal_info["width"], formal_info["height"]),
                ("PNG", 32, 24),
            )
            self.assertTrue(report["checks"]["artifact_files"])

            missing_state = complete_state()
            missing_path = materialize_state(project, missing_state)
            (project / "ART-FORMAL.png").unlink()
            with self.assertRaisesRegex(StateError, "ART-FORMAL file is missing"):
                load_and_validate_state(missing_path)

    def test_load_rejects_path_escape_and_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v5-state-path-gate-") as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            state = complete_state()
            path = materialize_state(project, state)
            formal = next(item for item in state["artifacts"] if item["id"] == "ART-FORMAL")
            outside = root / "escape.bin"
            outside.write_bytes(b"escape")
            formal["file"] = "../escape.bin"
            formal["fingerprint"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            refresh_fingerprint_bindings(state)
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "escapes project root"):
                load_and_validate_state(path)

            clean = complete_state()
            clean_path = materialize_state(project, clean)
            (project / "ART-FORMAL.png").write_bytes(b"tampered after state commit")
            with self.assertRaisesRegex(StateError, "SHA-256 does not match"):
                load_and_validate_state(clean_path)


    # V5.4 tests remain in ProjectStateTests; module entry point follows the class.
    # Keep this comment indented so the following test method remains part of the class.
    def test_v54_requires_generation_request_and_final_acceptance_archive(self) -> None:
        state = v54_direct_delivery_state()
        state["schema_version"] = "5.4"
        state["status"] = "delivered_pending_acceptance"
        state["frontstage"] = {
            "current_stage": "delivery", "completed_this_round": "automatic G2 passed",
            "pending_user_decision": "final acceptance", "next_action": "wait for client",
            "after_confirmation": "create handoff archive", "remaining_confirmations": 0,
        }
        state["production_profile"] = {
            "profile": "balanced",
            "selected_by": "agent_recommendation",
            "recommended_agent_model": "gpt-5.6-terra",
            "recommended_reasoning_effort": "medium",
            "recommended_generation_route": "stable",
            "active_agent_model": "",
            "active_reasoning_effort": "",
            "active_runtime_verified": False,
        }
        state["client_acceptance"] = {
            "status": "pending", "event_id": "", "handoff_archive_artifact_id": "",
        }
        formal = next(item for item in state["artifacts"] if item["id"] == "ART-FORMAL")
        request_dependencies = [record_id for record_id in formal["depends_on"] if record_id.startswith("DEC-")]
        request = artifact(
            "ART-REQUEST", "role_deliverable", decision_fingerprint=formal["decision_fingerprint"],
            depends_on=request_dependencies,
            dependency_fingerprints=_entity_fingerprints(state, request_dependencies),
            fingerprint="7" * 64, role="execution_scribe", deliverable_type="generation_request",
            self_check={"result": "pass", "summary": "exact prompt payload recorded"},
        )
        state["artifacts"].append(request)
        mark_valid(state, "artifacts", request["id"])
        formal["depends_on"].append(request["id"])
        formal["dependency_fingerprints"][request["id"]] = request["fingerprint"]
        self.assertTrue(validate_state(state)["valid"])

        unbound = copy.deepcopy(state)
        bad_formal = next(item for item in unbound["artifacts"] if item["id"] == "ART-FORMAL")
        bad_formal["depends_on"].remove("ART-REQUEST")
        bad_formal["dependency_fingerprints"].pop("ART-REQUEST")
        self.assert_invalid(unbound, "lacks a bound generation_request")

        g2 = next(item for item in state["confirmation_history"] if item["id"] == "CONF-G2")
        acceptance = {
            "id": "CONF-CLIENT-ACCEPT", "gate": "G2", "type": "user_confirmed", "actor": "user",
            "recorded_at": "2026-08-09T12:00:00+08:00", "expected_revision": 4,
            "decision_ids": [], "decision_fingerprints": [], "decision_record_fingerprints": [],
            "artifact_ids": list(g2["artifact_ids"]),
            "artifact_fingerprints": dict(g2["artifact_fingerprints"]),
        }
        state["confirmation_history"].append(acceptance)
        mark_valid(state, "approval_events", acceptance["id"])
        state["client_acceptance"].update(status="accepted", event_id=acceptance["id"])
        state["state_revision"] = 6
        self.assertTrue(validate_state(state)["valid"])

        state["status"] = "completed"
        self.assert_invalid(state, "requires a valid handoff archive")
        archive_dependencies = list(acceptance["artifact_ids"])
        archive = artifact(
            "ART-ARCHIVE", "handoff_archive", decision_fingerprint=formal["decision_fingerprint"],
            depends_on=archive_dependencies,
            dependency_fingerprints=_entity_fingerprints(state, archive_dependencies),
            approval_event_id=acceptance["id"], fingerprint="8" * 64, lifecycle="delivered",
        )
        state["artifacts"].append(archive)
        mark_valid(state, "artifacts", archive["id"])
        state["client_acceptance"]["handoff_archive_artifact_id"] = archive["id"]
        self.assertTrue(validate_state(state)["valid"])

# The module entry point follows the reusable V5.4 fixture.
# Keep helper construction available to package_handoff tests.
def v54_direct_delivery_state() -> dict:
    state = direct_state()
    state.update(schema_version="5.4", state_revision=5, current_internal_stage=8, status="delivered_pending_acceptance", generation_route="stable")
    state["frontstage"] = {
        "current_stage": "delivery", "completed_this_round": "automatic G2 passed",
        "pending_user_decision": "final acceptance", "next_action": "wait for client",
        "after_confirmation": "create handoff archive", "remaining_confirmations": 0,
    }
    state["production_profile"] = {
        "profile": "balanced", "selected_by": "agent_recommendation",
        "recommended_agent_model": "gpt-5.6-terra", "recommended_reasoning_effort": "medium",
        "recommended_generation_route": "fast", "active_agent_model": "",
        "active_reasoning_effort": "", "active_runtime_verified": False,
    }
    state["client_acceptance"] = {"status": "pending", "event_id": "", "handoff_archive_artifact_id": ""}
    formal = artifact("ART-FORMAL", "formal_image", fingerprint="4" * 64, lifecycle="delivered")
    qa = artifact(
        "ART-QA", "qa_report", depends_on=[formal["id"]],
        dependency_fingerprints={formal["id"]: formal["fingerprint"]}, fingerprint="5" * 64,
        lifecycle="delivered", qa_score=91, hard_failures=[],
    )
    pack = artifact(
        "ART-PACK", "build_pack", depends_on=[formal["id"], qa["id"]],
        dependency_fingerprints={formal["id"]: formal["fingerprint"], qa["id"]: qa["fingerprint"]},
        fingerprint="6" * 64, lifecycle="delivered",
    )
    state["artifacts"] = [formal, qa, pack]
    for item in state["artifacts"]:
        mark_valid(state, "artifacts", item["id"])
    event = {
        "id": "CONF-G2", "gate": "G2", "type": "system_validation", "actor": "qa_system",
        "recorded_at": "2026-08-09T10:10:00+08:00", "expected_revision": 3,
        "decision_ids": [], "decision_fingerprints": [], "decision_record_fingerprints": [],
        "artifact_ids": [formal["id"], qa["id"], pack["id"]],
        "artifact_fingerprints": {formal["id"]: formal["fingerprint"], qa["id"]: qa["fingerprint"], pack["id"]: pack["fingerprint"]},
    }
    state["confirmation_history"] = [event]
    mark_valid(state, "approval_events", event["id"])
    state["gates"]["G2"].update(status="delivered", approval_event_id=event["id"])
    return state


if __name__ == "__main__":
    unittest.main(verbosity=2)
