"""Tests de check_prd.py : l'exemple complet passe, chaque défaut introduit est détecté."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_prd  # noqa: E402

EX = ROOT / "examples" / "cantine"


class CheckPrd(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(EX, self.tmp / "ex")
        self.prd = self.tmp / "ex" / "prd.md"
        self.src = self.tmp / "ex" / "sources"

    def codes(self, mutate=None, level=None):
        if mutate:
            self.prd.write_text(mutate(self.prd.read_text(encoding="utf-8")), encoding="utf-8")
        res = check_prd.check(self.prd, self.src)
        return [c["code"] for c in res["constats"] if level is None or c["niveau"] == level]

    def test_example_is_clean(self):
        res = check_prd.check(self.prd, self.src)
        self.assertEqual(res["constats"], [])
        self.assertEqual(res["stats"]["FR"], 7)
        self.assertEqual(res["stats"]["FR_NFR_avec_source"], res["stats"]["FR_NFR_total"])

    def test_cli_exit_codes(self):
        def run(*a):
            return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_prd.py"), *a], capture_output=True, text=True)

        self.assertEqual(run(str(self.prd), "--sources", str(self.src), "--strict").returncode, 0)
        self.assertEqual(run(str(self.tmp / "absent.md")).returncode, 2)
        out = run(str(self.prd), "--sources", str(self.src), "--json")
        self.assertEqual(json.loads(out.stdout)["erreurs"], 0)
        self.prd.write_text(self.prd.read_text(encoding="utf-8").replace("(source : cahier-des-charges-cantine.md, § 3.1)", ""), encoding="utf-8")
        self.assertEqual(run(str(self.prd), "--sources", str(self.src)).returncode, 1)

    def test_requirement_without_source(self):
        c = self.codes(lambda t: t.replace(" (source : cahier-des-charges-cantine.md, § 3.1)", ""), "erreur")
        self.assertIn("sans-source", c)

    def test_assumption_only_is_warning(self):
        c = self.codes(lambda t: t.replace(" (source : cahier-des-charges-cantine.md, § 3.1)", " [ASSUMPTION: x]"))
        self.assertIn("hypothese-seule", c)

    def test_source_without_file_name(self):
        c = self.codes(lambda t: t.replace("(source : cahier-des-charges-cantine.md, § 3.1)", "(source : le client)"), "erreur")
        self.assertIn("source-sans-fichier", c)

    def test_cited_file_must_exist(self):
        c = self.codes(lambda t: t.replace("courriel-mairie.md, remarque 2", "fantome.md, § 1"), "erreur")
        self.assertIn("source-introuvable", c)

    def test_orphan_fr_outside_feature(self):
        c = self.codes(lambda t: t.replace("## 5. Non-objectifs", "#### FR-8 : Orphelin\nFait X. Réalise UJ-1. (source : courriel-mairie.md)\n\n## 5. Non-objectifs"), "erreur")
        self.assertIn("fr-orphelin", c)

    def test_empty_feature(self):
        c = self.codes(lambda t: t.replace("## 4bis.", "### 4.4 Vide\n**Description :** rien.\n\n## 4bis."), "erreur")
        self.assertIn("feature-vide", c)

    def test_unknown_reference(self):
        c = self.codes(lambda t: t.replace("Valide FR-1, FR-3, FR-6.", "Valide FR-1, FR-42."), "erreur")
        self.assertIn("ref-inconnue", c)

    def test_duplicate_and_gap_ids(self):
        c = self.codes(lambda t: t.replace("#### FR-3 :", "#### FR-2 :"), None)
        self.assertIn("dup-id", c)
        self.assertIn("gap-id", c)

    def test_epics_must_cover_every_fr(self):
        epics = "\n## Epics\n### Epic 1 — Réserver\nCouvre FR-1, FR-2, FR-3.\n### Epic 2 — Vide\nRien.\n"
        c = self.codes(lambda t: t + epics, "erreur")
        self.assertIn("epic-sans-fr", c)
        self.assertIn("fr-non-couvert", c)

    def test_unrealized_journey_and_unlinked_metric(self):
        c = self.codes(lambda s: s.replace("Réalise UJ-2.", "").replace("Valide FR-1, FR-2, FR-7.", ""))
        self.assertIn("uj-non-realise", c)
        self.assertIn("sm-sans-fr", c)

    def test_assumption_index_mismatch(self):
        c = self.codes(lambda t: t.replace("- SM-2 — indicateur « familles actives ».", ""))
        self.assertIn("assumption-index", c)

    def test_template_placeholder_left(self):
        c = self.codes(lambda t: t.replace("*Titre de travail — à confirmer.*", "{Product Name}"), "erreur")
        self.assertIn("placeholder", c)

    def test_missing_glossary_and_open_questions(self):
        c = self.codes(lambda s: s.replace("## 3. Glossaire", "## 3. Divers").replace("## 8. Questions ouvertes", "## 8. Suite"))
        self.assertIn("no-glossary", c)
        self.assertIn("no-open-questions", c)


if __name__ == "__main__":
    unittest.main()
