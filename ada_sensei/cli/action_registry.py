"""Centralized student-facing action registry (single source of truth).

Every action supported by the CLI/TUI selector is defined here exactly once:
stable id, localized display names/descriptions, input hints, availability
prerequisites, confirmation requirements, and the typed-command factory that
routes to the existing application workflows via ``CommandRouter``.

The GUI selector, the slash-command parser, and help text all derive from this
registry so the CLI, TUI, and docs cannot drift apart. Business logic stays in
the existing action services; this module only describes actions and builds the
corresponding typed command objects.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDefinition:
    """One student-facing action."""

    id: str
    name_es: str
    name_en: str
    desc_es: str
    desc_en: str
    hint_es: str
    hint_en: str
    slash: str
    requires_confirmation: bool = False
    requires_project: bool = False
    requires_text: bool = False
    help_es: str = ""
    help_en: str = ""

    def label(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.name_es
        return self.name_en

    def description(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.desc_es
        return self.desc_en

    def hint(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.hint_es
        return self.hint_en

    def help(self, locale: str | None) -> str:
        text = self.help_es if locale == "es-CO" else self.help_en
        return text or self.description(locale)


_ACTIONS: list[ActionDefinition] = [
    ActionDefinition(
        id="ask",
        name_es="Preguntar",
        name_en="Ask",
        desc_es="Haz una pregunta sobre tu etapa actual.",
        desc_en="Ask a question about your current stage.",
        hint_es="pregunta… p. ej. ¿por qué LazyColumn no se actualiza?",
        hint_en="ask… e.g. why does LazyColumn not update?",
        slash="/ask",
        requires_text=True,
        help_es="Uso: /ask <pregunta>. Requiere escribir una pregunta.",
        help_en="Usage: /ask <question>. Requires a question.",
    ),
    ActionDefinition(
        id="practice",
        name_es="Practicar",
        name_en="Practice",
        desc_es="Genera un ejercicio adaptado a tu etapa.",
        desc_en="Generate an exercise adapted to your stage.",
        hint_es="tema… p. ej. compose-state (opcional)",
        hint_en="enter a topic… e.g. compose-state (optional)",
        slash="/practice",
        help_es="Uso: /practice [--topic T] [--difficulty D]. El tema es opcional.",
        help_en="Usage: /practice [--topic T] [--difficulty D]. Topic is optional.",
    ),
    ActionDefinition(
        id="examples",
        name_es="Ejemplos",
        name_en="Examples",
        desc_es="Genera un ejemplo didáctico del tema.",
        desc_en="Generate a teachable example for the topic.",
        hint_es="tema… p. ej. ViewModel",
        hint_en="enter a topic… e.g. ViewModel",
        slash="/examples",
        requires_text=True,
        help_es="Uso: /examples <tema>. Requiere un tema.",
        help_en="Usage: /examples <topic>. Requires a topic.",
    ),
    ActionDefinition(
        id="evaluate",
        name_es="Evaluar proyecto",
        name_en="Evaluate project",
        desc_es="Evalúa el proyecto activo con evidencias.",
        desc_en="Evaluate the active project with evidence.",
        hint_es="evalúa el proyecto actual (Enter para ejecutar)",
        hint_en="evaluate the current project (Enter to run)",
        slash="/evaluate",
        requires_confirmation=True,
        requires_project=True,
        help_es="Uso: /evaluate [--yes]. Requiere proyecto activo y confirmación.",
        help_en="Usage: /evaluate [--yes]. Requires active project and confirmation.",
    ),
    ActionDefinition(
        id="exam-init",
        name_es="Iniciar examen",
        name_en="Start exam",
        desc_es="Inicia un examen desde un enunciado.",
        desc_en="Start an exam from a statement.",
        hint_es="enunciado… p. ej. docs/exam.md (Enter para iniciar)",
        hint_en="exam statement… e.g. docs/exam.md (Enter to start)",
        slash="/exam-init",
        requires_confirmation=True,
        requires_text=True,
        help_es="Uso: /exam-init <enunciado>. Requiere confirmación.",
        help_en="Usage: /exam-init <statement>. Requires confirmation.",
    ),
    ActionDefinition(
        id="exam-finish",
        name_es="Terminar examen",
        name_en="Finish exam",
        desc_es="Termina el examen activo y genera el informe.",
        desc_en="Finish the active exam and generate the report.",
        hint_es="termina el examen y genera el informe (Enter para ejecutar)",
        hint_en="finish the exam and generate the report (Enter to run)",
        slash="/exam-finish",
        requires_confirmation=True,
        help_es="Uso: /exam-finish. Requiere un examen activo y confirmación.",
        help_en="Usage: /exam-finish. Requires an active exam and confirmation.",
    ),
    ActionDefinition(
        id="learn",
        name_es="Ver plan de aprendizaje",
        name_en="View learning plan",
        desc_es="Explica los conceptos clave de tu etapa actual.",
        desc_en="Explain the key concepts of your current stage.",
        hint_es="tema… p. ej. estado en Compose (opcional)",
        hint_en="topic… e.g. Compose state (optional)",
        slash="/learn",
        help_es="Uso: /learn [tema]. Sin tema usa tu etapa actual.",
        help_en="Usage: /learn [topic]. Without a topic uses your current stage.",
    ),
    ActionDefinition(
        id="diagnose",
        name_es="Diagnóstico",
        name_en="Diagnostic",
        desc_es="Ejecuta un diagnóstico breve de tu etapa.",
        desc_en="Run a brief diagnostic of your stage.",
        hint_es="etapa… p. ej. kotlin-fundamentals (opcional)",
        hint_en="stage… e.g. kotlin-fundamentals (optional)",
        slash="/diagnose",
        help_es="Uso: /diagnose [etapa]. Sin etapa usa tu etapa actual.",
        help_en="Usage: /diagnose [stage]. Without a stage uses your current stage.",
    ),
    ActionDefinition(
        id="language",
        name_es="Cambiar idioma",
        name_en="Change language",
        desc_es="Cambia el idioma sin perder tu progreso.",
        desc_en="Change language without losing progress.",
        hint_es="idioma… es-CO o en-US",
        hint_en="locale… es-CO or en-US",
        slash="/language",
        help_es="Uso: /language <es-CO|en-US>. No altera tu progreso.",
        help_en="Usage: /language <es-CO|en-US>. Does not alter progress.",
    ),
    ActionDefinition(
        id="help",
        name_es="Ayuda",
        name_en="Help",
        desc_es="Muestra los comandos y ejemplos de uso.",
        desc_en="Show commands and usage examples.",
        hint_es="muestra la ayuda (Enter para ver)",
        hint_en="show help (Enter to view)",
        slash="/help",
        help_es="Uso: /help. Muestra esta ayuda.",
        help_en="Usage: /help. Shows this help.",
    ),
]

_BY_ID: dict[str, ActionDefinition] = {a.id: a for a in _ACTIONS}


def get_actions() -> list[ActionDefinition]:
    """Return all registered student-facing actions in selector order."""
    return list(_ACTIONS)


def get_action(action_id: str) -> ActionDefinition | None:
    return _BY_ID.get(action_id)


def action_ids() -> tuple[str, ...]:
    return tuple(a.id for a in _ACTIONS)


def build_command(action_id: str, text: str, *, confirmed: bool = False):
    """Build the typed command for ``action_id`` from free text.

    Raises ``ValueError`` for unknown actions. Mirrors the slash-command
    contract so GUI free-text routing and slash parsing produce identical
    command objects dispatched through the shared ``CommandRouter``.
    """
    from .commands import (
        AskCommand,
        DiagnoseCommand,
        EvaluateCommand,
        ExamineFinishCommand,
        ExamineStartCommand,
        ExamplesCommand,
        HelpCommand,
        LanguageCommand,
        LearnCommand,
        PracticeCommand,
    )

    cleaned = (text or "").strip()
    if action_id == "ask":
        return AskCommand(question=cleaned)
    if action_id == "practice":
        return PracticeCommand(topic=cleaned or None)
    if action_id == "examples":
        return ExamplesCommand(topic=cleaned)
    if action_id == "evaluate":
        return EvaluateCommand(yes=confirmed)
    if action_id == "exam-init":
        return ExamineStartCommand(statement=cleaned, yes=confirmed)
    if action_id == "exam-finish":
        return ExamineFinishCommand(yes=confirmed)
    if action_id == "learn":
        return LearnCommand(topic=cleaned or None)
    if action_id == "diagnose":
        return DiagnoseCommand(stage_id=cleaned or None)
    if action_id == "language":
        return LanguageCommand(locale=cleaned or None)
    if action_id == "help":
        return HelpCommand(scope=None)
    raise ValueError(f"unknown action: {action_id!r}")


def check_availability(
    action_id: str,
    *,
    project_path: str | None,
    exam_active: bool = False,
    locale: str | None = None,
) -> tuple[bool, str]:
    """Return ``(available, reason)`` for an action given session context.

    Unavailable actions are still shown (discoverability) with an explicit
    prerequisite explanation; ``reason`` is empty when available.
    """
    from ..locale.ui_strings import get_ui_string

    action = get_action(action_id)
    if action is None:
        return False, f"unknown action: {action_id!r}"
    if action.requires_project and not (project_path not in (None, "", ".")):
        return False, get_ui_string("prereq_project", locale)
    if action_id == "exam-finish" and not exam_active:
        if locale == "es-CO":
            return False, "No hay un examen activo. Inicie uno con /exam-init."
        return False, "No active exam. Start one with /exam-init."
    return True, ""


__all__ = [
    "ActionDefinition",
    "action_ids",
    "build_command",
    "check_availability",
    "get_action",
    "get_actions",
]
