"""Schéma SVG dessiné « à la main » → graphe : les liens sont déduits de la géométrie.

Les SVG produits par draw.io, Graphviz, Mermaid ou Excalidraw portent leur structure ; ceux d'Inkscape,
d'Illustrator, de Figma, de PowerPoint ou d'un script maison n'ont que des formes, des traits et du texte.
Ici on reconstruit le diagramme comme le ferait l'œil :

* un **nœud** est une forme fermée (rectangle, ellipse, losange, chemin fermé…) qui contient du texte ;
* un **lien** est un trait (ligne, polyligne, chemin ouvert) dont chaque extrémité touche un nœud ;
* le **sens** vient d'un marqueur de flèche (`marker-start/end`) ou d'une petite pointe triangulaire dessinée à côté ;
* une **étiquette de lien** est un texte court posé au voisinage d'un trait ;
* un **cadre** (couloir, groupe, zone) est une forme qui en contient plusieurs autres : sous-graphe nommé par son texte.

Rien n'est inventé : un trait dont une extrémité ne touche aucune forme n'est pas relié, et si trop de traits
restent dans ce cas le graphe est abandonné (le texte seul est restitué et le schéma signalé à lire visuellement).
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from .fmt_diagram import Graph
from .util import local

Point = Tuple[float, float]
_SKIP = {"defs", "style", "script", "metadata", "namedview", "clipPath", "mask", "symbol", "pattern", "filter",
         "linearGradient", "radialGradient", "marker", "title", "desc", "font", "font-face", "glyph", "text", "image",
         "foreignObject"}
_NUM = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


class Shape:
    __slots__ = ("x0", "y0", "x1", "y1", "kind", "texts", "order")

    def __init__(self, x0: float, y0: float, x1: float, y1: float, kind: str, order: int):
        self.x0, self.y0, self.x1, self.y1, self.kind, self.order = x0, y0, x1, y1, kind, order
        self.texts: List["TextBox"] = []

    @property
    def area(self) -> float:
        return max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0)

    @property
    def center(self) -> Point:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    def dist(self, p: Point) -> float:
        dx = max(self.x0 - p[0], 0.0, p[0] - self.x1)
        dy = max(self.y0 - p[1], 0.0, p[1] - self.y1)
        return math.hypot(dx, dy)

    def contains(self, o: "Shape", tol: float = 2.0) -> bool:
        return self.x0 - tol <= o.x0 and self.y0 - tol <= o.y0 and self.x1 + tol >= o.x1 and self.y1 + tol >= o.y1 and self.area > o.area * 1.15


class Conn:
    __slots__ = ("pts", "start_head", "end_head", "src", "dst")

    def __init__(self, pts: List[Point], start_head: bool, end_head: bool):
        self.pts, self.start_head, self.end_head = pts, start_head, end_head
        self.src: Optional[object] = None
        self.dst: Optional[object] = None


class TextBox:
    __slots__ = ("text", "x0", "y0", "x1", "y1", "item")

    def __init__(self, item) -> None:
        self.item = item
        self.text = item.text
        size = item.size or 12.0
        lines = max(1, getattr(item, "lines", 1))
        w = max(len(line) for line in item.text.split("\n")) * 0.55 * size if lines == 1 else len(item.text) * 0.55 * size / lines
        h = lines * size * 1.2
        anchor = getattr(item, "anchor", "start")
        if anchor == "middle":
            x0 = item.x - w / 2
        elif anchor == "end":
            x0 = item.x - w
        else:
            x0 = item.x
        y0 = item.y - size * 0.9
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x0 + w, y0 + h

    @property
    def center(self) -> Point:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2


# --------------------------------------------------------------------------
# Lecture de la géométrie
# --------------------------------------------------------------------------

def _num(v: Optional[str], default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)", v)
    return float(m.group(1)) if m else default


def parse_path(d: str) -> Tuple[List[Point], List[Point], bool]:
    """Chemin SVG → (points d'ancrage du premier sous-chemin, tous les points y compris de contrôle, fermé ?)."""
    toks = _NUM.findall(d or "")
    anchors: List[Point] = []
    allpts: List[Point] = []
    closed = False
    i, cmd = 0, ""
    cx = cy = 0.0
    started = False

    def take(n: int) -> Optional[List[float]]:
        nonlocal i
        if i + n > len(toks) or any(t.isalpha() for t in toks[i:i + n]):
            return None
        v = [float(t) for t in toks[i:i + n]]
        i += n
        return v

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                closed = True       # un éventuel second sous-chemin n'est pas pris en compte
                break
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            v = take(2)
            if v is None:
                break
            if started:           # nouveau sous-chemin : on s'arrête au premier
                break
            cx, cy = (cx + v[0], cy + v[1]) if rel else (v[0], v[1])
            started = True
            anchors.append((cx, cy))
            allpts.append((cx, cy))
            cmd = "l" if rel else "L"
        elif c == "L" or c == "T":
            v = take(2)
            if v is None:
                break
            cx, cy = (cx + v[0], cy + v[1]) if rel else (v[0], v[1])
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        elif c == "H":
            v = take(1)
            if v is None:
                break
            cx = cx + v[0] if rel else v[0]
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        elif c == "V":
            v = take(1)
            if v is None:
                break
            cy = cy + v[0] if rel else v[0]
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        elif c == "C":
            v = take(6)
            if v is None:
                break
            for k in (0, 2):
                allpts.append((cx + v[k], cy + v[k + 1]) if rel else (v[k], v[k + 1]))
            cx, cy = (cx + v[4], cy + v[5]) if rel else (v[4], v[5])
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        elif c in "SQ":
            v = take(4)
            if v is None:
                break
            allpts.append((cx + v[0], cy + v[1]) if rel else (v[0], v[1]))
            cx, cy = (cx + v[2], cy + v[3]) if rel else (v[2], v[3])
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        elif c == "A":
            v = take(7)
            if v is None:
                break
            cx, cy = (cx + v[5], cy + v[6]) if rel else (v[5], v[6])
            anchors.append((cx, cy))
            allpts.append((cx, cy))
        else:
            i += 1
    return anchors, allpts, closed


def _css_rules(root: ET.Element) -> Dict[str, Dict[str, str]]:
    rules: Dict[str, Dict[str, str]] = {}
    for st in root.iter():
        if isinstance(st.tag, str) and local(st.tag) == "style" and st.text:
            for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", re.sub(r"/\*.*?\*/", "", st.text, flags=re.S)):
                props = {}
                for part in body.split(";"):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        props[k.strip().lower()] = v.strip()
                for s in sel.split(","):
                    s = s.strip()
                    if s.startswith(".") and re.fullmatch(r"\.[\w-]+", s):
                        rules.setdefault(s[1:], {}).update(props)
    return rules


class _Collector:
    def __init__(self, root: ET.Element, parse_transform, mul, apply, style, hidden) -> None:
        self.parse_transform, self.mul, self.apply, self.style, self.hidden = parse_transform, mul, apply, style, hidden
        self.css = _css_rules(root)
        self.shapes: List[Shape] = []
        self.conns: List[Conn] = []
        self.heads: List[Point] = []
        self.order = 0

    def props(self, el: ET.Element, inherited: Dict[str, str]) -> Dict[str, str]:
        p = dict(inherited)
        for cls in (el.get("class") or "").split():
            p.update(self.css.get(cls, {}))
        for k in ("fill", "stroke", "marker-start", "marker-end"):
            if el.get(k) is not None:
                p[k] = el.get(k)  # type: ignore[assignment]
        st = self.style(el)
        for k in ("fill", "stroke", "marker-start", "marker-end"):
            if k in st:
                p[k] = st[k]
        if "marker" in st:
            p.setdefault("marker-start", st["marker"])
            p.setdefault("marker-end", st["marker"])
        return p

    def walk(self, el: ET.Element, m, inherited: Dict[str, str], depth: int = 0) -> None:
        if depth > 120:
            return
        for ch in el:
            if not isinstance(ch.tag, str):
                continue
            name = local(ch.tag)
            if name in _SKIP or self.hidden(ch):
                continue
            cm = self.mul(m, self.parse_transform(ch.get("transform")))
            props = self.props(ch, inherited)
            if name in ("g", "svg", "a", "switch"):
                self.walk(ch, cm, props, depth + 1)
                continue
            self.element(ch, name, cm, props)

    def pts(self, m, raw: List[Point]) -> List[Point]:
        return [self.apply(m, x, y) for x, y in raw]

    def add_shape(self, pts: List[Point], kind: str) -> None:
        if not pts:
            return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        s = Shape(min(xs), min(ys), max(xs), max(ys), kind, self.order)
        self.order += 1
        self.shapes.append(s)

    def add_conn(self, pts: List[Point], props: Dict[str, str]) -> None:
        if len(pts) < 2 or math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < 3:
            return
        ms, me = props.get("marker-start", "none"), props.get("marker-end", "none")
        self.conns.append(Conn(pts, ms not in ("none", "", None), me not in ("none", "", None)))  # type: ignore[comparison-overlap]

    def element(self, el: ET.Element, name: str, m, props: Dict[str, str]) -> None:
        fill = (props.get("fill") or "black").strip().lower()
        stroke = (props.get("stroke") or "none").strip().lower()
        filled = fill not in ("none", "transparent")
        if name == "line":
            self.add_conn(self.pts(m, [(_num(el.get("x1")), _num(el.get("y1"))), (_num(el.get("x2")), _num(el.get("y2")))]), props)
        elif name == "polyline":
            raw = [float(v) for v in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", el.get("points", ""))]
            pts = self.pts(m, list(zip(raw[0::2], raw[1::2])))
            if filled and len(pts) >= 3 and pts[0] == pts[-1] and "marker" not in "".join(props.get(k, "") for k in ("marker-start", "marker-end")):
                self.add_shape(pts, "polygon")
            else:
                self.add_conn(pts, props)
        elif name == "rect":
            x, y, w, h = _num(el.get("x")), _num(el.get("y")), _num(el.get("width")), _num(el.get("height"))
            if w > 0 and h > 0 and (filled or stroke != "none"):
                self.add_shape(self.pts(m, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), "rect")
        elif name in ("circle", "ellipse"):
            cx, cy = _num(el.get("cx")), _num(el.get("cy"))
            rx = _num(el.get("r")) if name == "circle" else _num(el.get("rx"))
            ry = rx if name == "circle" else _num(el.get("ry"))
            if rx > 0 and ry > 0 and (filled or stroke != "none"):
                self.add_shape(self.pts(m, [(cx - rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry), (cx + rx, cy - ry)]), "ellipse")
        elif name == "polygon":
            raw = [float(v) for v in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", el.get("points", ""))]
            pts = self.pts(m, list(zip(raw[0::2], raw[1::2])))
            self._closed(pts, filled)
        elif name == "path":
            anchors, allpts, closed = parse_path(el.get("d", ""))
            if not anchors:
                return
            has_marker = any(props.get(k, "none") not in ("none", "") for k in ("marker-start", "marker-end"))
            if has_marker or (not closed and not filled):
                self.add_conn(self.pts(m, anchors), props)
            elif closed or filled:
                self._closed(self.pts(m, allpts), filled, anchors=self.pts(m, anchors))
            elif stroke != "none":
                self.add_conn(self.pts(m, anchors), props)

    def _closed(self, pts: List[Point], filled: bool, anchors: Optional[List[Point]] = None) -> None:
        if len(pts) < 3:
            return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        n_anchor = len(anchors) if anchors is not None else len(pts)
        if n_anchor <= 4 and w * h < 260 and filled:                        # pointe de flèche dessinée
            self.heads.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
            return
        if w < 4 or h < 4:
            return
        self.add_shape(pts, "polygon")


# --------------------------------------------------------------------------
# Inférence du graphe
# --------------------------------------------------------------------------

def _seg_dist(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _poly_dist(p: Point, pts: List[Point]) -> float:
    return min(_seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


def infer_graph(root: ET.Element, items: list, helpers: Tuple, canvas: Tuple[float, float]) -> Tuple[Optional[Graph], Dict[str, int]]:
    """Renvoie (graphe ou None, statistiques). `helpers` = (parse_transform, mul, apply, style, hidden) de fmt_svg."""
    col = _Collector(root, *helpers)
    col.walk(root, (1, 0, 0, 1, 0, 0), {})
    stats = {"shapes": 0, "connectors": len(col.conns), "attached": 0}
    W, H = canvas
    if W <= 0 or H <= 0:
        xs = [s.x1 for s in col.shapes] or [1.0]
        ys = [s.y1 for s in col.shapes] or [1.0]
        W, H = max(xs), max(ys)
    diag = math.hypot(W, H)
    tol = max(10.0, 0.025 * max(W, H))
    shapes = [s for s in col.shapes if not (s.area >= 0.8 * W * H)]          # fond de page
    # dédoublonnage (ombres, doubles contours)
    uniq: List[Shape] = []
    for s in sorted(shapes, key=lambda s: s.order):
        if not any(abs(s.x0 - u.x0) < 1.5 and abs(s.y0 - u.y0) < 1.5 and abs(s.x1 - u.x1) < 1.5 and abs(s.y1 - u.y1) < 1.5 for u in uniq):
            uniq.append(s)
    shapes = uniq
    boxes = [TextBox(i) for i in items]

    # texte → plus petite forme qui le contient
    free: List[TextBox] = []
    for tb in boxes:
        c = tb.center
        cands = [s for s in shapes if s.x0 - 2 <= c[0] <= s.x1 + 2 and s.y0 - 2 <= c[1] <= s.y1 + 2]
        if cands:
            min(cands, key=lambda s: s.area).texts.append(tb)
        else:
            free.append(tb)
    with_text = [s for s in shapes if s.texts]
    # cadres : une forme qui en contient au moins deux autres portant du texte
    def is_container(s: Shape) -> bool:
        inner = [o for o in with_text if o is not s and s.contains(o)]
        if len(inner) >= 2:
            return True
        return len(inner) == 1 and s.area >= 6 * inner[0].area and s.area >= 0.05 * W * H     # couloir à un seul élément

    containers = [s for s in shapes if is_container(s)]
    nodes = [s for s in with_text if s not in containers]
    stats["shapes"] = len(nodes)
    if len(nodes) < 2 or not col.conns:
        return None, stats

    # liens : chaque extrémité sur le nœud le plus proche (dans la tolérance)
    def attach(p: Point) -> Optional[object]:
        best, bd = None, 1e18
        for s in nodes:
            d = s.dist(p)
            if d <= tol and (d < bd - 0.5 or (abs(d - bd) <= 0.5 and best is not None and s.area < best.area)):  # type: ignore[attr-defined]
                best, bd = s, d
        return best

    def attach_text(p: Point) -> Optional[TextBox]:
        best, bd = None, 1e18
        for tb in free:
            dx = max(tb.x0 - p[0], 0.0, p[0] - tb.x1)
            dy = max(tb.y0 - p[1], 0.0, p[1] - tb.y1)
            d = math.hypot(dx, dy)
            if d <= tol and d < bd:
                best, bd = tb, d
        return best

    edges: List[Tuple[object, object, bool, bool, List[Point]]] = []
    for cn in col.conns:
        a, b = cn.pts[0], cn.pts[-1]
        src, dst = attach(a), attach(b)
        if src is None:
            t = attach_text(a)
            src = t
        if dst is None:
            t = attach_text(b)
            dst = t
        if src is None or dst is None or src is dst:
            continue
        sh, eh = cn.start_head, cn.end_head
        if not sh and not eh:                                                 # pointe dessinée près d'une extrémité
            ds = min((math.hypot(h[0] - a[0], h[1] - a[1]) for h in col.heads), default=1e9)
            de = min((math.hypot(h[0] - b[0], h[1] - b[1]) for h in col.heads), default=1e9)
            lim = max(14.0, tol)
            if de <= lim and de <= ds:
                eh = True
            elif ds <= lim:
                sh = True
            if de <= lim and ds <= lim:
                sh = eh = True
        if not sh and not eh:
            (sx, sy), (ex, ey) = _center(src), _center(dst)
            if (abs(ey - sy) > 2 * tol and ey < sy) or (abs(ey - sy) <= 2 * tol and ex < sx):    # du haut vers le bas, sinon de gauche à droite
                src, dst = dst, src
        edges.append((src, dst, sh, eh, cn.pts))
    stats["attached"] = len(edges)
    if not edges or len(edges) < 0.5 * len(col.conns):
        return None, stats

    # étiquettes de liens : textes libres courts, près d'un trait
    labels: Dict[int, List[TextBox]] = {}
    used_free = {id(x) for e in edges for x in e[:2] if isinstance(x, TextBox)}
    for tb in free:
        if id(tb) in used_free or len(tb.text) > 40:
            continue
        best, bd = -1, max(25.0, 0.04 * diag)
        probes = [tb.center, (tb.x0, (tb.y0 + tb.y1) / 2), (tb.x1, (tb.y0 + tb.y1) / 2)]
        for k, e in enumerate(edges):
            d = min(_poly_dist(q, e[4]) for q in probes)
            if d < bd:
                best, bd = k, d
        if best >= 0:
            labels.setdefault(best, []).append(tb)
            used_free.add(id(tb))

    # construction du graphe
    g = Graph()
    ids: Dict[int, str] = {}

    def label_of(s: Shape) -> str:
        ts = sorted(s.texts, key=lambda t: (round(t.y0 / 6), t.x0))
        return " ".join(t.text for t in ts)

    def node_id(x: object) -> str:
        if id(x) not in ids:
            ids[id(x)] = f"s{len(ids) + 1}"
            g.nodes[ids[id(x)]] = label_of(x) if isinstance(x, Shape) else x.text  # type: ignore[union-attr]
        return ids[id(x)]

    seen = set()
    for k, (src, dst, sh, eh, _pts) in enumerate(edges):
        lab = " ".join(t.text for t in sorted(labels.get(k, []), key=lambda t: (t.y0, t.x0)))
        s, d = node_id(src), node_id(dst)
        arrow = "<->" if sh and eh else ("->" if eh else ("<-" if sh else "--"))
        if arrow == "<-":
            s, d, arrow = d, s, "->"
        key = (s, d, lab, arrow)
        if key not in seen:
            seen.add(key)
            g.edges.append((s, d, lab, arrow))
    # nœuds isolés (sans lien) : conservés pour ne rien perdre, dans l'ordre de lecture
    for s in sorted(nodes, key=lambda s: (round(s.y0 / 10), s.x0)):
        if id(s) not in ids and s.texts:
            node_id(s)
    # cadres → sous-graphes (chaque nœud dans son plus petit cadre)
    for ci, c in enumerate(sorted(containers, key=lambda c: c.area)):
        members = [ids[id(s)] for s in nodes if id(s) in ids and c.contains(s)
                   and not any(o is not c and o.area < c.area and o.contains(s) for o in containers)]
        title = label_of(c)
        if members and title:
            g.groups[f"c{ci}"] = (title, members)
    # sens de lecture
    dx = sum(abs(_center(a)[0] - _center(b)[0]) for a, b, *_ in edges)
    dy = sum(abs(_center(a)[1] - _center(b)[1]) for a, b, *_ in edges)
    g.direction = "LR" if dx > dy * 1.2 else "TD"
    # ordre : lecture haut-gauche → bas-droite, pour des identifiants stables
    pos = {ids[id(s)]: (round(_center(s)[1] / 12), _center(s)[0]) for s in nodes if id(s) in ids}
    pos.update({ids[id(t)]: (round(t.center[1] / 12), t.center[0]) for t in free if id(t) in ids})
    incoming = {e[1] for e in g.edges}
    queue = sorted((n for n in g.nodes if n not in incoming), key=lambda n: pos.get(n, (1e9, 0)))
    ordered: List[str] = []
    while queue:
        n = queue.pop(0)
        if n in ordered:
            continue
        ordered.append(n)
        queue += sorted((e[1] for e in g.edges if e[0] == n and e[1] not in ordered), key=lambda m: pos.get(m, (1e9, 0)))
    ordered += sorted((n for n in g.nodes if n not in ordered), key=lambda n: pos.get(n, (1e9, 0)))
    g.nodes = {n: g.nodes[n] for n in ordered}
    g.shown = [t.text for s in nodes for t in s.texts] + [t.text for c in containers for t in c.texts] + [t.text for tl in labels.values() for t in tl] \
        + [x.text for x in free if id(x) in ids]                                      # type: ignore[attr-defined]
    return (g if g.is_meaningful() else None), stats


def _center(x: object) -> Point:
    return x.center  # type: ignore[attr-defined]
