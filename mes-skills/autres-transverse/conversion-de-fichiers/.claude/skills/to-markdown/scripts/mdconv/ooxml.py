"""Briques communes à DOCX / PPTX / XLSX : espaces de noms, graphiques, SmartArt, équations, propriétés."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Sequence, Tuple

from .util import SafeZip, UnsafeXML, clean_text, esc_inline, local, md_table, parse_xml

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "v": "urn:schemas-microsoft-com:vml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dcterms": "http://purl.org/dc/terms/",
}


def W(tag: str) -> str:
    return "{%s}%s" % (NS["w"], tag)


def A(tag: str) -> str:
    return "{%s}%s" % (NS["a"], tag)


def P(tag: str) -> str:
    return "{%s}%s" % (NS["p"], tag)


def C(tag: str) -> str:
    return "{%s}%s" % (NS["c"], tag)


def M(tag: str) -> str:
    return "{%s}%s" % (NS["m"], tag)


def R(tag: str) -> str:
    return "{%s}%s" % (NS["r"], tag)


# Variante « Strict » d'Office Open XML : mêmes éléments, autres espaces de noms.
_STRICT = (
    (b"http://purl.oclc.org/ooxml/wordprocessingml/main", b"http://schemas.openxmlformats.org/wordprocessingml/2006/main"),
    (b"http://purl.oclc.org/ooxml/presentationml/main", b"http://schemas.openxmlformats.org/presentationml/2006/main"),
    (b"http://purl.oclc.org/ooxml/spreadsheetml/main", b"http://schemas.openxmlformats.org/spreadsheetml/2006/main"),
    (b"http://purl.oclc.org/ooxml/drawingml/main", b"http://schemas.openxmlformats.org/drawingml/2006/main"),
    (b"http://purl.oclc.org/ooxml/drawingml/chart", b"http://schemas.openxmlformats.org/drawingml/2006/chart"),
    (b"http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing", b"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"),
    (b"http://purl.oclc.org/ooxml/drawingml/diagram", b"http://schemas.openxmlformats.org/drawingml/2006/diagram"),
    (b"http://purl.oclc.org/ooxml/drawingml/picture", b"http://schemas.openxmlformats.org/drawingml/2006/picture"),
    (b"http://purl.oclc.org/ooxml/officeDocument/relationships", b"http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
    (b"http://purl.oclc.org/ooxml/officeDocument/math", b"http://schemas.openxmlformats.org/officeDocument/2006/math"),
)


def load_xml(zf: SafeZip, name: str) -> Optional[ET.Element]:
    """Charge une partie XML ; ramène la variante Strict à la variante Transitional."""
    data = zf.read_opt(name)
    if data is None:
        return None
    if b"purl.oclc.org/ooxml" in data:
        for old, new in _STRICT:
            data = data.replace(old, new)
    try:
        return parse_xml(data)
    except (ET.ParseError, UnsafeXML):
        return None


def find_all(el: ET.Element, path: str) -> List[ET.Element]:
    return el.findall(path, NS)


def text_of(el: Optional[ET.Element], tag_ns: str = "a", tag: str = "t") -> str:
    """Concatène tous les <a:t> (ou autre balise) d'un sous-arbre."""
    if el is None:
        return ""
    t = "{%s}%s" % (NS[tag_ns], tag)
    return "".join((x.text or "") for x in el.iter(t))


# --------------------------------------------------------------------------
# Propriétés du document
# --------------------------------------------------------------------------

def core_props(zf: SafeZip) -> Dict[str, str]:
    """Titre, auteur, dates… lus dans docProps/core.xml et app.xml."""
    out: Dict[str, str] = {}
    root = load_xml(zf, "docProps/core.xml")
    if root is not None:
        for key, ns, tag in (
            ("title", "dc", "title"), ("author", "dc", "creator"), ("subject", "dc", "subject"),
            ("description", "dc", "description"), ("keywords", "cp", "keywords"),
            ("language", "dc", "language"), ("created", "dcterms", "created"),
            ("modified", "dcterms", "modified"), ("last_modified_by", "cp", "lastModifiedBy"),
        ):
            el = root.find("{%s}%s" % (NS[ns], tag))
            if el is not None and (el.text or "").strip():
                out[key] = clean_text(el.text.strip())
    app = load_xml(zf, "docProps/app.xml")
    if app is not None:
        for el in app:
            name = local(el.tag)
            if name in ("Application", "Company") and (el.text or "").strip():
                out[name.lower()] = el.text.strip()
    return out


# --------------------------------------------------------------------------
# Graphiques (partagés DOCX / PPTX / XLSX)
# --------------------------------------------------------------------------

_CHART_KINDS = {
    "barChart": "histogramme/barres", "bar3DChart": "histogramme/barres 3D", "lineChart": "courbes",
    "line3DChart": "courbes 3D", "pieChart": "secteurs", "pie3DChart": "secteurs 3D",
    "doughnutChart": "anneau", "areaChart": "aires", "area3DChart": "aires 3D", "scatterChart": "nuage de points",
    "bubbleChart": "bulles", "radarChart": "radar", "stockChart": "cours de bourse",
    "surfaceChart": "surface", "surface3DChart": "surface 3D", "ofPieChart": "secteurs composés",
}


def _pts(cache: Optional[ET.Element]) -> List[Tuple[int, str]]:
    """Points (indice, valeur) d'un c:strCache / c:numCache."""
    out: List[Tuple[int, str]] = []
    if cache is None:
        return out
    for pt in cache.findall("c:pt", NS):
        v = pt.find("c:v", NS)
        out.append((int(pt.get("idx", len(out))), (v.text or "") if v is not None else ""))
    return out


def _series_ref(ser_child: Optional[ET.Element], resolver=None) -> List[str]:
    """Valeurs d'un c:cat / c:val / c:tx / c:xVal / c:yVal, en liste dense.

    ``resolver(formule)`` lit les cellules référencées quand le graphique n'embarque pas de cache.
    """
    if ser_child is None:
        return []
    cache = None
    for path in ("c:strRef/c:strCache", "c:numRef/c:numCache", "c:multiLvlStrRef/c:multiLvlStrCache/c:lvl",
                 "c:strLit", "c:numLit"):
        cache = ser_child.find(path, NS)
        if cache is not None:
            break
    if (cache is None or not cache.findall("c:pt", NS)) and resolver is not None:
        f = next((x for x in ser_child.iter("{%s}f" % NS["c"]) if (x.text or "").strip()), None)
        if f is not None:
            try:
                got = resolver(f.text.strip())
            except Exception:
                got = None
            if got:
                return [str(v) for v in got]
    pts = _pts(cache)
    count_el = cache.find("c:ptCount", NS) if cache is not None else None
    n = int(count_el.get("val", 0)) if count_el is not None else 0
    n = max(n, (max((i for i, _ in pts), default=-1) + 1))
    dense = [""] * n
    for i, v in pts:
        if 0 <= i < n:
            dense[i] = v
    if not dense and ser_child.find("c:v", NS) is not None:  # c:tx/c:v direct
        return [ser_child.find("c:v", NS).text or ""]
    return dense


def _num(s: str) -> str:
    """Nombre du cache sans bruit binaire (0.30000000000000004 → 0.3)."""
    try:
        f = float(s)
    except ValueError:
        return s
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return format(f, ".10g")


def parse_chart(root: ET.Element, resolver=None) -> Dict[str, object]:
    """Extrait titre, type, catégories et séries d'un graphique (valeurs en cache)."""
    chart = root.find("c:chart", NS)
    info: Dict[str, object] = {"title": "", "kinds": [], "series": [], "categories": [], "x_title": "", "y_title": ""}
    if chart is None:
        return info
    t = chart.find("c:title", NS)
    if t is not None:
        info["title"] = clean_text(text_of(t)).strip()
    plot = chart.find("c:plotArea", NS)
    if plot is None:
        return info
    for ax_tag, key in (("catAx", "x_title"), ("dateAx", "x_title"), ("valAx", "y_title")):
        for ax in plot.findall("c:" + ax_tag, NS):
            at = ax.find("c:title", NS)
            if at is not None and not info[key]:
                info[key] = clean_text(text_of(at)).strip()
    cats: List[str] = []
    for kind_el in plot:
        name = local(kind_el.tag)
        if name not in _CHART_KINDS:
            continue
        label = _CHART_KINDS[name]
        if name.startswith("bar"):
            bd = kind_el.find("c:barDir", NS)
            label = "barres" if (bd is not None and bd.get("val") == "bar") else "histogramme"
        grouping = kind_el.find("c:grouping", NS)
        if grouping is not None and grouping.get("val") in ("stacked", "percentStacked"):
            label += " empilé" + (" 100 %" if grouping.get("val") == "percentStacked" else "")
        info["kinds"].append(label)  # type: ignore[union-attr]
        for ser in kind_el.findall("c:ser", NS):
            name_vals = _series_ref(ser.find("c:tx", NS), resolver)
            sname = clean_text(name_vals[0]) if name_vals else ""
            if name == "scatterChart" or name == "bubbleChart":
                xs = [_num(v) for v in _series_ref(ser.find("c:xVal", NS), resolver)]
                ys = [_num(v) for v in _series_ref(ser.find("c:yVal", NS), resolver)]
                if xs and not cats:
                    cats = xs
                info["series"].append((sname, ys, xs))  # type: ignore[union-attr]
                continue
            cat = ser.find("c:cat", NS)
            cvals = [clean_text(v) for v in _series_ref(cat, resolver)]
            if cvals and (not cats or len(cvals) > len(cats)):
                cats = cvals
            vals = [_num(v) for v in _series_ref(ser.find("c:val", NS), resolver)]
            info["series"].append((sname, vals, None))  # type: ignore[union-attr]
    info["categories"] = cats
    return info


def chart_markdown(info: Dict[str, object], max_rows: int = 0) -> str:
    """Rend un graphique sous forme d'un court intitulé + tableau de données."""
    kinds = ", ".join(dict.fromkeys(info.get("kinds") or [])) or "graphique"  # type: ignore[arg-type]
    title = info.get("title") or ""
    head = f"**Graphique ({kinds})" + (f" — {esc_inline(str(title))}" if title else "") + "**"
    axes = []
    if info.get("x_title"):
        axes.append(f"axe X : {esc_inline(str(info['x_title']))}")
    if info.get("y_title"):
        axes.append(f"axe Y : {esc_inline(str(info['y_title']))}")
    if axes:
        head += " — " + ", ".join(axes)
    series = info.get("series") or []
    if not series:
        return head + "\n\n_(données du graphique non embarquées)_"
    cats: Sequence[str] = info.get("categories") or []  # type: ignore[assignment]
    scatter = any(s[2] is not None for s in series)  # type: ignore[index]
    rows: List[List[str]] = []
    if scatter:
        # un x commun → colonnes y multiples ; sinon un tableau (x, y) par série
        first_x = series[0][2]
        if all(s[2] == first_x for s in series):  # type: ignore[index]
            rows.append(["x"] + [esc_inline(s[0]) or f"y{i + 1}" for i, s in enumerate(series)])  # type: ignore[index]
            for i, x in enumerate(first_x):  # type: ignore[arg-type]
                rows.append([x] + [(s[1][i] if i < len(s[1]) else "") for s in series])  # type: ignore[index]
        else:
            out = [head]
            for s in series:
                r = [["x", esc_inline(s[0]) or "y"]] + [[x, y] for x, y in zip(s[2], s[1])]  # type: ignore[index]
                out.append(md_table(_cap(r, max_rows)))
            return "\n\n".join(out)
    else:
        n = max(len(cats), max((len(s[1]) for s in series), default=0))  # type: ignore[index]
        rows.append([""] + [esc_inline(s[0]) or f"Série {i + 1}" for i, s in enumerate(series)])  # type: ignore[index]
        for i in range(n):
            label = esc_inline(cats[i]) if i < len(cats) else str(i + 1)
            rows.append([label] + [(s[1][i] if i < len(s[1]) else "") for s in series])  # type: ignore[index]
    return head + "\n\n" + md_table(_cap(rows, max_rows))


def _cap(rows: List[List[str]], max_rows: int) -> List[List[str]]:
    if max_rows and len(rows) - 1 > max_rows:
        cut = len(rows) - 1 - max_rows
        rows = rows[: max_rows + 1] + [[f"… ({cut} lignes de plus)"] + [""] * (len(rows[0]) - 1)]
    return rows


def chart_source_text(info: Dict[str, object]) -> str:
    """Texte brut d'un graphique pour le calcul de rappel (titre, séries, catégories)."""
    parts = [str(info.get("title") or ""), str(info.get("x_title") or ""), str(info.get("y_title") or "")]
    parts += list(info.get("categories") or [])  # type: ignore[arg-type]
    for s in info.get("series") or []:  # type: ignore[union-attr]
        parts.append(s[0])
    return " ".join(parts)


# --------------------------------------------------------------------------
# SmartArt
# --------------------------------------------------------------------------

def smartart_outline(zf: SafeZip, data_part: str) -> List[str]:
    """Texte d'un SmartArt en liste à puces imbriquée (lignes déjà indentées)."""
    root = load_xml(zf, data_part)
    if root is None:
        return []
    pts: Dict[str, Tuple[str, str]] = {}
    for pt in root.findall("dgm:ptLst/dgm:pt", NS):
        mid = pt.get("modelId", "")
        ptype = pt.get("type", "node")
        t = pt.find("dgm:t", NS)
        pts[mid] = (ptype, clean_text(" ".join(filter(None, (
            "".join(x.text or "" for x in p.iter(A("t"))).strip() for p in (t.findall("a:p", NS) if t is not None else []))))))
    children: Dict[str, List[Tuple[int, str]]] = {}
    child_ids = set()
    for cxn in root.findall("dgm:cxnLst/dgm:cxn", NS):
        if cxn.get("type", "parOf") != "parOf":
            continue
        src, dst = cxn.get("srcId", ""), cxn.get("destId", "")
        if src in pts and dst in pts and pts[dst][0] in ("node", "asst"):
            children.setdefault(src, []).append((int(cxn.get("srcOrd", 0)), dst))
            child_ids.add(dst)
    roots = [m for m, (ty, _t) in pts.items() if ty == "doc"] or [m for m, (ty, _t) in pts.items() if ty in ("node", "asst") and m not in child_ids]
    lines: List[str] = []

    def walk(mid: str, depth: int, seen: set) -> None:
        if mid in seen:
            return
        seen.add(mid)
        for _o, kid in sorted(children.get(mid, [])):
            txt = pts[kid][1]
            if txt:
                lines.append("  " * depth + "- " + esc_inline(txt))
                walk(kid, depth + 1, seen)
            else:
                walk(kid, depth, seen)

    for r in roots:
        if pts[r][0] in ("node", "asst") and pts[r][1]:
            lines.append("- " + esc_inline(pts[r][1]))
            walk(r, 1, set())
        else:
            walk(r, 0, set())
    if not lines:  # à défaut d'arbre exploitable : tous les textes, à plat
        lines = ["- " + esc_inline(t) for (ty, t) in pts.values() if t and ty in ("node", "asst")]
    return lines


# --------------------------------------------------------------------------
# Équations OMML → LaTeX
# --------------------------------------------------------------------------

_LATEX_SYM = {
    "∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint", "⋃": r"\bigcup",
    "⋂": r"\bigcap", "≤": r"\le", "≥": r"\ge", "≠": r"\ne", "≈": r"\approx", "≡": r"\equiv", "∼": r"\sim",
    "×": r"\times", "÷": r"\div", "±": r"\pm", "∓": r"\mp", "·": r"\cdot", "⋅": r"\cdot", "∞": r"\infty",
    "→": r"\to", "←": r"\leftarrow", "↔": r"\leftrightarrow", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow", "∂": r"\partial", "∇": r"\nabla", "∈": r"\in", "∉": r"\notin", "⊂": r"\subset",
    "⊆": r"\subseteq", "⊃": r"\supset", "⊇": r"\supseteq", "∪": r"\cup", "∩": r"\cap", "∀": r"\forall",
    "∃": r"\exists", "∅": r"\emptyset", "…": r"\ldots", "⋯": r"\cdots", "∝": r"\propto", "°": r"^\circ",
    "′": "'", "″": "''", "−": "-", "∘": r"\circ", "⊕": r"\oplus", "⊗": r"\otimes", "∧": r"\wedge", "∨": r"\vee",
    "¬": r"\neg", "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}",
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "ε": r"\epsilon", "ζ": r"\zeta", "η": r"\eta",
    "θ": r"\theta", "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi",
    "π": r"\pi", "ρ": r"\rho", "σ": r"\sigma", "τ": r"\tau", "υ": r"\upsilon", "φ": r"\phi", "χ": r"\chi",
    "ψ": r"\psi", "ω": r"\omega", "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda", "Ξ": r"\Xi",
    "Π": r"\Pi", "Σ": r"\Sigma", "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega", "ϕ": r"\varphi", "ϵ": r"\varepsilon",
}
_FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log",
          "ln", "lg", "exp", "lim", "min", "max", "sup", "inf", "det", "dim", "ker", "gcd", "arg", "deg", "Pr"}
_ACCENTS = {"̂": "hat", "̄": "bar", "⃗": "vec", "̃": "tilde", "̇": "dot",
            "̈": "ddot", "̌": "check", "́": "acute", "̀": "grave", "^": "hat", "~": "tilde",
            "¯": "bar", "→": "vec", "˙": "dot"}


def _mval(el: Optional[ET.Element], tag: str, default: str = "") -> str:
    if el is None:
        return default
    x = el.find("m:" + tag, NS)
    return x.get("{%s}val" % NS["m"], default) if x is not None else default


_MATH_INVISIBLE = dict.fromkeys(range(0x2061, 0x2065), None)  # application de fonction, multiplication invisible…


def _sym(text: str) -> str:
    out = []
    for ch in text.translate(_MATH_INVISIBLE):
        if ch in _LATEX_SYM:
            out.append(_LATEX_SYM[ch] + " ")
        elif ch in "{}":
            out.append("\\" + ch)
        elif ch == "\\":
            out.append(r"\backslash ")
        elif ch in "#$%&_":
            out.append("\\" + ch)
        else:
            out.append(ch)
    s = "".join(out)
    return re.sub(r"(\\[A-Za-z]+) (?=[^A-Za-z\\])", r"\1 ", s)


def omml_to_latex(el: ET.Element) -> str:
    """Convertit un sous-arbre OMML (m:oMath) en LaTeX (sans délimiteurs $)."""
    return _omml(el).strip()


def _kids(el: Optional[ET.Element], skip: Sequence[str] = ()) -> str:
    if el is None:
        return ""
    return "".join(_omml(c) for c in el if local(c.tag) not in skip and not local(c.tag).endswith("Pr"))


def _omml(el: ET.Element) -> str:
    name = local(el.tag)
    if name in ("oMath", "e", "num", "den", "sub", "sup", "deg", "lim", "fName", "oMathPara", "box", "phant",
                "borderBox", "groupChr", "mr"):
        return _kids(el)
    if name == "r":
        sty = _mval(el.find("m:rPr", NS), "sty")
        raw = "".join(t.text or "" for t in el.findall("m:t", NS))
        txt = _sym(raw)
        if sty == "p" and len(raw) > 1 and raw.isalpha():
            return r"\mathrm{%s}" % raw
        return txt
    if name == "f":
        typ = _mval(el.find("m:fPr", NS), "type")
        num, den = _kids(el.find("m:num", NS)), _kids(el.find("m:den", NS))
        if typ == "noBar":
            return r"\binom{%s}{%s}" % (num, den)
        if typ == "lin":
            return "%s/%s" % (num, den)
        return r"\frac{%s}{%s}" % (num, den)
    if name == "sSup":
        return "{%s}^{%s}" % (_kids(el.find("m:e", NS)), _kids(el.find("m:sup", NS)))
    if name == "sSub":
        return "{%s}_{%s}" % (_kids(el.find("m:e", NS)), _kids(el.find("m:sub", NS)))
    if name == "sSubSup":
        return "{%s}_{%s}^{%s}" % (_kids(el.find("m:e", NS)), _kids(el.find("m:sub", NS)), _kids(el.find("m:sup", NS)))
    if name == "sPre":
        return "{}_{%s}^{%s}{%s}" % (_kids(el.find("m:sub", NS)), _kids(el.find("m:sup", NS)), _kids(el.find("m:e", NS)))
    if name == "rad":
        deg = _kids(el.find("m:deg", NS)).strip()
        hide = _mval(el.find("m:radPr", NS), "degHide") in ("1", "on", "true")
        body = _kids(el.find("m:e", NS))
        return (r"\sqrt[%s]{%s}" % (deg, body)) if deg and not hide else (r"\sqrt{%s}" % body)
    if name == "nary":
        pr = el.find("m:naryPr", NS)
        chr_el = pr.find("m:chr", NS) if pr is not None else None
        ch = chr_el.get("{%s}val" % NS["m"], "∫") if chr_el is not None else "∫"
        op = _LATEX_SYM.get(ch, ch)
        sub, sup = _kids(el.find("m:sub", NS)).strip(), _kids(el.find("m:sup", NS)).strip()
        s = op
        if sub:
            s += "_{%s}" % sub
        if sup:
            s += "^{%s}" % sup
        return s + " " + _kids(el.find("m:e", NS))
    if name == "d":
        pr = el.find("m:dPr", NS)
        beg = _mval(pr, "begChr", "(") if pr is not None and pr.find("m:begChr", NS) is not None else "("
        end = _mval(pr, "endChr", ")") if pr is not None and pr.find("m:endChr", NS) is not None else ")"
        sep = _mval(pr, "sepChr", ",") if pr is not None and pr.find("m:sepChr", NS) is not None else ","
        parts = [_kids(e) for e in el.findall("m:e", NS)]

        def d(ch: str, right: bool) -> str:
            if ch == "":
                return "."
            return {"{": r"\{", "}": r"\}", "⟨": r"\langle", "⟩": r"\rangle", "‖": r"\|", "⌊": r"\lfloor",
                    "⌋": r"\rfloor", "⌈": r"\lceil", "⌉": r"\rceil"}.get(ch, ch)

        return r"\left%s %s \right%s" % (d(beg, False), (" " + sep + " ").join(parts), d(end, True))
    if name == "func":
        fname = _kids(el.find("m:fName", NS)).strip()
        body = _kids(el.find("m:e", NS))
        m = re.fullmatch(r"\\mathrm\{([A-Za-z]+)\}|([A-Za-z]+)", fname)
        if m:
            plain = m.group(1) or m.group(2)
            macro = ("\\" + plain) if plain in _FUNCS else (r"\operatorname{%s}" % plain)
        else:
            macro = fname
        return macro + " " + body
    if name == "limLow":
        base = _kids(el.find("m:e", NS)).strip()
        plain = re.sub(r"\\mathrm\{([A-Za-z]+)\}", r"\1", base)
        if plain in _FUNCS:
            base = "\\" + plain
        elif not base.startswith("\\"):
            base = "{%s}" % base
        return "%s_{%s}" % (base, _kids(el.find("m:lim", NS)))
    if name == "limUpp":
        return "{%s}^{%s}" % (_kids(el.find("m:e", NS)), _kids(el.find("m:lim", NS)))
    if name == "acc":
        pr = el.find("m:accPr", NS)
        ch = _mval(pr, "chr", "̂") if pr is not None and pr.find("m:chr", NS) is not None else "̂"
        return "\\%s{%s}" % (_ACCENTS.get(ch, "hat"), _kids(el.find("m:e", NS)))
    if name == "bar":
        pos = _mval(el.find("m:barPr", NS), "pos", "top")
        return ("\\underline{%s}" if pos == "bot" else "\\overline{%s}") % _kids(el.find("m:e", NS))
    if name == "m":
        rows = []
        for mr in el.findall("m:mr", NS):
            rows.append(" & ".join(_kids(e) for e in mr.findall("m:e", NS)))
        return r"\begin{matrix} " + r" \\ ".join(rows) + r" \end{matrix}"
    if name == "eqArr":
        return r"\begin{aligned} " + r" \\ ".join(_kids(e) for e in el.findall("m:e", NS)) + r" \end{aligned}"
    if name in ("t",):
        return _sym(el.text or "")
    if name.endswith("Pr") or name == "ctrlPr":
        return ""
    return _kids(el)


# --------------------------------------------------------------------------
# DrawingML : texte de formes (utilisé par DOCX zones de texte, PPTX)
# --------------------------------------------------------------------------

def dml_para_text(p: ET.Element) -> str:
    """Texte d'un <a:p> : runs, sauts de ligne, champs."""
    out: List[str] = []
    for c in p:
        n = local(c.tag)
        if n in ("r", "fld"):
            t = c.find("a:t", NS)
            if t is not None and t.text:
                out.append(t.text)
        elif n == "br":
            out.append("\n")
    return "".join(out)
