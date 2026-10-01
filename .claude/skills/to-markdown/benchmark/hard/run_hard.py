#!/usr/bin/env python3
"""Passe la batterie de documents difficiles dans mdconv (et les concurrents installés) et dit où ça casse.

    python3 benchmark/hard/run_hard.py                    # tout, écrit HARD_RESULTS.md
    python3 benchmark/hard/run_hard.py --only docx-       # documents dont l'identifiant commence ainsi
    python3 benchmark/hard/run_hard.py --show docx-zone-texte-entete     # affiche la sortie de chaque convertisseur
    python3 benchmark/hard/run_hard.py --dump sorties/    # garde les Markdown produits pour les relire
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "scripts"))

import metrics  # noqa: E402
import run as bench  # noqa: E402


def _n(s: str) -> str:
    return " ".join(metrics.tokens(s))


def _count(hay: str, needle: str) -> int:
    n = _n(needle)
    return hay.count(n) if n else 0


def evaluate(case: Dict[str, Any], out: str, status: str, flagged_vision: bool, error: Optional[str]) -> Dict[str, Any]:
    """Note une sortie par rapport aux attentes du manifeste."""
    text = metrics.strip_front_matter(out)
    norm = _n(text)
    problems: List[str] = []
    checks = 0
    ok = 0

    def tally(passed: bool, msg: str) -> None:
        nonlocal checks, ok
        checks += 1
        ok += passed
        if not passed:
            problems.append(msg)

    for m in case.get("must", []):
        tally(_n(m) in norm, f"texte absent : « {m[:60]} »")
    for group in case.get("any_of", []):
        tally(any(_n(v) in norm for v in group), f"aucune variante trouvée : {' | '.join(group)[:60]}")
    pos = -1
    in_order = True
    for o in case.get("order", []):
        i = norm.find(_n(o), pos + 1)
        if i < 0:
            in_order = False
            tally(False, f"ordre de lecture : « {o[:40]} » absent ou après son suivant")
            break
        pos = i
    if case.get("order") and in_order:
        tally(True, "")
    for a in case.get("absent", []):
        tally(_n(a) not in norm, f"texte à exclure présent : « {a[:60]} »")
    for o in case.get("once", []):
        c = _count(norm, o)
        tally(c == 1, f"« {o[:50]} » apparaît {c} fois (attendu : 1)")
    for t, mx in case.get("at_most", {}).items():
        c = _count(norm, t)
        tally(c <= mx, f"« {t[:50]} » répété {c} fois (max {mx})")
    table_lines = [_n(ln) for ln in text.splitlines() if ln.lstrip().startswith("|")]
    for row in case.get("rows", []):
        def in_one_line(line: str, cells: List[str] = row) -> bool:
            at = -1
            for c in cells:
                at = line.find(_n(c), at + 1)
                if at < 0:
                    return False
            return True
        tally(any(in_one_line(ln) for ln in table_lines), f"ligne de tableau éclatée ou mal alignée : {' | '.join(row)[:60]}")
    if case.get("levels"):
        indent: Dict[str, int] = {}
        for ln in text.splitlines():
            m = re.match(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$", ln)
            if m:
                indent.setdefault(_n(m.group(2))[:60], len(m.group(1)))
        got: List[Tuple[int, int]] = []
        for t, lv in case["levels"]:
            key = next((k for k in indent if _n(t) and _n(t)[:30] in k), None)
            if key is not None:
                got.append((int(lv), indent[key]))
        consistent = len(got) == len(case["levels"]) and all(
            (lb > la) == (ib > ia) and (lb == la) == (ib == ia) for (la, ia), (lb, ib) in zip(got, got[1:]))
        tally(consistent, "imbrication des listes perdue (l'indentation ne suit pas les niveaux)")
    struct: Dict[str, Optional[float]] = {
        "titres": metrics.headings_score(case.get("headings", []), text),
        "tableaux": metrics.cells_score(case.get("cells", []), text),
        "listes": metrics.items_score(case.get("items", []), text),
        "liens": metrics.links_score([tuple(x) for x in case.get("links", [])], text),
    }
    for k, v in struct.items():
        if v is not None:
            tally(v >= 99.9, f"{k} : {v:.0f} % retrouvés comme structure Markdown")
    score = 100.0 * ok / checks if checks else 100.0
    expect = case.get("expect", "ok")
    if expect == "error":
        verdict = "ok" if (error or status in ("error", "unsupported")) else "ko"
        problems = [] if verdict == "ok" else ["devait échouer proprement (message clair), mais a produit une sortie"]
        score = 100.0 if verdict == "ok" else 0.0
    elif expect == "vision":
        found = _n(" ".join(case.get("must", []))) in norm if case.get("must") else False
        got_text = ok >= 0.9 * checks if checks else False
        if got_text:
            verdict, note = "ok", ""
        elif flagged_vision:
            verdict, note = "vision", "contenu non extrait mais signalé à lire visuellement (comportement attendu)"
            score = max(score, 0.0)
        else:
            verdict, note = "ko", "contenu perdu SANS signalement (aucun marqueur de lecture visuelle)"
        if note:
            problems.insert(0, note)
        _ = found
    else:
        verdict = "ok" if score >= 95 else "partiel" if score >= 70 else "ko"
    if error and expect != "error":
        verdict, score = "ko", 0.0
        problems = [f"erreur : {error[:100]}"]
    return {"score": round(score, 1), "verdict": verdict, "problems": problems, "structure": struct, "words": len(metrics.tokens(text))}


def run_mdconv(path: Path, external: bool) -> Tuple[str, str, bool, Optional[str], float]:
    from mdconv.core import Options
    from mdconv.pipeline import convert_to_memory

    t0 = time.perf_counter()
    if path.suffix.lower() in (".zip", ".tar", ".gz", ".tgz"):          # les archives sont dépliées par la ligne de commande, pas par convert_to_memory
        return _run_cli(path, external, t0)
    opts = Options(frontmatter="none", images="skip", external=external)
    out = convert_to_memory(path, opts, rel=path.name, assets_dir="a")
    dt = time.perf_counter() - t0
    err = out.error if out.status in ("error", "unsupported") else None
    return (out.body if out.result else ""), out.status, bool(out.ctx and out.ctx.vision), err, dt


def _run_cli(path: Path, external: bool, t0: float) -> Tuple[str, str, bool, Optional[str], float]:
    import contextlib
    import io
    import tempfile

    from mdconv.cli import main as cli_main

    with tempfile.TemporaryDirectory() as tmp:
        argv = [str(path), "-o", tmp, "-q", "--frontmatter", "none", "--images", "skip"] + ([] if external else ["--no-external"])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cli_main(argv)
        texts = [p.read_text(encoding="utf-8") for p in sorted(Path(tmp).rglob("*.md")) if p.name not in ("INDEX.md", "RAPPORT.md")]
        rep = Path(tmp) / "_report.json"
        report = json.loads(rep.read_text(encoding="utf-8")) if rep.exists() else {}
        vis = bool(report.get("vision_needed"))
    status = "ok" if texts else "error"
    return "\n\n".join(texts), status, vis, (None if texts else f"code {rc}"), time.perf_counter() - t0


def run_other(runner, path: Path) -> Tuple[str, str, bool, Optional[str], float]:
    t0 = time.perf_counter()
    try:
        out = runner(path)
        return out, "ok", False, None, time.perf_counter() - t0
    except Exception as exc:  # noqa: BLE001
        if "Unknown input format" in str(exc):
            return "", "skip", False, None, 0.0
        return "", "error", False, f"{type(exc).__name__}: {str(exc)[:100]}", time.perf_counter() - t0


ICON = {"ok": "✅", "partiel": "⚠️", "ko": "❌", "vision": "👁"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Batterie de documents difficiles : où mdconv (et les autres) cassent-ils ?")
    ap.add_argument("--only", help="préfixe d'identifiant (ex. docx-, pdf-scan)")
    ap.add_argument("--converters", default="mdconv-natif,mdconv-auto,markitdown,pandoc,pymupdf4llm", help="liste séparée par des virgules")
    ap.add_argument("--show", metavar="ID", help="affiche la sortie de chaque convertisseur pour ce document")
    ap.add_argument("--dump", metavar="DOSSIER", help="écrit les Markdown produits")
    ap.add_argument("--out", default=str(HERE / "HARD_RESULTS.md"))
    a = ap.parse_args(argv)
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    if a.only:
        manifest = [c for c in manifest if c["id"].startswith(a.only)]
    if a.show:
        manifest = [c for c in manifest if c["id"] == a.show]
    available = bench.converters()
    names = [n for n in a.converters.split(",") if n in available and available[n][0] is not None]
    results: List[Dict[str, Any]] = []
    for c in manifest:
        path = HERE / "corpus" / c["path"]
        if not path.exists():
            continue
        fmt = path.suffix.lstrip(".").lower()
        row: Dict[str, Any] = {"case": c, "res": {}}
        for n in names:
            runner, fmts, _d = available[n]
            if n.startswith("mdconv"):
                out, status, vis, err, dt = run_mdconv(path, n == "mdconv-auto")
            else:
                if fmts and fmt not in fmts:
                    continue
                out, status, vis, err, dt = run_other(runner, path)
            if status == "skip":
                continue
            ev = evaluate(c, out, status, vis, err)
            ev["seconds"] = round(dt, 2)
            row["res"][n] = ev
            if a.dump:
                d = Path(a.dump) / n
                d.mkdir(parents=True, exist_ok=True)
                (d / (c["id"] + ".md")).write_text(out, encoding="utf-8")
            if a.show:
                print(f"\n===== {n} ({ev['verdict']}, {ev['score']}) =====\n{out[:4000]}\n--- problèmes : {ev['problems']}")
        results.append(row)
        line = "  ".join(f"{n.split('-')[-1] if n.startswith('mdconv') else n}:{ICON[r['verdict']]}{r['score']:.0f}" for n, r in row["res"].items())
        print(f"{c['id']:42s} {line}", file=sys.stderr)
    if a.show:
        return 0
    Path(a.out).write_text(render(results, names), encoding="utf-8")
    print(f"Résultats : {a.out}", file=sys.stderr)
    return 0


def render(results: List[Dict[str, Any]], names: List[str]) -> str:
    md = [n for n in names if n.startswith("mdconv")]
    out = ["# Batterie de documents difficiles — résultats", "",
           f"_{len(results)} documents · généré par `benchmark/hard/run_hard.py` · voir [README](README.md) pour la méthode_", "",
           "✅ conforme (≥ 95 % des attentes) · ⚠️ partiel (70-95 %) · ❌ échec · 👁 contenu non extrait **mais signalé** à lire visuellement. "
           "Le score est la part des vérifications réussies (texte, ordre, doublons, bruit, structure).", ""]
    # synthèse par convertisseur
    out += ["## Synthèse", "", "| Convertisseur | ✅ | ⚠️ | ❌ | 👁 | Score moyen |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for n in names:
        rs = [r["res"][n] for r in results if n in r["res"]]
        if not rs:
            continue
        cnt = {k: sum(1 for r in rs if r["verdict"] == k) for k in ICON}
        out.append(f"| **{n}** ({len(rs)} docs) | {cnt['ok']} | {cnt['partiel']} | {cnt['ko']} | {cnt['vision']} | {sum(r['score'] for r in rs) / len(rs):.0f} |")
    # par catégorie, mdconv-auto
    out += ["", "## Document par document", "", "| Document | Difficulté | " + " | ".join(names) + " |", "| --- | :---: | " + " | ".join("---:" for _ in names) + " |"]
    for r in sorted(results, key=lambda r: (r["case"]["category"], r["case"]["id"])):
        c = r["case"]
        cells = [(f"{ICON[r['res'][n]['verdict']]} {r['res'][n]['score']:.0f}" if n in r["res"] else "—") for n in names]
        out.append(f"| `{c['id']}` | {'●' * c['difficulty']} | " + " | ".join(cells) + " |")
    # limites de mdconv
    out += ["", "## Limites constatées de mdconv", "", "Documents où `mdconv-auto` n'est pas ✅, avec ce qui manque (à améliorer en priorité) :", ""]
    any_limit = False
    for r in sorted(results, key=lambda r: (r["res"].get("mdconv-auto", r["res"].get(md[0], {"score": 100})) or {"score": 100})["score"] if md else 0):
        res = r["res"].get("mdconv-auto") or (r["res"].get(md[0]) if md else None)
        if not res or res["verdict"] == "ok":
            continue
        any_limit = True
        c = r["case"]
        others = ", ".join(f"{n} {ICON[x['verdict']]}{x['score']:.0f}" for n, x in r["res"].items() if not n.startswith("mdconv"))
        out += [f"### `{c['id']}` — {ICON[res['verdict']]} {res['score']:.0f} %", "", f"**Difficulté :** {c['challenge']}", ""]
        out += [f"- {p}" for p in res["problems"][:8]]
        if others:
            out += ["", f"_Autres convertisseurs : {others}_"]
        if c.get("notes"):
            out += ["", f"_{c['notes']}_"]
        out.append("")
    if not any_limit:
        out.append("Aucune limite constatée sur cette batterie.")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.exit(main())
