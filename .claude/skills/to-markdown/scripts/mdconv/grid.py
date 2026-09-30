"""Grilles de cellules (feuilles de calcul) → blocs de tableaux Markdown, partagé par XLSX, ODS, XLS, CSV."""
from __future__ import annotations

from typing import Dict, List

from .core import Ctx
from .util import md_table, slugify


def grid_blocks(ctx: Ctx, rows: Dict[int, Dict[int, str]], sheet: str, csv_text: str, total_rows: int) -> List[str]:
    """Découpe une feuille en blocs séparés par des lignes vides ; un bloc = un tableau GFM.

    Une cellule isolée devient un titre/une note. Au-delà de ``table_rows`` lignes, le tableau est
    tronqué et, si ``csv_text`` est fourni, la feuille complète est jointe en CSV annexe.
    """
    keys = sorted(rows)
    groups: List[List[int]] = []
    cur: List[int] = [keys[0]]
    for k in keys[1:]:
        if k == cur[-1] + 1:
            cur.append(k)
        else:
            groups.append(cur)
            cur = [k]
    groups.append(cur)
    out: List[str] = []
    cap = ctx.opts.table_rows
    truncated_any = False
    for gi, g in enumerate(groups):
        block = {r: rows[r] for r in g}
        cols = sorted({c for r in block.values() for c in r})
        c0, c1 = cols[0], cols[-1]
        n_nonempty = sum(len(r) for r in block.values())
        if n_nonempty == 1 and len(g) == 1:  # une seule cellule : titre / note
            text = next(iter(block[g[0]].values()))
            out.append(f"**{text}**" if gi == 0 and not text.startswith("**") else text)
            continue
        if len(cols) == 1 and len(g) <= 3 and all(len(r) == 1 for r in block.values()) and n_nonempty <= 3:
            out.append("\n\n".join(next(iter(block[r].values())) for r in g))
            continue
        grid = [[block[r].get(c, "") for c in range(c0, c1 + 1)] for r in g]
        if cap and len(grid) - 1 > cap:
            extra = len(grid) - 1 - cap
            grid = grid[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (len(grid[0]) - 1)]
            truncated_any = True
        out.append(md_table(grid))
    if truncated_any:
        if csv_text:
            link = ctx.add_file(f"{slugify(sheet)}.csv", csv_text.encode("utf-8"))
            out.append(f"_Tableau tronqué dans ce fichier ({total_rows} lignes au total) — données complètes : [{link.rsplit('/', 1)[-1]}]({link})_")
        else:
            out.append(f"_Tableau tronqué ({total_rows} lignes au total)._")
    return out
