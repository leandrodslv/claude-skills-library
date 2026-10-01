"""PDF difficiles : deux colonnes, tableaux sans bordures / fusionnés, pages pivotées, scans inclinés, pages mixtes, notes de bas de page."""
from __future__ import annotations

import io
import random
from typing import List

from gen_common import OUT, Case

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

_SENTENCES = [
    "Les mesures effectuées sur le terrain confirment la tendance observée lors de la campagne précédente.",
    "Un écart de deux pour cent subsiste entre les relevés manuels et les capteurs automatiques.",
    "La température moyenne du site est restée inférieure au seuil réglementaire pendant toute la période.",
    "Les opérateurs ont signalé quatre incidents mineurs, tous résolus dans un délai de vingt-quatre heures.",
    "Cette approche permet de réduire sensiblement le coût de maintenance sans dégrader la disponibilité.",
    "Les résultats détaillés figurent dans le tableau récapitulatif présenté en annexe du document.",
    "Une validation indépendante a été réalisée par un laboratoire accrédité au mois de septembre.",
    "Le protocole sera étendu à trois nouveaux sites dès que le financement aura été confirmé.",
]


def _para(n: int, k: int = 3) -> str:
    rnd = random.Random(n)
    return f"P{n:02d} " + " ".join(rnd.sample(_SENTENCES, k))


def _fonts() -> bool:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont("DV", _FONT))
        pdfmetrics.registerFont(TTFont("DV-B", _BOLD))
        pdfmetrics.registerFont(TTFont("DV-S", _SERIF))
        return True
    except Exception:  # noqa: BLE001
        return False


def _scan_jpeg(lines: List[str], angle: float = 1.6, seed: int = 7) -> bytes:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    w, h = 1240, 1754                                     # A4 à 150 dpi
    img = Image.new("L", (w, h), 245)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(_SERIF, 30)
    y = 150
    for ln in lines:
        d.text((110, y), ln, fill=25, font=f)
        y += 52
    img = img.rotate(angle, expand=False, fillcolor=240, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.6))
    rnd = random.Random(seed)
    px = img.load()
    for _ in range(9000):
        px[rnd.randrange(w), rnd.randrange(h)] = rnd.choice([0, 60, 255])
    b = io.BytesIO()
    img.save(b, "JPEG", quality=62)
    return b.getvalue()


SCAN_LINES = ["Compte rendu de la visite du 12 mars", "", "Le chantier avance conformément au planning prévisionnel.",
              "La livraison des menuiseries est confirmée pour le 4 avril.", "Deux réserves ont été levées lors de cette visite :",
              "  - le calfeutrement de la baie du rez-de-chaussée ;", "  - la reprise de l'enduit du pignon nord.", "",
              "Montant total des travaux : 128 450 euros hors taxes.", "Prochaine réunion de chantier : jeudi 21 mars à 9 heures."]
SCAN_MUST = ["Compte rendu de la visite du 12 mars", "Le chantier avance conformément au planning prévisionnel", "La livraison des menuiseries est confirmée pour le 4 avril",
             "le calfeutrement de la baie du rez-de-chaussée", "128 450 euros hors taxes", "Prochaine réunion de chantier"]


def build() -> List[Case]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import BaseDocTemplate, Frame, FrameBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
        import PIL  # noqa: F401
    except ImportError:
        return []
    if not _fonts():
        return []
    d = OUT / "pdf"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []
    body = ParagraphStyle("b", fontName="DV", fontSize=9.5, leading=13)
    h1 = ParagraphStyle("h1", fontName="DV-B", fontSize=14, leading=18, spaceBefore=8, spaceAfter=4)
    title = ParagraphStyle("t", fontName="DV-B", fontSize=20, leading=24, spaceAfter=6)

    # 1. article à deux colonnes, titre/résumé pleine largeur, en-tête courant, numéros de page
    path = d / "article-deux-colonnes.pdf"
    W, H = A4
    HEADER = "Journal of Examples — Vol. 12, 2025"

    def deco(c, doc):
        c.saveState()
        c.setFont("DV", 8)
        c.drawString(2 * cm, H - 1.2 * cm, HEADER)
        c.drawCentredString(W / 2, 1.1 * cm, f"Page {doc.page} sur 3")
        c.restoreState()

    full = Frame(2 * cm, H - 8 * cm, W - 4 * cm, 6 * cm, id="full")
    col = lambda x, y, hh: Frame(x, y, (W - 5 * cm) / 2, hh, id=f"c{x}{y}")  # noqa: E731
    first = PageTemplate("p1", [full, col(2 * cm, 2 * cm, H - 10.5 * cm), col(2 * cm + (W - 5 * cm) / 2 + cm, 2 * cm, H - 10.5 * cm)], onPage=deco)
    later = PageTemplate("p2", [col(2 * cm, 2 * cm, H - 4.5 * cm), col(2 * cm + (W - 5 * cm) / 2 + cm, 2 * cm, H - 4.5 * cm)], onPage=deco)
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[first, later])
    story = [Paragraph("Mesure de la dérive thermique en milieu industriel", title),
             Paragraph("Résumé. Cet article présente une méthode de suivi de la dérive thermique et en évalue les performances sur trois sites pilotes.", body), FrameBreak()]
    from reportlab.platypus import NextPageTemplate
    story.insert(2, NextPageTemplate("p2"))
    k = 1
    for sec in ["1. Introduction", "2. Méthodes", "3. Résultats", "4. Discussion"]:
        story.append(Paragraph(sec, h1))
        for _ in range(3):
            story.append(Paragraph(_para(k), body))
            story.append(Spacer(1, 5))
            k += 1
    doc.build(story)
    markers = [f"P{n:02d}" for n in range(1, k)]
    cases.append(Case("pdf-article-deux-colonnes", path, "pdf", 4, "deux colonnes sur 3 pages, titre/résumé pleine largeur, en-tête et numéros de page répétés",
                      order=["Mesure de la dérive thermique en milieu industriel"] + markers, must=["Résumé. Cet article présente une méthode"],
                      headings=["1. Introduction", "2. Méthodes", "3. Résultats", "4. Discussion"],
                      at_most={HEADER: 1}, absent=["Page 2 sur 3", "Page 3 sur 3"],
                      notes="Ordre de lecture : colonne de gauche entière puis colonne de droite ; l'en-tête courant et les numéros de page ne doivent pas être répétés dans le corps."))

    # 2. tableau sans bordures (colonnes alignées par l'espace)
    path = d / "tableau-sans-bordures.pdf"
    data = [["Produit", "Référence", "Prix unitaire", "Stock", "Statut"], ["Perceuse sans fil", "PRC-2041", "129,90 €", "34", "Disponible"],
            ["Scie circulaire", "SCI-1187", "89,50 €", "0", "Rupture"], ["Ponceuse orbitale", "PON-0932", "74,00 €", "12", "Disponible"],
            ["Visseuse à choc", "VIS-5520", "159,00 €", "5", "Dernières unités"], ["Niveau laser", "NIV-7714", "199,90 €", "21", "Disponible"]]
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[PageTemplate("t", [Frame(2 * cm, 2 * cm, W - 4 * cm, H - 4 * cm)])])
    tb = Table(data, colWidths=[4.6 * cm, 3 * cm, 3.4 * cm, 2 * cm, 4 * cm])
    tb.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "DV"), ("FONTNAME", (0, 0), (-1, 0), "DV-B"), ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("ALIGN", (2, 1), (3, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    doc.build([Paragraph("Catalogue outillage — extrait", title), Spacer(1, 10), tb, Spacer(1, 12), Paragraph("Prix TTC, valables jusqu'au 31 décembre.", body)])
    cases.append(Case("pdf-tableau-sans-bordures", path, "pdf", 4, "tableau sans aucun trait : seules les positions des colonnes le structurent",
                      cells=[c for r in data for c in r], rows=[r for r in data], must=["Prix TTC, valables jusqu'au 31 décembre"], headings=["Catalogue outillage — extrait"],
                      notes="Doit devenir un vrai tableau Markdown (une ligne par ligne, une colonne par colonne), pas un texte aplati."))

    # 3. tableau à bordures avec cellules fusionnées (SPAN)
    path = d / "tableau-bordures-fusionnees.pdf"
    data = [["Région", "Ventes 2025", "", "Objectif 2026"], ["", "S1", "S2", ""], ["Nord", "410", "455", "900"], ["", "Détail Lille : 120 / 135", "", "270"], ["Sud", "380", "402", "820"]]
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[PageTemplate("t", [Frame(2 * cm, 2 * cm, W - 4 * cm, H - 4 * cm)])])
    tb = Table(data, colWidths=[3.5 * cm, 4 * cm, 4 * cm, 4 * cm])
    tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.8, colors.black), ("FONTNAME", (0, 0), (-1, -1), "DV"), ("FONTSIZE", (0, 0), (-1, -1), 10),
                            ("SPAN", (1, 0), (2, 0)), ("SPAN", (0, 0), (0, 1)), ("SPAN", (3, 0), (3, 1)), ("SPAN", (0, 2), (0, 3)), ("SPAN", (1, 3), (2, 3)),
                            ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    doc.build([Paragraph("Ventes par région", title), Spacer(1, 10), tb])
    cases.append(Case("pdf-tableau-bordures-fusionnees", path, "pdf", 4, "tableau à traits avec cellules fusionnées horizontalement et verticalement",
                      cells=["Région", "Ventes 2025", "S1", "S2", "Objectif 2026", "Nord", "410", "455", "900", "Détail Lille : 120 / 135", "270", "Sud", "380", "402", "820"],
                      rows=[["Nord", "410", "455", "900"], ["Sud", "380", "402", "820"]], headings=["Ventes par région"],
                      notes="Chaque valeur doit rester sur la ligne de sa région ; les cellules fusionnées sont répétées ou clairement indiquées."))

    # 4. page pivotée (/Rotate 90)
    path = d / "page-pivotee.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("DV", 12)
    c.drawString(2 * cm, H - 3 * cm, "Page normale : introduction du dossier d'étude.")
    c.showPage()
    c.setPageRotation(90)
    c.setFont("DV-B", 14)
    c.drawString(2 * cm, H - 3 * cm, "Page pivotée de 90 degrés : tableau des écarts")
    c.setFont("DV", 11)
    for i, t in enumerate(["Écart de calibrage : 0,8 mm", "Écart de planéité : 1,2 mm", "Écart angulaire : 0,3 degré"]):
        c.drawString(2 * cm, H - 4.5 * cm - i * 0.8 * cm, t)
    c.showPage()
    c.save()
    cases.append(Case("pdf-page-pivotee", path, "pdf", 3, "une page est marquée /Rotate 90 : le texte est dessiné dans le repère non pivoté",
                      must=["Page normale : introduction du dossier d'étude", "Page pivotée de 90 degrés : tableau des écarts", "Écart de calibrage : 0,8 mm", "Écart de planéité : 1,2 mm", "Écart angulaire : 0,3 degré"],
                      order=["Page normale", "Écart de calibrage", "Écart de planéité", "Écart angulaire"]))

    # 5. scan incliné et bruité, une seule page
    path = d / "scan-incline-bruite.pdf"
    from PIL import Image
    Image.open(io.BytesIO(_scan_jpeg(SCAN_LINES))).save(str(path), "PDF", resolution=150.0)
    cases.append(Case("pdf-scan-incline-bruite", path, "pdf", 5, "scan en niveaux de gris, incliné de 1,6°, flou et bruit de numérisation : aucun texte natif",
                      must=SCAN_MUST, expect="vision",
                      notes="Avec OCR : le texte doit ressortir ; sans OCR : la page doit être signalée « à lire visuellement » (jamais une sortie vide silencieuse)."))

    # 6. document mixte : texte / scan / texte
    path = d / "mixte-texte-scan-texte.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("DV-B", 16)
    c.drawString(2 * cm, H - 3 * cm, "Dossier de candidature — première partie")
    c.setFont("DV", 11)
    c.drawString(2 * cm, H - 4 * cm, "Cette page contient du texte natif parfaitement extractible.")
    c.showPage()
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(io.BytesIO(_scan_jpeg(SCAN_LINES, angle=0.8, seed=11))), 0, 0, width=W, height=H)
    c.showPage()
    c.setFont("DV-B", 16)
    c.drawString(2 * cm, H - 3 * cm, "Dossier de candidature — dernière partie")
    c.setFont("DV", 11)
    c.drawString(2 * cm, H - 4 * cm, "Conclusion : la candidature est recevable sous réserve des pièces.")
    c.showPage()
    c.save()
    cases.append(Case("pdf-mixte-texte-scan-texte", path, "pdf", 4, "texte natif, puis une page scannée au milieu, puis texte natif",
                      must=["Dossier de candidature — première partie", "Cette page contient du texte natif parfaitement extractible", "Dossier de candidature — dernière partie",
                            "Conclusion : la candidature est recevable sous réserve des pièces"] + SCAN_MUST[:3],
                      order=["première partie", "dernière partie"], expect="vision",
                      notes="La page scannée du milieu doit être OCRisée ou signalée ; les pages texte ne doivent pas être affectées."))

    # 7. notes de bas de page en pied de page
    path = d / "notes-de-bas-de-page.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("DV-B", 15)
    c.drawString(2 * cm, H - 3 * cm, "L'économie circulaire dans le bâtiment")
    c.setFont("DV", 10.5)
    body_lines = ["Le réemploi des matériaux de second œuvre progresse rapidement depuis trois ans¹. Les maîtres d'ouvrage",
                  "exigent désormais un diagnostic ressources avant toute démolition², ce qui modifie les plannings.",
                  "Pour autant, la filière reste fragmentée et les volumes réellement valorisés demeurent modestes."]
    for i, ln in enumerate(body_lines):
        c.drawString(2 * cm, H - 4.5 * cm - i * 0.6 * cm, ln)
    c.line(2 * cm, 4.2 * cm, 7 * cm, 4.2 * cm)
    c.setFont("DV", 8.5)
    c.drawString(2 * cm, 3.7 * cm, "¹ Source : observatoire national du réemploi, rapport annuel 2024, page 31.")
    c.drawString(2 * cm, 3.2 * cm, "² Décret relatif au diagnostic portant sur la gestion des produits, équipements, matériaux et déchets.")
    c.showPage()
    c.setFont("DV", 10.5)
    c.drawString(2 * cm, H - 3 * cm, "La seconde partie examine les freins économiques et les leviers réglementaires disponibles.")
    c.showPage()
    c.save()
    cases.append(Case("pdf-notes-de-bas-de-page", path, "pdf", 3, "notes de bas de page en pied de page, appels en exposant dans le texte",
                      must=["Source : observatoire national du réemploi, rapport annuel 2024, page 31", "Décret relatif au diagnostic portant sur la gestion des produits"],
                      order=["Le réemploi des matériaux de second œuvre", "Pour autant, la filière reste fragmentée", "La seconde partie examine les freins économiques"],
                      headings=["L'économie circulaire dans le bâtiment"],
                      notes="Le corps du texte doit rester continu ; les notes doivent être conservées (idéalement identifiées comme notes), sans s'intercaler au milieu d'une phrase."))

    # 8. gros PDF de charge (option)
    from gen_common import WITH_BIG
    if WITH_BIG:
        big = OUT / "big"
        big.mkdir(parents=True, exist_ok=True)
        path = big / "pdf-300-pages.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        for n in range(1, 301):
            c.setFont("DV-B", 14)
            c.drawString(2 * cm, H - 3 * cm, f"Chapitre {n}")
            c.setFont("DV", 10)
            for i, s in enumerate(random.Random(n).sample(_SENTENCES, 5)):
                c.drawString(2 * cm, H - 4.5 * cm - i * 0.6 * cm, s)
            c.showPage()
        c.save()
        cases.append(Case("big-pdf-300-pages", path, "big", 3, "300 pages : tient-on la charge sans tout perdre ?", must=["Chapitre 1", "Chapitre 150", "Chapitre 300"]))
    return cases
