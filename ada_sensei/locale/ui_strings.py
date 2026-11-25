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
        "prereq_project": (
            "Requires an active project. Set one with /project <path> or "
            "--project <path>."
        ),
        "prereq_topic": "Enter a topic to continue.",
        "prereq_question": "Enter a question to continue.",
        "prereq_statement": (
            "Enter the exam statement as a validated .json file path or inline "
            "JSON. It must include a title and functional requirements. "
            "Example: /exam-init ~/exams/midterm.json"
        ),
        "exam_start_blocked": "The exam cannot start yet:",
        "exam_start_no_student": (
            "The student name is not configured. Use /name followed by your name."
        ),
        "exam_statement_not_found": (
            "Exam definition not found: {detail}. Pass an existing .json file "
            "path or paste a valid JSON definition."
        ),
        "exam_statement_invalid": (
            "The exam instructions are not valid: {detail}"
        ),
        "exam_start_confirm": (
            "Start exam — review before confirming.\n\n"
            "How to configure the exam:\n"
            "1. Create an exam definition file with a .json extension.\n"
            "2. Include schema_version, exam_id, title, and functional "
            "requirements with stable ids, weights, provenance, and acceptance "
            "criteria.\n"
            "3. Optionally set limits: Allowed duration "
            "(allowed_duration_seconds) and Allowed /ask count "
            "(allowed_ask_count).\n"
            "4. The JSON is validated against the published schema before the "
            "exam starts; errors include the JSON Pointer.\n\n"
            "Starting records the duration and every /ask, and writes "
            "docs/ada-sensei/ into the project.\n\n"
            "To confirm, type yes (or y) and press Enter. To cancel, type no."
        ),
        "exam_finish_confirm": (
            "Finish exam — review before confirming.\n\n"
            "Finishing stops the timer, scores the project (Gradle build, "
            "unit tests, Android Lint, Detekt), and writes a PDF report to "
            "docs/ada-sensei/exams/<exam>/report.pdf in the project.\n\n"
            "To confirm, type yes (or y) and press Enter. To cancel, type no."
        ),
        "evaluate_confirm": (
            "Evaluation runs Gradle build/tests/lint/detekt.\n\n"
            "To confirm, type yes (or y) and press Enter. To cancel, type no."
        ),
        "evaluate_aborted": "Evaluation aborted before running any Gradle task.",
        "exam_start_aborted": "Exam start aborted; no attempt was created.",
        "exam_finish_aborted": "Exam finish aborted; the attempt is still active.",
        "exam_preparing": "Preparing the exam. This can take a few minutes…",
        "exam_start_progress_validating": "Validating exam requirements…",
        "exam_start_progress_toolchain": (
            "Preparing static analysis tools (Gradle, Android Lint, Detekt, "
            "KtLint)…"
        ),
        "exam_start_progress_ready": "Tools ready. Creating the exam attempt…",
        "exam_progress_inspecting": "Inspecting the project…",
        "exam_progress_build": "Running Gradle build…",
        "exam_progress_unit_tests": "Running unit tests…",
        "exam_progress_lint": "Running Android Lint…",
        "exam_progress_detekt": "Running Detekt…",
        "exam_progress_interpreting": "Interpreting results with the model…",
        "exam_progress_report": "Generating the PDF report…",
        "confirm_yes": "Confirm",
        "confirm_no": "Cancel",
        "preflight_failed": (
            "Cannot start the exam: the current project cannot be evaluated."
        ),
        "preflight_no_project": (
            "No active project is configured. Set one with /project <path> or "
            "in the config file."
        ),
        "preflight_missing_path": "The project path does not exist: {detail}",
        "preflight_not_directory": (
            "The project path is not a directory: {detail}"
        ),
        "preflight_no_gradle": (
            "No Gradle wrapper (gradlew) or global Gradle was found. {detail}"
        ),
        "preflight_no_android_manifest": (
            "No AndroidManifest.xml was found in the project."
        ),
        "preflight_no_build_file": (
            "No build.gradle or build.gradle.kts was found in the project."
        ),
        "preflight_no_jdk": "No JDK 17+ was found. {detail}",
        "preflight_no_android_sdk": (
            "No Android SDK was found. Set ANDROID_HOME/ANDROID_SDK_ROOT or "
            "sdk.dir in local.properties."
        ),
        "preflight_no_instructions": (
            "No exam instructions file is configured. Set one with "
            "/instructions <path>."
        ),
        "preflight_instructions_not_markdown": (
            "The instructions file must be Markdown (.md). The JSON definition "
            "is configured with /exam-definition <path>."
        ),
        "preflight_instructions_missing": (
            "The exam instructions file was not found. Check the path set with "
            "/instructions <path>."
        ),
        "preflight_instructions_unreadable": (
            "The exam instructions file could not be read. Check its "
            "permissions and encoding."
        ),
        "preflight_instructions_empty": (
            "The exam instructions file is empty. Add a title and the "
            "functional requirements."
        ),
        "preflight_instructions_invalid": (
            "The exam instructions are not valid Markdown text."
        ),
        "preflight_instructions_wrong_resource": (
            "An exam definition JSON cannot be used as instructions. Configure "
            "it with /exam-definition <path>."
        ),
        "preflight_no_exam_definition": (
            "No exam definition JSON is configured. Set one with "
            "/exam-definition <path>."
        ),
        "preflight_exam_definition_missing": (
            "The exam definition JSON was not found. Check the path set with "
            "/exam-definition <path>."
        ),
        "preflight_exam_definition_unreadable": (
            "The exam definition JSON could not be read. Check its permissions "
            "and encoding."
        ),
        "preflight_exam_definition_invalid": (
            "The exam definition JSON does not satisfy the exam schema."
        ),
        "preflight_exam_definition_wrong_resource": (
            "The exam definition path points to a different resource type. "
            "Provide a validated JSON definition."
        ),
        "preflight_active_exam": (
            "An exam is already active. Finish it with /exam-finish before "
            "starting another."
        ),
        "preflight_toolchain_not_ready": (
            "The required static analysis toolchain is not ready: {detail}. No "
            "exam attempt or timer was created."
        ),
        "prereq_locale": "Enter a locale: es-CO or en-US.",
        "activation_hint": "Navigate with Up/Down and press Enter to run.",
        "lang_list_title": "Select language / Selecciona el idioma",
        "lang_list_hints": "Up/Down Move · Enter Select · Esc Cancel",
        "lang_cancelled": "Language change cancelled.",
        "lang_first_run_blocked": "Please choose a language to continue.",
        "lang_changed": (
            "Language changed to English. Learning progress is not affected."
        ),
        "next_step_prefix": "Suggested next step",
        "next_step_how": (
            "Select the action and press Enter to run it. Ignoring this does "
            "not affect your progress."
        ),
        "no_next_step": "Choose another action from the selector when you are ready.",
        "onboard_title": (
            "Learn to design, build, explain, test, and improve Android "
            "applications — not merely copy generated code."
        ),
        "onboard_stages": "Learning stages:",
        "onboard_choice": (
            "Reply with 'diagnose' for an initial diagnostic, a stage number "
            "or id to start there, or 'skip' to begin at the default stage."
        ),
        "onboard_unknown": (
            "Unknown stage choice. Please use a stage number or id from the list."
        ),
        "onboard_prereqs": (
            "Note: stage {stage} lists unmet prerequisites: {prereqs}. Skipped "
            "stages are NOT marked as mastered."
        ),
        "onboard_started": "Starting stage set to {number} — {title}.",
        "onboard_diagnostic": "Starting with an initial diagnostic at {title}.",
        "onboard_config_error": "Learning configuration error: {detail}",
        "plan_header": "Learning plan",
        "plan_current": "current",
        "plan_objective": "Objective:",
        "plan_outcomes": "Stage outcomes:",
        "plan_next": "Suggested next activities:",
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
        "busy_blocked": (
            "Ya hay una acción en curso. Espere o pulse Ctrl+C para cancelar."
        ),
        "prereq_project": (
            "Requiere un proyecto activo. Use /project <ruta> o --project <ruta>."
        ),
        "prereq_topic": "Ingrese un tema para continuar.",
        "prereq_question": "Ingrese una pregunta para continuar.",
        "prereq_statement": (
            "Ingrese la definición del examen: ruta .json validada o JSON "
            "en línea. Debe incluir título y requisitos funcionales. "
            "Ejemplo: /exam-init ~/exams/midterm.json"
        ),
        "exam_start_blocked": "El examen aún no puede comenzar:",
        "exam_start_no_student": (
            "El nombre del estudiante no está configurado. Usa /name seguido "
            "de tu nombre."
        ),
        "exam_statement_not_found": (
            "No se encontró la definición del examen: {detail}. Indica una ruta "
            ".json existente o pega una definición JSON válida."
        ),
        "exam_statement_invalid": (
            "Las instrucciones del examen no son válidas: {detail}"
        ),
        "exam_start_confirm": (
            "Iniciar examen — revisa antes de confirmar.\n\n"
            "Cómo configurar el examen:\n"
            "1. Crea un archivo de definición con extensión .json.\n"
            "2. Incluye Requisitos funcionales con IDs, pesos, procedencia y "
            "criterios de aceptación, además de schema_version, exam_id y título.\n"
            "3. Opcionalmente define allowed_duration_seconds y "
            "allowed_ask_count.\n"
            "4. El JSON se valida contra el esquema publicado antes de iniciar; "
            "los errores incluyen el JSON Pointer.\n\n"
            "Al iniciar se registran la duración y cada /ask, y se escribe "
            "docs/ada-sensei/ en el proyecto.\n\n"
            "Para confirmar, escribe yes (o y) y pulsa Enter. "
            "Para cancelar, escribe no."
        ),
        "exam_finish_confirm": (
            "Terminar examen — revisa antes de confirmar.\n\n"
            "Al terminar se detiene el temporizador, se califica el proyecto "
            "(build de Gradle, pruebas unitarias, Android Lint, Detekt) y se "
            "genera un informe PDF en docs/ada-sensei/exams/<exam>/report.pdf "
            "del proyecto.\n\n"
            "Para confirmar, escribe yes (o y) y pulsa Enter. "
            "Para cancelar, escribe no."
        ),
        "evaluate_confirm": (
            "La evaluación ejecuta build, pruebas, lint y detekt de Gradle.\n\n"
            "Para confirmar, escribe yes (o y) y pulsa Enter. "
            "Para cancelar, escribe no."
        ),
        "evaluate_aborted": (
            "Evaluación cancelada antes de ejecutar cualquier tarea de Gradle."
        ),
        "exam_start_aborted": (
            "Inicio del examen cancelado; no se creó ningún intento."
        ),
        "exam_finish_aborted": (
            "Finalización cancelada; el intento de examen sigue activo."
        ),
        "exam_preparing": "Preparando el examen. Puede tardar unos minutos…",
        "exam_start_progress_validating": "Validando requisitos del examen…",
        "exam_start_progress_toolchain": (
            "Preparando herramientas de análisis estático (Gradle, Android "
            "Lint, Detekt, KtLint)…"
        ),
        "exam_start_progress_ready": (
            "Herramientas listas. Creando el intento del examen…"
        ),
        "exam_progress_inspecting": "Inspeccionando el proyecto…",
        "exam_progress_build": "Ejecutando build de Gradle…",
        "exam_progress_unit_tests": "Ejecutando pruebas unitarias…",
        "exam_progress_lint": "Ejecutando Android Lint…",
        "exam_progress_detekt": "Ejecutando Detekt…",
        "exam_progress_interpreting": "Interpretando resultados con el modelo…",
        "exam_progress_report": "Generando el informe PDF…",
        "confirm_yes": "Confirmar",
        "confirm_no": "Cancelar",
        "preflight_failed": (
            "No se puede iniciar el examen: el proyecto actual no se puede "
            "evaluar."
        ),
        "preflight_no_project": (
            "No hay un proyecto activo configurado. Configúralo con "
            "/project <ruta> o en el archivo de configuración."
        ),
        "preflight_missing_path": "La ruta del proyecto no existe: {detail}",
        "preflight_not_directory": (
            "La ruta del proyecto no es un directorio: {detail}"
        ),
        "preflight_no_gradle": (
            "No se encontró el wrapper de Gradle (gradlew) ni Gradle global. "
            "{detail}"
        ),
        "preflight_no_android_manifest": (
            "No se encontró AndroidManifest.xml en el proyecto."
        ),
        "preflight_no_build_file": (
            "No se encontró build.gradle ni build.gradle.kts en el proyecto."
        ),
        "preflight_no_jdk": "No se encontró un JDK 17 o superior. {detail}",
        "preflight_no_android_sdk": (
            "No se encontró el Android SDK. Define ANDROID_HOME/"
            "ANDROID_SDK_ROOT o sdk.dir en local.properties."
        ),
        "preflight_no_instructions": (
            "No hay un archivo de instrucciones del examen configurado. "
            "Configúralo con /instructions <ruta>."
        ),
        "preflight_instructions_not_markdown": (
            "El archivo de instrucciones debe ser Markdown (.md). La definición "
            "JSON se configura con /exam-definition <ruta>."
        ),
        "preflight_instructions_missing": (
            "No se encontró el archivo de instrucciones del examen. Revisa la "
            "ruta configurada con /instructions <ruta>."
        ),
        "preflight_instructions_unreadable": (
            "No se pudo leer el archivo de instrucciones del examen. Revisa sus "
            "permisos y su codificación."
        ),
        "preflight_instructions_empty": (
            "El archivo de instrucciones del examen está vacío. Agrega un título "
            "y los requisitos funcionales."
        ),
        "preflight_instructions_invalid": (
            "Las instrucciones del examen no son texto Markdown válido."
        ),
        "preflight_instructions_wrong_resource": (
            "Un JSON de definición de examen no puede usarse como instrucciones. "
            "Configúralo con /exam-definition <ruta>."
        ),
        "preflight_no_exam_definition": (
            "No hay una definición JSON de examen configurada. Configúrala con "
            "/exam-definition <ruta>."
        ),
        "preflight_exam_definition_missing": (
            "No se encontró la definición JSON del examen. Revisa la ruta "
            "configurada con /exam-definition <ruta>."
        ),
        "preflight_exam_definition_unreadable": (
            "No se pudo leer la definición JSON del examen. Revisa sus permisos "
            "y su codificación."
        ),
        "preflight_exam_definition_invalid": (
            "La definición JSON del examen no cumple el esquema."
        ),
        "preflight_exam_definition_wrong_resource": (
            "La ruta de definición apunta a otro tipo de recurso. Proporciona "
            "una definición JSON válida."
        ),
        "preflight_active_exam": (
            "Ya hay un examen activo. Finalízalo con /exam-finish antes de "
            "iniciar otro."
        ),
        "preflight_toolchain_not_ready": (
            "El toolchain de análisis estático requerido no está listo: {detail}. "
            "No se creó ningún intento ni temporizador."
        ),
        "prereq_locale": "Ingrese un idioma: es-CO o en-US.",
        "activation_hint": "Navegue con Arriba/Abajo y pulse Enter para ejecutar.",
        "lang_list_title": "Select language / Selecciona el idioma",
        "lang_list_hints": "Arriba/Abajo Mover · Enter Elegir · Esc Cancelar",
        "lang_cancelled": "Cambio de idioma cancelado.",
        "lang_first_run_blocked": "Elija un idioma para continuar.",
        "lang_changed": (
            "Idioma cambiado a Español. Tu progreso no se vio afectado."
        ),
        "next_step_prefix": "Siguiente paso sugerido",
        "next_step_how": (
            "Seleccione la acción y pulse Enter para ejecutarla. Ignorar esto "
            "no afecta su progreso."
        ),
        "no_next_step": "Elija otra acción del selector cuando esté listo.",
        "onboard_title": (
            "Aprende a diseñar, construir, explicar, probar y mejorar "
            "aplicaciones Android, no solo a copiar código generado."
        ),
        "onboard_stages": "Etapas de aprendizaje:",
        "onboard_choice": (
            "Responda con 'diagnosticar' para un diagnóstico inicial, un número "
            "o id de etapa para empezar ahí, u 'omitir' para empezar en la etapa "
            "predeterminada."
        ),
        "onboard_unknown": (
            "Opción de etapa desconocida. Use un número o id de la lista."
        ),
        "onboard_prereqs": (
            "Nota: la etapa {stage} tiene prerrequisitos no cumplidos: {prereqs}. "
            "Las etapas omitidas NO se marcan como dominadas."
        ),
        "onboard_started": "Etapa inicial: {number} — {title}.",
        "onboard_diagnostic": "Comenzando con un diagnóstico inicial en {title}.",
        "onboard_config_error": "Error de configuración de aprendizaje: {detail}",
        "plan_header": "Plan de aprendizaje",
        "plan_current": "actual",
        "plan_objective": "Objetivo:",
        "plan_outcomes": "Resultados de la etapa:",
        "plan_next": "Próximas actividades sugeridas:",
    },
}


#: Stable blocker code -> localized UI string key. Codes come from
#: ``ProjectPreflight`` issues and ``ExamPreparationStatus.blockers``; keeping
#: the mapping here means the TUI never shows a raw machine identifier.
_BLOCKER_UI_KEYS: dict[str, str] = {
    "no_student": "exam_start_no_student",
    "no_project": "preflight_no_project",
    "missing_path": "preflight_missing_path",
    "not_directory": "preflight_not_directory",
    "no_gradle": "preflight_no_gradle",
    "no_android_manifest": "preflight_no_android_manifest",
    "no_build_file": "preflight_no_build_file",
    "no_jdk": "preflight_no_jdk",
    "no_android_sdk": "preflight_no_android_sdk",
    "no_instructions": "preflight_no_instructions",
    "instructions_not_markdown": "preflight_instructions_not_markdown",
    "instructions_missing": "preflight_instructions_missing",
    "instructions_unreadable": "preflight_instructions_unreadable",
    "instructions_empty": "preflight_instructions_empty",
    "instructions_invalid": "preflight_instructions_invalid",
    "instructions_wrong_resource": "preflight_instructions_wrong_resource",
    "no_exam_definition": "preflight_no_exam_definition",
    "exam_definition_missing": "preflight_exam_definition_missing",
    "exam_definition_unreadable": "preflight_exam_definition_unreadable",
    "exam_definition_invalid": "preflight_exam_definition_invalid",
    "exam_definition_wrong_resource": "preflight_exam_definition_wrong_resource",
    "active_exam": "preflight_active_exam",
    "toolchain_not_ready": "preflight_toolchain_not_ready",
}


def get_ui_string(key: str, locale: str | None) -> str:
    """Return the localized UI string for ``key`` with deterministic fallback."""
    requested = locale if locale in _UI_STRINGS else FALLBACK_LOCALE
    table = _UI_STRINGS.get(requested, _UI_STRINGS[FALLBACK_LOCALE])
    if key in table:
        return table[key]
    return _UI_STRINGS[FALLBACK_LOCALE].get(key, key)


def describe_blocker(code: str, locale: str | None, *, detail: str = "") -> str:
    """Return a localized, human-readable explanation for a blocker ``code``.

    Unknown codes fall back to the code itself so a new blocker never renders
    as an empty line. ``{detail}`` placeholders are filled when a detail is
    supplied and otherwise trimmed so the sentence stays readable.
    """
    key = _BLOCKER_UI_KEYS.get(code)
    if key is None:
        return code
    text = get_ui_string(key, locale)
    if "{detail}" not in text:
        return text
    if detail:
        return text.format(detail=detail)
    return text.replace(": {detail}", "").replace(" {detail}", "").strip()


def supported_ui_locales() -> tuple[str, ...]:
    return tuple(_UI_STRINGS.keys())


__all__ = ["describe_blocker", "get_ui_string", "supported_ui_locales"]
