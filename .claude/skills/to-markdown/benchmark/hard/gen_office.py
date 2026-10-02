"""PowerPoint, Excel et formats Office anciens difficiles."""
from __future__ import annotations

import io
from typing import List

from gen_common import OUT, WITH_BIG, Case, lo_convert  # noqa: F401


def _text_png(lines: List[str], size=(1400, 520), font_px=64) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_px)
    y = 60
    for ln in lines:
        d.text((60, y), ln, fill="black", font=f)
        y += font_px + 40
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def build_pptx() -> List[Case]:
    try:
        from pptx import Presentation
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE
        from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
        from pptx.util import Inches, Pt
    except ImportError:
        return []
    d = OUT / "pptx"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []

    # 1. schéma en formes libres + connecteurs, sans placeholder de contenu
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Architecture de la plateforme"
    names = ["Client mobile", "Passerelle API", "Service Paiement", "Service Catalogue", "Base de données"]
    pos = [(0.4, 2.2), (2.6, 2.2), (5.0, 1.3), (5.0, 3.2), (7.4, 2.2)]
    shapes = []
    for n, (x, y) in zip(names, pos):
        sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(1.8), Inches(0.8))
        sh.text_frame.text = n
        shapes.append(sh)
    for a, b in [(0, 1), (1, 2), (1, 3), (2, 4), (3, 4)]:
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, 0, 0, 0, 0)
        c.begin_connect(shapes[a], 3)
        c.end_connect(shapes[b], 1)
    note = s.shapes.add_textbox(Inches(0.4), Inches(5.4), Inches(8), Inches(0.5))
    note.text_frame.text = "Flux chiffrés de bout en bout (TLS 1.3)"
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s2.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(8), Inches(0.6))
    tb.text_frame.text = "Plan de déploiement"
    tb.text_frame.paragraphs[0].runs[0].font.size = Pt(32)
    for i, (t, x) in enumerate([("Phase 1 : pilote", 0.5), ("Phase 2 : extension", 3.5), ("Phase 3 : généralisation", 6.5)]):
        sh = s2.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(x), Inches(2.0), Inches(2.8), Inches(1.0))
        sh.text_frame.text = t
    prs.save(str(d / "schema-formes-libres.pptx"))
    cases.append(Case("pptx-schema-formes-libres", d / "schema-formes-libres.pptx", "pptx", 4,
                      "diapositive entièrement dessinée (formes + connecteurs, titre en zone de texte libre), sans liste ni tableau",
                      must=names + ["Flux chiffrés de bout en bout", "Phase 1 : pilote", "Phase 2 : extension", "Phase 3 : généralisation", "Plan de déploiement"],
                      order=["Phase 1 : pilote", "Phase 2 : extension", "Phase 3 : généralisation"], headings=["Architecture de la plateforme"],
                      notes="Idéal : un schéma Mermaid (nœuds = formes, flèches = connecteurs) ; au minimum tous les libellés dans l'ordre de lecture."))

    # 2. groupes, graphique, tableau à cellules fusionnées, notes, diapositive masquée
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Résultats trimestriels"
    cd = CategoryChartData()
    cd.categories = ["T1", "T2", "T3", "T4"]
    cd.add_series("Ventes France", (120, 135, 150, 170))
    cd.add_series("Ventes Export", (80, 95, 110, 130))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.5), Inches(5), Inches(3.5), cd)
    gf.chart.has_title = True
    gf.chart.chart_title.text_frame.text = "Ventes par trimestre (k€)"
    s.notes_slide.notes_text_frame.text = "Note de l'orateur : insister sur la progression de l'export au T4."
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Équipes et responsabilités"
    grp = s.shapes.add_group_shape()
    for i, t in enumerate(["Pôle Produit : Anaïs Moreau", "Pôle Technique : Karim Benali", "Pôle Ventes : Sofia Rossi"]):
        b = grp.shapes.add_textbox(Inches(0.5), Inches(1.6 + i * 0.7), Inches(4), Inches(0.5))
        b.text_frame.text = t
    tbl = s.shapes.add_table(3, 3, Inches(5), Inches(1.6), Inches(4.5), Inches(1.8)).table
    tbl.cell(0, 0).merge(tbl.cell(0, 2))
    tbl.cell(0, 0).text = "Budget par pôle"
    for j, h in enumerate(["Pôle", "Budget", "Effectif"]):
        tbl.cell(1, j).text = h
    for j, v in enumerate(["Produit", "420 k€", "12"]):
        tbl.cell(2, j).text = v
    hidden = prs.slides.add_slide(prs.slide_layouts[5])
    hidden.shapes.title.text = "Annexe masquée"
    hidden.shapes.add_textbox(Inches(1), Inches(2), Inches(6), Inches(1)).text_frame.text = "Hypothèses internes à ne pas diffuser"
    hidden._element.set("show", "0")
    prs.save(str(d / "groupes-graphique-notes.pptx"))
    cases.append(Case("pptx-groupes-graphique-notes", d / "groupes-graphique-notes.pptx", "pptx", 4,
                      "graphique (données dans le XML du graphique), formes groupées, tableau à cellules fusionnées, notes, diapositive masquée",
                      must=["Ventes par trimestre", "Ventes France", "Ventes Export", "170", "130", "Note de l'orateur : insister sur la progression de l'export au T4",
                            "Pôle Produit : Anaïs Moreau", "Pôle Technique : Karim Benali", "Pôle Ventes : Sofia Rossi", "Budget par pôle", "420 k€"],
                      rows=[["Pôle", "Budget", "Effectif"], ["Produit", "420 k€", "12"]], headings=["Résultats trimestriels", "Équipes et responsabilités"],
                      notes="Les valeurs du graphique doivent être restituées (tableau de données) ; la diapositive masquée doit être signalée ou exclue, pas confondue."))

    # 3. diapositive qui n'est qu'une image de texte (aucun texte extractible)
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[6])
    png = d / "_tmp.png"
    png.write_bytes(_text_png(["Chiffre d'affaires 2025", "4,2 M€ (+8 %)", "Objectif 2026 : 5 M€"]))
    s.shapes.add_picture(str(png), Inches(0.3), Inches(1), width=Inches(9.2))
    png.unlink()
    prs.save(str(d / "diapositive-image.pptx"))
    cases.append(Case("pptx-diapositive-image", d / "diapositive-image.pptx", "pptx", 3, "toute l'information est dans une image (aucun texte, aucun texte alternatif)",
                      must=["Chiffre d'affaires 2025", "4,2 M€", "Objectif 2026 : 5 M€"], expect="vision",
                      notes="Sans OCR, le contenu ne peut pas être extrait : il doit au moins être signalé « à lire visuellement »."))
    return cases


def build_xlsx() -> List[Case]:
    try:
        import xlsxwriter
    except ImportError:
        return []
    d = OUT / "xlsx"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []
    wb = xlsxwriter.Workbook(str(d / "budget-formules-masques.xlsx"))
    ws = wb.add_worksheet("Synthèse")
    title = wb.add_format({"bold": True, "align": "center", "font_size": 16})
    pct, eur, dt = wb.add_format({"num_format": "0.0%"}), wb.add_format({"num_format": '#,##0.00 "€"'}), wb.add_format({"num_format": "dd/mm/yyyy"})
    ws.merge_range("A1:D1", "Budget prévisionnel 2026", title)
    for j, h in enumerate(["Poste", "Montant", "Part", "Échéance"]):
        ws.write(2, j, h)
    rows = [("Salaires", 820000.5, 0.58), ("Loyers", 120000, 0.085), ("Informatique", 215000.25, 0.152), ("Divers", 258999.25, 0.183)]
    import datetime
    for i, (n, m, pc) in enumerate(rows):
        ws.write(3 + i, 0, n)
        ws.write_number(3 + i, 1, m, eur)
        ws.write_number(3 + i, 2, pc, pct)
        ws.write_datetime(3 + i, 3, datetime.datetime(2026, 1 + i, 15), dt)
    total = sum(r[1] for r in rows)
    ws.write(7, 0, "Total")
    ws.write_formula(7, 1, "=SUM(B4:B7)", eur, total)
    ws.write_comment("A8", "Hypothèse : inflation de 3 % sur les salaires")
    ws.set_row(5, None, None, {"hidden": True})            # « Informatique » masquée
    ws2 = wb.add_worksheet("Détail")
    ws2.write_row(0, 0, ["Service", "Responsable", "Observation"])
    ws2.write_row(1, 0, ["Comptabilité", "Hélène Dubois", "Clôture mensuelle au jour 5"])
    ws2.write_row(2, 0, ["Achats", "Mathieu Garnier", "Renégociation des contrats cadres"])
    ws3 = wb.add_worksheet("Brouillon")
    ws3.write(0, 0, "SECRET-INTERNE brouillon non validé")
    ws3.hide()
    wb.close()
    cases.append(Case("xlsx-budget-formules-masques", d / "budget-formules-masques.xlsx", "xlsx", 4,
                      "titre fusionné, formats (monnaie, %, date), formule à valeur en cache, commentaire, ligne et feuille masquées",
                      must=["Budget prévisionnel 2026", "Hypothèse : inflation de 3 % sur les salaires", "Hélène Dubois", "Renégociation des contrats cadres", "Salaires", "Loyers", "Divers"],
                      any_of=[["1 414 000", "1414000", "1 414 000,00", "1,414,000"], ["58,0 %", "58 %", "0,58", "0.58", "58.0%"], ["15/01/2026", "2026-01-15"],
                              ["820 000,50 €", "820000.50 €", "820000.5 €", "820,000.50 €", "€820000.5", "€ 820000.5"]],
                      rows=[["Salaires"], ["Total"]], headings=["Synthèse", "Détail"],
                      notes="Le montant doit garder son unité (820 000,50 €) : sans symbole monétaire, « 820000.5 » est ambigu pour un lecteur IA. Contenu masqué (feuille « Brouillon », ligne Informatique) : acceptable s'il est étiqueté « masqué »."))

    # grande feuille large
    rows_n, cols_n = (3000, 30)
    wb = xlsxwriter.Workbook(str(d / "grande-feuille-large.xlsx"))
    ws = wb.add_worksheet("Mesures")
    ws.write_row(0, 0, [f"Col{j + 1:02d}" for j in range(cols_n)])
    for i in range(rows_n):
        ws.write_row(i + 1, 0, [f"r{i + 1:04d}c{j + 1:02d}" for j in range(cols_n)])
    wb.close()
    cases.append(Case("xlsx-grande-feuille-large", d / "grande-feuille-large.xlsx", "xlsx", 3,
                      "3 000 lignes × 30 colonnes : tient-on la charge sans perdre silencieusement des lignes ?",
                      must=["r0001c01", "r0500c15", "r1000c30"], any_of=[["r3000c30", "lignes omises", "tronqué", "limite", "troncature"]],
                      notes="Une troncature est acceptable si elle est signalée dans le texte ; une perte silencieuse ne l'est pas."))
    return cases


def build_legacy() -> List[Case]:
    cases: List[Case] = []
    from pathlib import Path
    srcs = {"xlsx": OUT / "xlsx" / "budget-formules-masques.xlsx", "pptx": OUT / "pptx" / "groupes-graphique-notes.pptx"}
    d = OUT / "legacy"
    d.mkdir(parents=True, exist_ok=True)
    # Word 97-2003 : le format ne sait pas imbriquer de tableau ; on part donc d'un tableau à cellules fusionnées, sans imbrication
    html = d / "_tableaux.html"
    html.write_text("""<html><head><meta charset="utf-8"></head><body><h1>Chiffre d'affaires par zone</h1>
<table border="1" cellpadding="4"><tr><th rowspan="2">Zone</th><th colspan="2">Résultats 2025</th><th rowspan="2">Prévisions 2026</th></tr>
<tr><th>T1</th><th>T2</th></tr><tr><td>Europe</td><td>1 204</td><td>1 310</td><td>5 100</td></tr><tr><td>Asie</td><td>980</td><td>1 022</td><td>4 200</td></tr></table>
<p>Source : direction financière.</p><ul><li>Premier point</li><li>Second point</li></ul></body></html>""", encoding="utf-8")
    dest = d / "tableaux-fusionnes.doc"
    if lo_convert(html, "doc:MS Word 97", dest, infilter="HTML (StarWriter)"):
        cases.append(Case("legacy-tableaux-fusionnes", dest, "legacy", 4, "Word 97-2003 (.doc) : tableau à cellules fusionnées, liste",
                          cells=["Zone", "Résultats 2025", "T1", "T2", "Prévisions 2026", "Europe", "1 204", "1 310", "5 100", "Asie", "980", "1 022", "4 200"],
                          rows=[["Europe", "1 204", "1 310", "5 100"], ["Asie", "980", "1 022", "4 200"]],
                          must=["Chiffre d'affaires par zone", "Source : direction financière", "Premier point", "Second point"]))
    html.unlink(missing_ok=True)
    plan = [("xlsx", "xls", "xls:MS Excel 97", "xlsx-budget-formules-masques", "Excel 97-2003 (.xls) : formats, formule, commentaire",
             dict(must=["Budget prévisionnel 2026", "Salaires", "Loyers", "Hélène Dubois"])),
            ("pptx", "ppt", "ppt:MS PowerPoint 97", "pptx-groupes-graphique-notes", "PowerPoint 97-2003 (.ppt) : groupes, tableau, notes",
             dict(must=["Résultats trimestriels", "Pôle Produit : Anaïs Moreau", "Budget par pôle", "420 k€", "Note de l'orateur : insister sur la progression de l'export au T4"],
                  rows=[["Pôle", "Budget", "Effectif"], ["Produit", "420 k€", "12"]]))]
    for src_ext, ext, filt, base, challenge, exp in plan:
        src = srcs[src_ext]
        if not Path(src).exists():
            continue
        dest = d / f"{base.split('-', 1)[1]}.{ext}"
        if lo_convert(Path(src), filt, dest):
            cases.append(Case(f"legacy-{base.split('-', 1)[1]}", dest, "legacy", 4, challenge, **exp))
    return cases


def build() -> List[Case]:
    return build_pptx() + build_xlsx() + build_legacy()
