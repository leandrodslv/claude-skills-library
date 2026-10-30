"""Lance le skill sur chaque cas extrême, mesure temps / mémoire, vérifie les attentes.

usage : python3 run_extreme.py [CORPUS [SORTIE]] [--only PREFIXE] [--report FICHIER.md] [--extra ARGS_DU_CLI...]
        (défauts : benchmark/extreme/_corpus et benchmark/extreme/_runs ; le corpus se crée avec gen_extreme.py)

Chaque cas passe par la vraie ligne de commande (processus séparé, plafond de temps et de mémoire). Un cas échoue
sur : plantage non rattrapé, dépassement de temps ou de mémoire, statut inattendu, repère de contenu absent (sauf
troncature signalée), contenu interdit présent (secret d'une attaque XXE…), clôtures ``` déséquilibrées,
écriture hors du dossier de sortie. Code de sortie 1 s'il y a au moins un échec.
"""
import json
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = str(HERE.parents[1])
_argv = sys.argv[1:]
extra = _argv[_argv.index("--extra") + 1:] if "--extra" in _argv else []
_argv = _argv[:_argv.index("--extra")] if "--extra" in _argv else _argv
only = _argv[_argv.index("--only") + 1] if "--only" in _argv else ""
report_md = _argv[_argv.index("--report") + 1] if "--report" in _argv else ""
_pos = [a for i, a in enumerate(_argv) if not a.startswith("--") and (i == 0 or _argv[i - 1] not in ("--only", "--report"))]
corpus = Path(_pos[0]) if _pos else HERE / "_corpus"
outroot = Path(_pos[1]) if len(_pos) > 1 else HERE / "_runs"
cases = json.loads((corpus / "cases.json").read_text(encoding="utf-8"))
shutil.rmtree(outroot, ignore_errors=True)
outroot.mkdir(parents=True)
for stray in Path("/tmp").glob("EVIL-B5*"):
    stray.unlink()


def run(cmd, timeout, mem_limit_mb):
    def pre():
        os.setsid()
        lim = (mem_limit_mb + 1500) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    with open(cmd["stdout"], "wb") as so, open(cmd["stderr"], "wb") as se:
        p = subprocess.Popen(cmd["argv"], stdout=so, stderr=se, preexec_fn=pre, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        t0 = time.time()
        while True:
            pid, status, ru = os.wait4(p.pid, os.WNOHANG)
            if pid:
                return time.time() - t0, status, ru.ru_maxrss / 1024, False
            if time.time() - t0 > timeout:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, ru = os.wait4(p.pid, 0)
                return time.time() - t0, status, ru.ru_maxrss / 1024, True
            time.sleep(0.05)


def fence_balanced(text):
    open_len = 0
    for ln in text.splitlines():
        m = re.match(r"^ {0,3}(`{3,}|~{3,})", ln)
        if m:
            n = len(m.group(1))
            if not open_len:
                open_len = n
            elif n >= open_len and ln.strip().strip("`~") == "":
                open_len = 0
    return open_len == 0


results = []
for c in cases:
    if only and not c["id"].startswith(only):
        continue
    cid = re.sub(r"[^A-Za-z0-9]+", "_", c["id"])[:60]
    out = outroot / cid
    argv = [sys.executable, "-I", f"{SKILL}/scripts/convert.py", str(corpus / c["input"]), "-o", str(out), "--no-vision"] + extra
    secs, status, rss, timed_out = run(dict(argv=argv, stdout=outroot / f"{cid}.out", stderr=outroot / f"{cid}.err"), c["max_s"] * 2, c["max_mb"])
    stderr = (outroot / f"{cid}.err").read_text(errors="replace")
    stdout = (outroot / f"{cid}.out").read_text(errors="replace")
    rep = {}
    try:
        rep = json.loads((out / "_report.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    files = rep.get("files", [])
    statuses = sorted({f.get("status") for f in files}) or ["(aucun rapport)"]
    warns = [w for f in files for w in f.get("warnings", [])] + [w for f in files for w in f.get("errors", []) if isinstance(w, str)]
    md = ""
    if out.exists():
        for p in sorted(out.rglob("*.md")):
            if p.name not in ("INDEX.md", "RAPPORT.md"):
                md += p.read_text(encoding="utf-8", errors="replace") + "\n"
    problems = []
    notes = []
    if timed_out:
        problems.append(f"TIMEOUT (> {c['max_s'] * 2} s)")
    sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else 0
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -sig
    if sig and not timed_out:
        problems.append(f"TUÉ par signal {sig} (mémoire ?)")
    crashed = ("Traceback (most recent call last)" in stderr + stdout) and not rep
    if crashed:
        problems.append("PLANTAGE : traceback sans rapport produit (le lot entier est perdu)")
    elif "Traceback (most recent call last)" in stderr + stdout:
        notes.append("traceback d'un moteur externe cité dans le message d'erreur (rattrapé)")
    if "MemoryError" in stderr + stdout:
        problems.append("MemoryError")
    if rss > c["max_mb"]:
        problems.append(f"MÉMOIRE {rss:.0f} Mo > {c['max_mb']}")
    if secs > c["max_s"] and not timed_out:
        problems.append(f"LENT {secs:.0f} s > {c['max_s']}")
    bad_status = [s for s in statuses if s not in c["ok"] and s != "(aucun rapport)"]
    if bad_status:
        problems.append(f"statut inattendu {bad_status}")
    if statuses == ["(aucun rapport)"] and not timed_out and not sig:
        problems.append("aucun rapport produit")
    missing = [e for e in c["expect"] if not re.search(e, md)]
    if c.get("soft") and statuses and set(statuses) <= {"error", "unsupported"}:
        missing = []          # refus propre accepté (cas « lire OU refuser ») ; le message est vérifié ci-dessous
        if not any("imbrication" in str(a.get("detail", "")) or "profondeur" in str(a.get("detail", "")) for f in files for a in f.get("attempts", [])):
            problems.append("refus sans message d'imbrication trop profonde")
    truncated_flag = bool(re.search(r"tronqu|plafon|limit|partiel|coupé|omis|ignoré|au-delà|trop (grand|gros|volumineu)", " ".join(warns) + md + stdout, re.I))
    if missing:
        if c.get("flag_truncation") and truncated_flag:
            notes.append(f"contenu borné ET signalé ({len(missing)} repère(s) absent(s))")
        else:
            problems.append(f"repères absents : {missing}")
    for f in c["forbid"]:
        if re.search(f, md):
            problems.append(f"INTERDIT présent : {f!r}")
    if md and not fence_balanced(md):
        problems.append("clôtures ``` déséquilibrées")
    if c["id"].startswith("B5") and list(Path("/tmp").glob("EVIL-B5*")):
        problems.append("ÉCRITURE HORS SORTIE (traversée de chemin réussie)")
    verdict = "PASS" if not problems else "FAIL"
    results.append(dict(id=c["id"], verdict=verdict, secs=round(secs, 1), rss=round(rss), statuses=statuses, words=sum(f.get("words", 0) for f in files),
                        problems=problems, notes=notes, warns=warns[:4], note=c.get("note", ""), stderr=stderr.strip()[-300:]))
    print(f"[{verdict}] {c['id']:<58} {secs:6.1f}s {rss:6.0f}Mo {','.join(statuses)}" + (f"  <- {'; '.join(problems)}" if problems else ""), flush=True)

(outroot / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
n_fail = sum(r["verdict"] == "FAIL" for r in results)
print(f"\n{len(results) - n_fail} PASS / {n_fail} FAIL sur {len(results)}")
if report_md:
    lines = ["# Batterie « cas extrêmes » — résultats", "", f"{len(results) - n_fail} réussis / {n_fail} échecs sur {len(results)} cas "
             f"(plus long : {max((r['secs'] for r in results), default=0)} s ; pic mémoire : {max((r['rss'] for r in results), default=0)} Mo).", "",
             "| Verdict | Cas | Temps | Mémoire | Statut | Remarques |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['verdict']} | {r['id']} | {r['secs']} s | {r['rss']} Mo | {','.join(r['statuses'])} | {'; '.join(r['problems'] + r['notes']).replace('|', '/')} |")
    Path(report_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
sys.exit(1 if n_fail else 0)
