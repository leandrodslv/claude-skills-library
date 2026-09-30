"""Base commune des tests : chemins, options déterministes (noyau natif seul), utilitaires d'assertion."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))

from mdconv.core import Options  # noqa: E402
from mdconv.pipeline import Outcome, convert_to_memory  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mdconv_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def conv(self, path, **kw) -> Outcome:
        """Convertit avec le noyau natif uniquement (résultats identiques d'une machine à l'autre)."""
        kw.setdefault("external", False)
        kw.setdefault("frontmatter", "none")
        return convert_to_memory(Path(path), Options(**kw), rel=Path(path).name, assets_dir="assets")

    def md(self, path, **kw) -> str:
        out = self.conv(path, **kw)
        self.assertIn(out.status, ("ok", "warn", "needs_vision"), f"{out.status}: {out.error}")
        return out.body

    def write(self, name: str, content) -> Path:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def assertMd(self, md: str, *needles: str) -> None:
        for n in needles:
            self.assertIn(n, md, f"« {n} » absent de :\n{md}")

    def assertNotMd(self, md: str, *needles: str) -> None:
        for n in needles:
            self.assertNotIn(n, md, f"« {n} » présent dans :\n{md}")


def have(tool: str) -> bool:
    return shutil.which(tool) is not None
