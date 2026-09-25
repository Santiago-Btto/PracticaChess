# Spec Delta

## Purpose

Provide reliable, responsive Stockfish analysis that every desktop chess-analysis surface can request, cancel, and consume without sharing stale state.

## ADDED Requirements

### Requirement: Analysis results are request-scoped
The system SHALL associate every submitted analysis with an opaque request identifier and the exact FEN that was submitted. A completed result SHALL expose its identifier, FEN, best move, optional alternative move, and evaluation as one consistent result. A consumer SHALL use a result only when it matches the position and request that consumer still considers current.

#### Scenario: A completed result matches the current board
- **WHEN** analysis completes for the FEN currently requested by a live-board consumer
- **THEN** that consumer receives a result whose FEN and request identifier match its active request

#### Scenario: A stale result completes after the board changes
- **WHEN** the board changes after a request is submitted and the earlier request later completes
- **THEN** the live-board consumer SHALL not display, use for move selection, or use for move review the earlier result

### Requirement: Analysis requests can be superseded or cancelled
The system SHALL process analysis away from the graphical event loop. A consumer SHALL be able to cancel a request or supersede pending work with a newer request. Results for cancelled or superseded requests SHALL not be delivered as usable results, and stopping the service SHALL invalidate its outstanding requests and release the engine cleanly.

#### Scenario: A newer position supersedes pending work
- **WHEN** a consumer requests analysis for a newer position while an older request is pending or running
- **THEN** the consumer eventually receives analysis only for the newer active request and the older result is not usable

#### Scenario: A review is cancelled
- **WHEN** the user leaves a post-game review before all queued positions finish
- **THEN** the application remains responsive and no subsequent review result is applied to the closed review

#### Scenario: The engine is unavailable
- **WHEN** the engine process cannot be started or fails during analysis
- **THEN** the caller receives an unavailable or failed outcome without the graphical interface blocking or crashing

### Requirement: Live play and post-game review share the analysis facility
The desktop application SHALL obtain both live-board analysis and post-game move-review analysis through the same managed analysis facility. Post-game review SHALL not launch a separate direct engine-analysis workflow, and SHALL keep handling user events while its results are pending.

#### Scenario: A post-game review analyses a recorded move
- **WHEN** a user opens the post-game review for a completed game
- **THEN** the review requests the before- and after-move evaluations through the managed analysis facility and updates its progress without blocking event handling

#### Scenario: An AI move is ready for the current position
- **WHEN** an AI turn consumes an engine result
- **THEN** it SHALL only select a move from a result matching the current board and SHALL not apply a move that is illegal in that board

### Requirement: Analysis budget is independent of opponent difficulty
The system SHALL provide configurable analysis budgets for live and review analysis that are separate from the opponent difficulty configuration. Selecting or changing an opponent difficulty SHALL change only the opponent skill and move-thinking configuration, not either analysis budget.

#### Scenario: Difficulty changes during a new game setup
- **WHEN** the player selects a different opponent difficulty before starting a game
- **THEN** the configured live and review analysis budgets remain unchanged

#### Scenario: Analysis runs in either consumer
- **WHEN** either the live board or post-game review submits analysis
- **THEN** the managed facility applies that consumer's configured analysis budget rather than the opponent difficulty's move-thinking time
