# Batterie « cas extrêmes » — résultats

86 réussis / 0 échecs sur 86 cas (plus long : 6.0 s ; pic mémoire : 227 Mo).

| Verdict | Cas | Temps | Mémoire | Statut | Remarques |
|---|---|---|---|---|---|
| PASS | A1 xlsx 25 000 lignes | 2.4 s | 79 Mo | ok | contenu borné ET signalé (1 repère(s) absent(s)) |
| PASS | A2 docx 4 000 paragraphes + tableau | 0.7 s | 39 Mo | ok |  |
| PASS | A3 pdf 400 pages | 4.2 s | 49 Mo | ok |  |
| PASS | A4 csv 200 000 lignes | 0.5 s | 33 Mo | ok | contenu borné ET signalé (1 repère(s) absent(s)) |
| PASS | A5 pptx 200 diapositives | 0.3 s | 26 Mo | ok |  |
| PASS | A6 texte 8 Mo sans retour à la ligne | 2.4 s | 186 Mo | ok |  |
| PASS | A7 json 25 Mo | 0.8 s | 150 Mo | ok |  |
| PASS | A8 epub 600 chapitres | 0.4 s | 30 Mo | ok |  |
| PASS | A9 mbox 4 000 messages | 0.4 s | 28 Mo | ok | contenu borné ET signalé (1 repère(s) absent(s)) |
| PASS | A10 svg 700 nœuds | 0.9 s | 29 Mo | ok |  |
| PASS | A11 xlsx cellule de 1,5 Mo | 0.5 s | 43 Mo | ok |  |
| PASS | A12 xlsx 300 colonnes | 0.2 s | 26 Mo | ok |  |
| PASS | B1 bombe zip (docx 2 Go décompressé) | 1.1 s | 147 Mo | error |  |
| PASS | B2 docx « milliard de rires » (entités) | 1.2 s | 147 Mo | unsupported |  |
| PASS | B3 docx XXE (lecture d'un fichier local) | 1.1 s | 147 Mo | unsupported |  |
| PASS | B4 svg XXE (fichier + réseau) | 0.2 s | 26 Mo | error |  |
| PASS | B5 zip avec ../ et chemin absolu | 0.2 s | 26 Mo | ok |  |
| PASS | B6 zip dans zip dans zip… (14 niveaux) | 0.2 s | 21 Mo | unsupported |  |
| PASS | B7 html imbriqué sur 3 000 niveaux | 0.3 s | 26 Mo | ok |  |
| PASS | B8 xml imbriqué sur 6 000 niveaux | 1.1 s | 149 Mo | ok |  |
| PASS | B9 rtf à 5 000 groupes imbriqués | 0.2 s | 26 Mo | ok |  |
| PASS | B10 json imbriqué sur 5 000 niveaux | 0.9 s | 147 Mo | ok |  |
| PASS | B11 png 1,6 milliard de pixels | 0.2 s | 26 Mo | warn |  |
| PASS | B12 consignes cachées dans un document | 0.2 s | 26 Mo | ok |  |
| PASS | B13 html avec script, iframe, javascript: | 0.2 s | 26 Mo | ok |  |
| PASS | B14 pdf chiffré (mot de passe inconnu) | 0.2 s | 25 Mo | unsupported |  |
| PASS | C 0 octet .docx | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .xlsx | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .pptx | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .pdf | 0.2 s | 25 Mo | unsupported |  |
| PASS | C 0 octet .epub | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .doc | 0.2 s | 25 Mo | unsupported |  |
| PASS | C 0 octet .xls | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .ppt | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .odt | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .rtf | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .html | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .svg | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .json | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .csv | 0.2 s | 25 Mo | unsupported |  |
| PASS | C 0 octet .png | 0.2 s | 25 Mo | unsupported |  |
| PASS | C 0 octet .eml | 0.2 s | 26 Mo | unsupported |  |
| PASS | C 0 octet .zip | 0.2 s | 25 Mo | unsupported |  |
| PASS | C docx tronqué à 50 % | 0.2 s | 26 Mo | unsupported |  |
| PASS | C docx = octets aléatoires | 0.2 s | 26 Mo | unsupported |  |
| PASS | C xlsx tronqué à 50 % | 1.1 s | 147 Mo | error |  |
| PASS | C xlsx = octets aléatoires | 0.2 s | 26 Mo | unsupported |  |
| PASS | C pptx tronqué à 50 % | 1.0 s | 147 Mo | error |  |
| PASS | C pptx = octets aléatoires | 0.2 s | 26 Mo | unsupported |  |
| PASS | C pdf tronqué à 50 % | 1.1 s | 147 Mo | unsupported |  |
| PASS | C pdf = octets aléatoires | 0.2 s | 26 Mo | unsupported |  |
| PASS | C pdf déguisé en .docx | 1.0 s | 147 Mo | ok |  |
| PASS | C docx déguisé en .txt | 0.2 s | 26 Mo | ok |  |
| PASS | C xlsx déguisé en .pdf | 0.2 s | 26 Mo | ok |  |
| PASS | C pptx sans extension | 0.2 s | 26 Mo | ok |  |
| PASS | C texte déguisé en .png | 0.2 s | 26 Mo | ok |  |
| PASS | C texte avec octets NUL | 0.2 s | 26 Mo | ok |  |
| PASS | C pdf à table xref détruite | 1.1 s | 147 Mo | ok |  |
| PASS | C docx avec XML mal formé | 1.0 s | 147 Mo | warn |  |
| PASS | C docx aux octets d'en-tête abîmés | 0.2 s | 26 Mo | ok |  |
| PASS | D1 docx multilingue (RTL, CJK, emoji, combinants) | 0.2 s | 26 Mo | ok |  |
| PASS | D2 texte UTF-8 avec BOM, CRLF, CR, NEL | 0.2 s | 26 Mo | ok |  |
| PASS | D3 texte UTF-16 sans BOM | 0.2 s | 26 Mo | ok |  |
| PASS | D4 html annoncé utf-8 mais en latin-1 | 0.2 s | 26 Mo | ok |  |
| PASS | D5 json avec surrogate isolé et \u0000 | 0.2 s | 26 Mo | ok |  |
| PASS | D6 csv français (; , cp1252, retour dans une cellule) | 0.2 s | 26 Mo | ok |  |
| PASS | D7 texte à écritures mélangées (bidi) | 0.2 s | 26 Mo | ok |  |
| PASS | E1 noms de fichiers piégeux (dossier) | 0.3 s | 22 Mo | ok |  |
| PASS | E2 mêmes noms dans deux dossiers + a.docx/a.pdf | 1.2 s | 147 Mo | ok |  |
| PASS | F1 tableau Word aux caractères spéciaux | 0.2 s | 26 Mo | ok |  |
| PASS | F2 xlsx aux caractères spéciaux | 0.2 s | 26 Mo | ok |  |
| PASS | F3 json contenant des clôtures ```  | 0.2 s | 26 Mo | ok |  |
| PASS | F4 liste à 12 niveaux | 0.2 s | 26 Mo | ok |  |
| PASS | F5 tableaux imbriqués sur 5 niveaux | 0.2 s | 26 Mo | ok |  |
| PASS | F6 fichier déjà en Markdown (pas d'altération) | 0.2 s | 26 Mo | ok |  |
| PASS | F7 html à colspan/rowspan | 0.2 s | 26 Mo | ok |  |
| PASS | F8 gras/italique collés sans espace | 0.2 s | 26 Mo | ok |  |
| PASS | G1 .xls 2 000 lignes | 5.5 s | 216 Mo | ok | contenu borné ET signalé (1 repère(s) absent(s)) |
| PASS | G2 .ppt 80 diapositives | 5.2 s | 227 Mo | ok |  |
| PASS | G3 .doc 1 500 lignes + tableau | 6.0 s | 216 Mo | ok |  |
| PASS | H1 png 1x1 | 0.3 s | 26 Mo | warn |  |
| PASS | H2 png avec texte | 0.2 s | 26 Mo | warn |  |
| PASS | H3 gif animé | 0.2 s | 26 Mo | warn |  |
| PASS | H4 jpeg CMYK | 0.2 s | 26 Mo | warn |  |
| PASS | H5 png tronqué | 0.3 s | 26 Mo | warn |  |
| PASS | H6 docx contenant une image de 1,6 Gpixel | 0.2 s | 26 Mo | ok |  |
