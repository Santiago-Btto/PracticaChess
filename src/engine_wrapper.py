"""Servicio único, no bloqueante y cancelable para análisis con Stockfish."""
import logging
import queue
import threading
import uuid
from dataclasses import dataclass
from typing import Callable, Literal

import chess
import chess.engine

from src.platform_utils import IS_WINDOWS

log = logging.getLogger(__name__)
AnalysisPurpose = Literal["live", "review", "opponent"]


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Identidad inmutable de un trabajo de análisis enviado al servicio."""

    request_id: str
    fen: str
    owner: str
    purpose: AnalysisPurpose


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Resultado inmutable de un análisis asociado a una solicitud concreta."""

    request_id: str
    fen: str
    best_move: chess.Move | None
    alternative_move: chess.Move | None
    score: chess.engine.Score | int | None
    outcome: str = "success"
    error: str | None = None


@dataclass(frozen=True, slots=True)
class _Job:
    request: AnalysisRequest
    board: chess.Board
    generation: int
    time_limit: float
    skill_level: int | None


def ranked_moves(infos: list[dict]) -> tuple[chess.Move | None, chess.Move | None]:
    """Devuelve la mejor jugada UCI y una variante distinta de menor prioridad."""
    best_move: chess.Move | None = None
    alternative_move: chess.Move | None = None
    for info in infos:
        pv = info.get("pv", [])
        move = pv[0] if pv else None
        if move is None:
            continue
        if best_move is None:
            best_move = move
        elif move != best_move:
            alternative_move = move
            break
    return best_move, alternative_move


def result_matches(
    result: AnalysisResult | None, request_id: str | None, fen: str | None
) -> bool:
    """Indica si un resultado terminado sigue correspondiendo al consumidor."""
    return bool(result and result.outcome == "success" and result.request_id == request_id and result.fen == fen)


class EngineWrapper:
    """Worker único con resultados correlacionados y cancelación por owner."""

    _MIN_BUDGET = 0.05

    def __init__(
        self,
        stockfish_path: str,
        *,
        engine_factory: Callable[[str], chess.engine.SimpleEngine] | None = None,
        live_analysis_time: float = 0.15,
        review_analysis_time: float = 0.25,
        analysis_skill_level: int = 20,
    ):
        self._path = stockfish_path
        self._engine_factory = engine_factory or chess.engine.SimpleEngine.popen_uci
        self._engine: chess.engine.SimpleEngine | None = None
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue[_Job | None] = queue.Queue(maxsize=1)
        self._lock = threading.RLock()
        self._result_ready = threading.Condition(self._lock)
        self._running = False
        self._available = False
        self._generations: dict[str, int] = {}
        self._results: dict[str, AnalysisResult] = {}
        self._request_owners: dict[str, str] = {}
        self._live_analysis_time = self._safe_budget(live_analysis_time)
        self._review_analysis_time = self._safe_budget(review_analysis_time)
        self._analysis_skill = max(0, min(20, int(analysis_skill_level)))
        self._opponent_time = self._MIN_BUDGET
        self._opponent_skill = 10

        # Adaptadores de compatibilidad mientras se migran consumidores.
        self._best_move: chess.Move | None = None
        self._alternative_move: chess.Move | None = None
        self._score: chess.engine.Score | int | None = None
        self._analysis_fen: str | None = None
        self._is_analysing = False

    @classmethod
    def _safe_budget(cls, seconds: float) -> float:
        return max(cls._MIN_BUDGET, float(seconds))

    def start(self) -> bool:
        try:
            self._engine = self._engine_factory(self._path)
        except FileNotFoundError:
            hint = "Coloca stockfish.exe en bin o añádelo al PATH." if IS_WINDOWS else "Instálalo con: sudo apt install stockfish"
            log.error("Stockfish no encontrado en '%s'. %s", self._path, hint)
            return False
        except Exception as exc:
            log.error("Error al iniciar Stockfish: %s", exc)
            return False
        with self._lock:
            self._available = True
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True, name="StockfishWorker")
            self._thread.start()
        return True

    def shutdown(self):
        """Invalida solicitudes, detiene el worker y libera el único motor."""
        with self._lock:
            self._running = False
            self._available = False
            self._generations = {owner: generation + 1 for owner, generation in self._generations.items()}
            self._results.clear()
            self._result_ready.notify_all()
        self._discard_queued_jobs()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
        if self._engine:
            try:
                self._engine.quit()
            except Exception:
                pass

    def _discard_queued_jobs(self):
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def is_available(self) -> bool:
        return self._available

    def set_skill_level(self, level: int):
        """Perfil del rival: no cambia los presupuestos de análisis."""
        self._opponent_skill = max(0, min(20, int(level)))

    def set_analysis_time(self, seconds: float):
        """Adaptador antiguo; configura sólo el análisis de tablero en vivo."""
        self._live_analysis_time = self._safe_budget(seconds)

    def set_analysis_budgets(self, *, live: float, review: float):
        self._live_analysis_time = self._safe_budget(live)
        self._review_analysis_time = self._safe_budget(review)

    def set_opponent_profile(self, *, skill: int, time: float):
        self._opponent_skill = max(0, min(20, int(skill)))
        self._opponent_time = self._safe_budget(time)

    def submit_analysis(self, board: chess.Board, *, owner: str, purpose: AnalysisPurpose = "live", replace: bool = True) -> AnalysisRequest:
        request = AnalysisRequest(uuid.uuid4().hex, board.fen(), owner, purpose)
        with self._lock:
            generation = self._generations.get(owner, 0)
            if replace:
                generation += 1
                self._generations[owner] = generation
            elif owner not in self._generations:
                self._generations[owner] = generation
            self._request_owners[request.request_id] = owner
            if not self._available or not self._running:
                self._store_result_locked(AnalysisResult(request.request_id, request.fen, None, None, None, "unavailable", "Stockfish no está disponible"))
                return request
            limit, skill = self._profile_for(purpose)
            job = _Job(request, board.copy(), generation, limit, skill)
        if replace:
            self._discard_queued_jobs()
        self._enqueue_job(job)
        return request

    def request_analysis(self, board: chess.Board):
        return self.submit_analysis(board, owner="legacy", purpose="live")

    def cancel_owner(self, owner: str):
        with self._lock:
            self._generations[owner] = self._generations.get(owner, 0) + 1
            for request_id in tuple(self._results):
                if self._request_owners.get(request_id) == owner:
                    self._results.pop(request_id)
            self._result_ready.notify_all()
        self._discard_invalid_queued_jobs()

    def clear(self):
        self.cancel_owner("legacy")
        with self._lock:
            self._best_move = self._alternative_move = self._score = self._analysis_fen = None

    def _store_result(self, result: AnalysisResult):
        with self._lock:
            self._store_result_locked(result)

    def _store_result_locked(self, result: AnalysisResult):
        self._results[result.request_id] = result
        self._result_ready.notify_all()

    def get_result(self, request_id: str | None) -> AnalysisResult | None:
        with self._lock:
            return self._results.get(request_id) if request_id else None

    def wait_for_result(self, request_id: str, timeout: float | None = None) -> AnalysisResult | None:
        with self._result_ready:
            if request_id not in self._results:
                self._result_ready.wait_for(lambda: request_id in self._results, timeout)
            return self._results.get(request_id)

    @property
    def best_move(self):
        with self._lock:
            return self._best_move

    @property
    def alternative_move(self):
        with self._lock:
            return self._alternative_move

    @property
    def score(self):
        with self._lock:
            return self._score

    @property
    def analysis_fen(self):
        with self._lock:
            return self._analysis_fen

    @property
    def is_analysing(self):
        with self._lock:
            return self._is_analysing

    def _profile_for(self, purpose: AnalysisPurpose) -> tuple[float, int | None]:
        if purpose == "review":
            return self._review_analysis_time, self._analysis_skill
        if purpose == "opponent":
            return self._opponent_time, self._opponent_skill
        return self._live_analysis_time, self._analysis_skill

    def _enqueue_job(self, job: _Job):
        try:
            self._queue.put_nowait(job)
        except queue.Full:
            self._discard_queued_jobs()
            self._queue.put_nowait(job)

    def _discard_invalid_queued_jobs(self):
        retained: list[_Job] = []
        while True:
            try:
                job = self._queue.get_nowait()
            except queue.Empty:
                break
            if job is not None and self._job_is_current(job):
                retained.append(job)
        for job in retained:
            self._enqueue_job(job)

    def _job_is_current(self, job: _Job) -> bool:
        with self._lock:
            return self._running and self._generations.get(job.request.owner, 0) == job.generation

    def _worker(self):
        while True:
            try:
                job = self._queue.get(timeout=0.3)
            except queue.Empty:
                with self._lock:
                    if not self._running:
                        return
                continue
            if job is None:
                return
            if not self._job_is_current(job):
                continue
            with self._lock:
                self._is_analysing = True
            try:
                self._engine.configure({"Skill Level": job.skill_level})
                analysed = self._engine.analyse(job.board, chess.engine.Limit(time=job.time_limit), multipv=2)
                infos = analysed if isinstance(analysed, list) else [analysed]
                score = infos[0].get("score") if infos else None
                if hasattr(score, "white"):
                    score = score.white()
                best, alternative = ranked_moves(infos)
                result = AnalysisResult(job.request.request_id, job.request.fen, best, alternative, score)
            except Exception as exc:
                log.debug("Error en análisis UCI: %s", exc)
                result = AnalysisResult(job.request.request_id, job.request.fen, None, None, None, "failed", str(exc))
            finally:
                with self._lock:
                    self._is_analysing = False
            if self._job_is_current(job):
                with self._lock:
                    if self._job_is_current(job):
                        self._store_result_locked(result)
                        self._best_move, self._alternative_move = result.best_move, result.alternative_move
                        self._score, self._analysis_fen = result.score, result.fen
