"""Corrections issues de la batterie « cas extrêmes » (benchmark/extreme) et d'essais sur de vrais documents.

Chaque test reproduit un défaut constaté : PDF modernes à flux d'objets illisibles sans poppler, plantage sur un
substitut Unicode isolé, HTML au charset faux, UTF-16 sans BOM, fichiers Office tronqués ou au XML cassé.
"""
import json
import struct
import zlib

from common import Base
from fixtures import make_docx, make_pptx, make_xlsx, para, slide_xml, sp

from mdconv.cli import main
from mdconv.detect import detect
from mdconv.pdf_lite import PdfDoc, extract_pages
from mdconv.util import decode_text, nul_tolerable, scrub_surrogates, utf16_without_bom


def objstm_pdf(text: str) -> bytes:
    """PDF 1.5 « moderne » : catalogue, pages et police dans un flux d'objets, annuaire en flux /XRef."""
    inner = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    body, head, off = b"", "", 0
    for num, o in inner.items():
        head += f"{num} {off} "
        body += o + b" "
        off += len(o) + 1
    stm = zlib.compress(head.encode() + body)
    content = f"BT /F1 12 Tf 50 780 Td ({text}) Tj ET".encode()
    out = bytearray(b"%PDF-1.5\n")
    o5 = len(out)
    out += b"5 0 obj\n<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream\nendobj\n"
    o6 = len(out)
    out += b"6 0 obj\n<< /Type /ObjStm /N 4 /First %d /Filter /FlateDecode /Length %d >>\nstream\n" % (len(head), len(stm)) + stm + b"\nendstream\nendobj\n"
    o7 = len(out)
    rows = [(0, 0, 255)] + [(2, 6, i) for i in range(4)] + [(1, o5, 0), (1, o6, 0), (1, o7, 0)]
    xr = zlib.compress(b"".join(struct.pack(">BIB", *r) for r in rows))
    out += b"7 0 obj\n<< /Type /XRef /Size 8 /W [1 4 1] /Root 1 0 R /Filter /FlateDecode /Length %d >>\nstream\n" % len(xr) + xr + b"\nendstream\nendobj\n"
    out += b"startxref\n%d\n%%%%EOF\n" % o7
    return bytes(out)


class ModernPdf(Base):
    def test_pdf_with_object_streams_is_read_natively(self):
        p = self.write("moderne.pdf", objstm_pdf("Texte-dans-un-flux-d-objets"))
        pages, _ = extract_pages(p.read_bytes())
        self.assertIn("Texte-dans-un-flux-d-objets", " ".join(pages))
        self.assertMd(self.md(p), "Texte-dans-un-flux-d-objets")

    def test_an_integer_value_is_never_an_object_number(self):
        doc = PdfDoc(objstm_pdf("x"))
        self.assertEqual(doc.get(5), 5)          # « /N 5 » ou « /Widths [5 …] » sont des valeurs
        self.assertIsInstance(doc.obj(5), object)
        self.assertNotEqual(doc.obj(5), 5)       # alors que l'objet n° 5 existe bel et bien


class SurrogatesAndEncodings(Base):
    def test_lone_surrogate_in_json_does_not_crash_the_batch(self):
        src = self.write("mal-forme.json", '{"lone": "ab\\ud83dcd", "ok": "\\ud83d\\ude00 fin"}')
        good = self.write("bon.txt", "autre fichier du lot")
        out = self.tmp / "sortie"
        self.assertIn(main(["--no-external", "-j", "1", "-q", str(src), str(good), "-o", str(out)]), (0, 1))
        self.assertTrue((out / "bon.md").exists())
        md = (out / "mal-forme.md").read_text(encoding="utf-8")
        self.assertIn("fin", md)
        self.assertNotRegex(md, "[\ud800-\udfff]")
        json.loads((out / "_report.json").read_text(encoding="utf-8"))

    def test_scrub_surrogates_keeps_valid_text(self):
        self.assertEqual(scrub_surrogates("a\ud83db😀é"), "a�b😀é")

    def test_html_with_a_wrong_charset_declaration_is_decoded_by_content(self):
        p = self.write("faux-charset.html", '<html><head><meta charset="utf-8"></head><body><p>Café crème, à la carte</p></body></html>'.encode("latin-1"))
        self.assertMd(self.md(p), "Café crème, à la carte")

    def test_utf16_without_bom_is_text(self):
        for enc in ("utf-16-le", "utf-16-be"):
            raw = "Texte UTF-16 sans BOM — é ü 你好".encode(enc)
            self.assertEqual(utf16_without_bom(raw), enc)
            self.assertEqual(decode_text(raw)[0], "Texte UTF-16 sans BOM — é ü 你好")
            self.assertEqual(detect(self.write(f"u-{enc}.txt", raw)).fmt, "txt")

    def test_text_sprinkled_with_nul_bytes_is_text_but_binaries_are_not(self):
        self.assertMd(self.md(self.write("nul.txt", b"AVANT\x00\x00\x00milieu\x00APRES\n")), "AVANT", "APRES")
        self.assertFalse(nul_tolerable(bytes(range(256)) * 16))
        self.assertFalse(nul_tolerable(b"PK\x03\x04" + bytes(200) + bytes(range(1, 200)) * 4))


class DamagedOffice(Base):
    def test_truncated_docx_is_rescued_and_flagged(self):
        full = make_docx(self.tmp / "entier.docx", para("TITRE-DEBUT", "Heading1") + "".join(para(f"Paragraphe {i} " + "mot " * 40) for i in range(400)))
        raw = full.read_bytes()
        p = self.write("tronque.docx", raw[: int(len(raw) * 0.6)])
        self.assertEqual(detect(p).fmt, "docx")
        out = self.conv(p)
        self.assertEqual(out.status, "warn")
        self.assertEqual(out.result.engine, "rescue")
        self.assertMd(out.body, "TITRE-DEBUT", "Paragraphe 0 ", "Paragraphe 100 ")
        self.assertNotMd(out.body, "Paragraphe 399 ")
        self.assertTrue(any("tronqué" in w or "abîmé" in w for w in out.ctx.warnings), out.ctx.warnings)

    def test_docx_with_malformed_xml_gives_back_its_text(self):
        full = make_docx(self.tmp / "ok.docx", para("DEBUT-SAUVE") + para("SUITE-SAUVEE"))
        import zipfile
        bad = self.tmp / "casse.docx"
        with zipfile.ZipFile(full) as zin, zipfile.ZipFile(bad, "w") as zout:
            for n in zin.namelist():
                data = zin.read(n)
                if n == "word/document.xml":
                    data = data.replace(b"</w:body>", b"<w:oups>").replace(b"</w:document>", b"")
                zout.writestr(n, data)
        out = self.conv(bad)
        self.assertEqual(out.result.engine, "rescue")
        self.assertMd(out.body, "DEBUT-SAUVE", "SUITE-SAUVEE")

    def test_truncated_pptx_and_xlsx_are_rescued(self):
        slides = [slide_xml(sp(2, f"t{i}", [f"Titre diapo {i}"], ph="title") + sp(3, f"b{i}", [f"point {i} " + "x " * 60], ph="body")) for i in range(1, 80)]
        pp = make_pptx(self.tmp / "d.pptx", slides)
        raw = pp.read_bytes()
        out = self.conv(self.write("d-tronque.pptx", raw[: int(len(raw) * 0.6)]))
        self.assertEqual(out.result.engine, "rescue")
        self.assertMd(out.body, "Titre diapo 1", "Slide 1 ")
        rows = "".join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>LIGNE-{i:04d}</t></is></c><c r="B{i}"><v>{i}</v></c></row>' for i in range(1, 3000))
        xl = make_xlsx(self.tmp / "t.xlsx", [("Données", f"<sheetData>{rows}</sheetData>", "visible")])
        raw = xl.read_bytes()
        out = self.conv(self.write("t-tronque.xlsx", raw[: int(len(raw) * 0.6)]))
        self.assertEqual(out.result.engine, "rescue")
        self.assertMd(out.body, "LIGNE-0001")

    def test_intact_files_never_go_through_rescue(self):
        out = self.conv(make_docx(self.tmp / "sain.docx", para("Bonjour")))
        self.assertEqual(out.result.engine, "native")
        self.assertEqual(out.status, "ok")

    def test_zip_bomb_is_not_mistaken_for_a_damaged_file(self):
        import zipfile
        bomb = self.tmp / "bombe.docx"
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            z.writestr("word/document.xml", b"<w:document><w:body><w:p><w:r><w:t>" + b"A" * (80 << 20) + b"</w:t></w:r></w:p></w:body></w:document>")
        out = self.conv(bomb)
        self.assertIn(out.status, ("unsupported", "error"))
        self.assertNotIn("rescue", [a["engine"] for a in out.attempts if a.get("status") == "ok"])

    def test_garbage_is_still_refused(self):
        import os
        out = self.conv(self.write("hasard.docx", os.urandom(4096)))
        self.assertIn(out.status, ("unsupported", "error"))


class RescueRefusesHostileXml(Base):
    def test_rescue_never_works_on_a_file_declaring_entities(self):
        import zipfile
        bad = self.tmp / "xxe.docx"
        secret = self.write("secret.txt", "SECRET-XXE-4242")
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("word/document.xml", f'<!DOCTYPE d [<!ENTITY x SYSTEM "file://{secret}">]><w:document><w:body><w:p><w:r><w:t>AVANT &x; APRES</w:t></w:r></w:p></w:body></w:document>')
        out = self.conv(bad)
        self.assertIn(out.status, ("unsupported", "error"))
        self.assertNotIn("SECRET-XXE-4242", out.body)
        self.assertNotIn("rescue", [a["engine"] for a in out.attempts if a.get("status") == "ok"])


class ErrorMessages(Base):
    def test_short_error_keeps_the_exception_line_of_a_traceback(self):
        from mdconv.util import short_error
        tb = b'Traceback (most recent call last):\n  File "/usr/bin/markitdown", line 10, in <module>\n    main()\nValueError: docx illisible\n'
        self.assertEqual(short_error(tb), "ValueError: docx illisible")
        self.assertEqual(short_error(b"couldn't parse docx file: DocxError\nplus de details"), "couldn't parse docx file: DocxError")
        self.assertEqual(short_error(b""), "sortie d'erreur vide")

    def test_external_failure_message_is_one_line_and_full_detail_is_kept_for_verbose(self):
        from unittest import mock

        from mdconv.core import Unsupported
        from mdconv.fmt_pdf import pdf_pdftotext
        err = b'Traceback (most recent call last):\n  File "x.py", line 1, in <module>\nValueError: boum\n'
        with mock.patch("mdconv.fmt_pdf.ext.run", return_value=(1, b"", err)):
            with self.assertRaises(Unsupported) as cm:
                pdf_pdftotext(self.write("a.pdf", b"%PDF-1.4"), mock.Mock(opts=mock.Mock(timeout=5)))
        self.assertEqual(str(cm.exception), "pdftotext a échoué : ValueError: boum")
        self.assertIn("Traceback", cm.exception.detail)


class TruncationIsReported(Base):
    def test_cut_table_is_in_warnings_and_in_a_structured_field(self):
        rows = "".join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>L{i}</t></is></c><c r="B{i}"><v>{i}</v></c></row>' for i in range(1, 1501))
        src = make_xlsx(self.tmp / "gros.xlsx", [("Données", f"<sheetData>{rows}</sheetData>", "visible")])
        out = self.conv(src)
        t = out.truncated
        self.assertEqual((t["kept"], t["total"], t["tables"]), (1000, 1500, 1))
        self.assertTrue(t["full_data"] and t["full_data"][0].endswith(".csv"), t)
        self.assertTrue(any("tronqué" in w and "1500" in w for w in out.ctx.warnings), out.ctx.warnings)

    def test_report_json_and_readable_report_mention_it(self):
        src = self.write("long.csv", "id,v\n" + "".join(f"{i},{i * 2}\n" for i in range(1800)))
        out_dir = self.tmp / "sortie"
        main(["--no-external", "-j", "1", "-q", str(src), "-o", str(out_dir)])
        entry = json.loads((out_dir / "_report.json").read_text(encoding="utf-8"))["files"][0]
        self.assertEqual((entry["truncated"]["kept"], entry["truncated"]["total"]), (1000, 1800))
        self.assertTrue(any("tronqué" in w for w in entry["warnings"]))
        self.assertIn("tronqué", (out_dir / "RAPPORT.md").read_text(encoding="utf-8"))

    def test_nothing_is_reported_when_nothing_was_cut(self):
        self.assertEqual(self.conv(self.write("court.csv", "a,b\n1,2\n3,4\n")).truncated, {})


class EmphasisIsUnambiguous(Base):
    def test_touching_bold_and_italic_use_html_tags(self):
        from mdconv.inline import Fmt, Span, render_spans
        md = render_spans([Span("t", "gras", Fmt(bold=True)), Span("t", "italique", Fmt(italic=True)), Span("t", "normal")])
        self.assertEqual(md, "<strong>gras</strong><em>italique</em>normal")
        self.assertNotIn("***", md)

    def test_separated_emphasis_keeps_plain_markdown(self):
        from mdconv.inline import Fmt, Span, render_spans
        md = render_spans([Span("t", "gras ", Fmt(bold=True)), Span("t", "puis "), Span("t", "italique", Fmt(italic=True))])
        self.assertEqual(md, "**gras** puis _italique_")

    def test_docx_runs(self):
        body = ('<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>gras</w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t>italique</w:t></w:r><w:r><w:t>normal</w:t></w:r></w:p>')
        md = self.md(make_docx(self.tmp / "f.docx", body))
        self.assertMd(md, "<strong>gras</strong><em>italique</em>normal")


class PdfEngineChoice(Base):
    def test_native_reader_only_wins_when_it_reads_the_same_text_in_the_same_order(self):
        from mdconv.pipeline import _same_reading
        text = " ".join(f"mot{i}" for i in range(200))
        self.assertTrue(_same_reading(text, text))
        two_columns = " ".join(f"gauche{i}" for i in range(100)) + " " + " ".join(f"droite{i}" for i in range(100))
        interleaved = " ".join(f"{a} {b}" for a, b in zip((f"gauche{i}" for i in range(100)), (f"droite{i}" for i in range(100))))
        self.assertFalse(_same_reading(two_columns, interleaved))       # mêmes mots, ordre perdu
        self.assertFalse(_same_reading(text, text + " " + " ".join(f"bruit{i}" for i in range(80))))     # texte en trop
        self.assertFalse(_same_reading(text, ""))


class FormHeadings(Base):
    def test_a_line_that_goes_on_is_not_a_heading(self):
        from mdconv.textflow import _heading_of, looks_unfinished
        self.assertIsNone(_heading_of("4 Exemptions (codes apply only to", "certain entities, not individuals"))
        self.assertTrue(looks_unfinished("Exemptions (codes apply only to"))
        self.assertTrue(looks_unfinished("Name of the entity and"))
        self.assertTrue(looks_unfinished("Introduction", "suite de la phrase"))
        self.assertFalse(looks_unfinished("2.1 Méthode", "Nous avons mesuré"))
        self.assertIsNotNone(_heading_of("2.1 Méthode de calcul", "Nous avons mesuré"))

    def test_form_numbers_join_their_labels(self):
        from mdconv.textflow import join_form_fields, reflow
        raw = "1\n\nName of entity/individual\n\n2\n\nBusiness name, if different\n\n3\n\nCheck the box\n\n4\nExemptions (codes apply only to\ncertain entities)"
        lines, fields = join_form_fields(raw.split("\n"))
        self.assertIn("2 Business name, if different", lines)
        self.assertEqual(len(fields), 4)
        md = reflow(raw)
        self.assertIn("1 Name of entity/individual", md)
        self.assertNotIn("#", md)

    def test_a_lone_page_number_is_not_a_form_field(self):
        from mdconv.textflow import join_form_fields
        lines, fields = join_form_fields(["Texte", "", "12", "", "Suite du texte", "", "13", "", "Autre suite"])
        self.assertEqual(fields, set())


class HtmlCleanup(Base):
    def test_wikidata_edit_icons_are_dropped_and_urls_cleaned(self):
        html = ('<html><body><table><tr><td>Version 2004<img alt="Voir et modifier les données sur Wikidata" '
                'src="//upload.wikimedia.org/x/Blue_pencil.svg/20px-Blue_pencil.svg.png?utm_source=fr.wikipedia.org&utm_campaign=parser"></td></tr></table>'
                '<p><img alt="Logo" src="//thumb.wikimedia.org/a/logo.png?utm_source=x&w=250&utm_medium=y"> '
                '<a href="https://exemple.org/page?id=3&utm_campaign=z&fbclid=abc">lien</a></p></body></html>')
        md = self.md(self.write("w.html", html))
        self.assertNotIn("Wikidata", md)
        self.assertNotIn("utm_", md)
        self.assertNotIn("fbclid", md)
        self.assertMd(md, "![Logo](https://thumb.wikimedia.org/a/logo.png?w=250)", "](https://exemple.org/page?id=3)")
        self.assertNotRegex(md, r"\]\(//")


class RescueMarksWhatIsCut(Base):
    def test_xlsx_drops_an_unclosed_cell_and_flags_the_last_row(self):
        from mdconv.fmt_rescue import _xlsx
        sheet = (b'<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>a</t></is></c><c r="B1"><v>1</v></c></row>'
                 b'<row r="2"><c r="A2" t="inlineStr"><is><t>b</t></is></c><c r="B2"><v>2</v></c></row>'
                 b'<row r="3"><c r="A3" t="inlineStr"><is><t>coupe-ici</t></is></c><c r="B3"><v>12')
        md = _xlsx({"xl/worksheets/sheet1.xml": sheet})
        self.assertMd(md, "coupe-ici", "dernière ligne possiblement incomplète")
        self.assertNotIn("12", md.split("coupe-ici")[1].split("dernière")[0])         # la valeur « 12 » est coupée : écartée
        self.assertIn("| b | 2 |", md)

    def test_docx_flags_the_last_paragraph_when_the_file_stops_inside_it(self):
        from mdconv.fmt_rescue import _docx
        xml = b'<w:document><w:body><w:p><w:r><w:t>complet</w:t></w:r></w:p><w:p><w:r><w:t>coupe en plein mo'
        md = _docx({"word/document.xml": xml})
        self.assertMd(md, "complet", "coupe en plein mo ⚠ [fin du fichier")
        self.assertNotIn("complet ⚠", md)

    def test_complete_docx_part_is_not_flagged(self):
        from mdconv.fmt_rescue import _docx
        xml = b'<w:document><w:body><w:p><w:r><w:t>entier</w:t></w:r></w:p></w:body></w:document>'
        self.assertNotIn("⚠", _docx({"word/document.xml": xml}))


class DeepNesting(Base):
    def test_absurd_nesting_is_refused_with_a_clear_message(self):
        out = self.conv(self.write("profond.json", "[" * 5000 + '"fond"' + "]" * 5000))
        if out.status in ("error", "unsupported"):
            self.assertTrue(any("imbrication" in str(a.get("detail", "")) for a in out.attempts), out.attempts)
            self.assertNotIn("RecursionError", out.error)
        else:                                     # ou bien le contenu est lu : aucun plantage dans les deux cas
            self.assertIn("fond", out.body)
