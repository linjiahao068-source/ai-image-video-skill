#!/usr/bin/env python3
"""Contract tests for the deterministic V5 asset-board assembler."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from test_validate_project_state import artifact, bind_decision_dependencies, canonical_fingerprint, controlled_state, mark_valid, refresh_decision_record, refresh_fingerprint_bindings


SCRIPT = Path(__file__).with_name("assemble_asset_board.py")
FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AssetBoardAssemblerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.font = next((item for item in FONT_CANDIDATES if item.is_file()), None)
        if cls.font is None:
            raise unittest.SkipTest("No CJK font is installed for assembler tests")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="asset-board-v5-test-")
        self.root = Path(self.temp.name)
        self.red = self.root / "red.png"
        self.blue = self.root / "blue.png"
        Image.new("RGB", (640, 480), (240, 30, 30)).save(self.red)
        Image.new("RGB", (480, 640), (30, 90, 240)).save(self.blue)
        self.state_path = self.root / "project-state.json"
        self.state = self.pre_g1_state()
        self.write_state()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pre_g1_state(self) -> dict:
        state = controlled_state()
        state["state_revision"] = 3
        state["current_internal_stage"] = 5
        state["gates"]["G1"].update(status="pending", approval_event_id="")
        state["artifacts"] = []
        state["confirmation_history"] = state["confirmation_history"][:1]
        state["effective_validity"]["artifacts"] = {}
        state["effective_validity"]["approval_events"].pop("CONF-G1")
        state["status"] = "blocked"
        state["blockers"] = ["fidelity candidate pending"]
        state["risk_modules"]["fidelity_lock"]["status"] = "unresolved"
        state["schema_version"] = "5.2"
        state["frontstage"] = {
            "current_stage": "asset_detail",
            "completed_this_round": "asset board candidate pending",
            "pending_user_decision": "G1",
            "next_action": "assemble candidate assets",
            "after_confirmation": "release assets",
            "remaining_confirmations": 1,
        }
        decisions = {item["id"]: item for item in state["decisions"]}
        text_budget = decisions["DEC-TEXT"]
        text_budget["field"] = "text_budget"
        text_budget["value"] = {"max_chars": 30, "max_lines": 2}
        text_budget["fingerprint"] = canonical_fingerprint(text_budget["value"])
        refresh_decision_record(text_budget)
        g1 = decisions["DEC-G1"]
        g1["value"]["dependency_fields"] = ["creative_contract", "rights_scope", "text_budget"]
        g1["value"]["excluded_g0_fields"] = []
        g1["value"]["coverage"] = {
            "characters": [{
                "id": "hero",
                "identity_views": ["front", "three_quarter", "side"],
                "expression_actions": ["neutral", "common_emotion", "max_allowed_action"],
            }],
            "multi_character_scale": False,
            "style_dimensions": ["line", "shape", "palette"],
            "props": ["key-prop"],
            "scenes": ["key-scene"],
            "forbid_narrative_substitution": True,
        }
        g1["fingerprint"] = canonical_fingerprint(g1["value"])
        bind_decision_dependencies(g1, [decisions["DEC-G0"], decisions["DEC-RIGHTS"], text_budget])
        refresh_fingerprint_bindings(state)
        return state

    def write_state(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def asset(
        self,
        asset_id: str,
        source: Path,
        *,
        status: str = "candidate",
        contains_text: bool = False,
        clean_groups: list[str] | None = None,
        dedicated_group: str = "",
        sha256: str = "",
    ) -> dict:
        return {
            "id": asset_id,
            "file": str(source),
            "type": "character",
            "label": f"Character {asset_id}",
            "role": "identity and performance reference",
            "owner": "art_director",
            "must_preserve": ["silhouette"],
            "forbidden": ["role drift"],
            "contract_versions": ["character-contract-v0.2"],
            "rights_scope": "project-authorized-test",
            "approval_status": status,
            "contains_text": contains_text,
            "critical": True,
            "clean_groups": clean_groups if clean_groups is not None else ["characters"],
            "dedicated_group": dedicated_group,
            "sha256": sha256,
        }

    def manifest(self, assets: list[dict], *, mode: str = "candidate_preview") -> dict:
        g1_fp = self.state["decisions"][1]["fingerprint"]
        return {
            "schema_version": "5.0",
            "project_id": self.state["project_id"],
            "version": "asset-triad-v0.1",
            "build_mode": mode,
            "workflow_state_ref": str(self.state_path),
            "approval_event_id": "CONF-G1" if mode == "release" else "",
            "decision_fingerprint": g1_fp,
            "canvas": {
                "width": 1600,
                "height": 1200,
                "padding": 40,
                "gap": 24,
                "background": "#F4F4F4",
                "label_height": 220,
                "font_size": 34,
                "max_clean_slots": 8,
                "max_clean_primary_roles": 2,
                "min_clean_tile_short_side": 384,
                "min_annotated_tile_short_side": 384,
            },
            "boards": {
                "annotated": {
                    "filename": "project-asset-master-annotated-v01.png",
                    "sections": [
                        {
                            "id": "characters",
                            "title": "Main characters",
                            "asset_ids": [item["id"] for item in assets],
                        }
                    ],
                },
                "clean_groups": [
                    {
                        "id": "characters",
                        "filename": "project-asset-reference-clean-01-v01.png",
                        "primary_roles": ["identity", "performance"],
                        "asset_ids": [item["id"] for item in assets],
                    }
                ],
                "report_filename": "asset-board-build-report-v0.1.json",
            },
            "assets": assets,
        }

    def run_builder(
        self,
        manifest: dict,
        out_dir: Path,
        *,
        baseline: Path | None = None,
        font: Path | None = None,
        bind_state: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        count = len(list(self.root.glob("manifest-*.json")))
        manifest_path = self.root / f"manifest-{count:02d}.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        command = [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--out-dir",
            str(out_dir),
        ]
        if bind_state:
            command.extend(["--workflow-state", str(self.state_path)])
        if baseline is not None:
            command.extend(["--baseline-report", str(baseline)])
        if font is not None:
            command.extend(["--font", str(font)])
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        return subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            env=environment,
        )

    def build_candidate(self, assets: list[dict] | None = None) -> tuple[dict, Path]:
        assets = assets or [self.asset("CHAR-01", self.red)]
        manifest = self.manifest(assets)
        out_dir = self.root / f"candidate-{len(list(self.root.glob('candidate-*'))):02d}"
        result = self.run_builder(manifest, out_dir, font=self.font)
        self.assertEqual(result.returncode, 0, result.stderr)
        return manifest, out_dir / "asset-board-build-report-v0.1.json"

    def promote_state(
        self,
        baseline: Path,
        *,
        include_test: bool = True,
        preview_file: Path | None = None,
        preview_hash: str | None = None,
        event_type: str = "user_confirmed",
    ) -> None:
        decisions = {item["id"]: item for item in self.state["decisions"]}
        g1_ids = list(self.state["gates"]["G1"]["decision_ids"])
        self.assertEqual(len(g1_ids), 1)
        g1 = decisions[g1_ids[0]]
        g1_fp = g1["fingerprint"]
        anchor_ids = list(g1["depends_on"]) + g1_ids
        anchor_fingerprints = {
            record_id: decisions[record_id]["fingerprint"] for record_id in anchor_ids
        }

        resolved_preview = (preview_file or baseline).resolve()
        if preview_file is not None and not resolved_preview.exists():
            resolved_preview.write_bytes(baseline.read_bytes())
        preview = artifact(
            "ART-PREVIEW",
            "asset_triad_preview",
            decision_fingerprint=g1_fp,
            depends_on=anchor_ids,
            dependency_fingerprints=anchor_fingerprints,
            approval_event_id="CONF-G1",
            fingerprint=preview_hash or file_hash(resolved_preview),
            candidate_set_id="CAND-01",
        )
        preview["file"] = str(resolved_preview)
        artifacts = [preview]
        artifact_ids = [preview["id"]]
        if include_test:
            fidelity_path = self.root / "fidelity-test-v0.1.json"
            fidelity_path.write_text(
                json.dumps(
                    {"result": "passed", "hard_failures": []},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            fidelity = artifact(
                "ART-FIDELITY",
                "fidelity_test",
                decision_fingerprint=g1_fp,
                depends_on=anchor_ids,
                dependency_fingerprints=anchor_fingerprints,
                approval_event_id="CONF-G1",
                fingerprint=file_hash(fidelity_path),
                candidate_set_id="CAND-01",
                result="passed",
                hard_failures=[],
            )
            fidelity["file"] = str(fidelity_path)
            artifacts.append(fidelity)
            artifact_ids.append(fidelity["id"])
        self.state["state_revision"] = 4
        self.state["status"] = "active"
        self.state["blockers"] = []
        self.state["risk_modules"]["fidelity_lock"]["status"] = "resolved"
        self.state["current_internal_stage"] = 6
        self.state["gates"]["G1"].update(status="approved", approval_event_id="CONF-G1")
        self.state["artifacts"] = artifacts
        self.state["confirmation_history"].append(
            {
                "id": "CONF-G1",
                "gate": "G1",
                "type": event_type,
                "actor": "user",
                "recorded_at": "2026-08-07T10:05:00+08:00",
                "expected_revision": 2,
                "decision_ids": g1_ids,
                "decision_fingerprints": [g1_fp],
                "decision_record_fingerprints": [g1["record_fingerprint"]],
                "artifact_ids": artifact_ids,
                "artifact_fingerprints": {
                    item["id"]: item["fingerprint"] for item in artifacts
                },
            }
        )
        self.state["effective_validity"]["artifacts"] = {}
        for item in artifacts:
            mark_valid(self.state, "artifacts", item["id"])
        mark_valid(self.state, "approval_events", "CONF-G1")
        if event_type == "delegated_decision":
            self.state["delegation_scope"] = {
                "enabled": True,
                "allowed_fields": ["asset_board_spec"],
                "excluded_fields": ["rights_scope"],
                "authorized_by": "user",
                "source": "user_request",
            }
        self.write_state()

    def release_manifest(self, candidate: dict) -> dict:
        manifest = copy.deepcopy(candidate)
        manifest["build_mode"] = "release"
        manifest["approval_event_id"] = "CONF-G1"
        for item in manifest["assets"]:
            item["approval_status"] = "approved"
            item["sha256"] = file_hash(Path(item["file"]))
        return manifest

    def test_candidate_is_deterministic_clean_and_non_overwriting(self) -> None:
        assets = [self.asset("CHAR-01", self.red), self.asset("CHAR-02", self.blue)]
        manifest = self.manifest(assets)
        out_a, out_b = self.root / "out-a", self.root / "out-b"
        first = self.run_builder(manifest, out_a, font=self.font)
        second = self.run_builder(manifest, out_b, font=self.font)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        for name in (
            "project-asset-master-annotated-v01.png",
            "project-asset-reference-clean-01-v01.png",
            "asset-board-build-report-v0.1.json",
        ):
            self.assertEqual(file_hash(out_a / name), file_hash(out_b / name))
        report = json.loads((out_a / "asset-board-build-report-v0.1.json").read_text("utf-8"))
        self.assertFalse(report["registry_eligible"])
        checks = report["checks"]
        self.assertTrue(checks["no_added_text_in_clean_boards"])
        self.assertEqual(
            checks["no_added_text_in_clean_boards_meaning"],
            "deterministic compositor added no labels to clean boards",
        )
        self.assertFalse(checks["pixel_level_text_absence_verified"])
        self.assertEqual(checks["verification_method"], "not_run")
        self.assertTrue(checks["clean_source_text_flags_empty"])
        self.assertIn("manifest declarations only", checks["clean_source_text_flags_meaning"])
        self.assertFalse(checks["ocr_or_manual_text_qa_run"])
        before = file_hash(out_a / "asset-board-build-report-v0.1.json")
        repeated = self.run_builder(manifest, out_a, font=self.font)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("refusing to overwrite", repeated.stderr)
        self.assertEqual(before, file_hash(out_a / "asset-board-build-report-v0.1.json"))

    def test_legacy_v4_manifest_is_preview_only(self) -> None:
        manifest = self.manifest([self.asset("CHAR-01", self.red)])
        manifest["schema_version"] = "1.0"
        for key in ("workflow_state_ref", "approval_event_id", "decision_fingerprint"):
            manifest.pop(key)
        preview = self.run_builder(
            manifest, self.root / "legacy-preview", font=self.font, bind_state=False
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        report = json.loads(
            (self.root / "legacy-preview" / "asset-board-build-report-v0.1.json").read_text(
                "utf-8"
            )
        )
        self.assertFalse(report["registry_eligible"])

        manifest["build_mode"] = "release"
        release = self.run_builder(
            manifest, self.root / "legacy-release", font=self.font, bind_state=False
        )
        self.assertEqual(release.returncode, 2)
        self.assertIn("legacy V4 manifests may build candidate_preview only", release.stderr)

    def test_normal_candidate_to_release_promotion_passes(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline)
        out_dir = self.root / "release"
        result = self.run_builder(
            self.release_manifest(candidate), out_dir, baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((out_dir / "asset-board-build-report-v0.1.json").read_text("utf-8"))
        self.assertTrue(report["registry_eligible"])
        self.assertTrue(report["checks"]["approval_reference_valid"])
        self.assertTrue(report["checks"]["candidate_release_equivalent"])
        self.assertEqual(
            report["promotion_equivalence"]["approval_preview_artifact_id"], "ART-PREVIEW"
        )

    def test_release_rejects_empty_g1_artifact_ids(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline)
        self.state["confirmation_history"][-1]["artifact_ids"] = []
        self.state["confirmation_history"][-1]["artifact_fingerprints"] = {}
        self.write_state()
        result = self.run_builder(
            self.release_manifest(candidate), self.root / "empty-g1", baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("asset_triad_preview", result.stderr)

    def test_release_rejects_missing_fidelity_test(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline, include_test=False)
        result = self.run_builder(
            self.release_manifest(candidate), self.root / "missing-test", baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("fidelity_test", result.stderr)

    def test_release_rejects_baseline_path_mismatch(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline, preview_file=self.root / "different-report.json")
        result = self.run_builder(
            self.release_manifest(candidate), self.root / "path-mismatch", baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("baseline report path", result.stderr)

    def test_release_rejects_baseline_hash_mismatch(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline, preview_hash="0" * 64)
        result = self.run_builder(
            self.release_manifest(candidate), self.root / "hash-mismatch", baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("artifact ART-PREVIEW file SHA-256 does not match fingerprint", result.stderr)

    def test_release_rejects_delegated_visual_anchor_approval(self) -> None:
        candidate, baseline = self.build_candidate()
        self.promote_state(baseline, event_type="delegated_decision")
        result = self.run_builder(
            self.release_manifest(candidate), self.root / "delegated", baseline=baseline, font=self.font
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires user_confirmed", result.stderr)

    def test_blocked_state_rejects_candidate_preview(self) -> None:
        self.state["status"] = "blocked"
        self.state["blockers"] = ["rights unresolved"]
        self.state["risk_modules"]["rights_lock"] = {
            "level": "hard", "status": "unresolved", "evidence": []
        }
        self.write_state()
        result = self.run_builder(
            self.manifest([self.asset("CHAR-01", self.red)]),
            self.root / "blocked",
            font=self.font,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("workflow state is blocked", result.stderr)

    def test_fidelity_only_block_allows_controlled_candidate_preview(self) -> None:
        self.state["status"] = "blocked"
        self.state["blockers"] = ["fidelity candidate pending"]
        self.state["risk_modules"]["fidelity_lock"] = {
            "level": "hard", "status": "unresolved",
            "evidence": [self.state["gates"]["G1"]["decision_ids"][0]],
        }
        self.write_state()
        result = self.run_builder(
            self.manifest([self.asset("CHAR-01", self.red)]),
            self.root / "fidelity-candidate",
            font=self.font,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_candidate_requires_explicit_standing_authorization(self) -> None:
        authorized = copy.deepcopy(self.state)
        cases = (
            ("generate_one_candidate", False, "generate_one_candidate=true"),
            ("max_candidates", 0, "max_candidates>=1"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                self.state = copy.deepcopy(authorized)
                self.state["standing_authorization"][field] = value
                self.write_state()
                result = self.run_builder(
                    self.manifest([self.asset("CHAR-01", self.red)]),
                    self.root / f"unauthorized-{field}",
                    font=self.font,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("standing_authorization", result.stderr)
                self.assertIn(expected, result.stderr)

        self.state = copy.deepcopy(authorized)
        self.state["status"] = "active"
        self.state["blockers"] = []
        self.state["risk_modules"]["fidelity_lock"]["level"] = "low"
        self.state["risk_modules"]["fidelity_lock"]["status"] = "resolved"
        self.state["gates"]["G0"].update(status="pending", approval_event_id="")
        self.state["confirmation_history"] = []
        self.state["effective_validity"]["approval_events"].pop("CONF-G0")
        self.write_state()
        result = self.run_builder(
            self.manifest([self.asset("CHAR-01", self.red)]),
            self.root / "g0-pending",
            font=self.font,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("controlled candidate assets require approved G0", result.stderr)

    def test_manifest_cannot_relax_hard_split_limits(self) -> None:
        cases = (
            ("max_clean_slots", 9, "hard limit 8"),
            ("max_clean_primary_roles", 3, "hard limit 2"),
            ("min_clean_tile_short_side", 383, "hard minimum 384px"),
            ("min_annotated_tile_short_side", 383, "hard minimum 384px"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                manifest = self.manifest([self.asset("CHAR-01", self.red)])
                manifest["canvas"][field] = value
                result = self.run_builder(
                    manifest,
                    self.root / f"relaxed-{field}",
                    font=self.font,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)

    def test_clean_group_hard_limits_and_text_leak_fail(self) -> None:
        overloaded_assets = [self.asset(f"CHAR-{index:02d}", self.red) for index in range(9)]
        overloaded = self.manifest(overloaded_assets)
        overloaded["canvas"]["width"] = 4800
        overloaded["canvas"]["height"] = 4800
        result = self.run_builder(overloaded, self.root / "overloaded", font=self.font)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds max_clean_slots", result.stderr)

        text_manifest = self.manifest([self.asset("CHAR-01", self.red, contains_text=True)])
        text_result = self.run_builder(text_manifest, self.root / "text-bearing", font=self.font)
        self.assertEqual(text_result.returncode, 2)
        self.assertIn("contains text-bearing asset", text_result.stderr)

    def test_dedicated_group_cannot_mix_with_shared_asset(self) -> None:
        dedicated = self.asset(
            "CHAR-01", self.red, clean_groups=["detail"], dedicated_group="detail"
        )
        shared = self.asset("PROP-01", self.blue, clean_groups=["detail"])
        manifest = self.manifest([dedicated, shared])
        manifest["boards"]["clean_groups"][0]["id"] = "detail"
        result = self.run_builder(manifest, self.root / "dedicated", font=self.font)
        self.assertEqual(result.returncode, 2)
        self.assertIn("mixes dedicated and shared assets", result.stderr)

    def test_missing_font_and_label_overflow_block_outputs(self) -> None:
        manifest = self.manifest([self.asset("CHAR-01", self.red)])
        missing = self.run_builder(
            manifest, self.root / "missing-font", font=self.root / "none.ttf"
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("no usable CJK font", missing.stderr)

        overflow_manifest = copy.deepcopy(manifest)
        overflow_manifest["assets"][0]["label"] = "Very long label " * 100
        overflow_manifest["canvas"]["label_height"] = 60
        overflow = self.run_builder(
            overflow_manifest, self.root / "overflow", font=self.font
        )
        self.assertEqual(overflow.returncode, 2)
        self.assertIn("label overflow", overflow.stderr)

    def test_output_path_escape_is_rejected(self) -> None:
        manifest = self.manifest([self.asset("CHAR-01", self.red)])
        manifest["boards"]["annotated"]["filename"] = "../escape.png"
        result = self.run_builder(manifest, self.root / "escape", font=self.font)
        self.assertEqual(result.returncode, 2)
        self.assertIn("plain filename", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
