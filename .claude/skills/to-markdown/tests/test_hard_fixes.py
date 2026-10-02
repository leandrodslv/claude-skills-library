"""Corrections issues de la batterie de documents difficiles : chaque test s'appuie sur un fichier versionné de benchmark/hard/corpus."""
import json
import re
import shutil
from pathlib import Path

from common import Base

from mdconv.cli import main
from mdconv.encodings import refine_western
from mdconv.inline import alt_clean, is_placeholder_alt
from mdconv.util import decode_text

CORPUS = Path(__file__).resolve().parent.parent / "benchmark" / "hard" / "corpus"


def md_rows(md: str):
    return [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in md.splitlines() if ln.lstrip().startswith("|") and not re.match(r"^\s*\|[\s:|-]+\|\s*$", ln)]


class Encodings(Base):
    def test_polish_iso_8859_2_is_told_apart_from_cp1250(self):
        t = "Zażółć gęślą jaźń, pójdę do łóżka"
        self.assertEqual(decode_text(t.encode("iso8859_2"))[0], t)
        self.assertEqual(decode_text(t.encode("cp1250"))[0], t)
        self.assertEqual(refine_western("Café à 5 € crème brûlée".encode("cp1252")), "cp1252")


class PlaceholderAlt(Base):
    def test_file_names_and_automatic_names_are_not_descriptions(self):
        for t in ("_tmp.png", "Picture 1", "Image12", "IMG_2041", "photo.jpeg", "Content Placeholder 2"):
            self.assertTrue(is_placeholder_alt(t), t)
            self.assertEqual(alt_clean(t), "")
        for t in ("Ruche sur un toit lyonnais", "Logo ACME", "Figure 3 : courbe de charge"):
            self.assertFalse(is_placeholder_alt(t), t)
            self.assertEqual(alt_clean(t), t)

    def test_slide_that_is_only_an_unnamed_picture_is_flagged_even_without_extracting_images(self):
        for images in ("skip", "extract"):
            out = self.conv(CORPUS / "pptx" / "diapositive-image.pptx", images=images)
            self.assertEqual(out.status, "needs_vision", images)
            self.assertIn("À COMPLÉTER", out.body)
        self.assertNotIn("_tmp.png", self.conv(CORPUS / "pptx" / "diapositive-image.pptx").body)


class Email(Base):
    def run_cli(self, *args):
        return main(["--no-external", "-j", "1", "-q", "--frontmatter", "none", *map(str, args)])

    def test_html_part_with_a_table_wins_and_short_attachments_are_read_inline(self):
        out_dir = self.tmp / "o"
        self.run_cli(CORPUS / "web" / "email-multipartie.eml", "-o", out_dir)
        md = (out_dir / "email-multipartie.md").read_text(encoding="utf-8")
        self.assertIn("| Bilan budgétaire | Nicolas |", md)                     # tableau de la version HTML
        self.assertEqual(md.count("Merci de confirmer votre présence avant mardi"), 1)   # pas de doublon texte + HTML
        self.assertIn("### Pièce jointe : notes-preparation.txt", md)
        self.assertIn("Vérifier le budget restant : 18 400 euros", md)
        self.assertIn("Le devis numéro 2025-0417", md)                           # e-mail transféré en pièce jointe
        self.assertFalse((out_dir / "email-multipartie_attachments").exists())    # rien à lire à part : tout est dans le mail

    def test_plain_part_is_kept_when_html_adds_nothing(self):
        eml = self.tmp / "m.eml"
        eml.write_text("Subject: Test\nFrom: a@b.fr\nMIME-Version: 1.0\nContent-Type: multipart/alternative; boundary=XX\n\n--XX\nContent-Type: text/plain; charset=utf-8\n\n"
                       "Bonjour, ceci est un message simple sans aucune mise en forme particulière.\n--XX\nContent-Type: text/html; charset=utf-8\n\n"
                       "<p>Bonjour, ceci est un message simple sans aucune mise en forme particulière.</p>\n--XX--\n", encoding="utf-8")
        out = self.conv(eml)
        self.assertEqual(out.body.count("ceci est un message simple"), 1)


class Pdf(Base):
    def test_rotated_page_keeps_its_lines_and_reading_order(self):
        md = self.conv(CORPUS / "pdf" / "page-pivotee.pdf").body
        self.assertIn("Page pivotée de 90 degrés : tableau des écarts", md)
        self.assertRegex(md, r"Écart de calibrage : 0,8 mm\s+Écart de planéité : 1,2 mm\s+Écart angulaire")
        self.assertNotIn("écartsÉcart", md)                                       # lignes collées : le bug d'origine

    def test_table_without_borders_with_right_aligned_numbers(self):
        rows = md_rows(self.conv(CORPUS / "pdf" / "tableau-sans-bordures.pdf").body)
        self.assertEqual(rows[0], ["Produit", "Référence", "Prix unitaire", "Stock", "Statut"])
        self.assertIn(["Scie circulaire", "SCI-1187", "89,50 €", "0", "Rupture"], rows)
        self.assertEqual(len(rows), 6)

    def test_ruled_table_with_merged_cells_keeps_values_on_their_row(self):
        rows = md_rows(self.conv(CORPUS / "pdf" / "tableau-bordures-fusionnees.pdf").body)
        self.assertIn(["Nord", "410", "455", "900"], rows)
        self.assertIn(["Sud", "380", "402", "820"], rows)
        self.assertTrue(any(r[0] == "Nord" and "Détail Lille" in r[1] for r in rows))

    def test_running_header_and_footer_are_dropped_even_in_two_columns(self):
        md = self.conv(CORPUS / "pdf" / "article-deux-colonnes.pdf").body
        self.assertNotIn("Journal of Examples", md)
        self.assertNotIn("Page 1 sur 3", md)
        self.assertEqual(len(re.findall(r"(?m)^#\s+Mesure de la dérive thermique en milieu industriel$", md)), 1)     # titre sur deux lignes : un seul titre

    def test_truncated_pdf_is_reported_as_damaged_not_as_scanned(self):
        out = self.conv(CORPUS / "data" / "pdf-tronque.pdf")
        self.assertEqual(out.status, "unsupported")
        self.assertIn("abîmé ou tronqué", out.error)
        self.assertNotIn("scanné", out.error)

    def test_partly_truncated_pdf_gives_page_one_and_marks_the_lost_page(self):
        out = self.conv(CORPUS / "data" / "pdf-tronque-partiel.pdf")
        self.assertIn("Mesure de la dérive thermique", out.body)
        self.assertIn("PAGE ILLISIBLE", out.body)
        self.assertNotIn("page scannée", out.body)
        self.assertTrue(any("tronqué" in w for w in out.ctx.warnings))


class Legacy(Base):
    def test_doc_tables_keep_rows_and_blank_cells(self):
        md = self.conv(CORPUS / "legacy" / "tableaux-fusionnes.doc").body
        rows = md_rows(md)
        self.assertIn(["Europe", "1 204", "1 310", "5 100"], rows)
        self.assertIn(["Asie", "980", "1 022", "4 200"], rows)

    def test_ppt_tables_and_notes_are_rebuilt(self):
        out = self.conv(CORPUS / "legacy" / "groupes-graphique-notes.ppt")
        rows = md_rows(out.body)
        self.assertIn(["Pôle", "Budget", "Effectif"], rows)
        self.assertIn(["Produit", "420 k€", "12"], rows)
        self.assertIn("Note de l'orateur : insister sur la progression de l'export au T4", out.body)


class ConsensusPick(Base):
    def test_agreement_prefers_the_text_the_other_engines_share(self):
        from mdconv.pipeline import _agreement

        good = "Page pivotée tableau des écarts calibrage planéité"
        self.assertGreater(_agreement(good, good), 0.99)
        self.assertLess(_agreement(good, "2168p £'0 aujejnBue wu 7'T ap 11227"), 0.2)


# garde-fou : le corpus doit être présent pour que ces tests aient un sens
class CorpusPresent(Base):
    def test_corpus_files_exist(self):
        manifest = json.loads((CORPUS.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(manifest), 45)
        _ = shutil


class SmallFixes(Base):
    def test_xml_mixed_content_is_flattened_and_epub_footnotes_survive(self):
        md = self.conv(CORPUS / "data" / "xml-espaces-de-noms.xml").body
        self.assertIn("Voir la fiche technique avant toute commande.", md)
        epub = self.conv(CORPUS / "web" / "livre-chapitres-notes.epub").body
        self.assertIn("Note : la maison fut vendue en 1952.", epub)
