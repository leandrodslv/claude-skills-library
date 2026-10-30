"""DOCX, PPTX, XLSX, OpenDocument et RTF : structure, fidélité et cas limites."""
import unittest

from common import Base
import fixtures as fx


class Docx(Base):
    def test_headings_lists_and_emphasis(self):
        body = (fx.para("Rapport", "Title") + fx.para("Introduction", "Heading1") + fx.para("Détail", "Heading2")
                + fx.para(fx.run("Du ") + fx.run("gras", b=True) + fx.run(" et ") + fx.run("italique", i=True) + fx.run(".")))
        md = self.md(fx.make_docx(self.tmp / "a.docx", body))
        self.assertMd(md, "# Rapport", "## Introduction", "### Détail", "Du **gras** et _italique_.")

    def test_bullet_and_numbered_lists_with_nesting(self):
        body = (fx.para("un", num=(1, 0)) + fx.para("deux", num=(1, 0)) + fx.para("sous", num=(1, 1))
                + fx.para("premier", num=(2, 0)) + fx.para("second", num=(2, 0)) + fx.para("alpha", num=(2, 1)))
        md = self.md(fx.make_docx(self.tmp / "l.docx", body, numbering=fx.NUMBERING))
        self.assertMd(md, "- un\n- deux\n  - sous", "1. premier\n2. second", "a) alpha")

    def test_table_with_merged_cells_fills_down_and_flattens_headers(self):
        def tc(text, extra=""):
            return f'<w:tc><w:tcPr>{extra}</w:tcPr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>'
        restart = '<w:vMerge w:val="restart"/>'
        cont = "<w:vMerge/>"
        rows = (f'<w:tr>{tc("Région")}{tc("Produit")}{tc("Ventes")}</w:tr>'
                f'<w:tr>{tc("Europe", restart)}{tc("A")}{tc("10")}</w:tr>'
                f'<w:tr>{tc("", cont)}{tc("B")}{tc("20")}</w:tr>')
        md = self.md(fx.make_docx(self.tmp / "t.docx", f"<w:tbl>{rows}</w:tbl>"))
        self.assertMd(md, "| Région | Produit | Ventes |", "| Europe | A | 10 |", "| Europe | B | 20 |")

    def test_single_cell_table_becomes_blockquote(self):
        body = '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Encadré important</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        md = self.md(fx.make_docx(self.tmp / "box.docx", body))
        self.assertMd(md, "> Encadré important")

    def test_table_cells_inside_content_controls_are_kept(self):
        # régression : une ligne dont une cellule est enveloppée par <w:sdt> perdait cette cellule
        sdt = '<w:sdt><w:sdtContent><w:tc><w:p><w:r><w:t>Body copy</w:t></w:r></w:p></w:tc></w:sdtContent></w:sdt>'
        row = f'<w:tr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc>{sdt}<w:tc><w:p><w:r><w:t>c</w:t></w:r></w:p></w:tc></w:tr>'
        md = self.md(fx.make_docx(self.tmp / "sdt.docx", f'<w:tbl><w:tr><w:tc><w:p><w:r><w:t>h1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>h2</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>h3</w:t></w:r></w:p></w:tc></w:tr>{row}</w:tbl>'))
        self.assertMd(md, "| a | Body copy | c |")

    def test_hyperlinks_simple_field_and_autolink(self):
        body = fx.para(fx.run("Voir ") + '<w:hyperlink r:id="rId5">' + fx.run("le site") + "</w:hyperlink>"
                       + fx.run(" ou ") + '<w:hyperlink r:id="rId6">' + fx.run("https://exemple.org") + "</w:hyperlink>")
        rels = fx.hyperlink_rel("rId5", "https://exemple.org/page") + fx.hyperlink_rel("rId6", "https://exemple.org")
        md = self.md(fx.make_docx(self.tmp / "h.docx", body, rels=rels))
        self.assertMd(md, "[le site](https://exemple.org/page)", "<https://exemple.org>")

    def test_footnotes_and_comments(self):
        body = fx.para(fx.run("Texte") + '<w:r><w:footnoteReference w:id="1"/></w:r>' + fx.run(" ancré ")
                       + '<w:commentRangeStart w:id="0"/>' + fx.run("commenté") + '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r>')
        foot = fx.XML + f'<w:footnotes {fx.W}><w:footnote w:id="1"><w:p><w:r><w:t>Ma note.</w:t></w:r></w:p></w:footnote></w:footnotes>'
        com = fx.XML + f'<w:comments {fx.W}><w:comment w:id="0" w:author="Bob" w:date="2024-05-01T10:00:00Z"><w:p><w:r><w:t>À revoir</w:t></w:r></w:p></w:comment></w:comments>'
        md = self.md(fx.make_docx(self.tmp / "n.docx", body, footnotes=foot, comments=com))
        self.assertMd(md, "Texte[^1]", "[^1]: Ma note.", "[^c1]", "**Bob (2024-05-01)** sur « commenté » : À revoir")
        md2 = self.md(self.tmp / "n.docx", comments=False)
        self.assertNotMd(md2, "[^c1]", "À revoir")

    def test_images_extracted_with_alt_text(self):
        body = fx.para("Avant") + fx.para(fx.drawing("rId7", "Schéma d'architecture"))
        p = fx.make_docx(self.tmp / "i.docx", body, media={"pic.png": fx.png()}, rels=fx.image_rel("rId7", "pic.png"))
        out = self.conv(p)
        self.assertMd(out.body, "![Schéma d'architecture](assets/img-01.png)")
        self.assertIn("img-01.png", out.assets)
        self.assertEqual(self.md(p, images="skip").count("!["), 0)

    def test_tracked_changes_accept_or_mark(self):
        body = fx.para(fx.run("Bonjour ") + '<w:ins w:id="1"><w:r><w:t>beau </w:t></w:r></w:ins>'
                       '<w:del w:id="2"><w:r><w:delText>vilain </w:delText></w:r></w:del>' + fx.run("monde"))
        p = fx.make_docx(self.tmp / "tc.docx", body)
        self.assertMd(self.md(p), "Bonjour beau monde")
        marked = self.md(p, track_changes="mark")
        self.assertMd(marked, "<ins>beau</ins>", "<del>vilain</del>")

    def test_table_of_contents_is_dropped_unless_requested(self):
        body = fx.para("Table des matières", "TOC1") + fx.para("1 Intro ..... 3", "TOC1") + fx.para("Intro", "Heading1") + fx.para("Corps")
        p = fx.make_docx(self.tmp / "toc.docx", body)
        self.assertNotMd(self.md(p), "Intro .....")
        self.assertMd(self.md(p, keep_toc=True), "Intro .....")

    def test_superscripts_subscripts_and_ordinals(self):
        sup = '<w:vertAlign w:val="superscript"/>'
        sub = '<w:vertAlign w:val="subscript"/>'
        body = fx.para(fx.run("m") + fx.run("2", extra=sup) + fx.run(" H") + fx.run("2", extra=sub) + fx.run("O, 1") + fx.run("er", extra=sup) + fx.run(" ") + fx.run("texte", extra=sup))
        md = self.md(fx.make_docx(self.tmp / "s.docx", body))
        self.assertMd(md, "m² H₂O, 1er <sup>texte</sup>")

    def test_equations_become_latex(self):
        omml = ('<m:oMath><m:f><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:sSup><m:e><m:r><m:t>b</m:t></m:r></m:e>'
                '<m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:den></m:f></m:oMath>')
        md = self.md(fx.make_docx(self.tmp / "m.docx", fx.para(fx.run("Soit ") + omml)))
        self.assertMd(md, "Soit $\\frac{a}{{b}^{2}}$")

    def test_alternate_content_is_not_duplicated(self):
        ac = ('<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wp:anchor><a:graphic><a:graphicData><wps:wsp><wps:txbx><w:txbxContent>'
              '<w:p><w:r><w:t>Zone de texte</w:t></w:r></w:p></w:txbxContent></wps:txbx></wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice>'
              '<mc:Fallback><w:pict><v:textbox xmlns:v="urn:schemas-microsoft-com:vml"><w:txbxContent><w:p><w:r><w:t>Zone de texte</w:t></w:r></w:p></w:txbxContent></v:textbox></w:pict></mc:Fallback>'
              '</mc:AlternateContent></w:r></w:p>')
        md = self.md(fx.make_docx(self.tmp / "tb.docx", ac))
        self.assertEqual(md.count("Zone de texte"), 1)

    def test_code_style_and_quote(self):
        body = fx.para("print('a')", "Code") + fx.para("x = 1", "Code") + fx.para("Une citation", "Quote")
        md = self.md(fx.make_docx(self.tmp / "c.docx", body))
        self.assertMd(md, "```\nprint('a')\nx = 1\n```", "> Une citation")

    def test_headings_inferred_from_formatting_when_no_styles(self):
        big = '<w:sz w:val="36"/>'
        body = fx.para(fx.run("Grand titre", b=True, extra=big)) + "".join(fx.para(f"Paragraphe {i} avec assez de texte pour compter.") for i in range(6))
        md = self.md(fx.make_docx(self.tmp / "inf.docx", body))
        self.assertMd(md, "# Grand titre")
        self.assertNotMd(self.md(self.tmp / "inf.docx", infer_headings=False), "# Grand titre")

    def test_metadata_title_becomes_h1(self):
        p = fx.make_docx(self.tmp / "mt.docx", fx.para("Corps du texte."), core_title="Titre des métadonnées")
        self.assertTrue(self.md(p).startswith("# Titre des métadonnées"))

    def test_numbered_headings_keep_their_numbers(self):
        num = fx.NUMBERING.replace("</w:numbering>", '<w:abstractNum w:abstractNumId="2"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>'
                                   '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2"/></w:lvl></w:abstractNum>'
                                   '<w:num w:numId="3"><w:abstractNumId w:val="2"/></w:num></w:numbering>')
        body = fx.para("Méthode", "Heading1", num=(3, 0)) + fx.para("Données", "Heading2", num=(3, 1)) + fx.para("Analyse", "Heading2", num=(3, 1))
        md = self.md(fx.make_docx(self.tmp / "nh.docx", body, numbering=num))
        self.assertMd(md, "# 1. Méthode", "## 1.1 Données", "## 1.2 Analyse")

    def test_recall_is_full_on_plain_document(self):
        out = self.conv(fx.make_docx(self.tmp / "r.docx", fx.para("Un deux trois.") + fx.para("Quatre cinq six.")))
        self.assertEqual(out.score.recall, 1.0)


class DocxImages(Base):
    def test_images_without_alt_text_are_flagged_for_visual_reading(self):
        body = fx.para(fx.drawing("rId7", "")) + fx.para(fx.drawing("rId7", "Décrite"))
        out = self.conv(fx.make_docx(self.tmp / "noalt.docx", body, media={"pic.png": fx.png()}, rels=fx.image_rel("rId7", "pic.png")))
        self.assertMd(out.body, "![](assets/img-01.png)", "![Décrite](assets/img-01.png)")
        self.assertTrue(any("1 image(s) sans texte alternatif" in w for w in out.ctx.warnings), out.ctx.warnings)


class DocxBigImages(Base):
    def test_large_unlabeled_image_is_added_to_the_reading_list(self):
        body = fx.para(fx.drawing("rId7", ""))
        out = self.conv(fx.make_docx(self.tmp / "big.docx", body, media={"pic.png": fx.png(300, 200, noisy=True)}, rels=fx.image_rel("rId7", "pic.png")))
        self.assertEqual(out.status, "needs_vision")
        self.assertIn("graphique", out.ctx.vision[0].reason)


class DocxOle(Base):
    def test_embedded_object_is_extracted_as_an_attachment(self):
        body = fx.para("Voir : " + '<w:r><w:object><v:shape xmlns:v="urn:schemas-microsoft-com:vml"/><o:OLEObject xmlns:o="urn:schemas-microsoft-com:office:office" r:id="rId9"/></w:object></w:r>')
        rel = '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/package" Target="embeddings/tableau.xlsx"/>'
        out = self.conv(fx.make_docx(self.tmp / "ole.docx", body, rels=rel, extra_parts={"word/embeddings/tableau.xlsx": "PK-fake"}))
        self.assertMd(out.body, "[objet incorporé : tableau.xlsx](assets/tableau.xlsx)")
        self.assertIn("tableau.xlsx", out.assets)


class Pptx(Base):
    def test_slides_follow_presentation_order_not_file_order(self):
        s1 = fx.slide_xml(fx.sp(2, "T", ["Premier"], ph="title"))
        s2 = fx.slide_xml(fx.sp(2, "T", ["Second"], ph="title"))
        p = fx.make_pptx(self.tmp / "o.pptx", [s1, s2], order=[2, 1])
        md = self.md(p)
        self.assertLess(md.index("Second"), md.index("Premier"))
        self.assertMd(md, "## Slide 1 — Second", "## Slide 2 — Premier")

    def test_title_body_bullets_levels_and_notes(self):
        lvl0 = '<a:pPr lvl="0"/><a:r><a:t>Point A</a:t></a:r>'
        lvl1 = '<a:pPr lvl="1"/><a:r><a:t>Détail A1</a:t></a:r>'
        shapes = fx.sp(2, "Titre", ["Mon titre"], ph="title") + fx.sp(3, "Corps", [lvl0, lvl1], ph="body", off=(0, 1000000))
        rels = '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
        notes = fx.XML + f'<p:notes {fx.P_NS}><p:cSld><p:spTree>' + fx.sp(2, "n", ["Dire bonjour"], ph="body") + "</p:spTree></p:cSld></p:notes>"
        p = fx.make_pptx(self.tmp / "b.pptx", [fx.slide_xml(shapes)], slide_rels={1: rels}, extra={"ppt/notesSlides/notesSlide1.xml": notes})
        md = self.md(p)
        self.assertTrue(md.startswith("## Slide 1 — Mon titre"), md)
        self.assertMd(md, "- Point A\n  - Détail A1", "**Notes du présentateur :**", "> Dire bonjour")
        self.assertNotMd(self.md(p, notes=False), "Dire bonjour")

    def test_table_and_hidden_slide(self):
        tbl = ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="T"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
               '<p:xfrm><a:off x="0" y="0"/><a:ext cx="1" cy="1"/></p:xfrm><a:graphic><a:graphicData><a:tbl>'
               '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>Nom</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>Score</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
               '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>Zoé</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>42</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
               '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
        s1 = fx.slide_xml(fx.sp(2, "T", ["Résultats"], ph="title") + tbl)
        s2 = fx.slide_xml(fx.sp(2, "T", ["Cachée"], ph="title"), hidden=True)
        p = fx.make_pptx(self.tmp / "t.pptx", [s1, s2])
        md = self.md(p)
        self.assertMd(md, "| Nom | Score |", "| Zoé | 42 |", "*(masquée)*")
        self.assertNotMd(self.md(p, hidden=False), "Cachée")

    def test_chart_data_from_cache(self):
        chart = fx.XML + ('<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:chart>'
                          '<c:title><c:tx><c:rich><a:p><a:r><a:t>Ventes</a:t></a:r></a:p></c:rich></c:tx></c:title><c:plotArea><c:barChart><c:barDir val="col"/>'
                          '<c:ser><c:tx><c:strRef><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>2024</c:v></c:pt></c:strCache></c:strRef></c:tx>'
                          '<c:cat><c:strRef><c:strCache><c:ptCount val="2"/><c:pt idx="0"><c:v>Nord</c:v></c:pt><c:pt idx="1"><c:v>Sud</c:v></c:pt></c:strCache></c:strRef></c:cat>'
                          '<c:val><c:numRef><c:numCache><c:ptCount val="2"/><c:pt idx="0"><c:v>10</c:v></c:pt><c:pt idx="1"><c:v>20.5</c:v></c:pt></c:numCache></c:numRef></c:val>'
                          '</c:ser></c:barChart></c:plotArea></c:chart></c:chartSpace>')
        frame = ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="C"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr><p:xfrm><a:off x="0" y="0"/><a:ext cx="1" cy="1"/></p:xfrm>'
                 '<a:graphic><a:graphicData><c:chart r:id="rId2"/></a:graphicData></a:graphic></p:graphicFrame>')
        rels = '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/>'
        p = fx.make_pptx(self.tmp / "c.pptx", [fx.slide_xml(fx.sp(2, "T", ["Bilan"], ph="title") + frame)], slide_rels={1: rels}, extra={"ppt/charts/chart1.xml": chart})
        md = self.md(p)
        self.assertMd(md, "**Graphique (histogramme) — Ventes**", "| Nord | 10 |", "| Sud | 20.5 |")

    def test_connectors_become_mermaid_graph(self):
        def cx(i, a, b):
            return (f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{i}" name="c"/><p:cNvCxnSpPr><a:stCxn id="{a}" idx="0"/><a:endCxn id="{b}" idx="0"/></p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr>'
                    f'<p:spPr><a:ln><a:tailEnd type="triangle"/></a:ln></p:spPr></p:cxnSp>')
        shapes = (fx.sp(2, "Titre", ["Architecture"], ph="title") + fx.sp(10, "A", ["Frontend"], off=(0, 1000000)) + fx.sp(11, "B", ["API"], off=(3000000, 1000000))
                  + fx.sp(12, "C", ["Base"], off=(6000000, 1000000)) + cx(20, 10, 11) + cx(21, 11, 12))
        md = self.md(fx.make_pptx(self.tmp / "g.pptx", [fx.slide_xml(shapes)]))
        self.assertMd(md, "```mermaid", 'n1["Frontend"]', "n1 --> n2", "n2 --> n3", "| Frontend | → | API |", "| API | → | Base |")

    def test_free_form_diagram_without_connectors_is_flagged(self):
        def box(i, label, x):
            return (f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="b{i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="2000000"/><a:ext cx="800000" cy="400000"/></a:xfrm>'
                    f'<a:prstGeom prst="rect"/></p:spPr><p:txBody><a:bodyPr/><a:p><a:r><a:t>{label}</a:t></a:r></a:p></p:txBody></p:sp>')

        def arrow(i, x):
            return (f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="a{i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="2100000"/><a:ext cx="300000" cy="200000"/></a:xfrm>'
                    f'<a:prstGeom prst="rightArrow"/></p:spPr></p:sp>')
        shapes = fx.sp(2, "T", ["Flux"], ph="title") + "".join(box(10 + i, f"Étape {i}", i * 900000) for i in range(6)) + "".join(arrow(30 + i, i * 900000 + 800000) for i in range(3))
        out = self.conv(fx.make_pptx(self.tmp / "free.pptx", [fx.slide_xml(shapes)]))
        self.assertMd(out.body, "Étape 0", "Étape 5", "```mermaid", "-->")
        self.assertTrue(any("schéma reconstitué" in w for w in out.ctx.warnings), out.ctx.warnings)

    def test_reading_order_is_spatial(self):
        shapes = (fx.sp(2, "T", ["Titre"], ph="title") + fx.sp(3, "B", ["En bas"], off=(0, 5000000)) + fx.sp(4, "A", ["Au milieu"], off=(0, 2000000)))
        md = self.md(fx.make_pptx(self.tmp / "ro.pptx", [fx.slide_xml(shapes)]))
        self.assertLess(md.index("Au milieu"), md.index("En bas"))

    def test_picture_only_slide_requests_vision(self):
        pic = ('<p:pic><p:nvPicPr><p:cNvPr id="5" name="Picture 4"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId3"/></p:blipFill>'
               '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1" cy="1"/></a:xfrm></p:spPr></p:pic>')
        rels = '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>'
        p = fx.make_pptx(self.tmp / "v.pptx", [fx.slide_xml(pic)], slide_rels={1: rels}, extra={"ppt/media/image1.png": fx.png(200, 120)})
        out = self.conv(p)
        self.assertEqual(out.status, "needs_vision")
        self.assertTrue(out.ctx.vision and "slide01-img" in out.ctx.vision[0].path)
        self.assertMd(out.body, "[À COMPLÉTER")


class Xlsx(Base):
    def _cells(self):
        rows = ('<sheetData>'
                '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c></row>'
                '<row r="2"><c r="A2" t="s"><v>4</v></c><c r="B2" s="1"><v>45306</v></c><c r="C2" s="2"><v>0.125</v></c><c r="D2" t="b"><v>1</v></c></row>'
                '<row r="3"><c r="A3" t="s"><v>5</v></c><c r="B3"><v>0.30000000000000004</v></c><c r="C3" s="3"><v>0.5</v></c><c r="D3" t="b"><v>0</v></c></row>'
                '<row r="5"><c r="A5"><f>SUM(B2:B3)</f></c></row>'
                '</sheetData><mergeCells count="0"/>')
        return rows

    def test_types_dates_percent_booleans_and_float_noise(self):
        shared = ["Nom", "Date", "Taux", "Actif", "Alice", "Bob"]
        p = fx.make_xlsx(self.tmp / "v.xlsx", [("Ventes", self._cells(), "visible")], shared=shared, styles=fx.STYLES_XLSX)
        md = self.md(p)
        self.assertMd(md, "## Ventes", "| Nom | Date | Taux | Actif |", "| Alice | 2024-01-15 | 12% | TRUE |", "| Bob | 0.3 | 50.00% | FALSE |")
        self.assertMd(md, "=SUM(B2:B3)")       # formule sans valeur en cache : affichée plutôt que perdue

    def test_1904_date_system(self):
        sheet = '<sheetData><row r="1"><c r="A1" s="1"><v>43844</v></c></row></sheetData>'
        p = fx.make_xlsx(self.tmp / "d.xlsx", [("S", sheet, "visible")], styles=fx.STYLES_XLSX, date1904=True)
        self.assertMd(self.md(p), "2024-01-15")

    def test_hidden_sheet_is_flagged_and_can_be_excluded(self):
        p = fx.make_xlsx(self.tmp / "h.xlsx", [("Vue", '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>visible</t></is></c></row></sheetData>', "visible"),
                                              ("Cachée", '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>secret</t></is></c></row></sheetData>', "hidden")])
        self.assertMd(self.md(p), "## Cachée *(masquée)*", "secret")
        self.assertNotMd(self.md(p, hidden=False), "secret")

    def test_blocks_separated_by_blank_rows_and_merged_cells(self):
        sheet = ('<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Titre du rapport</t></is></c></row>'
                 '<row r="3"><c r="A3" t="inlineStr"><is><t>X</t></is></c><c r="B3" t="inlineStr"><is><t>Y</t></is></c></row>'
                 '<row r="4"><c r="A4" t="inlineStr"><is><t>Groupe</t></is></c><c r="B4"><v>1</v></c></row>'
                 '<row r="5"><c r="B5"><v>2</v></c></row></sheetData><mergeCells count="1"><mergeCell ref="A4:A5"/></mergeCells>')
        md = self.md(fx.make_xlsx(self.tmp / "b.xlsx", [("S", sheet, "visible")]))
        self.assertMd(md, "**Titre du rapport**", "| X | Y |", "| Groupe | 1 |", "| Groupe | 2 |")

    def test_large_sheet_is_truncated_with_full_csv_attached(self):
        rows = "".join(f'<row r="{i}"><c r="A{i}"><v>{i}</v></c><c r="B{i}" t="inlineStr"><is><t>ligne {i}</t></is></c></row>' for i in range(1, 51))
        out = self.conv(fx.make_xlsx(self.tmp / "big.xlsx", [("Gros", f"<sheetData>{rows}</sheetData>", "visible")]), table_rows=10)
        self.assertMd(out.body, "lignes de plus", "Tableau tronqué dans ce fichier (50 lignes au total)")
        csv_asset = next(a for n, a in out.assets.items() if n.endswith(".csv"))
        self.assertEqual(csv_asset.data.decode().count("\n"), 50)

    def test_shared_strings_with_rich_text_and_special_chars(self):
        shared = ["a &amp; b", "x | y"]
        sheet = '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2"><v>1</v></c><c r="B2"><v>2</v></c></row></sheetData>'
        md = self.md(fx.make_xlsx(self.tmp / "sp.xlsx", [("S", sheet, "visible")], shared=shared))
        self.assertMd(md, "a & b", "x \\| y")


class OpenDocument(Base):
    def test_odt_headings_lists_tables_notes(self):
        body = ('<office:text><text:h text:outline-level="1">Titre ODT</text:h><text:p>Un <text:span text:style-name="B">mot</text:span> gras'
                '<text:note text:note-class="footnote"><text:note-citation>1</text:note-citation><text:note-body><text:p>Ma note</text:p></text:note-body></text:note>.</text:p>'
                '<text:list><text:list-item><text:p>un</text:p></text:list-item><text:list-item><text:p>deux</text:p></text:list-item></text:list>'
                '<table:table><table:table-row><table:table-cell><text:p>a</text:p></table:table-cell><table:table-cell><text:p>b</text:p></table:table-cell></table:table-row>'
                '<table:table-row><table:table-cell><text:p>1</text:p></table:table-cell><table:table-cell><text:p>2</text:p></table:table-cell></table:table-row></table:table></office:text>')
        styles = '<style:style style:name="B" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style>'
        p = fx.make_odf(self.tmp / "a.odt", "application/vnd.oasis.opendocument.text", body, styles)
        md = self.md(p)
        self.assertMd(md, "# Titre ODT", "Un **mot** gras[^1].", "- un\n- deux", "| a | b |", "| 1 | 2 |", "[^1]: Ma note")

    def test_ods_values_and_types(self):
        body = ('<office:spreadsheet><table:table table:name="Feuil"><table:table-row>'
                '<table:table-cell office:value-type="string"><text:p>Nom</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>Taux</text:p></table:table-cell></table:table-row>'
                '<table:table-row><table:table-cell office:value-type="string"><text:p>A</text:p></table:table-cell><table:table-cell office:value-type="percentage" office:value="0.25"><text:p>25%</text:p></table:table-cell></table:table-row>'
                '</table:table></office:spreadsheet>')
        md = self.md(fx.make_odf(self.tmp / "a.ods", "application/vnd.oasis.opendocument.spreadsheet", body))
        self.assertMd(md, "## Feuil", "| Nom | Taux |", "| A | 25% |")

    def test_odp_slides_with_title_and_notes(self):
        body = ('<office:presentation><draw:page draw:name="p1"><draw:frame presentation:class="title" svg:y="1cm"><draw:text-box><text:p>Titre diapo</text:p></draw:text-box></draw:frame>'
                '<draw:frame presentation:class="outline" svg:y="5cm"><draw:text-box><text:list><text:list-item><text:p>puce</text:p></text:list-item></text:list></draw:text-box></draw:frame>'
                '</draw:page></office:presentation>')
        md = self.md(fx.make_odf(self.tmp / "a.odp", "application/vnd.oasis.opendocument.presentation", body))
        self.assertMd(md, "## Slide 1 — Titre diapo", "- puce")


class OpenDocumentDraw(Base):
    def test_odg_shapes_texts_and_connectors(self):
        body = ('<office:drawing><draw:page draw:name="Architecture">'
                '<draw:custom-shape draw:id="a" svg:x="1cm" svg:y="1cm"><text:p>Client</text:p></draw:custom-shape>'
                '<draw:custom-shape draw:id="b" svg:x="6cm" svg:y="1cm"><text:p>Serveur</text:p></draw:custom-shape>'
                '<draw:custom-shape draw:id="c" svg:x="11cm" svg:y="1cm"><text:p>Base</text:p></draw:custom-shape>'
                '<draw:connector draw:start-shape="a" draw:end-shape="b"/><draw:connector draw:start-shape="b" draw:end-shape="c"/>'
                '</draw:page><draw:page draw:name="page2"><draw:frame svg:x="1cm" svg:y="1cm"><draw:text-box><text:p>Seconde page</text:p></draw:text-box></draw:frame></draw:page></office:drawing>')
        md = self.md(fx.make_odf(self.tmp / "a.odg", "application/vnd.oasis.opendocument.graphics", body))
        self.assertMd(md, "## Page 1 — Architecture", "Client", "```mermaid", 'N1["Client"] --> N2["Serveur"]', "## Page 2", "Seconde page")
        self.assertNotMd(md, "page2")

    def test_odg_without_text_requests_visual_reading(self):
        body = '<office:drawing><draw:page draw:name="page1"><draw:ellipse svg:x="1cm" svg:y="1cm"/></draw:page></office:drawing>'
        out = self.conv(fx.make_odf(self.tmp / "b.odg", "application/vnd.oasis.opendocument.graphics", body))
        self.assertEqual(out.status, "needs_vision")


class Visio(Base):
    NS = 'xmlns="http://schemas.microsoft.com/office/visio/2012/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'

    def make(self, name, page_xml):
        return fx.write_zip(self.tmp / name, {
            "[Content_Types].xml": fx.XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
            "_rels/.rels": fx.XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/></Relationships>',
            "visio/document.xml": fx.XML + f'<VisioDocument {self.NS}/>',
            "visio/pages/pages.xml": fx.XML + f'<Pages {self.NS}><Page ID="0" Name="Flux de commande" NameU="Flux"><Rel r:id="rId1"/></Page></Pages>',
            "visio/pages/_rels/pages.xml.rels": fx.XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/></Relationships>',
            "visio/pages/page1.xml": fx.XML + page_xml,
        })

    @staticmethod
    def shape(sid, text, x, y, extra=""):
        t = f"<Text><cp IX=\"0\"/>{text}</Text>" if text else ""
        return f'<Shape ID="{sid}" NameU="Process" Type="Shape"><Cell N="PinX" V="{x}"/><Cell N="PinY" V="{y}"/>{extra}{t}</Shape>'

    def test_shapes_and_connectors_become_a_mermaid_graph(self):
        conn = '<Shape ID="9" NameU="Dynamic connector" Type="Shape"><Cell N="EndArrow" V="13"/><Text>oui</Text></Shape>'
        conn2 = '<Shape ID="10" NameU="Dynamic connector" Type="Shape"/>'
        page = (f'<PageContents {self.NS}><Shapes>' + self.shape(1, "Commande reçue", 2, 8) + self.shape(2, "Stock vérifié", 5, 8) + self.shape(3, "Expédier", 8, 8)
                + self.shape(4, "Note : livraison sous 48 h", 5, 2) + conn + conn2 +
                '</Shapes><Connects>'
                '<Connect FromSheet="9" FromCell="BeginX" ToSheet="1" ToCell="PinX"/><Connect FromSheet="9" FromCell="EndX" ToSheet="2" ToCell="PinX"/>'
                '<Connect FromSheet="10" FromCell="BeginX" ToSheet="2" ToCell="PinX"/><Connect FromSheet="10" FromCell="EndX" ToSheet="3" ToCell="PinX"/>'
                '</Connects></PageContents>')
        out = self.conv(self.make("flux.vsdx", page))
        self.assertEqual(out.status, "ok", out.error)
        self.assertMd(out.body, "## Page 1 — Flux de commande", "```mermaid", 'n1["Commande reçue"]', 'n2["Stock vérifié"]', 'n3["Expédier"]',
                      "n1 -->|oui| n2", "n2 --> n3", "**Textes :**", "- Note : livraison sous 48 h")

    def test_page_without_text_requests_visual_reading(self):
        page = f'<PageContents {self.NS}><Shapes>' + self.shape(1, "", 2, 8) + '</Shapes></PageContents>'
        out = self.conv(self.make("vide.vsdx", page))
        self.assertEqual(out.status, "needs_vision")

    def test_unlinked_texts_are_listed_in_reading_order(self):
        page = f'<PageContents {self.NS}><Shapes>' + self.shape(1, "Bas", 2, 1) + self.shape(2, "Haut", 2, 9) + '</Shapes></PageContents>'
        md = self.md(self.make("t.vsdx", page))
        self.assertLess(md.index("Haut"), md.index("Bas"))


class Office2003Xml(Base):
    SHEET = """<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office">
<Worksheet ss:Name="Ventes"><Table>
<Row><Cell><Data ss:Type="String">Région</Data></Cell><Cell><Data ss:Type="String">Date</Data></Cell><Cell><Data ss:Type="String">Montant</Data></Cell><Cell><Data ss:Type="String">Payé</Data></Cell></Row>
<Row><Cell ss:MergeDown="1"><Data ss:Type="String">Europe</Data></Cell><Cell><Data ss:Type="DateTime">2024-01-15T00:00:00.000</Data></Cell><Cell><Data ss:Type="Number">12.5</Data></Cell><Cell><Data ss:Type="Boolean">1</Data></Cell></Row>
<Row><Cell ss:Index="2"><Data ss:Type="DateTime">2024-02-01T10:30:00.000</Data></Cell><Cell><Data ss:Type="Number">1000</Data></Cell><Cell><Data ss:Type="Boolean">0</Data></Cell></Row>
</Table></Worksheet>
<Worksheet ss:Name="Cachée"><Table><Row><Cell><Data ss:Type="String">secret</Data></Cell></Row></Table><WorksheetOptions><Visible>SheetHidden</Visible></WorksheetOptions></Worksheet>
</Workbook>"""

    WORD = """<?xml version="1.0"?><?mso-application progid="Word.Document"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml" xmlns:wx="http://schemas.microsoft.com/office/word/2003/auxHint">
<w:styles><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>
<w:body><wx:sect><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Titre ancien</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Du </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>gras</w:t></w:r></w:p>
<wx:sub-section><w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>2</w:t></w:r></w:p></w:tc></w:tr></w:tbl></wx:sub-section></wx:sect></w:body></w:wordDocument>"""

    def test_spreadsheetml_types_merges_and_hidden_sheets(self):
        p = self.write("old.xml", self.SHEET)
        md = self.md(p)
        self.assertMd(md, "## Ventes", "| Région | Date | Montant | Payé |", "| Europe | 2024-01-15 | 12.5 | TRUE |", "| Europe | 2024-02-01 10:30 | 1000 | FALSE |",
                      "## Cachée *(masquée)*", "secret")
        self.assertNotMd(self.md(p, hidden=False), "secret")

    def test_wordml_2003_is_converted_through_the_docx_reader(self):
        md = self.md(self.write("old-word.xml", self.WORD))
        self.assertMd(md, "# Titre ancien", "Du **gras**", "| A | B |", "| 1 | 2 |")


class Rtf(Base):
    def test_text_formatting_lists_tables_links_unicode(self):
        rtf = (r"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times;}}{\stylesheet{\s1 heading 1;}}"
               r"\pard\s1 Titre\par"
               r"\pard Du \b gras\b0  et un @u8364? avec \'e9\'e8, {\field{\*\fldinst{HYPERLINK @qhttps://ex.org@q}}{\fldrslt lien}}.\par"
               r"{\pntext\f0 1.\tab}Premier\par{\pntext\f0 2.\tab}Second\par"
               r"\trowd\cellx3000\cellx6000\intbl A\cell \intbl B\cell\row \trowd\cellx3000\cellx6000\intbl 1\cell \intbl 2\cell\row \pard Fin.\par}")
        md = self.md(self.write("a.rtf", rtf.replace("@u", chr(92) + "u").replace("@q", chr(34))))
        self.assertMd(md, "# Titre", "Du **gras** et un € avec éè, [lien](https://ex.org).", "1. Premier\n2. Second", "| A | B |", "| 1 | 2 |", "Fin.")

    def test_hyperlink_field_with_nested_groups_and_several_runs(self):
        # forme écrite par Word : instruction et résultat imbriqués dans des sous-groupes
        rtf = (r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}}\pard Voir {\field{\*\fldinst {HYPERLINK @qhttps://ex.org/a@q}}"
               r"{\fldrslt {\ul un }{\ul lien}}} puis fin.\par}")
        md = self.md(self.write("n.rtf", rtf.replace("@q", chr(34))))
        self.assertMd(md, "Voir [un lien](https://ex.org/a) puis fin.")     # les deux segments forment un seul lien


if __name__ == "__main__":
    unittest.main()
