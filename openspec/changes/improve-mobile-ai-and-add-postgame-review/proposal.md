# Proposal

## Why

La APK ofrece una partida local funcional, pero su IA usa una búsqueda fija y el análisis se ejecuta de forma síncrona, por lo que aumentar su fuerza puede degradar la respuesta de la interfaz. Además, quien no quiere ver sugerencias no puede desactivar el análisis en vivo, y al finalizar una partida no recibe una lectura general que resuma sus mejores decisiones y errores.

## What Changes

- Mejorar el motor heurístico local de la APK con búsqueda iterativa dentro de un presupuesto apropiado para Android, manteniendo su ejecución sin red ni motor nativo externo.
- Hacer cancelables los análisis y vincular sus resultados a una posición y solicitud concretas, para que cambios de tablero, reinicios y deshacer no apliquen resultados obsoletos ni bloqueen Kivy.
- Conservar evaluaciones del motor para las posiciones de la partida y usarlas para identificar la alternativa recomendada y el cambio de evaluación por jugada.
- Añadir una revisión post-partida desde la aplicación móvil: progreso no bloqueante, navegación por jugadas, tablero de la posición revisada, jugada realizada, mejor alternativa y clasificación comprensible de la calidad de cada jugada.
- Permitir activar o desactivar, durante la sesión, el análisis en vivo de mejores jugadas; al desactivarlo no se calcularán ni mostrarán sugerencias automáticas.
- Presentar, al completar la revisión post-partida, un resumen general local con conteos por categoría, mejores jugadas y momentos críticos, además del detalle navegable por jugada.
- Cancelar o invalidar una revisión en curso al reiniciar, deshacer o salir de ella; mantener la partida y los controles utilizables.

## Capabilities

### New Capabilities

- `mobile-local-analysis`: Análisis de posiciones y sugerencias de la APK mediante una IA local más fuerte, presupuestada y segura frente a resultados obsoletos.
- `mobile-postgame-review`: Revisión post-partida offline y navegable que explica la calidad de las jugadas y sus alternativas.

### Modified Capabilities

- None.

## Impact

- Afecta `mobile/controller.py` para el motor, la preferencia de análisis en vivo, el historial y resumen de análisis, y la coordinación cancelable de trabajos.
- Afecta `mobile/app.py` y recursos de UI para mostrar el estado de la preferencia, la revisión y el resumen post-partida sin bloquear la pantalla Kivy.
- Afecta las pruebas de controlador, layout y empaquetado móvil; se añadirán pruebas deterministas de IA, cancelación y revisión.
- Mantiene `mobile/buildozer.spec`, dependencias y permisos compatibles con Android API 24+, sin `INTERNET`, servicios remotos ni motores binarios.
