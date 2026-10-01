"""Données, encodages, archives, fichiers abîmés et formats ouverts (ODT, RTF) difficiles."""
from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from typing import List

from gen_common import OUT, WITH_BIG, Case, lo_convert


def build() -> List[Case]:
    d = OUT / "data"
    d.mkdir(parents=True, exist_ok=True)
    cases: List[Case] = []

    # 1. JSON profond, hétérogène
    doc = {"commande": {"id": "CMD-2025-0042", "client": {"nom": "Société Lumière", "adresse": {"rue": "12 rue des Écoles", "ville": "Nantes", "contact": {"tel": "+33 2 40 00 11 22", "horaires": {"semaine": {"matin": ["8h30", "12h"], "après-midi": ["14h", "18h"]}}}}},
                         "lignes": [{"ref": "A-100", "libellé": "Câble réseau 5 m", "qté": 40, "options": {"couleur": "bleu", "blindé": True}}, {"ref": "B-220", "libellé": "Switch 24 ports", "qté": 2, "options": None}],
                         "notes": "Livraison avant le 12 juin — fragile", "total": {"ht": 1840.5, "tva": 368.1, "ttc": 2208.6}}}
    (d / "json-profond.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cases.append(Case("data-json-profond", d / "json-profond.json", "data", 3, "JSON imbriqué sur 8 niveaux, tableaux d'objets hétérogènes, null, booléens, accents",
                      must=["CMD-2025-0042", "Société Lumière", "12 rue des Écoles", "Nantes", "+33 2 40 00 11 22", "8h30", "14h", "Câble réseau 5 m", "Switch 24 ports", "bleu", "Livraison avant le 12 juin — fragile", "2208.6"],
                      notes="Lisible par un humain : hiérarchie conservée (titres/listes/tableaux), pas un bloc JSON brut illisible."))

    # 2. XML avec espaces de noms, CDATA, contenu mixte
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<cat:catalogue xmlns:cat="http://exemple.fr/catalogue" xmlns:meta="http://exemple.fr/meta">
<meta:info meta:version="2.1"><meta:auteur>Bureau d'études</meta:auteur></meta:info>
<cat:produit ref="X1"><cat:nom>Vanne papillon DN80</cat:nom><cat:description><![CDATA[Vanne <robuste> & étanche, pression max 16 bar.]]></cat:description>
<cat:note>Voir la <cat:lien href="http://exemple.fr/fiche">fiche technique</cat:lien> avant <cat:em>toute</cat:em> commande.</cat:note></cat:produit>
<cat:produit ref="X2"><cat:nom>Clapet anti-retour</cat:nom><cat:description>Montage horizontal ou vertical.</cat:description></cat:produit></cat:catalogue>"""
    (d / "xml-espaces-de-noms.xml").write_text(xml, encoding="utf-8")
    cases.append(Case("data-xml-namespaces", d / "xml-espaces-de-noms.xml", "data", 3, "XML à espaces de noms, CDATA avec chevrons et esperluette, contenu mixte (texte + éléments en ligne)",
                      must=["Bureau d'études", "Vanne papillon DN80", "pression max 16 bar", "Clapet anti-retour", "Montage horizontal ou vertical", "fiche technique", "avant toute commande"],
                      any_of=[["Vanne <robuste> & étanche", "Vanne &lt;robuste&gt; &amp; étanche", "Vanne robuste & étanche"]],
                      notes="Le contenu mixte doit rester une phrase continue ; le CDATA doit être restitué littéralement."))

    # 3. SQLite relationnelle
    db = d / "base-relationnelle.sqlite"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript("""CREATE TABLE clients(id INTEGER PRIMARY KEY, nom TEXT NOT NULL, ville TEXT);
CREATE TABLE commandes(id INTEGER PRIMARY KEY, client_id INTEGER REFERENCES clients(id), montant REAL, commentaire TEXT, pdf BLOB);
CREATE VIEW gros_clients AS SELECT c.nom, SUM(o.montant) AS total FROM clients c JOIN commandes o ON o.client_id=c.id GROUP BY c.nom;
INSERT INTO clients VALUES (1,'Boulangerie Léon','Rennes'),(2,'Garage Müller','Strasbourg'),(3,'Café « Le Zèbre »','Lille');
INSERT INTO commandes VALUES (1,1,120.5,'Livraison urgente',x'255044462d'),(2,2,980,NULL,NULL),(3,1,45.25,'Remise fidélité',NULL);""")
    con.commit()
    con.close()
    cases.append(Case("data-sqlite-relationnelle", db, "data", 3, "deux tables liées par clé étrangère, une vue, un BLOB, NULL, accents",
                      must=["clients", "commandes", "Boulangerie Léon", "Garage Müller", "Café « Le Zèbre »", "Strasbourg", "Livraison urgente", "Remise fidélité", "980"],
                      notes="Le schéma (colonnes, clé étrangère) et un aperçu des lignes doivent apparaître ; le BLOB ne doit pas polluer la sortie."))

    # 4. encodages hérités, un fichier par encodage
    enc = [("texte-cp1252.txt", "cp1252", "Café à 5 € — « guillemets » et œuvre"), ("texte-shiftjis.txt", "shift_jis", "これは日本語のテストです。東京は日本の首都です。"),
           ("texte-utf16.txt", "utf-16", "Résumé du projet : coût 1 250 € — échéance fixée"), ("texte-latin2.txt", "iso8859_2", "Zażółć gęślą jaźń, pójdę do łóżka"),
           ("texte-koi8r.txt", "koi8_r", "Привет мир это проверка кодировки")]
    for name, codec, text in enc:
        (d / name).write_bytes(text.encode(codec))
        cases.append(Case(f"data-{name.rsplit('.', 1)[0]}", d / name, "data", 2, f"texte non UTF-8 sans déclaration d'encodage ({codec})", must=[text],
                          notes="L'encodage doit être deviné correctement (aucun caractère de remplacement)."))

    # 5. archive imbriquée avec noms Unicode et un membre corrompu
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("notes internes.txt", "Contenu imbriqué : le code d'accès est 4821.")
        z.writestr("résumé été.md", "# Résumé de l'été\n\nTrois chantiers livrés dans les délais.\n")
    path = d / "archive-imbriquee.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("dossier/lisez-moi.txt", "Archive de test.")
        z.writestr("dossier/interne.zip", inner.getvalue())
        z.writestr("dossier/cassé.docx", b"PK\x03\x04 ceci n'est pas un vrai docx")
        z.writestr("日本語/メモ.txt", "メモの内容：確認済み")
    cases.append(Case("data-archive-imbriquee", path, "data", 4, "zip dans un zip, noms de fichiers Unicode, un membre corrompu",
                      must=["Archive de test", "le code d'accès est 4821", "Trois chantiers livrés dans les délais", "メモの内容：確認済み"],
                      notes="Les fichiers lisibles doivent être convertis ; le membre corrompu doit être signalé, sans faire échouer le reste."))

    # 6. fichiers abîmés : échec propre attendu
    docx = OUT / "docx" / "tableaux-fusionnes.docx"
    if docx.exists():
        raw = docx.read_bytes()
        (d / "docx-tronque.docx").write_bytes(raw[: int(len(raw) * 0.6)])
        cases.append(Case("data-docx-tronque", d / "docx-tronque.docx", "data", 4, "DOCX tronqué à 60 % (téléchargement interrompu)", expect="error",
                          notes="Doit répondre par un message clair (fichier abîmé), jamais une sortie vide ou un plantage."))
    pdf = OUT / "pdf" / "article-deux-colonnes.pdf"
    if pdf.exists():
        raw = pdf.read_bytes()
        (d / "pdf-tronque.pdf").write_bytes(raw[: int(len(raw) * 0.5)])
        cases.append(Case("data-pdf-tronque", d / "pdf-tronque.pdf", "data", 4, "PDF tronqué à 50 % (sans table de références ni fin de fichier)", expect="ok",
                          must=["Mesure de la dérive thermique en milieu industriel"], notes="Récupération partielle bienvenue (le début du texte), sinon échec propre."))
    (d / "faux-docx.docx").write_bytes(b"Ceci est simplement un fichier texte renomme en .docx.\nIl contient deux lignes.")
    cases.append(Case("data-faux-docx", d / "faux-docx.docx", "data", 2, "fichier texte renommé en .docx", must=["Ceci est simplement un fichier texte renomme", "Il contient deux lignes"],
                      notes="Le format doit être détecté par le contenu, pas par l'extension."))

    # 7. RTF et ODT via LibreOffice, à partir de contenus riches
    html = d / "_src.html"
    html.write_text("""<html><head><meta charset="utf-8"></head><body><h1>Cahier des charges</h1><p>Le prestataire s'engage à livrer <b>avant le 30 septembre</b> les éléments suivants :</p>
<ol><li>Étude préalable<ul><li>Audit de l'existant</li><li>Analyse des risques</li></ul></li><li>Réalisation</li><li>Recette</li></ol>
<table border="1"><tr><th>Lot</th><th>Délai</th><th>Pénalité</th></tr><tr><td>Étude</td><td>4 semaines</td><td>0,5 % / jour</td></tr><tr><td>Réalisation</td><td>12 semaines</td><td>1 % / jour</td></tr></table>
<p>Caractères spéciaux : œuvre, naïveté, 5 € · ½ · « guillemets » — tiret long.</p></body></html>""", encoding="utf-8")
    must = ["Cahier des charges", "avant le 30 septembre", "Audit de l'existant", "Analyse des risques", "Recette", "4 semaines", "0,5 % / jour", "12 semaines", "œuvre, naïveté, 5 €"]
    rows = [["Étude", "4 semaines", "0,5 % / jour"], ["Réalisation", "12 semaines", "1 % / jour"]]
    for ext, filt in (("rtf", "rtf:Rich Text Format"), ("odt", "odt:writer8")):
        dest = d / f"cahier-des-charges.{ext}"
        if lo_convert(html, filt, dest, infilter="HTML (StarWriter)"):
            cases.append(Case(f"data-{ext}-liste-tableau", dest, "data", 3, f"{ext.upper()} produit par LibreOffice : liste imbriquée, tableau, caractères spéciaux",
                              must=must, rows=rows, items=["Audit de l'existant", "Analyse des risques", "Étude préalable"], headings=["Cahier des charges"]))
    html.unlink(missing_ok=True)

    if WITH_BIG:
        big = OUT / "big"
        big.mkdir(parents=True, exist_ok=True)
        with open(big / "csv-200000-lignes.csv", "w", encoding="utf-8") as f:
            f.write("id,nom,montant\n")
            for i in range(1, 200001):
                f.write(f"{i},client-{i:06d},{i * 1.5}\n")
        cases.append(Case("big-csv-200000-lignes", big / "csv-200000-lignes.csv", "big", 3, "200 000 lignes : charge et troncature signalée",
                          must=["client-000001"], any_of=[["client-200000", "lignes omises", "tronqué", "limite", "troncature"]]))
    return cases
