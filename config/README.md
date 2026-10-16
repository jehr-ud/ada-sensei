# ADA Sensei — configuración bilingüe / Bilingual configuration

## Español

Este paquete contiene las configuraciones de aprendizaje de ADA Sensei en español (`es-CO`) e inglés (`en-US`):

- `stages.es.json` y `stages.en.json`: catálogo de etapas y orden de progresión.
- `stage-rubrics.es.json` y `stage-rubrics.en.json`: rúbricas de salida por etapa.
- `progression-policy.es.json` y `progression-policy.en.json`: política común de dominio y progresión.
- `0010-language-selection/`: especificación para elegir, guardar y aplicar el idioma preferido.

### Nueva etapa 6: Aplicación Android básica

La etapa `android-basic-application` se ubica después de `state-basic-architecture` y antes de `web-services-api-integration`. Las etapas posteriores se renumeran, pero los identificadores estables se conservan.

La aplicación **no está predeterminada**. El subagente `Trainer` propone dinámicamente una aplicación pequeña según los intereses disponibles del estudiante, sus etapas dominadas y la evidencia previa. El estudiante puede aceptar la propuesta o pedir un ajuste. Si no hay información personalizada disponible, Trainer propone una aplicación sencilla por defecto.

Trainer debe entregar: título, problema, usuario objetivo, alcance, requisitos funcionales, criterios de aceptación, flujo de pantallas sugerido, modelo de datos, escenarios de prueba, elementos fuera de alcance y mapeo de requisitos a objetivos de aprendizaje.

La temática es variable, pero los objetivos evaluados permanecen estables: Kotlin, estructura y ciclo de vida Android, Compose, estado, arquitectura básica, validación, pruebas y explicación del estudiante. No se deben exigir servicios web, API remotas, autenticación, bases de datos ni persistencia externa en esta etapa.

La rúbrica `stage-android-basic-application-v1` es independiente de la temática. Trainer genera la propuesta; no decide si el estudiante domina la etapa. La decisión de progresión continúa basada en evidencias y en `progression-policy`.

## English

This package contains ADA Sensei learning configuration in Spanish (`es-CO`) and English (`en-US`):

- `stages.es.json` and `stages.en.json`: learning-stage catalog and progression order.
- `stage-rubrics.es.json` and `stage-rubrics.en.json`: stage exit rubrics.
- `progression-policy.es.json` and `progression-policy.en.json`: mastery and progression policy.
- `0010-language-selection/`: specification for selecting, persisting, and applying the preferred language.

### New stage 6: Basic Android application

The `android-basic-application` stage follows `state-basic-architecture` and precedes `web-services-api-integration`. Later stages are renumbered, while stable identifiers are preserved.

The application is **not hard-coded**. The `Trainer` subagent dynamically proposes a small application based on the learner’s available interests, mastered stages, and prior evidence. The learner can accept the proposal or request an adjustment. If no personalization data is available, Trainer proposes a simple default application.

Trainer must provide: title, problem statement, target user, scope, functional requirements, acceptance criteria, suggested screen flow, data model, test scenarios, out-of-scope items, and a mapping from requirements to learning targets.

The theme can vary, but assessed learning targets remain stable: Kotlin, Android structure and lifecycle, Compose, state, basic architecture, validation, testing, and learner explanation. Do not require web services, remote APIs, authentication, databases, or external persistence at this stage.

The `stage-android-basic-application-v1` rubric is independent of the app theme. Trainer generates the proposal; it does not decide whether the learner has mastered the stage. Progression remains evidence-driven and governed by `progression-policy`.

## Consistency and implementation notes

- Keep IDs, enum values, weights, rubric criteria, and progression thresholds equivalent across locales. Translate student-facing text only.
- The language-selection spec supports `es-CO` and `en-US`.
- Pass the selected locale to Trainer and other learner-facing agents.
- Do not ask the LLM to determine mastery directly. Evaluation and progression must use the evidence pipeline and deterministic policy.
- Validate JSON syntax and check that every stage references an existing rubric and exit challenge.
- English strings in older rubric entries may require editorial review before production use.
