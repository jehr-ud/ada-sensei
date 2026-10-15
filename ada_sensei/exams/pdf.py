"""A dependency-free PDF writer for exam assessment reports.

The project carries no PDF library, so this module emits PDF 1.4 directly: a
catalog, a page tree, one content stream per page, the base-14 Helvetica fonts,
and a correct cross-reference table. It supports exactly what
``ExamReportGenerator`` needs — wrapped paragraphs, headings, bullets,
key/value rows and column-aligned tables — and nothing more.

Every laid-out line carries an absolute position, so serialization is a direct
translation with no layout state to reconstruct. Text is encoded as WinAnsi
(cp1252) because the standard fonts have no Unicode cmap; characters outside that
repertoire become ``?`` rather than silently disappearing.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field

#: A4 in points.
DEFAULT_PAGE_SIZE = (595.0, 842.0)
DEFAULT_MARGIN = 56.0
BODY_SIZE = 10.0
LEADING = 14.0

#: Base-14 font widths (1/1000 em) for printable ASCII, used for wrapping.
_HELVETICA = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278,
    278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584,
    584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556,
    833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278,
    278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222,
    500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500,
    500, 334, 260, 334, 584,
)
_HELVETICA_BOLD = (
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278,
    278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584,
    584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611,
    833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333,
    278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278,
    556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556,
    500, 389, 280, 389, 584,
)
_WIDTHS = {False: _HELVETICA, True: _HELVETICA_BOLD}

#: Resource names for the two standard fonts.
FONT_REGULAR = "F1"
FONT_BOLD = "F2"

INDENT = 12.0


class PdfError(Exception):
    """The document could not be laid out or written."""


@dataclass(frozen=True)
class Span:
    """One run of text sharing a style."""

    text: str
    bold: bool = False


@dataclass(frozen=True)
class TextLine:
    """A laid-out line at an absolute position, measured from the bottom-left."""

    x: float
    y: float
    spans: tuple[Span, ...]
    size: float


@dataclass
class Page:
    width: float
    height: float
    lines: list[TextLine] = field(default_factory=list)
    rules: list[float] = field(default_factory=list)


def text_width(text: str, size: float, bold: bool = False) -> float:
    """Rendered width in points, from the base-14 metric table."""
    table = _WIDTHS[bold]
    total = 0.0
    for char in text:
        code = ord(char)
        if 32 <= code <= 126:
            total += table[code - 32]
        elif char in ("\n", "\r", "\t"):
            continue
        else:
            total += 500
    return total * size / 1000.0


def wrap(text: str, size: float, max_width: float, bold: bool = False) -> list[str]:
    """Greedy word wrap; a word longer than the line is split, never overflowed."""
    lines: list[str] = []
    for raw in str(text).replace("\r", "").split("\n"):
        current = ""
        for word in raw.split(" "):
            candidate = f"{current} {word}" if current else word
            if text_width(candidate, size, bold) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            while text_width(word, size, bold) > max_width and len(word) > 1:
                cut = len(word)
                while cut > 1 and text_width(word[:cut], size, bold) > max_width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
        lines.append(current)
    return lines or [""]


class SimplePdfWriter:
    """Lays out text into pages and serializes a valid PDF 1.4 document."""

    def __init__(
        self,
        page_size: tuple[float, float] = DEFAULT_PAGE_SIZE,
        margin: float = DEFAULT_MARGIN,
        body_size: float = BODY_SIZE,
        leading: float = LEADING,
        compress: bool = True,
    ) -> None:
        self.page_width, self.page_height = page_size
        self.margin = margin
        self.body_size = body_size
        self.leading = leading
        self.compress = compress
        self.pages: list[Page] = []
        self._new_page()

    # -- geometry ---------------------------------------------------------

    @property
    def content_width(self) -> float:
        return self.page_width - 2 * self.margin

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def _new_page(self) -> Page:
        page = Page(width=self.page_width, height=self.page_height)
        self.pages.append(page)
        return page

    def _page(self) -> Page:
        return self.pages[-1]

    def _cursor(self) -> float:
        page = self._page()
        if not page.lines and not page.rules:
            return self.page_height - self.margin
        lowest = min(
            [line.y for line in page.lines] + page.rules,
            default=self.page_height - self.margin,
        )
        return lowest

    def _room(self) -> float:
        return self._cursor() - self.margin

    def _ensure(self, needed: float) -> None:
        if needed < 0:
            needed = 0
        if self._room() < needed:
            self._new_page()

    def _emit(self, x: float, y: float, spans: tuple[Span, ...], size: float) -> None:
        self._page().lines.append(TextLine(x=x, y=y, spans=spans, size=size))

    # -- content ----------------------------------------------------------

    def heading(self, text: str, level: int = 1) -> None:
        size = {1: 15.0, 2: 12.0, 3: 10.5}.get(level, self.body_size)
        leading = size + 4
        gap = 0.0 if not self._page().lines else (12.0 if level == 1 else 8.0)
        lines = wrap(text, size, self.content_width, bold=True)
        for index, line in enumerate(lines):
            self._ensure(leading + (gap if index == 0 else 0.0))
            y = self._cursor() - (gap if index == 0 else 0.0) - leading
            self._emit(self.margin, y, (Span(line, bold=True),), size)
        if level <= 2:
            self.rule(gap=4.0)

    def rule(self, gap: float = 6.0) -> None:
        self._ensure(gap + 2.0)
        y = self._cursor() - gap
        self._page().rules.append(y)
        self._emit(self.margin, y, (Span(""),), 1.0)

    def paragraph(
        self, text: str, size: float | None = None, indent: float = 0.0
    ) -> None:
        size = size or self.body_size
        for line in wrap(text, size, max(20.0, self.content_width - indent)):
            self._ensure(self.leading)
            self._emit(self.margin + indent, self._cursor() - self.leading,
                       (Span(line),), size)

    def bullet(self, text: str, size: float | None = None) -> None:
        size = size or self.body_size
        width = self.content_width - INDENT
        for index, line in enumerate(wrap(text, size, width)):
            self._ensure(self.leading)
            marker = "\u2022" if index == 0 else ""
            spans = (Span(f"{marker} "), Span(line)) if marker else (Span(line),)
            self._emit(self.margin + INDENT, self._cursor() - self.leading,
                       spans, size)

    def key_value(self, key: str, value: str, size: float | None = None) -> None:
        """``key: value`` with a bold key and a hanging indent."""
        size = size or self.body_size
        key_text = f"{key}: "
        first = self.content_width - text_width(key_text, size, bold=True)
        lines = wrap(value, size, max(20.0, first))
        self._ensure(self.leading)
        self._emit(
            self.margin,
            self._cursor() - self.leading,
            (Span(key_text, bold=True), Span(lines[0])),
            size,
        )
        for line in lines[1:]:
            self._ensure(self.leading)
            self._emit(self.margin + INDENT, self._cursor() - self.leading,
                       (Span(line),), size)

    def table(
        self,
        rows: list[list[str]],
        weights: list[float] | None = None,
        size: float = 9.0,
        gap: float = 3.0,
    ) -> None:
        """Column-aligned table; trailing columns are truncated to fit."""
        if not rows:
            return
        columns = max(len(r) for r in rows)
        weights = list(weights or []) or [1.0] * columns
        while len(weights) < columns:
            weights.append(1.0)
        total = sum(weights[:columns]) or 1.0
        widths = [self.content_width * w / total for w in weights[:columns]]
        for row_index, row in enumerate(rows):
            cells = [str(c) for c in row][:columns]
            cells += [""] * (columns - len(cells))
            bold = row_index == 0
            wrapped = [
                wrap(cell, size, max(12.0, width - 6.0), bold=bold)
                for cell, width in zip(cells, widths, strict=True)
            ]
            height = self.leading * max(len(w) for w in wrapped) + gap
            self._ensure(height)
            top = self._cursor()
            for lines, width in zip(wrapped, widths, strict=True):
                x = self.margin
                for line_index, line in enumerate(lines):
                    y = top - (line_index + 1) * self.leading
                    self._emit(x, y, (Span(line, bold=bold),), size)
                    x += width

    def page_break(self) -> None:
        self._new_page()

    # -- serialization ----------------------------------------------------

    def build(self) -> bytes:
        if not self.pages:
            self._new_page()
        return _serialize(
            self.pages, self.page_width, self.page_height, compress=self.compress
        )


def _escape(data: bytes) -> bytes:
    out = bytearray()
    for byte in data:
        char = bytes((byte,))
        if char in (b"\\", b"(", b")"):
            out.extend(b"\\" + char)
        elif byte < 32 or byte > 126:
            out.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            out.extend(char)
    return bytes(out)


def _page_stream(page: Page, margin: float) -> bytes:
    parts: list[bytes] = [b"BT\n"]
    current_font: tuple[float, bool] | None = None
    for line in page.lines:
        if not any(span.text for span in line.spans):
            continue
        parts.append(f"1 0 0 1 {line.x:.2f} {line.y:.2f} Tm\n".encode("ascii"))
        for span in line.spans:
            if not span.text:
                continue
            key = (line.size, span.bold)
            if key != current_font:
                font = FONT_BOLD if span.bold else FONT_REGULAR
                parts.append(f"/{font} {line.size:.2f} Tf\n".encode("ascii"))
                current_font = key
            payload = _escape(span.text.encode("cp1252", errors="replace"))
            parts.append(b"(" + payload + b") Tj\n")
    parts.append(b"ET\n")
    for rule_y in page.rules:
        parts.append(b"0.75 w\n")
        parts.append(
            (
                f"{margin:.2f} {rule_y:.2f} m "
                f"{page.width - margin:.2f} {rule_y:.2f} l S\n"
            ).encode("ascii")
        )
    return b"".join(parts)


def _serialize(
    pages: list[Page],
    page_width: float,
    page_height: float,
    *,
    compress: bool,
) -> bytes:
    """Assemble objects, the cross-reference table, and the trailer."""
    objects: dict[int, bytes] = {}

    # 1 catalog, 2 page tree, 3/4 fonts, then 2 objects per page.
    page_object_ids = [5 + 2 * i for i in range(len(pages))]
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{oid} 0 R" for oid in page_object_ids)
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii")
    )
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )
    objects[4] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        b"/Encoding /WinAnsiEncoding >>"
    )
    for index, page in enumerate(pages):
        page_id = page_object_ids[index]
        content_id = page_id + 1
        stream = _page_stream(page, DEFAULT_MARGIN)

        if compress:
            packed = zlib.compress(stream)
            extra = b" /Filter /FlateDecode"
        else:
            packed = stream
            extra = b""
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2f} "
            f"{page_height:.2f}] /Resources << /Font << /{FONT_REGULAR} 3 0 R "
            f"/{FONT_BOLD} 4 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = (
            b"<< /Length " + str(len(packed)).encode("ascii") + extra + b" >>\nstream\n"
            + packed
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n".encode("ascii")
        out += objects[object_id]
        out += b"\nendobj\n"

    count = max(objects) + 1
    xref_offset = len(out)
    out += f"xref\n0 {count}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for object_id in range(1, count):
        offset = offsets.get(object_id, 0)
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n"
        f"{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


__all__ = [
    "BODY_SIZE",
    "DEFAULT_MARGIN",
    "DEFAULT_PAGE_SIZE",
    "FONT_BOLD",
    "FONT_REGULAR",
    "INDENT",
    "LEADING",
    "Page",
    "PdfError",
    "SimplePdfWriter",
    "Span",
    "TextLine",
    "text_width",
    "wrap",
]
