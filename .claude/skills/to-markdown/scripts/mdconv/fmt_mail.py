"""E-mails (EML, MBOX, MSG Outlook) et pages archivées MHTML → Markdown, en bibliothèque standard."""
from __future__ import annotations

import email
import email.policy
import mailbox
import re
import struct
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .cfb import CFB, CFBError
from .core import Ctx, Result, Unsupported, engine
from .fmt_html import decode_html, html_to_markdown
from .util import clean_text, esc_inline, human_bytes, slugify

MAX_MESSAGES = 500
CONVERTIBLE = {"pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls", "odt", "ods", "odp", "rtf", "txt", "csv", "html", "htm",
               "md", "json", "xml", "epub", "svg", "png", "jpg", "jpeg", "eml"}


def _fmt_addr(v: Optional[str]) -> str:
    return clean_text(v or "").replace("\n", " ").strip()


def _header_block(fields: List[Tuple[str, str]]) -> str:
    return "\n".join(f"**{k} :** {esc_inline(v)}" + "  " for k, v in fields if v).rstrip() if fields else ""


def _render_message(msg: EmailMessage, ctx: Ctx, stem: str, heading: int, attachments_out: List[str]) -> Tuple[str, str, str]:
    subject = _fmt_addr(str(msg.get("subject", "")))
    fields = [("De", _fmt_addr(str(msg.get("from", "")))), ("À", _fmt_addr(str(msg.get("to", "")))),
              ("Cc", _fmt_addr(str(msg.get("cc", "")))), ("Date", _fmt_addr(str(msg.get("date", "")))),
              ("Objet", subject)]
    body_md = ""
    src = ""
    # images embarquées référencées par cid:
    cids: Dict[str, bytes] = {}
    for part in msg.walk():
        cid = part.get("Content-ID")
        if cid and part.get_content_maintype() == "image":
            payload = part.get_payload(decode=True)
            if payload:
                cids[cid.strip("<>")] = payload
    plain = msg.get_body(preferencelist=("plain",))
    html = msg.get_body(preferencelist=("html",))
    plain_text = ""
    if plain is not None:
        try:
            plain_text = clean_text(plain.get_content()).replace("\r\n", "\n").strip()
        except Exception:
            plain_text = ""
    if plain_text and len(plain_text) > 20:
        body_md, src = plain_text, plain_text
    elif html is not None:
        try:
            raw = html.get_content()
        except Exception:
            raw = decode_html(html.get_payload(decode=True) or b"")
        md, _t, _m, s = html_to_markdown(raw, ctx, stem=slugify(stem) or "img",
                                         image_loader=lambda src: cids.get(src[4:]) if src.startswith("cid:") else None)
        body_md, src = md, s
    else:
        body_md = plain_text
        src = plain_text
    atts: List[str] = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "piece-jointe"
        data = part.get_payload(decode=True)
        if part.get_content_type() == "message/rfc822":
            try:
                data = part.get_content().as_bytes()
            except Exception:
                data = data or b""
            name = name if name != "piece-jointe" else "message.eml"
        if not data:
            continue
        link = ctx.add_file(slugify(name, keep_dots=True), data)
        atts.append(f"- [{esc_inline(name)}]({link}) — {human_bytes(len(data))}")
        attachments_out.append(link.rsplit("/", 1)[-1])
    parts = [f"{'#' * heading} {esc_inline(subject) or '(sans objet)'}", _header_block([f for f in fields if f[0] != "Objet"])]
    if body_md.strip():
        parts.append(body_md.strip())
    if atts:
        parts.append("**Pièces jointes :**\n\n" + "\n".join(atts))
    return "\n\n".join(p for p in parts if p), subject, src


@engine("eml", name="native", prio=10)
def eml_native(path, ctx: Ctx) -> Result:
    msg = email.message_from_bytes(Path(path).read_bytes(), policy=email.policy.default)
    atts: List[str] = []
    md, subject, src = _render_message(msg, ctx, Path(path).stem, 1, atts)  # type: ignore[arg-type]
    res = Result(markdown=md, fmt="eml", engine="native", title=subject)
    res.source_text = src
    res.stats["partial_source"] = True
    if atts:
        res.stats["attachments"] = atts
        ctx.warn(f"{len(atts)} pièce(s) jointe(s) extraite(s) dans le dossier d'assets")
    return res


@engine("mbox", name="native", prio=10)
def mbox_native(path, ctx: Ctx) -> Result:
    box = mailbox.mbox(str(path), factory=lambda f: email.message_from_binary_file(f, policy=email.policy.default))
    parts: List[str] = []
    srcs: List[str] = []
    atts: List[str] = []
    n = 0
    for msg in box:
        n += 1
        if n > MAX_MESSAGES:
            ctx.warn(f"boîte tronquée à {MAX_MESSAGES} messages")
            break
        md, _s, src = _render_message(msg, ctx, f"{Path(path).stem}-{n}", 2, atts)  # type: ignore[arg-type]
        parts.append(md)
        srcs.append(src)
    if not parts:
        raise Unsupported("aucun message")
    res = Result(markdown=f"# {esc_inline(Path(path).stem)}\n\n_{n} message(s)_\n\n" + "\n\n---\n\n".join(parts), fmt="mbox", engine="native",
                 title=Path(path).stem)
    res.source_text = "\n".join(srcs)
    res.stats["partial_source"] = True
    return res


@engine("mhtml", name="native", prio=10)
def mhtml_native(path, ctx: Ctx) -> Result:
    msg = email.message_from_bytes(Path(path).read_bytes(), policy=email.policy.default)
    html_part = None
    resources: Dict[str, bytes] = {}
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/html" and html_part is None:
            html_part = part
        elif part.get_content_maintype() == "image":
            loc = part.get("Content-Location") or (("cid:" + part.get("Content-ID").strip("<>")) if part.get("Content-ID") else "")
            data = part.get_payload(decode=True)
            if loc and data:
                resources[loc] = data
    if html_part is None:
        raise Unsupported("aucune partie HTML dans le MHTML")
    raw = html_part.get_content()
    md, title, meta, src = html_to_markdown(raw, ctx, stem=slugify(Path(path).stem) or "img",
                                            image_loader=lambda s: resources.get(s) or resources.get(s.split("#")[0]))
    head = f"# {esc_inline(title)}\n\n" if title and not re.match(r"(?m)^#\s", md) else ""
    res = Result(markdown=head + md, fmt="mhtml", engine="native", title=title)
    res.source_text = src
    res.stats["partial_source"] = True
    return res


# --------------------------------------------------------------------------
# Outlook .msg (OLE) — lecture minimale sans dépendance
# --------------------------------------------------------------------------

def _prop_str(cfb: CFB, prefix: str, tag: str) -> str:
    for suffix, enc in (("001F", "utf-16-le"), ("001E", "cp1252")):
        data = cfb.read_opt(f"{prefix}__substg1.0_{tag}{suffix}")
        if data:
            return clean_text(data.decode(enc, "replace").rstrip("\x00")).strip()
    return ""


def _msg_date(cfb: CFB) -> str:
    data = cfb.read_opt("__properties_version1.0")
    if not data or len(data) < 40:
        return ""
    for i in range(32, len(data) - 15, 16):
        tag, _flags, val = struct.unpack_from("<IIQ", data, i)
        if (tag >> 16) in (0x0040,) and (tag & 0xFFFF) in (0x0039, 0x0E06):
            try:
                return (datetime(1601, 1, 1) + timedelta(microseconds=val // 10)).strftime("%Y-%m-%d %H:%M")
            except (OverflowError, ValueError):
                return ""
    return ""


@engine("msg", name="native", prio=10)
def msg_native(path, ctx: Ctx) -> Result:
    try:
        cfb = CFB(Path(path).read_bytes())
    except CFBError as exc:
        raise Unsupported(str(exc))
    subject = _prop_str(cfb, "", "0037")
    sender = _prop_str(cfb, "", "0C1A")
    sender_mail = _prop_str(cfb, "", "5D01") or _prop_str(cfb, "", "0C1F")
    to, cc = _prop_str(cfb, "", "0E04"), _prop_str(cfb, "", "0E03")
    body = _prop_str(cfb, "", "1000")
    html_raw = cfb.read_opt("__substg1.0_10130102") or b""
    fields = [("De", f"{sender} <{sender_mail}>" if sender and sender_mail and sender_mail != sender else (sender or sender_mail)),
              ("À", to), ("Cc", cc), ("Date", _msg_date(cfb))]
    body_md, src = body.replace("\r\n", "\n"), body
    if (not body.strip() or len(body.strip()) < 20) and html_raw:
        md, _t, _m, s = html_to_markdown(decode_html(html_raw), ctx, stem="msg")
        body_md, src = md, s
    atts: List[str] = []
    att_lines: List[str] = []
    for path_name in cfb.names():
        m = re.match(r"^(__attach_version1\.0_#[0-9A-F]+)$", path_name, re.I)
        if not m:
            continue
        pre = m.group(1) + "/"
        name = _prop_str(cfb, pre, "3707") or _prop_str(cfb, pre, "3704") or "piece-jointe"
        data = cfb.read_opt(pre + "__substg1.0_37010102")
        if data:
            link = ctx.add_file(slugify(name, keep_dots=True), data)
            atts.append(link.rsplit("/", 1)[-1])
            att_lines.append(f"- [{esc_inline(name)}]({link}) — {human_bytes(len(data))}")
    parts = [f"# {esc_inline(subject) or '(sans objet)'}", _header_block(fields), body_md.strip()]
    if att_lines:
        parts.append("**Pièces jointes :**\n\n" + "\n".join(att_lines))
    md = "\n\n".join(p for p in parts if p)
    if not (subject or body_md.strip()):
        raise Unsupported("aucun contenu lisible dans le .msg")
    res = Result(markdown=md, fmt="msg", engine="native", title=subject)
    res.source_text = src
    res.stats["partial_source"] = True
    if atts:
        res.stats["attachments"] = atts
        ctx.warn(f"{len(atts)} pièce(s) jointe(s) extraite(s) dans le dossier d'assets")
    return res
