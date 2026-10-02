"""--render : aperçus PNG des pages, diapositives et SVG (outils externes requis, sinon les tests sont ignorés)."""
import unittest

from common import Base, have
import fixtures as fx

from mdconv import external as ext


def _png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG")


class Previews(Base):
    def conv_render(self, path, **kw):
        return self.conv(path, external=True, render=True, **kw)

    def test_no_previews_without_the_flag_or_external_tools(self):
        p = fx.make_pdf(self.tmp / "a.pdf", [[(50, 700, "Un texte de quelques mots pour la page.")]])
        self.assertEqual(self.conv(p, external=True).ctx.previews, [])
        out = self.conv(p, external=False, render=True)
        self.assertEqual(out.ctx.previews, [])
        self.assertTrue(any("--render" in w for w in out.ctx.warnings))

    @unittest.skipUnless(have("pdftoppm") or ext.has_module("fitz") or ext.has_module("pypdfium2"), "aucun outil de rendu PDF")
    def test_pdf_pages_become_png_previews(self):
        p = fx.make_pdf(self.tmp / "b.pdf", [[(50, 700, "Page une avec assez de mots pour etre lisible.")], [(50, 700, "Page deux egalement lisible ici.")]])
        out = self.conv_render(p)
        self.assertEqual(out.ctx.previews, ["assets/apercu-001.png", "assets/apercu-002.png"])
        self.assertTrue(all(_png(out.assets[n.split("/")[-1]].data) for n in out.ctx.previews))
        self.assertNotMd(out.body, "apercu")       # les aperçus ne polluent pas le Markdown

    @unittest.skipUnless(have("rsvg-convert") or have("inkscape"), "aucun rendu SVG")
    def test_svg_preview(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="60"><rect width="120" height="60" fill="#3366cc"/><text x="10" y="35" fill="white">Bonjour</text></svg>'
        out = self.conv_render(self.write("s.svg", svg))
        self.assertEqual(out.ctx.previews, ["assets/apercu-001.png"])
        self.assertTrue(_png(out.assets["apercu-001.png"].data))

    @unittest.skipUnless(have("soffice") and have("pdftoppm"), "LibreOffice ou poppler absent")
    def test_office_document_is_rendered_through_libreoffice(self):
        if not ext.libreoffice_ok("writer"):
            self.skipTest("module Writer de LibreOffice non fonctionnel")
        p = fx.make_docx(self.tmp / "d.docx", fx.para("Titre", "Heading1") + fx.para("Un paragraphe de texte pour la page."))
        out = self.conv_render(p)
        self.assertEqual(out.ctx.previews, ["assets/apercu-001.png"])

    def test_previews_are_listed_in_report_with_absolute_paths(self):
        import contextlib
        import io
        import json
        from mdconv.cli import main

        if not (have("pdftoppm") or ext.has_module("fitz") or ext.has_module("pypdfium2")):
            self.skipTest("aucun outil de rendu PDF")
        d = self.tmp / "in"
        d.mkdir()
        fx.make_pdf(d / "c.pdf", [[(50, 700, "Une page avec quelques mots lisibles.")]])
        out = self.tmp / "out"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main(["-j", "1", str(d), "-o", str(out), "--render"])
        self.assertEqual(code, 0, err.getvalue())
        rep = json.loads((out / "_report.json").read_text(encoding="utf-8"))
        shot = rep["files"][0]["previews"][0]
        self.assertTrue(shot.endswith("c_assets/apercu-001.png"), shot)
        self.assertTrue(_png((out / "c_assets" / "apercu-001.png").read_bytes()))
        self.assertIn("Aperçus PNG (1 image(s))", err.getvalue())


if __name__ == "__main__":
    unittest.main()
