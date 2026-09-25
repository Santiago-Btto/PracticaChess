# Proposal

## Why

The application currently uses an asynchronous `EngineWrapper` for live play but starts a separate, synchronous Stockfish process for the post-game screen.  This duplicates engine behavior, can freeze the interface during review, and conflates the live-analysis budget with opponent difficulty.  A single cancellable background service will make analysis responsive and ensure both surfaces use the same engine contract.

## What Changes

- Introduce one background engine-analysis service that owns Stockfish lifecycle and accepts identified analysis requests.
- Make live-board analysis and post-game move review consume results from that service instead of creating independent engine workflows.
- Supersede pending work and prevent cancelled or stale results from being delivered to callers.
- Add a configurable analysis budget that is distinct from the opponent's skill level and move-thinking time.
- Preserve graceful operation when Stockfish is unavailable and orderly cleanup when analysis is stopped or the application exits.
- Add deterministic tests for request supersession, cancellation, result routing, budgeting, and both consuming flows.

## Capabilities

### New Capabilities

- `cancellable-engine-analysis`: Background, cancellable chess-engine analysis with request-scoped results and an independent analysis budget for live and post-game consumers.

### Modified Capabilities

- None.

## Impact

- Affected code: `src/engine_wrapper.py`, `src/board_gui.py`, `src/analysis_screen.py`, `config.py`, and focused tests under `tests/`.
- The existing `EngineWrapper` public behavior will be migrated or adapted to the unified service so GUI callers no longer depend on shared mutable “latest result” fields alone.
- Uses the existing `python-chess` UCI/Stockfish dependency; no new external engine dependency is planned.
