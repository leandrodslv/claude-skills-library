"""Contrôle qualité : mesure ce qu'une conversion a pu perdre, sans jamais faire confiance au moteur.

Deux signaux complémentaires :
* le **rappel de mots** — proportion des mots de la source (extraits par une
  méthode indépendante de la mise en forme) retrouvés dans le Markdown ;
* des **détecteurs de bruit** — caractères de remplacement, « (cid:12) » des PDF
  mal décodés, texte quasi vide, lignes d'un caractère…
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .core import Result
from .util import word_recall, words

_CID = re.compile(r"\(cid:\d+\)")
_MOJIBAKE = re.compile(r"(?:Ã[\x80-\xbf©¨ª«¼]|â€[™œ\x9d\x93\x94¦]|Â[\xa0-\xbf])")


@dataclass
class Score:
    value: float
    recall: Optional[float] = None
    notes: List[str] = field(default_factory=list)
    words: int = 0


def assess(res: Result) -> Score:
    md = res.markdown or ""
    md_words = len(words(md))
    notes: List[str] = []
    if md_words == 0:
        if res.source_text is not None and not words(res.source_text) and not md.strip("# \n"):
            return Score(1.0, 1.0, ["document sans texte"], 0)
        return Score(0.0, None, ["sortie vide"], 0)
    value = 1.0
    recall: Optional[float] = None
    if res.source_text is not None:
        src_words = len(words(res.source_text))
        if src_words:
            recall = word_recall(res.source_text, md)
            value = recall
            if recall < 0.97:
                notes.append(f"rappel de texte {recall:.1%}")
            if md_words > src_words * 1.35 + 80 and not res.stats.get("partial_source"):
                value -= 0.10
                notes.append("texte probablement dupliqué")
    bad = md.count("�") + len(_CID.findall(md)) + len(_MOJIBAKE.findall(md))
    if bad:
        ratio = bad / md_words
        if ratio > 0.005:
            value -= min(0.6, ratio * 8)
            notes.append(f"{bad} caractère(s) illisible(s) ou mal décodé(s)")
    if res.units and res.unit_name == "page":
        per_page = md_words / res.units
        res.stats["words_per_page"] = round(per_page, 1)
        if per_page < 6:
            value = min(value, 0.35)
            notes.append(f"très peu de texte par page ({per_page:.1f} mots) : document probablement scanné")
        elif per_page < 20:
            value = min(value, 0.75)
            notes.append(f"peu de texte par page ({per_page:.1f} mots)")
    if res.units and res.units_found is not None and res.units_found < res.units:
        missing = res.units - res.units_found
        value -= min(0.3, 0.05 * missing)
        notes.append(f"{res.units_found}/{res.units} {res.unit_name or 'unités'} retrouvées")
    return Score(max(0.0, min(1.0, value)), recall, notes, md_words)


def lint_markdown(md: str) -> List[str]:
    """Anomalies de structure Markdown (clôtures non fermées, tableaux mal formés)."""
    problems: List[str] = []
    fence_open: Optional[str] = None
    table_widths: List[int] = []
    for line in md.split("\n"):
        s = line.strip()
        m = re.match(r"^(`{3,}|~{3,})", s)
        if m:
            if fence_open is None:
                fence_open = m.group(1)
            elif s.startswith(fence_open[0] * len(fence_open)) and set(s) <= {fence_open[0]}:
                fence_open = None
            continue
        if fence_open:
            continue
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            width = len(re.findall(r"(?<!\\)\|", s)) - 1
            table_widths.append(width)
        else:
            if len(set(table_widths)) > 1:
                problems.append("tableau aux lignes de largeurs différentes")
            table_widths = []
    if len(set(table_widths)) > 1:
        problems.append("tableau aux lignes de largeurs différentes")
    if fence_open:
        problems.append("bloc de code non refermé")
    return sorted(set(problems))
