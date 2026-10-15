from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .config import Config
from .models import AssistanceLevel, Turn
from .urns import URN

MAX_TURNS = 60
SESSION_ID_ANON = "anonymous"


class SessionState(BaseModel):
    student_id: str | None = None
    project_id: str | None = None
    attempt_id: str | None = None
    #: Set while an exam is running so ``/ask`` and ``Finish Exam`` can find the
    #: attempt without the student restating its id (RQ-EXM-001, RQ-EXM-004).
    exam_attempt_id: str | None = None
    current_exercise_id: str | None = None
    assistance_level: AssistanceLevel = AssistanceLevel.guiding_question
    conversation: list[Turn] = []
    last_classification: str | None = None


class SessionContext:
    def __init__(
        self, config: Config | None = None, data_dir: Path | None = None
    ) -> None:
        self.config = config
        self._data_dir = Path(
            data_dir
            or (config.data_dir if config else None)
            or Path(os.getenv("ADA_SENSEI_DATA_DIR") or ".")
        )
        self._session_dir = self._data_dir / "sessions"
        self.state = SessionState()

    @property
    def student_id(self) -> str | None:
        return self.state.student_id

    @property
    def project_id(self) -> str | None:
        return self.state.project_id

    @property
    def attempt_id(self) -> str:
        return self.state.attempt_id or ""

    @attempt_id.setter
    def attempt_id(self, value: str | None) -> None:
        self.state.attempt_id = value

    @property
    def current_exercise_id(self) -> str | None:
        return self.state.current_exercise_id

    @current_exercise_id.setter
    def current_exercise_id(self, value: str | None) -> None:
        self.state.current_exercise_id = value

    @property
    def exam_attempt_id(self) -> str | None:
        return self.state.exam_attempt_id

    @exam_attempt_id.setter
    def exam_attempt_id(self, value: str | None) -> None:
        self.state.exam_attempt_id = value

    def clear_exam(self) -> None:
        """Leave exam mode: no further ``/ask`` is attributed to the exam."""
        self.state.exam_attempt_id = None

    @property
    def assistance_level(self) -> AssistanceLevel:
        return self.state.assistance_level

    @assistance_level.setter
    def assistance_level(self, value: AssistanceLevel) -> None:
        self.state.assistance_level = value

    @property
    def conversation(self) -> list[Turn]:
        return self.state.conversation

    @property
    def last_classification(self) -> str | None:
        return self.state.last_classification

    @last_classification.setter
    def last_classification(self, value: str | None) -> None:
        self.state.last_classification = value

    @property
    def session_key(self) -> str:
        if self.state.student_id:
            return self.state.student_id.rsplit("://", 1)[-1]
        return SESSION_ID_ANON

    def set_student(self, student_id: str | None) -> None:
        self.state.student_id = student_id
        if student_id:
            saved = self._load_state()
            if saved:
                self.state = saved
                self.state.student_id = student_id

    def set_project(self, path: str | Path | None) -> None:
        if path is None:
            self.state.project_id = None
            return
        resolved = str(Path(path).expanduser().resolve())
        self.state.project_id = URN.project_id_from_path(resolved)

    def set_exercise(self, exercise_id: str) -> None:
        self.state.current_exercise_id = exercise_id
        self.assistance_level = AssistanceLevel.guiding_question

    def add_turn(self, role: str, content: str) -> None:
        self.state.conversation.append(Turn(role=role, content=content))
        if len(self.state.conversation) > MAX_TURNS:
            self.state.conversation = self.state.conversation[-MAX_TURNS:]

    def advance_assistance(self) -> AssistanceLevel:
        order = list(AssistanceLevel)
        current = self.assistance_level
        if current in order:
            idx = min(order.index(current) + 1, len(order) - 1)
            self.assistance_level = order[idx]
        return self.assistance_level

    def persist(self) -> None:
        self._session_dir.mkdir(parents=True, exist_ok=True)
        path = self._session_dir / f"{self.session_key}.json"
        payload = self.state.model_dump_json()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload)
        os.replace(tmp, path)

    def _load_state(self) -> SessionState | None:
        path = self._session_dir / f"{self.session_key}.json"
        if not path.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(path.read_text())
            return SessionState.model_validate(data)
        except Exception:
            return None
