#!/usr/bin/env python3
"""Tests for final client-accepted handoff packaging."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_handoff import PackageError, write_archive
from test_validate_project_state import (
    _entity_fingerprints,
    artifact,
    v54_direct_delivery_state,
    mark_valid,
    materialize_state,
)


def accepted_v54_state() -> dict:
    state = v54_direct_delivery_state()
    state["schema_version"] = "5.4"
    state["status"] = "delivered_pending_acceptance"
    state["frontstage"] = {
        "current_stage": "delivery", "completed_this_round": "automatic G2 passed",
        "pending_user_decision": "final acceptance", "next_action": "wait for client",
        "after_confirmation": "create handoff archive", "remaining_confirmations": 0,
    }
    state["production_profile"] = {
        "profile": "balanced", "selected_by": "agent_recommendation",
        "recommended_agent_model": "gpt-5.6-terra", "recommended_reasoning_effort": "medium",
        "recommended_generation_route": "stable", "active_agent_model": "",
        "active_reasoning_effort": "", "active_runtime_verified": False,
    }
    state["client_acceptance"] = {"status": "pending", "event_id": "", "handoff_archive_artifact_id": ""}
    formal = next(item for item in state["artifacts"] if item["id"] == "ART-FORMAL")
    base_dependencies = [record_id for record_id in formal["depends_on"] if record_id.startswith("DEC-")]
    for record_id, deliverable_type in (
        ("ART-REQUEST", "generation_request"), ("ART-CONTENT", "content_pack"), ("ART-PROMPT", "prompt_pack"),
    ):
        role = "execution_scribe" if deliverable_type in {"generation_request", "prompt_pack"} else "content_character_director"
        item = artifact(
            record_id, "role_deliverable", decision_fingerprint=formal["decision_fingerprint"],
            depends_on=base_dependencies, dependency_fingerprints=_entity_fingerprints(state, base_dependencies),
            fingerprint=(record_id[-1].lower() * 64), role=role, deliverable_type=deliverable_type,
            self_check={"result": "pass", "summary": f"{deliverable_type} persisted"},
        )
        state["artifacts"].append(item)
        mark_valid(state, "artifacts", record_id)
        if deliverable_type == "generation_request":
            formal["depends_on"].append(record_id)
            formal["dependency_fingerprints"][record_id] = item["fingerprint"]
    g2 = next(item for item in state["confirmation_history"] if item["id"] == "CONF-G2")
    acceptance = {
        "id": "CONF-CLIENT-ACCEPT", "gate": "G2", "type": "user_confirmed", "actor": "user",
        "recorded_at": "2026-08-09T12:00:00+08:00", "expected_revision": 4,
        "decision_ids": [], "decision_fingerprints": [], "decision_record_fingerprints": [],
        "artifact_ids": list(g2["artifact_ids"]), "artifact_fingerprints": dict(g2["artifact_fingerprints"]),
    }
    state["confirmation_history"].append(acceptance)
    mark_valid(state, "approval_events", acceptance["id"])
    state["client_acceptance"].update(status="accepted", event_id=acceptance["id"])
    state["state_revision"] = 6
    return state


class PackageHandoffTests(unittest.TestCase):
    def test_packages_only_final_reproducibility_material_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v54-handoff-") as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            state = accepted_v54_state()
            state_path = materialize_state(project, state)
            output = project / "output" / "final-handoff.zip"
            result = write_archive(state_path, output)
            self.assertEqual(result["members"], 7)
            self.assertTrue(output.is_file())
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("ART-FORMAL.png", names)
                self.assertIn("ART-REQUEST.bin", names)
                self.assertIn("ART-CONTENT.bin", names)
                self.assertIn("ART-PROMPT.bin", names)
                self.assertIn("handoff-manifest.json", names)
                self.assertNotIn("ART-PREVIEW.bin", names)
                manifest = json.loads(archive.read("handoff-manifest.json"))
                self.assertEqual(manifest["project_id"], "state-contract-test")
            with self.assertRaisesRegex(PackageError, "refusing to overwrite"):
                write_archive(state_path, output)

    def test_rejects_archive_before_required_reproducibility_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v54-handoff-missing-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            state = accepted_v54_state()
            state["artifacts"] = [item for item in state["artifacts"] if item["id"] != "ART-CONTENT"]
            state["effective_validity"]["artifacts"].pop("ART-CONTENT")
            state_path = materialize_state(project, state)
            with self.assertRaisesRegex(PackageError, "lacks required reproducibility artifacts"):
                write_archive(state_path, project / "handoff.zip")


if __name__ == "__main__":
    unittest.main(verbosity=2)
