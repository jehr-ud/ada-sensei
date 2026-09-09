from __future__ import annotations

from ..models import EvaluationResult, LearningEvent, StudentProfile
from .json_store import JsonStore

KIND = "student"


class ConfirmationRequiredError(Exception):
    pass


class HistoryStore:
    def __init__(self, data_dir: str) -> None:
        self.store = JsonStore(data_dir)

    @staticmethod
    def _urn(student_id: str) -> str:
        return JsonStore.ensure_urn(KIND, student_id)

    def has(self, student_id: str) -> bool:
        return self.store.read(self._urn(student_id)) is not None

    def get(self, student_id: str) -> StudentProfile | None:
        uri = self._urn(student_id)
        return JsonStore.from_payload(StudentProfile, self.store.read(uri))

    def create_profile(
        self, student_id: str, confirmed: bool = False
    ) -> StudentProfile:
        if not confirmed:
            raise ConfirmationRequiredError(
                "student record creation requires explicit confirmation"
            )
        uri = self._urn(student_id)
        if self.store.read(uri) is None:
            profile = StudentProfile(student_id=uri)
            self.store.write(uri, JsonStore.to_payload(profile))
            return profile
        return JsonStore.from_payload(StudentProfile, self.store.read(uri))

    def _update(self, student_id: str, fn) -> None:
        uri = self._urn(student_id)
        profile = JsonStore.from_payload(StudentProfile, self.store.read(uri))
        if profile is None:
            return
        fn(profile)
        self.store.write(uri, JsonStore.to_payload(profile))

    def set_name(self, student_id: str, name: str) -> None:
        self._update(student_id, lambda p: setattr(p, "name", name))

    def append_event(self, student_id: str, event: LearningEvent) -> None:
        self._update(student_id, lambda p: p.events.append(event))

    def record_exercise_attempted(
        self, student_id: str, exercise_id: str, attempt_id: str | None = None
    ) -> None:
        self.append_event(
            student_id,
            LearningEvent(
                type="exercise_attempted",
                exercise_id=exercise_id,
                attempt_id=attempt_id,
                payload={"exercise_id": exercise_id, "attempt_id": attempt_id},
            ),
        )

    def record_exercise_result(
        self, student_id: str, exercise_id: str, passed: bool
    ) -> None:
        self.append_event(
            student_id,
            LearningEvent(
                type="exercise_result",
                exercise_id=exercise_id,
                payload={"passed": passed},
            ),
        )

    def record_hint_requested(
        self, student_id: str, exercise_id: str, hint: str
    ) -> None:
        self.append_event(
            student_id,
            LearningEvent(
                type="hint_requested", exercise_id=exercise_id, payload={"hint": hint}
            ),
        )

    def record_recurring_error(self, student_id: str, error: str) -> None:
        def add(profile: StudentProfile) -> None:
            if error not in profile.recurring_errors:
                profile.recurring_errors.append(error)

        self._update(student_id, add)

    def add_strength(self, student_id: str, strength: str) -> None:
        def add(profile: StudentProfile) -> None:
            if strength not in profile.strengths:
                profile.strengths.append(strength)

        self._update(student_id, add)

    def add_weakness(self, student_id: str, weakness: str) -> None:
        def add(profile: StudentProfile) -> None:
            if weakness not in profile.weaknesses:
                profile.weaknesses.append(weakness)

        self._update(student_id, add)

    def append_evaluation(self, student_id: str, result: EvaluationResult) -> None:
        self.append_event(
            student_id,
            LearningEvent(
                type="evaluation_completed",
                student_id=self._urn(student_id),
                project_id=result.project_id,
                exercise_id=result.exercise_id,
                attempt_id=result.attempt_id,
                result_id=result.id,
                payload={"overall_score": result.overall_score},
            ),
        )

    def summary(self, student_id: str) -> str:
        profile = self.get(student_id)
        if profile is None:
            return "(no profile)"
        return profile.summary
