"""Corpus du banc d'essai : documents dont le contenu exact est connu, produits par des outils tiers.

Chaque document est décrit une fois (titres, paragraphes, listes, tableau, lien) puis écrit par un
producteur INDÉPENDANT de mdconv — python-docx, python-pptx, openpyxl, LibreOffice — de sorte que la
« vérité » (mots, titres, cellules, éléments de liste, liens) vient de la description et non d'un convertisseur.
Chaque rendu renvoie la vérité de ce qu'il a réellement écrit (``Truth``).
"""
from __future__ import annotations

import csv
import html
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

Block = Tuple  # ("h", niveau, texte) | ("p", texte) | ("ul", [..]) | ("ol", [..]) | ("table", entêtes, lignes) | ("link", avant, texte, url)


@dataclass
class Doc:
    slug: str
    title: str
    blocks: List[Block]


@dataclass
class Truth:
    text: str = ""                                   # tout le texte écrit dans le fichier
    headings: List[str] = field(default_factory=list)
    cells: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    links: List[Tuple[str, str]] = field(default_factory=list)


DOCS: List[Doc] = [
    Doc("rapport-energie", "Rapport annuel de consommation énergétique", [
        ("h", 1, "Introduction"),
        ("p", "Ce rapport présente la consommation d'électricité et de gaz des cinq sites de la collectivité pour l'exercice 2025. Il compare les résultats à l'année précédente et propose des actions prioritaires."),
        ("h", 2, "Méthodologie"),
        ("p", "Les relevés proviennent des compteurs communicants, vérifiés chaque trimestre par le service technique."),
        ("ul", ["Relevés mensuels des compteurs électriques", "Factures de gaz rapprochées des index", "Correction des variations climatiques par degrés-jours unifiés"]),
        ("h", 2, "Résultats"),
        ("p", "La consommation totale atteint 4 820 MWh, soit une baisse de 6,4 % par rapport à 2024. Les écoles et la piscine municipale concentrent plus de la moitié de la consommation."),
        ("table", ["Site", "Consommation (MWh)", "Variation", "Statut"], [
            ["Mairie annexe", "312,5", "-8,1 %", "Conforme"],
            ["Piscine municipale", "1 480,0", "-3,2 %", "À surveiller"],
            ["École des Tilleuls", "905,2", "-9,7 %", "Conforme"],
            ["Gymnase Pasteur", "764,8", "+1,4 %", "Écart"],
            ["Médiathèque", "1 357,5", "-7,9 %", "Conforme"]]),
        ("h", 2, "Recommandations"),
        ("ol", ["Remplacer la chaudière du gymnase Pasteur avant l'hiver", "Installer une régulation horaire à la piscine", "Étendre le contrat de suivi à tous les bâtiments"]),
        ("h", 3, "Limites de l'étude"),
        ("p", "Les données de l'école des Tilleuls couvrent onze mois seulement ; la valeur de décembre est estimée."),
        ("link", "Les données brutes sont publiées sur ", "le portail ouvert de la ville", "https://data.exemple.fr/energie-2025")]),
    Doc("launch-plan", "Product launch plan for the third quarter", [
        ("h", 1, "Overview"),
        ("p", "The Atlas mobile app moves from private beta to general availability on 15 September. This plan lists the workstreams, owners and the checkpoints that decide whether the date holds."),
        ("h", 2, "Goals"),
        ("ul", ["Reach 20,000 active accounts within 30 days", "Keep crash-free sessions above 99.5 percent", "Publish the pricing page before the announcement"]),
        ("h", 2, "Timeline"),
        ("table", ["Milestone", "Owner", "Due date", "Risk"], [
            ["Feature freeze", "Dana Whitfield", "2 August", "Low"],
            ["Security review", "Priya Raman", "19 August", "Medium"],
            ["Store submission", "Tomás Beltrán", "30 August", "High"],
            ["Press embargo lifts", "Marketing", "15 September", "Low"]]),
        ("h", 2, "Open decisions"),
        ("ol", ["Choose the launch-week discount policy", "Decide whether to localise the onboarding flow", "Confirm the on-call rota for the first weekend"]),
        ("p", "Budget remains within the approved envelope of 184,000 euros, with a contingency of 12 percent held by finance."),
        ("link", "The full backlog is tracked in ", "the release board", "https://tracker.example.com/atlas/release")]),
    Doc("compte-rendu", "Compte rendu du conseil d'école du 14 novembre", [
        ("h", 1, "Ordre du jour"),
        ("p", "Le conseil s'est réuni en présence de la directrice, de trois enseignants, de quatre parents élus et d'un représentant de la mairie. Le quorum était atteint dès l'ouverture de la séance."),
        ("h", 2, "Sécurité aux abords de l'école"),
        ("p", "Les parents signalent des vitesses excessives rue des Lilas. La mairie étudie la pose d'un ralentisseur et d'un passage piéton surélevé, sans calendrier arrêté."),
        ("ul", ["Demande d'une zone 30 devant le portail", "Remplacement du panneau abîmé", "Présence d'un agent aux heures d'entrée"]),
        ("h", 2, "Projet pédagogique"),
        ("p", "Les classes de CM1 et CM2 préparent un spectacle de fin d'année autour du thème des saisons. Le budget demandé s'élève à 450 euros pour les costumes."),
        ("table", ["Classe", "Effectif", "Projet", "Budget"], [
            ["CE2", "24", "Jardin pédagogique", "120 €"],
            ["CM1", "26", "Spectacle des saisons", "250 €"],
            ["CM2", "25", "Spectacle des saisons", "200 €"]]),
        ("h", 2, "Questions diverses"),
        ("ol", ["Renouvellement du mobilier de la salle de motricité", "Date de la kermesse fixée au 20 juin", "Accueil des nouveaux élèves en septembre"]),
        ("p", "La séance est levée à vingt heures quinze. Le prochain conseil aura lieu en mars."),
        ("link", "Le règlement intérieur est consultable sur ", "le site de l'école", "https://ecole-tilleuls.exemple.fr/reglement")]),
    Doc("api-guide", "Payments API integration guide", [
        ("h", 1, "Getting started"),
        ("p", "Every request must carry a bearer token in the Authorization header. Tokens expire after 3600 seconds and can be renewed without user interaction using the refresh endpoint."),
        ("h", 2, "Endpoints"),
        ("table", ["Method", "Path", "Description", "Rate limit"], [
            ["POST", "/v2/charges", "Create a charge", "100/min"],
            ["GET", "/v2/charges/{id}", "Retrieve a charge", "300/min"],
            ["POST", "/v2/refunds", "Refund a charge", "50/min"],
            ["GET", "/v2/balance", "Current account balance", "60/min"]]),
        ("h", 2, "Error handling"),
        ("p", "Errors use conventional HTTP status codes. A 429 response means the rate limit was exceeded and the Retry-After header gives the delay in seconds."),
        ("ul", ["Retry idempotent requests with exponential backoff", "Never retry a charge without an idempotency key", "Log the request identifier returned in every response"]),
        ("h", 3, "Webhooks"),
        ("ol", ["Register an HTTPS endpoint in the dashboard", "Verify the signature of each delivery", "Acknowledge within five seconds"]),
        ("link", "Reference documentation lives at ", "the developer portal", "https://developers.example.com/payments")]),
]


# --------------------------------------------------------------------------
# Vérité
# --------------------------------------------------------------------------

def _truth(doc: Doc, with_links: bool = True, skip_title: bool = False) -> Truth:
    t = Truth()
    parts: List[str] = [] if skip_title else [doc.title]
    if not skip_title:
        t.headings.append(doc.title)
    for b in doc.blocks:
        if b[0] == "h":
            parts.append(b[2])
            t.headings.append(b[2])
        elif b[0] == "p":
            parts.append(b[1])
        elif b[0] in ("ul", "ol"):
            parts.extend(b[1])
            t.items.extend(b[1])
        elif b[0] == "table":
            parts.extend(b[1])
            t.cells.extend(b[1])
            for row in b[2]:
                parts.extend(row)
                t.cells.extend(row)
        elif b[0] == "link":
            parts.append(b[1] + b[2])
            if with_links:
                t.links.append((b[2], b[3]))
    t.text = "\n".join(parts)
    return t


# --------------------------------------------------------------------------
# Producteurs
# --------------------------------------------------------------------------

def to_html(doc: Doc) -> str:
    e = html.escape
    out = [f"<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>{e(doc.title)}</title></head><body>", f"<h1>{e(doc.title)}</h1>"]
    for b in doc.blocks:
        if b[0] == "h":
            out.append(f"<h{b[1] + 1}>{e(b[2])}</h{b[1] + 1}>")
        elif b[0] == "p":
            out.append(f"<p>{e(b[1])}</p>")
        elif b[0] in ("ul", "ol"):
            out.append(f"<{b[0]}>" + "".join(f"<li>{e(i)}</li>" for i in b[1]) + f"</{b[0]}>")
        elif b[0] == "table":
            rows = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in b[2])
            out.append("<table border=\"1\" cellpadding=\"4\"><tr>" + "".join(f"<th>{e(c)}</th>" for c in b[1]) + f"</tr>{rows}</table>")
        elif b[0] == "link":
            out.append(f"<p>{e(b[1])}<a href=\"{e(b[3])}\">{e(b[2])}</a></p>")
    out.append("</body></html>")
    return "\n".join(out)


def make_html(doc: Doc, path: Path) -> Truth:
    path.write_text(to_html(doc), encoding="utf-8")
    return _truth(doc)


def make_docx_python(doc: Doc, path: Path) -> Optional[Truth]:
    try:
        import docx
    except ImportError:
        return None
    d = docx.Document()
    d.add_heading(doc.title, 0)
    for b in doc.blocks:
        if b[0] == "h":
            d.add_heading(b[2], b[1])
        elif b[0] == "p":
            d.add_paragraph(b[1])
        elif b[0] == "ul":
            for i in b[1]:
                d.add_paragraph(i, style="List Bullet")
        elif b[0] == "ol":
            for i in b[1]:
                d.add_paragraph(i, style="List Number")
        elif b[0] == "table":
            tb = d.add_table(rows=1, cols=len(b[1]))
            tb.style = "Table Grid"
            for j, c in enumerate(b[1]):
                tb.rows[0].cells[j].text = c
            for r in b[2]:
                cells = tb.add_row().cells
                for j, c in enumerate(r):
                    cells[j].text = c
        elif b[0] == "link":
            d.add_paragraph(b[1] + b[2])
    d.save(str(path))
    return _truth(doc, with_links=False)


def make_pptx_python(doc: Doc, path: Path) -> Optional[Truth]:
    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ImportError:
        return None
    prs = Presentation()
    t = Truth()
    parts: List[str] = [doc.title]
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = doc.title
    t.headings.append(doc.title)
    title, body = None, []

    def flush() -> None:
        if title is None:
            return
        sl = prs.slides.add_slide(prs.slide_layouts[1])
        sl.shapes.title.text = title
        tf = sl.placeholders[1].text_frame
        tf.clear()
        for k, line in enumerate(body):
            (tf.paragraphs[0] if k == 0 else tf.add_paragraph()).text = line

    for b in doc.blocks:
        if b[0] == "h":
            flush()
            title, body = b[2], []
            parts.append(b[2])
            t.headings.append(b[2])
        elif b[0] == "p" or b[0] == "link":
            txt = b[1] if b[0] == "p" else b[1] + b[2]
            body.append(txt)
            parts.append(txt)
        elif b[0] in ("ul", "ol"):
            body.extend(b[1])
            parts.extend(b[1])
            t.items.extend(b[1])
        elif b[0] == "table":
            flush()
            sl = prs.slides.add_slide(prs.slide_layouts[5])
            sl.shapes.title.text = title or "Tableau"
            tb = sl.shapes.add_table(len(b[2]) + 1, len(b[1]), Inches(0.5), Inches(1.6), Inches(9), Inches(3)).table
            for j, c in enumerate(b[1]):
                tb.cell(0, j).text = c
            for i, r in enumerate(b[2], 1):
                for j, c in enumerate(r):
                    tb.cell(i, j).text = c
            parts.extend(b[1])
            t.cells.extend(b[1])
            for r in b[2]:
                parts.extend(r)
                t.cells.extend(r)
            parts.append(title or "Tableau")                 # titre de la diapositive du tableau
            t.headings.append(title or "Tableau")
            title, body = None, []
    flush()
    prs.save(str(path))
    t.text = "\n".join(parts)
    return t


def make_xlsx_python(doc: Doc, path: Path) -> Optional[Truth]:
    try:
        import openpyxl
    except ImportError:
        return None
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    t = Truth()
    parts: List[str] = []
    n = 0
    for b in doc.blocks:
        if b[0] != "table":
            continue
        n += 1
        name = f"Tableau {n}"
        ws = wb.create_sheet(name)
        ws.append(b[1])
        for r in b[2]:
            ws.append(r)
        parts.extend([name] + b[1] + [c for r in b[2] for c in r])
        t.headings.append(name)
        t.cells.extend(b[1])
        t.cells.extend(c for r in b[2] for c in r)
    wb.save(str(path))
    t.text = "\n".join(parts)
    return t


def make_csv(doc: Doc, path: Path) -> Optional[Truth]:
    tables = [b for b in doc.blocks if b[0] == "table"]
    if not tables:
        return None
    b = tables[0]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(b[1])
        w.writerows(b[2])
    t = Truth()
    t.cells = list(b[1]) + [c for r in b[2] for c in r]
    t.text = "\n".join(t.cells)
    return t


def _soffice() -> Optional[str]:
    return shutil.which("soffice") or shutil.which("libreoffice")


def make_with_libreoffice(doc: Doc, out_dir: Path, targets: Dict[str, str]) -> Dict[str, Truth]:
    """Produit, via LibreOffice, un fichier par format demandé à partir de la description HTML du document."""
    exe = _soffice()
    if not exe:
        return {}
    done: Dict[str, Truth] = {}
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"{doc.slug}.html"
        src.write_text(to_html(doc), encoding="utf-8")
        for ext, flt in targets.items():
            dest = Path(tmp) / f"out_{ext}"
            dest.mkdir()
            cmd = [exe, f"-env:UserInstallation=file://{tmp}/profile", "--headless", "--infilter=HTML (StarWriter)",
                   "--convert-to", flt, "--outdir", str(dest), str(src)]
            try:
                subprocess.run(cmd, capture_output=True, timeout=180, check=False)
            except (OSError, subprocess.TimeoutExpired):
                continue
            made = next(iter(dest.glob(f"{doc.slug}.*")), None)
            if made and made.stat().st_size:
                final = out_dir / f"{doc.slug}-lo.{ext}"
                shutil.copyfile(made, final)
                done[ext] = _truth(doc, with_links=(ext != "pdf"))
    return done


# format → (extension écrite, producteur)
LO_TARGETS = {"docx": "docx:MS Word 2007 XML", "odt": "odt:writer8", "rtf": "rtf:Rich Text Format", "pdf": "pdf:writer_pdf_Export"}

PYTHON_MAKERS: Dict[str, Tuple[str, Callable[[Doc, Path], Optional[Truth]]]] = {
    "html": ("html", make_html),
    "docx": ("docx", make_docx_python),
    "pptx": ("pptx", make_pptx_python),
    "xlsx": ("xlsx", make_xlsx_python),
    "csv": ("csv", make_csv),
}


def build_corpus(out_dir: Path, log: Callable[[str], None] = lambda s: None) -> List[Tuple[Path, str, str, Truth]]:
    """Écrit le corpus dans out_dir. Renvoie [(chemin, document, format, vérité)]."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files: List[Tuple[Path, str, str, Truth]] = []
    for doc in DOCS:
        for key, (ext, fn) in PYTHON_MAKERS.items():
            p = out_dir / f"{doc.slug}-py.{ext}"
            truth = fn(doc, p)
            if truth is None:
                log(f"  (ignoré : {key} pour {doc.slug} — producteur indisponible)")
                p.unlink(missing_ok=True)
                continue
            files.append((p, doc.slug, key, truth))
        for ext, truth in make_with_libreoffice(doc, out_dir, LO_TARGETS).items():
            files.append((out_dir / f"{doc.slug}-lo.{ext}", doc.slug, ext, truth))
    return files
