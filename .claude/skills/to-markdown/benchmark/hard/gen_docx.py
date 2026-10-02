"""Word difficiles : listes imbriquées, cellules fusionnées, notes, révisions, zones de texte, RTL/CJK, équations."""
from __future__ import annotations

from typing import List

from gen_common import OUT, W_NS, Case, cell, make_docx, num_p, p, table, x


def build() -> List[Case]:
    d = OUT / "docx"
    cases: List[Case] = []

    # 1. listes imbriquées sur 4 niveaux, numérotation continue
    items = [("Préparer le terrain", 0), ("Relever les cotes", 1), ("Mesures au laser", 2), ("Contrôle par recoupement", 2), ("Vérifier les réseaux", 1),
             ("Couler la dalle", 0), ("Armatures", 1), ("Treillis soudé", 2), ("Coffrage périphérique", 3), ("Béton", 1), ("Séchage de vingt-huit jours", 0)]
    body = p("Plan de chantier", "Title") + p("Étapes", "Heading1") + "".join(num_p(t, 1, lv) for t, lv in items)
    body += p("Rappels", "Heading1") + num_p("Port du casque obligatoire", 2, 0) + num_p("Balisage des zones de levage", 2, 1) + num_p("Contrôle des échafaudages chaque matin", 2, 1)
    make_docx(d / "listes-imbriquees.docx", body)
    cases.append(Case("docx-listes-imbriquees", d / "listes-imbriquees.docx", "docx", 3, "listes à 4 niveaux, numérotation continue, puces mêlées aux numéros",
                      items=[t for t, _ in items] + ["Port du casque obligatoire", "Balisage des zones de levage", "Contrôle des échafaudages chaque matin"],
                      order=[t for t, _ in items], headings=["Plan de chantier", "Étapes", "Rappels"],
                      levels=[[t, lv] for t, lv in items] + [["Port du casque obligatoire", 0], ["Balisage des zones de levage", 1], ["Contrôle des échafaudages chaque matin", 1]],
                      notes="L'indentation doit refléter les niveaux (sous-listes), pas seulement le texte."))

    # 2. tableaux à cellules fusionnées, tableau imbriqué
    nested = table([cell(p("Dont France"), width=1500) + cell(p("48 %"), width=1500)], 2)
    rows = [
        cell(p("Zone"), vmerge="restart") + cell(p("Résultats 2025"), span=2) + cell(p("Prévisions 2026")),
        cell("", vmerge="continue") + cell(p("T1")) + cell(p("T2")) + cell(p("Année")),
        cell(p("Europe"), vmerge="restart") + cell(p("1 204")) + cell(p("1 310")) + cell(p("5 100")),
        cell("", vmerge="continue") + cell(p("Détail pays") + nested, span=3),
        cell(p("Asie")) + cell(p("980")) + cell(p("1 022")) + cell(p("4 200")),
    ]
    make_docx(d / "tableaux-fusionnes.docx", p("Chiffre d'affaires par zone", "Heading1") + table(rows) + p("Source : direction financière."))
    cases.append(Case("docx-tableaux-fusionnes", d / "tableaux-fusionnes.docx", "docx", 4, "en-têtes fusionnés horizontalement et verticalement, tableau dans une cellule",
                      cells=["Zone", "Résultats 2025", "Prévisions 2026", "T1", "T2", "Année", "Europe", "1 204", "1 310", "5 100", "Asie", "980", "1 022", "4 200", "Dont France", "48 %"],
                      rows=[["Europe", "1 204", "1 310", "5 100"], ["Asie", "980", "1 022", "4 200"], ["Dont France", "48 %"], ["Zone", "T1"]],
                      must=["Détail pays", "Source : direction financière"], headings=["Chiffre d'affaires par zone"],
                      notes="Les valeurs doivent rester rattachées à la bonne colonne ; le tableau imbriqué ne doit pas disparaître."))

    # 3. notes de bas de page, de fin, commentaires, révisions
    fn = lambda i: f'<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteReference w:id="{i}"/></w:r>'  # noqa: E731
    en = '<w:r><w:endnoteReference w:id="2"/></w:r>'
    body = (p("Étude de cas", "Heading1")
            + p("", runs=f'<w:r><w:t xml:space="preserve">Le taux de rebut a baissé de 12 % en un an</w:t></w:r>{fn(2)}<w:r><w:t xml:space="preserve"> grâce au nouveau procédé</w:t></w:r>{en}<w:r><w:t>.</w:t></w:r>')
            + p("", runs='<w:commentRangeStart w:id="0"/><w:r><w:t xml:space="preserve">Ce chiffre reste à confirmer par le service qualité</w:t></w:r><w:commentRangeEnd w:id="0"/>'
                         '<w:r><w:commentReference w:id="0"/></w:r><w:r><w:t>.</w:t></w:r>')
            + p("", runs='<w:r><w:t xml:space="preserve">Le contrat prévoit </w:t></w:r><w:del w:id="5" w:author="Marc" w:date="2025-03-01T10:00:00Z"><w:r><w:delText>trente jours</w:delText></w:r></w:del>'
                         '<w:ins w:id="6" w:author="Marc" w:date="2025-03-01T10:00:00Z"><w:r><w:t>quarante-cinq jours</w:t></w:r></w:ins><w:r><w:t xml:space="preserve"> de préavis.</w:t></w:r>'))
    fns = (f'<?xml version="1.0" encoding="UTF-8"?><w:footnotes {W_NS}><w:footnote w:type="separator" w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
           '<w:footnote w:type="continuationSeparator" w:id="1"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
           '<w:footnote w:id="2"><w:p><w:r><w:footnoteRef/></w:r><w:r><w:t xml:space="preserve"> Source : rapport interne qualité 2024-2025, page 17.</w:t></w:r></w:p></w:footnote></w:footnotes>')
    ens = (f'<?xml version="1.0" encoding="UTF-8"?><w:endnotes {W_NS}><w:endnote w:type="separator" w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>'
           '<w:endnote w:type="continuationSeparator" w:id="1"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:endnote>'
           '<w:endnote w:id="2"><w:p><w:r><w:endnoteRef/></w:r><w:r><w:t xml:space="preserve"> Procédé breveté, licence valable jusqu\'en 2031.</w:t></w:r></w:p></w:endnote></w:endnotes>')
    com = (f'<?xml version="1.0" encoding="UTF-8"?><w:comments {W_NS}><w:comment w:id="0" w:author="Léa Marchand" w:date="2025-03-02T09:00:00Z" w:initials="LM">'
           '<w:p><w:r><w:t>Vérifier avec la base de données qualité avant diffusion</w:t></w:r></w:p></w:comment></w:comments>')
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ct = "application/vnd.openxmlformats-officedocument.wordprocessingml."
    make_docx(d / "notes-commentaires-revisions.docx", body,
              parts={"word/footnotes.xml": fns, "word/endnotes.xml": ens, "word/comments.xml": com},
              rels=f'<Relationship Id="rIdF" Type="{R}/footnotes" Target="footnotes.xml"/><Relationship Id="rIdE" Type="{R}/endnotes" Target="endnotes.xml"/>'
                   f'<Relationship Id="rIdC" Type="{R}/comments" Target="comments.xml"/>',
              ctypes=f'<Override PartName="/word/footnotes.xml" ContentType="{ct}footnotes+xml"/><Override PartName="/word/endnotes.xml" ContentType="{ct}endnotes+xml"/>'
                     f'<Override PartName="/word/comments.xml" ContentType="{ct}comments+xml"/>')
    cases.append(Case("docx-notes-commentaires-revisions", d / "notes-commentaires-revisions.docx", "docx", 3, "notes de bas de page et de fin, commentaire, texte supprimé/inséré en suivi des modifications",
                      must=["Source : rapport interne qualité 2024-2025, page 17", "Procédé breveté, licence valable jusqu'en 2031", "Vérifier avec la base de données qualité avant diffusion",
                            "quarante-cinq jours", "Ce chiffre reste à confirmer par le service qualité"],
                      absent=["trente jours"], headings=["Étude de cas"],
                      notes="Le texte supprimé (suivi des modifications) ne doit pas figurer dans le texte final ; les notes et le commentaire doivent être conservés."))

    # 4. zone de texte (doublon Choice/Fallback), en-tête, pied de page
    tb = ('<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="1" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
          '<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>'
          '<wp:extent cx="3000000" cy="800000"/><wp:wrapSquare wrapText="bothSides"/><wp:docPr id="1" name="Zone de texte 1"/><a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
          '<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="3000000" cy="800000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></wps:spPr>'
          '<wps:txbx><w:txbxContent><w:p><w:r><w:t>Encadré : à retenir absolument</w:t></w:r></w:p><w:p><w:r><w:t>La date limite est le 30 juin.</w:t></w:r></w:p></w:txbxContent></wps:txbx><wps:bodyPr/></wps:wsp>'
          '</a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice><mc:Fallback><w:pict><v:shape id="_x0000_s1026" type="#_x0000_t202" style="width:236pt;height:63pt"><v:textbox><w:txbxContent>'
          '<w:p><w:r><w:t>Encadré : à retenir absolument</w:t></w:r></w:p><w:p><w:r><w:t>La date limite est le 30 juin.</w:t></w:r></w:p></w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>')
    body = p("Note de service", "Heading1") + p("Les inscriptions pour la session d'automne sont ouvertes à tous les agents.") + tb + p("Merci de transmettre vos demandes à la direction des ressources humaines.")
    hdr = f'<?xml version="1.0" encoding="UTF-8"?><w:hdr {W_NS}><w:p><w:r><w:t>CONFIDENTIEL — Projet Orion</w:t></w:r></w:p></w:hdr>'
    ftr = (f'<?xml version="1.0" encoding="UTF-8"?><w:ftr {W_NS}><w:p><w:r><w:t xml:space="preserve">Page </w:t></w:r><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
           '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
    sect = '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdFt"/></w:sectPr>'
    make_docx(d / "zone-texte-entete.docx", body, parts={"word/header1.xml": hdr, "word/footer1.xml": ftr}, sect=sect,
              rels=f'<Relationship Id="rIdH" Type="{R}/header" Target="header1.xml"/><Relationship Id="rIdFt" Type="{R}/footer" Target="footer1.xml"/>',
              ctypes=f'<Override PartName="/word/header1.xml" ContentType="{ct}header+xml"/><Override PartName="/word/footer1.xml" ContentType="{ct}footer+xml"/>')
    cases.append(Case("docx-zone-texte-entete", d / "zone-texte-entete.docx", "docx", 4, "zone de texte stockée en double (Choice + Fallback), en-tête et pied de page",
                      must=["Note de service", "La date limite est le 30 juin", "Merci de transmettre vos demandes à la direction des ressources humaines"],
                      once=["Encadré : à retenir absolument"], headings=["Note de service"],
                      notes="Le contenu de la zone de texte doit apparaître une seule fois ; l'en-tête/pied de page est du bruit par défaut."))

    # 5. RTL, CJK, emoji, symboles
    bidi = lambda t: p("", extra_ppr="<w:bidi/>", runs=f'<w:r><w:rPr><w:rtl/></w:rPr><w:t xml:space="preserve">{x(t)}</w:t></w:r>')  # noqa: E731
    lines = ["مرحبا بالعالم هذا اختبار للغة العربية", "שלום עולם זהו מבחן בעברית", "这是一个包含中文的测试文档", "これは日本語のテスト文書です", "이것은 한국어 시험 문서입니다",
             "Résultat ✅ validé 🚀 coût 12 € — « citation » œuvre", "Formule : α + β ≤ γ ≈ ∑ x² → ∞"]
    body = p("Document multilingue", "Heading1") + bidi(lines[0]) + bidi(lines[1]) + "".join(p(t) for t in lines[2:])
    make_docx(d / "multilingue-rtl-cjk.docx", body)
    cases.append(Case("docx-multilingue-rtl-cjk", d / "multilingue-rtl-cjk.docx", "docx", 3, "arabe et hébreu (droite à gauche), chinois, japonais, coréen, emoji, symboles",
                      must=lines, headings=["Document multilingue"]))

    # 6. sommaire (champ TOC), signets, lien interne, contrôle de contenu, équation
    toc = ('<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
           '<w:r><w:t>1. Contexte ........ 2</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:t>2. Méthode ........ 3</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    sdt = ('<w:sdt><w:sdtPr><w:alias w:val="Valeur"/><w:tag w:val="valeur"/></w:sdtPr><w:sdtContent><w:p><w:r><w:t>Valeur saisie : 42 unités</w:t></w:r></w:p></w:sdtContent></w:sdt>')
    eq = ('<w:p><m:oMathPara><m:oMath><m:r><m:t>x=</m:t></m:r><m:f><m:num><m:r><m:t>-b±√(b²-4ac)</m:t></m:r></m:num><m:den><m:r><m:t>2a</m:t></m:r></m:den></m:f></m:oMath></m:oMathPara></w:p>')
    link = '<w:p><w:hyperlink w:anchor="methode"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>Voir la section Méthode</w:t></w:r></w:hyperlink></w:p>'
    body = (p("Rapport technique", "Title") + p("Table des matières", "Heading1") + toc + p("Contexte", "Heading1")
            + p("Le contexte décrit les enjeux de la mesure.") + link + sdt + p("Méthode", "Heading1", runs='<w:bookmarkStart w:id="9" w:name="methode"/><w:r><w:t>Méthode</w:t></w:r><w:bookmarkEnd w:id="9"/>')
            + p("La solution de l'équation quadratique est donnée par :") + eq)
    make_docx(d / "sommaire-equation-controle.docx", body)
    cases.append(Case("docx-sommaire-equation-controle", d / "sommaire-equation-controle.docx", "docx", 4, "champ de sommaire, lien interne, contrôle de contenu (SDT), équation OMML",
                      must=["Valeur saisie : 42 unités", "Voir la section Méthode", "La solution de l'équation quadratique", "2a"],
                      any_of=[["4ac", "4 a c"]], headings=["Rapport technique", "Contexte", "Méthode"], once=["Valeur saisie : 42 unités"],
                      notes="L'équation doit rester lisible (LaTeX ou texte) ; les contrôles de contenu ne doivent pas être ignorés."))
    return cases
