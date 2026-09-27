# Spec Delta

## Purpose

Proporcionar análisis de ajedrez local más útil y fiable en la APK sin depender de red, motores externos ni resultados de posiciones que ya cambiaron.

## ADDED Requirements

### Requirement: Offline local analysis
La aplicación SHALL analizar posiciones exclusivamente con los recursos empaquetados en la APK y SHALL conservar compatibilidad con Android API 24+ sin requerir permiso de Internet, servicios remotos ni binarios de motor externos. Para una posición no terminal, el análisis SHALL devolver una jugada legal recomendada y una evaluación numérica consistente; para una posición terminal, SHALL informar que no existe jugada recomendada.

#### Scenario: Analyze a playable position offline
- **WHEN** the application requests analysis for a non-terminal legal position while the device has no network connectivity
- **THEN** it returns a legal recommended move and an evaluation without attempting a network request

#### Scenario: Analyze a terminal position
- **WHEN** the application requests analysis for a checkmate, stalemate, or claimed-draw position
- **THEN** it reports that no recommended move is available and does not attempt to select an illegal move

### Requirement: Budgeted stronger analysis
La aplicación SHALL mejorar el análisis local más allá de una evaluación de profundidad única fija, buscando progresivamente variaciones más profundas hasta que expire el presupuesto móvil aplicable o se encuentre un resultado terminal. El presupuesto usado para una sugerencia interactiva SHALL configurarse independientemente del presupuesto de revisión post-partida, para que una revisión más fuerte no haga esperar las interacciones normales de juego.

#### Scenario: Interactive hint uses its own budget
- **WHEN** a player requests or triggers an analysis hint during a game
- **THEN** the application completes that analysis using the interactive budget and exposes its best completed result

#### Scenario: Post-game analysis uses a separate budget
- **WHEN** the application analyzes a move during post-game review
- **THEN** it may use the review budget without changing the configured budget for interactive hints

### Requirement: User-controlled live best-move analysis
La aplicación SHALL proporcionar una preferencia de sesión, activada por defecto, para activar o desactivar el análisis automático en vivo de mejores jugadas. Cuando esté desactivada, SHALL cancelar o invalidar la solicitud interactiva pendiente, no SHALL iniciar nuevas solicitudes interactivas después de cambios de tablero y no SHALL mostrar una sugerencia o indicador procedente de análisis en vivo. Cuando se reactive, SHALL solicitar análisis únicamente para la posición vigente. Esta preferencia SHALL NOT impedir una revisión post-partida que el usuario inicie explícitamente.

#### Scenario: Disable live analysis while a hint is pending
- **WHEN** the user disables live analysis while a hint request is still running
- **THEN** the pending hint cannot update the recommended move or visible live-analysis indicators and later board changes do not schedule a new interactive hint

#### Scenario: Re-enable live analysis for the current position
- **WHEN** the user enables live analysis after making one or more moves while it was disabled
- **THEN** the application requests a new interactive analysis for the current position and can display only that matching result

#### Scenario: Start an explicit review while live analysis is disabled
- **WHEN** the user starts post-game review with live analysis disabled
- **THEN** the review remains available and uses its separate local review analysis budget

### Requirement: Position-bound, interruptible results
La aplicación SHALL associate each asynchronous analysis request with the requested position and a monotonically newer request identity. It SHALL apply a completed result only when both still match the active request; it SHALL invalidate or cancel outstanding work after a move, undo, restart, board replacement, review exit, or disabling live analysis. A superseded result SHALL not alter the hint, evaluation history, review data, or visible board state.

#### Scenario: Board changes during analysis
- **WHEN** the user makes a legal move while analysis for the prior position is still running
- **THEN** the prior result is discarded and only a result for the current position can update the visible analysis

#### Scenario: Restart invalidates pending work
- **WHEN** the user restarts or undoes a game while an analysis or review job is running
- **THEN** the job is cancelled or invalidated and it cannot repopulate data for the replaced game

#### Scenario: Preference change invalidates a live result
- **WHEN** the user disables live analysis after its result was requested but before it is delivered
- **THEN** that result is discarded and cannot restore a live suggestion while the preference remains disabled

### Requirement: Analysis history reflects engine evaluation
La aplicación SHALL retain analysis data for the initial position and each played position using the engine's evaluation rather than a separate material-only proxy. The retained data SHALL identify the analyzed position and any available recommended continuation so post-game review can explain the actual game without re-analyzing an unrelated board.

#### Scenario: Record a completed played position
- **WHEN** analysis completes for a position in the current game
- **THEN** the application stores the position identity, engine evaluation, and available recommended continuation with that game position

#### Scenario: Do not replace history with stale data
- **WHEN** a result arrives for a position that is no longer part of the active game history
- **THEN** the application leaves the current game's recorded analysis history unchanged
