"""Interface en ligne de commande : dossiers ou fichiers → Markdown."""
from __future__ import annotations

import argparse
import atexit
import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import VERSION, Options
from .detect import detect
from .pipeline import convert_to_memory
from .writer import (InputFile, Planned, build_index, load_cache, options_signature, plan_outputs,
                     save_cache, write_combined, write_outcome, write_report)
from .util import sha256_file

SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".svn", ".hg", ".idea", ".vscode", ".venv", "venv"}
SKIP_FILES = {"thumbs.db", "desktop.ini", ".ds_store"}
DEFAULT_OUT = "markdown_output"
STATUS_TAG = {"ok": "ok", "warn": "!", "needs_vision": "vision", "unsupported": "non géré", "error": "échec",
              "unchanged": "="}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convert.py",
        description="Convertit n'importe quel fichier (Word, PowerPoint, Excel, SVG, PDF, HTML, images…) en Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exemples :\n"
               "  convert.py rapport.docx                    → markdown_output/rapport.md\n"
               "  convert.py entrants/ -o md/ --combined     → un .md par fichier + combined.md\n"
               "  convert.py deck.pptx -o - --images skip    → Markdown sur la sortie standard\n"
               "  convert.py --doctor                        → moteurs disponibles sur cette machine\n"
               "  convert.py --check md/                     → vérifie un dossier converti")
    p.add_argument("inputs", nargs="*", help="fichiers ou dossiers à convertir")
    g = p.add_argument_group("sortie")
    g.add_argument("-o", "--output", default=None, help=f"dossier de sortie (défaut : ./{DEFAULT_OUT}) ; « - » = sortie standard")
    g.add_argument("--in-place", action="store_true", help="écrit chaque .md à côté de sa source")
    g.add_argument("--flat", action="store_true", help="n'imite pas l'arborescence d'entrée")
    g.add_argument("--combined", action="store_true", help="produit aussi combined.md (tout concaténé)")
    g.add_argument("--only-combined", action="store_true", help="ne garde que combined.md")
    g.add_argument("--frontmatter", choices=["min", "full", "none"], default="min", help="en-tête YAML (défaut : min)")
    g.add_argument("--no-index", action="store_true", help="pas d'INDEX.md")
    g.add_argument("--json", action="store_true", help="imprime le rapport JSON sur la sortie standard")
    c = p.add_argument_group("contenu")
    c.add_argument("--images", choices=["extract", "skip"], default="extract", help="extraire les images incluses (défaut) ou les ignorer")
    c.add_argument("--table-rows", type=int, default=1000, help="plafond de lignes par tableau, 0 = illimité (défaut : 1000)")
    c.add_argument("--formulas", action="store_true", help="Excel : affiche aussi les formules")
    c.add_argument("--no-comments", action="store_true", help="ignore les commentaires (Word/Excel/PowerPoint)")
    c.add_argument("--no-notes", action="store_true", help="ignore notes du présentateur et notes de bas de page")
    c.add_argument("--headers-footers", action="store_true", help="Word : inclut en-têtes et pieds de page")
    c.add_argument("--keep-toc", action="store_true", help="Word : conserve la table des matières")
    c.add_argument("--track-changes", choices=["accept", "mark"], default="accept", help="modifications suivies : accepter (défaut) ou marquer <ins>/<del>")
    c.add_argument("--html-mode", choices=["auto", "full", "main"], default="auto", help="HTML : contenu principal (auto), page entière ou <main> seul")
    c.add_argument("--no-infer-headings", action="store_true", help="Word : ne déduit pas les titres de la mise en forme")
    c.add_argument("--no-hidden", action="store_true", help="ignore feuilles et diapositives masquées")
    e = p.add_argument_group("moteurs")
    e.add_argument("--engines", default=None, help="ordre imposé, ex. « native,markitdown,libreoffice »")
    e.add_argument("--no-external", action="store_true", help="n'utilise que le noyau natif (aucun outil externe)")
    e.add_argument("--ocr", choices=["auto", "off", "force"], default="auto", help="OCR des pages/images sans texte (défaut : auto)")
    e.add_argument("--ocr-lang", default="", help="langues Tesseract, ex. fra+eng (défaut : détection)")
    e.add_argument("--render", action="store_true", help="écrit des aperçus PNG (pages PDF, diapositives, feuilles) dans le dossier d'assets pour vérifier la conversion à l'œil")
    e.add_argument("--compare", action="store_true", help="essaie tous les moteurs disponibles et affiche le comparatif")
    e.add_argument("--threshold", type=float, default=0.90, help="score minimal pour s'arrêter à un moteur (défaut : 0.90)")
    r = p.add_argument_group("lot")
    r.add_argument("-j", "--jobs", type=int, default=0, help="processus parallèles (défaut : auto)")
    r.add_argument("--include", action="append", default=[], help="motif (glob) à inclure, répétable")
    r.add_argument("--exclude", action="append", default=[], help="motif (glob) à exclure, répétable")
    r.add_argument("--force", action="store_true", help="reconvertit même si la source n'a pas changé")
    r.add_argument("--max-size-mb", type=int, default=500)
    r.add_argument("--timeout", type=int, default=180, help="délai par outil externe, en secondes")
    r.add_argument("--chunk-tokens", type=int, default=0, help="découpe les sorties longues en parties d'environ N jetons")
    m = p.add_argument_group("divers")
    m.add_argument("--doctor", action="store_true", help="diagnostic : moteurs disponibles et ce qu'ils apportent")
    m.add_argument("--check", metavar="DOSSIER", help="vérifie un dossier de Markdown converti")
    m.add_argument("-q", "--quiet", action="store_true")
    m.add_argument("-v", "--verbose", action="store_true")
    m.add_argument("--version", action="version", version=f"mdconv {VERSION}")
    return p


def options_from_args(a: argparse.Namespace) -> Options:
    opts = Options(
        images=a.images, comments=not a.no_comments, notes=not a.no_notes, hidden=not a.no_hidden,
        headers_footers=a.headers_footers, keep_toc=a.keep_toc, formulas=a.formulas,
        track_changes=a.track_changes, table_rows=a.table_rows, html_mode=a.html_mode,
        infer_headings=not a.no_infer_headings, frontmatter=a.frontmatter,
        engines=[x.strip() for x in a.engines.split(",") if x.strip()] if a.engines else None,
        external=not a.no_external, ocr=a.ocr, ocr_lang=a.ocr_lang, render=a.render,
        max_size_mb=a.max_size_mb, timeout=a.timeout, quality_threshold=a.threshold, compare=a.compare,
    )
    return opts


# --------------------------------------------------------------------------
# Collecte des entrées
# --------------------------------------------------------------------------

def _match(rel: str, name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(name, p) for p in patterns)


def collect_inputs(inputs: List[str], include: List[str], exclude: List[str], skip_dir: Optional[Path]) -> List[InputFile]:
    files: List[InputFile] = []
    dirs = [Path(i) for i in inputs if Path(i).is_dir()]
    multi = len(dirs) > 1
    for raw in inputs:
        p = Path(raw).expanduser()
        if not p.exists():
            print(f"[avert] introuvable : {raw}", file=sys.stderr)
            continue
        if p.is_file():
            files.append(InputFile(p.resolve(), p.name))
            continue
        root = p.resolve()
        for cur, dnames, fnames in os.walk(root):
            cur_p = Path(cur)
            dnames[:] = sorted(d for d in dnames if d not in SKIP_DIRS and not d.startswith(".")
                               and not (skip_dir and (cur_p / d).resolve() == skip_dir))
            for fn in sorted(fnames):
                low = fn.lower()
                if fn.startswith(".") or fn.startswith("~$") or low in SKIP_FILES or low.endswith((".tmp", ".part", ".crdownload")):
                    continue
                full = cur_p / fn
                rel = full.relative_to(root).as_posix()
                if multi:
                    rel = f"{root.name}/{rel}"
                if include and not _match(rel, fn, include):
                    continue
                if exclude and _match(rel, fn, exclude):
                    continue
                if full.is_symlink() and not full.exists():
                    continue
                files.append(InputFile(full, rel))
    return files


def expand_archives(files: List[InputFile], opts: Options, tmp_root: Path, notes: List[Dict[str, Any]]) -> List[InputFile]:
    """Remplace chaque archive par ses membres (récursif, profondeur bornée)."""
    from .fmt_archive import expand_archive

    def rec(f: InputFile, depth: int) -> List[InputFile]:
        try:
            det = detect(f.src)
        except OSError:
            return [f]
        if det.fmt not in ("zip", "tar", "gz", "bz2", "xz") or det.note in ("jar/apk", "zip corrompu"):
            return [f]
        if depth >= opts.archive_depth:
            notes.append({"source": f.rel, "format": det.fmt, "status": "unsupported",
                          "error": f"archives imbriquées au-delà de {opts.archive_depth} niveaux : non ouverte"})
            return []
        dest = Path(tempfile.mkdtemp(prefix="arc_", dir=str(tmp_root)))
        try:
            members = expand_archive(f.src, det.fmt, dest)
        except Exception as exc:
            notes.append({"source": f.rel, "format": det.fmt, "status": "error", "error": f"archive illisible : {exc}"})
            return []
        base = f.rel
        for suf in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz", ".zip", ".tar", ".gz", ".bz2", ".xz"):
            if base.lower().endswith(suf):
                base = base[: -len(suf)]
                break
        out: List[InputFile] = []
        for name, path in members:
            low = Path(name).name
            if low.startswith(".") or low.startswith("~$") or low.lower() in SKIP_FILES or name.startswith("__MACOSX/"):
                continue
            out.extend(rec(InputFile(path, f"{base}/{name}", origin=f.rel), depth + 1))
        notes.append({"source": f.rel, "format": det.fmt, "status": "ok", "children": len(out),
                      "note": f"archive ouverte : {len(out)} fichier(s)"})
        return out

    result: List[InputFile] = []
    for f in files:
        result.extend(rec(f, 0))
    return result


# --------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------

LEGACY_FMTS = {"doc", "xls", "xlsb", "ppt", "wps", "iwork"}


def _prepare_legacy(files: List[InputFile], opts: Options, tmp_root: Path, quiet: bool) -> None:
    """Fichiers .doc/.xls/.ppt : un seul lancement LibreOffice pour tout le lot (le démarrage domine le coût)."""
    if not opts.external:
        return
    legacy: List[Path] = []
    for f in files:
        try:
            if detect(f.src).fmt in LEGACY_FMTS:
                legacy.append(f.src)
        except OSError:
            continue
    if not legacy:
        return
    from .fmt_legacy import prepare_legacy

    if not quiet:
        print(f"{len(legacy)} fichier(s) legacy : conversion groupée par LibreOffice…", file=sys.stderr)
    try:
        prepare_legacy(legacy, tmp_root / "lo", timeout=opts.timeout)
    except Exception as exc:  # la pré-conversion n'est qu'une optimisation
        print(f"[avert] pré-conversion LibreOffice ignorée : {exc}", file=sys.stderr)


def _convert_attachments(out, opts: Options, task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pièces jointes d'un e-mail : chacune est convertie à son tour (un niveau), et liée depuis le mail."""
    from urllib.parse import quote

    from .util import slugify

    out_root = Path(task["out_root"])
    base_md = Path(task["out_md"])
    child_dir = base_md.with_suffix("").as_posix() + "_attachments"
    entries: List[Dict[str, Any]] = []
    used: set = set()
    for name in out.result.stats.get("attachments", []):
        asset = out.ctx.assets.get(name)
        if asset is None:
            continue
        tmp = Path(out.ctx.tmp) / name
        tmp.write_bytes(asset.data)
        try:
            det = detect(tmp)
        except OSError:
            continue
        if det.fmt in ("binary", "empty", "zip", "encrypted") or det.fmt in ("audio", "video"):
            continue
        stem = slugify(Path(name).stem)
        while stem in used:
            stem += "-2"
        used.add(stem)
        child_md = f"{child_dir}/{stem}.md"
        o2 = convert_to_memory(tmp, opts, rel=f"{task['rel']}/attachments/{name}", assets_dir=f"{stem}_assets", det=det)
        if o2.result is None:
            continue
        entries.append(write_outcome(o2, opts, out_root, child_md))
        rel_link = os.path.relpath(out_root / child_md, (out_root / base_md).parent).replace(os.sep, "/")
        suffix = f" — [converti en Markdown]({quote(rel_link)})"
        out.body = re.sub(r"(\(" + re.escape(out.ctx.assets_dir + "/" + name) + r"\)[^\n]*)", lambda m, tail=suffix: m.group(1) + tail,
                          out.body, count=1)
    return entries


def run_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Traite un fichier (exécutable dans un processus fils)."""
    opts = Options(**task["opts"])
    out = convert_to_memory(Path(task["src"]), opts, rel=task["rel"], assets_dir=task["assets_dir"],
                            verbose=task.get("verbose", False))
    children: List[Dict[str, Any]] = []
    if out.result is not None and out.ctx is not None and out.result.stats.get("attachments") and not task.get("stdout"):
        try:
            children = _convert_attachments(out, opts, task)
        except Exception as exc:  # une pièce jointe illisible ne doit pas faire perdre le mail
            out.ctx.warn(f"pièces jointes : conversion interrompue ({exc})")
    entry = write_outcome(out, opts, Path(task["out_root"]), task["out_md"], write_md=not task.get("stdout"))
    if children:
        entry["_children"] = children
    if task.get("stdout") and out.result is not None:
        from .pipeline import front_matter

        entry["_stdout"] = out.body if opts.frontmatter == "none" else front_matter(out, opts, out.src) + out.body
    if task.get("compare"):
        entry["attempts"] = out.attempts
    entry["_rel"] = task["rel"]
    return entry


def _progress(i: int, n: int, e: Dict[str, Any], quiet: bool) -> None:
    if quiet:
        return
    tag = STATUS_TAG.get(e["status"], e["status"])
    extra = ""
    if e["status"] in ("error", "unsupported"):
        extra = " — " + str(e.get("error", ""))[:140].replace("\n", " ")
    else:
        bits = [e.get("format", "")]
        if e.get("words") is not None:
            bits.append(f"{e.get('words', 0)} mots")
        if e.get("score") is not None and e["score"] < 0.995:
            bits.append(f"qualité {e['score']:.2f}")
        bits.append(f"{e.get('seconds', 0):.1f} s")
        extra = " · " + " · ".join(str(b) for b in bits if b != "")
        if e.get("output"):
            extra = f" → {e['output']}" + extra
    print(f"[{i:>{len(str(n))}}/{n}] [{tag}] {e['source']}{extra}", file=sys.stderr, flush=True)


def _utf8_console() -> None:
    """Sorties standard en UTF-8 : sous Windows (ou avec LANG=C) une console cp1252 planterait sur « → », « ✓ » ou « ≈ »,
    et le Markdown envoyé sur la sortie standard (-o -) doit être en UTF-8 quelle que soit la machine."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: Optional[List[str]] = None) -> int:
    _utf8_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.doctor:
        from .doctor import run_doctor

        return run_doctor(as_json=args.json, timeout=args.timeout)
    if args.check:
        from .check import run_check

        return run_check(Path(args.check), as_json=args.json)
    if not args.inputs:
        parser.print_usage(sys.stderr)
        print("Indique au moins un fichier ou un dossier (ou --doctor).", file=sys.stderr)
        return 2

    opts = options_from_args(args)
    to_stdout = args.output == "-"
    if to_stdout and opts.images == "extract":
        opts.images = "skip"
    out_root = Path(args.output).expanduser().resolve() if args.output and not to_stdout else Path(DEFAULT_OUT).resolve()
    if to_stdout:
        out_root = Path(tempfile.mkdtemp(prefix="mdconv_out_"))
        atexit.register(shutil.rmtree, str(out_root), True)

    t0 = time.time()
    skip_dir = out_root if not args.in_place else None
    files = collect_inputs(args.inputs, args.include, args.exclude, skip_dir)
    if not files:
        print("Aucun fichier à convertir.", file=sys.stderr)
        return 1
    tmp_root = Path(tempfile.mkdtemp(prefix="mdconv_arc_"))
    atexit.register(shutil.rmtree, str(tmp_root), True)
    notes: List[Dict[str, Any]] = []
    files = expand_archives(files, opts, tmp_root, notes)
    if to_stdout and len(files) != 1:
        print("« -o - » ne convient qu'à un seul fichier.", file=sys.stderr)
        return 2
    _prepare_legacy(files, opts, tmp_root, args.quiet)

    if args.in_place:
        planned = [Planned(f, str(Path(f.src).with_suffix(".md")) if not f.origin else Path(f.rel).with_suffix(".md").as_posix(),
                           Path(f.src).stem + "_assets") for f in files]
        out_root = Path("/") if os.name != "nt" else Path(Path(files[0].src).anchor)
    else:
        planned = plan_outputs(files, flat=args.flat)
    n = len(planned)

    cache = {} if (args.force or args.compare or args.in_place) else load_cache(out_root)
    sig = options_signature(opts)
    entries: List[Dict[str, Any]] = []
    todo: List[Planned] = []
    for pl in planned:
        c = cache.get(pl.file.rel)
        if c and c.get("sig") == sig and (out_root / pl.out_md).exists() and not pl.file.origin:
            st = pl.file.src.stat()
            if c.get("size") == st.st_size and (c.get("mtime") == st.st_mtime_ns or c.get("sha") == sha256_file(pl.file.src)):
                e = dict(c["entry"])
                e["status_prev"] = e.get("status")
                e["status"] = "unchanged" if e.get("status") in ("ok", "warn", "needs_vision") else e.get("status", "ok")
                entries.append(e)
                continue
        todo.append(pl)
    skipped = len(planned) - len(todo)

    jobs = args.jobs or (min(os.cpu_count() or 1, 8) if len(todo) >= 4 else 1)
    jobs = max(1, min(jobs, len(todo) or 1))
    tasks = [{"src": str(pl.file.src), "rel": pl.file.rel, "out_md": pl.out_md, "assets_dir": pl.assets_dir,
              "opts": asdict(opts), "out_root": str(out_root), "verbose": args.verbose, "stdout": to_stdout,
              "compare": args.compare} for pl in todo]
    done = skipped
    if not args.quiet and skipped:
        print(f"{skipped} fichier(s) inchangé(s), ignoré(s) (--force pour tout reconvertir)", file=sys.stderr)
    results: List[Dict[str, Any]] = []
    if jobs == 1:
        for t in tasks:
            e = run_task(t)
            done += 1
            _progress(done, n, e, args.quiet)
            results.append(e)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(run_task, t): t for t in tasks}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    e = fut.result()
                except Exception as exc:  # plantage d'un processus fils
                    e = {"source": t["rel"], "status": "error", "error": f"{type(exc).__name__}: {exc}", "_rel": t["rel"]}
                done += 1
                _progress(done, n, e, args.quiet)
                results.append(e)
    entries.extend(results)
    for r in results:
        entries.extend(r.pop("_children", []))
    for note in notes:
        if note["status"] in ("error", "unsupported"):
            entries.append(note)
    # cache incrémental
    if not args.in_place and not args.compare:
        new_cache = {k: v for k, v in cache.items()}
        for e in results:
            if e["status"] in ("ok", "warn", "needs_vision") and e.get("output"):
                src = next((pl.file.src for pl in todo if pl.file.rel == e["_rel"]), None)
                if src is not None and not next((pl.file.origin for pl in todo if pl.file.rel == e["_rel"]), ""):
                    st = src.stat()
                    new_cache[e["_rel"]] = {"sig": sig, "size": st.st_size, "mtime": st.st_mtime_ns,
                                            "sha": sha256_file(src), "entry": {k: v for k, v in e.items() if not k.startswith("_")}}
        save_cache(out_root, new_cache)

    if to_stdout:
        text = next((e.get("_stdout") for e in results if e.get("_stdout")), "")
        sys.stdout.write(text)
        for e in results:
            if e["status"] in ("error", "unsupported"):
                print(f"[{e['status']}] {e.get('error', '')}", file=sys.stderr)
        return 0 if results and results[0]["status"] not in ("error", "unsupported") else 1

    elapsed = time.time() - t0
    real = [e for e in entries if "_rel" in e or e.get("source")]
    if args.combined or args.only_combined:
        write_combined(real, out_root, only=args.only_combined)
    if args.chunk_tokens:
        from .chunk import chunk_outputs

        chunk_outputs(real, out_root, args.chunk_tokens)
    report = write_report(real, out_root, opts, args.inputs, elapsed)
    if (len(real) > 1 or args.combined) and not args.no_index and not args.in_place:
        (out_root / "INDEX.md").write_text(build_index(real, out_root), encoding="utf-8")
    if args.compare:
        _print_compare(results)
    _summary(report, out_root, args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    bad = report["summary"]["by_status"]
    return 1 if (bad.get("error", 0) or bad.get("unsupported", 0)) and not (bad.get("ok", 0) + bad.get("unchanged", 0) + bad.get("warn", 0) + bad.get("needs_vision", 0)) else 0


def _print_compare(results: List[Dict[str, Any]]) -> None:
    """Comparatif des moteurs essayés (mode --compare) : le meilleur score est celui retenu."""
    for e in results:
        print(f"\nComparatif — {e['source']} ({e.get('format', '?')})", file=sys.stderr)
        print(f"  {'moteur':<22} {'statut':<20} {'score':>6} {'mots':>8} {'secondes':>9}", file=sys.stderr)
        for a in e.get("attempts", []):
            score = f"{a['score']:.3f}" if "score" in a else "-"
            print(f"  {a['engine']:<22} {a.get('status', ''):<20} {score:>6} {a.get('words', '-'):>8} {a.get('seconds', '-'):>9}"
                  + (f"  ({'; '.join(a['notes'])})" if a.get("notes") else "")
                  + (f"  [{a['detail'][:70]}]" if a.get("detail") else ""), file=sys.stderr)


def _summary(report: Dict[str, Any], out_root: Path, args: argparse.Namespace) -> None:
    if args.quiet:
        return
    s = report["summary"]
    by = s["by_status"]
    parts = []
    for key, label in (("ok", "converti(s)"), ("unchanged", "inchangé(s)"), ("warn", "à vérifier"),
                       ("needs_vision", "à lire visuellement"), ("unsupported", "non géré(s)"), ("error", "en échec")):
        if by.get(key):
            parts.append(f"{by[key]} {label}")
    print(f"\n{s['files']} fichier(s) : " + ", ".join(parts) + f" — {s['words']} mots, ≈ {s['tokens_est']} jetons, {s['seconds']} s",
          file=sys.stderr)
    print(f"Sortie : {out_root}", file=sys.stderr)
    vis = report.get("vision_needed") or []
    if vis:
        print(f"\nÀ TRAITER PAR LECTURE VISUELLE ({len(vis)}) :", file=sys.stderr)
        for v in vis[:30]:
            pg = f" pages {v['pages']}" if v.get("pages") else ""
            print(f"  - {v['path']}{pg} — {v['reason']}", file=sys.stderr)
        if len(vis) > 30:
            print(f"  … et {len(vis) - 30} autre(s) (voir _report.json)", file=sys.stderr)
    shots = [(e["source"], e["previews"]) for e in report["files"] if e.get("previews")]
    if shots:
        print(f"\nAperçus PNG ({sum(len(p) for _s, p in shots)} image(s)) :", file=sys.stderr)
        for src, paths in shots[:15]:
            print(f"  - {src} → {paths[0]}" + (f" … {paths[-1]}" if len(paths) > 1 else ""), file=sys.stderr)
    for e in report["files"]:
        if e["status"] in ("error", "unsupported"):
            print(f"  ✗ {e['source']} — {str(e.get('error', ''))[:200]}", file=sys.stderr)
    warns = [(e["source"], w) for e in report["files"] for w in e.get("warnings", [])]
    if warns:
        print(f"\nAvertissements ({len(warns)}) :", file=sys.stderr)
        for src, w in warns[:20]:
            print(f"  - {src} : {w}", file=sys.stderr)
        if len(warns) > 20:
            print("  … voir _report.json", file=sys.stderr)
