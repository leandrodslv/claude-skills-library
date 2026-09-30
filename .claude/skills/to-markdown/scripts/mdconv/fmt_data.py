"""Données et texte → Markdown : CSV/TSV, JSON/JSONL, notebooks Jupyter, YAML, XML/RSS, texte, Markdown, code.

Règle : ce qui est tabulaire devient un tableau ; ce qui est structuré reste lisible (bloc de code borné) ;
les gros fichiers sont résumés (schéma + aperçu) plutôt que recopiés en entier dans le contexte d'une IA.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .detect import CODE_LANGS
from .util import (clean_text, decode_text, esc_inline, fence, html_to_text, local, md_table,
                   parse_xml)

MAX_TEXT = 25_000        # au-delà : résumé + aperçu plutôt que copie intégrale d'un bloc structuré
HEAD_LINES = 200


def _read_text(path) -> Tuple[str, str]:
    return decode_text(Path(path).read_bytes())


def _truncate_block(text: str, limit_lines: int = HEAD_LINES, tail: int = 20) -> Tuple[str, bool]:
    lines = text.split("\n")
    if len(text) <= MAX_TEXT and len(lines) <= 800:
        return text, False
    head = lines[:limit_lines]
    end = lines[-tail:] if tail else []
    omitted = len(lines) - len(head) - len(end)
    return "\n".join(head + [f"… ({omitted} lignes omises) …"] + end), True


# --------------------------------------------------------------------------
# CSV / TSV
# --------------------------------------------------------------------------

def _sniff_dialect(sample: str) -> Any:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        first = "\n".join(sample.split("\n")[:5])
        counts = {d: first.count(d) for d in (",", ";", "\t", "|")}
        best = max(counts, key=counts.get)  # type: ignore[arg-type]

        class _D(csv.excel):
            delimiter = best

        return _D()


def _looks_numeric(s: str) -> bool:
    return bool(re.fullmatch(r"[-+]?\d+([.,]\d+)?(e[-+]?\d+)?%?", s.strip(), re.I))


def profile_columns(header: List[str], rows: List[List[str]]) -> List[List[str]]:
    """Schéma compact : type, valeurs non vides, min/max ou exemples, par colonne."""
    out = [["Colonne", "Type", "Non vides", "Aperçu"]]
    sample = rows[:5000]
    for j, name in enumerate(header):
        vals = [r[j].strip() for r in sample if j < len(r) and r[j].strip()]
        n = len(vals)
        if not vals:
            out.append([esc_inline(name), "vide", "0", ""])
            continue
        if all(_looks_numeric(v) for v in vals):
            nums = []
            for v in vals:
                try:
                    nums.append(float(v.replace(",", ".").rstrip("%")))
                except ValueError:
                    pass
            kind = "entier" if all(x == int(x) for x in nums) else "décimal"
            prev = f"{min(nums):g} … {max(nums):g}" if nums else ""
        elif all(re.fullmatch(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?", v) or re.fullmatch(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", v) for v in vals):
            kind = "date"
            prev = f"{min(vals)} … {max(vals)}"
        else:
            uniq = list(dict.fromkeys(vals))
            kind = "texte" if len(uniq) > 12 or len(uniq) > n * 0.5 else f"catégorie ({len(uniq)})"
            prev = ", ".join(esc_inline(u[:24]) for u in uniq[:4])
        out.append([esc_inline(name), kind, str(n), prev])
    return out


@engine("csv", name="native", prio=10)
def csv_native(path, ctx: Ctx) -> Result:
    p = Path(path)
    raw_head = p.read_bytes()[:262144]
    text_head, enc = decode_text(raw_head)
    dialect = _sniff_dialect(text_head[:65536])
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    cap = ctx.opts.table_rows
    rows: List[List[str]] = []
    total = 0
    ncols = 0
    with open(p, newline="", encoding=enc if enc != "utf-8-sig" else "utf-8-sig", errors="replace") as f:
        for r in csv.reader(f, dialect):
            if not any(c.strip() for c in r):
                continue
            total += 1
            ncols = max(ncols, len(r))
            if not cap or len(rows) <= cap + 1000:
                rows.append([clean_text(c) for c in r])
    if not rows:
        raise Unsupported("CSV vide")
    header_row = rows[0]
    has_header = (all(c.strip() for c in header_row) and not any(_looks_numeric(c) for c in header_row)
                  and len(set(header_row)) == len(header_row))
    if not has_header:
        header_row = [f"col{i + 1}" for i in range(ncols)]
        body = rows
    else:
        body = rows[1:]
    header_row = header_row + [f"col{i + 1}" for i in range(len(header_row), ncols)]
    shown = body[:cap] if cap else body
    grid = [header_row] + [[esc_inline(c) for c in r] + [""] * (ncols - len(r)) for r in shown]
    grid[0] = [esc_inline(c) for c in grid[0]]
    delim = getattr(dialect, "delimiter", ",")
    stats = f"{total - (1 if has_header else 0)} ligne(s) × {ncols} colonne(s) · séparateur {'tabulation' if delim == chr(9) else repr(delim)} · encodage {enc}"
    parts = [f"_{stats}_", md_table(grid)]
    truncated = len(body) > len(shown) or total - (1 if has_header else 0) > len(shown)
    if truncated:
        left = total - (1 if has_header else 0) - len(shown)
        parts.append(f"_… {left} ligne(s) de plus dans le fichier source (aperçu limité à {cap} lignes)._")
        parts.append("## Schéma des colonnes (échantillon)\n\n" + md_table(profile_columns(header_row, body)))
    md = "\n\n".join(parts)
    res = Result(markdown=md, fmt="csv", engine="native", title=p.stem)
    res.stats["partial_source"] = True
    return res


# --------------------------------------------------------------------------
# JSON / JSONL
# --------------------------------------------------------------------------

def _flatten(obj: Any, prefix: str = "", out: Optional[Dict[str, str]] = None, depth: int = 0) -> Dict[str, str]:
    """Aplatit un enregistrement JSON : {"a": {"b": 1}} → {"a.b": "1"} (jusqu'à 3 niveaux)."""
    out = {} if out is None else out
    if isinstance(obj, dict) and depth < 3:
        for k, v in obj.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict) and depth < 2:
                _flatten(v, key + ".", out, depth + 1)
            else:
                out[key] = _cell(v)
    else:
        out[prefix.rstrip(".") or "value"] = _cell(obj)
    return out


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return esc_inline(clean_text(v))
    s = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return s if len(s) <= 200 else s[:197] + "…"


def _records_table(items: List[dict], cap: int) -> Optional[str]:
    if len(items) < 2 or not all(isinstance(i, dict) for i in items):
        return None
    flat = [_flatten(i) for i in items[: (cap or len(items)) + 1000]]
    keys: List[str] = []
    seen = set()
    for r in flat:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    if len(keys) > 40:
        return None
    freq = {k: sum(1 for r in flat if k in r) for k in keys}
    if max(freq.values()) < len(flat) * 0.6:
        return None
    shown = flat[:cap] if cap else flat
    grid = [[esc_inline(k) for k in keys]] + [[r.get(k, "") for k in keys] for r in shown]
    md = md_table(grid)
    if len(items) > len(shown):
        md += f"\n\n_… {len(items) - len(shown)} enregistrement(s) de plus (aperçu limité à {cap})._"
    return md


def _shape(obj: Any, depth: int = 0) -> str:
    if isinstance(obj, dict):
        if depth >= 3:
            return f"objet ({len(obj)} clés)"
        inner = ", ".join(f"{k}: {_shape(v, depth + 1)}" for k, v in list(obj.items())[:12])
        return "{" + inner + (", …" if len(obj) > 12 else "") + "}"
    if isinstance(obj, list):
        return f"liste[{len(obj)}]" + (f" de {_shape(obj[0], depth + 1)}" if obj and depth < 3 else "")
    return type(obj).__name__ if obj is not None else "null"


def json_markdown(obj: Any, cap: int, name: str) -> str:
    if isinstance(obj, list):
        t = _records_table(obj, cap)
        if t:
            return f"_{len(obj)} enregistrement(s)_\n\n{t}"
    if isinstance(obj, dict) and len(obj) <= 6:
        for k, v in obj.items():
            if isinstance(v, list) and len(v) >= 3 and all(isinstance(i, dict) for i in v):
                t = _records_table(v, cap)
                if t:
                    others = {kk: vv for kk, vv in obj.items() if kk != k}
                    pre = ("```json\n" + json.dumps(others, ensure_ascii=False, indent=2)[:2000] + "\n```\n\n") if others else ""
                    return f"{pre}**{esc_inline(k)}** — {len(v)} enregistrement(s)\n\n{t}"
    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
    block, cut = _truncate_block(pretty)
    out = fence(block, "json")
    if cut:
        out = f"_Structure : {_shape(obj)}_\n\n" + out
    return out


@engine(["json"], name="native", prio=10)
def json_native(path, ctx: Ctx) -> Result:
    text, _enc = _read_text(path)
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise Unsupported(f"JSON invalide : {exc}")
    res = Result(markdown=json_markdown(obj, ctx.opts.table_rows, Path(path).stem), fmt="json", engine="native", title=Path(path).stem)
    res.stats["partial_source"] = True
    return res


@engine(["jsonl"], name="native", prio=10)
def jsonl_native(path, ctx: Ctx) -> Result:
    text, _enc = _read_text(path)
    items = []
    bad = 0
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            items.append(json.loads(ln))
        except ValueError:
            bad += 1
    if not items:
        raise Unsupported("aucune ligne JSON valide")
    if bad:
        ctx.warn(f"{bad} ligne(s) non JSON ignorée(s)")
    res = Result(markdown=json_markdown(items, ctx.opts.table_rows, Path(path).stem), fmt="jsonl", engine="native", title=Path(path).stem)
    res.stats["partial_source"] = True
    return res


# --------------------------------------------------------------------------
# Notebooks Jupyter
# --------------------------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _src(v: Any) -> str:
    return "".join(v) if isinstance(v, list) else str(v or "")


@engine("ipynb", name="native", prio=10)
def ipynb_native(path, ctx: Ctx) -> Result:
    text, _enc = _read_text(path)
    try:
        nb = json.loads(text)
    except ValueError as exc:
        raise Unsupported(f"notebook invalide : {exc}")
    cells = nb.get("cells")
    if cells is None:  # nbformat 3
        cells = [c for ws in nb.get("worksheets", []) for c in ws.get("cells", [])]
    meta = nb.get("metadata", {})
    lang = (meta.get("language_info", {}).get("name") or meta.get("kernelspec", {}).get("language") or "python").lower()
    out: List[str] = []
    title = ""
    n_img = 0
    for c in cells:
        kind = c.get("cell_type")
        src = _src(c.get("source", c.get("input", ""))).rstrip()
        if kind == "markdown" or kind == "heading":
            if src:
                out.append(src)
                if not title:
                    m = re.match(r"#\s+(.+)", src)
                    if m:
                        title = m.group(1).strip()
        elif kind == "code":
            if src:
                out.append(fence(src, lang))
            for o in c.get("outputs", []):
                otype = o.get("output_type")
                if otype == "stream":
                    t = _ANSI.sub("", _src(o.get("text", "")))
                    if t.strip():
                        blk, _cut = _truncate_block(t.rstrip(), 40, 10)
                        out.append("**Sortie :**\n\n" + fence(blk, "text"))
                elif otype in ("execute_result", "display_data", "pyout"):
                    data = o.get("data", {})
                    md_out = _notebook_output(data, ctx, path, n_img)
                    if md_out:
                        if "![" in md_out:
                            n_img += 1
                        out.append(md_out)
                elif otype in ("error", "pyerr"):
                    tb = _ANSI.sub("", "\n".join(o.get("traceback", []))) or f"{o.get('ename', '')}: {o.get('evalue', '')}"
                    blk, _cut = _truncate_block(tb.rstrip(), 15, 5)
                    out.append("**Erreur :**\n\n" + fence(blk, "text"))
        elif kind == "raw" and src:
            out.append(fence(src, "text"))
    if not out:
        raise Unsupported("notebook vide")
    md = "\n\n".join(out)
    res = Result(markdown=md, fmt="ipynb", engine="native", title=title or Path(path).stem)
    res.stats["partial_source"] = True
    return res


def _notebook_output(data: Dict[str, Any], ctx: Ctx, path, n: int) -> str:
    import base64

    if "text/markdown" in data:
        return _src(data["text/markdown"]).strip()
    for mime, ext in (("image/png", "png"), ("image/jpeg", "jpg"), ("image/svg+xml", "svg")):
        if mime in data:
            raw = _src(data[mime])
            try:
                blob = raw.encode("utf-8") if ext == "svg" else base64.b64decode(re.sub(r"\s+", "", raw))
            except Exception:
                continue
            link = ctx.add_asset(blob, ext, stem="sortie")
            if link:
                return f"![sortie]({link})"
    if "text/html" in data:
        html = _src(data["text/html"])
        if "<table" in html.lower():
            from .fmt_html import html_to_markdown

            md, _t, _m, _s = html_to_markdown(html, ctx, stem="sortie")
            if md.strip():
                return md.strip()
        txt = _ANSI.sub("", html_to_text(html)).strip()
        if txt:
            return fence(_truncate_block(txt, 40, 10)[0], "text")
    if "text/plain" in data:
        t = _ANSI.sub("", _src(data["text/plain"])).rstrip()
        if t and not re.match(r"^<[\w.]+ .*at 0x[0-9a-f]+>$", t) and not re.match(r"^<Figure size", t):
            return "**Résultat :**\n\n" + fence(_truncate_block(t, 40, 10)[0], "text")
    return ""


# --------------------------------------------------------------------------
# YAML, XML, RSS
# --------------------------------------------------------------------------

@engine("yaml", name="native", prio=10)
def yaml_native(path, ctx: Ctx) -> Result:
    text, _e = _read_text(path)
    block, cut = _truncate_block(text.rstrip())
    res = Result(markdown=fence(block, "yaml"), fmt="yaml", engine="native", title=Path(path).stem)
    res.stats["partial_source"] = True
    return res


@engine("xml", name="native", prio=10)
def xml_native(path, ctx: Ctx) -> Result:
    raw = Path(path).read_bytes()
    root = parse_xml(raw)
    tags: Dict[str, int] = {}
    depth = 0

    def walk(e: ET.Element, d: int) -> None:
        nonlocal depth
        depth = max(depth, d)
        tags[local(e.tag)] = tags.get(local(e.tag), 0) + 1
        for c in e:
            if isinstance(c.tag, str):
                walk(c, d + 1)

    walk(root, 1)
    text, _e = decode_text(raw)
    if hasattr(ET, "indent") and len(raw) < 2_000_000:
        try:
            ET.indent(root)  # type: ignore[attr-defined]
            text = ET.tostring(root, encoding="unicode")
        except Exception:
            pass
    block, cut = _truncate_block(text.strip())
    top = ", ".join(f"`{k}` ×{v}" for k, v in sorted(tags.items(), key=lambda kv: -kv[1])[:10])
    md = f"_XML — racine `{local(root.tag)}`, {sum(tags.values())} éléments, profondeur {depth}. Balises : {top}_\n\n" + fence(block, "xml")
    res = Result(markdown=md, fmt="xml", engine="native", title=Path(path).stem)
    res.stats["partial_source"] = True
    return res


@engine("feed", name="native", prio=10)
def feed_native(path, ctx: Ctx) -> Result:
    root = parse_xml(Path(path).read_bytes())
    items: List[str] = []
    title = ""
    is_atom = local(root.tag) == "feed"
    channel = root if is_atom else next((c for c in root if local(c.tag) == "channel"), root)
    for c in channel:
        n = local(c.tag)
        if n == "title" and not title:
            title = clean_text(c.text or "").strip()
    for it in channel.iter():
        if local(it.tag) not in ("item", "entry"):
            continue
        f = {local(k.tag): k for k in it}
        t = clean_text((f["title"].text if "title" in f else "") or "").strip()
        link = ""
        if "link" in f:
            link = f["link"].get("href") or (f["link"].text or "")
        date = ((f.get("pubDate") or f.get("updated") or f.get("published") or f.get("date") or ET.Element("x")).text or "").strip()
        desc = ""
        for key in ("description", "summary", "content", "encoded"):
            if key in f and (f[key].text or "").strip():
                desc = clean_text(html_to_text(f[key].text or "")).replace("\n", " ").strip()
                break
        line = f"- [{esc_inline(t)}]({link})" if link else f"- {esc_inline(t)}"
        if date:
            line += f" — {date}"
        if desc:
            line += f"\n  {esc_inline(desc[:400])}"
        items.append(line)
    md = (f"# {esc_inline(title)}\n\n" if title else "") + "\n".join(items)
    res = Result(markdown=md, fmt="feed", engine="native", title=title)
    res.stats["partial_source"] = True
    return res


# --------------------------------------------------------------------------
# Texte, Markdown, code
# --------------------------------------------------------------------------

def _wrap_front_matter(text: str) -> str:
    """Le front matter YAML d'un .md source ne doit pas concurrencer celui du convertisseur."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if m:
        return "```yaml\n" + m.group(1).rstrip() + "\n```\n\n" + text[m.end():]
    return text


@engine("md", name="native", prio=10)
def md_native(path, ctx: Ctx) -> Result:
    text, _e = _read_text(path)
    text = _wrap_front_matter(clean_text(text.replace("\r\n", "\n")))
    res = Result(markdown=text, fmt="md", engine="native", title=Path(path).stem)
    res.source_text = text
    return res


def _looks_preformatted(lines: List[str]) -> bool:
    ne = [ln for ln in lines if ln.strip()]
    if len(ne) < 3:
        return False
    indented = sum(1 for ln in ne if ln.startswith(("  ", "\t")))
    aligned = sum(1 for ln in ne if re.search(r"\S {3,}\S", ln))
    boxed = sum(1 for ln in ne if re.search(r"[│┃─━┌┐└┘├┤┬┴┼+|]{2,}", ln))
    logs = sum(1 for ln in ne if re.match(r"^\s*(\d{4}-\d{2}-\d{2}|\[\d|\w{3} +\d+ \d{2}:\d{2}|\d{2}:\d{2}:\d{2})", ln))
    return (indented + aligned + boxed) / len(ne) > 0.3 or logs / len(ne) > 0.5


@engine("txt", name="native", prio=10)
def txt_native(path, ctx: Ctx) -> Result:
    text, enc = _read_text(path)
    text = clean_text(text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = text.split("\n")
    res_fmt = "txt"
    if _looks_preformatted(lines):
        block, cut = _truncate_block(text.rstrip(), 400, 40)
        md = fence(block, "text")
    else:
        md = text.strip()  # texte courant : repris tel quel (fidélité à ce que l'auteur a écrit)
    res = Result(markdown=md, fmt=res_fmt, engine="native", title=Path(path).stem)
    res.source_text = text
    return res


@engine("code", name="native", prio=10)
def code_native(path, ctx: Ctx) -> Result:
    p = Path(path)
    text, _e = _read_text(path)
    lang = CODE_LANGS.get(p.suffix.lower().lstrip("."), p.suffix.lower().lstrip("."))
    if p.name.lower() in ("dockerfile", "makefile"):
        lang = p.name.lower()
    body = text.replace("\r\n", "\n").rstrip("\n")
    n = body.count("\n") + 1
    md = f"_{n} ligne(s) · {lang or 'texte'}_\n\n" + fence(body, lang)
    res = Result(markdown=md, fmt="code", engine="native", title=p.name)
    res.source_text = body
    return res


@engine("markup", name="native", prio=90)
def markup_raw(path, ctx: Ctx) -> Result:
    """Repli sans pandoc : le source brut dans un bloc de code (lisible tel quel par une IA)."""
    p = Path(path)
    text, _e = _read_text(path)
    lang = CODE_LANGS.get(p.suffix.lower().lstrip("."), "")
    ctx.warn("pandoc absent : source brut conservé dans un bloc de code (installer pandoc pour une conversion structurée)")
    res = Result(markdown=fence(text.replace("\r\n", "\n").rstrip("\n"), lang), fmt="markup", engine="native-raw", title=p.name)
    res.source_text = text
    return res
