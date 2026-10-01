"""Web et assimilés difficiles : page HTML « du monde réel », HTML structurel tordu, e-mail multipartie, notebook, EPUB, SVG, draw.io."""
from __future__ import annotations

import base64
import io
import json
from email.message import EmailMessage
from email.utils import formatdate
from typing import List

from gen_common import OUT, Case, write_zip


def _png_b64(text: str) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    img = Image.new("RGB", (640, 220), "white")
    ImageDraw.Draw(img).text((20, 80), text, fill="black", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34))
    b = io.BytesIO()
    img.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def build() -> List[Case]:
    d = OUT / "web"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []

    # 1. page d'article avec tout le bruit du web
    html = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Les abeilles urbaines prospèrent | Le Journal Vert</title>
<meta name="description" content="Enquête sur les ruches installées sur les toits."><style>.nav{display:flex}.cookie{position:fixed}</style>
<script>window.dataLayer=[{event:'pageview',secret:'TRACKER-XYZ-123'}];</script></head><body>
<div class="cookie" id="cookie-banner"><p>Nous utilisons des cookies. <button>Accepter les cookies</button> <button>Refuser</button></p></div>
<header><nav class="nav"><a href="/">Accueil</a> <a href="/rubriques">Menu principal</a> <a href="/abonnement">S'abonner à la newsletter</a></nav></header>
<aside class="ad"><p>Publicité : offrez-vous une ruche connectée</p></aside>
<main><article><h1>Les abeilles urbaines prospèrent</h1><p class="byline">Par Claire Fontaine · 3 mai 2025</p>
<p>Sur les toits de Lyon, trente-deux ruches abritent plus d'un million d'abeilles. Les apiculteurs urbains constatent des rendements supérieurs de quinze pour cent à ceux des campagnes voisines.</p>
<h2>Pourquoi la ville leur réussit</h2><p>La diversité florale des parcs et des balcons, associée à des hivers plus doux, explique en grande partie ces résultats.</p>
<figure><img src="ruche.jpg" alt="Ruche sur un toit lyonnais"><figcaption>Une ruche installée sur le toit de l'hôtel de ville.</figcaption></figure>
<blockquote><p>« Nous récoltons en moyenne vingt-huit kilos de miel par ruche », témoigne un apiculteur.</p></blockquote>
<h2>Les limites</h2><ul><li>Pollution aux particules fines</li><li>Concurrence avec les abeilles sauvages</li><li>Manque de ressources en fin d'été</li></ul></article></main>
<section class="related"><h3>Articles liés</h3><ul><li><a href="/a1">Le retour des vers de terre</a></li><li><a href="/a2">Jardins partagés : bilan</a></li></ul></section>
<section class="comments"><h3>Commentaires (3)</h3><p>Jean : super article !</p></section>
<footer><p>© 2025 Le Journal Vert — Tous droits réservés</p><a href="/mentions">Mentions légales</a></footer></body></html>"""
    (d / "article-web-bruite.html").write_text(html, encoding="utf-8")
    cases.append(Case("web-article-bruite", d / "article-web-bruite.html", "web", 3, "article noyé dans le bruit : bandeau cookies, menu, publicité, articles liés, commentaires, pied de page, script",
                      must=["Sur les toits de Lyon, trente-deux ruches", "La diversité florale des parcs et des balcons", "Une ruche installée sur le toit de l'hôtel de ville", "vingt-huit kilos de miel par ruche",
                            "Pollution aux particules fines", "Manque de ressources en fin d'été"],
                      absent=["Accepter les cookies", "Menu principal", "Publicité : offrez-vous une ruche connectée", "TRACKER-XYZ-123", "Tous droits réservés", "Jean : super article"],
                      headings=["Les abeilles urbaines prospèrent", "Pourquoi la ville leur réussit", "Les limites"], items=["Pollution aux particules fines", "Concurrence avec les abeilles sauvages"],
                      notes="Seul l'article doit rester ; le script, le bandeau et la navigation sont du bruit. Les « articles liés » et les commentaires sont discutables mais ne doivent pas se mêler au corps."))

    # 2. HTML structurel tordu
    svg_label = "Schéma : trois étapes du procédé"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Spécification technique</title></head><body>
<table width="100%" border="0"><tr><td width="20%" valign="top"><b>Sommaire</b><br>1. Principe<br>2. Mise en œuvre</td>
<td><table><tr><td><h1>Spécification du module de calcul</h1><p>Ce document décrit le comportement attendu du module.</p></td></tr></table></td></tr></table>
<details><summary>Pré-requis (cliquer pour déplier)</summary><p>Python 3.11 ou supérieur et 2 Go de mémoire vive.</p></details>
<dl><dt>Tolérance</dt><dd>Écart maximal admissible : 0,5 %</dd><dt>Horizon</dt><dd>Prévision à douze mois</dd></dl>
<pre><code>def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a</code></pre>
<table><thead><tr><th rowspan="2">Mode</th><th colspan="2">Performance</th></tr><tr><th>Débit</th><th>Latence</th></tr></thead>
<tbody><tr><td>Normal</td><td>1 200 req/s</td><td>12 ms</td></tr><tr><td>Dégradé</td><td>300 req/s</td><td>85 ms</td></tr></tbody></table>
<p>Prix : 12&nbsp;€ HT &mdash; soit 14,40&nbsp;€ TTC ; r&eacute;f&eacute;rence caf&eacute; &amp; th&eacute;.</p>
<blockquote>Citation principale<blockquote>Citation imbriquée de second niveau</blockquote></blockquote>
<svg width="300" height="80" xmlns="http://www.w3.org/2000/svg"><text x="10" y="40">{svg_label}</text></svg>
<p>Équation : <math><mfrac><mi>a</mi><mi>b</mi></mfrac><mo>=</mo><mn>0,75</mn></math></p>
<p>Ligne un<br>Ligne deux<br>Ligne trois</p>
<p><img alt="Courbe de charge en fonction du temps" src="data:image/png;base64,{_png_b64('Courbe de charge')}"></p></body></html>"""
    (d / "html-structure-tordue.html").write_text(html, encoding="utf-8")
    cases.append(Case("web-html-structure-tordue", d / "html-structure-tordue.html", "web", 4, "table de mise en page imbriquée, details, dl, code indenté, tableau à en-têtes fusionnés, entités, SVG, MathML, image en base64",
                      must=["Spécification du module de calcul", "Pré-requis", "Python 3.11 ou supérieur et 2 Go de mémoire vive", "Écart maximal admissible : 0,5 %", "Prévision à douze mois",
                            "def fibonacci(n):", "a, b = b, a + b", "12 € HT", "14,40 € TTC", "café & thé", "Citation principale", "Citation imbriquée de second niveau", svg_label, "Courbe de charge en fonction du temps", "Ligne deux"],
                      any_of=[["a/b", "a b = 0,75", "\\frac{a}{b}", "a / b", "a b"]],
                      rows=[["Normal", "1 200 req/s", "12 ms"], ["Dégradé", "300 req/s", "85 ms"]], headings=["Spécification du module de calcul"],
                      notes="Le code doit garder son indentation (bloc de code) ; la table de mise en page ne doit pas devenir un tableau de données ; l'équation et le texte du SVG ne doivent pas disparaître."))

    # 3. e-mail multipartie complexe
    msg = EmailMessage()
    msg["Subject"] = "Réunion décalée : projet Éole — pièces jointes ✔"
    msg["From"] = "Amélie Rousseau <amelie.rousseau@exemple.fr>"
    msg["To"] = "equipe@exemple.fr"
    msg["Date"] = formatdate(1746000000)
    msg.set_content("Bonjour à tous,\n\nLa réunion du projet Éole est décalée au jeudi 15 mai à 14 h 30, salle Mistral.\nMerci de confirmer votre présence avant mardi.\n\nAmélie")
    msg.add_alternative("""<html><body><p>Bonjour à tous,</p><p>La réunion du projet <b>Éole</b> est décalée au <b>jeudi 15 mai à 14 h 30</b>, salle Mistral.</p>
<table border="1"><tr><th>Point</th><th>Responsable</th></tr><tr><td>Bilan budgétaire</td><td>Nicolas</td></tr><tr><td>Planning de recette</td><td>Inès</td></tr></table>
<p>Merci de confirmer votre présence avant mardi.</p><p>Amélie</p></body></html>""", subtype="html")
    msg.add_attachment("Notes de préparation\n- Vérifier le budget restant : 18 400 euros\n- Imprimer l'ordre du jour\n".encode("utf-8"), maintype="text", subtype="plain", filename="notes-préparation.txt")
    inner = EmailMessage()
    inner["Subject"] = "TR: Validation du devis fournisseur"
    inner["From"] = "fournisseur@exemple.com"
    inner.set_content("Le devis numéro 2025-0417 d'un montant de 18 400 euros est valable jusqu'au 30 juin.")
    msg.add_attachment(inner)
    (d / "email-multipartie.eml").write_bytes(msg.as_bytes())
    cases.append(Case("web-email-multipartie", d / "email-multipartie.eml", "web", 4, "sujet encodé, corps texte + HTML, tableau, pièce jointe texte, e-mail transféré en pièce jointe",
                      must=["Réunion décalée : projet Éole", "jeudi 15 mai à 14 h 30, salle Mistral", "Bilan budgétaire", "Nicolas", "Planning de recette", "notes-préparation.txt",
                            "Vérifier le budget restant : 18 400 euros", "Validation du devis fournisseur", "devis numéro 2025-0417", "Amélie Rousseau"],
                      once=["Merci de confirmer votre présence avant mardi"], rows=[["Bilan budgétaire", "Nicolas"], ["Planning de recette", "Inès"]],
                      notes="Un seul corps (texte OU HTML, pas les deux dupliqués) ; les pièces jointes texte et le message transféré doivent être lus."))

    # 4. notebook Jupyter
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Analyse des ventes\n", "\n", "On étudie l'évolution mensuelle avec $\\bar{x} = \\frac{1}{n}\\sum x_i$.\n"]},
        {"cell_type": "code", "metadata": {}, "execution_count": 1, "source": ["import pandas as pd\n", "df = pd.read_csv('ventes.csv')\n", "df.describe()"],
         "outputs": [{"output_type": "execute_result", "execution_count": 1, "metadata": {}, "data": {"text/plain": ["       montant\n", "count   120.0\n", "mean   1520.5"],
                      "text/html": ["<table><tr><th>stat</th><th>montant</th></tr><tr><td>count</td><td>120.0</td></tr><tr><td>mean</td><td>1520.5</td></tr></table>"]}}]},
        {"cell_type": "code", "metadata": {}, "execution_count": 2, "source": ["print('Total :', df.montant.sum())\n", "1/0"],
         "outputs": [{"output_type": "stream", "name": "stdout", "text": ["Total : 182460.0\n"]}, {"output_type": "error", "ename": "ZeroDivisionError", "evalue": "division by zero", "traceback": ["ZeroDivisionError: division by zero"]}]},
        {"cell_type": "code", "metadata": {}, "execution_count": 3, "source": ["plt.plot(df.montant)"], "outputs": [{"output_type": "display_data", "metadata": {}, "data": {"image/png": _png_b64("Graphique des ventes"), "text/plain": ["<Figure size 640x480>"]}}]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Conclusion\n", "Les ventes progressent de **12 %** sur l'année."]}]}
    (d / "notebook-sorties.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    cases.append(Case("web-notebook-sorties", d / "notebook-sorties.ipynb", "web", 3, "cellules Markdown/code, sorties texte, HTML, erreur, image ; formule LaTeX",
                      must=["Analyse des ventes", "df = pd.read_csv('ventes.csv')", "Total : 182460.0", "ZeroDivisionError: division by zero", "Les ventes progressent de 12 % sur l'année", "1520.5"],
                      any_of=[["\\frac{1}{n}", "frac{1}{n}"]], headings=["Analyse des ventes", "Conclusion"],
                      notes="Le code et les sorties doivent être distingués (blocs de code) ; la sortie HTML ne doit pas être dupliquée avec son équivalent texte."))

    # 5. EPUB avec chapitres, notes et table des matières
    chap = lambda n, t, body: (f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{t}</title></head><body><h1>{t}</h1>{body}</body></html>')  # noqa: E731
    parts = {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "OEBPS/content.opf": ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                              '<dc:identifier id="id">urn:uuid:1234</dc:identifier><dc:title>Le voyage de Salomé</dc:title><dc:creator>Marc Delorme</dc:creator><dc:language>fr</dc:language></metadata>'
                              '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>'
                              '<item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/><item id="c3" href="c3.xhtml" media-type="application/xhtml+xml"/></manifest>'
                              '<spine><itemref idref="c1"/><itemref idref="c2"/><itemref idref="c3"/></spine></package>'),
        "OEBPS/nav.xhtml": '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="c1.xhtml">Le départ</a></li><li><a href="c2.xhtml">La traversée</a></li><li><a href="c3.xhtml">L\'arrivée</a></li></ol></nav></body></html>',
        "OEBPS/c1.xhtml": chap(1, "Le départ", '<p>Salomé ferma la porte de la maison pour la dernière fois<a epub:type="noteref" href="#n1">1</a>. Le train partait à l\'aube.</p><aside epub:type="footnote" id="n1"><p>Note : la maison fut vendue en 1952.</p></aside>'),
        "OEBPS/c2.xhtml": chap(2, "La traversée", '<p>La mer était calme le premier jour. Puis vint la tempête qui dura trois nuits.</p><p><em>Elle écrivait chaque soir dans son carnet.</em></p>'),
        "OEBPS/c3.xhtml": chap(3, "L'arrivée", '<p>Le port de Marseille apparut dans la brume matinale. Salomé retrouva enfin son frère Gabriel.</p>'),
    }
    path = d / "livre-chapitres-notes.epub"
    path.parent.mkdir(parents=True, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", parts.pop("mimetype"), zipfile.ZIP_STORED)
        for n, c in parts.items():
            z.writestr(n, c, zipfile.ZIP_DEFLATED)
    cases.append(Case("web-epub-chapitres-notes", path, "web", 3, "EPUB 3 : ordre de lecture (spine), table des matières, note de fin liée, métadonnées",
                      must=["Le voyage de Salomé", "Marc Delorme", "Salomé ferma la porte de la maison", "Note : la maison fut vendue en 1952", "La mer était calme le premier jour", "Elle écrivait chaque soir dans son carnet", "Gabriel"],
                      order=["Le départ", "Salomé ferma la porte", "La traversée", "La mer était calme", "L'arrivée", "Le port de Marseille"],
                      headings=["Le départ", "La traversée", "L'arrivée"]))

    # 6. SVG de diagramme (groupes, transformations, tspans, texte sur chemin) et draw.io
    svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="700" height="400" viewBox="0 0 700 400">
<title>Processus de validation</title><defs><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7"/></marker></defs>
<g transform="translate(20,20)"><rect x="0" y="0" width="150" height="60" rx="8" fill="#cfe"/><text x="75" y="35" text-anchor="middle">Demande reçue</text></g>
<g transform="translate(250,20)"><polygon points="75,0 150,40 75,80 0,40" fill="#fec"/><text x="75" y="44" text-anchor="middle"><tspan>Montant</tspan><tspan x="75" dy="14">supérieur à 5 k€ ?</tspan></text></g>
<g transform="translate(520,0)"><rect width="150" height="60" rx="8" fill="#fcc"/><text x="75" y="35" text-anchor="middle">Validation direction</text></g>
<g transform="translate(520,140)"><rect width="150" height="60" rx="8" fill="#cef"/><text x="75" y="35" text-anchor="middle">Validation manager</text></g>
<g transform="translate(250,280)"><rect width="150" height="60" rx="8" fill="#eee"/><text x="75" y="35" text-anchor="middle">Archivage</text></g>
<line x1="170" y1="50" x2="250" y2="60" stroke="black" marker-end="url(#a)"/><line x1="400" y1="50" x2="520" y2="30" stroke="black" marker-end="url(#a)"/>
<line x1="400" y1="70" x2="520" y2="170" stroke="black" marker-end="url(#a)"/><path d="M595 200 L595 300 L400 310" fill="none" stroke="black" marker-end="url(#a)"/>
<text x="440" y="25" font-size="11">oui</text><text x="440" y="120" font-size="11">non</text>
<path id="p" d="M20 380 L680 380" fill="none"/><text><textPath xlink:href="#p">Légende : les montants s'entendent hors taxes</textPath></text></svg>"""
    (d / "diagramme-processus.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("web-svg-processus", d / "diagramme-processus.svg", "web", 4, "diagramme SVG : groupes transformés, losange, tspans multilignes, flèches, texte sur chemin",
                      must=["Demande reçue", "supérieur à 5 k€", "Validation direction", "Validation manager", "Archivage", "oui", "non", "Légende : les montants s'entendent hors taxes", "Processus de validation"],
                      notes="Idéal : un flowchart Mermaid reflétant les flèches (Demande → Montant ? → direction / manager → Archivage) ; au minimum tous les libellés."))
    drawio = """<mxfile><diagram name="Séquence de livraison"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="a" value="Commande client" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="40" y="40" width="120" height="50" as="geometry"/></mxCell>
<mxCell id="b" value="Préparation&lt;br&gt;entrepôt" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="240" y="40" width="120" height="50" as="geometry"/></mxCell>
<mxCell id="c" value="Expédition" style="ellipse;" vertex="1" parent="1"><mxGeometry x="440" y="40" width="120" height="50" as="geometry"/></mxCell>
<mxCell id="e1" value="validée" edge="1" source="a" target="b" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e2" value="colis prêt" edge="1" source="b" target="c" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell></root></mxGraphModel></diagram></mxfile>"""
    (d / "sequence-livraison.drawio").write_text(drawio, encoding="utf-8")
    cases.append(Case("web-drawio-sequence", d / "sequence-livraison.drawio", "web", 3, "diagramme draw.io : sommets, arêtes étiquetées, retour à la ligne HTML dans un libellé",
                      must=["Commande client", "Préparation", "entrepôt", "Expédition", "validée", "colis prêt"], order=["Commande client", "Préparation", "Expédition"]))
    _ = write_zip
    return cases
