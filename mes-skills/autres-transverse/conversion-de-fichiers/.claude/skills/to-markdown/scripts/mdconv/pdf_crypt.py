"""Déchiffrement des PDF protégés (gestionnaire standard) avec mot de passe utilisateur VIDE, en bibliothèque standard.

Beaucoup de PDF « sécurisés » ne le sont que pour l'édition ou la copie : ils s'ouvrent sans mot de passe (mot de passe
utilisateur vide) et seul le propriétaire a un secret. On les lit alors comme les autres. Un vrai mot de passe
d'ouverture est détecté et signalé — jamais deviné, jamais contourné.

Couvre RC4 40/128 bits (V1-V3, R2-R3), AES-128 (V4, R4) et AES-256 (V5, R5/R6). AES est écrit en Python pur avec des
tables T : de l'ordre de 0,5 Mo/s, suffisant car seuls les flux utiles au texte (contenus de pages, tables Unicode, flux
d'objets) sont déchiffrés, à la demande.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any, Callable, Dict, List, Optional, Tuple

from .core import Protected, Unsupported

PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")


# --------------------------------------------------------------------------
# RC4
# --------------------------------------------------------------------------

def rc4(key: bytes, data: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 255
        s[i], s[j] = s[j], s[i]
    out = bytearray(len(data))
    i = j = 0
    for n, b in enumerate(data):
        i = (i + 1) & 255
        j = (j + s[i]) & 255
        s[i], s[j] = s[j], s[i]
        out[n] = b ^ s[(s[i] + s[j]) & 255]
    return bytes(out)


# --------------------------------------------------------------------------
# AES (tables T), blocs de 128 bits, clés de 128/192/256 bits
# --------------------------------------------------------------------------

def _build_tables() -> Tuple[List[int], List[int], List[List[int]], List[List[int]]]:
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= (q << 1) & 0xFF
        q ^= (q << 2) & 0xFF
        q ^= (q << 4) & 0xFF
        if q & 0x80:
            q ^= 0x09
        rot = lambda x, n: ((x << n) | (x >> (8 - n))) & 0xFF  # noqa: E731
        sbox[p] = (q ^ rot(q, 1) ^ rot(q, 2) ^ rot(q, 3) ^ rot(q, 4) ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i

    def mul(a: int, b: int) -> int:
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = ((a << 1) ^ 0x11B) if a & 0x80 else a << 1
            b >>= 1
        return r & 0xFF

    def ror(w: int, n: int) -> int:
        return ((w >> n) | (w << (32 - n))) & 0xFFFFFFFF

    te0 = [(mul(s, 2) << 24) | (s << 16) | (s << 8) | mul(s, 3) for s in sbox]
    td0 = [(mul(s, 14) << 24) | (mul(s, 9) << 16) | (mul(s, 13) << 8) | mul(s, 11) for s in (inv[x] for x in range(256))]
    te = [te0] + [[ror(w, 8 * k) for w in te0] for k in (1, 2, 3)]
    td = [td0] + [[ror(w, 8 * k) for w in td0] for k in (1, 2, 3)]
    return sbox, inv, te, td


_SBOX, _INV, _TE, _TD = _build_tables()


class AES:
    def __init__(self, key: bytes):
        if len(key) not in (16, 24, 32):
            raise ValueError("clé AES invalide")
        nk = len(key) // 4
        self.rounds = nk + 6
        w = list(struct.unpack(">%dI" % nk, key))
        rcon = 1
        for i in range(nk, 4 * (self.rounds + 1)):
            t = w[i - 1]
            if i % nk == 0:
                t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
                t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
                t ^= rcon << 24
                rcon = ((rcon << 1) ^ 0x11B) & 0xFF if rcon & 0x80 else rcon << 1
            elif nk > 6 and i % nk == 4:
                t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
            w.append(w[i - nk] ^ t)
        self.ek = w
        # clé de déchiffrement « équivalente » : InvMixColumns sur les tours intermédiaires
        td0, td1, td2, td3 = _TD
        dk: List[int] = []
        for r in range(self.rounds, -1, -1):
            for c in range(4):
                x = w[4 * r + c]
                if 0 < r < self.rounds:
                    x = td0[_SBOX[x >> 24]] ^ td1[_SBOX[(x >> 16) & 255]] ^ td2[_SBOX[(x >> 8) & 255]] ^ td3[_SBOX[x & 255]]
                dk.append(x)
        self.dk = dk

    def encrypt_block(self, block: bytes) -> bytes:
        te0, te1, te2, te3 = _TE
        rk = self.ek
        s0, s1, s2, s3 = (a ^ b for a, b in zip(struct.unpack(">4I", block), rk[0:4]))
        k = 4
        for _ in range(self.rounds - 1):
            t0 = te0[s0 >> 24] ^ te1[(s1 >> 16) & 255] ^ te2[(s2 >> 8) & 255] ^ te3[s3 & 255] ^ rk[k]
            t1 = te0[s1 >> 24] ^ te1[(s2 >> 16) & 255] ^ te2[(s3 >> 8) & 255] ^ te3[s0 & 255] ^ rk[k + 1]
            t2 = te0[s2 >> 24] ^ te1[(s3 >> 16) & 255] ^ te2[(s0 >> 8) & 255] ^ te3[s1 & 255] ^ rk[k + 2]
            t3 = te0[s3 >> 24] ^ te1[(s0 >> 16) & 255] ^ te2[(s1 >> 8) & 255] ^ te3[s2 & 255] ^ rk[k + 3]
            s0, s1, s2, s3 = t0, t1, t2, t3
            k += 4
        sb = _SBOX
        o0 = ((sb[s0 >> 24] << 24) | (sb[(s1 >> 16) & 255] << 16) | (sb[(s2 >> 8) & 255] << 8) | sb[s3 & 255]) ^ rk[k]
        o1 = ((sb[s1 >> 24] << 24) | (sb[(s2 >> 16) & 255] << 16) | (sb[(s3 >> 8) & 255] << 8) | sb[s0 & 255]) ^ rk[k + 1]
        o2 = ((sb[s2 >> 24] << 24) | (sb[(s3 >> 16) & 255] << 16) | (sb[(s0 >> 8) & 255] << 8) | sb[s1 & 255]) ^ rk[k + 2]
        o3 = ((sb[s3 >> 24] << 24) | (sb[(s0 >> 16) & 255] << 16) | (sb[(s1 >> 8) & 255] << 8) | sb[s2 & 255]) ^ rk[k + 3]
        return struct.pack(">4I", o0, o1, o2, o3)

    def decrypt_block(self, block: bytes) -> bytes:
        td0, td1, td2, td3 = _TD
        rk = self.dk
        s0, s1, s2, s3 = (a ^ b for a, b in zip(struct.unpack(">4I", block), rk[0:4]))
        k = 4
        for _ in range(self.rounds - 1):
            t0 = td0[s0 >> 24] ^ td1[(s3 >> 16) & 255] ^ td2[(s2 >> 8) & 255] ^ td3[s1 & 255] ^ rk[k]
            t1 = td0[s1 >> 24] ^ td1[(s0 >> 16) & 255] ^ td2[(s3 >> 8) & 255] ^ td3[s2 & 255] ^ rk[k + 1]
            t2 = td0[s2 >> 24] ^ td1[(s1 >> 16) & 255] ^ td2[(s0 >> 8) & 255] ^ td3[s3 & 255] ^ rk[k + 2]
            t3 = td0[s3 >> 24] ^ td1[(s2 >> 16) & 255] ^ td2[(s1 >> 8) & 255] ^ td3[s0 & 255] ^ rk[k + 3]
            s0, s1, s2, s3 = t0, t1, t2, t3
            k += 4
        ib = _INV
        o0 = ((ib[s0 >> 24] << 24) | (ib[(s3 >> 16) & 255] << 16) | (ib[(s2 >> 8) & 255] << 8) | ib[s1 & 255]) ^ rk[k]
        o1 = ((ib[s1 >> 24] << 24) | (ib[(s0 >> 16) & 255] << 16) | (ib[(s3 >> 8) & 255] << 8) | ib[s2 & 255]) ^ rk[k + 1]
        o2 = ((ib[s2 >> 24] << 24) | (ib[(s1 >> 16) & 255] << 16) | (ib[(s0 >> 8) & 255] << 8) | ib[s3 & 255]) ^ rk[k + 2]
        o3 = ((ib[s3 >> 24] << 24) | (ib[(s2 >> 16) & 255] << 16) | (ib[(s1 >> 8) & 255] << 8) | ib[s0 & 255]) ^ rk[k + 3]
        return struct.pack(">4I", o0, o1, o2, o3)

    def cbc_decrypt(self, iv: bytes, data: bytes) -> bytes:
        out = bytearray()
        prev = int.from_bytes(iv, "big")
        for i in range(0, len(data) - len(data) % 16, 16):
            blk = data[i:i + 16]
            plain = int.from_bytes(self.decrypt_block(blk), "big") ^ prev
            out += plain.to_bytes(16, "big")
            prev = int.from_bytes(blk, "big")
        return bytes(out)

    def cbc_encrypt(self, iv: bytes, data: bytes) -> bytes:
        out = bytearray()
        prev = int.from_bytes(iv, "big")
        for i in range(0, len(data) - len(data) % 16, 16):
            x = int.from_bytes(data[i:i + 16], "big") ^ prev
            enc = self.encrypt_block(x.to_bytes(16, "big"))
            out += enc
            prev = int.from_bytes(enc, "big")
        return bytes(out)


def _unpad(data: bytes) -> bytes:
    if data:
        n = data[-1]
        if 1 <= n <= 16 and data.endswith(bytes([n]) * n):
            return data[:-n]
    return data


# --------------------------------------------------------------------------
# Gestionnaire de sécurité standard, mot de passe vide
# --------------------------------------------------------------------------

def _hash_r6(password: bytes, salt: bytes, udata: bytes = b"") -> bytes:
    """Algorithme 2.B (ISO 32000-2) : condensat itéré SHA-256/384/512 + AES-128-CBC."""
    k = hashlib.sha256(password + salt + udata).digest()
    i = 0
    while True:
        k1 = (password + k + udata) * 64
        e = AES(k[:16]).cbc_encrypt(k[16:32], k1)
        mod = sum(e[:16]) % 3
        k = (hashlib.sha256, hashlib.sha384, hashlib.sha512)[mod](e).digest()
        i += 1
        if i >= 64 and e[-1] <= i - 32:
            break
    return k[:32]


class Decryptor:
    """Clé de fichier + déchiffrement par objet. ``get`` résout les références du document."""

    def __init__(self, enc: Dict[str, Any], id0: bytes, get: Callable[[Any], Any]):
        g = lambda k, d=None: (get(enc.get(k)) if enc.get(k) is not None else d)  # noqa: E731
        if str(g("Filter", "Standard")) != "Standard":
            raise Protected("PDF chiffré par un gestionnaire non standard : non pris en charge")
        self.v, self.r = int(g("V", 0) or 0), int(g("R", 0) or 0)
        o, u = g("O", b""), g("U", b"")
        if not (isinstance(o, bytes) and isinstance(u, bytes)):
            raise Unsupported("dictionnaire de chiffrement illisible")
        self.encrypt_metadata = g("EncryptMetadata", True) is not False
        cf = g("CF", {}) or {}
        cf = {str(k): (get(v) if not isinstance(v, dict) else v) for k, v in cf.items()} if isinstance(cf, dict) else {}

        def method(name_key: str) -> str:
            if self.v < 4:
                return "RC4"
            name = str(g(name_key, "Identity"))
            if name == "Identity":
                return "Identity"
            filt = cf.get(name) or {}
            cfm = str(get(filt.get("CFM")) or "None")
            return {"V2": "RC4", "AESV2": "AESV2", "AESV3": "AESV3", "None": "Identity"}.get(cfm, "Unknown")

        self.stm, self.strm = method("StmF"), method("StrF")
        if "Unknown" in (self.stm, self.strm):
            raise Unsupported("méthode de chiffrement PDF inconnue")
        if self.v >= 5:
            self.key = self._key_v5(u, g("UE", b""), o)
            return
        p = int(g("P", 0) or 0)
        length = (int(g("Length", 40) or 40) // 8) if self.v >= 2 else 5
        if self.v == 4:
            filt = cf.get(str(g("StmF", "StdCF"))) or {}
            length = 16 if self.stm == "AESV2" else max(5, int(get(filt.get("Length")) or 128) // (8 if int(get(filt.get("Length")) or 128) > 40 else 1))
        length = max(5, min(length, 16))
        h = hashlib.md5(PAD + o[:32] + (p & 0xFFFFFFFF).to_bytes(4, "little") + id0)
        if self.r >= 4 and not self.encrypt_metadata:
            h.update(b"\xff\xff\xff\xff")
        key = h.digest()
        if self.r >= 3:
            for _ in range(50):
                key = hashlib.md5(key[:length]).digest()
        self.key = key[:length]
        if not self._user_ok(u, id0):
            raise Protected("PDF protégé par mot de passe (ouverture)")

    # -- vérifications ---------------------------------------------------
    def _user_ok(self, u: bytes, id0: bytes) -> bool:
        if self.r == 2:
            return rc4(self.key, PAD) == u[:32]
        x = rc4(self.key, hashlib.md5(PAD + id0).digest())
        for i in range(1, 20):
            x = rc4(bytes(b ^ i for b in self.key), x)
        return x[:16] == u[:16]

    def _key_v5(self, u: bytes, ue: Any, _o: bytes) -> bytes:
        if not isinstance(ue, bytes) or len(u) < 48:
            raise Unsupported("dictionnaire de chiffrement AES-256 incomplet")
        vsalt, ksalt = u[32:40], u[40:48]
        h = _hash_r6 if self.r >= 6 else (lambda pw, salt, ud=b"": hashlib.sha256(pw + salt + ud).digest())
        if h(b"", vsalt) != u[:32]:
            raise Protected("PDF protégé par mot de passe (ouverture)")
        return AES(h(b"", ksalt)).cbc_decrypt(b"\x00" * 16, ue[:32])

    # -- déchiffrement -------------------------------------------------------
    def _object_key(self, num: int, gen: int, aes: bool) -> bytes:
        k = self.key + num.to_bytes(3, "little") + gen.to_bytes(2, "little") + (b"sAlT" if aes else b"")
        return hashlib.md5(k).digest()[:min(len(self.key) + 5, 16)]

    def _apply(self, method: str, num: int, gen: int, data: bytes) -> bytes:
        if method == "Identity" or not data:
            return data
        if method == "RC4":
            return rc4(self._object_key(num, gen, False), data)
        key = self.key if method == "AESV3" else self._object_key(num, gen, True)
        if len(data) < 32:
            return b""
        return _unpad(AES(key).cbc_decrypt(data[:16], data[16:]))

    def stream(self, num: int, gen: int, data: bytes) -> bytes:
        return self._apply(self.stm, num, gen, data)

    def string(self, num: int, gen: int, data: bytes) -> bytes:
        return self._apply(self.strm, num, gen, data)


def first_id(trailer: Dict[str, Any], get: Callable[[Any], Any]) -> bytes:
    ids: Optional[Any] = get(trailer.get("ID"))
    if isinstance(ids, list) and ids:
        first = get(ids[0])
        if isinstance(first, bytes):
            return first
    return b""
