"""Test-only loopback server; never reads an operator's real snapshot or fetches data."""

import csv
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import uvicorn

from opponent_intelligence.api import create_app
from tests_api.synthetic_snapshot import write_snapshot
from tests_api.test_frontend_contract import ROOT, time_rows


SOURCE_LABEL = "SYNTHETIC browser integration fixture; invented plays, IDs and timestamps; not real NFL observations"


def main():
    with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as stream:
        # Reuse the established four-stage fixture, not a second analytics/data pipeline.
        rows = time_rows(list(csv.DictReader(stream)), "time_four_stage")
    temporary = TemporaryDirectory(prefix="nfl-oi-browser-synthetic-")
    with temporary as directory:
        snapshot = write_snapshot(Path(directory), rows, list(rows[0]))
        app = create_app(snapshot=snapshot, source_label=SOURCE_LABEL)
        lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def clean_snapshot(application):
            try:
                async with lifespan(application):
                    yield
            finally:
                # Uvicorn re-raises SIGTERM after lifespan shutdown, before returning
                # from run(). Clean before then; the outer context covers startup errors.
                temporary.cleanup()

        app.router.lifespan_context = clean_snapshot
        # Incoming loopback requests still work. No outbound acquisition is allowed.
        with patch("socket.socket.connect", side_effect=AssertionError("Test API must not connect outbound")):
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
