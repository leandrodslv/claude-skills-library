"""Briques de base : texte/Markdown, détection de format, sécurité, qualité, plan de sortie."""
import unittest
import zipfile

from common import Base
import fixtures as fx
from mdconv import util
from mdconv.core import Result
from mdconv.detect import detect
from mdconv.fmt_archive import expand_archive
from mdconv.quality import assess, lint_markdown
from mdconv.writer import InputFile, plan_outputs


class TextHelpers(unittest.TestCase):
    def test_escape_only_what_is_ambiguous(self):
        self.assertEqual(util.esc_inline("5 * 3 = 15"), "5 \\* 3 = 15")
        self.assertEqual(util.esc_inline("snake_case_name"), "snake_case_name")   # intra-mot : pas d'échappement
        self.assertEqual(util.esc_inline("_italique_"), "\\_italique\\_")
        self.assertEqual(util.esc_inline("[1]"), "[1]")                            # pas un lien : laissé lisible
        self.assertEqual(util.esc_inline("[a](b)"), "[a]\\(b)")
        self.assertEqual(util.esc_inline("a < b et <div>"), "a < b et \\<div>")

    def test_block_start_escape(self):
        self.assertEqual(util.esc_block_start("# pas un titre"), "\\# pas un titre")
        self.assertEqual(util.esc_block_start("1. pas une liste"), "1\\. pas une liste")
        self.assertEqual(util.esc_block_start("texte normal"), "texte normal")

    def test_table_and_cells(self):
        md = util.md_table([["a", "b"], ["1|2", "x\ny"]])
        self.assertEqual(md.split("\n")[1], "| --- | --- |")
        self.assertIn("1\\|2", md)
        self.assertIn("x<br>y", md)

    def test_fence_grows_when_code_contains_backticks(self):
        f = util.fence("```py\nx\n```", "md")
        self.assertTrue(f.startswith("````md"))

    def test_emphasis_hoists_whitespace(self):
        self.assertEqual(util.wrap_emphasis(" a ", True, False), " **a** ")
        self.assertEqual(util.wrap_emphasis("a", True, True), "**_a_**")
        self.assertEqual(util.wrap_emphasis("a", False, True, intraword=True), "*a*")
        self.assertEqual(util.wrap_emphasis("  ", True, False), "  ")

    def test_normalize_markdown_keeps_code_blocks(self):
        md = util.normalize_markdown("a  \n\n\n\nb\n```\nx   \n\n\n\ny\n```\n")
        self.assertEqual(md, "a\n\nb\n```\nx   \n\n\n\ny\n```\n")

    def test_decode_text_prefers_western_codepage_for_isolated_accents(self):
        self.assertEqual(util.decode_text("café crème à l'été".encode("cp1252"))[0], "café crème à l'été")
        self.assertEqual(util.decode_text("Привет мир, это тест кодировки".encode("cp1251"))[1], "cp1251")
        self.assertEqual(util.decode_text("héllo".encode("utf-8"))[1], "utf-8")

    def test_word_recall_ignores_markup_and_unicode_scripts(self):
        self.assertEqual(util.word_recall("m2 et H2O", "`m`² et H₂O"), 1.0)
        self.assertLess(util.word_recall("un deux trois quatre", "un deux"), 0.6)
        self.assertEqual(util.word_recall("", "n'importe quoi"), 1.0)

    def test_est_tokens_is_monotonic(self):
        self.assertLess(util.est_tokens("abc"), util.est_tokens("abc " * 100))


class Ciphers(Base):
    """AES et RC4 écrits en Python pur : vecteurs de test officiels (FIPS-197, RFC 6229)."""

    def test_aes_known_answers_and_cbc_round_trip(self):
        from mdconv.pdf_crypt import AES
        pt = bytes.fromhex("00112233445566778899aabbccddeeff")
        k128 = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        k192 = bytes.fromhex("000102030405060708090a0b0c0d0e0f1011121314151617")
        k256 = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
        for key, ct in ((k128, "69c4e0d86a7b0430d8cdb78070b4c55a"), (k192, "dda97ca4864cdfe06eaf70a0ec0d7191"), (k256, "8ea2b7ca516745bfeafc49904b496089")):
            self.assertEqual(AES(key).encrypt_block(pt).hex(), ct)
            self.assertEqual(AES(key).decrypt_block(bytes.fromhex(ct)), pt)
        data = bytes(range(256)) * 3
        iv = bytes(range(16))
        self.assertEqual(AES(k256).cbc_decrypt(iv, AES(k256).cbc_encrypt(iv, data)), data)

    def test_rc4_known_answer(self):
        from mdconv.pdf_crypt import rc4
        self.assertEqual(rc4(b"Key", b"Plaintext").hex().upper(), "BBF316E8D940AF0AD3")
        self.assertEqual(rc4(b"Wiki", b"pedia").hex().upper(), "1021BF0420")


class LegacyEncodings(Base):
    """Devinette d'encodage sans dépendance : chaque texte est encodé à l'ancienne puis relu."""
    SAMPLES = [
        ("cp1251", "Привет мир, это простой тест определения кодировки текста. Мы проверяем, что русский текст читается правильно."),
        ("koi8-r", "Привет мир, это простой тест определения кодировки текста. Мы проверяем, что русский текст читается правильно."),
        ("cp1253", "Αυτό είναι ένα απλό τεστ για τον έλεγχο της κωδικοποίησης του κειμένου στα ελληνικά."),
        ("cp1256", "هذا اختبار بسيط للتحقق من ترميز النص باللغة العربية في الملفات القديمة."),
        ("cp1255", "זהו מבחן פשוט לבדיקת קידוד הטקסט בעברית בקבצים ישנים."),
        ("cp932", "これは文字コードを判定するための簡単なテストです。日本語の文章を読み込みます。"),
        ("euc_jp", "これは文字コードを判定するための簡単なテストです。日本語の文章を読み込みます。"),
        ("gb18030", "这是一个用于检测文字编码的简单测试。我们需要确认中文内容能够被正确读取。"),
        ("big5", "這是一個用於檢測文字編碼的簡單測試。我們需要確認繁體中文內容能夠被正確讀取。"),
        ("cp949", "이것은 문자 인코딩을 확인하기 위한 간단한 테스트입니다. 한국어 문장을 올바르게 읽어야 합니다."),
    ]

    def test_stdlib_guess_recovers_non_latin_legacy_texts(self):
        from mdconv.encodings import guess_legacy_codepage
        for enc, text in self.SAMPLES:
            guess = guess_legacy_codepage(text.encode(enc))
            self.assertTrue(guess, enc)
            self.assertEqual(text.encode(enc).decode(guess), text, f"{enc} lu comme {guess}")

    def test_decode_text_gives_the_right_text_with_or_without_charset_normalizer(self):
        for enc, text in self.SAMPLES:
            self.assertEqual(util.decode_text(text.encode(enc))[0], text, enc)

    def test_central_european_and_turkish_are_told_apart_from_western(self):
        from mdconv.encodings import refine_western
        pl = "Zażółć gęślą jaźń — pchnąć w tę łódź jeża lub ośm skrzyń fig. Mężczyzna łączy słowa."
        tr = "Öğrenci şehirdeki güzel bahçede çalışıyor, ığdır'dan gelen arkadaşı yardım ediyor."
        fr = "Le cœur de la sœur bat fort ; l'œuvre coûte 12 £ — ça va, déjà, où ? ¿Qué? Naïve façade à l'été."
        self.assertEqual(refine_western(pl.encode("cp1250")), "cp1250")
        self.assertEqual(refine_western(tr.encode("cp1254")), "cp1254")
        self.assertEqual(refine_western(fr.encode("cp1252")), "cp1252")       # œ, £ et ¿ sont légitimes en français/espagnol
        self.assertEqual(util.decode_text(pl.encode("cp1250"))[0], pl)


class Detection(Base):
    def test_office_formats_by_content_not_extension(self):
        d = fx.make_docx(self.tmp / "renamed.dat", fx.para("x"))
        self.assertEqual(detect(d).fmt, "docx")
        p = fx.make_pptx(self.tmp / "s.bin", [fx.slide_xml("")])
        self.assertEqual(detect(p).fmt, "pptx")
        x = fx.make_xlsx(self.tmp / "t.xlsx", [("S", "<sheetData/>", "visible")])
        self.assertEqual(detect(x).fmt, "xlsx")

    def test_extension_mismatch_is_flagged(self):
        html = self.write("export.xls", "<html><body><table><tr><td>a</td></tr></table></body></html>")
        det = detect(html)
        self.assertEqual(det.fmt, "html")
        self.assertTrue(det.ext_mismatch)

    def test_text_sniffing(self):
        cases = {
            "a.svg": ('<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>', "svg"),
            "b.txt": ("<html><body>hi</body></html>", "html"),
            "c.json": ('{"a": 1}', "json"),
            "d.dat": ('{"nbformat": 4, "cells": []}', "ipynb"),
            "e.csv": ("a,b\n1,2\n", "csv"),
            "f.md": ("# titre\n", "md"),
            "g.py": ("print(1)\n", "code"),
            "h.xml": ('<?xml version="1.0"?><root><a/></root>', "xml"),
            "i.drawio": ('<mxfile><diagram/></mxfile>', "drawio"),
            "j.eml": ("From: a@b.c\nTo: d@e.f\nSubject: x\nDate: today\n\ncorps\n", "eml"),
        }
        for name, (content, fmt) in cases.items():
            self.assertEqual(detect(self.write(name, content)).fmt, fmt, name)

    def test_magic_bytes(self):
        self.assertEqual(detect(self.write("x.bin", b"%PDF-1.4\n...")).fmt, "pdf")
        self.assertEqual(detect(self.write("x.bin", fx.png())).fmt, "image")
        self.assertEqual(detect(self.write("x.bin", b"{\\rtf1 hello}")).fmt, "rtf")
        self.assertEqual(detect(self.write("x.bin", b"\x00\x01\x02" * 100)).fmt, "binary")
        self.assertEqual(detect(self.write("empty.txt", b"")).fmt, "empty")

    def test_odf_and_epub(self):
        odt = fx.make_odf(self.tmp / "a.odt", "application/vnd.oasis.opendocument.text", "<office:text><text:p>x</text:p></office:text>")
        self.assertEqual(detect(odt).fmt, "odt")
        epub = fx.make_epub(self.tmp / "b.epub", [("c", "<html><body><p>x</p></body></html>")])
        self.assertEqual(detect(epub).fmt, "epub")

    def test_plain_zip(self):
        z = fx.write_zip(self.tmp / "data.zip", {"a.txt": "hello"})
        self.assertEqual(detect(z).fmt, "zip")


class Security(Base):
    def test_xxe_and_entity_declarations_are_refused(self):
        body = fx.para("ok")
        p = fx.make_docx(self.tmp / "evil.docx", body)
        with zipfile.ZipFile(p) as z:
            files = {n: z.read(n) for n in z.namelist()}
        files["word/document.xml"] = files["word/document.xml"].replace(
            b"<w:document", b'<!DOCTYPE d [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><w:document', 1)
        with zipfile.ZipFile(p, "w") as z:
            for n, d in files.items():
                z.writestr(n, d)
        out = self.conv(p)
        self.assertIn(out.status, ("error", "unsupported"))
        self.assertNotIn("root:", out.body)

    def test_billion_laughs_is_refused(self):
        with self.assertRaises(util.UnsafeXML):
            util.parse_xml(b'<!DOCTYPE l [<!ENTITY a "aa"><!ENTITY b "&a;&a;">]><l>&b;</l>')

    def test_zip_size_cap(self):
        z = self.tmp / "bomb.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.bin", b"\0" * (5 << 20))
        with self.assertRaises(util.UnsafeArchive):
            util.SafeZip(z, max_total=1 << 20)

    def test_archive_extraction_ignores_path_traversal(self):
        z = self.tmp / "evil.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("../../escape.txt", "x")
            zf.writestr("ok/inner.txt", "y")
        dest = self.tmp / "dest"
        members = expand_archive(z, "zip", dest)
        for _name, path in members:
            self.assertTrue(str(path.resolve()).startswith(str(dest.resolve())))
        self.assertFalse((self.tmp.parent / "escape.txt").exists())

    def test_external_relationship_never_fetched(self):
        # une image liée en externe reste un lien : aucun accès réseau
        body = ('<w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" name="x" descr="distante"/><a:graphic><a:graphicData><pic:pic><pic:blipFill>'
                '<a:blip r:link="rId9"/></pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        rel = ('<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
               'Target="http://example.invalid/i.png" TargetMode="External"/>')
        md = self.md(fx.make_docx(self.tmp / "l.docx", body, rels=rel))
        self.assertMd(md, "![distante](http://example.invalid/i.png)")


class Quality(unittest.TestCase):
    def test_empty_output_scores_zero(self):
        self.assertEqual(assess(Result(markdown="")).value, 0.0)

    def test_recall_drives_score(self):
        r = Result(markdown="un deux", source_text="un deux trois quatre cinq six sept huit")
        self.assertLess(assess(r).value, 0.5)
        r2 = Result(markdown="un deux trois", source_text="un deux trois")
        self.assertEqual(assess(r2).value, 1.0)

    def test_scanned_pdf_signature(self):
        r = Result(markdown="<!-- page 1 -->\n\nx", units=10, unit_name="page")
        s = assess(r)
        self.assertLess(s.value, 0.5)
        self.assertTrue(any("scanné" in n for n in s.notes))

    def test_garbage_is_penalised(self):
        s = assess(Result(markdown="(cid:12) (cid:34) (cid:56) texte " * 3))
        self.assertLess(s.value, 0.9)

    def test_lint(self):
        self.assertIn("bloc de code non refermé", lint_markdown("```\nx"))
        self.assertTrue(lint_markdown("| a | b |\n| - | - |\n| 1 |\n"))
        self.assertEqual(lint_markdown("| a | b |\n| - | - |\n| 1 | 2 |\n"), [])


class Planning(unittest.TestCase):
    def test_same_stem_different_extension_gets_suffix(self):
        files = [InputFile(None, "d/a.docx"), InputFile(None, "d/a.pdf"), InputFile(None, "d/b.xlsx")]
        plan = {p.file.rel: p.out_md for p in plan_outputs(files)}
        self.assertEqual(plan["d/a.docx"], "d/a.docx.md")
        self.assertEqual(plan["d/a.pdf"], "d/a.pdf.md")
        self.assertEqual(plan["d/b.xlsx"], "d/b.md")

    def test_assets_dir_is_url_safe(self):
        files = [InputFile(None, "Rapport Été 2024.docx")]
        p = plan_outputs(files)[0]
        self.assertRegex(p.assets_dir, r"^[A-Za-z0-9_-]+_assets$")


if __name__ == "__main__":
    unittest.main()


class EngineIsolation(Base):
    def test_chatty_external_engine_cannot_pollute_stdout(self):
        import contextlib
        import io
        from mdconv import core
        from mdconv.core import EngineSpec, Result

        def chatty(path, ctx):
            print("=== bruit d'un moteur tiers ===")
            import sys
            print("avertissement", file=sys.stderr)
            return Result(markdown="Contenu utile", fmt="txt")

        spec = EngineSpec("txt", "chatty", chatty, kind="external", prio=1)
        core.engines_for("txt")            # force le chargement du registre
        core._REGISTRY["txt"].insert(0, spec)
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                res = self.conv(self.write("a.txt", "x"), external=True)
        finally:
            core._REGISTRY["txt"].remove(spec)
        self.assertIn("Contenu utile", res.body)
        self.assertEqual(out.getvalue() + err.getvalue(), "")
