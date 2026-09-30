"""PPTX → Markdown, en bibliothèque standard.

Une section « Slide N — titre » par diapositive, dans l'ordre réel du
diaporama (pas celui des fichiers), avec : texte hiérarchisé, tableaux,
graphiques (données), SmartArt, groupes de formes, connecteurs (→ diagramme
Mermaid), images, notes du présentateur et commentaires.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .inline import Fmt, Span, alt_clean, render_spans
from .ooxml import (NS, A, P, R, chart_markdown, chart_source_text, core_props, load_xml, parse_chart,
                    smartart_outline)
from .util import Rels, SafeZip, clean_text, esc_inline, local, md_table

_MONO = {"courier new", "courier", "consolas", "menlo", "monaco", "lucida console", "source code pro",
         "fira code", "fira mono", "dejavu sans mono", "cascadia code", "cascadia mono", "jetbrains mono"}
_GENERIC_NAME = re.compile(r"(?i)^(picture|image|graphic|figure|photo|content placeholder|espace réservé|"
                           r"rectangle|zone de texte|text box|object|objet|group|groupe|titre|title|"
                           r"placeholder|diagram|diagramme|table|tableau|chart|graphique|connecteur|connector|"
                           r"straight connector|elbow connector|freeform|forme libre|oval|ellipse|arrow)\s*\d*$")
_GENERIC_TITLES = re.compile(r"(?i)^(powerpoint presentation|présentation powerpoint|presentation\d*|présentation\d*|"
                             r"slide \d+|diapositive \d+|untitled|sans titre|document\d*)$")
_SKIP_PH = {"sldNum", "dt", "ftr", "hdr", "sldImg"}
_TITLE_PH = {"title", "ctrTitle"}


@dataclass
class Item:
    kind: str                       # text | table | chart | smartart | picture | media | title | note
    x: float = 0.0
    y: float = 0.0
    md: str = ""
    order: int = 0
    words: int = 0
    ph: str = ""
    sid: str = ""
    size: float = 0.0               # plus grande taille de police (repérage d'un titre implicite)
    alt: bool = False               # image dotée d'un texte alternatif
    asset: str = ""


@dataclass
class Connector:
    start: str
    end: str
    head: bool = False              # décoration au départ
    tail: bool = False              # flèche à l'arrivée


class PptxConverter:
    def __init__(self, zf: SafeZip, ctx: Ctx):
        self.zf, self.ctx, self.opts = zf, ctx, ctx.opts
        self.pres_part = "ppt/presentation.xml"
        self._geom_cache: Dict[str, Dict[Tuple[str, str], Tuple[float, float, float, float]]] = {}
        self.shape_stats = {"shapes": 0, "arrows": 0}
        self._bullets_cache: Dict[str, bool] = {}
        self.src_parts: List[str] = []
        self.slide_w = 12192000.0
        self.slide_h = 6858000.0
        self.vision_slides: List[int] = []

    # ------------------------------------------------------------------
    def run(self) -> Result:
        root = load_xml(self.zf, self.pres_part)
        if root is None:
            raise Unsupported("presentation.xml illisible")
        rels = Rels(self.zf, self.pres_part)
        sz = root.find("p:sldSz", NS)
        if sz is not None:
            self.slide_w = float(sz.get("cx", self.slide_w))
            self.slide_h = float(sz.get("cy", self.slide_h))
        slide_ids = [(s.get(R("id")), s.get("id")) for s in root.findall("p:sldIdLst/p:sldId", NS)]
        sections: Dict[str, str] = {}
        for sec in root.iter("{http://schemas.microsoft.com/office/powerpoint/2010/main}section"):
            for sid in sec.iter("{http://schemas.microsoft.com/office/powerpoint/2010/main}sldId"):
                sections[sid.get("id", "")] = sec.get("name", "")
        props = core_props(self.zf)
        blocks: List[str] = []
        titles: List[str] = []
        n_slides = len(slide_ids)
        current_section = None
        rendered = 0
        hidden = 0
        for idx, (rid, sid) in enumerate(slide_ids, 1):
            part = rels.target(rid)
            if not part or not self.zf.has(part):
                continue
            sroot = load_xml(self.zf, part)
            if sroot is None:
                continue
            is_hidden = sroot.get("show") in ("0", "false")
            if is_hidden:
                hidden += 1
                if not self.opts.hidden:
                    continue
            sec_name = sections.get(sid or "", None)
            if sections and sec_name is not None and sec_name != current_section and sec_name:
                blocks.append(f"## {esc_inline(sec_name)}")
                current_section = sec_name
            title, md = self.slide(idx, part, sroot, is_hidden, level=3 if sections else 2)
            titles.append(title)
            blocks.append(md)
            rendered += 1
        deck_title = props.get("title", "").strip()
        md = "\n\n".join(b for b in blocks if b.strip())
        if deck_title and not _GENERIC_TITLES.match(deck_title):
            md = f"# {esc_inline(deck_title)}\n\n{md}"
        else:
            # pas de vrai titre dans les métadonnées : le titre de la 1re diapositive sert de titre de document
            # (métadonnées/front matter seulement — il figure déjà dans « ## Slide 1 — … », inutile de le répéter en H1)
            deck_title = next((t for t in titles if t), "")
        res = Result(markdown=md, fmt="pptx", engine="native", title=deck_title, meta=dict(props))
        res.units, res.unit_name = (n_slides if self.opts.hidden else n_slides - hidden), "slide"
        res.units_found = len(re.findall(r"(?m)^#{2,3} Slide \d+", md))
        res.source_text = "\n".join(self.src_parts)
        if hidden:
            self.ctx.warn(f"{hidden} diapositive(s) masquée(s)" + (" (incluses, signalées)" if self.opts.hidden else " (ignorées)"))
        if self.ctx.skipped_images:
            self.ctx.warn(f"{self.ctx.skipped_images} image(s) décorative(s) ignorée(s) (trop petites)")
        return res

    # ------------------------------------------------------------------
    def slide(self, num: int, part: str, root: ET.Element, hidden: bool, level: int) -> Tuple[str, str]:
        rels = Rels(self.zf, part)
        layout = next((t for _r, t in rels.of_type("slideLayout")), None)
        items: List[Item] = []
        connectors: List[Connector] = []
        shapes_text: Dict[str, str] = {}
        tree = root.find("p:cSld/p:spTree", NS)
        counter = [0]
        self.shape_stats = {"shapes": 0, "arrows": 0}
        if tree is not None:
            self.walk(tree, rels, layout, (0.0, 0.0, 1.0, 1.0), items, connectors, shapes_text, counter, num)
        # titre : placeholder, sinon plus gros texte proche du haut de la diapositive
        title_items = [i for i in items if i.kind == "title"]
        title = ""
        if title_items:
            title = re.sub(r"\s+", " ", title_items[0].md).strip()
            extra = [i for i in title_items[1:]]
            for e in extra:
                e.kind = "text"
        else:
            cand = [i for i in items if i.kind == "text" and i.size and i.y < self.slide_h * 0.28 and i.words <= 20
                    and "\n" not in i.md.strip()]
            if cand:
                best = max(cand, key=lambda i: (i.size, -i.y))
                others = [i.size for i in items if i.kind == "text" and i is not best and i.size]
                if not others or best.size >= max(others) + 2:
                    title = re.sub(r"[*_`\\]", "", best.md).strip().lstrip("#").strip()
                    best.kind = "used"
        head = f"{'#' * level} Slide {num}" + (f" — {esc_inline(title)}" if title else "")
        if hidden:
            head += " *(masquée)*"
        body_items = [i for i in items if i.kind not in ("title", "used")]
        body_items = self.reading_order(body_items)
        parts = [head]
        parts.extend(i.md for i in body_items if i.md.strip())
        graph = self.diagram(connectors, shapes_text)
        if graph:
            parts.append(graph)
        elif self.shape_stats["shapes"] >= 8 and self.shape_stats["arrows"] >= 2:
            self.ctx.warn(f"diapositive {num} : schéma de {self.shape_stats['shapes']} formes dont {self.shape_stats['arrows']} flèches/lignes "
                          "sans connecteurs — les liens ne sont pas restitués (--render pour regarder la diapositive)")
        # notes et commentaires
        if self.opts.notes:
            notes = self.notes(rels)
            if notes:
                parts.append("**Notes du présentateur :**\n\n" + "\n".join(("> " + ln) if ln.strip() else ">" for ln in notes.split("\n")))
        if self.opts.comments:
            cm = self.comments(rels, part)
            if cm:
                parts.append("**Commentaires :**\n\n" + "\n".join(f"- {c}" for c in cm))
        # lecture visuelle : diapositive quasi sans texte mais pleine d'images
        text_words = sum(i.words for i in body_items if i.kind in ("text", "table", "chart", "smartart"))
        pics = [i for i in body_items if i.kind == "picture"]
        if pics and text_words + (len(title.split()) if title else 0) < 8 and not any(i.alt for i in pics):
            self.ctx.warn(f"diapositive {num} : contenu surtout visuel (images sans texte alternatif)")
            for p in pics[:3]:
                if p.asset:
                    self.ctx.need_vision("slide", p.asset, f"diapositive {num} : image sans texte ni description — à décrire")
            parts.append(f"> **[À COMPLÉTER : description visuelle]** diapositive {num} — image(s) sans texte extractible.")
        return title, "\n\n".join(parts)

    # -- parcours de l'arbre de formes ---------------------------------
    def walk(self, tree: ET.Element, rels: Rels, layout: Optional[str], tf: Tuple[float, float, float, float],
             items: List[Item], connectors: List[Connector], shapes_text: Dict[str, str], counter: List[int],
             num: int) -> None:
        for el in tree:
            tag = el.tag
            if tag == P("sp"):
                self.shape(el, rels, layout, tf, items, shapes_text, counter, num)
            elif tag == P("pic"):
                self.picture(el, rels, tf, items, counter, num)
            elif tag == P("graphicFrame"):
                self.frame(el, rels, tf, items, counter, num)
            elif tag == P("grpSp"):
                sp = el.find("p:grpSpPr/a:xfrm", NS)
                ntf = self.compose(tf, sp)
                self.walk(el, rels, layout, ntf, items, connectors, shapes_text, counter, num)
            elif tag == P("cxnSp"):
                c = self.connector(el)
                if c:
                    connectors.append(c)
            elif tag == "{%s}AlternateContent" % NS["mc"]:
                choice = el.find("mc:Choice", NS)
                pick = choice if choice is not None else el.find("mc:Fallback", NS)
                if pick is not None:
                    self.walk(pick, rels, layout, tf, items, connectors, shapes_text, counter, num)

    @staticmethod
    def compose(tf, xfrm: Optional[ET.Element]):
        """Transformation groupe → diapositive, composée avec celle du parent."""
        if xfrm is None:
            return tf
        off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
        choff, chext = xfrm.find("a:chOff", NS), xfrm.find("a:chExt", NS)
        if off is None or ext is None or choff is None or chext is None:
            return tf
        ox, oy, sx, sy = tf
        cw, ch = float(chext.get("cx", 1)) or 1.0, float(chext.get("cy", 1)) or 1.0
        gx, gy = float(off.get("x", 0)), float(off.get("y", 0))
        gw, gh = float(ext.get("cx", 1)), float(ext.get("cy", 1))
        nsx, nsy = (gw / cw), (gh / ch)
        cox, coy = float(choff.get("x", 0)), float(choff.get("y", 0))
        # point enfant p → parent: gx + (p - cox) * nsx ; puis parent → slide via tf
        return (ox + (gx - cox * nsx) * sx, oy + (gy - coy * nsy) * sy, sx * nsx, sy * nsy)

    def geometry(self, el: ET.Element, layout: Optional[str], ph_type: str, ph_idx: str,
                 tf: Tuple[float, float, float, float]) -> Tuple[float, float]:
        xfrm = el.find("p:spPr/a:xfrm", NS)
        if xfrm is None:
            xfrm = el.find("p:xfrm", NS)  # graphicFrame
        x = y = None
        if xfrm is not None:
            off = xfrm.find("a:off", NS)
            if off is not None:
                x, y = float(off.get("x", 0)), float(off.get("y", 0))
        if x is None and layout:
            geo = self._layout_geom(layout)
            g = geo.get((ph_type, ph_idx)) or geo.get(("", ph_idx)) or geo.get((ph_type, ""))
            if g:
                x, y = g[0], g[1]
        if x is None:
            return -1.0, -1.0
        ox, oy, sx, sy = tf
        return ox + x * sx, oy + y * sy

    def _layout_geom(self, layout: str) -> Dict[Tuple[str, str], Tuple[float, float, float, float]]:
        if layout in self._geom_cache:
            return self._geom_cache[layout]
        geo: Dict[Tuple[str, str], Tuple[float, float, float, float]] = {}
        self._geom_cache[layout] = geo
        chain = [layout]
        lrels = Rels(self.zf, layout)
        master = next((t for _r, t in lrels.of_type("slideMaster")), None)
        if master:
            chain.append(master)
        for part in reversed(chain):  # le layout écrase le master
            root = load_xml(self.zf, part)
            if root is None:
                continue
            for sp in root.iter(P("sp")):
                ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
                xf = sp.find("p:spPr/a:xfrm", NS)
                if ph is None or xf is None:
                    continue
                off, ext = xf.find("a:off", NS), xf.find("a:ext", NS)
                if off is None or ext is None:
                    continue
                g = (float(off.get("x", 0)), float(off.get("y", 0)), float(ext.get("cx", 0)), float(ext.get("cy", 0)))
                t, i = ph.get("type", ""), ph.get("idx", "")
                geo[(t, i)] = g
                geo.setdefault((t, ""), g)
                geo.setdefault(("", i), g)
        return geo

    def bullets_by_default(self, layout: Optional[str], ph_type: str, ph_idx: str) -> bool:
        """Le placeholder de corps affiche-t-il des puces par héritage (layout/master) ?"""
        key = f"{layout}|{ph_type}|{ph_idx}"
        if key in self._bullets_cache:
            return self._bullets_cache[key]
        result = True
        if layout:
            lroot = load_xml(self.zf, layout)
            if lroot is not None:
                for sp in lroot.iter(P("sp")):
                    ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
                    if ph is None or (ph.get("idx", "") != ph_idx and ph.get("type", "") != ph_type):
                        continue
                    lvl1 = sp.find("p:txBody/a:lstStyle/a:lvl1pPr", NS)
                    if lvl1 is not None:
                        if lvl1.find("a:buNone", NS) is not None:
                            result = False
                        elif lvl1.find("a:buChar", NS) is not None or lvl1.find("a:buAutoNum", NS) is not None:
                            result = True
                        else:
                            result = self._master_bullets(layout)
                        self._bullets_cache[key] = result
                        return result
            result = self._master_bullets(layout)
        self._bullets_cache[key] = result
        return result

    def _master_bullets(self, layout: str) -> bool:
        lrels = Rels(self.zf, layout)
        master = next((t for _r, t in lrels.of_type("slideMaster")), None)
        if master:
            mroot = load_xml(self.zf, master)
            if mroot is not None:
                lvl1 = mroot.find("p:txStyles/p:bodyStyle/a:lvl1pPr", NS)
                if lvl1 is not None and lvl1.find("a:buNone", NS) is not None:
                    return False
        return True

    # -- formes de texte -------------------------------------------------
    def shape(self, sp: ET.Element, rels: Rels, layout: Optional[str], tf, items: List[Item],
              shapes_text: Dict[str, str], counter: List[int], num: int) -> None:
        nv = sp.find("p:nvSpPr", NS)
        cnv = nv.find("p:cNvPr", NS) if nv is not None else None
        sid = cnv.get("id", "") if cnv is not None else ""
        ph = nv.find("p:nvPr/p:ph", NS) if nv is not None else None
        ph_type = ph.get("type", "") if ph is not None else ""
        ph_idx = ph.get("idx", "") if ph is not None else ""
        if ph_type in _SKIP_PH:
            return
        tx = sp.find("p:txBody", NS)
        x, y = self.geometry(sp, layout, ph_type, ph_idx, tf)
        counter[0] += 1
        if ph is None:                                   # statistiques « schéma dessiné » de la diapositive
            geom = sp.find("p:spPr/a:prstGeom", NS)
            prst = geom.get("prst", "") if geom is not None else ("custom" if sp.find("p:spPr/a:custGeom", NS) is not None else "")
            self.shape_stats["shapes"] += 1
            if "rrow" in prst or "onnector" in prst or prst in ("line", "custom") and tx is None:
                self.shape_stats["arrows"] += 1
        if tx is None:
            return
        paras = tx.findall("a:p", NS)
        plain = "\n".join("".join(t.text or "" for t in p.iter(A("t"))) for p in paras).strip()
        # texte indépendant pour le contrôle de rappel (les champs de pied de page sont exclus plus haut)
        if plain:
            self.src_parts.append(plain)
        else:
            return
        shapes_text[sid] = re.sub(r"\s+", " ", plain)
        if ph_type in _TITLE_PH:
            title = " ".join(clean_text("".join(t.text or "" for t in p.iter(A("t")))).strip() for p in paras).strip()
            items.append(Item("title", x, y, title, counter[0], len(title.split()), ph_type, sid))
            return
        is_body_ph = ph is not None and ph_type not in ("subTitle",)
        default_bullets = self.bullets_by_default(layout, ph_type, ph_idx) if is_body_ph else False
        md, size = self.paragraphs(paras, rels, default_bullets, in_placeholder=ph is not None)
        if md.strip():
            items.append(Item("text", x, y, md, counter[0], len(plain.split()), ph_type, sid, size))

    def paragraphs(self, paras: List[ET.Element], rels: Rels, default_bullets: bool, in_placeholder: bool) -> Tuple[str, float]:
        lines: List[str] = []
        nums: Dict[int, int] = {}
        size_max = 0.0
        prev_list = False
        for p in paras:
            spans, sz = self.spans(p, rels)
            size_max = max(size_max, sz)
            if not any(s.text.strip() for s in spans if s.kind == "t"):
                if prev_list is False and lines and lines[-1] != "":
                    lines.append("")
                continue
            ppr = p.find("a:pPr", NS)
            lvl = int(ppr.get("lvl", 0)) if ppr is not None and ppr.get("lvl", "").isdigit() else 0
            bullet = default_bullets
            auto = None
            if ppr is not None:
                if ppr.find("a:buNone", NS) is not None:
                    bullet = False
                elif ppr.find("a:buChar", NS) is not None:
                    bullet = True
                else:
                    an = ppr.find("a:buAutoNum", NS)
                    if an is not None:
                        bullet, auto = True, an
            if bullet:
                text = render_spans(spans, inline_only=True, escape_start=False)
                if auto is not None:
                    n = nums.get(lvl)
                    n = int(auto.get("startAt", 1)) if n is None else n + 1
                    nums[lvl] = n
                    for k in [k for k in nums if k > lvl]:
                        del nums[k]
                    marker = f"{n}."
                else:
                    marker = "-"
                    for k in [k for k in nums if k >= lvl]:
                        del nums[k]
                lines.append("  " * lvl + f"{marker} {text}")
                prev_list = True
            else:
                text = render_spans(spans)
                if prev_list and lines:
                    lines.append("")
                if lines and not prev_list and lines[-1] != "":
                    lines.append("")
                lines.append(text)
                prev_list = False
                nums.clear()
        return "\n".join(lines).strip("\n"), size_max

    def spans(self, p: ET.Element, rels: Rels) -> Tuple[List[Span], float]:
        out: List[Span] = []
        size = 0.0
        for c in p:
            n = local(c.tag)
            if n in ("r", "fld"):
                t = c.find("a:t", NS)
                if t is None or t.text is None:
                    continue
                if n == "fld" and c.get("type", "").startswith(("slidenum", "datetime")):
                    continue
                f = Fmt()
                rpr = c.find("a:rPr", NS)
                sz = 0.0
                if rpr is not None:
                    f.bold = rpr.get("b") in ("1", "true")
                    f.italic = rpr.get("i") in ("1", "true")
                    f.strike = (rpr.get("strike") or "noStrike") != "noStrike"
                    base = rpr.get("baseline")
                    if base and base.lstrip("-").isdigit():
                        f.sup, f.sub = int(base) > 0, int(base) < 0
                    if rpr.get("sz", "").isdigit():
                        sz = int(rpr.get("sz")) / 100.0
                    lat = rpr.find("a:latin", NS)
                    if lat is not None and lat.get("typeface", "").lower() in _MONO:
                        f.code = True
                    h = rpr.find("a:hlinkClick", NS)
                    if h is not None and h.get(R("id")) and rels.is_external(h.get(R("id"))):
                        f.link = rels.target(h.get(R("id")))
                size = max(size, sz)
                out.append(Span("t", t.text, f, size=sz))
            elif n == "br":
                out.append(Span("br"))
        return out, size

    # -- images ----------------------------------------------------------
    def picture(self, pic: ET.Element, rels: Rels, tf, items: List[Item], counter: List[int], num: int) -> None:
        cnv = pic.find("p:nvPicPr/p:cNvPr", NS)
        blip = pic.find("p:blipFill/a:blip", NS)
        alt = ""
        if cnv is not None:
            alt = cnv.get("descr") or cnv.get("title") or ""
            if not alt and not _GENERIC_NAME.match(cnv.get("name", "")) and not re.search(r"\.(png|jpe?g|gif|svg|emf)$", cnv.get("name", ""), re.I):
                alt = cnv.get("name", "")
        x, y = self.geometry(pic, None, "", "", tf)
        counter[0] += 1
        for tag in ("videoFile", "audioFile", "wavAudioFile", "quickTimeFile"):
            m = pic.find(f".//a:{tag}", NS)
            if m is not None:
                items.append(Item("media", x, y, f"*[média : {esc_inline(alt or m.get(R('link'), tag))}]*", counter[0]))
                return
        if blip is None:
            return
        rid = blip.get(R("embed"))
        alt = alt_clean(alt)
        tgt = rels.target(rid) if rid else None
        data = self.zf.read_opt(tgt) if tgt else None
        if alt:
            self.src_parts.append(alt)
        if data is None:
            return
        ext = tgt.rsplit(".", 1)[-1] if tgt and "." in tgt else ""
        link = self.ctx.add_asset(data, ext, stem=f"slide{num:02d}-img", alt=alt)
        if link is None:
            if alt and self.opts.images == "skip":
                items.append(Item("picture", x, y, f"*[image : {alt}]*", counter[0], len(alt.split()), alt=True))
            return
        if ext.lower() in ("emf", "wmf"):
            self.ctx.warn(f"image {ext.upper()} non affichable telle quelle ({link})")
        items.append(Item("picture", x, y, f"![{alt}]({link})", counter[0], 0, alt=bool(alt), asset=link))

    # -- cadres graphiques : tableaux, graphiques, SmartArt ---------------
    def frame(self, gf: ET.Element, rels: Rels, tf, items: List[Item], counter: List[int], num: int) -> None:
        x, y = self.geometry(gf, None, "", "", tf)
        counter[0] += 1
        gd = gf.find("a:graphic/a:graphicData", NS)
        if gd is None:
            return
        tbl = gd.find("a:tbl", NS)
        if tbl is not None:
            md = self.table(tbl, rels)
            if md:
                words = len(re.sub(r"[|\-]", " ", md).split())
                items.append(Item("table", x, y, md, counter[0], words))
            return
        ch = gd.find("c:chart", NS)
        if ch is not None:
            tgt = rels.target(ch.get(R("id")))
            croot = load_xml(self.zf, tgt) if tgt else None
            if croot is not None:
                info = parse_chart(croot)
                self.src_parts.append(chart_source_text(info))
                md = chart_markdown(info, self.opts.table_rows)
                items.append(Item("chart", x, y, md, counter[0], len(md.split())))
            return
        rel = gd.find("dgm:relIds", NS)
        if rel is not None:
            tgt = rels.target(rel.get(R("dm")))
            if tgt:
                lines = smartart_outline(self.zf, tgt)
                if lines:
                    self.src_parts.append(" ".join(re.sub(r"^\s*- ", "", ln) for ln in lines))
                    items.append(Item("smartart", x, y, "\n".join(lines), counter[0], len(" ".join(lines).split())))
            return
        # objet OLE / autre : image de repli éventuelle
        pic = gd.find(".//p:pic", NS)
        if pic is not None:
            self.picture(pic, rels, tf, items, counter, num)

    def table(self, tbl: ET.Element, rels: Rels) -> str:
        grid: List[List[str]] = []
        vfill: Dict[int, str] = {}
        for tr in tbl.findall("a:tr", NS):
            row: List[str] = []
            col = 0
            for tc in tr.findall("a:tc", NS):
                if tc.get("hMerge") in ("1", "true"):
                    row.append("")
                    col += 1
                    continue
                paras = tc.findall("a:txBody/a:p", NS)
                cell_parts = []
                for p in paras:
                    spans, _sz = self.spans(p, rels)
                    t = render_spans(spans, inline_only=True, escape_start=False)
                    if t.strip():
                        cell_parts.append(t)
                        self.src_parts.append("".join(s.text for s in spans if s.kind == "t"))
                text = "<br>".join(cell_parts)
                if tc.get("vMerge") in ("1", "true"):
                    text = vfill.get(col, "")
                elif int(tc.get("rowSpan", 1) or 1) > 1:
                    vfill[col] = text
                else:
                    vfill.pop(col, None)
                row.append(text)
                span = int(tc.get("gridSpan", 1) or 1)
                row.extend([""] * (span - 1))
                col += span
            grid.append(row)
        if not grid:
            return ""
        cap = self.opts.table_rows
        if cap and len(grid) - 1 > cap:
            extra = len(grid) - 1 - cap
            width = max(len(r) for r in grid)
            grid = grid[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (width - 1)]
        if len(grid) == 1 and len(grid[0]) == 1:
            return grid[0][0]
        return md_table(grid)

    # -- connecteurs → diagramme -----------------------------------------
    def connector(self, cx: ET.Element) -> Optional[Connector]:
        st = cx.find("p:nvCxnSpPr/p:cNvCxnSpPr/a:stCxn", NS)
        en = cx.find("p:nvCxnSpPr/p:cNvCxnSpPr/a:endCxn", NS)
        if st is None or en is None:
            return None
        ln = cx.find("p:spPr/a:ln", NS)
        head = tail = False
        if ln is not None:
            h, t = ln.find("a:headEnd", NS), ln.find("a:tailEnd", NS)
            head = h is not None and h.get("type", "none") != "none"
            tail = t is not None and t.get("type", "none") != "none"
        return Connector(st.get("id", ""), en.get("id", ""), head, tail)

    def diagram(self, connectors: List[Connector], texts: Dict[str, str]) -> str:
        edges = [c for c in connectors if c.start in texts and c.end in texts and c.start != c.end]
        if len(edges) < 2:
            return ""
        ids: Dict[str, str] = {}

        def node(sid: str) -> str:
            if sid not in ids:
                ids[sid] = f"N{len(ids) + 1}"
            label = texts[sid].replace('"', "'")
            label = label if len(label) <= 80 else label[:77] + "…"
            return f'{ids[sid]}["{label}"]'

        lines = ["flowchart LR"]
        for c in edges:
            arrow = "<-->" if (c.head and c.tail) else ("<--" if c.head else ("-->" if c.tail else "---"))
            lines.append(f"    {node(c.start)} {arrow} {node(c.end)}")
        return "**Diagramme (connecteurs de la diapositive) :**\n\n```mermaid\n" + "\n".join(lines) + "\n```"

    # -- notes et commentaires ------------------------------------------
    def notes(self, rels: Rels) -> str:
        tgt = next((t for _r, t in rels.of_type("notesSlide")), None)
        root = load_xml(self.zf, tgt) if tgt else None
        if root is None:
            return ""
        nrels = Rels(self.zf, tgt)
        out: List[str] = []
        for sp in root.iter(P("sp")):
            ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
            # tout le texte de la page de notes, sauf la vignette, le numéro, l'en-tête, le pied et la date
            if ph is not None and ph.get("type") in ("sldImg", "sldNum", "hdr", "ftr", "dt"):
                continue
            for p in sp.findall("p:txBody/a:p", NS):
                spans, _sz = self.spans(p, nrels)
                t = render_spans(spans, escape_start=False)
                if t.strip():
                    out.append(t)
                    self.src_parts.append("".join(s.text for s in spans if s.kind == "t"))
        return "\n\n".join(out)

    def comments(self, rels: Rels, part: str) -> List[str]:
        out: List[str] = []
        authors: Dict[str, str] = {}
        aroot = load_xml(self.zf, "ppt/commentAuthors.xml")
        if aroot is not None:
            for a in aroot:
                authors[a.get("id", "")] = a.get("name", "")
        for _rid, tgt in rels.of_type("comments"):
            root = load_xml(self.zf, tgt)
            if root is None:
                continue
            for cm in root.iter():
                if local(cm.tag) != "cm":
                    continue
                txt_el = next((c for c in cm if local(c.tag) == "text"), None)
                if txt_el is None:
                    txt_el = next((e for e in cm.iter() if local(e.tag) in ("t",)), None)
                    txt = "".join((e.text or "") for e in cm.iter() if local(e.tag) == "t")
                else:
                    txt = txt_el.text or ""
                who = authors.get(cm.get("authorId", ""), "") or cm.get("authorId", "")
                if txt.strip():
                    out.append(f"**{esc_inline(who)}** : {esc_inline(clean_text(txt).strip())}" if who else esc_inline(clean_text(txt).strip()))
                    self.src_parts.append(txt)
        return out

    # -- ordre de lecture --------------------------------------------------
    def reading_order(self, items: List[Item]) -> List[Item]:
        if not items:
            return items
        tol = self.slide_h / 24.0
        placed = [i for i in items if i.y >= 0 and i.x >= 0]
        unplaced = [i for i in items if not (i.y >= 0 and i.x >= 0)]
        if len(placed) < len(items) // 2:
            return sorted(items, key=lambda i: i.order)
        placed.sort(key=lambda i: (round(i.y / tol), i.x, i.order))
        # les éléments sans position gardent leur ordre d'apparition, avant les éléments positionnés
        return sorted(unplaced, key=lambda i: i.order) + placed


@engine("pptx", name="native", prio=10)
def pptx_native(path, ctx: Ctx) -> Result:
    with SafeZip(path) as zf:
        if not zf.has("ppt/presentation.xml"):
            raise Unsupported("ppt/presentation.xml introuvable")
        res = PptxConverter(zf, ctx).run()
        if any(n.lower().endswith("vbaproject.bin") for n in zf.names()):
            ctx.warn("la présentation contient des macros VBA (ignorées, jamais exécutées)")
        return res
