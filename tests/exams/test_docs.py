"""RQ-EXM-008/009: student documentation and generated start docs."""

from __future__ import annotations

from ada_sensei.exams.docs import (
    ARCHITECTURE_NAME,
    CONTEXT_NAME,
    GENERATED_MARKER,
    README_NAME,
    RUBRIC_NAME,
    SUMMARY_NAME,
    ExamDocs,
    ExamDocsWriter,
    is_generated,
)
from exams_helpers import make_definition, make_project


def test_student_documentation_accepted(tmp_path):
    project = make_project(tmp_path)
    docs_dir = project / "docs" / "exam"
    docs_dir.mkdir(parents=True, exist_ok=True)
    notes = docs_dir / "notes.md"
    notes.write_text("# Design decisions\nWe separated layers.\n", encoding="utf-8")
    (project / "docs" / "README.md").write_text("project readme", encoding="utf-8")

    definition = make_definition()
    matched = definition.documentation_paths(project)
    assert matched == [notes]
    assert (project / "docs" / "README.md") not in matched

    exam_docs = ExamDocs(project, definition.exam_id)
    exam_docs.write(
        "student-notes.md", "generated mirror of the accepted documentation"
    )
    assert notes.read_text(encoding="utf-8").startswith("# Design decisions")
    assert is_generated(exam_docs.path("student-notes.md"))


def test_start_docs_created(tmp_path):
    project = make_project(tmp_path)
    definition = make_definition()
    writer = ExamDocsWriter(project)
    docs = ExamDocs(project, definition.exam_id)

    written = writer.write_start_docs(definition, docs)

    names = {path.name for path in written}
    assert names == {README_NAME, CONTEXT_NAME, RUBRIC_NAME}
    for path in written:
        body = path.read_text(encoding="utf-8")
        assert GENERATED_MARKER in body
    assert definition.title in docs.path(README_NAME).read_text(encoding="utf-8")
    assert not docs.path(ARCHITECTURE_NAME).exists()
    assert not docs.path(SUMMARY_NAME).exists()