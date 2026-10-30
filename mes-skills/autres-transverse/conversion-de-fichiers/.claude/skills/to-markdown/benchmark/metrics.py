"""Mesures du banc d'essai : fonctions pures, bibliothèque standard.

Tous les scores sont en pourcentage. Les mots sont comparés en multiensembles, sans casse ni ponctuation ;
les adresses (http…) sont retirées des deux côtés (leur présence est mesurée à part par « liens »).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

_URL = re.compile(r"https?://\S+")
_FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
_WORD = re.compile(r"\w+", re.U)
_LIST_LINE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+(.*)$")
_HEAD_LINE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")


_MARKER = re.compile(r"(?m)^\s*(?:[-*+•]|\d+[.)])\s+")


def tokens(text: str) -> List[str]:
    """Mots du texte ; adresses et puces / numéros de liste (syntaxe Markdown, pas du contenu) ignorés."""
    return _WORD.findall(_MARKER.sub("", _URL.sub(" ", text)).casefold())


def _norm(text: str) -> str:
    return " ".join(tokens(text))


def strip_front_matter(md: str) -> str:
    return _FRONT.sub("", md, count=1)


def recall_precision(truth_text: str, output: str) -> Tuple[float, float]:
    t, o = Counter(tokens(truth_text)), Counter(tokens(output))
    if not t:
        return 100.0, 100.0
    common = sum((t & o).values())
    rec = 100.0 * common / sum(t.values())
    prec = 100.0 * common / sum(o.values()) if o else 0.0
    return rec, prec


def _share(found: int, total: int) -> Optional[float]:
    return None if total == 0 else 100.0 * found / total


def headings_score(truth: Sequence[str], output: str) -> Optional[float]:
    lines = [_norm(m.group(1)) for ln in output.splitlines() if (m := _HEAD_LINE.match(ln))]
    return _share(sum(1 for h in truth if any(_norm(h) and _norm(h) in ln for ln in lines)), len(truth))


def cells_score(truth: Sequence[str], output: str) -> Optional[float]:
    rows = [_norm(ln) for ln in output.splitlines() if ln.lstrip().startswith("|")]
    cells = [c for c in truth if _norm(c)]
    return _share(sum(1 for c in cells if any(_norm(c) in r for r in rows)), len(cells))


def items_score(truth: Sequence[str], output: str) -> Optional[float]:
    lines = [_norm(m.group(1)) for ln in output.splitlines() if (m := _LIST_LINE.match(ln))]
    return _share(sum(1 for i in truth if any(_norm(i) in ln for ln in lines)), len(truth))


def links_score(truth: Sequence[Tuple[str, str]], output: str) -> Optional[float]:
    found = 0
    for text, url in truth:
        pat = r"\[[^\]]*" + re.escape(text.split()[-1]) + r"[^\]]*\]\(\s*<?" + re.escape(url) + r"[>\s\"')]|<" + re.escape(url) + r">"
        if re.search(pat, output):
            found += 1
    return _share(found, len(truth))


def score_output(truth, output: str) -> Dict[str, Optional[float]]:
    output = strip_front_matter(output)
    rec, prec = recall_precision(truth.text, output)
    return {
        "recall": rec, "precision": prec,
        "headings": headings_score(truth.headings, output),
        "tables": cells_score(truth.cells, output),
        "lists": items_score(truth.items, output),
        "links": links_score(truth.links, output),
    }


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None
