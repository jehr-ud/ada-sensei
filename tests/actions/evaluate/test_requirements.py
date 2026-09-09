from __future__ import annotations

from ada_sensei.actions.evaluate import RequirementMatcher
from ada_sensei.models import Evidence, Exercise, Requirement


class Fixtures:
    @staticmethod
    def make_exercise(req_ids, summaries):
        requirements = [
            Requirement(id=rid, summary=summary)
            for rid, summary in zip(req_ids, summaries, strict=True)
        ]
        return Exercise(
            id="exercise://e1",
            student_id="student://s1",
            project_id="project://p1",
            requirements=requirements,
        )


def test_match_exercise_reqs(tmp_path):
    ex = Fixtures.make_exercise(["req://r1"], ["Task repository list"])
    build = Evidence(source="build", type="compilation", status="pass")
    structure = Evidence(
        source="file",
        type="structure",
        status="pass",
        file="app/src/main/java/TaskRepository.kt",
    )
    match = RequirementMatcher(ex, build).match(
        {"structure": [structure], "unit_test": []}
    )
    assert match
    assert match[0].requirement_id == "req://r1"
    assert match[0].dimension == "functional_requirements"
    assert match[0].score is not None


def test_match_subweights_normalized(tmp_path):
    ex = Fixtures.make_exercise(["req://r1", "req://r2"], ["one", "two"])
    build = Evidence(source="build", type="compilation", status="pass")
    match = RequirementMatcher(ex, build).match({"structure": [], "unit_test": []})
    assert len(match) == 2
    assert abs(sum(c.weight for c in match) - 1.0) < 1e-6


def test_no_exercise_no_criteria(tmp_path):
    match = RequirementMatcher(None, None).match({"structure": [], "unit_test": []})
    assert match == []


def test_build_failure_marks_not_evaluated(tmp_path):
    ex = Fixtures.make_exercise(["req://r1"], ["list tasks"])
    build = Evidence(source="build", type="compilation", status="fail")
    match = RequirementMatcher(ex, build).match({"structure": [], "unit_test": []})
    assert match
    # build failure -> no strong evidence -> requirement_score None or 0
    assert match[0].score in (None, 0)