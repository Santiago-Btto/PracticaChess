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

### Requirement: Position-bound, interruptible results
La aplicación SHALL associate each asynchronous analysis request with the requested position and a monotonically newer request identity. It SHALL apply a completed result only when both still match the active request; it SHALL invalidate or cancel outstanding work after a move, undo, restart, board replacement, or review exit. A superseded result SHALL not alter the hint, evaluation history, review data, or visible board state.

#### Scenario: Board changes during analysis
- **WHEN** the user makes a legal move while analysis for the prior position is still running
- **THEN** the prior result is discarded and only a result for the current position can update the visible analysis

#### Scenario: Restart invalidates pending work
- **WHEN** the user restarts or undoes a game while an analysis or review job is running
- **THEN** the job is cancelled or invalidated and it cannot repopulate data for the replaced game

### Requirement: Analysis history reflects engine evaluation
La aplicación SHALL retain analysis data for the initial position and each played position using the engine's evaluation rather than a separate material-only proxy. The retained data SHALL identify the analyzed position and any available recommended continuation so post-game review can explain the actual game without re-analyzing an unrelated board.

#### Scenario: Record a completed played position
- **WHEN** analysis completes for a position in the current game
- **THEN** the application stores the position identity, engine evaluation, and available recommended continuation with that game position

#### Scenario: Do not replace history with stale data
- **WHEN** a result arrives for a position that is no longer part of the active game history
- **THEN** the application leaves the current game's recorded analysis history unchanged
