#!/usr/bin/env python3
"""Fixture-only contract tests for V5.1 asset coverage."""

import unittest

from assemble_asset_board import BuildError, validate_v51_asset_coverage


class AssetCoverageTests(unittest.TestCase):
    def test_required_detail_types_are_enforced(self) -> None:
        requirements = {
            "characters": [{"id": "character-01", "identity_views": ["front", "three_quarter", "side"], "expression_actions": ["neutral", "common_emotion", "max_allowed_action"]}],
            "multi_character_scale": False, "style_dimensions": ["line", "shape", "palette"],
            "props": ["key-prop"], "scenes": ["key-scene"],
        }
        assets = {
            "identity": {"type": "character_identity", "owner": "character-01", "views": ["front", "three_quarter", "side"], "coverage_tags": []},
            "actions": {"type": "expression_action", "owner": "character-01", "views": [], "coverage_tags": ["neutral", "common_emotion", "max_allowed_action"]},
            "style": {"type": "style_anchor", "owner": "style", "views": [], "coverage_tags": ["line", "shape", "palette"]},
            "prop": {"type": "prop_detail", "owner": "prop", "views": [], "coverage_tags": ["key-prop"]},
            "scene": {"type": "scene_reference", "owner": "scene", "views": [], "coverage_tags": ["key-scene"]},
        }
        validate_v51_asset_coverage(requirements, assets)
        assets.pop("scene")
        with self.assertRaisesRegex(BuildError, "missing scene_reference"):
            validate_v51_asset_coverage(requirements, assets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
