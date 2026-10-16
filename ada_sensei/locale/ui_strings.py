"""Localized UI strings for the CLI/TUI selector and status header.

Covers spec 0010 RQ-LNG-005 for the graphical action selector, learning-stage
status, version label, and loading/error/empty states in ``es-CO`` and
``en-US``. Stable machine identifiers (action ids, stage ids, version values)
are never translated here.

Fallback: missing keys or unknown locales resolve deterministically to
``en-US`` (FALLBACK_LOCALE), mirroring ``LocaleService`` behavior.
"""

from __future__ import annotations

from .models import FALLBACK_LOCALE

_UI_STRINGS: dict[str, dict[str, str]] = {
    "en-US": {
        "selector_title": "Action",
        "selector_help": "Select an action, type your input, press Enter.",
        "stage_label": "Stage",
        "stage_current": "Current stage",
        "stage_not_started": "Learning path not started",
        "stage_unknown": "Stage unavailable",
        "version_label": "ADA Sensei v{version}",
        "locale_label": "Language",
        "loading": "Running…",
        "evaluating": "Evaluating…",
        "examining": "Examining…",
        "waiting_confirmation": "Waiting for confirmation",
        "ready": "Ready",
        "error": "Error",
        "cancelled": "Cancelled",
        "busy_blocked": "An action is already running. Wait or press Ctrl+C to cancel.",
        "prereq_project": "Requires an active project. Set one with /project <path> or --project <path>.",
        "prereq_topic": "Enter a topic to continue.",
        "prereq_question": "Enter a question to continue.",
        "prereq_statement": "Enter an exam statement (file path or text) to continue.",
        "prereq_locale": "Enter a locale: es-CO or en-US.",
    },
    "es-CO": {
        "selector_title": "Acción",
        "selector_help": "Seleccione una acción, escriba su entrada y pulse Enter.",
        "stage_label": "Etapa",
        "stage_current": "Etapa actual",
        "stage_not_started": "Ruta de aprendizaje no iniciada",
        "stage_unknown": "Etapa no disponible",
        "version_label": "ADA Sensei versión {version}",
        "locale_label": "Idioma",
        "loading": "Ejecutando…",
        "evaluating": "Evaluando…",
        "examining": "Examinando…",
        "waiting_confirmation": "Esperando confirmación",
        "ready": "Listo",
        "error": "Error",
        "cancelled": "Cancelado",
        "busy_blocked": "Ya hay una acción en curso. Espere o pulse Ctrl+C para cancelar.",
        "prereq_project": "Requiere un proyecto activo. Use /project <ruta> o --project <ruta>.",
        "prereq_topic": "Ingrese un tema para continuar.",
        "prereq_question": "Ingrese una pregunta para continuar.",
        "prereq_statement": "Ingrese el enunciado del examen (ruta o texto) para continuar.",
        "prereq_locale": "Ingrese un idioma: es-CO o en-US.",
    },
}


def get_ui_string(key: str, locale: str | None) -> str:
    """Return the localized UI string for ``key`` with deterministic fallback."""
    requested = locale if locale in _UI_STRINGS else FALLBACK_LOCALE
    table = _UI_STRINGS.get(requested, _UI_STRINGS[FALLBACK_LOCALE])
    if key in table:
        return table[key]
    return _UI_STRINGS[FALLBACK_LOCALE].get(key, key)


def supported_ui_locales() -> tuple[str, ...]:
    return tuple(_UI_STRINGS.keys())


__all__ = ["get_ui_string", "supported_ui_locales"]
