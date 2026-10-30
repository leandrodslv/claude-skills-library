"""Lecteur OLE2 / Compound File Binary (bibliothèque standard) : .doc, .xls, .ppt, .msg, .vsd…

Lecture seule, avec garde-fous (boucles de chaînes, tailles). Suffisant pour extraire des flux nommés.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional

ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF
NOSTREAM = 0xFFFFFFFF
MAX_FILE = 256 << 20


class CFBError(ValueError):
    pass


@dataclass
class Entry:
    name: str
    etype: int          # 1 = storage, 2 = stream, 5 = racine
    left: int
    right: int
    child: int
    start: int
    size: int
    sid: int = 0
    path: str = ""


class CFB:
    def __init__(self, data: bytes):
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise CFBError("signature OLE absente")
        if len(data) > MAX_FILE:
            raise CFBError("fichier OLE trop volumineux")
        self.data = data
        shift, mini_shift = struct.unpack_from("<HH", data, 30)
        if shift not in (9, 12):
            raise CFBError("taille de secteur invalide")
        self.ssz = 1 << shift
        self.mssz = 1 << mini_shift
        (n_fat, first_dir, _tx, self.mini_cutoff, first_minifat, n_minifat, first_difat, n_difat) = struct.unpack_from(
            "<IIIIIIII", data, 44)
        difat = [x for x in struct.unpack_from("<109I", data, 76) if x < 0xFFFFFFF0]
        sec = first_difat
        for _ in range(min(n_difat, 512)):
            if sec >= 0xFFFFFFF0:
                break
            vals = struct.unpack_from("<%dI" % (self.ssz // 4), data, self._off(sec))
            difat += [x for x in vals[:-1] if x < 0xFFFFFFF0]
            sec = vals[-1]
        self.fat: List[int] = []
        for s in difat[: max(n_fat, len(difat))]:
            off = self._off(s)
            if off + self.ssz > len(data):
                break
            self.fat += struct.unpack_from("<%dI" % (self.ssz // 4), data, off)
        self.entries: List[Entry] = []
        raw_dir = self._read_chain(first_dir)
        for i in range(len(raw_dir) // 128):
            ent = raw_dir[i * 128:(i + 1) * 128]
            nlen = struct.unpack_from("<H", ent, 64)[0]
            etype = ent[66]
            name = ent[: max(0, nlen - 2)].decode("utf-16-le", "replace") if 2 <= nlen <= 64 else ""
            left, right, child = struct.unpack_from("<III", ent, 68)
            start = struct.unpack_from("<I", ent, 116)[0]
            size = struct.unpack_from("<Q", ent, 120)[0] & 0xFFFFFFFF
            self.entries.append(Entry(name, etype, left, right, child, start, size, i))
        self.minifat: List[int] = []
        if first_minifat < 0xFFFFFFF0:
            raw = self._read_chain(first_minifat)
            self.minifat = list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))
        root = self.entries[0] if self.entries else None
        self.ministream = self._read_chain(root.start, root.size) if root and root.start < 0xFFFFFFF0 else b""
        self.paths: Dict[str, Entry] = {}
        if root:
            self._walk(root.child, "")

    def _off(self, sector: int) -> int:
        return (sector + 1) * self.ssz

    def _read_chain(self, start: int, size: Optional[int] = None) -> bytes:
        out = bytearray()
        sec, hops = start, 0
        limit = len(self.fat) + 8
        while sec < 0xFFFFFFF0 and hops < limit:
            off = self._off(sec)
            if off + self.ssz > len(self.data):
                out += self.data[off:off + self.ssz]
                break
            out += self.data[off:off + self.ssz]
            sec = self.fat[sec] if sec < len(self.fat) else ENDOFCHAIN
            hops += 1
        return bytes(out[:size]) if size is not None else bytes(out)

    def _read_mini(self, start: int, size: int) -> bytes:
        out = bytearray()
        sec, hops = start, 0
        while sec < 0xFFFFFFF0 and hops < len(self.minifat) + 8:
            off = sec * self.mssz
            out += self.ministream[off:off + self.mssz]
            sec = self.minifat[sec] if sec < len(self.minifat) else ENDOFCHAIN
            hops += 1
        return bytes(out[:size])

    def _walk(self, sid: int, prefix: str, seen: Optional[set] = None) -> None:
        seen = seen if seen is not None else set()
        stack = [(sid, prefix)]
        while stack:
            cur, pre = stack.pop()
            if cur == NOSTREAM or cur >= len(self.entries) or cur in seen:
                continue
            seen.add(cur)
            e = self.entries[cur]
            e.path = (pre + "/" + e.name) if pre else e.name
            self.paths[e.path.lower()] = e
            stack.append((e.left, pre))
            stack.append((e.right, pre))
            if e.etype == 1:
                stack.append((e.child, e.path))

    # -- API ------------------------------------------------------------
    def names(self) -> List[str]:
        return [e.path for e in self.paths.values()]

    def has(self, path: str) -> bool:
        return path.lower() in self.paths

    def read(self, path: str) -> bytes:
        e = self.paths.get(path.lower())
        if e is None or e.etype != 2:
            raise KeyError(path)
        if e.size < self.mini_cutoff:
            return self._read_mini(e.start, e.size)
        return self._read_chain(e.start, e.size)

    def read_opt(self, path: str) -> Optional[bytes]:
        try:
            return self.read(path)
        except KeyError:
            return None

    def children(self, storage: str) -> List[str]:
        pre = storage.lower().rstrip("/") + "/"
        depth = pre.count("/")
        return [e.path for p, e in self.paths.items() if p.startswith(pre) and p.count("/") == depth]
