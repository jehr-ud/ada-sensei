"""RQ-EXM-052–063: JSON-only exam definition loading."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from ada_sensei.exams.definition import (
    ExamDefinitionIssue,
    ExamDefinitionLoader,
    ExamDefinitionValidationError,
)
from ada_sensei.exams.models import StatementFormat

VALID_DEFINITION = {
    "schema_version": "1.0",
    "exam_id": "android-midterm",
    "title": "Android Midterm",
    "version": "1.0",
    "description": "Teacher-authored definition",
    "statement_language": "es-CO",
    "allowed_duration_seconds": 3600,
    "allowed_ask_count": 4,
    "documentation_rules": {"accepted_globs": ["docs/**/*.md"]},
    "rubric_ref": "unified-android:v2",
    "requirements": [
        {
            "id": "REQ-AND-001",
            "type": "functional",
            "title": "CRUD repository",
            "description": "The app exposes a repository with CRUD operations.",
            "weight": 0.6,
            "source": {
                "file": "android-midterm.json",
                "section": "Requisitos",
                "reference": "R1",
            },
            "acceptance_criteria": [
                {
                    "id": "AC-001",
                    "description": "Unit tests cover insert, read, update and delete.",
                    "verification": ["unit_test"],
                    "evidence_hints": ["RepositoryTest"],
                }
            ],
            "related_requirements": [],
            "tags": ["repository"],
        },
        {
            "id": "REQ-AND-002",
            "type": "functional",
            "title": "MVVM separation",
            "description": "The ViewModel does not depend on Android views.",
            "weight": 0.4,
            "source": {"file": "android-midterm.json", "section": "Requisitos"},
            "acceptance_criteria": [
                {
                    "id": "AC-002",
                    "description": "ViewModel source contains no android.view imports.",
                    "verification": ["static_analysis", "source_inspection"],
                }
            ],
        },
    ],
}

EXAMPLE = (
    Path(__file__).parents[2]
    / "specs/007-examine/examples/domino-conquista.exam.v2.json"
)


def _payload(**overrides: object) -> dict:
    payload = copy.deepcopy(VALID_DEFINITION)
    payload.update(overrides)
    return payload


def _write(tmp_path, body: str, name: str = "exam.json") -> str:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def _issues(payload: dict) -> list[ExamDefinitionIssue]:
    with pytest.raises(ExamDefinitionValidationError) as exc:
        ExamDefinitionLoader().load_text(json.dumps(payload))
    return list(exc.value.issues)


def test_loads_valid_json_definition_with_typed_requirements(tmp_path):
    raw = json.dumps(VALID_DEFINITION)
    definition = ExamDefinitionLoader().load(_write(tmp_path, raw))

    assert definition.statement_format is StatementFormat.json
    assert definition.exam_id == "android-midterm"
    assert definition.title == "Android Midterm"
    assert definition.rubric_ref == "unified-android:v2"
    assert definition.statement_language == "es-CO"
    assert definition.allowed_duration_seconds == 3600
    assert definition.allowed_ask_count == 4
    assert definition.requirements[0].requirement_type.value == "functional"
    assert definition.requirements[0].source is not None
    assert definition.requirements[0].source.reference == "R1"
    criterion = definition.requirements[0].acceptance_criteria[0]
    assert criterion.id == "AC-001"
    assert [method.value for method in criterion.verification] == ["unit_test"]


def test_preserves_snapshot_and_sha256(tmp_path):
    raw = json.dumps(VALID_DEFINITION, sort_keys=True)
    definition = ExamDefinitionLoader().load(_write(tmp_path, raw))

    assert definition.definition_snapshot == raw
    assert definition.definition_sha256 == hashlib.sha256(raw.encode()).hexdigest()


def test_loads_domino_example():
    definition = ExamDefinitionLoader().load(str(EXAMPLE))

    assert definition.exam_id == "domino-conquista"
    assert definition.rubric_ref == "unified-android:v2"
    assert len(definition.requirements) == 14
    functional = [
        requirement
        for requirement in definition.requirements
        if requirement.requirement_type.value == "functional"
    ]
    assert sum(requirement.weight for requirement in functional) == pytest.approx(1.0)
    assert all(requirement.acceptance_criteria for requirement in definition.requirements)


def test_rejects_non_json_files(tmp_path):
    with pytest.raises(ExamDefinitionValidationError) as exc:
        ExamDefinitionLoader().load(_write(tmp_path, "# exam", "exam.md"))
    assert exc.value.issues[0].code == "unsupported_extension"


def test_rejects_missing_statement(tmp_path):
    with pytest.raises(ExamDefinitionValidationError) as exc:
        ExamDefinitionLoader().load(str(tmp_path / "missing.json"))
    assert exc.value.issues[0].code == "definition_not_found"


def test_rejects_invalid_json_syntax():
    with pytest.raises(ExamDefinitionValidationError) as exc:
        ExamDefinitionLoader().load_text("{not json")
    assert exc.value.issues[0].code == "invalid_json"


def test_reports_required_property_with_json_pointer():
    payload = _payload()
    del payload["title"]

    found = _issues(payload)

    assert any(
        issue.pointer == "/title" and issue.code == "required" for issue in found
    )


def test_rejects_unknown_properties_with_json_pointer():
    payload = _payload(unexpected_property=True)

    found = _issues(payload)

    assert any(
        issue.pointer == "/" and issue.code == "additionalProperties"
        for issue in found
    )


def test_rejects_duplicate_requirement_ids():
    payload = _payload()
    payload["requirements"][1]["id"] = payload["requirements"][0]["id"]

    found = _issues(payload)

    assert any(
        issue.pointer == "/requirements/1/id" and issue.code == "duplicate_id"
        for issue in found
    )


def test_rejects_duplicate_acceptance_criterion_ids():
    payload = _payload()
    payload["requirements"][1]["acceptance_criteria"][0]["id"] = "AC-001"

    found = _issues(payload)

    assert any(
        issue.pointer
        == "/requirements/1/acceptance_criteria/0/id"
        and issue.code == "duplicate_id"
        for issue in found
    )


def test_rejects_invalid_functional_weight_sum():
    payload = _payload()
    payload["requirements"][0]["weight"] = 0.5

    found = _issues(payload)

    assert any(
        issue.pointer == "/requirements"
        and issue.code == "invalid_functional_weights"
        for issue in found
    )


def test_rejects_weight_out_of_range():
    payload = _payload()
    payload["requirements"][0]["weight"] = 1.5

    found = _issues(payload)

    assert any(
        issue.pointer == "/requirements/0/weight" and issue.code == "maximum"
        for issue in found
    )


def test_rejects_criterion_without_verification_method():
    payload = _payload()
    payload["requirements"][0]["acceptance_criteria"][0]["verification"] = []

    found = _issues(payload)

    assert any(
        issue.code in {"minItems", "missing_verification"} for issue in found
    )


def test_rejects_unsupported_verification_method():
    payload = _payload()
    payload["requirements"][0]["acceptance_criteria"][0]["verification"] = [
        "astrology"
    ]

    found = _issues(payload)

    assert any(issue.code == "enum" for issue in found)


def test_rejects_missing_source():
    payload = _payload()
    del payload["requirements"][0]["source"]

    found = _issues(payload)

    assert any(
        issue.pointer == "/requirements/0/source" and issue.code == "missing_source"
        for issue in found
    )


def test_rejects_incompatible_rubric_reference():
    payload = _payload(rubric_ref="exam-default:v1")

    found = _issues(payload)

    assert any(
        issue.pointer == "/rubric_ref" and issue.code == "incompatible_rubric"
        for issue in found
    )


def test_inline_json_statement_resolves_without_a_file():
    definition = ExamDefinitionLoader().load_text(json.dumps(VALID_DEFINITION))

    assert definition.statement_source == "inline"
    assert definition.statement_format is StatementFormat.json


def test_inline_non_json_statement_is_rejected():
    with pytest.raises(ExamDefinitionValidationError) as exc:
        ExamDefinitionLoader().load_text("# Markdown")
    assert exc.value.issues[0].code == "invalid_json"
