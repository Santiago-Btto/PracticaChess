# Tasks

## 1. Request-scoped engine service

- [x] 1.1 Run the focused existing engine, game-analysis, training-screen, and local-suggestions tests before modifying their code; record the passing baseline and stop to report any pre-existing failure.
- [x] 1.2 Write failing deterministic unit tests for immutable request-scoped results (request id, FEN, best/alternative moves, score) and exact result acceptance; verify the tests fail before service production code is changed.
- [x] 1.3 Implement the minimal request/result contract and thread-safe result retrieval in `src/engine_wrapper.py`; run the new tests to GREEN, then add at least a second FEN/request case and refactor only with the suite remaining green.
- [x] 1.4 Write failing fake-engine tests for replacement of queued and already-running requests, owner/session cancellation, shutdown invalidation, and unavailable/failed engine outcomes; verify RED without timing-dependent sleeps.
- [x] 1.5 Implement generation-based invalidation, bounded worker scheduling, failure delivery, and clean shutdown in the managed service; triangulate each behavior with the fake engine and verify the focused service suite passes.

## 2. Independent analysis and opponent profiles

- [x] 2.1 Write failing configuration and fake-engine tests proving live/review analysis budgets remain unchanged when opponent difficulty changes, and that analysis and opponent-move jobs apply their separate time/skill profiles; verify RED.
- [x] 2.2 Add explicit live and review analysis budgets to `config.py`, separate opponent move-thinking time from `DIFFICULTY_LEVELS`, and implement purpose-specific engine configuration; run the new tests to GREEN and add boundary tests for safe minimum budgets and sequential mixed-purpose jobs.
- [x] 2.3 Refactor shared profile/request construction for clarity without changing behavior; verify the focused configuration and service tests remain green after each refactor.

## 3. Migrate live desktop consumers safely

- [x] 3.1 Write failing controller-level tests for a board change while analysis is in flight, ensuring stale indicators and in-game review data are ignored and an AI never applies an old or illegal move; verify RED with a deterministic service fake.
- [x] 3.2 Migrate `main.py` live evaluation, AI-turn, and in-game review paths to retain active request ids/FENs and consume only matching service results; run the controller tests to GREEN, then triangulate with both white and black turns plus an invalid returned move.
- [x] 3.3 Write failing and then passing `TrainingScreen` tests that use the request-scoped result API, including cancellation or replacement of its active puzzle request; refactor test doubles and production adaptation while preserving current challenge behavior.
- [x] 3.4 Run the relevant UI/controller test files after migration and verify legacy shared-result access is not used by newly migrated desktop flows.

## 4. Make post-game review asynchronous and cancellable

- [x] 4.1 Write failing `AnalysisScreen` tests with a controllable service fake for non-blocking before/after requests, progress only from the active review session, and cancellation on exit; verify RED without opening Stockfish.
- [x] 4.2 Change `AnalysisScreen` to receive the managed service, submit and poll review work through it during the event/render loop, and remove direct `SimpleEngine` ownership; run the new tests to GREEN and add a multi-move plus early-exit triangulation case.
- [x] 4.3 Wire the application to pass its existing service into post-game review and cancel review ownership before returning to play/menu; verify the focused integration tests show only one managed desktop engine lifecycle.

## 5. Regression verification

- [ ] 5.1 Run `python -m pytest -q` and verify all tests pass; manually start a short desktop game and a post-game review when Stockfish is available to confirm responsive live feedback, a responsive cancellable review, and analysis strength unchanged across difficulty selections.
