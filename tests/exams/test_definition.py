"""RQ-EXM-002: the loader resolves Markdown, JSON and PDF exam statements."""

from __future__ import annotations

import json

import pytest
from ada_sensei.exams.definition import ExamDefinitionLoader
from ada_sensei.exams.models import StatementFormat
from exams_helpers import STATEMENT_MARKDOWN, make_statement_pdf

JSON_STATEMENT = json.dumps(
    {
        "title": "JSON exam",
        "requirements": [
            {
                "requirement_id": "req://fr1",
                "description": "repository with CRUD operations",
                "weight": 1.0,
            }
        ],
        "allowed_duration_seconds": 3600,
        "allowed_ask_count": 4,
    }
)


def _write(tmp_path, name, body) -> str:
    path = tmp_path / name
    path.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
    return str(path)


def test_resolves_markdown_json_and_pdf(tmp_path):
    loader = ExamDefinitionLoader()

    md = loader.load(_write(tmp_path, "exam.md", STATEMENT_MARKDOWN))
    assert md.statement_format is StatementFormat.markdown
    assert md.title == "Midterm Android Exam"
    assert md.allowed_duration_seconds == 3600
    assert md.allowed_ask_count == 4
    assert md.requirements[0].description == "Repository with CRUD operations"
    assert "Midterm Android Exam" in md.original_statement

    js = loader.load(_write(tmp_path, "exam.json", JSON_STATEMENT))
    assert js.statement_format is StatementFormat.json
    assert js.requirements[0].requirement_id == "req://fr1"
    assert js.allowed_duration_seconds == 3600
    assert js.title == "JSON exam"
    assert json.loads(js.original_statement)["requirements"][0]["weight"] == 1.0

    pdf = loader.load(
        _write(tmp_path, "exam.pdf", make_statement_pdf(STATEMENT_MARKDOWN))
    )
    assert pdf.statement_format is StatementFormat.pdf
    assert pdf.allowed_ask_count == 4
    assert pdf.requirements[0].description == "Repository with CRUD operations"
    assert "Requirements" in pdf.original_statement


def test_same_statement_source_yields_same_exam_id(tmp_path):
    loader = ExamDefinitionLoader()
    path = str(tmp_path / "exam.md")
    _write(tmp_path, "exam.md", STATEMENT_MARKDOWN)
    assert loader.load(path).exam_id == loader.load(path).exam_id
    different = _write(
        tmp_path,
        "other.md",
        STATEMENT_MARKDOWN.replace("repository", "network"),
    )
    assert loader.load(path).exam_id != loader.load(different).exam_id


def test_missing_statement_is_an_error(tmp_path):
    from ada_sensei.exams.models import ExamDefinitionError

    with pytest.raises(ExamDefinitionError):
        ExamDefinitionLoader().load(str(tmp_path / "missing.md"))


def test_inline_statement_resolves_without_a_file():
    """The CLI advertises inline statements; the loader must honour that."""
    definition = ExamDefinitionLoader().load_text(STATEMENT_MARKDOWN)
    assert definition.statement_format is StatementFormat.markdown
    assert definition.title == "Midterm Android Exam"
    assert definition.allowed_duration_seconds == 3600
    assert definition.allowed_ask_count == 4
    assert definition.requirements
    assert STATEMENT_MARKDOWN.strip() in definition.original_statement


def test_inline_json_statement_resolves():
    definition = ExamDefinitionLoader().load_text(
        JSON_STATEMENT, statement_format=StatementFormat.json
    )
    assert definition.statement_format is StatementFormat.json
    assert definition.requirements[0].requirement_id == "req://fr1"


def test_inline_statement_cannot_be_pdf():
    from ada_sensei.exams.models import ExamDefinitionError

    with pytest.raises(ExamDefinitionError, match="cannot be PDF"):
        ExamDefinitionLoader().load_text(
            "anything", statement_format=StatementFormat.pdf
        )