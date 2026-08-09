#!/usr/bin/env python3
"""Unit tests for deterministic lettering and actual-shape geometry validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import assemble_lettering
import validate_lettering_geometry


FONT = Path("C:/Windows/Fonts/arial.ttf")
COMIC_FONT = Path("C:/Windows/Fonts/msyhbd.ttc")
VARIABLE_FONT = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class LetteringContractTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[argparse.Namespace, argparse.Namespace, Path, Path]:
        base = root / "base.png"
        Image.new("RGBA", (240, 160), "white").save(base)
        display = root / "display.json"
        write_json(display, {
            "schema_version": "1.0",
            "canvas": {"width": 240, "height": 160},
            "profile": "actual_shape",
            "elements": [{
                "id": "basket-plaque-p2",
                "container_presence": "required",
                "text_mode": "exact",
                "text": "ETF",
                "max_lines": 1,
                "max_font_size": 40,
                "min_font_size": 12,
                "repeat_group": "basket-plaque",
                "repeat_rule": "same_text",
            }],
        })
        geometry = root / "geometry.json"
        write_json(geometry, {
            "schema_version": "1.0",
            "canvas": {"width": 240, "height": 160},
            "source_base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            "regions": [{
                "element_id": "basket-plaque-p2",
                "container_polygon": [[30, 25], [210, 25], [210, 125], [30, 125]],
                "safe_margin_px": 8,
                "safe_polygon": [[45, 40], [195, 40], [195, 105], [45, 105]],
                "exclusion_polygons": [{"kind": "tail", "points": [[110, 90], [140, 90], [125, 120]]}],
                "text_box": [50, 45, 190, 90],
            }],
        })
        output = root / "final.png"
        report = root / "build.json"
        masks = root / "masks"
        assembly = argparse.Namespace(
            base=base, display_contract=display, geometry_contract=geometry,
            font=FONT, output=output, mask_dir=masks, report=report,
        )
        fit = argparse.Namespace(
            base=base, final=output, display_contract=display, geometry_contract=geometry,
            build_report=report, output=root / "fit.json",
        )
        return assembly, fit, report, masks / "basket-plaque-p2.png"

    @unittest.skipUnless(FONT.is_file(), "requires Windows Arial font")
    def test_clean_lettering_passes_actual_shape_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, fit, _, _ = self.fixture(Path(raw))
            assemble_lettering.build(assembly)
            report, code = validate_lettering_geometry.validate(fit)
            self.assertEqual(code, 0)
            self.assertTrue(report["passed"])
            self.assertEqual(report["checks"][0]["outside_pixels"], 0)

    @unittest.skipUnless(FONT.is_file(), "requires Windows Arial font")
    def test_mask_crossing_tail_fails_even_when_build_log_is_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, fit, build_path, mask_path = self.fixture(Path(raw))
            assemble_lettering.build(assembly)
            mask = Image.open(mask_path).convert("L")
            mask.putpixel((125, 110), 255)  # In the explicitly excluded tail.
            mask.save(mask_path)
            build = json.loads(build_path.read_text(encoding="utf-8"))
            build["entries"][0]["mask_sha256"] = hashlib.sha256(mask_path.read_bytes()).hexdigest()
            write_json(build_path, build)
            report, code = validate_lettering_geometry.validate(fit)
            self.assertEqual(code, 2)
            self.assertFalse(report["passed"])
            self.assertIn("glyph mask exceeds safe polygon", report["errors"][0])



class ComicTypographyTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[argparse.Namespace, argparse.Namespace, Path, Path]:
        base = root / "base.png"
        Image.new("RGBA", (640, 400), "white").save(base)
        display = root / "display.json"
        write_json(display, {
            "schema_version": "1.0",
            "canvas": {"width": 640, "height": 400},
            "typography_profile": "comic_display",
            "elements": [
                {"id": "p1-dialogue", "container_presence": "required", "text_mode": "exact", "text": "ETF知识一篮子资产", "semantic_role": "dialogue", "reading_priority": 1, "max_lines": 2, "max_font_size": 44, "min_font_size": 12},
                {"id": "p2-anchor", "container_presence": "required", "text_mode": "exact", "text": "ETF", "semantic_role": "primary_anchor", "reading_priority": 1, "max_lines": 1, "max_font_size": 88, "min_font_size": 12},
                {"id": "p3-label", "container_presence": "required", "text_mode": "exact", "text": "苹果", "semantic_role": "object_label", "reading_priority": 2, "max_lines": 1, "max_font_size": 40, "min_font_size": 12},
                {"id": "p4-footer", "container_presence": "required", "text_mode": "exact", "text": "分散风险", "semantic_role": "footer", "reading_priority": 3, "max_lines": 1, "max_font_size": 40, "min_font_size": 12},
            ],
        })
        boxes = {
            "p1-dialogue": [40, 40, 320, 150],
            "p2-anchor": [360, 40, 620, 150],
            "p3-label": [40, 230, 200, 300],
            "p4-footer": [230, 230, 620, 320],
        }
        lines = {
            "p1-dialogue": ["ETF知识", "一篮子资产"],
            "p2-anchor": ["ETF"],
            "p3-label": ["苹果"],
            "p4-footer": ["分散风险"],
        }
        regions = []
        for identifier, box in boxes.items():
            left, top, right, bottom = box
            regions.append({
                "element_id": identifier,
                "container_polygon": [[left, top], [right, top], [right, bottom], [left, bottom]],
                "safe_margin_px": 0,
                "safe_polygon": [[left - 5, top - 5], [right + 5, top - 5], [right + 5, bottom + 5], [left - 5, bottom + 5]],
                "exclusion_polygons": [],
                "text_box": box,
                "typography": {"locked_lines": lines[identifier], "optical_offset_px": [0, 0]},
            })
        geometry = root / "geometry.json"
        write_json(geometry, {
            "schema_version": "1.0",
            "canvas": {"width": 640, "height": 400},
            "source_base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            "regions": regions,
        })
        typography = root / "typography.json"
        font_hash = hashlib.sha256(COMIC_FONT.read_bytes()).hexdigest()
        roles = {
            "dialogue": ("center", "center", "bold", 24, 0.25, 4),
            "primary_anchor": ("center", "center", "bold", 48, 0.30, 2),
            "object_label": ("center", "center", "bold", 18, 0.15, 2),
            "footer": ("left", "center", "bold", 18, 0.15, 3),
        }
        write_json(typography, {
            "schema_version": "1.0",
            "profile": "comic_display",
            "use_scope": "commercial",
            "font": {"file": str(COMIC_FONT), "sha256": font_hash, "family": "Microsoft YaHei", "weight": "bold", "license_status": "confirmed"},
            "roles": {
                key: {"alignment": value[0], "vertical_anchor": value[1], "font_weight": value[2], "fill": "#111111", "stroke_width": 0, "minimum_font_size": value[3], "minimum_occupancy_ratio": value[4], "line_spacing": value[5]}
                for key, value in roles.items()
            },
        })
        output, report, masks = root / "final.png", root / "build.json", root / "masks"
        assembly = argparse.Namespace(base=base, display_contract=display, geometry_contract=geometry, typography_contract=typography, font=None, output=output, mask_dir=masks, report=report)
        fit = argparse.Namespace(base=base, final=output, display_contract=display, geometry_contract=geometry, typography_contract=typography, build_report=report, output=root / "fit.json")
        return assembly, fit, typography, report

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_comic_display_passes_geometry_and_typography_checks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, fit, _, _ = self.fixture(Path(raw))
            assemble_lettering.build(assembly)
            report, code = validate_lettering_geometry.validate(fit)
            self.assertEqual(code, 0)
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["typography_checks"]), 4)
            self.assertTrue(all(item["result"] == "passed" for item in report["typography_checks"]))

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_comic_display_refuses_to_shrink_below_art_direction_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, _, typography_path, _ = self.fixture(Path(raw))
            payload = json.loads(typography_path.read_text(encoding="utf-8"))
            payload["roles"]["dialogue"]["minimum_font_size"] = 80
            write_json(typography_path, payload)
            with self.assertRaisesRegex(assemble_lettering.LetteringError, "minimum_font_size"):
                assemble_lettering.build(assembly)

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_independent_validator_rejects_tampered_centering_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, fit, _, build_path = self.fixture(Path(raw))
            assemble_lettering.build(assembly)
            build = json.loads(build_path.read_text(encoding="utf-8"))
            build["entries"][0]["max_center_error_px"] = 9
            write_json(build_path, build)
            report, code = validate_lettering_geometry.validate(fit)
            self.assertEqual(code, 2)
            self.assertFalse(report["passed"])
            self.assertIn("not optically centered", report["errors"][0])

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_comic_display_requires_typography_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, _, _, _ = self.fixture(Path(raw))
            assembly.typography_contract = None
            assembly.font = COMIC_FONT
            with self.assertRaisesRegex(assemble_lettering.LetteringError, "requires --typography-contract"):
                assemble_lettering.build(assembly)

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_comic_display_rejects_font_hash_and_line_group_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, _, typography_path, _ = self.fixture(Path(raw))
            payload = json.loads(typography_path.read_text(encoding="utf-8"))
            payload["font"]["sha256"] = "0" * 64
            write_json(typography_path, payload)
            with self.assertRaisesRegex(assemble_lettering.LetteringError, "SHA-256"):
                assemble_lettering.build(assembly)
            payload["font"]["sha256"] = hashlib.sha256(COMIC_FONT.read_bytes()).hexdigest()
            write_json(typography_path, payload)
            geometry = json.loads(assembly.geometry_contract.read_text(encoding="utf-8"))
            geometry["regions"][0]["typography"]["locked_lines"] = ["ETF知识", "错误资产"]
            write_json(assembly.geometry_contract, geometry)
            with self.assertRaisesRegex(assemble_lettering.LetteringError, "locked_lines"):
                assemble_lettering.build(assembly)

    @unittest.skipUnless(COMIC_FONT.is_file(), "requires Microsoft YaHei Bold")
    def test_comic_display_rejects_insufficient_visual_occupancy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            assembly, _, typography_path, _ = self.fixture(Path(raw))
            payload = json.loads(typography_path.read_text(encoding="utf-8"))
            payload["roles"]["dialogue"]["minimum_occupancy_ratio"] = 0.99
            write_json(typography_path, payload)
            with self.assertRaisesRegex(assemble_lettering.LetteringError, "minimum occupancy"):
                assemble_lettering.build(assembly)

    @unittest.skipUnless(VARIABLE_FONT.is_file(), "requires Noto Sans SC variable font")
    def test_variable_font_applies_requested_weight(self) -> None:
        regular = assemble_lettering.load_weighted_font(VARIABLE_FONT, 48, "regular", "regular")
        bold = assemble_lettering.load_weighted_font(VARIABLE_FONT, 48, "bold", "regular")
        self.assertNotEqual(bytes(regular.getmask("ETF", mode="L")), bytes(bold.getmask("ETF", mode="L")))

if __name__ == "__main__":
    unittest.main()
