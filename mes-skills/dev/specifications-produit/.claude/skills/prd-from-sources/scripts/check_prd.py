#!/usr/bin/env python3
"""check_prd.py — contrôle mécanique d'un PRD rédigé avec prd-from-sources (gabarit BMAD).

    python3 scripts/check_prd.py prd.md [--sources DOSSIER] [--strict] [--json]

Vérifie, sans réseau et avec la seule bibliothèque standard :
  - chaque FR / NFR cite au moins un fichier source (« source : fichier.md, § titre ») ou porte un [ASSUMPTION…] ;
  - chaque fichier cité existe (dans --sources, par défaut le dossier du PRD ; recherche récursive par nom) ;
  - aucun FR orphelin : tout FR est défini sous une fonctionnalité de la section Features / Fonctionnalités ;
  - toute fonctionnalité contient au moins un FR ; si des epics existent, chacun renvoie à des FR et tout FR est couvert ;
  - toute référence (FR-n, NFR-n, UJ-n, SM-n, SM-Cn) renvoie à un identifiant défini ; identifiants uniques et continus ;
  - parcours (UJ) réalisés par au moins un FR, FR rattachés à un parcours, indicateurs (SM) rattachés à des FR ;
  - hypothèses en ligne = index des hypothèses ; Glossaire et Questions ouvertes présents ; aucun {placeholder} du gabarit.

Code de sortie : 0 = aucun défaut bloquant, 1 = au moins une erreur (avec --strict : ou un avertissement), 2 = usage.
Définition d'un identifiant : un titre `#### FR-3 : …` ou une ligne en gras `- **FR-3** : …` (les mentions ailleurs sont des références).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

PREFIXES = ("NFR", "FR", "UJ", "SM-C", "SM")
ID_RE = re.compile(r"\b(NFR|FR|UJ|SM-C|SM)-?(\d+)\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
DEF_HEADING_RE = re.compile(r"^(#{1,6})\s*\**\s*(NFR|FR|UJ|SM-C|SM)-?(\d+)\b")
DEF_BOLD_RE = re.compile(r"^(\s*)(?:[-*+]\s+|\d+[.)]\s+)?\*\*\s*(NFR|FR|UJ|SM-C|SM)-?(\d+)\b")
SOURCE_RE = re.compile(r"(?i)\b(?:sources?)\s*:\s*(.+)")
FILE_TOKEN_RE = re.compile(r"[\w\-./\\]+\.[A-Za-z][A-Za-z0-9]{0,4}\b")
ASSUMPTION_TAGS = ("[ASSUMPTION", "[HYPOTHÈSE", "[HYPOTHESE", "[déduit", "[deduit", "[À CONFIRMER", "[A CONFIRMER")
PLACEHOLDER_RE = re.compile(r"\{[A-Za-z][^{}\n]*\}")
FEATURES_RE = re.compile(r"(?i)^(?:\d+(?:\.\d+)*[.)]?\s*)?(features?|fonctionnalit[ée]s?|fonctions)\b")
GLOSSARY_RE = re.compile(r"(?i)\b(glossary|glossaire)\b")
OPENQ_RE = re.compile(r"(?i)\b(open questions|questions ouvertes)\b")
ASSUME_IDX_RE = re.compile(r"(?i)\b(assumptions? index|index des hypoth[èe]ses|assumptions|hypoth[èe]ses)\b")
EPIC_RE = re.compile(r"(?i)^(?:\d+(?:\.\d+)*[.)]?\s*)?[ée]pics?\b")


class Finding:
    def __init__(self, level: str, line: int, code: str, message: str):
        self.level, self.line, self.code, self.message = level, line, code, message

    def as_dict(self) -> Dict[str, object]:
        return {"niveau": self.level, "ligne": self.line, "code": self.code, "message": self.message}


def _strip_front_matter_and_fences(text: str) -> List[str]:
    """Lignes du PRD, avec front matter et blocs ``` neutralisés (numérotation des lignes conservée)."""
    lines = text.splitlines()
    out: List[str] = []
    in_fence = False
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                out.extend([""] * (i + 1))
                start = i + 1
                break
    for ln in lines[start:]:
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else ln)
    return out


def _key(prefix: str, num: str) -> str:
    return f"{prefix}-{int(num)}"


class Item:
    def __init__(self, key: str, line: int, end: int):
        self.key, self.line, self.end = key, line, end
        self.feature: Optional[str] = None


def parse(lines: List[str]):
    headings: List[Tuple[int, int, str]] = []          # (ligne, niveau, texte)
    defs: List[Item] = []
    for i, ln in enumerate(lines):
        m = HEADING_RE.match(ln)
        if m:
            headings.append((i, len(m.group(1)), m.group(2)))
        mh = DEF_HEADING_RE.match(ln)
        mb = DEF_BOLD_RE.match(ln) if not mh else None
        if mh:
            defs.append(Item(_key(mh.group(2), mh.group(3)), i, -1))
            defs[-1].level = len(mh.group(1))      # type: ignore[attr-defined]
            defs[-1].indent = -1                   # type: ignore[attr-defined]
        elif mb:
            defs.append(Item(_key(mb.group(2), mb.group(3)), i, -1))
            defs[-1].level = 0                     # type: ignore[attr-defined]
            defs[-1].indent = len(mb.group(1))     # type: ignore[attr-defined]
    heading_lines = [h[0] for h in headings]
    def_lines = {d.line for d in defs}
    for d in defs:
        end = len(lines)
        for j in range(d.line + 1, len(lines)):
            if j in def_lines:
                end = j
                break
            hm = HEADING_RE.match(lines[j])
            if hm and (d.level == 0 or len(hm.group(1)) <= d.level):      # type: ignore[attr-defined]
                end = j
                break
            if d.level == 0 and j in heading_lines:                       # type: ignore[attr-defined]
                end = j
                break
            if d.level == 0:                                              # type: ignore[attr-defined]
                m2 = re.match(r"^(\s*)[-*+]\s+", lines[j])
                if m2 and len(m2.group(1)) <= d.indent:                   # type: ignore[attr-defined]
                    end = j
                    break
        d.end = end
    return headings, defs


def file_tokens(text: str) -> List[str]:
    toks: List[str] = []
    for m in SOURCE_RE.finditer(text):
        for t in FILE_TOKEN_RE.findall(m.group(1)):
            t = t.strip(".,;:()[]`*_")
            if t and not re.fullmatch(r"\d+(\.\d+)*", t):
                toks.append(t)
    return toks


def resolve_source(token: str, bases: List[Path]) -> bool:
    token = token.replace("\\", "/")
    for b in bases:
        if (b / token).is_file():
            return True
    name = Path(token).name
    for b in bases:
        if b.is_dir() and any(p.is_file() for p in b.rglob(name)):
            return True
    return False


def check(prd: Path, sources: Optional[Path] = None) -> Dict[str, object]:
    text = prd.read_text(encoding="utf-8", errors="replace")
    lines = _strip_front_matter_and_fences(text)
    headings, defs = parse(lines)
    F: List[Finding] = []

    def err(i: int, code: str, msg: str) -> None:
        F.append(Finding("erreur", i + 1, code, msg))

    def warn(i: int, code: str, msg: str) -> None:
        F.append(Finding("avertissement", i + 1, code, msg))

    bases = [sources] if sources else []
    bases.append(prd.parent)

    # --- sections de niveau 2 -------------------------------------------------
    h2 = [(i, t) for i, lv, t in headings if lv == 2]

    def section(rx: "re.Pattern[str]") -> Optional[Tuple[int, int]]:
        for n, (i, t) in enumerate(h2):
            if rx.search(t):
                end = h2[n + 1][0] if n + 1 < len(h2) else len(lines)
                return i, end
        return None

    feat_sec = section(FEATURES_RE)
    feats: List[Tuple[int, str]] = []
    if feat_sec:
        feats = [(i, t) for i, lv, t in headings if lv == 3 and feat_sec[0] < i < feat_sec[1]]
    else:
        err(0, "no-features", "section Features / Fonctionnalités (## 4) introuvable")

    # --- identifiants : unicité, continuité --------------------------------
    by_key: Dict[str, List[Item]] = {}
    for d in defs:
        by_key.setdefault(d.key, []).append(d)
    for k, items in by_key.items():
        if len(items) > 1:
            err(items[1].line, "dup-id", f"{k} défini {len(items)} fois (lignes {', '.join(str(x.line + 1) for x in items)})")
    for p in PREFIXES:
        nums = sorted({int(k.split("-")[-1]) for k in by_key if k.rsplit("-", 1)[0] == p})
        if nums:
            gaps = [n for n in range(1, nums[-1] + 1) if n not in nums]
            if gaps:
                warn(by_key[f"{p}-{nums[0]}"][0].line, "gap-id", f"{p} : numéros manquants {', '.join(f'{p}-{g}' for g in gaps)}")

    # --- FR / NFR : source ou hypothèse --------------------------------------
    stats = {"FR": 0, "NFR": 0, "FR_avec_source": 0, "NFR_avec_source": 0}
    cited_all: Set[str] = set()
    for d in defs:
        pre = d.key.rsplit("-", 1)[0]
        if pre not in ("FR", "NFR"):
            continue
        block = "\n".join(lines[d.line:d.end])
        toks = file_tokens(block)
        assumed = any(t.lower() in block.lower() for t in ASSUMPTION_TAGS)
        stats[pre] += 1
        if toks:
            stats[pre + "_avec_source"] += 1
        elif SOURCE_RE.search(block):
            err(d.line, "source-sans-fichier", f"{d.key} : « source : » sans nom de fichier (citer le .md et la section)")
        elif assumed:
            warn(d.line, "hypothese-seule", f"{d.key} ne repose que sur une hypothèse : à confirmer avant de s'en servir")
        else:
            err(d.line, "sans-source", f"{d.key} sans source : ajouter (source : fichier.md, § section) ou [ASSUMPTION: …]")

    # --- fichiers cités : ils existent ---------------------------------------
    for i, ln in enumerate(lines):
        for t in file_tokens(ln):
            cited_all.add(t)
            if not resolve_source(t, bases):
                err(i, "source-introuvable", f"source citée introuvable : {t}")

    # --- FR orphelins, fonctionnalités vides ----------------------------------
    fr_defs = [d for d in defs if d.key.startswith("FR-")]
    feat_of: Dict[str, Optional[str]] = {}
    for d in fr_defs:
        owner = None
        if feat_sec and feat_sec[0] < d.line < feat_sec[1]:
            owners = [t for i, t in feats if i < d.line]
            owner = owners[-1] if owners else None
        feat_of[d.key] = owner
        if owner is None:
            err(d.line, "fr-orphelin", f"{d.key} hors de toute fonctionnalité (§ Features) : le rattacher à une fonctionnalité")
    for n, (i, t) in enumerate(feats):
        nxt = feats[n + 1][0] if n + 1 < len(feats) else feat_sec[1]       # type: ignore[index]
        if not any(i < d.line < nxt for d in fr_defs):
            err(i, "feature-vide", f"fonctionnalité « {t} » sans aucun FR")

    # --- epics (facultatifs) --------------------------------------------------
    epics = [(i, lv, t) for i, lv, t in headings if EPIC_RE.search(t)]
    covered: Set[str] = set()
    for i, lv, t in epics:
        end = len(lines)
        for j, lv2, _ in headings:
            if j > i and lv2 <= lv:
                end = j
                break
        refs = {_key(m.group(1), m.group(2)) for m in ID_RE.finditer("\n".join(lines[i:end])) if m.group(1) == "FR"}
        if not refs:
            err(i, "epic-sans-fr", f"epic « {t} » ne renvoie à aucun FR")
        covered |= refs
    if epics:
        for d in fr_defs:
            if d.key not in covered:
                err(d.line, "fr-non-couvert", f"{d.key} n'est couvert par aucun epic")

    # --- références résolues ---------------------------------------------------
    defined = set(by_key)
    seen_missing: Set[str] = set()
    for i, ln in enumerate(lines):
        for m in ID_RE.finditer(ln):
            k = _key(m.group(1), m.group(2))
            if k not in defined and (k, i) not in seen_missing:
                seen_missing.add((k, i))                                  # type: ignore[arg-type]
                err(i, "ref-inconnue", f"{k} référencé mais jamais défini")

    # --- parcours, indicateurs ---------------------------------------------
    uj = [d for d in defs if d.key.startswith("UJ-")]
    if uj:
        used: Set[str] = set()
        for d in fr_defs:
            block = "\n".join(lines[d.line:d.end])
            refs = {_key(m.group(1), m.group(2)) for m in ID_RE.finditer(block) if m.group(1) == "UJ"}
            used |= refs
            if not refs:
                warn(d.line, "fr-sans-uj", f"{d.key} ne renvoie à aucun parcours (« Realizes UJ-n »)")
        for d in uj:
            if d.key not in used:
                warn(d.line, "uj-non-realise", f"{d.key} n'est réalisé par aucun FR")
    for d in defs:
        if d.key.startswith("SM-") and not d.key.startswith("SM-C"):
            block = "\n".join(lines[d.line:d.end])
            if not any(m.group(1) == "FR" for m in ID_RE.finditer(block)):
                warn(d.line, "sm-sans-fr", f"{d.key} ne cite aucun FR qu'il valide (« Validates FR-n »)")

    # --- hypothèses, glossaire, questions ouvertes, placeholders ---------------
    idx_sec = None
    for n, (i, t) in enumerate(h2):
        if ASSUME_IDX_RE.search(t) and not OPENQ_RE.search(t):
            idx_sec = (i, h2[n + 1][0] if n + 1 < len(h2) else len(lines))
    inline = 0
    for i, ln in enumerate(lines):
        if idx_sec and idx_sec[0] <= i < idx_sec[1]:
            continue
        inline += len(re.findall(r"\[ASSUMPTION|\[HYPOTH[ÈE]SE", re.sub(r"`[^`]*`", "", ln), flags=re.I))
    if inline:
        if not idx_sec:
            warn(0, "no-assumption-index", f"{inline} hypothèse(s) en ligne mais aucune section « Assumptions Index / Index des hypothèses »")
        else:
            n_idx = sum(1 for ln in lines[idx_sec[0] + 1:idx_sec[1]] if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\S", ln))
            if n_idx != inline:
                warn(idx_sec[0], "assumption-index", f"{inline} hypothèse(s) en ligne, {n_idx} dans l'index : les deux doivent correspondre")
    if not section(GLOSSARY_RE):
        warn(0, "no-glossary", "section Glossary / Glossaire absente")
    oq = section(OPENQ_RE)
    if not oq:
        warn(0, "no-open-questions", "section Open Questions / Questions ouvertes absente")
    elif not any(re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\S", ln) for ln in lines[oq[0] + 1:oq[1]]):
        warn(oq[0], "open-questions-vide", "Questions ouvertes vide : vérifier qu'il ne manque vraiment rien dans les sources")
    for i, ln in enumerate(lines):
        m = PLACEHOLDER_RE.search(ln)
        if m:
            err(i, "placeholder", f"champ du gabarit non rempli : {m.group(0)}")

    F.sort(key=lambda f: (f.level != "erreur", f.line))
    counts = {p: len({k for k in by_key if k.rsplit("-", 1)[0] == p}) for p in PREFIXES}
    return {
        "prd": str(prd),
        "stats": {"FR": counts["FR"], "NFR": counts["NFR"], "UJ": counts["UJ"], "SM": counts["SM"] + counts["SM-C"],
                  "fonctionnalites": len(feats), "epics": len(epics), "hypotheses_en_ligne": inline,
                  "fichiers_sources_cites": len(cited_all),
                  "FR_NFR_avec_source": stats["FR_avec_source"] + stats["NFR_avec_source"],
                  "FR_NFR_total": stats["FR"] + stats["NFR"]},
        "erreurs": sum(1 for f in F if f.level == "erreur"),
        "avertissements": sum(1 for f in F if f.level == "avertissement"),
        "constats": [f.as_dict() for f in F],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Contrôle mécanique d'un PRD (gabarit BMAD) : sources, orphelins, références.")
    ap.add_argument("prd", help="fichier prd.md")
    ap.add_argument("--sources", help="dossier des sources .md (défaut : dossier du PRD)")
    ap.add_argument("--strict", action="store_true", help="les avertissements font échouer le contrôle")
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    a = ap.parse_args(argv)
    prd = Path(a.prd)
    if not prd.is_file():
        print(f"Fichier introuvable : {prd}", file=sys.stderr)
        return 2
    sources = Path(a.sources) if a.sources else None
    if sources and not sources.is_dir():
        print(f"Dossier de sources introuvable : {sources}", file=sys.stderr)
        return 2
    res = check(prd, sources)
    bad = res["erreurs"] or (a.strict and res["avertissements"])
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if bad else 0
    st = res["stats"]
    print(f"{prd.name} : {st['FR']} FR, {st['NFR']} NFR, {st['UJ']} parcours, {st['SM']} indicateurs, "
          f"{st['fonctionnalites']} fonctionnalités, {st['epics']} epics ; "
          f"{st['FR_NFR_avec_source']}/{st['FR_NFR_total']} exigences avec source, {st['hypotheses_en_ligne']} hypothèse(s)")
    for f in res["constats"]:
        mark = "✗" if f["niveau"] == "erreur" else "!"
        print(f"  {mark} ligne {f['ligne']:>4} [{f['code']}] {f['message']}")
    if not res["constats"]:
        print("  ✓ aucun défaut détecté")
    else:
        print(f"{res['erreurs']} erreur(s), {res['avertissements']} avertissement(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
