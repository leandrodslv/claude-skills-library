"""Ligne de commande de bout en bout : dossiers, index, rapport, cache incrémental, archives, sortie standard, --check."""
import contextlib
import io
import json
import os
import unittest
import zipfile
from pathlib import Path

from common import Base
import fixtures as fx

from mdconv.cli import main


class Cli(Base):
    def run_cli(self, *args, expect: int = 0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--no-external", "-j", "1", *map(str, args)])
        self.assertEqual(code, expect, f"code {code}\n--- stdout ---\n{out.getvalue()}\n--- stderr ---\n{err.getvalue()}")
        return out.getvalue(), err.getvalue()

    def inputs(self) -> Path:
        d = self.tmp / "entrants"
        (d / "tableaux").mkdir(parents=True)
        fx.make_docx(d / "rapport.docx", fx.para("Rapport", "Heading1") + fx.para("Contenu du rapport."))
        fx.make_xlsx(d / "tableaux" / "chiffres.xlsx", [("Ventes", '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Zone</t></is></c><c r="B1" t="inlineStr"><is><t>CA</t></is></c></row>'
                                                        '<row r="2"><c r="A2" t="inlineStr"><is><t>Nord</t></is></c><c r="B2"><v>12</v></c></row></sheetData>', "visible")])
        (d / "tableaux" / "notes.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        (d / "page.html").write_text("<html><body><main><h1>Page</h1><p>Texte de la page.</p></main></body></html>", encoding="utf-8")
        (d / "lisez-moi.txt").write_text("Bonjour le monde.\n", encoding="utf-8")
        fx.make_pptx(d / "deck.pptx", [fx.slide_xml(fx.sp(2, "T", ["Ouverture"], ph="title"))])
        (d / "mystere.bin").write_bytes(bytes(range(256)) * 8)
        (d / ".cache").write_text("caché", encoding="utf-8")
        (d / "~$verrou.docx").write_bytes(b"x")
        with zipfile.ZipFile(d / "lot.zip", "w") as z:
            z.writestr("a.txt", "Fichier A")
            z.writestr("sub/b.md", "# Fichier B\n")
            z.writestr("../evil.txt", "ne doit pas sortir")
        return d

    def test_folder_run_mirrors_tree_and_writes_report_and_index(self):
        src, out = self.inputs(), self.tmp / "md"
        _o, err = self.run_cli(src, "-o", out)
        for rel in ("rapport.md", "tableaux/chiffres.md", "tableaux/notes.md", "page.md", "lisez-moi.md", "deck.md", "lot/a.md", "lot/sub/b.md"):
            self.assertTrue((out / rel).exists(), f"{rel} manquant : {sorted(p.relative_to(out).as_posix() for p in out.rglob('*.md'))}")
        self.assertFalse((out / "mystere.md").exists())
        self.assertFalse(list(out.rglob("*verrou*")) or list(out.rglob(".cache*.md")))
        self.assertFalse((self.tmp / "evil.txt").exists() or (src.parent / "evil.txt").exists())     # zip-slip : jamais hors du dossier
        rep = json.loads((out / "_report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["summary"]["by_status"].get("unsupported"), 1)
        self.assertGreaterEqual(rep["summary"]["files"], 9)
        by_source = {f["source"]: f for f in rep["files"]}
        self.assertEqual(by_source["rapport.docx"]["output"], "rapport.md")
        self.assertEqual(by_source["mystere.bin"]["status"], "unsupported")
        index = (out / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("[rapport.md](rapport.md)", index)
        self.assertIn("mystere.bin", index)
        self.assertIn("non convertis", index.lower())
        self.assertIn("1 non géré(s)", err)

    def test_front_matter_modes(self):
        f = fx.make_docx(self.tmp / "doc.docx", fx.para("Bonjour"))
        out = self.tmp / "o"
        self.run_cli(f, "-o", out)
        text = (out / "doc.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nsource: doc.docx\nformat: docx\n"), text[:200])
        self.assertIn("converter: mdconv/native", text)
        self.run_cli(f, "-o", self.tmp / "o2", "--frontmatter", "none")
        self.assertFalse((self.tmp / "o2" / "doc.md").read_text(encoding="utf-8").startswith("---"))
        self.run_cli(f, "-o", self.tmp / "o3", "--frontmatter", "full")
        self.assertRegex((self.tmp / "o3" / "doc.md").read_text(encoding="utf-8"), r"sha256: [0-9a-f]{64}")

    def test_incremental_cache_skips_unchanged_files_and_force_reconverts(self):
        src, out = self.inputs(), self.tmp / "md"
        self.run_cli(src, "-o", out)
        target = out / "rapport.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nmodif manuelle\n", encoding="utf-8")
        _o, err = self.run_cli(src, "-o", out)
        self.assertIn("inchangé(s), ignoré(s)", err)
        self.assertIn("modif manuelle", target.read_text(encoding="utf-8"))           # rien n'a été réécrit
        rep = json.loads((out / "_report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["summary"]["by_status"].get("unchanged"), 6)      # les membres d'archive sont ré-extraits à chaque passage
        self.run_cli(src, "-o", out, "--force")
        self.assertNotIn("modif manuelle", target.read_text(encoding="utf-8"))
        (src / "rapport.docx").write_bytes(fx.make_docx(self.tmp / "v2.docx", fx.para("Version deux")).read_bytes())
        self.run_cli(src, "-o", out)
        self.assertIn("Version deux", target.read_text(encoding="utf-8"))               # source modifiée : reconvertie

    def test_same_stem_files_do_not_overwrite_each_other(self):
        d = self.tmp / "in"
        d.mkdir()
        fx.make_docx(d / "note.docx", fx.para("Depuis Word"))
        (d / "note.txt").write_text("Depuis le texte", encoding="utf-8")
        out = self.tmp / "o"
        self.run_cli(d, "-o", out)
        self.assertIn("Depuis Word", (out / "note.docx.md").read_text(encoding="utf-8"))
        self.assertIn("Depuis le texte", (out / "note.txt.md").read_text(encoding="utf-8"))

    def test_stdout_mode_prints_markdown_only(self):
        f = fx.make_docx(self.tmp / "s.docx", fx.para("Titre", "Heading1") + fx.para("Corps du texte."))
        out, _err = self.run_cli(f, "-o", "-", "--frontmatter", "none")
        self.assertEqual(out.strip(), "# Titre\n\nCorps du texte.")
        (self.tmp / "autre.txt").write_text("deux fichiers", encoding="utf-8")
        _out, err = self.run_cli(self.tmp, "-o", "-", expect=2)         # plusieurs fichiers : refusé
        self.assertIn("qu'à un seul fichier", err)

    def test_combined_and_only_combined(self):
        src = self.tmp / "in"
        src.mkdir()
        (src / "a.txt").write_text("Alpha", encoding="utf-8")
        (src / "b.txt").write_text("Bravo", encoding="utf-8")
        out = self.tmp / "o"
        self.run_cli(src, "-o", out, "--combined")
        combined = (out / "combined.md").read_text(encoding="utf-8")
        self.assertLess(combined.index("Alpha"), combined.index("Bravo"))
        self.assertIn("<!-- source: a.txt -->", combined)
        self.assertTrue((out / "a.md").exists())
        out2 = self.tmp / "o2"
        self.run_cli(src, "-o", out2, "--only-combined")
        self.assertTrue((out2 / "combined.md").exists())
        self.assertFalse((out2 / "a.md").exists())

    def test_include_exclude_filters(self):
        src = self.inputs()
        out = self.tmp / "o"
        self.run_cli(src, "-o", out, "--include", "*.docx", "--include", "*.csv", "--exclude", "~$*")
        self.assertEqual(sorted(p.relative_to(out).as_posix() for p in out.rglob("*.md") if p.name != "INDEX.md"), ["rapport.md", "tableaux/notes.md"])

    def test_in_place_writes_next_to_sources(self):
        d = self.tmp / "in"
        d.mkdir()
        (d / "x.txt").write_text("Texte", encoding="utf-8")
        self.run_cli(d / "x.txt", "--in-place")
        self.assertIn("Texte", (d / "x.md").read_text(encoding="utf-8"))
        self.assertFalse((d / "_report.json").exists())

    def test_process_pool_gives_same_result(self):
        d = self.tmp / "in"
        d.mkdir()
        for i in range(6):
            (d / f"f{i}.txt").write_text(f"Contenu numéro {i}", encoding="utf-8")
        out = self.tmp / "o"
        errbuf = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errbuf):
            code = main(["--no-external", "-j", "3", str(d), "-o", str(out)])
        self.assertEqual(code, 0, errbuf.getvalue())
        for i in range(6):
            self.assertIn(f"Contenu numéro {i}", (out / f"f{i}.md").read_text(encoding="utf-8"))

    def test_vision_items_are_reported_and_check_flags_unresolved_markers(self):
        d = self.tmp / "in"
        d.mkdir()
        fx.make_pdf(d / "scan.pdf", [[], []], image_only=True)
        out = self.tmp / "o"
        _o, err = self.run_cli(d, "-o", out, "--ocr", "off")
        self.assertIn("À TRAITER PAR LECTURE VISUELLE", err)
        rep = json.loads((out / "_report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["summary"]["by_status"], {"needs_vision": 1})
        self.assertEqual(rep["vision_needed"][0]["pages"], "1-2")
        text, _ = self.run_cli("--check", out, expect=1)
        self.assertIn("2 passage(s) à décrire par lecture visuelle non traité(s)", text)
        md = out / "scan.md"
        done = md.read_text(encoding="utf-8").replace("> **[À COMPLÉTER : lecture visuelle]** page 1 — aucun texte extractible (page scannée ou image).", "Page 1 : facture n° 42.")
        done = done.replace("> **[À COMPLÉTER : lecture visuelle]** page 2 — aucun texte extractible (page scannée ou image).", "Page 2 : conditions générales.")
        md.write_text(done, encoding="utf-8")
        text, _ = self.run_cli("--check", out)
        self.assertIn("aucun problème détecté", text)

    def test_check_detects_broken_links_and_bad_characters(self):
        out = self.tmp / "o"
        out.mkdir()
        (out / "a.md").write_text("# A\n\n![x](assets/manquante.png) et �\n", encoding="utf-8")
        text, _ = self.run_cli("--check", out, expect=1)
        self.assertIn("introuvable", text)
        self.assertIn("illisible", text)

    def test_chunking_splits_long_documents_at_headings(self):
        d = self.tmp / "in"
        d.mkdir()
        (d / "long.md").write_text("".join(f"## Section {i}\n\n" + ("mot " * 300) + "\n\n" for i in range(6)), encoding="utf-8")
        out = self.tmp / "o"
        self.run_cli(d, "-o", out, "--chunk-tokens", "800")
        parts = sorted((out / "long_chunks").glob("part-*.md"))
        self.assertGreaterEqual(len(parts), 3)
        self.assertIn("## Section 0", parts[0].read_text(encoding="utf-8"))
        idx = json.loads((out / "long_chunks" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(idx["parts"]), len(parts))

    def test_doctor_reports_native_core_as_json(self):
        out, _ = self.run_cli("--doctor", "--json")
        data = json.loads(out)
        levels = {r["format"]: r["niveau"] for r in data["formats"]}
        self.assertEqual(levels["docx"], "natif")
        self.assertEqual(levels["svg"], "natif")
        self.assertIn("capabilities", data)

    def test_special_characters_in_file_names_give_valid_links(self):
        d = self.tmp / "in"
        (d / "Sous dossier (v2)").mkdir(parents=True)
        fx.make_docx(d / "Compte rendu #3 (final).docx", fx.para("Titre", "Heading1") + fx.para(fx.drawing("rId7", "Schéma")),
                     media={"pic.png": fx.png()}, rels=fx.image_rel("rId7", "pic.png"))
        (d / "Sous dossier (v2)" / "note % 100.txt").write_text("Texte", encoding="utf-8")
        out = self.tmp / "o"
        self.run_cli(d, "-o", out, "--combined")
        index = (out / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("(Compte%20rendu%20%233%20%28final%29.md)", index)
        self.assertIn("(Sous%20dossier%20%28v2%29/note%20%25%20100.md)", index)
        text, _ = self.run_cli("--check", out)
        self.assertIn("aucun problème détecté", text)
        combined = (out / "combined.md").read_text(encoding="utf-8")
        self.assertIn("![Schéma](Compte-rendu-3-final_assets/img-01.png)", combined)

    def test_output_is_utf8_even_when_the_console_encoding_is_not(self):
        import subprocess
        import sys
        f = fx.make_docx(self.tmp / "acc.docx", fx.para("Élève → ≈ 3 € ‹ok›"))
        script = Path(__file__).resolve().parent.parent / "scripts" / "convert.py"
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        done = subprocess.run([sys.executable, str(script), "--no-external", "-o", "-", "--frontmatter", "none", str(f)], capture_output=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
        self.assertEqual(done.stdout.decode("utf-8").strip(), "Élève → ≈ 3 € ‹ok›")
        doctor = subprocess.run([sys.executable, str(script), "--doctor"], capture_output=True, env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr.decode("utf-8", "replace"))
        self.assertIn("✓", doctor.stdout.decode("utf-8"))

    def test_missing_input_and_empty_folder(self):
        _o, err = self.run_cli(self.tmp / "nexiste-pas", expect=1)
        self.assertIn("introuvable", err)
        (self.tmp / "vide").mkdir()
        _o, err = self.run_cli(self.tmp / "vide", expect=1)
        self.assertIn("Aucun fichier à convertir", err)

    def test_images_are_extracted_next_to_markdown(self):
        d = self.tmp / "in"
        d.mkdir()
        fx.make_docx(d / "img.docx", fx.para(fx.drawing("rId7", "Schéma")), media={"pic.png": fx.png()}, rels=fx.image_rel("rId7", "pic.png"))
        out = self.tmp / "o"
        self.run_cli(d, "-o", out)
        md = (out / "img.md").read_text(encoding="utf-8")
        self.assertIn("![Schéma](img_assets/img-01.png)", md)
        self.assertTrue((out / "img_assets" / "img-01.png").read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
