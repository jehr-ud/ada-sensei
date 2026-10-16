# ADR-025 — GUI Action Registry, Learning-Stage Header, Version Display, Bilingual Chrome

Status: Accepted.

## Context

The TUI selector exposed only 6 actions (ask/practice/examples/evaluate/
exam-init/exam-finish) while the product supports 9+ student-facing intents
(plus help); the spec already required learn/diagnose in the selector. The GUI
showed no learning stage and no application version, and GUI chrome had no
localized string source. Separate hardcoded action lists risked CLI/TUI drift.

## Decision

1. Centralize student-facing actions in `ada_sensei/cli/action_registry.py`
   (stable ids, es/en names/descriptions/hints, command factory, availability
   rules). GUI, parser `AVAILABLE_ACTIONS`, and help derive from it.
2. Resolve the displayed stage read-only in `ada_sensei/learning/status.py`
   from the persisted `LearningProfile` + locale catalog; render in
   `SessionBar`/`SessionFooter` at startup and after each completed worker.
   Never advance or infer mastery in presentation code.
3. Serve the version from `ada_sensei/version.py` (installed metadata,
   `__version__` fallback); expose via `CommandRouter.app_version()`; render
   in header + footer. Never hardcode, never LLM-fetch.
4. Localize GUI chrome in `ada_sensei/locale/ui_strings.py` (es-CO/en-US,
   deterministic en-US fallback) + per-action registry labels; refresh on
   locale change without touching learning data. Ids/versions untranslated.
5. Block duplicate submissions with a busy guard; keep unavailable actions
   visible with prerequisite reasons.

## Consequences

GUI exposes all 10 registry actions through existing workflows; stage/version
are authoritative and refresh correctly; es-CO/en-US work throughout without
progress resets. New actions require one registry entry + tests.
