"""Authoritative exam definition resolution (RQ-EXM-002).

The instructor's statement is the only source of exam requirements. It may be
Markdown, a structured JSON specification, or a PDF; all three normalize into one
``ExamDefinition`` and the original statement is always preserved so the
normalized requirements stay reviewable (spec.md §Exam definition and
documentation).

The loader is deterministic: the same statement always yields the same exam id
and the same ``req://`` ids, because both are derived from the statement text.

## Supported Markdown requirement formats

The loader recognises two explicit formats:

**Format A — bullet list under a requirements heading:**

The heading (level 1-6) must match one of the labels in ``_REQUIREMENT_HEADINGS``.
Bullets may be:
  - plain: ``- Some requirement text``
  - explicit id+weight: ``- [REQ-01] (0.20) Some requirement text``

**Format B — Markdown table under a criteria/evaluation heading:**

The heading must match one of the labels in ``_CRITERIA_HEADINGS``.
The table must have a column labelled ``ID`` or ``id`` and a column labelled
``Criterio``, ``Criterion``, ``Criteria``, ``Description`` or ``Descripción``.
An optional ``Peso funcional`` / ``Functional weight`` column provides weights.
Row ids beginning with ``**`` (bold total rows) are skipped.

If neither format is found and the statement has non-trivial content, a
``limitations`` entry is added describing the unrecognised section and the
section name, so the problem is explicit rather than silent.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import (
    DEFAULT_EXAM_RUBRIC_REF,
    DocumentationRules,
    ExamDefinition,
    ExamDefinitionError,
    ExamRequirement,
    StatementFormat,
    requirement_id_for,
)
from .pdftext import PdfTextExtractionError, extract_text_file

#: A Markdown heading that introduces a functional requirement list.
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<text>.+?)\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
#: ``- id: FR-1 (0.5) Some text`` gives explicit ids and weights.
_WEIGHTED_RE = re.compile(
    r"^\[(?P<id>[A-Za-z0-9_.\-]+)\]\s*(?:\((?P<weight>[0-9]*\.?[0-9]+)\)\s*)?(?P<text>.+)$"
)
#: ``allowed duration: 90m`` / ``allowed /ask count: 3`` in a Markdown front block.
#: Separators and unit spellings are matched loosely because instructors write
#: these headers by hand; an unparsed limit would silently turn a scored
#: criterion into ``not_evaluated`` (RQ-EXM-007, RQ-EXM-017).
_DURATION_RE = re.compile(
    r"allowed[\s_/-]*duration"
    r"(?:[\s_]+(?P<word>seconds?|secs?|minutes?|mins?|hours?|hrs?))?"
    r"[\s_]*[:=]\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>seconds?|secs?|minutes?|mins?|hours?|hrs?|[smh])?",
    re.I,
)
_ASK_RE = re.compile(
    r"allowed[\s_/-]*(?:/\s*)?asks?[\s_]*(?:count|usage)?[\s_]*[:=]\s*(?P<value>\d+)",
    re.I,
)

#: Unit spellings accepted in a Markdown duration header, in seconds.
_DURATION_UNITS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
}

#: Markdown sections whose bullets are the functional requirements (Format A).
_REQUIREMENT_HEADINGS = (
    "requirement",
    "requirements",
    "functional requirement",
    "functional requirements",
    "requisitos",
    "requisitos funcionales",
)

#: Markdown sections whose tables are the evaluation criteria (Format B).
#: Numbered headings (``## 7. Criterios de evaluación``) are matched by
#: stripping the leading number and dot first.
_CRITERIA_HEADINGS = (
    "criterios de evaluación",
    "criterios de evaluacion",
    "criterios de calificación",
    "criterios de calificacion",
    "evaluation criteria",
    "grading criteria",
    "scoring criteria",
    "criteria",
    "criterios",
    "rúbrica",
    "rubrica",
    "rubric",
)

#: Markdown table row: ``| cell | cell | …``
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
#: Separator row: ``|---|---|``
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s|:\-]+\|\s*$")

#: Column names accepted as the requirement id column (case-insensitive).
_ID_COL_NAMES = {"id", "req", "código", "codigo", "code", "num", "#"}
#: Column names accepted as the description column.
_DESC_COL_NAMES = {
    "criterio",
    "criterion",
    "criteria",
    "description",
    "descripción",
    "descripcion",
    "requirement",
    "requisito",
    "detalle",
    "detail",
}
#: Column names accepted as the functional weight column.
#: Listed from most specific to least specific; the first match wins.
_WEIGHT_COL_NAMES_ORDERED = (
    "peso funcional",
    "functional weight",
    "ponderación",
    "ponderacion",
    "weight",
    "peso",
    "puntaje",
    "score",
    "puntos",
    "points",
)
_WEIGHT_COL_NAMES = set(_WEIGHT_COL_NAMES_ORDERED)


def _strip_heading_number(label: str) -> str:
    """Remove a leading ordinal (``7.``, ``3)``, ``II.``) from a heading label.

    ``## 7. Criterios de evaluación`` → ``criterios de evaluación``.
    """
    return re.sub(r"^\s*(?:\d+|[ivxlIVXL]+)[.)]\s*", "", label).strip()


class ExamDefinitionLoader:
    """Resolves an ``ExamDefinition`` from an instructor statement."""

    def load(
        self, source: str | Path, *, exam_id: str | None = None
    ) -> ExamDefinition:
        path = Path(source).expanduser()
        if not path.is_file():
            raise ExamDefinitionError(f"exam statement not found: {path}")
        suffix = path.suffix.lower()
        if suffix in {".json"}:
            return self._from_json(path, exam_id)
        if suffix in {".pdf"}:
            return self._from_pdf(path, exam_id)
        return self._from_markdown(path, exam_id)

    def load_text(
        self,
        text: str,
        *,
        statement_format: StatementFormat = StatementFormat.markdown,
        exam_id: str | None = None,
        source: str = "inline",
    ) -> ExamDefinition:
        """Normalize an inline statement without touching the filesystem."""
        if statement_format is StatementFormat.json:
            return self._definition_from_payload(
                self._parse_json(text), exam_id, source, None, StatementFormat.json
            )
        if statement_format is StatementFormat.pdf:
            raise ExamDefinitionError(
                "inline statements cannot be PDF; pass a .pdf path to load()"
            )
        payload = self._parse_markdown(text)
        return self._definition_from_payload(
            payload, exam_id, source, None, StatementFormat.markdown, original=text
        )

    # -- formats ----------------------------------------------------------

    def _from_markdown(self, path: Path, exam_id: str | None) -> ExamDefinition:
        text = path.read_text(encoding="utf-8")
        payload = self._parse_markdown(text)
        return self._definition_from_payload(
            payload,
            exam_id,
            str(path),
            str(path),
            StatementFormat.markdown,
            original=text,
        )

    def _from_json(self, path: Path, exam_id: str | None) -> ExamDefinition:
        raw = path.read_text(encoding="utf-8")
        return self._definition_from_payload(
            self._parse_json(raw),
            exam_id,
            str(path),
            str(path),
            StatementFormat.json,
            original=raw,
        )

    def _from_pdf(self, path: Path, exam_id: str | None) -> ExamDefinition:
        """RQ-EXM-002: the original PDF is preserved; text is normalized."""
        try:
            text = extract_text_file(path)
        except (PdfTextExtractionError, OSError) as exc:
            raise ExamDefinitionError(
                f"could not read exam statement PDF {path}: {exc}"
            ) from exc
        limitations: list[str] = []
        if not text.strip():
            limitations.append(
                f"no extractable text in {path.name}; normalized requirements "
                "must be reviewed by the instructor"
            )
            text = ""
        payload = self._parse_markdown(text)
        definition = self._definition_from_payload(
            payload,
            exam_id,
            str(path),
            str(path),
            StatementFormat.pdf,
            original=text,
        )
        definition.limitations.extend(limitations)
        return definition

    # -- parsers ----------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise ExamDefinitionError(
                f"exam statement is not valid JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ExamDefinitionError(
                "structured exam statements must be a JSON object"
            )
        return payload

    @staticmethod
    def _parse_markdown(text: str) -> dict:
        """Extract requirements, title, and limits from a Markdown statement.

        Supports two formats:
        - Format A: bullet list under a requirements heading.
        - Format B: Markdown table under a criteria/evaluation heading.

        Returns a dict with keys ``title``, ``requirements``,
        ``allowed_duration_seconds``, ``allowed_ask_count``, and
        ``limitations`` (a list of human-readable parse warnings).
        """
        lines = text.splitlines()
        title = ""
        front: list[str] = []
        limitations: list[str] = []

        # --- pass 1: collect title and determine section types -----------
        # We need to scan all headings to find what sections exist and
        # which section type (bullet vs table) each is.
        sections: list[tuple[int, str, str]] = []  # (line_idx, section_type, heading_label)
        for idx, raw_line in enumerate(lines):
            heading = _HEADING_RE.match(raw_line)
            if heading:
                raw_label = heading.group("text").strip()
                label = raw_label.lower().rstrip(":")
                stripped = _strip_heading_number(label)
                if not title:
                    title = raw_label
                if label in _REQUIREMENT_HEADINGS or stripped in _REQUIREMENT_HEADINGS:
                    sections.append((idx, "bullets", raw_label))
                elif label in _CRITERIA_HEADINGS or stripped in _CRITERIA_HEADINGS:
                    sections.append((idx, "table", raw_label))

        # --- pass 2: extract requirements --------------------------------
        requirements: list[dict] = []

        for sec_idx, (line_idx, sec_type, heading_label) in enumerate(sections):
            end_idx = sections[sec_idx + 1][0] if sec_idx + 1 < len(sections) else len(lines)
            section_lines = lines[line_idx + 1 : end_idx]

            if sec_type == "bullets":
                found = ExamDefinitionLoader._parse_bullet_requirements(
                    section_lines, heading_label
                )
                requirements.extend(found)
            elif sec_type == "table":
                found, table_limitations = ExamDefinitionLoader._parse_table_requirements(
                    section_lines, heading_label
                )
                requirements.extend(found)
                limitations.extend(table_limitations)

            if not requirements and not found:
                limitations.append(
                    f"section '{heading_label}' matched a known criteria heading "
                    "but no parsable requirements were found in it; check the "
                    "format (expected bullets or a table with ID and description columns)"
                )

        # Collect non-section lines for duration/ask scanning
        # (everything outside the recognised sections)
        in_section = set()
        for sec_idx, (line_idx, _, _) in enumerate(sections):
            end_idx = sections[sec_idx + 1][0] if sec_idx + 1 < len(sections) else len(lines)
            in_section.update(range(line_idx, end_idx))

        for idx, raw_line in enumerate(lines):
            if idx not in in_section:
                front.append(raw_line)

        header = "\n".join(front)
        return {
            "title": title,
            "requirements": requirements,
            "allowed_duration_seconds": _scan_duration(header),
            "allowed_ask_count": _scan_asks(header),
            "limitations": limitations,
        }

    @staticmethod
    def _parse_bullet_requirements(
        section_lines: list[str], heading_label: str
    ) -> list[dict]:
        """Extract requirements from a bullet list section (Format A)."""
        requirements: list[dict] = []
        for raw_line in section_lines:
            bullet = _BULLET_RE.match(raw_line)
            if bullet is None:
                continue
            body = bullet.group("text").strip()
            if not body or body.startswith("<!--"):
                continue
            requirements.append(
                ExamDefinitionLoader._markdown_requirement(body, len(requirements))
            )
        return requirements

    @staticmethod
    def _parse_table_requirements(
        section_lines: list[str], heading_label: str
    ) -> tuple[list[dict], list[str]]:
        """Extract requirements from a Markdown table section (Format B).

        Returns ``(requirements, limitations)``. Limitations describe parse
        warnings without raising an exception, so the caller can surface them
        instead of silently returning an empty list.
        """
        limitations: list[str] = []
        # Collect the table lines (must start with |)
        table_lines = [l for l in section_lines if _TABLE_ROW_RE.match(l)]
        if not table_lines:
            return [], []

        # First non-separator row is the header
        header_row: list[str] | None = None
        data_rows: list[list[str]] = []
        for line in table_lines:
            if _TABLE_SEP_RE.match(line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header_row is None:
                header_row = cells
            else:
                data_rows.append(cells)

        if header_row is None:
            limitations.append(
                f"section '{heading_label}': table found but no header row could be parsed"
            )
            return [], limitations

        # Locate relevant columns
        header_lower = [h.lower().strip() for h in header_row]
        id_col = next(
            (i for i, h in enumerate(header_lower) if h in _ID_COL_NAMES), None
        )
        desc_col = next(
            (i for i, h in enumerate(header_lower) if h in _DESC_COL_NAMES), None
        )
        # Weight column uses priority order: "peso funcional" wins over "puntaje".
        weight_col: int | None = None
        for col_name in _WEIGHT_COL_NAMES_ORDERED:
            idx = next((i for i, h in enumerate(header_lower) if h == col_name), None)
            if idx is not None:
                weight_col = idx
                break

        if id_col is None:
            limitations.append(
                f"section '{heading_label}': table has no recognized ID column; "
                f"headers found: {header_row}. Expected one of: {sorted(_ID_COL_NAMES)}"
            )
            return [], limitations
        if desc_col is None:
            limitations.append(
                f"section '{heading_label}': table has no recognized description column; "
                f"headers found: {header_row}. Expected one of: {sorted(_DESC_COL_NAMES)}"
            )
            return [], limitations

        requirements: list[dict] = []
        for row in data_rows:
            if len(row) <= max(id_col, desc_col):
                continue
            req_id = _strip_md_bold(row[id_col]).strip()
            description = _strip_md_bold(row[desc_col]).strip()
            # Skip total/summary rows (bold id or empty description)
            if not req_id or not description or req_id.startswith("*"):
                continue
            # Skip obviously non-requirement rows (totals)
            if req_id.lower() in {"total", "totales", "subtotal", "suma"}:
                continue
            weight: float | None = None
            if weight_col is not None and weight_col < len(row):
                raw_w = _strip_md_bold(row[weight_col]).strip().rstrip("%")
                try:
                    weight = float(raw_w)
                    # If column is in percentage points (e.g. 20), normalize to 0-1
                    if weight > 1.0:
                        weight = weight / 100.0
                except (ValueError, TypeError):
                    weight = None
            requirements.append(
                {
                    "requirement_id": req_id,
                    "description": description,
                    "weight": weight,
                }
            )

        if not requirements:
            limitations.append(
                f"section '{heading_label}': table parsed but contained no "
                "valid requirement rows (all rows may be total/summary rows or "
                "the id/description columns could not be matched)"
            )
        return requirements, limitations

    @staticmethod
    def _markdown_requirement(body: str, index: int) -> dict:
        explicit = _WEIGHTED_RE.match(body)
        if explicit:
            return {
                "requirement_id": explicit.group("id"),
                "description": explicit.group("text").strip(),
                "weight": (
                    float(explicit.group("weight"))
                    if explicit.group("weight")
                    else None
                ),
            }
        return {
            "requirement_id": requirement_id_for(body, index),
            "description": body,
            "weight": None,
        }

    # -- normalization ----------------------------------------------------

    def _definition_from_payload(
        self,
        payload: dict,
        exam_id: str | None,
        source: str,
        source_path: str | None,
        statement_format: StatementFormat,
        *,
        original: str = "",
    ) -> ExamDefinition:
        requirements = self._requirements(payload.get("requirements") or [])
        title = str(payload.get("title") or "").strip()
        version = str(payload.get("version") or "v1")
        statement = original or str(payload.get("statement") or "")
        resolved_exam_id = exam_id or self._exam_id_for(
            title, statement, source_path or source
        )
        rules = self._documentation_rules(payload.get("documentation_rules"))
        # Surface parse limitations (from table/bullet parsing) explicitly so
        # the user can see why requirements may be absent rather than getting a
        # silent empty list (RQ-EXM-002, spec.md §Exam definition and documentation).
        parse_limitations: list[str] = [
            str(lim) for lim in (payload.get("limitations") or [])
        ]
        return ExamDefinition(
            exam_id=resolved_exam_id,
            title=title or resolved_exam_id,
            version=version,
            statement_format=statement_format,
            statement_source=source,
            original_statement=statement,
            original_source_path=source_path,
            requirements=requirements,
            allowed_duration_seconds=_as_optional_int(
                payload.get("allowed_duration_seconds")
            ),
            allowed_ask_count=_as_optional_int(payload.get("allowed_ask_count")),
            rubric_ref=str(payload.get("rubric_ref") or DEFAULT_EXAM_RUBRIC_REF),
            documentation_rules=rules,
            limitations=parse_limitations,
        )

    @staticmethod
    def _requirements(raw: object) -> list[ExamRequirement]:
        """Normalize requirements and give them weights summing to 1.0.

        An instructor who declares no weights gets equal shares; declared weights
        are kept verbatim, so a malformed weighting surfaces as a validation error
        rather than being silently repaired (spec.md §Functional requirements).
        """
        if not isinstance(raw, list):
            raise ExamDefinitionError(
                "exam requirements must be a list of requirement objects"
            )
        entries: list[dict] = []
        for index, item in enumerate(raw):
            if isinstance(item, str):
                entries.append(
                    {
                        "requirement_id": requirement_id_for(item, index),
                        "description": item,
                        "weight": None,
                    }
                )
                continue
            if not isinstance(item, dict):
                raise ExamDefinitionError(
                    f"exam requirement #{index + 1} must be a string or an object, "
                    f"got {type(item).__name__}"
                )
            description = str(item.get("description") or item.get("text") or "").strip()
            if not description:
                raise ExamDefinitionError(
                    f"exam requirement #{index + 1} has no description"
                )
            entries.append(
                {
                    "requirement_id": str(
                        item.get("requirement_id")
                        or item.get("id")
                        or requirement_id_for(description, index)
                    ),
                    "description": description,
                    "dimension": str(
                        item.get("dimension") or "functional_requirements"
                    ),
                    "weight": item.get("weight"),
                    "evidence_expectations": [
                        str(e) for e in (item.get("evidence_expectations") or [])
                    ],
                }
            )
        if not entries:
            return []
        declared = [e.get("weight") for e in entries]
        if all(w is None for w in declared):
            share = 1.0 / len(entries)
            weights = [share] * len(entries)
        else:
            if any(w is None for w in declared):
                raise ExamDefinitionError(
                    "exam requirements must either all declare a weight or "
                    "none of them"
                )
            weights = [float(w) for w in declared]
        return [
            ExamRequirement(
                requirement_id=e["requirement_id"],
                description=e["description"],
                dimension=e.get("dimension", "functional_requirements"),
                weight=weight,
                evidence_expectations=e.get("evidence_expectations", []),
            )
            for e, weight in zip(entries, weights, strict=True)
        ]

    @staticmethod
    def _documentation_rules(raw: object) -> DocumentationRules:
        if not isinstance(raw, dict):
            return DocumentationRules()
        defaults = DocumentationRules()
        return DocumentationRules(
            accepted_globs=tuple(
                raw.get("accepted_globs") or defaults.accepted_globs
            ),
            required_files=tuple(raw.get("required_files") or ()),
            documentation_is_advisory=bool(
                raw.get(
                    "documentation_is_advisory",
                    defaults.documentation_is_advisory,
                )
            ),
        )

    @staticmethod
    def _exam_id_for(title: str, statement: str, source: str) -> str:
        """A stable id derived from the statement, never from a prompt."""
        digest = hashlib.sha256(
            f"{title}\n{statement}\n{source}".encode()
        ).hexdigest()[:12]
        return f"exam://{digest}"


def _strip_md_bold(text: str) -> str:
    """Remove Markdown bold markers (``**text**`` → ``text``)."""
    return re.sub(r"\*{1,2}([^*]*)\*{1,2}", r"\1", text)


def _scan_duration(text: str) -> int | None:
    match = _DURATION_RE.search(text)
    if match is None:
        return None
    value = float(match.group("value"))
    # A bare number is read as minutes, matching how instructors write "60" for
    # a one-hour exam. A spelled-out unit in the header (``allowed_duration_
    # seconds: 5400``) is honoured before falling back to that default.
    unit = (match.group("unit") or match.group("word") or "m").lower()
    return int(value * _DURATION_UNITS.get(unit, 60))


def _scan_asks(text: str) -> int | None:
    match = _ASK_RE.search(text)
    return int(match.group("value")) if match else None


def _as_optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ExamDefinitionError(
            f"expected an integer limit, got {value!r}"
        ) from exc


__all__ = ["ExamDefinitionLoader"]
