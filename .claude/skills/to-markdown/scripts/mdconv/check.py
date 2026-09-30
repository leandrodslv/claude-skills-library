"""`convert.py --check DOSSIER` : vérifie un dossier de Markdown converti (et ce qu'il reste à faire)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote
from typing import Any, Dict, List

from .quality import lint_markdown
from .util import est_tokens, words

VISION_MARK = "[À COMPLÉTER"
_LINK = re.compile(r"(?<!\\)!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def check_file(path: Path, root: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    issues: List[str] = []
    if not body.strip():
        issues.append("fichier vide")
    todo = body.count(VISION_MARK)
    if todo:
        issues.append(f"{todo} passage(s) à décrire par lecture visuelle non traité(s)")
    broken = []
    in_fence = False
    for line in body.split("\n"):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
        if in_fence:
            continue
        for m in _LINK.finditer(line):
            target = m.group(1).strip("<>")
            if re.match(r"^(https?:|mailto:|tel:|#|data:|ftp:)", target, re.I):
                continue
            rel = unquote(target.split("#")[0])
            if rel and not (path.parent / rel).exists():
                broken.append(target)
    if broken:
        issues.append(f"{len(broken)} lien(s)/image(s) local(aux) introuvable(s) : {', '.join(broken[:3])}")
    bad = body.count("�") + len(re.findall(r"\(cid:\d+\)", body))
    if bad:
        issues.append(f"{bad} caractère(s) illisible(s) (� ou (cid:…))")
    issues += lint_markdown(body)
    return {"file": path.relative_to(root).as_posix(), "words": len(words(body)), "tokens": est_tokens(body),
            "todo_vision": todo, "issues": issues}


def run_check(root: Path, as_json: bool = False) -> int:
    root = root.resolve()
    if not root.is_dir():
        print(f"Dossier introuvable : {root}", file=sys.stderr)
        return 2
    files = [p for p in sorted(root.rglob("*.md")) if p.name not in ("INDEX.md",) and "_chunks" not in p.parts]
    results = [check_file(p, root) for p in files]
    report_ok = True
    rp = root / "_report.json"
    pending_vision = 0
    if rp.exists():
        try:
            rep = json.loads(rp.read_text(encoding="utf-8"))
            pending_vision = len(rep.get("vision_needed", []))
        except ValueError:
            report_ok = False
    problems = [r for r in results if r["issues"]]
    if as_json:
        print(json.dumps({"files": results, "with_issues": len(problems), "report_readable": report_ok}, ensure_ascii=False, indent=2))
    else:
        total_tokens = sum(r["tokens"] for r in results)
        print(f"{len(results)} fichier(s) Markdown · {sum(r['words'] for r in results)} mots · ≈ {total_tokens} jetons")
        for r in problems:
            print(f"  ✗ {r['file']}")
            for i in r["issues"]:
                print(f"      - {i}")
        if not problems:
            print("  ✓ aucun problème détecté")
        elif pending_vision:
            print(f"\n{pending_vision} élément(s) de lecture visuelle listé(s) dans _report.json.")
    return 1 if problems else 0
