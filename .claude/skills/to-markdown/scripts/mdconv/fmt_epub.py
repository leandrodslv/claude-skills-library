"""EPUB → Markdown : chapitres dans l'ordre de lecture (spine), images extraites, métadonnées, table des matières."""
from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .fmt_html import decode_html, html_to_markdown
from .util import SafeZip, clean_text, esc_inline, local

DC = "http://purl.org/dc/elements/1.1/"


def _text(el: Optional[ET.Element]) -> str:
    return clean_text("".join(el.itertext())).strip() if el is not None else ""


@engine("epub", name="native", prio=10)
def epub_native(path, ctx: Ctx) -> Result:
    with SafeZip(path) as zf:
        container = zf.xml("META-INF/container.xml")
        opf_path = ""
        if container is not None:
            rf = next((e for e in container.iter() if local(e.tag) == "rootfile"), None)
            opf_path = rf.get("full-path", "") if rf is not None else ""
        if not opf_path:
            opf_path = next((n for n in zf.names() if n.lower().endswith(".opf")), "")
        opf = zf.xml(opf_path) if opf_path else None
        if opf is None:
            raise Unsupported("fichier OPF introuvable")
        base = posixpath.dirname(opf_path)
        meta: Dict[str, str] = {}
        for el in opf.iter():
            if el.tag.startswith("{%s}" % DC) and _text(el):
                meta.setdefault(local(el.tag), _text(el))
        manifest: Dict[str, Tuple[str, str, str]] = {}
        for it in opf.iter():
            if local(it.tag) == "item":
                manifest[it.get("id", "")] = (posixpath.normpath(posixpath.join(base, it.get("href", "").split("#")[0])),
                                             it.get("media-type", ""), it.get("properties", ""))
        spine = [ref.get("idref", "") for ref in opf.iter() if local(ref.tag) == "itemref"]
        toc = _toc_titles(zf, manifest, opf, base)
        parts: List[str] = []
        srcs: List[str] = []
        for idref in spine:
            item = manifest.get(idref)
            if not item or "html" not in item[1] and "xml" not in item[1]:
                continue
            href = item[0]
            data = zf.read_opt(href)
            if data is None:
                continue
            chapter_dir = posixpath.dirname(href)

            def loader(src: str, _dir: str = chapter_dir) -> Optional[bytes]:
                target = posixpath.normpath(posixpath.join(_dir, src.split("#")[0].split("?")[0].replace("%20", " ")))
                return zf.read_opt(target)

            md, title, _m, src = html_to_markdown(decode_html(data), ctx, stem="img", image_loader=loader)
            if not md.strip():
                continue
            if not re.match(r"\s*#{1,6}\s", md) and toc.get(href):
                md = f"## {esc_inline(toc[href])}\n\n{md}"
            parts.append(md.strip())
            srcs.append(src)
        if not parts:
            raise Unsupported("aucun chapitre lisible")
        title = meta.get("title", "")
        if title:   # un seul H1 (le titre du livre) : les chapitres s'y rangent en dessous
            parts = [_nest_headings(p) for p in parts]
        head = f"# {esc_inline(title)}" if title else ""
        byline = " · ".join(x for x in (meta.get("creator", ""), meta.get("date", "")[:10], meta.get("language", "")) if x)
        blurb = meta.get("description", "")
        top = "\n\n".join(x for x in (head, f"_{esc_inline(byline)}_" if byline else "",
                                       esc_inline(blurb[:600]) if blurb else "") if x)
        md = (top + "\n\n" if top else "") + "\n\n".join(parts)
        res = Result(markdown=md, fmt="epub", engine="native", title=title,
                     meta={"author": meta.get("creator", ""), "language": meta.get("language", "")})
        res.units, res.unit_name = len(parts), "chapitre"
        res.source_text = " ".join(srcs)
        res.stats["partial_source"] = True
        return res


_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_ATX = re.compile(r"^(#{1,6})(\s+\S.*)$")


def _nest_headings(md: str, top: int = 2) -> str:
    """Décale les titres d'un chapitre pour que le plus haut soit de niveau ``top`` (le titre du livre occupe le niveau 1)."""
    lines = md.split("\n")
    fence = ""
    levels: List[int] = []
    for ln in lines:
        m = _FENCE.match(ln)
        if m:
            fence = "" if fence and m.group(1)[0] == fence[0] else (fence or m.group(1))
            continue
        if not fence and (h := _ATX.match(ln)):
            levels.append(len(h.group(1)))
    if not levels or min(levels) >= top:
        return md
    shift = top - min(levels)
    out: List[str] = []
    fence = ""
    for ln in lines:
        m = _FENCE.match(ln)
        if m:
            fence = "" if fence and m.group(1)[0] == fence[0] else (fence or m.group(1))
        elif not fence and (h := _ATX.match(ln)):
            ln = "#" * min(6, len(h.group(1)) + shift) + h.group(2)
        out.append(ln)
    return "\n".join(out)


def _toc_titles(zf: SafeZip, manifest: Dict[str, Tuple[str, str, str]], opf: ET.Element, base: str) -> Dict[str, str]:
    """href de chapitre → titre, d'après nav.xhtml (EPUB 3) ou toc.ncx (EPUB 2)."""
    out: Dict[str, str] = {}
    nav = next((h for h, _m, props in manifest.values() if "nav" in props.split()), None)
    if nav:
        data = zf.read_opt(nav)
        if data:
            d = posixpath.dirname(nav)
            for m in re.finditer(rb'<a[^>]+href="([^"#]+)[^"]*"[^>]*>(.*?)</a>', data, re.S | re.I):
                href = posixpath.normpath(posixpath.join(d, m.group(1).decode("utf-8", "ignore")))
                label = re.sub(r"<[^>]+>", "", m.group(2).decode("utf-8", "ignore")).strip()
                if label:
                    out.setdefault(href, clean_text(label))
    ncx = next((h for h, mt, _p in manifest.values() if "ncx" in mt), None)
    if ncx and not out:
        root = zf.xml(ncx)
        if root is not None:
            d = posixpath.dirname(ncx)
            for np in root.iter():
                if local(np.tag) == "navPoint":
                    label = _text(next((e for e in np.iter() if local(e.tag) == "text"), None))
                    src = next((e.get("src", "") for e in np if local(e.tag) == "content"), "")
                    if label and src:
                        out.setdefault(posixpath.normpath(posixpath.join(d, src.split("#")[0])), label)
    return out
