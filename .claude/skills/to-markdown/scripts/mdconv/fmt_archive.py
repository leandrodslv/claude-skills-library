"""Archives (zip, tar, tgz, gz, bz2, xz) : extraction sûre, le CLI convertit ensuite chaque membre."""
from __future__ import annotations

import bz2
import gzip
import lzma
import posixpath
import tarfile
import zipfile
from pathlib import Path
from typing import List, Tuple

from .core import Ctx, Result, Unsupported, engine
from .util import UnsafeArchive

MAX_MEMBERS = 20_000
MAX_TOTAL = 2 << 30
MAX_MEMBER = 512 << 20


def _safe_name(name: str) -> str:
    name = name.replace("\\", "/")
    parts = [p for p in posixpath.normpath("/" + name).split("/") if p not in ("", ".", "..")]
    return "/".join(parts)


def _copy_limited(src, dest: Path, budget: List[int]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(dest, "wb") as out:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            written += len(chunk)
            budget[0] += len(chunk)
            if written > MAX_MEMBER or budget[0] > MAX_TOTAL:
                raise UnsafeArchive("archive trop volumineuse une fois décompressée (protection zip bomb)")
            out.write(chunk)


def expand_archive(path: Path, fmt: str, dest: Path) -> List[Tuple[str, Path]]:
    """Extrait l'archive dans ``dest`` ; renvoie [(chemin relatif, fichier extrait)]."""
    dest.mkdir(parents=True, exist_ok=True)
    budget = [0]
    out: List[Tuple[str, Path]] = []
    if fmt == "zip":
        with zipfile.ZipFile(path) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > MAX_MEMBERS:
                raise UnsafeArchive(f"trop de membres ({len(infos)})")
            for info in infos:
                name = _safe_name(info.filename)
                if not name or info.flag_bits & 0x1:  # chiffré
                    continue
                target = dest / name
                with zf.open(info) as src:
                    _copy_limited(src, target, budget)
                out.append((name, target))
    elif fmt in ("tar", "tgz", "tbz2", "txz") or (fmt in ("gz", "bz2", "xz") and _is_tar(path, fmt)):
        with tarfile.open(path) as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            if len(members) > MAX_MEMBERS:
                raise UnsafeArchive(f"trop de membres ({len(members)})")
            for m in members:
                name = _safe_name(m.name)
                if not name:
                    continue
                src = tf.extractfile(m)
                if src is None:
                    continue
                target = dest / name
                _copy_limited(src, target, budget)
                out.append((name, target))
    elif fmt in ("gz", "bz2", "xz"):
        opener = {"gz": gzip.open, "bz2": bz2.open, "xz": lzma.open}[fmt]
        if path.suffix.lower() == ".svgz":
            name = path.name[:-1]  # .svgz → .svg
        else:
            name = path.name[: -len(path.suffix)] if path.suffix else path.name + ".out"
        target = dest / (_safe_name(name) or "contenu")
        with opener(path, "rb") as src:
            _copy_limited(src, target, budget)
        out.append((target.name, target))
    return out


def _is_tar(path: Path, fmt: str) -> bool:
    try:
        return tarfile.is_tarfile(path)
    except Exception:
        return False


@engine(["zip", "tar", "gz", "bz2", "xz"], name="archive", prio=99)
def archive_placeholder(path, ctx: Ctx) -> Result:
    raise Unsupported("archive : les membres sont convertis un par un par le CLI (convert.py)",
                      hint="lancer convert.py sur l'archive, pas la bibliothèque seule")
