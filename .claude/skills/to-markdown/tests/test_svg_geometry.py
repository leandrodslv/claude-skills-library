"""Schémas SVG sans structure sémantique : les liens sont déduits de la géométrie (formes, traits, pointes, étiquettes)."""
import re

from common import Base

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300"><defs><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7"/></marker></defs>'


def box(x, y, w, h, t):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#000"/><text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle">{t}</text>'


class SvgGeometry(Base):
    def md(self, name: str, svg: str) -> str:
        p = self.tmp / name
        p.write_text(svg, encoding="utf-8")
        out = self.conv(p)
        self.assertEqual(out.status in ("ok", "needs_vision", "warn"), True, out.error)
        return out.body

    def edges(self, md: str):
        nodes = dict(re.findall(r'(\w+)\["([^"]*)"\]', md))
        return {(nodes[a], nodes[b], (lab or "")) for a, arrow, lab, b in re.findall(r"(\w+) (-->|---|<-->)(?:\|([^|]*)\|)? (\w+)", md)}

    def test_flow_with_marker_arrows_and_edge_label(self):
        svg = (HEAD + box(20, 100, 120, 50, "Début") + box(240, 100, 120, 50, "Test ?") + box(460, 100, 120, 50, "Fin")
               + '<path d="M140 125 L240 125" stroke="#000" marker-end="url(#a)"/>'
               + '<path d="M360 125 L460 125" stroke="#000" marker-end="url(#a)"/><text x="395" y="115" font-size="11">oui</text></svg>')
        md = self.md("flux.svg", svg)
        self.assertIn("déduit de la géométrie", md)
        self.assertIn("flowchart LR", md)
        self.assertEqual(self.edges(md), {("Début", "Test ?", ""), ("Test ?", "Fin", "oui")})

    def test_arrow_direction_follows_the_marker_and_swimlanes_become_subgraphs(self):
        svg = (HEAD.replace('height="300"', 'height="320"').replace("0 0 600 300", "0 0 600 320")
               + '<rect x="5" y="5" width="590" height="140" fill="#eef" stroke="#99a"/><text x="15" y="25">Équipe A</text>'
               + '<rect x="5" y="160" width="590" height="140" fill="#efe" stroke="#9a9"/><text x="15" y="180">Équipe B</text>'
               + box(40, 50, 140, 50, "Demande") + box(380, 50, 140, 50, "Archive") + box(210, 210, 150, 50, "Traitement")
               + '<path d="M110 100 L240 210" fill="none" stroke="#000" marker-start="url(#a)"/>'      # pointe côté « Demande » : le sens est inversé
               + '<path d="M360 235 L450 235 L450 100" fill="none" stroke="#000" marker-end="url(#a)"/></svg>')
        md = self.md("couloirs.svg", svg)
        self.assertEqual(self.edges(md), {("Traitement", "Demande", ""), ("Traitement", "Archive", "")})
        self.assertIn('subgraph g1["Équipe A"]', md)
        self.assertIn('subgraph g2["Équipe B"]', md)       # couloir à un seul nœud

    def test_drawn_triangle_arrowheads_give_direction(self):
        svg = (HEAD.replace("<defs>", "<defs/><g>").replace("</defs>", "") + box(20, 100, 120, 50, "Source") + box(260, 100, 120, 50, "Cible")
               + '<line x1="140" y1="125" x2="250" y2="125" stroke="#000"/><polygon points="260,125 250,120 250,130" fill="#000"/></g></svg>')
        md = self.md("pointe.svg", svg)
        self.assertEqual(self.edges(md), {("Source", "Cible", "")})

    def test_lines_without_arrowheads_are_undirected_top_to_bottom(self):
        svg = (HEAD + box(240, 20, 120, 40, "Chef") + box(60, 160, 120, 40, "Équipier 1") + box(420, 160, 120, 40, "Équipier 2")
               + '<path d="M300 60 V110 H120 V160" fill="none" stroke="#000"/><path d="M300 60 V110 H480 V160" fill="none" stroke="#000"/></svg>')
        md = self.md("arbre.svg", svg)
        self.assertEqual(self.edges(md), {("Chef", "Équipier 1", ""), ("Chef", "Équipier 2", "")})
        self.assertIn("---", md)

    def test_chart_is_not_mistaken_for_a_diagram(self):
        svg = (HEAD + '<line x1="40" y1="260" x2="560" y2="260" stroke="#000"/><line x1="40" y1="260" x2="40" y2="30" stroke="#000"/>'
               '<polyline points="40,240 200,180 360,120 520,60" fill="none" stroke="#c00"/><text x="300" y="285">Mois</text><text x="5" y="140">Ventes</text></svg>')
        md = self.md("courbe.svg", svg)
        self.assertNotIn("mermaid", md)
        self.assertIn("Ventes", md)

    def test_unattached_connectors_are_flagged_for_visual_reading_instead_of_guessing(self):
        svg = (HEAD + box(20, 20, 100, 40, "A") + box(480, 240, 100, 40, "B")
               + '<path d="M200 100 L300 100" stroke="#000" marker-end="url(#a)"/><path d="M200 150 L300 150" stroke="#000" marker-end="url(#a)"/></svg>')
        out = self.conv(self._write("flottants.svg", svg))
        self.assertNotIn("```mermaid", out.body)
        self.assertEqual(out.status, "needs_vision")
        self.assertIn("liens n'ont pas pu être déduits", out.body)

    def _write(self, name: str, svg: str):
        p = self.tmp / name
        p.write_text(svg, encoding="utf-8")
        return p

    def test_diagrams_option_text_gives_pure_markdown_and_mermaid_only_keeps_the_block(self):
        svg = HEAD + box(20, 100, 120, 50, "Début") + box(240, 100, 120, 50, "Fin") + '<path d="M140 125 L240 125" stroke="#000" marker-end="url(#a)"/></svg>'
        p = self._write("deux.svg", svg)
        both = self.conv(p).body
        self.assertIn("```mermaid", both)
        self.assertIn("| Début | → | Fin |", both)
        text = self.conv(p, diagrams="text").body
        self.assertNotIn("```mermaid", text)
        self.assertIn("| Début | → | Fin |", text)
        mer = self.conv(p, diagrams="mermaid").body
        self.assertIn("```mermaid", mer)
        self.assertNotIn("Liens du schéma", mer)

    def test_xml_comment_as_child_of_root_does_not_crash(self):
        svg = HEAD.replace("<defs>", "<!-- commentaire en tête --><defs>") + box(20, 100, 120, 50, "Un") + box(240, 100, 120, 50, "Deux") \
            + '<path d="M140 125 L240 125" stroke="#000" marker-end="url(#a)"/></svg>'
        self.assertEqual(self.edges(self.md("commentaire.svg", svg)), {("Un", "Deux", "")})

    def test_arrows_between_columns_link_the_frames_not_a_node_near_the_border(self):
        svg = (HEAD + '<rect x="10" y="20" width="200" height="250" fill="none" stroke="#000"/><text x="20" y="40">Analyse</text>'
               + box(30, 60, 160, 40, "Atelier") + box(30, 120, 160, 40, "Synthèse")
               + '<rect x="290" y="20" width="200" height="250" fill="none" stroke="#000"/><text x="300" y="40">Conception</text>'
               + box(310, 60, 160, 40, "Maquette") + box(310, 120, 160, 40, "Prototype")
               + '<path d="M210 140 L290 140" stroke="#000" marker-end="url(#a)"/></svg>')
        md = self.md("colonnes.svg", svg)
        self.assertIn("g1 --> g2", md)
        self.assertNotIn("n5", md.replace("flowchart", ""))      # aucun nœud anonyme créé pour une extrémité de cadre
        self.assertIn("| Analyse | → | Conception |", md)

    @staticmethod
    def plain_edges(md: str):
        """Liens d'un bloc Mermaid dont les formes (rondes, losanges, cylindres…) sont ramenées à des libellés."""
        nodes = {k: v for k, v in re.findall(r'(\w+)(?:\[\(|\(\[|\(\(|\{|\(|\[)"([^"]*)"', md)}
        return {(nodes[a], nodes[b], (lab or "")) for a, _arrow, lab, b in re.findall(r"(\w+) (-->|---|<-->)(?:\|([^|]*)\|)? (\w+)", md)}

    def test_decision_diamond_database_cylinder_and_round_shapes_keep_their_look(self):
        svg = (HEAD + '<rect x="20" y="20" width="120" height="50" rx="8" fill="none" stroke="#000"/><text x="80" y="50" text-anchor="middle">Début</text>'
               '<polygon points="300,20 380,60 300,100 220,60" fill="none" stroke="#000"/><text x="300" y="64" text-anchor="middle">Valide ?</text>'
               '<path d="M450 20 C450 8 530 8 530 20 L530 90 C530 102 450 102 450 90 Z" fill="none" stroke="#000"/><text x="490" y="60" text-anchor="middle">Base</text>'
               '<path d="M140 45 L220 55" stroke="#000" marker-end="url(#a)"/><path d="M380 60 L450 60" stroke="#000" marker-end="url(#a)"/></svg>')
        md = self.md("formes.svg", svg)
        self.assertIn('("Début")', md)
        self.assertIn('{"Valide ?"}', md)
        self.assertIn('[("Base")]', md)
        self.assertIn("**Décisions (losanges) :** Valide ?", md)
        self.assertEqual(self.plain_edges(md), {("Début", "Valide ?", ""), ("Valide ?", "Base", "")})

    def test_shapes_without_text_become_nodes_with_their_caption_or_a_placeholder_name(self):
        svg = (HEAD + '<circle cx="60" cy="100" r="25" fill="#9cf" stroke="#000"/><text x="60" y="150" text-anchor="middle">Capteur</text>'
               '<circle cx="300" cy="100" r="25" fill="#fc9" stroke="#000"/><text x="300" y="150" text-anchor="middle">Passerelle</text>'
               '<circle cx="540" cy="100" r="25" fill="#cf9" stroke="#000"/>'
               '<path d="M85 100 L275 100" stroke="#000" marker-end="url(#a)"/><path d="M325 100 L515 100" stroke="#000" marker-end="url(#a)"/></svg>')
        md = self.md("icones.svg", svg)
        self.assertEqual(self.plain_edges(md), {("Capteur", "Passerelle", ""), ("Passerelle", "forme sans texte n°1 (cercle)", "")})

    def test_bar_chart_with_axes_is_not_a_diagram_even_though_shapes_and_lines_touch(self):
        svg = (HEAD + '<line x1="40" y1="260" x2="560" y2="260" stroke="#000"/><line x1="40" y1="260" x2="40" y2="30" stroke="#000"/>'
               + "".join(f'<rect x="{70 + i * 90}" y="{260 - h}" width="50" height="{h}" fill="#69c"/>' for i, h in enumerate((80, 120, 160, 200)))
               + '<text x="300" y="285">Trimestres</text></svg>')
        md = self.md("barres.svg", svg)
        self.assertNotIn("mermaid", md)
