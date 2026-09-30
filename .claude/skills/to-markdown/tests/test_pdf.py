"""PDF : lecteur natif (mise en page, titres, colonnes, en-têtes/pieds), escalade OCR/vision, fichiers défectueux."""
import unittest
from pathlib import Path

from common import Base, have
import fixtures as fx

LOREM = ("Le traitement automatique des documents suppose de conserver la structure logique du texte afin que les "
         "lecteurs humains comme les modeles de langage puissent retrouver rapidement les informations utiles sans "
         "avoir a parcourir un flux desordonne de lignes coupees au hasard par la mise en page originale")


def wrap(text: str, per_line: int = 9):
    words = text.split()
    return [" ".join(words[i:i + per_line]) for i in range(0, len(words), per_line)]


def body(start_y: float, *paragraphs: str, x: float = 50, leading: float = 14):
    """Paragraphes de 12 pt séparés par une ligne vide."""
    items, y = [], start_y
    for para in paragraphs:
        for ln in wrap(para):
            items.append((x, y, ln))
            y -= leading
        y -= leading
    return items, y


class NativePdf(Base):
    def test_paragraphs_page_markers_and_running_header_footer_removal(self):
        pages = []
        for i in range(1, 4):
            items, _ = body(740, f"Premier paragraphe de la page {i}. " + LOREM, f"Second paragraphe de la page {i}. " + LOREM)
            pages.append([(50, 800, f"Rapport annuel 2024 - Page {i}"), (50, 40, "ACME confidentiel")] + items)
        out = self.conv(fx.make_pdf(self.tmp / "r.pdf", pages))
        md = out.body
        self.assertEqual(out.status, "ok")
        for i in (1, 2, 3):
            self.assertMd(md, f"<!-- page {i} -->", f"Premier paragraphe de la page {i}.", f"Second paragraphe de la page {i}.")
        self.assertNotMd(md, "Rapport annuel", "ACME confidentiel")
        self.assertRegex(md, r"originale\n\nSecond paragraphe de la page 1")      # saut de paragraphe rétabli d'après l'espacement
        self.assertEqual((out.result.units, out.result.units_found), (3, 3))

    def test_headings_from_font_size_and_bold(self):
        pages = []
        for i, (big, mid, small) in enumerate([("Titre du document", "1. Introduction", "Contexte"),
                                              ("Suite du document", "2. Méthode", "Données")], 1):
            y = 780
            items = [(50, y, big, 24, True), (50, y - 40, mid, 16, True)]
            para, y = body(y - 70, LOREM)
            items += para + [(50, y, small, 12, True)]
            para2, _ = body(y - 20, f"Texte de la sous-partie numéro {i} avec quelques mots seulement.")
            pages.append(items + para2)
        md = self.md(fx.make_pdf(self.tmp / "h.pdf", pages))
        self.assertMd(md, "# Titre du document", "## 1. Introduction", "### Contexte", "# Suite du document", "## 2. Méthode", "### Données")

    def test_bold_table_header_is_not_a_heading(self):
        items = [(50, 780, "Nom", 12, True), (250, 780, "Prix", 12, True), (400, 780, "Quantité", 12, True)]
        para, _ = body(740, LOREM)
        md = self.md(fx.make_pdf(self.tmp / "t.pdf", [items + para]))
        self.assertNotMd(md, "# Nom")

    def test_two_columns_are_read_column_by_column(self):
        left = [f"gauche {k:02d} " + " ".join(["mot"] * 6) for k in range(22)]
        right = [f"droite {k:02d} " + " ".join(["mot"] * 6) for k in range(22)]
        items = [(50, 780 - 14 * k, t) for k, t in enumerate(left)] + [(320, 780 - 14 * k, t) for k, t in enumerate(right)]
        md = self.md(fx.make_pdf(self.tmp / "c.pdf", [items]))
        self.assertLess(md.index("gauche 21"), md.index("droite 00"))
        self.assertLess(md.index("droite 00"), md.index("droite 21"))

    def test_chapter_titles_are_not_taken_for_running_headers(self):
        pages = []
        for i in range(1, 5):
            items, _ = body(700, f"Contenu unique de la section {i}. " + LOREM)
            pages.append([(50, 760, f"Chapitre {i}"), (50, 40, f"Page {i} sur 4")] + items)
        md = self.md(fx.make_pdf(self.tmp / "ch.pdf", pages))
        for i in range(1, 5):
            self.assertMd(md, f"Chapitre {i}")
        self.assertNotMd(md, "Page 1 sur 4", "sur 4")

    def test_pages_made_only_of_repeated_lines_are_kept(self):
        same = [(50, 700, "Formulaire type - ne rien écrire ici"), (50, 680, "Nom : ____________"), (50, 660, "Date : ____________")]
        out = self.conv(fx.make_pdf(self.tmp / "form.pdf", [same, same, same]))
        self.assertMd(out.body, "Formulaire type", "Nom :", "Date :")
        self.assertFalse(out.ctx.vision)          # le texte est là : aucune lecture visuelle à demander

    def test_tj_arrays_hex_strings_and_word_gaps(self):
        stream = (b"BT /F1 12 Tf 50 700 Td [(Hel) 20 (lo) -300 (World)] TJ ET\n"
                  b"BT /F1 12 Tf 50 680 Td <4D6F6E> Tj ( ) Tj <646520E9E9> Tj ET")
        md = self.md(fx.make_pdf(self.tmp / "tj.pdf", [stream], compress=False))
        self.assertMd(md, "Hello World", "Mon de éé")

    def test_metadata_title_used_unless_generic(self):
        page = [(50, 700, "Un texte de quelques mots pour la page.")]
        self.assertTrue(self.md(fx.make_pdf(self.tmp / "t1.pdf", [page], title="Mon rapport")).startswith("# Mon rapport"))
        self.assertFalse(self.md(fx.make_pdf(self.tmp / "t2.pdf", [page], title="Microsoft Word - note.docx")).startswith("# "))

    def test_image_only_pdf_requests_visual_reading(self):
        out = self.conv(fx.make_pdf(self.tmp / "scan.pdf", [[], []], image_only=True), ocr="off")
        self.assertEqual(out.status, "needs_vision")
        self.assertMd(out.body, "<!-- page 1 -->", "[À COMPLÉTER : lecture visuelle]** page 1", "page 2")
        self.assertEqual(out.ctx.vision[0].pages, "1-2")

    def test_only_empty_pages_of_a_mixed_pdf_are_flagged(self):
        pages = [[(50, 700, "Cette page contient du texte normal et lisible pour le test.")], []]
        out = self.conv(fx.make_pdf(self.tmp / "mix.pdf", pages), ocr="off")
        self.assertEqual(out.ctx.vision[0].pages, "2")
        self.assertMd(out.body, "texte normal et lisible", "[À COMPLÉTER : lecture visuelle]** page 2")
        self.assertNotMd(out.body, "** page 1")

    def test_encrypted_truncated_and_empty_files_fail_cleanly(self):
        good = fx.make_pdf(self.tmp / "g.pdf", [[(50, 700, "Bonjour tout le monde")]]).read_bytes()
        enc = good.replace(b"/Root 1 0 R", b"/Root 1 0 R /Encrypt << /Filter /Standard /V 1 /R 2 /O (x) /U (y) /P -4 >>")
        out = self.conv(self.write("enc.pdf", enc))
        self.assertEqual(out.status, "unsupported")
        self.assertIn("protégé", out.error)
        self.assertIn(self.conv(self.write("trunc.pdf", good[:300])).status, ("unsupported", "error"))
        self.assertEqual(self.conv(self.write("empty.pdf", b"")).status, "unsupported")


@unittest.skipUnless(have("tesseract") and have("pdftoppm"), "tesseract ou poppler absent")
class OcrPdf(Base):
    """Un « scan » fabriqué en rastérisant un PDF de texte : l'OCR doit retrouver les mots."""

    LINES = ["Facture numero 4821 du 12 mars 2024", "Client : Societe Durand et Fils", "Montant total a payer : 1250 euros",
             "Merci de regler avant la fin du mois"]

    def scan(self, name: str, pages: int = 1):
        import subprocess
        text_pdf = fx.make_pdf(self.tmp / f"{name}-text.pdf", [[(60, 760 - 40 * k, ln, 20) for k, ln in enumerate(self.LINES)]] * pages)
        pngs = []
        for i in range(1, pages + 1):
            base = self.tmp / f"{name}-{i}"
            subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", str(i), "-l", str(i), "-singlefile", str(text_pdf), str(base)], check=True)
            pngs.append(Path(f"{base}.png").read_bytes())
        return fx.make_scan_pdf(self.tmp / f"{name}.pdf", pngs)

    def test_scanned_pages_are_read_by_ocr(self):
        out = self.conv(self.scan("s"), external=True, ocr_lang="eng")
        self.assertMd(out.body, "<!-- page 1 (OCR", "Facture", "4821", "Durand", "1250")
        self.assertFalse(out.ctx.vision)
        self.assertTrue(any("lue(s) par OCR" in w for w in out.ctx.warnings))

    def test_ocr_is_not_repeated_when_several_engines_try_the_same_scan(self):
        from unittest import mock
        from mdconv import external
        calls = []
        real = external.ocr_png

        def counting(png, lang="", timeout=120):
            calls.append(1)
            return real(png, lang, timeout=timeout)

        pdf = self.scan("m", pages=2)
        with mock.patch.object(external, "ocr_png", counting):
            out = self.conv(pdf, external=True, ocr_lang="eng", compare=True, engines=["pdftotext", "pdflite"])
        self.assertEqual(len(out.attempts), 2, out.attempts)
        self.assertEqual(len(calls), 2)          # 2 pages, 2 moteurs : 2 lectures OCR et non 4

    def test_ocr_off_leaves_visual_reading_markers(self):
        out = self.conv(self.scan("o"), external=True, ocr="off")
        self.assertEqual(out.status, "needs_vision")
        self.assertTrue(out.ctx.vision)


if __name__ == "__main__":
    unittest.main()
