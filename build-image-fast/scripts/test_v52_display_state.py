#!/usr/bin/env python3
"""Focused V5.2 state-contract tests for display semantics and copy separation."""

from __future__ import annotations

import unittest

from test_validate_project_state import (
    bind_decision_dependencies,
    canonical_fingerprint,
    controlled_state,
    decision,
    mark_valid,
    refresh_fingerprint_bindings,
    refresh_decision_record,
    sync_g1_change,
)
from validate_project_state import StateError, validate_state


def v52_text_state() -> dict:
    state = controlled_state()
    state["schema_version"] = "5.2"
    state["frontstage"] = {
        "current_stage": "visual_anchor",
        "completed_this_round": "display contract locked",
        "pending_user_decision": "none",
        "next_action": "continue production",
        "after_confirmation": "not_applicable",
        "remaining_confirmations": 0,
    }
    decisions = {item["id"]: item for item in state["decisions"]}
    display = decision(
        "DEC-DISPLAY",
        "G0",
        "display_semantics",
        {
            "profile": "actual_shape",
            "elements": [{
                "id": "p2-basket-plaque",
                "panel_id": "p2",
                "target_object": "etf-basket",
                "container_presence": "required",
                "text_mode": "exact",
                "text_key": "basket_etf",
                "max_lines": 1,
                "repeat_group": "etf-basket-plaque",
                "repeat_rule": "same_text",
            }],
        },
    )
    exact = decisions["DEC-TEXT"]
    exact["value"] = {"strings": {"basket_etf": "ETF"}}
    exact["fingerprint"] = canonical_fingerprint(exact["value"])
    refresh_decision_record(exact)
    g1 = decisions["DEC-G1"]
    g1["value"]["dependency_fields"] = [
        "creative_contract", "rights_scope", "display_semantics",
    ]
    g1["value"]["coverage"] = {
        "characters": [{
            "id": "hero",
            "identity_views": ["front", "three_quarter", "side"],
            "expression_actions": ["neutral", "common_emotion", "max_allowed_action"],
        }],
        "multi_character_scale": False,
        "style_dimensions": ["line", "shape", "palette"],
        "props": ["basket"],
        "scenes": ["market"],
        "forbid_narrative_substitution": True,
    }
    g1["fingerprint"] = canonical_fingerprint(g1["value"])
    bind_decision_dependencies(g1, [decisions["DEC-G0"], decisions["DEC-RIGHTS"], display])
    state["decisions"].append(display)
    mark_valid(state, "decisions", display["id"])
    state["gates"]["G0"]["decision_ids"].append(display["id"])
    g0_event = state["confirmation_history"][0]
    g0_event["decision_ids"].append(display["id"])
    sync_g1_change(state)
    refresh_fingerprint_bindings(state)
    return state


class V52DisplayStateTests(unittest.TestCase):
    def test_v52_display_and_exact_text_contract_is_valid_before_formal_generation(self) -> None:
        report = validate_state(v52_text_state())
        self.assertFalse(report["migration_required"])
        self.assertTrue(report["text_contract"]["active"])
        self.assertEqual(report["text_contract"]["profile"], "actual_shape")

    def test_v52_exact_text_cannot_bypass_display_semantics(self) -> None:
        state = v52_text_state()
        decisions = {item["id"]: item for item in state["decisions"]}
        display = decisions["DEC-DISPLAY"]
        display["field"] = "layout_constraints"
        refresh_decision_record(display)
        g1 = decisions["DEC-G1"]
        g1["value"]["dependency_fields"][-1] = "layout_constraints"
        g1["fingerprint"] = canonical_fingerprint(g1["value"])
        bind_decision_dependencies(g1, [decisions["DEC-G0"], decisions["DEC-RIGHTS"], display])
        sync_g1_change(state)
        refresh_fingerprint_bindings(state)
        with self.assertRaisesRegex(StateError, "display_semantics"):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
