"""Fabrique de fichiers de test : OOXML, ODF, EPUB, PDF, PNG… construits à la main avec la bibliothèque standard.

Aucun de ces helpers n'utilise mdconv : un test ne doit jamais dépendre du code qu'il vérifie pour produire son entrée.
"""
from __future__ import annotations

import io
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

W = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
     'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
     'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
     'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
     'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
     'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
     'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
     'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def png(w: int = 40, h: int = 40, rgb: Tuple[int, int, int] = (200, 30, 30), noisy: bool = False) -> bytes:
    """PNG valide (RVB, unicolore) ; assez gros pour passer le filtre « image décorative »."""
    if noisy:
        import random
        rnd = random.Random(7)
        raw = b"".join(b"\x00" + bytes(rnd.randrange(256) for _ in range(3 * w)) for _ in range(h))
    else:
        raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    noise = b"".join(struct.pack(">I", (i * 2654435761) & 0xFFFFFFFF) for i in range(150))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"tEXt", b"Comment\x00" + noise[:300]) + chunk(b"IEND", b""))


def write_zip(path, files: Dict[str, bytes | str]) -> Path:
    path = Path(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


# --------------------------------------------------------------------------
# DOCX
# --------------------------------------------------------------------------

STYLES = XML + f'''<w:styles {W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="character" w:styleId="Strong"><w:name w:val="Strong"/><w:rPr><w:b/></w:rPr></w:style>
</w:styles>'''

NUMBERING = XML + f'''<w:numbering {W}>
<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/></w:lvl>
<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/><w:lvlText w:val="o"/></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2)"/></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>'''


def run(text: str, b: bool = False, i: bool = False, extra: str = "") -> str:
    rpr = ("<w:b/>" if b else "") + ("<w:i/>" if i else "") + extra
    return f'<w:r>{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}<w:t xml:space="preserve">{text}</w:t></w:r>'


def para(content: str, style: Optional[str] = None, num: Optional[Tuple[int, int]] = None) -> str:
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if num:
        ppr += f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>'
    if "<w:r" not in content and "<w:hyperlink" not in content and "<m:" not in content and "<w:sdt" not in content:
        content = run(content)
    return f'<w:p>{"<w:pPr>" + ppr + "</w:pPr>" if ppr else ""}{content}</w:p>'


def make_docx(path, body: str, *, styles: str = STYLES, numbering: str = "", footnotes: str = "", comments: str = "",
              media: Optional[Dict[str, bytes]] = None, rels: str = "", core_title: str = "", extra_parts: Optional[Dict[str, str]] = None) -> Path:
    files: Dict[str, bytes | str] = {
        "[Content_Types].xml": XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                               '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
                               '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>',
        "word/document.xml": XML + f'<w:document {W}><w:body>{body}<w:sectPr/></w:body></w:document>',
        "word/styles.xml": styles,
        "word/_rels/document.xml.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + rels + "</Relationships>",
    }
    if core_title:
        files["docProps/core.xml"] = XML + ('<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                                            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>' + core_title + '</dc:title><dc:creator>Alice</dc:creator></cp:coreProperties>')
    if numbering:
        files["word/numbering.xml"] = numbering
    if footnotes:
        files["word/footnotes.xml"] = footnotes
    if comments:
        files["word/comments.xml"] = comments
    for name, data in (media or {}).items():
        files["word/media/" + name] = data
    for name, data in (extra_parts or {}).items():
        files[name] = data
    return write_zip(path, files)


def hyperlink_rel(rid: str, url: str) -> str:
    return f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{url}" TargetMode="External"/>'


def image_rel(rid: str, name: str) -> str:
    return f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>'


def drawing(rid: str, alt: str = "") -> str:
    return (f'<w:r><w:drawing><wp:inline><wp:docPr id="1" name="Picture 1" descr="{alt}"/><a:graphic><a:graphicData>'
            f'<pic:pic><pic:blipFill><a:blip r:embed="{rid}"/></pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


# --------------------------------------------------------------------------
# PPTX
# --------------------------------------------------------------------------

P_NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"')


def sp(sid: int, name: str, paras: Sequence[str], ph: str = "", off: Tuple[int, int] = (0, 0), bullets: str = "") -> str:
    phx = f'<p:nvPr><p:ph type="{ph}"/></p:nvPr>' if ph and ph != "body" else ('<p:nvPr><p:ph idx="1"/></p:nvPr>' if ph == "body" else "<p:nvPr/>")
    ps = "".join(f'<a:p>{bullets}<a:r><a:rPr lang="fr-FR"/><a:t>{t}</a:t></a:r></a:p>' if not t.startswith("<") else f"<a:p>{t}</a:p>" for t in paras)
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/>{phx}</p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{off[0]}" y="{off[1]}"/><a:ext cx="4000000" cy="800000"/></a:xfrm></p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/>{ps}</p:txBody></p:sp>')


def slide_xml(shapes: str, hidden: bool = False) -> str:
    return XML + (f'<p:sld {P_NS}{" show=" + chr(34) + "0" + chr(34) if hidden else ""}><p:cSld><p:spTree>'
                  f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{shapes}</p:spTree></p:cSld></p:sld>')


def make_pptx(path, slides: Sequence[str], *, order: Optional[Sequence[int]] = None, slide_rels: Optional[Dict[int, str]] = None,
              extra: Optional[Dict[str, bytes | str]] = None, title: str = "") -> Path:
    """``slides[i]`` est le XML de la diapositive stockée dans « slide{i+1}.xml » ; ``order`` = ordre réel de présentation."""
    n = len(slides)
    order = list(order) if order is not None else list(range(1, n + 1))
    files: Dict[str, bytes | str] = {
        "[Content_Types].xml": XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
        "_rels/.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
        "ppt/presentation.xml": XML + f'<p:presentation {P_NS}><p:sldIdLst>' + "".join(
            f'<p:sldId id="{256 + k}" r:id="rId{k}"/>' for k in order) + '</p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/></p:presentation>',
        "ppt/_rels/presentation.xml.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
            f'<Relationship Id="rId{k}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{k}.xml"/>'
            for k in range(1, n + 1)) + "</Relationships>",
    }
    if title:
        files["docProps/core.xml"] = XML + ('<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                                            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>' + title + '</dc:title></cp:coreProperties>')
    for i, xml in enumerate(slides, 1):
        files[f"ppt/slides/slide{i}.xml"] = xml
        if slide_rels and i in slide_rels:
            files[f"ppt/slides/_rels/slide{i}.xml.rels"] = XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + slide_rels[i] + "</Relationships>"
    files.update(extra or {})
    return write_zip(path, files)


# --------------------------------------------------------------------------
# XLSX
# --------------------------------------------------------------------------

X_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def make_xlsx(path, sheets: Sequence[Tuple[str, str, str]], *, shared: Sequence[str] = (), styles: str = "", extra: Optional[Dict[str, bytes | str]] = None,
              date1904: bool = False) -> Path:
    """``sheets`` : (nom, xml de <sheetData>+, état) ; ``styles`` : XML <styleSheet> complet (optionnel)."""
    files: Dict[str, bytes | str] = {
        "[Content_Types].xml": XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
        "_rels/.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": XML + f'<workbook {X_NS}>' + ('<workbookPr date1904="1"/>' if date1904 else "") + "<sheets>" + "".join(
            f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"' + (f' state="{st}"' if st != "visible" else "") + "/>" for i, (n, _x, st) in enumerate(sheets, 1)) + "</sheets></workbook>",
        "xl/_rels/workbook.xml.rels": XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheets) + 1)) + "</Relationships>",
    }
    for i, (_n, xml, _st) in enumerate(sheets, 1):
        files[f"xl/worksheets/sheet{i}.xml"] = XML + f"<worksheet {X_NS}>{xml}</worksheet>"
    if shared:
        files["xl/sharedStrings.xml"] = XML + f'<sst {X_NS} count="{len(shared)}" uniqueCount="{len(shared)}">' + "".join(
            f"<si><t>{s}</t></si>" for s in shared) + "</sst>"
    if styles:
        files["xl/styles.xml"] = styles
    files.update(extra or {})
    return write_zip(path, files)


STYLES_XLSX = XML + f'''<styleSheet {X_NS}><numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/></numFmts>
<cellXfs count="4"><xf numFmtId="0"/><xf numFmtId="164"/><xf numFmtId="9"/><xf numFmtId="10"/></cellXfs></styleSheet>'''


# --------------------------------------------------------------------------
# ODF, EPUB
# --------------------------------------------------------------------------

ODF_NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
          'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
          'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
          'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
          'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/"')


def make_odf(path, mimetype: str, body: str, autostyles: str = "") -> Path:
    path = Path(path)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), mimetype)  # premier membre, non compressé
        z.writestr("content.xml", XML + f'<office:document-content {ODF_NS}><office:automatic-styles>{autostyles}</office:automatic-styles><office:body>{body}</office:body></office:document-content>')
        z.writestr("META-INF/manifest.xml", XML + '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>')
    return path


def make_epub(path, chapters: Sequence[Tuple[str, str]], title: str = "Mon livre", author: str = "Auteur") -> Path:
    items = "".join(f'<item id="c{i}" href="c{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(len(chapters)))
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(chapters)))
    files: Dict[str, bytes | str] = {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": XML + '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles>'
                                        '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "OEBPS/content.opf": XML + f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                                   f'<dc:title>{title}</dc:title><dc:creator>{author}</dc:creator><dc:language>fr</dc:language></metadata>'
                                   f'<manifest>{items}</manifest><spine>{spine}</spine></package>',
    }
    for i, (_t, html) in enumerate(chapters):
        files[f"OEBPS/c{i}.xhtml"] = html
    return write_zip(path, files)


# --------------------------------------------------------------------------
# PDF (écrit à la main : Helvetica, flux compressé)
# --------------------------------------------------------------------------

def make_pdf(path, pages: Sequence[Sequence[tuple]], *, compress: bool = True, image_only: bool = False,
             title: str = "") -> Path:
    """``pages[i]`` = liste de (x, y, texte[, taille[, gras]]) ou flux de contenu brut (bytes). Helvetica/WinAnsi ;
    ``image_only`` : pages sans texte (scan simulé)."""
    objs: List[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    add(b"")  # 1 : catalogue (rempli à la fin)
    add(b"")  # 2 : arbre des pages
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    kids = []
    for texts in pages:
        if image_only:
            stream = b"q 100 0 0 100 50 50 cm /Im0 Do Q"
        elif isinstance(texts, (bytes, bytearray)):
            stream = bytes(texts)           # flux de contenu fourni tel quel (TJ, chaînes hexadécimales…)
        else:
            ops = ["BT"]
            for item in texts:
                x, y, t = item[:3]
                size = item[3] if len(item) > 3 else 12
                face = "F2" if len(item) > 4 and item[4] else "F1"
                esc = t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                ops.append(f"/{face} {size} Tf 1 0 0 1 {x} {y} Tm ({esc}) Tj")
            ops.append("ET")
            stream = "\n".join(ops).encode("cp1252")
        body = zlib.compress(stream) if compress else stream
        flt = b" /Filter /FlateDecode" if compress else b""
        cont = add(b"<< /Length " + str(len(body)).encode() + flt + b" >>\nstream\n" + body + b"\nendstream")
        page = add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {cont} 0 R "
                   f"/Resources << /Font << /F1 {font} 0 R /F2 {font_bold} 0 R >> >> >>".encode())
        kids.append(page)
    objs[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(f'{k} 0 R' for k in kids)}] >>".encode()
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    info = add(f"<< /Title ({title}) >>".encode()) if title else 0
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for o in offs:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R{f' /Info {info} 0 R' if info else ''} >>\nstartxref\n{xref}\n%%EOF\n".encode())
    Path(path).write_bytes(out.getvalue())
    return Path(path)


def make_scan_pdf(path, pngs: Sequence[bytes]) -> Path:
    """PDF « scanné » : une image par page (PNG RVB ou niveaux de gris non entrelacé, ré-embarqué tel quel via le prédicteur PNG)."""
    objs: List[bytes] = [b"", b""]
    kids = []
    for png_bytes in pngs:
        pos, idat, w, h, ctype = 8, b"", 0, 0, 2
        while pos < len(png_bytes):
            n = struct.unpack(">I", png_bytes[pos:pos + 4])[0]
            kind = png_bytes[pos + 4:pos + 8]
            body = png_bytes[pos + 8:pos + 8 + n]
            if kind == b"IHDR":
                w, h, depth, ctype, _c, _f, inter = struct.unpack(">IIBBBBB", body)
                assert depth == 8 and ctype in (0, 2) and inter == 0, "PNG RVB/gris 8 bits non entrelacé requis"
            elif kind == b"IDAT":
                idat += body
            pos += 12 + n
        colors, space = (3, "/DeviceRGB") if ctype == 2 else (1, "/DeviceGray")
        img = len(objs) + 1
        objs.append((f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace {space} /BitsPerComponent 8 "
                     f"/Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors {colors} /BitsPerComponent 8 /Columns {w} >> "
                     f"/Length {len(idat)} >>\nstream\n").encode() + idat + b"\nendstream")
        content = b"q 595 0 0 842 0 0 cm /Im0 Do Q"
        cont = len(objs) + 1
        objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
        page = len(objs) + 1
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {cont} 0 R /Resources << /XObject << /Im0 {img} 0 R >> >> >>".encode())
        kids.append(page)
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(f'{k} 0 R' for k in kids)}] >>".encode()
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for o in offs:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    Path(path).write_bytes(out.getvalue())
    return Path(path)
