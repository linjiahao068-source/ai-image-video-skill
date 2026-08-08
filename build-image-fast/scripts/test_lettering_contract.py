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


if __name__ == "__main__":
    unittest.main()
