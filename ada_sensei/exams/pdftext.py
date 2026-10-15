"""Dependency-free PDF text extraction for instructor exam statements.

``ExamDefinitionLoader`` must be able to read a PDF statement (RQ-EXM-002) and
this project deliberately carries no PDF dependency, so the small subset of PDF
needed to recover page text is implemented here: content-stream discovery,
Flate/zlib inflation, and the ``Tj`` / ``TJ`` / ``'`` / ``"`` text-showing
operators. Anything outside that subset is reported as an empty extraction so
the caller records a limitation instead of inventing requirements.
"""

from __future__ import annotations

import re
import zlib

#: ``stream ... endstream`` payload, either raw or Flate-compressed.
_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)

#: Text-showing operators, in both literal-string and hex-string form.
_SHOW_RE = re.compile(
    rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>"
    rb"\s*(?:Tj|TJ|'|\")"
)

_LITERAL_RE = re.compile(rb"^\((.*)\)$", re.DOTALL)

#: Escapes a PDF literal string may contain.
_ESCAPES = {
    b"n": b"\n",
    b"r": b"\r",
    b"t": b"\t",
    b"b": b"\b",
    b"f": b"\f",
    b"(": b"(",
    b")": b")",
    b"\\": b"\\",
}


class PdfTextExtractionError(Exception):
    """The PDF could not be read as a text statement."""


def _unescape(raw: bytes) -> str:
    out = bytearray()
    index = 0
    while index < len(raw):
        char = raw[index : index + 1]
        if char != b"\\" or index + 1 >= len(raw):
            out.extend(char)
            index += 1
            continue
        nxt = raw[index + 1 : index + 2]
        if nxt in _ESCAPES:
            out.extend(_ESCAPES[nxt])
            index += 2
            continue
        if nxt.isdigit():
            octal = raw[index + 1 : index + 4]
            digits = bytes(c for c in octal if 0x30 <= c <= 0x37)
            if digits:
                out.append(int(digits, 8) & 0xFF)
                index += 1 + len(digits)
                continue
        # Octal escape with more or fewer digits than the 3-digit window.
        out.extend(nxt)
        index += 2
    return out.decode("latin-1", errors="replace")


def _decode_string(token: bytes) -> str:
    if token.startswith(b"<"):
        hexdigits = re.sub(rb"\s", b"", token[1:-1])
        if len(hexdigits) % 2:
            hexdigits += b"0"
        try:
            raw = bytes.fromhex(hexdigits.decode("ascii"))
        except ValueError:
            return ""
        return raw.decode("latin-1", errors="replace")
    match = _LITERAL_RE.match(token)
    return _unescape(match.group(1)) if match else ""


def _inflate(payload: bytes) -> bytes | None:
    try:
        return zlib.decompress(payload)
    except zlib.error:
        try:
            return zlib.decompressobj().decompress(payload)
        except zlib.error:
            return None


def _content_streams(data: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in _STREAM_RE.finditer(data):
        payload = match.group(1)
        streams.append(_inflate(payload) or payload)
    return streams


def extract_text(data: bytes) -> str:
    """Recover the visible text of a PDF, page order preserved.

    Raises :class:`PdfTextExtractionError` when the bytes are not a PDF at all;
    returns an empty string when the file is a valid PDF whose text cannot be
    recovered, so the caller can record a limitation (RQ-EXM-002).
    """
    if not data.startswith(b"%PDF-"):
        raise PdfTextExtractionError("file does not start with a %PDF- header")
    lines: list[str] = []
    for stream in _content_streams(data):
        for token in _SHOW_RE.findall(stream):
            for piece in re.findall(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", token):
                text = _decode_string(piece)
                if text.strip():
                    lines.append(text.strip())
    return "\n".join(lines)


def extract_text_file(path) -> str:
    from pathlib import Path

    return extract_text(Path(path).read_bytes())


__all__ = [
    "PdfTextExtractionError",
    "extract_text",
    "extract_text_file",
]
