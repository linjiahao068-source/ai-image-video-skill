#!/usr/bin/env python3
"""V5.3 state tests for display semantics and opt-in comic typography."""

from __future__ import annotations

import unittest

from test_v52_display_state import v52_text_state
from test_validate_project_state import (
    bind_decision_dependencies,
    canonical_fingerprint,
    decision,
    mark_valid,
    refresh_decision_record,
    refresh_fingerprint_bindings,
    sync_g1_change,
)
from validate_project_state import StateError, validate_state


def v53_comic_state() -> dict:
    state = v52_text_state()
    state["schema_version"] = "5.3"
    decisions = {item["id"]: item for item in state["decisions"]}
    display = decisions["DEC-DISPLAY"]
    display["value"]["elements"][0]["semantic_role"] = "primary_anchor"
    display["value"]["elements"][0]["reading_priority"] = 1
    display["fingerprint"] = canonical_fingerprint(display["value"])
    refresh_decision_record(display)
    profile = decision("DEC-TYPOGRAPHY", "G0", "typography_profile", "comic_display")
    state["decisions"].append(profile)
    mark_valid(state, "decisions", profile["id"])
    state["gates"]["G0"]["decision_ids"].append(profile["id"])
    g0_event = state["confirmation_history"][0]
    g0_event["decision_ids"].append(profile["id"])
    g0_event["decision_fingerprints"].append(profile["fingerprint"])
    g0_event["decision_record_fingerprints"].append(profile["record_fingerprint"])
    g1 = decisions["DEC-G1"]
    g1["value"]["dependency_fields"].append("typography_profile")
    g1["fingerprint"] = canonical_fingerprint(g1["value"])
    bind_decision_dependencies(g1, [decisions["DEC-G0"], decisions["DEC-RIGHTS"], display, profile])
    sync_g1_change(state)
    refresh_fingerprint_bindings(state)
    return state


def refresh_v53_dependency_chain(state: dict) -> None:
    decisions = {item["id"]: item for item in state["decisions"]}
    g1 = decisions["DEC-G1"]
    g1["fingerprint"] = canonical_fingerprint(g1["value"])
    bind_decision_dependencies(g1, [decisions["DEC-G0"], decisions["DEC-RIGHTS"], decisions["DEC-DISPLAY"], decisions["DEC-TYPOGRAPHY"]])
    sync_g1_change(state)
    refresh_fingerprint_bindings(state)


class V53TypographyStateTests(unittest.TestCase):
    def test_v53_comic_profile_requires_semantic_display_roles(self) -> None:
        report = validate_state(v53_comic_state())
        self.assertEqual(report["schema_version"], "5.3")
        self.assertEqual(report["text_contract"]["typography_profile"], "comic_display")

    def test_v53_rejects_missing_semantic_role(self) -> None:
        state = v53_comic_state()
        decision_by_id = {item["id"]: item for item in state["decisions"]}
        display = decision_by_id["DEC-DISPLAY"]
        display["value"]["elements"][0].pop("semantic_role")
        display["fingerprint"] = canonical_fingerprint(display["value"])
        refresh_decision_record(display)
        refresh_v53_dependency_chain(state)
        with self.assertRaisesRegex(StateError, "semantic_role"):
            validate_state(state)

    def test_v53_rejects_invalid_typography_profile(self) -> None:
        state = v53_comic_state()
        profile = next(item for item in state["decisions"] if item["id"] == "DEC-TYPOGRAPHY")
        profile["value"] = "unknown_profile"
        profile["fingerprint"] = canonical_fingerprint(profile["value"])
        refresh_decision_record(profile)
        refresh_v53_dependency_chain(state)
        with self.assertRaisesRegex(StateError, "typography_profile"):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
