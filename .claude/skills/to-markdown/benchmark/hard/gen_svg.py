"""Schémas SVG dessinés sans structure sémantique : les liens doivent être déduits de la géométrie."""
from __future__ import annotations

from typing import List

from gen_common import OUT, Case

NS = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
ARROW = '<marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7"/></marker>'


def build() -> List[Case]:
    d = OUT / "svg"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []

    # 1. flux avec classes CSS, rectangles sans remplissage, polylignes à marqueur CSS, texte aligné à gauche, étiquettes
    svg = f"""<svg {NS} width="640" height="300" viewBox="0 0 640 300"><style>.box{{fill:none;stroke:#333;stroke-width:2}}.edge{{fill:none;stroke:#333;marker-end:url(#arr)}}.t{{font-size:14px;font-family:sans-serif}}.l{{font-size:11px;fill:#555}}</style>
<defs>{ARROW}</defs>
<rect class="box" x="30" y="40" width="140" height="56"/><text class="t" x="46" y="73">Saisie commande</text>
<rect class="box" x="250" y="40" width="140" height="56"/><text class="t" x="270" y="73">Contrôle stock</text>
<rect class="box" x="470" y="40" width="140" height="56"/><text class="t" x="490" y="73">Préparation</text>
<rect class="box" x="250" y="200" width="140" height="56"/><text class="t" x="262" y="233">Réapprovisionner</text>
<rect class="box" x="470" y="200" width="140" height="56"/><text class="t" x="490" y="233">Expédition</text>
<polyline class="edge" points="170,68 250,68"/><polyline class="edge" points="390,68 470,68"/><text class="l" x="402" y="60">en stock</text>
<polyline class="edge" points="320,96 320,200"/><text class="l" x="328" y="150">rupture</text>
<polyline class="edge" points="540,96 540,200"/><polyline class="edge" points="390,228 470,228"/></svg>"""
    (d / "flux-classes-css.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-flux-classes-css", d / "flux-classes-css.svg", "svg", 3, "rectangles sans remplissage, flèches par classe CSS (marker-end dans <style>), texte aligné à gauche, étiquettes de liens",
                      must=["Saisie commande", "Contrôle stock", "Préparation", "Réapprovisionner", "Expédition", "en stock", "rupture"],
                      edges=[["Saisie commande", "Contrôle stock"], ["Contrôle stock", "Préparation", "en stock"], ["Contrôle stock", "Réapprovisionner", "rupture"],
                             ["Préparation", "Expédition"], ["Réapprovisionner", "Expédition"]],
                      notes="Attendu : un flowchart Mermaid avec les 5 liens, orientés, dont 2 étiquetés."))

    # 2. couloirs (swimlanes) avec liens qui les traversent
    svg = f"""<svg {NS} width="700" height="360" viewBox="0 0 700 360"><defs>{ARROW}</defs>
<g font-family="sans-serif" font-size="13">
<rect x="10" y="10" width="680" height="100" fill="#f4f8ff" stroke="#99a"/><text x="20" y="30" font-weight="bold">Client</text>
<rect x="10" y="125" width="680" height="100" fill="#f4fff4" stroke="#9a9"/><text x="20" y="145" font-weight="bold">Support</text>
<rect x="10" y="240" width="680" height="100" fill="#fff8f0" stroke="#a98"/><text x="20" y="260" font-weight="bold">Technique</text>
<rect x="60" y="45" width="150" height="45" rx="6" fill="#fff" stroke="#333"/><text x="135" y="72" text-anchor="middle">Ouvre un ticket</text>
<rect x="480" y="45" width="160" height="45" rx="6" fill="#fff" stroke="#333"/><text x="560" y="72" text-anchor="middle">Reçoit la solution</text>
<rect x="230" y="160" width="170" height="45" rx="6" fill="#fff" stroke="#333"/><text x="315" y="187" text-anchor="middle">Qualifie la demande</text>
<rect x="230" y="275" width="170" height="45" rx="6" fill="#fff" stroke="#333"/><text x="315" y="302" text-anchor="middle">Analyse et corrige</text>
<path d="M135 90 L260 160" stroke="#333" fill="none" marker-end="url(#arr)"/>
<path d="M315 205 L315 275" stroke="#333" fill="none" marker-end="url(#arr)"/>
<path d="M400 297 L560 297 L560 90" stroke="#333" fill="none" marker-end="url(#arr)"/></g></svg>"""
    (d / "couloirs-processus.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-couloirs-processus", d / "couloirs-processus.svg", "svg", 4, "trois couloirs (cadres nommés) dont un ne contient qu'un seul nœud ; liens qui traversent les couloirs, un chemin coudé",
                      must=["Client", "Support", "Technique", "Ouvre un ticket", "Reçoit la solution", "Qualifie la demande", "Analyse et corrige"],
                      edges=[["Ouvre un ticket", "Qualifie la demande"], ["Qualifie la demande", "Analyse et corrige"], ["Analyse et corrige", "Reçoit la solution"]],
                      groups=[["Client", ["Ouvre un ticket", "Reçoit la solution"]], ["Support", ["Qualifie la demande"]], ["Technique", ["Analyse et corrige"]]],
                      notes="Les couloirs doivent devenir des sous-graphes (subgraph), pas des nœuds."))

    # 3. architecture : ellipse, cylindre, courbes de Bézier, flèche bidirectionnelle, texte sur deux lignes
    svg = f"""<svg {NS} width="720" height="300" viewBox="0 0 720 300"><defs>{ARROW}<marker id="arr0" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto"><polygon points="10 0,0 3.5,10 7"/></marker></defs>
<g font-family="sans-serif" font-size="13" stroke="#333" fill="#fff">
<ellipse cx="70" cy="150" rx="55" ry="30"/><text x="70" y="154" text-anchor="middle" stroke="none" fill="#000">Navigateur</text>
<rect x="200" y="120" width="130" height="60"/><text x="265" y="146" text-anchor="middle" stroke="none" fill="#000"><tspan x="265">API</tspan><tspan x="265" dy="16">Gateway</tspan></text>
<rect x="420" y="30" width="130" height="50"/><text x="485" y="60" text-anchor="middle" stroke="none" fill="#000">Service Auth</text>
<rect x="420" y="220" width="150" height="50"/><text x="495" y="250" text-anchor="middle" stroke="none" fill="#000">Service Commandes</text>
<path d="M630 110 C630 90 700 90 700 110 L700 190 C700 210 630 210 630 190 Z"/><text x="665" y="155" text-anchor="middle" stroke="none" fill="#000">Base SQL</text>
<path d="M125 150 L200 150" fill="none" marker-end="url(#arr)"/><text x="162" y="140" text-anchor="middle" stroke="none" fill="#000" font-size="11">HTTPS</text>
<path d="M300 120 C330 80 380 55 420 55" fill="none" marker-start="url(#arr0)" marker-end="url(#arr)"/>
<path d="M300 180 C330 220 380 245 420 245" fill="none" marker-end="url(#arr)"/>
<path d="M570 245 C600 245 620 205 650 195" fill="none" marker-end="url(#arr)"/></g></svg>"""
    (d / "architecture-courbes.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-architecture-courbes", d / "architecture-courbes.svg", "svg", 4, "ellipse, cylindre (chemin fermé à courbes), liens en courbes de Bézier, flèche bidirectionnelle, libellé sur deux lignes",
                      must=["Navigateur", "API Gateway", "Service Auth", "Service Commandes", "Base SQL", "HTTPS"],
                      edges=[["Navigateur", "API", "HTTPS"], ["API", "Service Auth", "", "<>"], ["API", "Service Commandes"], ["Service Commandes", "Base SQL"]]))

    # 4. organigramme : coudes en chemins H/V, aucune pointe de flèche (liens non orientés)
    box = lambda x, y, w, h, t: f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#eef" stroke="#336"/><text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle">{t}</text>'  # noqa: E731
    svg = f"""<svg {NS} width="700" height="340" viewBox="0 0 700 340"><g font-family="sans-serif" font-size="13">
{box(260, 20, 180, 50, "Direction générale")}{box(40, 150, 140, 50, "Technique")}{box(280, 150, 140, 50, "Commercial")}{box(520, 150, 140, 50, "Finance")}
{box(20, 260, 100, 45, "Infra")}{box(140, 260, 100, 45, "Dev")}
<g stroke="#336" fill="none"><path d="M350 70 V110 H110 V150"/><path d="M350 70 V150"/><path d="M350 70 V110 H590 V150"/>
<path d="M110 200 V230 H70 V260"/><path d="M110 200 V230 H190 V260"/></g></g></svg>"""
    (d / "organigramme-coudes.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-organigramme-coudes", d / "organigramme-coudes.svg", "svg", 3, "arbre à trois niveaux, connecteurs coudés (V/H) sans pointe de flèche",
                      must=["Direction générale", "Technique", "Commercial", "Finance", "Infra", "Dev"],
                      edges=[["Direction générale", "Technique", "", "-"], ["Direction générale", "Commercial", "", "-"], ["Direction générale", "Finance", "", "-"],
                             ["Technique", "Infra", "", "-"], ["Technique", "Dev", "", "-"]],
                      notes="Sans pointe, le sens n'est pas connu : lien non orienté (---) du haut vers le bas."))

    # 5. pointes de flèche dessinées (triangles), pas de marqueur
    tri = lambda x, y, d_: {"r": f'<polygon points="{x},{y} {x - 10},{y - 5} {x - 10},{y + 5}"/>', "d": f'<polygon points="{x},{y} {x - 5},{y - 10} {x + 5},{y - 10}"/>'}[d_]  # noqa: E731
    svg = f"""<svg {NS} width="620" height="220" viewBox="0 0 620 220"><g font-family="sans-serif" font-size="14" fill="#222" stroke="#222">
<rect x="20" y="70" width="130" height="50" fill="#fff"/><text x="85" y="100" text-anchor="middle" stroke="none">Capteur</text>
<rect x="240" y="70" width="130" height="50" fill="#fff"/><text x="305" y="100" text-anchor="middle" stroke="none">Passerelle</text>
<rect x="460" y="70" width="130" height="50" fill="#fff"/><text x="525" y="100" text-anchor="middle" stroke="none">Cloud</text>
<rect x="240" y="160" width="130" height="45" fill="#fff"/><text x="305" y="187" text-anchor="middle" stroke="none">Alarme locale</text>
<line x1="150" y1="95" x2="230" y2="95"/>{tri(240, 95, "r")}<line x1="370" y1="95" x2="450" y2="95"/>{tri(460, 95, "r")}
<line x1="305" y1="120" x2="305" y2="150"/>{tri(305, 160, "d").replace("points", "points")}</g></svg>"""
    (d / "pointes-dessinees.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-pointes-dessinees", d / "pointes-dessinees.svg", "svg", 3, "les flèches n'ont pas de marqueur : la pointe est un petit triangle dessiné à part",
                      must=["Capteur", "Passerelle", "Cloud", "Alarme locale"],
                      edges=[["Capteur", "Passerelle"], ["Passerelle", "Cloud"], ["Passerelle", "Alarme locale"]]))

    # 6. faux positif : un graphique (axes, courbe) ne doit pas devenir un schéma
    svg = f"""<svg {NS} width="500" height="320" viewBox="0 0 500 320"><g font-family="sans-serif" font-size="12">
<text x="250" y="24" text-anchor="middle" font-size="16">Ventes mensuelles 2025</text>
<line x1="60" y1="270" x2="470" y2="270" stroke="#000"/><line x1="60" y1="270" x2="60" y2="50" stroke="#000"/>
<polyline points="60,240 130,200 200,215 270,150 340,120 410,90" fill="none" stroke="#c33" stroke-width="2"/>
<text x="130" y="288">Févr.</text><text x="270" y="288">Avr.</text><text x="410" y="288">Juin</text><text x="20" y="150">k€</text>
<text x="415" y="82">142 k€</text></g></svg>"""
    (d / "graphique-courbe.svg").write_text(svg, encoding="utf-8")
    cases.append(Case("svg-graphique-courbe", d / "graphique-courbe.svg", "svg", 3, "graphique en courbe : axes, polyligne de données, libellés — ne doit PAS être pris pour un schéma de flux",
                      must=["Ventes mensuelles 2025", "Févr.", "Avr.", "Juin", "142 k€"], absent=["flowchart", "mermaid"],
                      notes="Pas de diagramme inventé ; le texte est restitué ; les valeurs de la courbe elle-même se lisent sur le rendu."))
    return cases
