#!/usr/bin/env python3
"""Create a non-overwriting final image handoff ZIP after client acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from validate_project_state import FORMAL_ARTIFACT_KINDS, StateError, load_and_validate_state


class PackageError(RuntimeError):
    pass


EXCLUDED_KINDS = {"candidate_asset", "asset_triad_preview", "fidelity_test"}
SENSITIVE_SUFFIXES = {".env", ".key", ".pem", ".p12", ".pfx"}
REQUIRED_ROLE_DELIVERABLES = {"content_pack", "prompt_pack", "generation_request"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path, help="Accepted V5.4 project-state.json")
    parser.add_argument("--output", required=True, type=Path, help="New ZIP path; existing files are refused")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(root)
    except ValueError as exc:
        raise PackageError(f"path escapes project root: {path}") from exc


def is_sensitive(relative: Path) -> bool:
    lower_parts = {part.lower() for part in relative.parts}
    return relative.name.lower() in {".env", "secrets.json"} or relative.suffix.lower() in SENSITIVE_SUFFIXES or "secrets" in lower_parts


def add_member(members: dict[Path, Path], root: Path, path: Path) -> None:
    relative = within(root, path)
    if not path.is_file():
        raise PackageError(f"required handoff file is missing: {relative}")
    if is_sensitive(relative) or relative.parts[:2] == ("outputs", "candidates"):
        raise PackageError(f"refusing to package restricted file: {relative}")
    members[relative] = path.resolve()


def collect_members(report: dict[str, Any], state_path: Path) -> dict[Path, Path]:
    root = state_path.parent.resolve()
    state = report["_state"]
    acceptance = state["client_acceptance"]
    if state["status"] != "delivered_pending_acceptance" or acceptance["status"] != "accepted":
        raise PackageError("handoff ZIP requires a V5.4 accepted project awaiting archive")
    g2 = report["_events"][report["_gates"]["G2"]["approval_event_id"]]
    artifacts = report["_artifacts"]
    validity = report["_artifact_validity"]
    g2_ids = set(g2["artifact_ids"])
    final_ids = {artifact_id for artifact_id in g2_ids if artifacts[artifact_id]["kind"] in FORMAL_ARTIFACT_KINDS}
    pack_ids = {artifact_id for artifact_id in g2_ids if artifacts[artifact_id]["kind"] == "build_pack"}
    if not final_ids or not pack_ids:
        raise PackageError("G2 must contain final image and Build Pack before packaging")
    members: dict[Path, Path] = {}
    add_member(members, root, state_path)
    role_types: set[str] = set()
    for artifact_id, artifact in artifacts.items():
        if not validity[artifact_id]["valid"] or artifact["lifecycle"] in {"planned", "invalidated"}:
            continue
        kind = artifact["kind"]
        include = artifact_id in g2_ids or kind in {"asset_triad_release", "lettering_base_image", "role_deliverable"}
        if not include or kind in EXCLUDED_KINDS:
            continue
        if kind == "role_deliverable":
            role_types.add(str(artifact.get("deliverable_type", "")))
        add_member(members, root, root / artifact["file"])
    missing = sorted(REQUIRED_ROLE_DELIVERABLES - role_types)
    if missing:
        raise PackageError(f"handoff ZIP lacks required reproducibility artifacts: {missing}")
    approved_assets = root / "assets" / "approved"
    if approved_assets.is_dir():
        for path in approved_assets.rglob("*"):
            if path.is_file():
                add_member(members, root, path)
    return members


def write_archive(state_path: Path, output: Path) -> dict[str, Any]:
    try:
        report = load_and_validate_state(state_path)
    except StateError as exc:
        raise PackageError(f"invalid project state: {exc}") from exc
    members = collect_members(report, state_path)
    output = output.resolve(strict=False)
    if output.exists():
        raise PackageError(f"refusing to overwrite existing handoff ZIP: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_files = [
        {"path": relative.as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
        for relative, path in sorted(members.items(), key=lambda item: item[0].as_posix())
    ]
    manifest = {
        "schema_version": "1.0",
        "project_id": report["project_id"],
        "source_state": state_path.name,
        "files": manifest_files,
    }
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, path in sorted(members.items(), key=lambda item: item[0].as_posix()):
                archive.write(path, relative.as_posix())
            archive.writestr("handoff-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        if output.exists():
            output.unlink()
        raise
    return {"file": str(output), "sha256": sha256(output), "members": len(manifest_files)}


def main() -> int:
    args = parse_args()
    try:
        result = write_archive(args.state, args.output)
    except (OSError, PackageError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
