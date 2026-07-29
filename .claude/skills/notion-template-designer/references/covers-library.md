# Covers Library — URLs Unsplash prêtes à l'emploi

Notion accepte les URLs Unsplash directes en tant que covers. Ces URLs sont **testées et stables** (photos non supprimées au moment de la rédaction du skill).

Format de l'URL : `https://images.unsplash.com/photo-[ID]?q=80&w=1920&auto=format&fit=crop`

Si une URL ne marche plus, fallback : rechercher sur Unsplash avec les mots-clés associés et prendre une image similaire.

---

## Cover via recherche Unsplash (recommandé)

Notion a une intégration Unsplash native : dans l'UI, l'utilisateur peut chercher directement. Mais via l'API MCP, il faut une URL directe.

**Méthode fiable pour obtenir une URL Unsplash à la volée** :
1. Aller sur `unsplash.com/s/photos/[mot-clé]`
2. Cliquer sur une photo → bouton "Download free" → clic droit sur l'image ouverte → copier l'URL
3. Prendre la version optimisée : remplacer les paramètres par `?q=80&w=1920&auto=format&fit=crop`

---

## Catalogue par mood

### Minimaliste / Abstrait

Noir & blanc, textures, formes pures :
- `photo-1557683316-973673baf926` — bleu abstrait dégradé
- `photo-1618005182384-a83a8bd57fbe` — vagues monochromes
- `photo-1557682250-33bd709cbe85` — flou bleu/violet
- `photo-1614850523011-8f49ffc73908` — texture papier blanche

### Pastel aesthetic

Tons doux, fleurs, céramique, lumière douce :
- `photo-1579546929518-9e396f3cc809` — pastel gradient rose/bleu
- `photo-1557683304-673a23048d34` — rose flou
- `photo-1617957689233-207e3cd3c610` — fleurs pastel
- `photo-1522441815192-d9f04eb0615c` — coucher de soleil doux

### Dark / Moody / Néon

Nuit urbaine, cyberpunk, noir profond :
- `photo-1478760329108-5c3ed9d495a0` — néon violet ville
- `photo-1451187580459-43490279c0fa` — galaxie
- `photo-1506318137071-a8e063b4bec0` — forêt sombre
- `photo-1550745165-9bc0b252726f` — ordi néon

### Corporate / Architecture

Bureaux, bâtiments, paysages urbains épurés :
- `photo-1497366216548-37526070297c` — bureau moderne
- `photo-1486406146926-c627a92ad1ab` — architecture lignes
- `photo-1431576901776-e539bd916ba2` — building abstrait
- `photo-1542626991-cbc4e32524cc` — bibliothèque

### Vibrant / Créatif

Peintures abstraites, mixed media, couleurs vives :
- `photo-1536924430914-91f9e2041b83` — peinture jaune/rose
- `photo-1541701494587-cb58502866ab` — pigments colorés
- `photo-1549490349-8643362247b5` — graffiti
- `photo-1513364776144-60967b0f800f` — art mural

### Earthy / Naturel

Nature, forêt, café, textures organiques :
- `photo-1441974231531-c6227db76b6e` — forêt brume
- `photo-1499678329028-101435549a4e` — café nature
- `photo-1506126613408-eca07ce68773` — méditation
- `photo-1502082553048-f009c37129b9` — forêt doré

---

## Covers par type de page

### Productivité / Dashboard
Unsplash queries : `desk setup`, `minimal workspace`, `morning coffee`
- `photo-1484480974693-6ca0a78fb36b` — desk minimaliste
- `photo-1499750310107-5fef28a66643` — mac sur bureau

### Journal / Daily notes
Unsplash queries : `journal notebook`, `morning light`, `quiet moment`
- `photo-1517842645767-c639042777db` — carnet ouvert
- `photo-1455390582262-044cdead277a` — bullet journal

### Habits / Wellness
Unsplash queries : `morning ritual`, `yoga`, `running`, `water`
- `photo-1545205597-3d9d02c29597` — course route
- `photo-1593811167562-9cef47bfc4a7` — yoga minimal

### Projet / Produit
Unsplash queries : `whiteboard sketch`, `sticky notes`, `design process`
- `photo-1531403009284-440f080d1e12` — sticky notes
- `photo-1519389950473-47ba0277781c` — design sketch

### Portfolio
Unsplash queries : `creative desk`, `portfolio minimal`, `studio`
- `photo-1558655146-d09347e92766` — studio créatif
- `photo-1626785774573-4b799315345d` — desk designer

### Knowledge / Library
Unsplash queries : `library`, `books`, `reading nook`
- `photo-1507842217343-583bb7270b66` — bibliothèque
- `photo-1524995997946-a1c2e315a42f` — livres empilés

### Dev / Tech
Unsplash queries : `code screen`, `terminal`, `mechanical keyboard`
- `photo-1461749280684-dccba630e2f6` — code sombre
- `photo-1555066931-4365d14bab8c` — terminal

---

## Protocole de sélection

1. Identifier la direction visuelle retenue (phase 2)
2. Identifier le type de page (productivité / journal / projet / portfolio / knowledge / dev)
3. Croiser → piocher dans la section correspondante
4. Coller l'URL complète dans le paramètre `cover` du MCP Notion

**Exemple de cover dans un appel MCP** :
```
cover_url: "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?q=80&w=1920&auto=format&fit=crop"
```

---

## Fallback : générer un cover custom

Si aucune image Unsplash ne convient, options de fallback :

1. **Gradient simple** : Notion a des covers "gradient" natifs (accessibles via "Change cover" → "Gradients")
2. **Cover généré via Canva/Figma** : l'utilisateur peut créer un cover 1500×600px et l'uploader
3. **Ressources gratuites** :
   - **coverdesign.notion.so** — générateur de covers Notion
   - **notion-covers.com** — covers géométriques colorés
   - **wallpapershome.com** + crop en 1500×600
