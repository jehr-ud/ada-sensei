"""Typed tutoring models (spec 0011 §§4–5).

``Recommendation`` uses stable action IDs and validated parameters — never
localized labels as executable values. Rendering is localized via
:meth:`Recommendation.display`; execution always goes through the existing
action workflow after explicit student selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Recommendation:
    """One optional, validated next-action suggestion."""

    action_id: str
    params: dict[str, str] = field(default_factory=dict)
    rationale_es: str = ""
    rationale_en: str = ""
    objective_es: str = ""
    objective_en: str = ""
    prerequisites_es: str = ""
    prerequisites_en: str = ""

    def rationale(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.rationale_es or self.rationale_en
        return self.rationale_en or self.rationale_es

    def objective(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.objective_es or self.objective_en
        return self.objective_en or self.objective_es

    def prerequisites(self, locale: str | None) -> str:
        if locale == "es-CO":
            return self.prerequisites_es or self.prerequisites_en
        return self.prerequisites_en or self.prerequisites_es

    def display(self, locale: str | None) -> str:
        """Localized one-block rendering: label + rationale + how to run."""
        from ..cli.action_registry import get_action
        from ..locale.ui_strings import get_ui_string

        action = get_action(self.action_id)
        label = action.label(locale) if action else self.action_id
        prefix = get_ui_string("next_step_prefix", locale)
        how = get_ui_string("next_step_how", locale)
        lines = [f"{prefix}: {label} ({self.action_id})"]
        reason = self.rationale(locale)
        if reason:
            lines.append(reason)
        goal = self.objective(locale)
        if goal:
            lines.append(goal)
        prereq = self.prerequisites(locale)
        if prereq:
            lines.append(prereq)
        lines.append(how)
        return "\n".join(lines)


__all__ = ["Recommendation"]
