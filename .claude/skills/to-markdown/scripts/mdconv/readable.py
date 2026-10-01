"""RAPPORT.md : le compte rendu d'une conversion, pour un humain.

`_report.json` est complet mais fait pour les machines ; ce rapport dit en clair, fichier par fichier,
ce qui est fiable, ce qui demande une relecture et pourquoi, ce qui reste à lire visuellement ou n'a pas été converti.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .core import VERSION

THRESHOLD = 0.90


def _pct(x: Any) -> str:
    return f"{round(float(x) * 100)} %" if x is not None else "—"


def _kind(e: Dict[str, Any]) -> str:
    st = e.get("status_prev") if e.get("status") == "unchanged" else e.get("status")
    if st in ("error", "unsupported"):
        return "non_converti"
    if e.get("unread"):
        return "non_lu"
    if st == "needs_vision" or e.get("vision"):
        return "vision"
    score = e.get("score")
    if st == "warn" or (score is not None and score < THRESHOLD):
        return "relire"
    if e.get("warnings"):
        return "remarques"
    return "fiable"


def _why_relire(e: Dict[str, Any]) -> List[str]:
    why: List[str] = []
    score, recall = e.get("score"), e.get("recall")
    if recall is not None and recall < THRESHOLD:
        why.append(f"{_pct(recall)} seulement des mots de la source se retrouvent dans le Markdown : du texte a pu être perdu")
    elif score is not None and score < THRESHOLD:
        why.append(f"note de fidélité {_pct(score)} (sous le seuil de {_pct(THRESHOLD)}) : mise en page, doublons ou texte parasite probables")
    for w in e.get("warnings", []):
        why.append(w)
    return why or ["la conversion a été jugée à vérifier (voir _report.json)"]


def build_report_md(report: Dict[str, Any]) -> str:
    files = report.get("files", [])
    groups: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ("fiable", "remarques", "relire", "vision", "non_lu", "non_converti")}
    for e in files:
        groups[_kind(e)].append(e)
    s = report.get("summary", {})
    out: List[str] = ["# Rapport de conversion", ""]
    out.append(f"_{s.get('files', len(files))} fichier(s) · {s.get('words', 0):,} mots · ≈ {s.get('tokens_est', 0):,} jetons · "
               f"mdconv {VERSION} · {report.get('generated_at', '')[:16].replace('T', ' ')}_".replace(",", " "))
    out.append("")
    ok = len(groups["fiable"]) + len(groups["remarques"])
    todo = len(groups["relire"]) + len(groups["vision"]) + len(groups["non_converti"]) + len(groups["non_lu"])
    if not todo:
        out.append(f"**Tout est exploitable : {ok} fichier(s) fiable(s), rien à relire.**")
    else:
        out.append(f"**{ok} fichier(s) fiable(s) · {todo} à traiter** (relecture, lecture visuelle ou conversion impossible) — détail ci-dessous.")
    out += ["", "> **Fidélité** = part des mots du fichier d'origine retrouvés dans le Markdown, après contrôle de bruit et de doublons. "
            "Elle mesure le *texte*, pas la mise en page : tableaux et schémas se vérifient à l'œil quand ils comptent.", ""]

    def table(rows: List[Dict[str, Any]], extra: str = "") -> None:
        out.append("| Fichier | Markdown | Format | Moteur | Fidélité | Mots |")
        out.append("| --- | --- | --- | --- | ---: | ---: |")
        for e in rows:
            md = e.get("output")
            out.append(f"| {e['source']} | {('`' + md + '`') if md else '—'} | {e.get('format', '')} | {e.get('engine', '—')} | "
                       f"{_pct(e.get('score'))} | {int(e.get('words', 0))} |")
        out.append("")

    if groups["non_converti"]:
        out += ["## ❌ Non convertis", ""]
        for e in groups["non_converti"]:
            out.append(f"- **{e['source']}** ({e.get('format', '?')}) — {e.get('error', e.get('status'))}")
        out.append("")
    if groups["vision"]:
        out += ["## 👁 À lire visuellement", "",
                "Ces passages n'ont pas pu être extraits par un script (scans, schémas, images) : un marqueur `[À COMPLÉTER]` les signale dans le `.md`.", ""]
        for e in groups["vision"]:
            out.append(f"- **{e['source']}** → `{e.get('output', '')}`")
            for v in e.get("vision", []):
                pg = f", pages {v['pages']}" if v.get("pages") else ""
                out.append(f"  - {v['reason']}{pg}")
        out.append("")
    if groups["non_lu"]:
        out += ["## 🔒 Non lus volontairement (`--no-vision`)", "",
                "La lecture visuelle était désactivée : ces éléments non textuels sont marqués `NON LU` dans le `.md` et n'ont été vus par personne.", ""]
        for e in groups["non_lu"]:
            out.append(f"- **{e['source']}** — " + " ; ".join(sorted({u["reason"] for u in e.get("unread", [])})))
        out.append("")
    if groups["relire"]:
        out += ["## 🔎 À relire", ""]
        for e in groups["relire"]:
            out.append(f"- **{e['source']}** → `{e.get('output', '')}` (moteur {e.get('engine', '—')}, fidélité {_pct(e.get('score'))})")
            for w in _why_relire(e):
                out.append(f"  - {w}")
        out.append("")
    if groups["remarques"]:
        out += ["## ✅ Fiables, avec remarques", ""]
        for e in groups["remarques"]:
            out.append(f"- **{e['source']}** → `{e.get('output', '')}` (fidélité {_pct(e.get('score'))})")
            for w in e.get("warnings", []):
                out.append(f"  - {w}")
        out.append("")
    if groups["fiable"]:
        out += ["## ✅ Fiables", ""]
        table(groups["fiable"])
    out.append("_Détail technique : `_report.json` · liens et statuts : `INDEX.md`._")
    return "\n".join(out) + "\n"
