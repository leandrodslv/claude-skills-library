"""Écriture des sorties : planification des noms, .md + assets, INDEX.md, rapport JSON, fichier combiné."""
from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import quote
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core import Options, VERSION
from .pipeline import Outcome, front_matter, report_entry
from .util import slugify


@dataclass
class InputFile:
    src: Path
    rel: str                       # chemin relatif (séparateur « / »), sert au nom de sortie
    origin: str = ""               # archive d'origine, le cas échéant


@dataclass
class Planned:
    file: InputFile
    out_md: str                    # relatif à la racine de sortie
    assets_dir: str                # nom du dossier d'assets, voisin du .md


def plan_outputs(files: List[InputFile], flat: bool = False) -> List[Planned]:
    """Attribue un .md à chaque entrée. « a.docx » et « a.pdf » voisins → « a.docx.md » / « a.pdf.md »."""
    groups: Dict[Tuple[str, str], List[InputFile]] = {}
    for f in files:
        p = Path(f.rel)
        d = "" if flat else p.parent.as_posix()
        groups.setdefault((d.lower(), p.stem.lower()), []).append(f)
    planned: List[Planned] = []
    used: Dict[str, int] = {}
    for f in files:
        p = Path(f.rel)
        d = "" if flat else p.parent.as_posix()
        clash = len(groups[(d.lower(), p.stem.lower())]) > 1
        name = f"{p.stem}.{p.suffix.lstrip('.').lower()}" if clash and p.suffix else p.stem
        rel_md = (Path(d) / (name + ".md")).as_posix() if d not in ("", ".") else name + ".md"
        key = rel_md.lower()
        if key in used:  # collision résiduelle (casse, dossiers aplatis) : suffixe numérique
            used[key] += 1
            rel_md = rel_md[:-3] + f"-{used[key]}.md"
        else:
            used[key] = 1
        assets = slugify(Path(rel_md).stem, keep_dots=False) + "_assets"
        planned.append(Planned(f, rel_md, assets))
    return planned


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_outcome(out: Outcome, opts: Options, out_root: Path, out_md: str, write_md: bool = True) -> Dict[str, Any]:
    """Écrit le .md et ses assets ; renvoie l'entrée de rapport (chemins de vision résolus)."""
    md_path = out_root / out_md
    entry_md: Optional[str] = None
    if out.result is not None and out.status not in ("error", "unsupported"):
        fm = front_matter(out, opts, out.src)
        final = fm + out.body
        if write_md:
            atomic_write(md_path, final.encode("utf-8"))
            entry_md = out_md
        if out.ctx is not None:
            for name, asset in out.ctx.assets.items():
                atomic_write(md_path.parent / out.ctx.assets_dir / name, asset.data)
            for v in out.ctx.vision:  # chemins d'assets → chemins absolus lisibles par l'IA
                if v.path.startswith(out.ctx.assets_dir + "/"):
                    v.path = str((md_path.parent / v.path).resolve())
                elif not os.path.isabs(v.path):
                    v.path = str((out.src.parent / v.path).resolve()) if (out.src.parent / v.path).exists() else v.path
        out.ctx.cleanup() if out.ctx else None
    if out.ctx is not None and out.ctx.previews:
        out.ctx.previews = [str((md_path.parent / p).resolve()) for p in out.ctx.previews]
    entry = report_entry(out, entry_md)
    entry["_bytes"] = len(out.body.encode("utf-8")) if out.body else 0
    return entry


def build_index(entries: List[Dict[str, Any]], out_root: Path, title: str = "Index des conversions") -> str:
    done = [e for e in entries if e.get("output")]
    total_words = sum(int(e.get("words", 0)) for e in done)
    total_tokens = sum(int(e.get("tokens_est", 0)) for e in done)
    lines = [f"# {title}", "",
             f"_{len(done)} fichier(s) converti(s) sur {len(entries)} · {total_words:,} mots · ≈ {total_tokens:,} jetons_".replace(",", " "),
             "", "| Fichier source | Markdown | Format | Mots | Jetons | Statut |", "| --- | --- | --- | ---: | ---: | --- |"]
    sym = {"ok": "ok", "warn": "à vérifier", "needs_vision": "lecture visuelle", "unsupported": "non pris en charge",
           "error": "erreur", "unchanged": "inchangé"}
    for e in sorted(entries, key=lambda x: x["source"]):
        md = e.get("output")
        link = f"[{md}]({quote(md, safe='/')})" if md else "—"
        st = sym.get(e["status"], e["status"])
        lines.append(f"| {e['source']} | {link} | {e.get('format', '')} | {int(e.get('words', 0))} | {int(e.get('tokens_est', 0))} | {st} |")
    vis = [(e, v) for e in entries for v in e.get("vision", [])]
    if vis:
        lines += ["", "## À traiter par lecture visuelle", ""]
        for e, v in vis:
            pages = f" (pages {v['pages']})" if v.get("pages") else ""
            lines.append(f"- `{v['path']}`{pages} — {v['reason']} _(source : {e['source']})_")
    bad = [e for e in entries if e["status"] in ("error", "unsupported")]
    if bad:
        lines += ["", "## Non convertis", ""]
        for e in bad:
            lines.append(f"- `{e['source']}` — {e.get('error', e['status'])}")
    warn = [e for e in entries if e.get("warnings") and e.get("output")]
    if warn:
        lines += ["", "## Avertissements", ""]
        for e in warn:
            for w in e["warnings"]:
                lines.append(f"- `{e['source']}` — {w}")
    return "\n".join(lines) + "\n"


def write_report(entries: List[Dict[str, Any]], out_root: Path, opts: Options, inputs: List[str],
                 elapsed: float) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for e in entries:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    clean = [{k: v for k, v in e.items() if not k.startswith("_")} for e in sorted(entries, key=lambda x: x["source"])]
    report = {
        "tool": "mdconv", "version": VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": inputs, "output_dir": str(out_root),
        "summary": {"files": len(entries), "by_status": counts,
                    "words": sum(int(e.get("words", 0)) for e in entries),
                    "tokens_est": sum(int(e.get("tokens_est", 0)) for e in entries),
                    "seconds": round(elapsed, 2)},
        "vision_needed": [{"source": e["source"], **v} for e in clean for v in e.get("vision", [])],
        "files": clean,
    }
    atomic_write(out_root / "_report.json", json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    return report


def write_combined(entries: List[Dict[str, Any]], out_root: Path, only: bool, name: str = "combined.md") -> Optional[Path]:
    parts: List[str] = []
    for e in sorted(entries, key=lambda x: x["source"]):
        md = e.get("output")
        if not md or not (out_root / md).exists():
            continue
        text = (out_root / md).read_text(encoding="utf-8")
        text = re.sub(r"\A---\n.*?\n---\n\n?", "", text, flags=re.S)
        d = Path(md).parent.as_posix()
        if d not in ("", "."):  # les liens d'images doivent rester valides depuis la racine
            text = re.sub(r"(!\[[^\]]*\]\()(?!https?:|data:|/)", lambda m, prefix=quote(d, safe="/") + "/": m.group(1) + prefix, text)
        parts.append(f"<!-- source: {e['source']} -->\n\n{text.strip()}")
    if not parts:
        return None
    path = out_root / name
    atomic_write(path, ("\n\n---\n\n".join(parts) + "\n").encode("utf-8"))
    if only:
        for e in entries:
            md = e.get("output")
            if md and (out_root / md).exists():
                (out_root / md).unlink()
                e.pop("output", None)
    return path


# -- cache incrémental --------------------------------------------------------

CACHE_NAME = ".mdconv-cache.json"


def load_cache(out_root: Path) -> Dict[str, Any]:
    try:
        return json.loads((out_root / CACHE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(out_root: Path, cache: Dict[str, Any]) -> None:
    try:
        atomic_write(out_root / CACHE_NAME, json.dumps(cache, ensure_ascii=False).encode("utf-8"))
    except OSError:
        pass


def options_signature(opts: Options) -> str:
    import hashlib
    from dataclasses import asdict

    d = asdict(opts)
    for k in ("timeout", "archive_depth"):
        d.pop(k, None)
    return hashlib.sha1((VERSION + json.dumps(d, sort_keys=True)).encode()).hexdigest()[:12]
