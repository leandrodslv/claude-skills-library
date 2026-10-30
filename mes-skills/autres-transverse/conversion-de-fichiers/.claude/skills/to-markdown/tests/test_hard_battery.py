"""Intégrité de la batterie de documents difficiles (fonctions pures, sans convertisseur tiers)."""
import json
import sys
import unittest
from pathlib import Path

HARD = Path(__file__).resolve().parent.parent / "benchmark" / "hard"
sys.path.insert(0, str(HARD.parent))
sys.path.insert(0, str(HARD))
sys.path.insert(0, str(HARD.parent.parent / "scripts"))
import run_hard  # noqa: E402


class HardBattery(unittest.TestCase):
    def test_manifest_points_to_existing_files_with_unique_ids(self):
        manifest = json.loads((HARD / "manifest.json").read_text(encoding="utf-8"))
        ids = [c["id"] for c in manifest]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 40)
        for c in manifest:
            if c["category"] == "big":
                continue
            self.assertTrue((HARD / "corpus" / c["path"]).is_file(), c["path"])
            self.assertIn(c["difficulty"], range(1, 6))
            self.assertTrue(c.get("challenge"))
            self.assertTrue(any(c.get(k) for k in ("must", "any_of", "cells", "items", "order", "rows")) or c.get("expect") == "error", c["id"])

    def test_evaluate_scores_what_is_found_and_flags_noise(self):
        case = {"must": ["alpha beta", "gamma"], "absent": ["bruit"], "once": ["delta"], "headings": ["Titre"], "cells": ["a", "b"], "rows": [["a", "b"]]}
        good = "# Titre\n\nalpha beta gamma delta\n\n| a | b |\n| --- | --- |\n"
        r = run_hard.evaluate(case, good, "ok", False, None)
        self.assertEqual((r["verdict"], r["score"]), ("ok", 100.0))
        bad = run_hard.evaluate(case, "alpha beta bruit delta delta", "ok", False, None)
        self.assertEqual(bad["verdict"], "ko")
        self.assertTrue(any("bruit" in p for p in bad["problems"]))
        self.assertTrue(any("delta" in p for p in bad["problems"]))

    def test_vision_and_error_expectations(self):
        vis = {"must": ["texte du scan"], "expect": "vision"}
        self.assertEqual(run_hard.evaluate(vis, "", "ok", True, None)["verdict"], "vision")
        self.assertEqual(run_hard.evaluate(vis, "", "ok", False, None)["verdict"], "ko")
        self.assertEqual(run_hard.evaluate(vis, "texte du scan", "ok", False, None)["verdict"], "ok")
        err = {"expect": "error"}
        self.assertEqual(run_hard.evaluate(err, "", "error", False, "fichier abîmé")["verdict"], "ok")
        self.assertEqual(run_hard.evaluate(err, "du texte", "ok", False, None)["verdict"], "ko")

    def test_reading_order_and_list_levels(self):
        case = {"order": ["un", "deux", "trois"], "levels": [["parent", 0], ["enfant", 1]]}
        ok = run_hard.evaluate(case, "un deux trois\n\n- parent\n  - enfant\n", "ok", False, None)
        self.assertEqual(ok["verdict"], "ok")
        wrong = run_hard.evaluate(case, "trois deux un\n\n- parent\n- enfant\n", "ok", False, None)
        self.assertNotEqual(wrong["verdict"], "ok")


if __name__ == "__main__":
    unittest.main()
