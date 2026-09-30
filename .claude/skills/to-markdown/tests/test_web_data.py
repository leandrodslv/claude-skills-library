"""HTML, EPUB, SVG/diagrammes, données tabulaires et structurées, e-mails, texte brut."""
import base64
import json
import unittest

from common import Base
import fixtures as fx

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Ma page</title>
<style>.x{color:red}</style><script>var secret=1;</script></head><body>
<nav><a href="/">Accueil</a> <a href="/a">Autre</a></nav>
<div class="cookie-banner">Nous utilisons des cookies</div>
<main><article>
<h1>Titre principal</h1><p>Un paragraphe avec <strong>gras</strong>, <em>italique</em>, <code>code</code> et un <a href="https://ex.org">lien</a>.</p>
<h2>Liste</h2><ul><li>un</li><li>deux<ul><li>sous</li></ul></li></ul><ol><li>premier</li><li>second</li></ol>
<table><thead><tr><th>Nom</th><th>Valeur</th></tr></thead><tbody><tr><td>a</td><td>1</td></tr></tbody></table>
<pre><code class="language-python">print("x")
</code></pre>
<blockquote>Citation</blockquote>
%s
</article></main><footer>© 2024 Société</footer></body></html>"""


def data_uri_png() -> str:
    return "data:image/png;base64," + base64.b64encode(fx.png(48, 48)).decode()


class Html(Base):
    def test_structure_is_preserved_and_page_noise_removed(self):
        md = self.md(self.write("a.html", PAGE % ""))
        self.assertMd(md, "# Titre principal", "**gras**, _italique_, `code`", "[lien](https://ex.org)", "## Liste",
                      "- un\n- deux\n  - sous", "1. premier\n2. second", "| Nom | Valeur |", "| a | 1 |",
                      '```python\nprint("x")\n```', "> Citation")
        self.assertNotMd(md, "secret", "color:red", "Accueil", "cookies", "Société")

    def test_full_mode_keeps_navigation_and_footer(self):
        md = self.md(self.write("a.html", PAGE % ""), html_mode="full")
        self.assertMd(md, "Accueil", "Société")

    def test_embedded_image_extracted_or_skipped(self):
        p = self.write("img.html", PAGE % f'<img src="{data_uri_png()}" alt="Logo">')
        out = self.conv(p)
        self.assertMd(out.body, "![Logo](assets/img-01.png)")
        self.assertEqual(len(out.assets), 1)
        self.assertNotMd(self.md(p, images="skip"), "![")

    def test_layout_tables_are_flattened(self):
        html = "<html><body><table><tr><td><h2>Colonne A</h2><p>Texte A</p></td><td><h2>Colonne B</h2><p>Texte B</p></td></tr></table></body></html>"
        md = self.md(self.write("l.html", html))
        self.assertMd(md, "## Colonne A", "Texte A", "## Colonne B", "Texte B")
        self.assertNotMd(md, "| ---")

    def test_declared_latin1_charset(self):
        raw = "<html><head><meta charset='iso-8859-1'><title>é</title></head><body><p>Café crème à l'été</p></body></html>".encode("latin-1")
        self.assertMd(self.md(self.write("latin.html", raw)), "Café crème à l'été")

    def test_table_cells_with_lists_and_breaks(self):
        html = "<html><body><table><tr><th>Étape</th><th>Détail</th></tr><tr><td>1</td><td><ul><li>a</li><li>b</li></ul></td></tr><tr><td>2</td><td>ligne<br>deux</td></tr></table></body></html>"
        md = self.md(self.write("tc.html", html))
        self.assertMd(md, "| Étape | Détail |", "| 1 | • a<br>• b |", "| 2 | ligne<br>deux |")     # pas de liste dans une cellule

    def test_no_data_lost_on_plain_fragment(self):
        out = self.conv(self.write("f.html", "<p>Un</p><p>Deux</p><p>Trois</p>"))
        self.assertEqual(out.score.recall, 1.0)


class Epub(Base):
    def test_chapters_follow_spine_and_nest_under_book_title(self):
        page = "<html xmlns='http://www.w3.org/1999/xhtml'><head><title>c</title></head><body><h1>%s</h1><p>%s</p></body></html>"
        p = fx.make_epub(self.tmp / "b.epub", [("1", page % ("Chapitre un", "Texte un.")), ("2", page % ("Chapitre deux", "Texte deux."))])
        md = self.md(p)
        self.assertMd(md, "# Mon livre", "_Auteur · fr_", "## Chapitre un", "Texte un.", "## Chapitre deux")
        self.assertLess(md.index("Chapitre un"), md.index("Chapitre deux"))
        self.assertEqual(md.count("\n# "), 0)     # un seul H1 : le titre du livre


class Svg(Base):
    def test_text_in_reading_order_with_title(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><title>Mon schéma</title>'
               '<text x="10" y="150">Bas</text><text x="10" y="30">Haut</text><text x="10" y="90">Milieu</text></svg>')
        md = self.md(self.write("t.svg", svg))
        self.assertMd(md, "# Mon schéma", "- Haut\n- Milieu\n- Bas")

    def test_hidden_text_is_ignored(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="10">visible</text>'
               '<text x="1" y="20" style="display:none">caché</text><g visibility="hidden"><text x="1" y="30">invisible</text></g></svg>')
        md = self.md(self.write("h.svg", svg))
        listed = md.split("## Source SVG")[0]        # la source simplifiée, elle, reste fidèle au fichier
        self.assertMd(listed, "- visible")
        self.assertNotMd(listed, "caché", "invisible")

    def test_icon_without_text_requests_visual_reading(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2L2 22h20z"/><circle cx="12" cy="12" r="4"/></svg>'
        out = self.conv(self.write("icon.svg", svg))
        self.assertEqual(out.status, "needs_vision")
        self.assertMd(out.body, "[À COMPLÉTER", "```svg")
        self.assertEqual(len(out.ctx.vision), 1)

    def test_graphviz_output_becomes_mermaid(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="200pt" height="100pt" viewBox="0 0 200 100">'
               '<g id="graph0" class="graph" transform="translate(4 96)"><title>G</title>'
               '<g id="node1" class="node"><title>a</title><ellipse cx="30" cy="-70" rx="27" ry="18"/><text text-anchor="middle" x="30" y="-66">Début</text></g>'
               '<g id="node2" class="node"><title>b</title><ellipse cx="130" cy="-70" rx="27" ry="18"/><text text-anchor="middle" x="130" y="-66">Fin</text></g>'
               '<g id="edge1" class="edge"><title>a&#45;&gt;b</title><path d="M57,-70C75,-70 90,-70 103,-70"/><polygon points="103,-73 113,-70 103,-67"/></g></g></svg>')
        out = self.conv(self.write("g.svg", svg))
        self.assertMd(out.body, "```mermaid", "flowchart TD", 'n1["Début"]', 'n2["Fin"]', "n1 --> n2")
        self.assertEqual(out.status, "ok")           # les identifiants internes <title> ne comptent pas comme du texte perdu
        self.assertNotMd(out.body, "## Texte (ordre de lecture)")     # étiquettes déjà dans le diagramme

    def test_drawio_becomes_mermaid_with_edge_labels(self):
        xml = ('<mxfile><diagram name="Page-1"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
               '<mxCell id="a" value="Client" vertex="1" parent="1"><mxGeometry x="0" y="0" width="80" height="40" as="geometry"/></mxCell>'
               '<mxCell id="b" value="Serveur" vertex="1" parent="1"><mxGeometry x="200" y="0" width="80" height="40" as="geometry"/></mxCell>'
               '<mxCell id="e" edge="1" source="a" target="b" value="HTTP" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>'
               '</root></mxGraphModel></diagram></mxfile>')
        md = self.md(self.write("d.drawio", xml))
        self.assertMd(md, "```mermaid", 'n1["Client"]', 'n2["Serveur"]', "n1 -->|HTTP| n2")

    def test_svgz_is_decompressed(self):
        import gzip
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="10">compressé</text></svg>'
        p = self.tmp / "z.svgz"
        p.write_bytes(gzip.compress(svg.encode()))
        from mdconv.detect import detect
        self.assertEqual(detect(p).fmt, "gz")      # le CLI l'ouvre puis convertit le SVG contenu (voir test_cli)


class Tabular(Base):
    def test_semicolon_csv_in_cp1252_with_embedded_newline_and_pipe(self):
        raw = "nom;age;ville\nAlice;30;Paris\nBob;25;Lyon\n\"Zoé | X\";41;\"Saint\nÉtienne\"\n".encode("cp1252")
        md = self.md(self.write("fr.csv", raw))
        self.assertMd(md, "3 ligne(s) × 3 colonne(s) · séparateur ';' · encodage cp1252", "| nom | age | ville |",
                      "| Alice | 30 | Paris |", "| Zoé \\| X | 41 | Saint<br>Étienne |")

    def test_utf8_bom_and_tsv(self):
        md = self.md(self.write("t.tsv", "﻿a\tb\n1\t2\n".encode("utf-8")))
        self.assertMd(md, "| a | b |", "| 1 | 2 |")
        self.assertNotMd(md, "﻿")

    def test_large_csv_is_truncated_with_sidecar(self):
        rows = "\n".join(f"{i};ligne {i}" for i in range(1, 61))
        out = self.conv(self.write("big.csv", "id;txt\n" + rows + "\n"), table_rows=10)
        self.assertMd(out.body, "50 ligne(s) de plus dans le fichier source", "| 1 | ligne 1 |", "| id | entier | 60 | 1 … 60 |")
        self.assertNotMd(out.body, "| 60 | ligne 60 |")
        self.assertFalse(out.assets)          # la source est déjà un CSV complet : pas de copie inutile

    def test_json_records_become_table_with_flattened_columns(self):
        data = [{"id": 1, "name": "Alice", "tags": ["a", "b"]}, {"id": 2, "name": "Bob", "extra": {"x": 1}}]
        md = self.md(self.write("list.json", json.dumps(data)))
        self.assertMd(md, "2 enregistrement(s)", "| id | name | tags | extra.x |", '| 1 | Alice | ["a","b"] |  |', "| 2 | Bob |  | 1 |")

    def test_json_object_stays_a_fenced_document(self):
        md = self.md(self.write("obj.json", json.dumps({"name": "cfg", "server": {"port": 8080}})))
        self.assertMd(md, "```json", '"port": 8080')

    def test_very_large_json_array_is_streamed_with_bounded_memory(self):
        from unittest import mock
        from mdconv import fmt_data
        items = [{"id": i, "note": 'texte avec ] , } et "guillemets" \\ ' + str(i), "sub": {"k": [i, i + 1]}} for i in range(3000)]
        p = self.write("gros.json", json.dumps(items, ensure_ascii=False, indent=1))
        # seuil et taille de bloc minuscules : force la lecture en flux et les éléments coupés entre deux blocs
        with mock.patch.object(fmt_data, "BIG_JSON", 1000), mock.patch.object(fmt_data, "_CHUNK", 257):
            out = self.conv(p, table_rows=10)
        self.assertMd(out.body, "3000 enregistrement(s)", "| id | note | sub.k |", "| 9 | texte avec ] , } et \"guillemets\"", "| [9,10] |",
                      "2990 enregistrement(s) de plus")
        self.assertNotMd(out.body, "| 10 |")
        self.assertTrue(any("lecture en flux" in w for w in out.ctx.warnings))
        with mock.patch.object(fmt_data, "BIG_JSON", 1000), mock.patch.object(fmt_data, "_CHUNK", 257):
            bad = self.conv(self.write("casse.json", json.dumps(items)[:-40] + "}}}"))
        self.assertEqual(bad.status, "unsupported")

    def test_very_large_jsonl_is_streamed(self):
        from unittest import mock
        from mdconv import fmt_data
        lines = "\n".join(json.dumps({"a": i, "b": "x" * (i % 7)}) for i in range(2500))
        with mock.patch.object(fmt_data, "BIG_JSON", 1000):
            out = self.conv(self.write("gros.jsonl", lines + "\n"), table_rows=5)
        self.assertMd(out.body, "2500 enregistrement(s)", "| a | b |", "2495 enregistrement(s) de plus")

    def test_jsonl(self):
        md = self.md(self.write("l.jsonl", '{"a":1,"b":"x"}\n{"a":2,"b":"y"}\n'))
        self.assertMd(md, "| a | b |", "| 1 | x |", "| 2 | y |")

    def test_notebook_cells_and_outputs(self):
        b64 = base64.b64encode(fx.png(48, 48)).decode()
        nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
              "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Analyse\n", "Un *texte*."]},
                        {"cell_type": "code", "metadata": {}, "execution_count": 1, "source": ["print('bonjour')\n", "2+2"],
                         "outputs": [{"output_type": "stream", "name": "stdout", "text": ["bonjour\n"]},
                                     {"output_type": "execute_result", "execution_count": 1, "metadata": {}, "data": {"text/plain": ["4"]}},
                                     {"output_type": "display_data", "metadata": {}, "data": {"image/png": b64, "text/plain": ["<Figure>"]}}]}]}
        out = self.conv(self.write("n.ipynb", json.dumps(nb)))
        self.assertMd(out.body, "# Analyse\nUn *texte*.", "```python\nprint('bonjour')\n2+2\n```", "**Sortie :**", "bonjour", "**Résultat :**", "![sortie](assets/sortie-01.png)")
        self.assertEqual(len(out.assets), 1)

    def test_yaml_and_xml_are_fenced(self):
        self.assertMd(self.md(self.write("c.yaml", "name: demo\nports:\n  - 80\n  - 443\n")), "```yaml", "name: demo")
        md = self.md(self.write("x.xml", '<?xml version="1.0"?><catalog><book id="1"><title>Un</title></book></catalog>'))
        self.assertMd(md, "racine `catalog`", "```xml", "<title>Un</title>")


class Mail(Base):
    EML = """From: Alice <alice@ex.org>
To: Bob <bob@ex.org>
Subject: =?utf-8?q?R=C3=A9union_demain?=
Date: Mon, 15 Jan 2024 10:30:00 +0100
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="B"

--B
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Bonjour Bob,=0A=0AA demain =C3=A0 10h.
--B
Content-Type: application/pdf; name="doc.pdf"
Content-Disposition: attachment; filename="doc.pdf"
Content-Transfer-Encoding: base64

%s
--B--
"""

    def test_headers_encoded_subject_body_and_attachment(self):
        out = self.conv(self.write("m.eml", self.EML % base64.b64encode(b"%PDF-1.4 fake").decode()))
        self.assertMd(out.body, "# Réunion demain", "**De :** Alice", "alice@ex.org", "**À :** Bob", "Bonjour Bob,", "A demain à 10h.",
                      "**Pièces jointes :**", "[doc.pdf](assets/doc.pdf)")
        self.assertIn("doc.pdf", out.assets)

    def test_html_only_mail_is_converted(self):
        eml = ("From: a@ex.org\nTo: b@ex.org\nSubject: Promo\nMIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\n\n"
               "<html><body><h2>Offre</h2><p>Une <b>super</b> offre.</p></body></html>\n")
        md = self.md(self.write("h.eml", eml))
        self.assertMd(md, "# Promo", "## Offre", "Une **super** offre.")


class PlainText(Base):
    def test_markdown_passthrough_fences_front_matter(self):
        md = self.md(self.write("r.md", "---\ntitle: T\n---\n# Bonjour\n\ntexte\n"))
        self.assertMd(md, "```yaml\ntitle: T\n```", "# Bonjour", "texte")

    def test_source_code_is_fenced_with_language(self):
        md = self.md(self.write("s.py", "def f(x):\n    return x * 2\n"))
        self.assertMd(md, "```python\ndef f(x):\n    return x * 2\n```")

    def test_text_encodings_are_detected(self):
        self.assertMd(self.md(self.write("c.txt", "Le café était très chaud.\n".encode("cp1252"))), "café était très chaud")
        self.assertMd(self.md(self.write("u.txt", "Été à Zürich\n".encode("utf-16"))), "Été à Zürich")

    def test_paragraphs_are_preserved(self):
        md = self.md(self.write("t.txt", "Premier paragraphe\nsuite de la ligne.\n\nSecond paragraphe.\n"))
        self.assertMd(md, "Premier paragraphe\nsuite de la ligne.\n\nSecond paragraphe.")


if __name__ == "__main__":
    unittest.main()
