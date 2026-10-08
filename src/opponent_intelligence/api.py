"""Optional, read-only HTTP reports from one operator-configured local snapshot."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .api_models import ErrorResponse, ReportQuery, ReportResponse
from .ingestion import load_snapshot
from .report import build_report


MAX_QUERY_BYTES = 2048
MAX_SNAPSHOT_ROWS = 100000
MAX_SNAPSHOT_GAMES = 300


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, fields=()):
        self.status, self.code, self.message, self.fields = status, code, message, list(fields)


def _error(status: int, code: str, message: str, fields=(), headers=None) -> JSONResponse:
    return JSONResponse(status_code=status, headers=headers, content={
        "error": {"code": code, "message": message, "fields": list(fields)},
    })


def create_app(*, snapshot: Path, source_label: str) -> FastAPI:
    """Load and verify once per lifespan; never select files from HTTP input.

    Configuration errors abort startup. Changing the cache after startup cannot
    replace the in-memory dataset; choosing new bytes requires a new lifespan.
    """
    snapshot = Path(snapshot)
    if not snapshot.is_absolute():
        raise ValueError("API snapshot configuration must be an absolute directory")
    if not isinstance(source_label, str) or not source_label.strip() or len(source_label) > 300:
        raise ValueError("API source label must be nonempty and at most 300 characters")
    dataset = None
    active_report = Lock()

    @asynccontextmanager
    async def lifespan(app):
        nonlocal dataset
        loaded = load_snapshot(snapshot)
        if (loaded.input_rows > MAX_SNAPSHOT_ROWS
                or len({play.game_id for play in loaded.plays}) > MAX_SNAPSHOT_GAMES):
            raise ValueError("snapshot exceeds this single-season API's row/game limits")
        dataset = loaded
        try:
            yield
        finally:
            dataset = None

    app = FastAPI(
        title="NFL Opponent Intelligence", version="1.0.0", lifespan=lifespan,
        description="Read-only retrospective reports; response schema v2. Local use only.",
        docs_url=None, redoc_url=None, redirect_slashes=False,
    )

    @app.middleware("http")
    async def guard_request(request: Request, call_next):
        # Inspect bounded raw query bytes before FastAPI decodes/validates them.
        if len(request.scope.get("query_string", b"")) > MAX_QUERY_BYTES:
            return _error(414, "query_too_long", "Query string exceeds 2048 bytes.")
        if request.url.path == "/v1/report":
            keys = list(request.query_params.keys())
            if any(len(request.query_params.getlist(key)) > 1 for key in keys):
                return _error(422, "duplicate_parameter", "Each query parameter may appear only once.")
            if request.headers.get("content-length", "0") != "0" or "transfer-encoding" in request.headers:
                return _error(400, "body_not_supported", "Report requests accept query parameters only.")
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_query(request, exc):
        # Do not expose rejected values, unknown keys, parser internals or paths.
        fields = sorted({str(part) for error in exc.errors() for part in error["loc"]
                         if part in ReportQuery.model_fields})
        return _error(422, "invalid_query", "Invalid report query; see the request contract.", fields)

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return _error(exc.status, exc.code, exc.message, exc.fields,
                      {"Retry-After": "1"} if exc.code == "report_busy" else None)

    @app.exception_handler(HTTPException)
    async def routing_error(request, exc):
        codes = {404: ("not_found", "Route not found."),
                 405: ("method_not_allowed", "Method not allowed.")}
        code, message = codes.get(exc.status_code, ("http_error", "Request failed."))
        return _error(exc.status_code, code, message, headers=exc.headers)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        return _error(500, "internal_error", "Report generation failed.")

    @app.get(
        "/v1/report", response_model=ReportResponse, response_model_exclude_unset=True,
        responses={status: {"model": ErrorResponse} for status in (400, 422, 500, 503, 414)},
    )
    def get_report(query: Annotated[ReportQuery, Query()]):
        # Synchronous routes run in FastAPI's worker pool, not on the event loop.
        # Reject overlap instead of accumulating a queue of CPU-heavy reports.
        if not active_report.acquire(blocking=False):
            raise APIError(503, "report_busy", "One report is already running; retry later.")
        try:
            current = dataset
            if current is None:
                raise APIError(503, "snapshot_not_ready", "Snapshot is not ready.")
            if query.season != current.source_manifest["season"]:
                raise APIError(422, "season_unavailable", "Season differs from the configured snapshot.", ["season"])
            needed = {
                "yardline_100": query.yardline_min is not None or query.yardline_max is not None,
                "score_differential": query.score_min is not None or query.score_max is not None,
                "qtr": query.period is not None,
                "quarter_seconds_remaining": query.clock_min is not None or query.clock_max is not None,
            }
            missing = sorted(name for name, required in needed.items()
                             if required and name not in current.optional_columns)
            if missing:
                raise APIError(422, "context_unavailable", "Snapshot lacks requested context columns.", missing)
            return build_report(current, source_label=source_label, **query.builder_options())
        finally:
            active_report.release()

    return app


def app_from_env() -> FastAPI:
    """Uvicorn --factory entry point; only operator environment selects the input."""
    snapshot = os.environ.get("NFL_OI_SNAPSHOT")
    source_label = os.environ.get("NFL_OI_SOURCE_LABEL")
    if not snapshot or not source_label:
        raise ValueError("Set NFL_OI_SNAPSHOT and NFL_OI_SOURCE_LABEL before starting the API")
    return create_app(snapshot=Path(snapshot), source_label=source_label)
