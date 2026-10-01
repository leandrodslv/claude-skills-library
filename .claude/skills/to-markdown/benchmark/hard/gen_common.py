"""Aides communes à la batterie de documents difficiles : manifeste, écrivains OOXML à la main, LibreOffice."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.sax.saxutils import escape as xesc

WITH_BIG = False
OUT = Path(__file__).resolve().parent / "corpus"


@dataclass
class Case:
    """Un document difficile et ce qu'on doit en retrouver."""
    id: str
    path: Path
    category: str
    difficulty: int                                         # 1 (facile) … 5 (très dur)
    challenge: str                                          # ce qui rend ce document difficile (une phrase)
    must: List[str] = field(default_factory=list)           # textes à retrouver (casse et ponctuation ignorées)
    any_of: List[List[str]] = field(default_factory=list)   # groupes : au moins une variante de chaque groupe
    order: List[str] = field(default_factory=list)          # textes à retrouver DANS CET ORDRE (ordre de lecture)
    absent: List[str] = field(default_factory=list)         # textes qui ne doivent PAS apparaître (bruit, supprimé)
    once: List[str] = field(default_factory=list)           # textes présents exactement une fois (doublons)
    at_most: Dict[str, int] = field(default_factory=dict)   # texte -> occurrences maximales (en-têtes répétés)
    headings: List[str] = field(default_factory=list)
    cells: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)     # lignes de tableau : toutes ces cellules sur la même ligne Markdown, dans l'ordre
    levels: List[List[object]] = field(default_factory=list)  # [[texte d'élément de liste, niveau d'imbrication]] : l'indentation doit suivre
    links: List[List[str]] = field(default_factory=list)    # [[texte, url], …]
    expect: str = "ok"                                      # ok | vision (lecture visuelle ou OCR) | error (échec propre attendu)
    notes: str = ""

    def to_json(self) -> Dict[str, object]:
        d = {k: v for k, v in self.__dict__.items() if v not in ([], {}, "")}
        d["path"] = self.path.relative_to(OUT).as_posix()
        return d


def x(s: str) -> str:
    return xesc(s)


def write_zip(path: Path, parts: Dict[str, str], binary: Optional[Dict[str, bytes]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
        for name, b in (binary or {}).items():
            z.writestr(name, b)


W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w10="urn:schemas-microsoft-com:office:word"')

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W_NS}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="48"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""


def p(text: str, style: str = "", extra_ppr: str = "", runs: Optional[str] = None) -> str:
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + extra_ppr
    body = runs if runs is not None else f'<w:r><w:t xml:space="preserve">{x(text)}</w:t></w:r>'
    return f"<w:p>{('<w:pPr>' + ppr + '</w:pPr>') if ppr else ''}{body}</w:p>"


def num_p(text: str, num_id: int, lvl: int) -> str:
    return p(text, "ListParagraph", f'<w:numPr><w:ilvl w:val="{lvl}"/><w:numId w:val="{num_id}"/></w:numPr>')


def cell(content: str, span: int = 1, vmerge: str = "", width: int = 2000) -> str:
    pr = f'<w:tcW w:w="{width}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{span}"/>' if span > 1 else "")
    if vmerge == "restart":
        pr += '<w:vMerge w:val="restart"/>'
    elif vmerge == "continue":
        pr += "<w:vMerge/>"
    return f"<w:tc><w:tcPr>{pr}</w:tcPr>{content or '<w:p/>'}</w:tc>"


def table(rows: List[str], cols: int = 4) -> str:
    grid = "".join('<w:gridCol w:w="2000"/>' for _ in range(cols))
    return (f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
            + "".join(f"<w:tr>{r}</w:tr>" for r in rows) + "</w:tbl>")


def numbering_xml() -> str:
    lv = lambda i, fmt, txt, ind: (f'<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{txt}"/>'  # noqa: E731
                                   f'<w:pPr><w:ind w:left="{ind}" w:hanging="360"/></w:pPr></w:lvl>')
    multi = "".join([lv(0, "decimal", "%1.", 720), lv(1, "lowerLetter", "%2)", 1440), lv(2, "lowerRoman", "%3.", 2160), lv(3, "bullet", "•", 2880)])
    bullets = "".join(lv(i, "bullet", "•", 720 * (i + 1)) for i in range(4))
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering {W_NS}>'
            f'<w:abstractNum w:abstractNumId="0">{multi}</w:abstractNum><w:abstractNum w:abstractNumId="1">{bullets}</w:abstractNum>'
            '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num></w:numbering>')


def make_docx(path: Path, body: str, parts: Optional[Dict[str, str]] = None, rels: str = "", sect: str = "", ctypes: str = "") -> None:
    """DOCX minimal écrit à la main. `parts` : parties supplémentaires (nom → XML) ; `rels` : relations de document.xml."""
    parts = dict(parts or {})
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W_NS}><w:body>{body}{sect or "<w:sectPr/>"}</w:body></w:document>'
    types = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
             '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
             + ctypes + "</Types>")
    base_rels = ('<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                 '<Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>')
    all_parts = {
        "[Content_Types].xml": types,
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": doc,
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                        + base_rels + rels + "</Relationships>",
        "word/styles.xml": STYLES,
        "word/numbering.xml": numbering_xml(),
    }
    all_parts.update(parts)
    write_zip(path, all_parts)


def soffice() -> Optional[str]:
    return shutil.which("soffice") or shutil.which("libreoffice")


def lo_convert(src: Path, target: str, dest: Path, infilter: str = "") -> bool:
    """Convertit `src` avec LibreOffice (target : « doc », « pdf:writer_pdf_Export »…) vers le fichier `dest`."""
    exe = soffice()
    if not exe:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "o"
        out.mkdir()
        cmd = [exe, f"-env:UserInstallation=file://{tmp}/profile", "--headless"]
        if infilter:
            cmd.append(f"--infilter={infilter}")
        cmd += ["--convert-to", target, "--outdir", str(out), str(src)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=240, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False
        made = next(iter(out.iterdir()), None)
        if not made or not made.stat().st_size:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(made, dest)
    return True
