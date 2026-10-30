"""Compare les moteurs PDF du skill sur des PDF RÉELS que vous fournissez (rien de tiers n'est versionné).

usage : python3 benchmark/compare_pdf_engines.py FICHIER.pdf [...] [--engines pdftotext,pdflite] [--truth pypdfium2|pdfminer|none]

Pour chaque PDF et chaque moteur : mots, rappel et précision du texte face à une extraction INDÉPENDANTE
(pypdfium2 ou pdfminer s'ils sont installés, sinon face au texte brut de pdftotext -raw), nombre de titres,
de lignes de tableau, bruit (lignes de 1-2 caractères, lignes répétées), ordre de lecture (part des couples de mots
consécutifs de la référence retrouvés : un texte à deux colonnes entremêlées garde ses mots mais perd cette part), durée.
Sert à décider de l'ordre des moteurs (references/engines.md) : le natif ne passe devant que s'il est au moins aussi
fidèle en texte.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "scripts"), str(HERE)]

from metrics import recall_precision, tokens  # noqa: E402

from mdconv.core import Options  # noqa: E402
from mdconv.pipeline import convert_to_memory  # noqa: E402


def truth_text(pdf: Path, kind: str) -> tuple:
    if kind in ("auto", "pypdfium2"):
        try:
            import pypdfium2 as pdfium  # type: ignore

            doc = pdfium.PdfDocument(str(pdf))
            return "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))), "pypdfium2"
        except Exception:
            pass
    if kind in ("auto", "pdfminer"):
        try:
            from pdfminer.high_level import extract_text  # type: ignore

            return extract_text(str(pdf)), "pdfminer"
        except Exception:
            pass
    out = subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, timeout=300)
    return out.stdout.decode("utf-8", "replace"), "pdftotext -raw (non indépendant)"


def order_score(truth: str, md: str) -> float:
    """Part (en %) des couples de mots consécutifs de la référence qu'on retrouve dans le Markdown (multiensembles)."""
    from collections import Counter

    def pairs(text):
        w = tokens(text)
        return Counter(zip(w, w[1:]))
    t, o = pairs(truth), pairs(md)
    return 100.0 * sum((t & o).values()) / max(sum(t.values()), 1)


def stats(md: str) -> dict:
    lines = [ln for ln in md.splitlines() if ln.strip()]
    short = sum(1 for ln in lines if len(ln.strip()) <= 2 and not ln.startswith("#"))
    dup = sum(1 for a, b in zip(lines, lines[1:]) if a == b)
    return {"titres": sum(1 for ln in lines if re.match(r"^#{1,6} ", ln)),
            "lignes_tableau": sum(1 for ln in lines if ln.lstrip().startswith("|")),
            "bruit": short + dup, "lignes": len(lines)}


def main(argv) -> int:
    engines = ["pdftotext", "pdflite"]
    truth_kind = "auto"
    files = []
    it = iter(argv)
    for a in it:
        if a == "--engines":
            engines = next(it).split(",")
        elif a == "--truth":
            truth_kind = next(it)
        else:
            files.append(Path(a))
    if not files:
        print(__doc__)
        return 2
    print(f"{'PDF':<28}{'moteur':<11}{'mots':>7}{'rappel':>8}{'précis.':>9}{'ordre':>7}{'titres':>8}{'tab.':>6}{'bruit':>7}{'s':>7}")
    for pdf in files:
        truth, src = truth_text(pdf, truth_kind)
        for eng in engines:
            t0 = time.time()
            out = convert_to_memory(pdf, Options(engines=[eng], external=eng != "pdflite", frontmatter="none"), rel=pdf.name)
            if out.status in ("error", "unsupported"):
                print(f"{pdf.name[:27]:<28}{eng:<11}  ÉCHEC : {out.error[:80]}")
                continue
            rec, prec = recall_precision(truth, out.body)
            s = stats(out.body)
            print(f"{pdf.name[:27]:<28}{eng:<11}{len(out.body.split()):>7}{rec:>7.1f}%{prec:>8.1f}%{order_score(truth, out.body):>6.1f}%{s['titres']:>8}{s['lignes_tableau']:>6}{s['bruit']:>7}{time.time() - t0:>7.1f}")
        print(f"{'':<28}(référence de texte : {src})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
