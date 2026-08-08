#!/usr/bin/env python3
"""Atomically apply a top-level JSON patch to a V5.2 project-state file."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from validate_project_state import StateError, load_and_validate_state, validate_state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True, type=int)
    return parser.parse_args()


def commit_state(state_path: Path, patch_path: Path, expected_revision: int) -> dict[str, Any]:
    state_path = state_path.resolve()
    if not state_path.is_file() or not patch_path.is_file():
        raise StateError("state and patch files must exist")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    if not isinstance(patch, dict):
        raise StateError("patch must be a JSON object")
    if state.get("state_revision") != expected_revision:
        raise StateError("stale state revision; refusing overwrite")
    forbidden = {"project_id", "schema_version", "state_revision"}
    if forbidden & set(patch):
        raise StateError("patch cannot replace project identity or revision")
    candidate = {**state, **patch, "state_revision": expected_revision + 1}
    validate_state(candidate)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{state_path.stem}.", suffix=".tmp", dir=state_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(candidate, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, state_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return load_and_validate_state(state_path)


def main() -> int:
    args = parse_args()
    report = commit_state(args.state, args.patch, args.expected_revision)
    print(json.dumps({key: value for key, value in report.items() if not key.startswith("_")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (StateError, OSError, json.JSONDecodeError) as exc:
        print(f"project-state commit failed: {exc}")
        raise SystemExit(2)
