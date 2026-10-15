"""RQ-EXM-014/023/030: architecture analysis is evidence-grounded."""

from __future__ import annotations

from ada_sensei.evaluation import EvidenceContext
from ada_sensei.exams.architecture import ArchitectureAnalyzer
from ada_sensei.exams.models import ArchitectureClaim
from ada_sensei.models import Evidence, UnsupportedClaim
from exams_helpers import make_definition, make_project

STRUCTURE = [
    Evidence(
        id="ev://domain",
        source="structure",
        type="structure",
        status="pass",
        file="app/src/main/java/com/example/app/domain/Task.kt",
        message="domain file",
    ),
    Evidence(
        id="ev://repo",
        source="structure",
        type="structure",
        status="pass",
        file="app/src/main/java/com/example/app/data/TaskRepository.kt",
        message="data file",
    ),
    Evidence(
        id="ev://ui",
        source="structure",
        type="structure",
        status="pass",
        file="app/src/main/java/com/example/app/ui/TaskViewModel.kt",
        message="ui file",
    ),
]


def _analyze(project, inferred=None, with_docs=True):
    definition = make_definition()
    if with_docs:
        docs = project / "docs" / "exam"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "design.md").write_text(
            "# Architecture decision\nSealed layers.\n", encoding="utf-8"
        )
    analyzer = ArchitectureAnalyzer(project)
    evidence = EvidenceContext(evidence=STRUCTURE, project_id="project://p1")
    return analyzer.analyze(evidence, definition, inferred_claims=inferred)


def test_observed_documented_inferred(tmp_path):
    project = make_project(tmp_path)
    report = _analyze(
        project,
        inferred=[
            ArchitectureClaim(
                claim="the app uses a repository boundary",
                kind="inferred",
                evidence_refs=["ev://repo"],
            )
        ],
    )
    assert report.observed
    assert report.documented
    assert any("docs/exam/design.md" in d for d in report.documentation_files)
    assert any(c.kind == "inferred" for c in report.inferred)
    assert "com.example.app.domain" in report.packages
    assert not report.unsupported_claims


def test_report_is_evidence_grounded(tmp_path):
    project = make_project(tmp_path)
    report = _analyze(project)
    claims = [c.claim for c in report.claims if c.kind == "observed"]
    assert claims
    narrative = report.narrative
    assert f"Observed in the project: {len(report.observed)}" in narrative
    assert report.packages == sorted(report.packages)
    assert all(claim.evidence_refs for claim in report.inferred)


def test_no_unsupported_claims(tmp_path):
    project = make_project(tmp_path)
    report = _analyze(
        project,
        inferred=[
            ArchitectureClaim(
                claim="grounded inference",
                kind="inferred",
                evidence_refs=["ev://domain"],
            ),
            ArchitectureClaim(
                claim="invented component",
                kind="inferred",
                evidence_refs=["ev://missing"],
            ),
        ],
    )
    assert len(report.unsupported_claims) == 1
    (grounded,) = report.inferred
    assert grounded.claim == "grounded inference"
    (unsupported,) = report.unsupported_claims
    assert unsupported.claim == "invented component"
    assert isinstance(unsupported, UnsupportedClaim)
    assert [c.claim for c in report.claims if c.kind == "inferred"] == [
        "grounded inference"
    ]