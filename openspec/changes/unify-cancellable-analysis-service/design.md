# Design

## Context

See [proposal.md](proposal.md) for motivation and the [cancellable-engine-analysis spec](specs/cancellable-engine-analysis/spec.md) for the behavioral contract.

`EngineWrapper` already owns one Stockfish process on a worker thread, but its queue stores only boards and it publishes shared mutable `best_move`/`score` fields. Its bounded queue cannot invalidate an analysis already in progress. `main.py` currently assigns the selected difficulty's `time` to the wrapper's analysis time. `AnalysisScreen` bypasses the wrapper entirely: it starts a second `SimpleEngine` and calls `analyse` synchronously for every before/after position.

The desktop app uses a single pygame event loop and `python-chess` UCI engine. The mobile controller has a separate local engine and is outside this change.

## Goals / Non-Goals

**Goals:**

- Give all desktop consumers one lifecycle-managed, non-blocking analysis API with atomic, position-correlated results.
- Make logical cancellation and latest-request-wins behavior deterministic, including when an engine calculation has already begun.
- Separate analysis quality budgets from AI opponent skill and move-thinking time.
- Migrate live indicators, AI moves, in-game review sampling, training, and post-game review to validate request-scoped results.

**Non-Goals:**

- Change move-quality categories, thresholds, review prose, UI layout, or game rules.
- Guarantee interruption in the middle of an individual UCI calculation; cancellation must prevent delivery and the configured finite budget bounds any already-running calculation.
- Change the mobile engine, introduce cloud analysis, or add a new chess-engine dependency.

## Decisions

### Evolve the existing engine wrapper into the sole managed analysis service

`src/engine_wrapper.py` will own the only desktop Stockfish process and worker. It will expose immutable request and result values rather than having consumers infer freshness from shared latest-result fields. A request contains an opaque id, a copied position/FEN, consumer ownership, purpose, and the selected budget; a result atomically carries its request id, FEN, principal moves, and normalized score.

Callers submit work and poll or drain results on the pygame thread. They retain their current request id and FEN, accepting only an exact match. Compatibility accessors can remain temporarily only while every existing consumer is migrated; new app behavior must use the request-scoped result path.

Alternative considered: retain the current wrapper and add FEN checks at each caller. This leaves post-game analysis on a second engine and makes cancellation, error delivery, and future consumers inconsistent.

### Use generation-based invalidation with bounded engine work

Each owner/request group has a current generation. Submitting a replacement, clearing a group, cancelling a review, or stopping the service invalidates earlier generations and removes queued work where possible. The worker checks validity before starting and after `analyse` returns; it discards invalidated results instead of publishing them. Jobs use a finite configured time limit, so an in-flight UCI call can delay cancellation only by that known maximum.

The worker will report explicit unavailable/failed outcomes through the same result channel, preserving GUI responsiveness and avoiding exceptions across thread boundaries. Service shutdown invalidates all handles before joining and quitting the engine.

Alternative considered: kill and recreate Stockfish whenever cancellation occurs. That adds process churn and failure paths while not improving the observable guarantee that a cancelled result cannot be consumed.

### Model analysis and opponent move selection as distinct job purposes

The service serializes access to one engine but configures each job according to its purpose. Analysis jobs use the dedicated analysis budget and analysis-strength configuration; opponent-move jobs use the selected opponent skill and move-thinking budget. Before executing a job, the worker applies the appropriate engine options so a weak opponent does not make the analysis panel weak.

The board controller will only use an opponent-move result if its FEN is still current and its move is legal. Live evaluation, training, and in-game review will likewise retain and compare their active request identities rather than relying on timing or `is_analysing`.

Alternative considered: share a single mutable engine skill setting and time limit for all work. This is the present coupling and lets difficulty selection silently lower analysis quality.

### Schedule post-game review as cancellable asynchronous work

`AnalysisScreen` will receive the managed service from the app rather than an engine path. It will submit before- and after-move analysis requests, consume completed results during its normal event/render loop, and increment visible progress only for results belonging to its active review session. Exiting the screen cancels its session; it will not construct, directly call, or quit a second `SimpleEngine`.

Alternative considered: move the screen's existing synchronous loop to a new thread. That would still duplicate lifecycle, configuration, error handling, and result correlation.

### Make analysis budgets explicit configuration separate from difficulty profiles

`config.py` will define named live and review analysis budgets in one analysis configuration, with safe minimum validation in the service. Difficulty profiles will retain skill and be renamed or documented as opponent move-thinking values; they will no longer configure analysis time. Defaults preserve the application's current intended responsiveness (fast live analysis and a deeper review budget) while making both values visible and independently adjustable.

Alternative considered: one global analysis time. It is simpler but loses the existing responsiveness/depth distinction between continuous live feedback and post-game review.

## Risks / Trade-offs

- [A running UCI call cannot be forcibly stopped safely] → Use short, bounded budgets and invalidate its result before it can reach a consumer.
- [One engine serializes live and review requests] → Only one desktop surface normally owns active work; use owner cancellation and latest-request-wins semantics to prevent a departed surface from delaying current work.
- [Changing the wrapper may break training and GUI test doubles] → Define a minimal request/result protocol, retain adapters only during migration, and update focused fake-engine tests.
- [Engine options persist between jobs] → Apply the full purpose-specific configuration immediately before every job and test both job sequences.
- [Stockfish may be missing on user systems] → Keep existing availability messaging and deliver unavailable outcomes instead of blocking the UI.

## Migration Plan

1. Add deterministic unit tests around the new request/result contract using a controllable fake engine; establish the existing focused-test baseline first.
2. Implement the service and configuration split, then migrate live board, AI move, training, and in-game review consumers.
3. Replace direct post-game UCI calls with asynchronous service-driven review and cancellation on exit.
4. Run the focused and full pytest suites. If a regression requires rollback, restore the previous `EngineWrapper` implementation and `AnalysisScreen` constructor together; no persisted user data or migration is involved.

## Open Questions

- None. The default live and review budget values will preserve the current `.15s`, `.25s`/`.20s` intent while centralizing the exact configured values during implementation.
