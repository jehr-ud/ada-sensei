"""Authoritative exam definition resolution (RQ-EXM-002).

The instructor's statement is the only source of exam requirements. It may be
Markdown, a structured JSON specification, or a PDF; all three normalize into one
``ExamDefinition`` and the original statement is always preserved so the
normalized requirements stay reviewable (spec.md §Exam definition and
documentation).

The loader is deterministic: the same statement always yields the same exam id
and the same ``req://`` ids, because both are derived from the statement text.
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

#: Markdown sections whose bullets are the functional requirements.
_REQUIREMENT_HEADINGS = (
    "requirement",
    "requirements",
    "functional requirement",
    "functional requirements",
    "requisitos",
    "requisitos funcionales",
)


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
        """Extract requirements, title, and limits from a Markdown statement."""
        requirements: list[dict] = []
        in_requirements = False
        title = ""
        front: list[str] = []
        for raw_line in text.splitlines():
            heading = _HEADING_RE.match(raw_line)
            if heading:
                label = heading.group("text").strip().lower().rstrip(":")
                in_requirements = label in _REQUIREMENT_HEADINGS
                if not title and not in_requirements and label:
                    title = heading.group("text").strip()
                continue
            if in_requirements:
                bullet = _BULLET_RE.match(raw_line)
                if bullet is None:
                    continue
                body = bullet.group("text").strip()
                if not body or body.startswith("<!--"):
                    continue
                requirements.append(
                    ExamDefinitionLoader._markdown_requirement(
                        body, len(requirements)
                    )
                )
                continue
            front.append(raw_line)
        header = "\n".join(front)
        return {
            "title": title,
            "requirements": requirements,
            "allowed_duration_seconds": _scan_duration(header),
            "allowed_ask_count": _scan_asks(header),
        }

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
