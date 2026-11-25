# ADR-032 — `local.properties` como autoridad del Android SDK

## Estado
Aceptado (2026-11-25). Modifica la detección descrita en
`specs/001-foundation/design.md` y complementa RQ-FND-019.

## Contexto
`ToolDiscovery.find_sdk()` eliminaba todas las barras invertidas del valor de
`sdk.dir` y validaba el resultado con `Path(...).is_dir()`. Ese tratamiento
convertía `C\:\\Users\\...\\Sdk` en `C:Users...Sdk`, una ruta que no existe.
Además, las variables de entorno tenían prioridad sobre `local.properties`,
aunque Gradle use ese archivo para ejecutar el proyecto.

## Decisión
1. Si el proyecto contiene `local.properties` con `sdk.dir`, ese valor es la
   fuente autoritativa del Android SDK.
2. El valor se usa literalmente: no se eliminan barras invertidas, no se
   convierten unidades de Windows a `/mnt/<letra>` y no se reescribe con
   `expanduser()`, `resolve()` ni otra normalización.
3. `ANDROID_HOME` y `ANDROID_SDK_ROOT` solo se usan cuando no hay `sdk.dir`
   utilizable en `local.properties`.
4. La detección no valida subdirectorios del SDK. Si el valor literal no es
   ejecutable, Gradle lo reporta durante la ejecución real.

## Consecuencias
- ADA Sensei usa exactamente la misma configuración que usa Gradle para correr
  la aplicación.
- No se descarta una ruta válida de Windows o WSL por diferencias de formato.
- Una ruta inválida en `local.properties` puede pasar el preflight y fallar
  después; ese riesgo se acepta para no reinterpretar la configuración de Android.
