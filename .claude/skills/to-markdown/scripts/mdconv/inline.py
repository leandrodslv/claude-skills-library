"""Rendu Markdown du texte en ligne (gras, italique, code, liens, exposants) — partagé par DOCX, PPTX, ODF, RTF.

Le principe : les convertisseurs produisent une liste de ``Span`` (texte + mise
en forme) ; ce module la fusionne puis l'écrit en Markdown valide CommonMark :
espaces de bord sortis des marqueurs, italique « _x_ » (ou « *x* » au milieu
d'un mot), liens automatiques « <url> » quand le texte est l'adresse.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .util import clean_text, esc_block_start, esc_inline, wrap_emphasis

_ORDINALS = {"e", "er", "re", "ère", "è", "ème", "eme", "nd", "rd", "th", "st", "o", "os", "º", "ª", "d", "es", "res"}
_SUP = str.maketrans("0123456789+-=()niabcdefghjklmoprstuvwxyz", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵇᶜᵈᵉᶠᵍʰʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ")
_SUB = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")


def md_url(url: str) -> str:
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29").replace("<", "%3C").replace(">", "%3E")


def alt_clean(s: str) -> str:
    """Texte alternatif d'image sur une ligne, sans crochets."""
    s = clean_text(s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s.replace("[", "(").replace("]", ")")


@dataclass
class Fmt:
    bold: bool = False
    italic: bool = False
    strike: bool = False
    code: bool = False
    sup: bool = False
    sub: bool = False
    link: Optional[str] = None
    ins: bool = False
    dele: bool = False

    def key(self) -> Tuple:
        return (self.bold, self.italic, self.strike, self.code, self.sup, self.sub, self.link, self.ins, self.dele)

    def copy(self, **kw) -> "Fmt":
        d = dict(self.__dict__)
        d.update(kw)
        return Fmt(**d)


@dataclass
class Span:
    kind: str                # t | br | raw | block | fn | cm | math
    text: str = ""
    fmt: Fmt = field(default_factory=Fmt)
    display: bool = False
    size: float = 0.0        # corps de police en points (0 = inconnu)


def _edge(spans: List[Span], i: int, direction: int) -> str:
    """Caractère voisin (collé) d'un segment, pour choisir entre « _x_ » et « *x* ».

    Un voisin lui-même mis en forme se termine/commence par un marqueur
    (ponctuation), pas par une lettre.
    """
    j = i + direction
    if 0 <= j < len(spans) and spans[j].kind == "t" and spans[j].text:
        f = spans[j].fmt
        if f.bold or f.italic or f.strike or f.code or f.link or f.sup or f.sub or f.ins or f.dele:
            return "*"
        return spans[j].text[-1] if direction < 0 else spans[j].text[0]
    return ""


def merge_spans(spans: List[Span]) -> List[Span]:
    """Fusionne les segments contigus de même format ; un blanc non formaté entre deux
    segments identiques en hérite (évite « **a** **b** » au lieu de « **a b** »)."""
    for k in range(1, len(spans) - 1):
        a, b, c = spans[k - 1], spans[k], spans[k + 1]
        if (a.kind == b.kind == c.kind == "t" and not b.text.strip() and a.fmt.key() == c.fmt.key()
                and b.fmt.key() != a.fmt.key() and (a.fmt.bold or a.fmt.italic or a.fmt.strike) and not a.fmt.link):
            b.fmt = a.fmt.copy()
    out: List[Span] = []
    for s in spans:
        if out and s.kind == "t" and out[-1].kind == "t" and s.fmt.key() == out[-1].fmt.key():
            out[-1] = Span("t", out[-1].text + s.text, out[-1].fmt, size=max(out[-1].size, s.size))
        else:
            out.append(s)
    return out


def _script(txt: str, f: Fmt, prev: str) -> str:
    """Exposant/indice : Unicode si c'est un exposant court (m², H₂O), texte simple pour 1er/2e, sinon <sup>."""
    stripped = txt.strip()
    lead, trail = txt[: len(txt) - len(txt.lstrip())], txt[len(txt.rstrip()):]
    low = stripped.lower().replace("−", "-")
    if f.sup:
        if low in _ORDINALS and prev[-1:].isdigit():
            return txt
        if re.fullmatch(r"[0-9+\-=()]{1,6}|[nixyzabc]", low):
            return lead + low.translate(_SUP) + trail
    elif re.fullmatch(r"[0-9+\-=()]{1,6}|[aehijklmnoprstuvx]", low):
        return lead + low.translate(_SUB) + trail
    tag = "sup" if f.sup else "sub"
    inner = wrap_emphasis(stripped, False, False, code=True) if f.code else wrap_emphasis(
        esc_inline(stripped), f.bold, f.italic, f.strike)
    return f"{lead}<{tag}>{inner}</{tag}>{trail}"


def fmt_text(s: Span, prev: str = "", nxt: str = "") -> str:
    """Un segment de texte, avec sa mise en forme, en Markdown."""
    txt = clean_text(s.text)
    f = s.fmt
    if not txt:
        return ""
    if f.sup or f.sub:
        return _script(txt, f, prev)
    if f.code:
        return wrap_emphasis(txt, False, False, False, code=True)
    body = esc_inline(txt)
    intraword = bool(f.italic) and (
        (prev[-1:].isalnum() and not txt[:1].isspace()) or (nxt[:1].isalnum() and not txt[-1:].isspace()))
    out = wrap_emphasis(body, f.bold, f.italic, f.strike, intraword=intraword)
    if f.dele or f.ins:
        core = out.strip()
        tag = "del" if f.dele else "ins"
        return out.replace(core, f"<{tag}>{core}</{tag}>", 1) if core else out
    return out


def render_spans(spans: List[Span], inline_only: bool = False,
                 note_ref: Optional[Callable[[str, bool], str]] = None,
                 comment_ref: Optional[Callable[[str], str]] = None,
                 escape_start: bool = True) -> str:
    """Liste de segments → une ligne (ou un paragraphe) de Markdown."""
    spans = merge_spans(spans)
    parts: List[str] = []
    i, n = 0, len(spans)
    while i < n:
        s = spans[i]
        if s.kind == "t":
            if s.fmt.link:
                j = i
                inner: List[str] = []
                while j < n and spans[j].kind == "t" and spans[j].fmt.link == s.fmt.link:
                    inner.append(fmt_text(spans[j], _edge(spans, j, -1), _edge(spans, j, 1)))
                    j += 1
                label = "".join(inner)
                plain = re.sub(r"[*_`~\\]", "", label).strip()
                url = s.fmt.link
                norm = lambda u: re.sub(r"^https?://|/$", "", u.strip())  # noqa: E731
                if plain and norm(plain) == norm(url) and re.match(r"(?i)^(https?|ftp)://", url):
                    parts.append(f"<{url}>")
                elif label.strip():
                    lead = label[: len(label) - len(label.lstrip())]
                    trail = label[len(label.rstrip()):]
                    parts.append(f"{lead}[{label.strip()}]({md_url(url)}){trail}")
                else:
                    parts.append(label)
                i = j
                continue
            parts.append(fmt_text(s, _edge(spans, i, -1), _edge(spans, i, 1)))
        elif s.kind == "br":
            parts.append(" " if inline_only else "\\\n")
        elif s.kind == "raw":
            parts.append(s.text)
        elif s.kind == "math":
            parts.append(f"$${s.text}$$" if s.display else f"${s.text}$")
        elif s.kind == "fn" and note_ref:
            parts.append(note_ref(s.text, s.display))
        elif s.kind == "cm" and comment_ref:
            ref = comment_ref(s.text)
            if ref:
                parts.append(ref)
        i += 1
    text = "".join(parts)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\\\n", "\\\n", text)
    text = re.sub(r"(\\\n)+\s*$", "", text).strip()
    text = re.sub(r"\\\n\s+", "\\\n", text)
    if escape_start and text and not text.startswith(("![", "<")):
        return esc_block_start(text)
    return text
