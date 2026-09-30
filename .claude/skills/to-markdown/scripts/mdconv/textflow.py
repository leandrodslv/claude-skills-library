"""Remise en forme du texte brut issu de PDF/OCR : paragraphes, dé-césure, listes, titres, en-têtes/pieds de page.

Les extracteurs « texte seul » (pdftotext, pypdf, OCR…) rendent des lignes coupées à la largeur de la page.
Ce module reconstitue des paragraphes lisibles sans jamais inventer de contenu.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional, Sequence

from .util import clean_text, esc_inline

_BULLET = re.compile(r"^\s*([•·▪◦●○■□◆◇➢➤▶►‣⁃–—*-]|\(?\d{1,3}[.)]|\(?[a-zA-Z][.)]|[ivxIVX]{1,4}[.)])\s+(?=\S)")
_PAGE_NUM = re.compile(r"^\s*(?:page|p\.|-)?\s*\d{1,4}\s*(?:/|sur|of|de)?\s*\d{0,4}\s*-?\s*$", re.I)
_NUM_HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})\.?\s+([A-ZÉÈÀÂÊÎÔÛÇ][^.!?;]{2,78})$")
_SENT_END = re.compile(r"[.!?:;»”\")\]]$")
_HEAD_MARK = re.compile(r"^⟪H([1-5])⟫\s*(.*)$")      # titre repéré par le lecteur PDF (taille de police / gras)


_PAGE_WORD = r"(?:pages?|pag\.|p\.|seite|pagina)"
_OF = r"(?:/|sur|of|de|von)"


def _has_page_cue(t: str) -> bool:
    """La ligne (déjà en minuscules) ressemble-t-elle à une numérotation de page ? Courte, avec le numéro à une extrémité."""
    if len(t) > 80:
        return False
    if re.fullmatch(r"[-–—\s]*\d+[-–—\s]*", t):                                  # « 3 », « - 3 - »
        return True
    if len(t) <= 40 and re.search(rf"\b\d+\s*{_OF}\s*\d+\b", t):                  # « 3 / 12 », « 3 sur 12 »
        return True
    if re.match(rf"{_PAGE_WORD}\s*\d+", t) or re.search(rf"{_PAGE_WORD}\s*\d+(?:\s*{_OF}\s*\d+)?[\s.]*$", t):
        return True                                                                # « Page 3 — Rapport », « Rapport - page 3 »
    return bool(re.search(r"[|•·–—]\s*\d+\s*$", t) or re.match(r"\d+\s*[|•·–—]", t))     # « Rapport | 3 », « 3 | Rapport »


def _norm_for_repeat(line: str) -> str:
    """Forme comparable d'une ligne d'en-tête/pied : les chiffres ne sont neutralisés que pour une numérotation de page,
    jamais pour « Chapitre 3 » ou « Article 12 » qui sont de vrais titres."""
    t = re.sub(r"\s+", " ", line.strip().lower())
    return re.sub(r"\d+", "#", t) if _has_page_cue(t) else t


def _edge_for(n_lines: int, edge: int) -> int:
    """Nombre de lignes candidates en haut/bas d'une page : jamais plus du tiers d'une page courte."""
    return min(edge, max(1, n_lines // 3))


def strip_repeated(pages: Sequence[str], edge: int = 3) -> List[str]:
    """Retire les lignes qui reviennent sur au moins la moitié des pages (en-têtes, pieds, numéros)."""
    if len(pages) < 2:
        return [_drop_page_numbers(p) for p in pages]
    heads: Counter = Counter()
    tails: Counter = Counter()
    split = []
    for p in pages:
        lines = [ln for ln in p.split("\n")]
        ne = [i for i, ln in enumerate(lines) if ln.strip()]
        e = _edge_for(len(ne), edge)
        split.append((lines, ne, e))
        for i in ne[:e]:
            heads[_norm_for_repeat(lines[i])] += 1
        for i in ne[-e:]:
            tails[_norm_for_repeat(lines[i])] += 1
    threshold = max(2, int(len(pages) * 0.5))
    drop_h = {k for k, v in heads.items() if v >= threshold and len(k) < 120}
    drop_t = {k for k, v in tails.items() if v >= threshold and len(k) < 120}
    out = []
    for lines, ne, e in split:
        kill = set()
        for i in ne[:e]:
            if _norm_for_repeat(lines[i]) in drop_h:
                kill.add(i)
        for i in ne[-e:]:
            if _norm_for_repeat(lines[i]) in drop_t:
                kill.add(i)
        if kill and sum(len(lines[i].split()) for i in kill) * 2 > sum(len(lines[i].split()) for i in ne):
            kill = set()      # on ne retire jamais plus de la moitié d'une page (gabarit, formulaire répété…)
        out.append(_drop_page_numbers("\n".join(ln for i, ln in enumerate(lines) if i not in kill)))
    return out


def repeated_sets(pages_lines: Sequence[Sequence[str]], edge: int = 3):
    """Ensembles (en-têtes, pieds) de lignes normalisées qui reviennent sur au moins la moitié des pages."""
    if len(pages_lines) < 2:
        return set(), set()
    heads: Counter = Counter()
    tails: Counter = Counter()
    for lines in pages_lines:
        ne = [ln for ln in lines if ln.strip()]
        e = _edge_for(len(ne), edge)
        for ln in ne[:e]:
            heads[_norm_for_repeat(ln)] += 1
        for ln in ne[-e:]:
            tails[_norm_for_repeat(ln)] += 1
    threshold = max(2, int(len(pages_lines) * 0.5))
    return ({k for k, v in heads.items() if v >= threshold and len(k) < 120},
            {k for k, v in tails.items() if v >= threshold and len(k) < 120})


def is_page_number(line: str) -> bool:
    return bool(_PAGE_NUM.match(line)) and len(line.strip()) <= 12


def _drop_page_numbers(text: str) -> str:
    lines = text.split("\n")
    ne = [i for i, ln in enumerate(lines) if ln.strip()]
    for i in (ne[:1] + ne[-1:]):
        if i < len(lines) and _PAGE_NUM.match(lines[i]) and len(lines[i].strip()) <= 12:
            lines[i] = ""
    return "\n".join(lines)


def _heading_of(s: str) -> Optional[str]:
    """Titre Markdown si la ligne ressemble à un titre numéroté (« 2.1 Méthode ») ou en capitales."""
    if len(s) > 80 or len(s.split()) > 10 or _SENT_END.search(s):
        return None
    m = _NUM_HEADING.match(s)
    if m:
        return "#" * min(m.group(1).count(".") + 2, 5) + " " + s
    if s.isupper() and 2 <= len(s.split()) <= 9 and len(s) <= 70 and re.search(r"[A-ZÉÈÀ]{3}", s) and not re.search(r"\d{3,}", s):
        return "## " + s.title()
    return None


def _bullet_lead(marker: str) -> str:
    m = marker.strip()
    if re.fullmatch(r"\(?\d{1,3}[.)]", m):
        return re.sub(r"\D", "", m) + ". "
    if re.fullmatch(r"\(?[A-Za-z]{1,4}[.)]", m):
        return f"- {m} "
    return "- "


def reflow(text: str, headings: bool = True) -> str:
    """Lignes de largeur fixe → paragraphes Markdown (dé-césure, puces, titres numérotés ou en capitales)."""
    text = clean_text(text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [ln.rstrip() for ln in text.split("\n")]
    nonblank = [len(ln.strip()) for ln in lines if ln.strip()]
    if not nonblank:
        return ""
    ref = sorted(nonblank)[int(len(nonblank) * 0.75)]  # longueur « pleine » d'une ligne de paragraphe
    out: List[str] = []
    cur: List[str] = []

    def flush() -> None:
        if cur:
            para = _join(cur)
            if para.strip():
                out.append(para if para.startswith("- ") or re.match(r"^\d{1,3}\. ", para) else esc_inline(para))
            cur.clear()

    n = len(lines)
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            flush()
            continue
        hm = _HEAD_MARK.match(s)
        if hm:
            flush()
            if hm.group(2).strip():
                out.append("#" * int(hm.group(1)) + " " + esc_inline(hm.group(2).strip()))
            continue
        if headings:
            h = _heading_of(s)
            if h:
                flush()
                out.append(h)
                continue
        b = _BULLET.match(s)
        if b:
            flush()
            body = esc_inline(s[b.end():])
            cur.append(_bullet_lead(b.group(1)) + body)
            continue
        nxt = lines[i + 1].strip() if i + 1 < n else ""
        cur.append(s)
        short = len(s) < max(20, ref * 0.55)
        if short and _SENT_END.search(s) and (not nxt or nxt[:1].isupper() or nxt[:1].isdigit()):
            flush()
    flush()
    return "\n\n".join(_merge_list_items(out))


def _merge_list_items(blocks: List[str]) -> List[str]:
    res: List[str] = []
    for b in blocks:
        if res and b.startswith(("- ", "1. ")) and res[-1].startswith(("- ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")) and "\n\n" not in res[-1]:
            res[-1] += "\n" + b
        else:
            res.append(b)
    return res


def _join(parts: List[str]) -> str:
    """Joint les lignes d'un paragraphe en supprimant les césures (« infor- / mation » → « information »)."""
    out = parts[0]
    for nxt in parts[1:]:
        if re.search(r"[A-Za-zÀ-ÿ]-$", out) and nxt[:1].islower():
            out = out[:-1] + nxt
        else:
            out += " " + nxt
    return re.sub(r"[ \t]{2,}", " ", out)


def page_marker(n: int) -> str:
    return f"<!-- page {n} -->"


def words_count(text: str) -> int:
    return len(re.findall(r"\w+", text))
