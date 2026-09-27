# Spec Delta

## Purpose

Permitir que una partida terminada en la APK se revise localmente, jugada por jugada, para que el usuario vea alternativas y comprenda la calidad de sus decisiones.

## ADDED Requirements

### Requirement: Start an offline post-game review
La aplicación SHALL offer a post-game review action only after a game has ended. Starting it SHALL preserve the completed game's move history and result, analyze that immutable game snapshot locally, and present visible progress while analysis remains incomplete. The review SHALL not require network access.

#### Scenario: Finished game offers review
- **WHEN** a game reaches a terminal result
- **THEN** the application displays a post-game review action alongside the final result

#### Scenario: Review runs locally with progress
- **WHEN** the user starts review for a finished game
- **THEN** the application keeps the completed game available, shows review progress, and does not make a network request

### Requirement: Explain every reviewed move
La aplicación SHALL produce a review entry for each legal move in the completed game's main line. Each entry SHALL identify the played move, evaluation before and after the move from the moving side's perspective, the best local alternative when one exists, and one user-visible classification selected from best move, good move, inaccuracy, mistake, or blunder. Terminal moves with no alternative SHALL be represented without inventing a best move.

#### Scenario: Classify a non-terminal move
- **WHEN** review analysis completes for a non-terminal played move
- **THEN** its entry shows the played move, its classification, and the best alternative and evaluation change

#### Scenario: Represent a terminal move honestly
- **WHEN** a reviewed move ends the game and no legal continuation exists
- **THEN** its entry identifies the played move and terminal outcome without showing a fabricated alternative move

### Requirement: Present a completed general game analysis
After the review entries for one immutable completed game have all been produced, the application SHALL present a general local analysis of that game. The summary SHALL include counts for best moves, good moves, inaccuracies, mistakes, and blunders; a deterministic selection of best moves and critical moments; and an explanation derived from those local review results. The application SHALL identify the summary as local AI analysis and SHALL NOT present it as external-engine or network analysis. It SHALL not present a completed summary while the review is incomplete.

#### Scenario: Show a complete summary after review finishes
- **WHEN** every move in a completed game has an accepted review entry
- **THEN** the application displays the category counts, highlighted best moves and critical moments, and a general local-analysis explanation for that same game

#### Scenario: Keep the summary incomplete while review progresses
- **WHEN** post-game review still has one or more moves pending
- **THEN** the application shows review progress and does not display a final general summary

### Requirement: Navigate reviewed positions
La aplicación SHALL let the user navigate backward and forward through the reviewed game, including the initial position and final position. For the selected ply, it SHALL display the corresponding board position and review entry without mutating the completed game, its result, or its move history.

#### Scenario: Move to an earlier reviewed position
- **WHEN** the user selects a prior move in a completed review
- **THEN** the board and annotations show the position and entry for that ply while the completed game's stored final state remains unchanged

#### Scenario: Move to the final reviewed position
- **WHEN** the user advances to the last review entry
- **THEN** the board shows the finished position and the application retains the original game result

### Requirement: Safely leave or replace a review
La aplicación SHALL allow the user to leave a review or begin a replacement game while review analysis is pending or complete. It SHALL cancel or invalidate unfinished review work, clear review-specific presentation state including any general summary, and prevent its late results from changing the replacement game.

#### Scenario: Leave a review in progress
- **WHEN** the user exits review before all moves have been analyzed
- **THEN** the application stops accepting unfinished review results and returns to a usable non-review state

#### Scenario: Start a new game from review
- **WHEN** the user restarts while viewing or generating review data
- **THEN** the application begins the new game with no review data from the prior game applied to it

#### Scenario: Cancelled review cannot publish a summary
- **WHEN** the user leaves or replaces a game before its review is complete
- **THEN** no late review entry or final summary from that game is displayed in the resulting state
