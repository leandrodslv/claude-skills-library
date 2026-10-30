"""Devinette d'encodage de secours, en bibliothèque standard, pour les anciens fichiers texte non UTF-8.

Le cas courant (français, anglais : cp1252) est réglé dans ``util.decode_text``. Ici, ce qui reste :
alphabets non latins sur un octet (cyrillique, grec, hébreu, arabe), européen central / turc, et CJK sur deux octets.
Pas de statistiques de langue : on vérifie qu'un décodage strict donne des lettres d'un seul alphabet (et une casse
plausible), ce qui suffit à écarter les mauvais candidats sans dictionnaire.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Optional, Tuple

_SINGLE_BYTE = ("cp1255", "cp1251", "koi8-r", "cp1253", "cp1256")     # cp1255 avant cp1251 : ses octets libres échouent sur du russe
_CASED = {"CYRILLIC", "GREEK"}
_CJK_SCRIPTS = {"CJK", "HIRAGANA", "KATAKANA", "HANGUL"}


def _script(ch: str) -> str:
    try:
        return unicodedata.name(ch).split(" ", 1)[0]
    except ValueError:
        return ""


def _group(ch: str) -> str:
    """Alphabet d'une lettre ; idéogrammes, kana et hangul forment un seul groupe (un texte japonais mêle les trois)."""
    sc = _script(ch)
    return "CJK" if sc in _CJK_SCRIPTS else sc


def _letters(text: str) -> Tuple[str, float, float, list]:
    """(alphabet dominant, cohérence, couverture, lettres) ; cohérence = part des lettres de l'alphabet dominant,
    couverture = part des caractères non blancs qui sont des lettres."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "", 0.0, 0.0, []
    script, n = Counter(_group(c) for c in letters).most_common(1)[0]
    visible = sum(1 for c in text if not c.isspace()) or 1
    return script, n / len(letters), len(letters) / visible, letters


def _single_byte(sample: bytes) -> Optional[str]:
    best, best_score = None, 0.0
    for enc in _SINGLE_BYTE:
        try:
            text = sample.decode(enc)
        except UnicodeDecodeError:
            continue
        script, coherence, cover, letters = _letters(text)
        if len(letters) < 6 or script == "LATIN" or coherence < 0.9 or cover < 0.7:      # < 0,7 : du CJK lu en octets simples
            continue
        score = coherence * cover
        if script in _CASED:
            lower = sum(c.islower() for c in letters) / len(letters)
            if lower < 0.6:            # cp1251 lu en koi8-r (ou l'inverse) : majuscules et minuscules échangées
                continue
            score *= lower
        if score > best_score:
            best, best_score = enc, score
    return best


def _multi_byte(sample: bytes) -> Optional[str]:
    """Shift_JIS / EUC-JP (présence de kana), GB / Big5 / EUC-KR (plages d'octets de tête et de queue)."""
    if not re.search(rb"[\x81-\xfe][\x40-\xfe]", sample):
        return None
    best, best_kana = None, 0.0
    for enc in ("cp932", "euc_jp"):
        try:
            text = sample.decode(enc)
        except UnicodeDecodeError:
            continue
        script, coherence, _cover, letters = _letters(text)
        kana = sum(_script(c) in ("HIRAGANA", "KATAKANA") for c in letters) / max(len(letters), 1)
        if len(letters) >= 4 and coherence >= 0.9 and script == "CJK" and kana >= 0.15 and kana > best_kana:
            best, best_kana = enc, kana
    if best:
        return best
    pairs = re.findall(rb"[\xa1-\xfe][\x40-\xfe]", sample)
    if len(pairs) < 4:
        return None
    if all(0xB0 <= p[0] <= 0xC8 and p[1] >= 0xA1 for p in pairs):
        candidates = ("cp949", "gb18030")               # syllabes hangul : têtes B0–C8, queues ≥ A1
    elif sum(p[1] >= 0xA1 for p in pairs) / len(pairs) >= 0.95:
        candidates = ("gb18030", "big5")                # GB2312 : la queue est toujours ≥ A1 ; Big5 a ~40 % de queues 40–7E
    else:
        candidates = ("big5", "gb18030")
    # plages des caractères courants : GB2312 niveaux 1-2 = têtes A1–A9 et B0–D7 ; Big5 = têtes A1–C6. Du cyrillique lu
    # comme du GB tombe surtout en E0–FF (« русский » = E0–FF) : le décodage est « valide » mais ce sont des idéogrammes rares.
    common = {"gb18030": lambda h: 0xA1 <= h <= 0xA9 or 0xB0 <= h <= 0xD7, "big5": lambda h: 0xA1 <= h <= 0xC6,
              "cp949": lambda h: 0xB0 <= h <= 0xC8}
    for enc in candidates:
        if sum(common[enc](p[0]) for p in pairs) / len(pairs) < 0.85:
            continue
        try:
            text = sample.decode(enc)
        except UnicodeDecodeError:
            continue
        script, coherence, _cover, letters = _letters(text)
        if len(letters) >= 4 and coherence >= 0.9 and script == "CJK":
            return enc
    return None


def _double_byte_runs(sample: bytes) -> bool:
    """Les suites d'octets ≥ 0x80 sont-elles toutes de longueur paire ? Vrai des codages EUC/GB (chaque caractère = 2 octets
    hauts) ; un texte cyrillique ou grec sur un octet donne des mots de longueurs quelconques."""
    runs = re.findall(rb"[\x80-\xff]+", sample)
    return sum(map(len, runs)) >= 12 and all(len(r) % 2 == 0 for r in runs)


def guess_legacy_codepage(sample: bytes) -> Optional[str]:
    """Encodage probable d'un texte majoritairement en octets ≥ 0x80 (ni UTF-8, ni occidental), ou None."""
    if _double_byte_runs(sample):
        return _multi_byte(sample) or _single_byte(sample)
    return _single_byte(sample) or _multi_byte(sample)


# Lettres propres au polonais/tchèque/hongrois (cp1250) ou au turc (cp1254) : lues en cp1252 elles apparaissent sous
# forme de symboles (« ¹ ³ ¿ ») ou de lettres islandaises (« ð þ ») au milieu des mots — jamais le cas d'un texte occidental.
_INSIDE = r"[^\W\d_]{{1}}{cls}[^\W\d_]"
_CE_SYMBOLS = re.compile(_INSIDE.format(cls=r"[¹³¥£¯¿¼¾]"))
_TR_LETTERS = re.compile(_INSIDE.format(cls=r"[ðþÐÞ]"))
# ISO-8859-2 range les mêmes lettres ailleurs (ą ś ź en 0xB1 0xB6 0xBC) : lues en cp1252 → « ± ¶ ¼ » au milieu des mots,
# alors que cp1250 les met en 0xB9 (¹) ou 0x9C/0x9F (octets que cp1252 ne définit pas ou autrement)
_L2_ONLY = re.compile(_INSIDE.format(cls=r"[±¶¼¡¦¬]"))
_CP1250_ONLY = re.compile(_INSIDE.format(cls=r"[¹]"))


def _decodes(data: bytes, enc: str) -> bool:
    try:
        data.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def refine_western(data: bytes) -> str:
    """cp1252 par défaut ; cp1250 ou cp1254 quand les indices ci-dessus sont nets (au moins 2 occurrences).

    Des octets que cp1252 ne définit pas (0x81, 0x8D, 0x8F, 0x90, 0x9D) prouvent que ce n'est pas du cp1252.
    """
    try:
        text = data.decode("cp1252")
    except UnicodeDecodeError:
        return next((e for e in ("cp1250", "cp1254", "cp1257") if _decodes(data, e)), "latin-1")
    if len(_CE_SYMBOLS.findall(text)) >= 2 and _decodes(data, "cp1250"):
        if (_L2_ONLY.search(text) and not _CP1250_ONLY.search(text) and not any(0x80 <= b <= 0x9F for b in data)
                and _decodes(data, "iso8859_2")):
            return "iso8859_2"
        return "cp1250"
    if len(_TR_LETTERS.findall(text)) >= 2 and _decodes(data, "cp1254"):
        return "cp1254"
    return "cp1252"
