"""Mesures du banc d'essai (fonctions pures) : un convertisseur qui perd ou ajoute du contenu doit être noté."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmark"))
import metrics  # noqa: E402
from corpus import Truth  # noqa: E402


class Metrics(unittest.TestCase):
    TRUTH = Truth(text="Titre\nUn paragraphe de test\nAlpha\nBeta\nNom\nValeur\nx\n42",
                  headings=["Titre"], cells=["Nom", "Valeur", "x", "42"], items=["Alpha", "Beta"],
                  links=[("le site", "https://exemple.fr/a")])
    GOOD = ("# Titre\n\nUn paragraphe de test\n\n- Alpha\n- Beta\n\n| Nom | Valeur |\n| --- | --- |\n| x | 42 |\n\n"
            "Voir [le site](https://exemple.fr/a)\n")

    def test_perfect_output(self):
        r = metrics.score_output(self.TRUTH, self.GOOD)
        for k in ("recall", "headings", "tables", "lists", "links"):
            self.assertEqual(r[k], 100.0, k)

    def test_lost_text_lowers_recall_and_extra_text_lowers_precision(self):
        lost = metrics.score_output(self.TRUTH, self.GOOD.replace("Un paragraphe de test", ""))
        self.assertLess(lost["recall"], 100)
        noisy = metrics.score_output(self.TRUTH, self.GOOD + "\nbruit parasite répété répété répété\n")
        self.assertEqual(noisy["recall"], 100.0)
        self.assertLess(noisy["precision"], 100)

    def test_structure_must_be_markdown_structure(self):
        flat = "Titre\nUn paragraphe de test\nAlpha\nBeta\nNom Valeur\nx 42\nle site\n"
        r = metrics.score_output(self.TRUTH, flat)
        self.assertEqual(r["recall"], 100.0)
        self.assertEqual((r["headings"], r["tables"], r["lists"], r["links"]), (0.0, 0.0, 0.0, 0.0))

    def test_front_matter_urls_and_list_markers_are_not_content(self):
        text = "---\ntitle: x\n---\n# Titre\n\n1. Alpha\n2. Beta\n\nhttps://exemple.fr/zzz\n"
        r = metrics.score_output(Truth(text="Titre\nAlpha\nBeta", headings=["Titre"], items=["Alpha", "Beta"]), text)
        self.assertEqual(r["precision"], 100.0)
        self.assertEqual(r["lists"], 100.0)

    def test_not_applicable_is_none(self):
        r = metrics.score_output(Truth(text="a b"), "a b")
        self.assertIsNone(r["tables"])
        self.assertIsNone(r["links"])


if __name__ == "__main__":
    unittest.main()
