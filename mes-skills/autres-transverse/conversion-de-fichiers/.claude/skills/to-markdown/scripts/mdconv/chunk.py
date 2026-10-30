"""Découpage des longs Markdown en parties de taille bornée (jetons), sans casser tableaux ni blocs de code."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .util import est_tokens, slugify


def split_blocks(md: str) -> List[Tuple[str, str]]:
    """Blocs atomiques (type, texte) : titre, code, tableau, paragraphe/liste."""
    lines = md.split("\n")
    blocks: List[Tuple[str, str]] = []
    cur: List[str] = []
    kind = "p"
    fence = None

    def flush() -> None:
        nonlocal cur, kind
        if cur and any(x.strip() for x in cur):
            blocks.append((kind, "\n".join(cur).rstrip()))
        cur, kind = [], "p"

    for ln in lines:
        m = re.match(r"^\s*(`{3,}|~{3,})", ln)
        if fence:
            cur.append(ln)
            if m and ln.strip().startswith(fence) and set(ln.strip()) <= {fence[0]}:
                fence = None
                flush()
            continue
        if m:
            flush()
            fence, kind = m.group(1), "code"
            cur.append(ln)
            continue
        if re.match(r"^#{1,6}\s", ln):
            flush()
            blocks.append(("h", ln))
            continue
        if ln.startswith("|"):
            if kind != "table":
                flush()
                kind = "table"
            cur.append(ln)
            continue
        if not ln.strip():
            flush()
            continue
        if kind == "table":
            flush()
        cur.append(ln)
    flush()
    return blocks


def _split_big(text: str, kind: str, budget: int) -> List[str]:
    """Bloc plus gros que le budget : coupe un tableau par lignes (en-tête répété), le reste par lignes."""
    lines = text.split("\n")
    head = lines[:2] if kind == "table" and len(lines) > 2 else []
    body = lines[2:] if head else lines
    out, cur = [], list(head)
    for ln in body:
        if est_tokens("\n".join(cur + [ln])) > budget and len(cur) > len(head):
            out.append("\n".join(cur))
            cur = list(head)
        cur.append(ln)
    if len(cur) > len(head):
        out.append("\n".join(cur))
    return out or [text]


def chunk_markdown(md: str, max_tokens: int) -> List[Dict[str, Any]]:
    fm = re.match(r"\A---\n.*?\n---\n", md, re.S)
    body = md[fm.end():] if fm else md
    chunks: List[Dict[str, Any]] = []
    cur: List[str] = []
    path: List[str] = []
    cur_path: List[str] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            text = "\n\n".join(cur).strip()
            if text:
                chunks.append({"text": text, "tokens": est_tokens(text), "section": " > ".join(cur_path)})
        cur = []

    for kind, text in split_blocks(body):
        if kind == "h":
            level = len(re.match(r"^#+", text).group(0))  # type: ignore[union-attr]
            title = re.sub(r"^#+\s*", "", text).strip()
            cur_tokens = est_tokens("\n\n".join(cur))
            if cur and (level <= 2 and cur_tokens >= max_tokens * 0.4 or cur_tokens >= max_tokens * 0.85):
                flush()
            path = path[: level - 1] + [title]
            if not cur:
                cur_path = list(path)
            cur.append(text)
            continue
        t = est_tokens(text)
        pieces = [text] if t <= max_tokens else _split_big(text, kind, max_tokens)
        for piece in pieces:
            if cur and est_tokens("\n\n".join(cur + [piece])) > max_tokens:
                flush()
                cur_path = list(path)
            if not cur:
                cur_path = list(path)
            cur.append(piece)
    flush()
    return chunks


def chunk_outputs(entries: List[Dict[str, Any]], out_root: Path, max_tokens: int) -> None:
    """Pour chaque .md dépassant ``max_tokens`` : dossier « <nom>_chunks/ » (part-NN.md + index.json)."""
    for e in entries:
        md_rel = e.get("output")
        if not md_rel or int(e.get("tokens_est", 0)) <= max_tokens:
            continue
        md_path = out_root / md_rel
        if not md_path.exists():
            continue
        parts = chunk_markdown(md_path.read_text(encoding="utf-8"), max_tokens)
        if len(parts) < 2:
            continue
        cdir = md_path.with_name(slugify(md_path.stem) + "_chunks")
        cdir.mkdir(parents=True, exist_ok=True)
        index = []
        for i, c in enumerate(parts, 1):
            name = f"part-{i:02d}.md"
            header = f"<!-- source: {e['source']} · partie {i}/{len(parts)}" + (f" · section: {c['section']}" if c["section"] else "") + " -->\n\n"
            (cdir / name).write_text(header + c["text"] + "\n", encoding="utf-8")
            index.append({"file": name, "tokens": c["tokens"], "section": c["section"]})
        (cdir / "index.json").write_text(json.dumps({"source": e["source"], "parts": index}, ensure_ascii=False, indent=2), encoding="utf-8")
        e["chunks"] = f"{cdir.relative_to(out_root).as_posix()}/"
