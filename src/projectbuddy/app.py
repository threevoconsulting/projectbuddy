"""FastAPI application factory.

Wires the adapter container (lifespan), mounts the portable face front-end as static
assets, and registers the REST routers. Build with
``uvicorn projectbuddy.app:create_app --factory``.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from projectbuddy import __version__
from projectbuddy.api import converse, person, recognition, session, ws_converse
from projectbuddy.config import Settings, get_settings
from projectbuddy.core.retention import sweep_face_retention
from projectbuddy.deps import Container
from projectbuddy.protocol.rest import HealthResponse

_WEB_DIR = Path(__file__).parent / "web"
_PARENT_DIR = Path(__file__).parent / "parent"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    async def _retention_loop(container: Container) -> None:
        """Periodically delete face data past its retention date (M8)."""
        while True:
            await asyncio.sleep(settings.retention_sweep_seconds)
            with contextlib.suppress(Exception):
                sweep_face_retention(container.consents, container.face_embeddings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = Container.build(settings)
        app.state.container = container
        await container.llm.warmup()  # pre-warm to protect first-token latency
        # Enforce retention immediately, then on a timer.
        sweep_face_retention(container.consents, container.face_embeddings)
        retention_task = asyncio.create_task(_retention_loop(container))
        try:
            yield
        finally:
            retention_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await retention_task
            container.db.close()

    app = FastAPI(title="Buddy", version=__version__, lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    app.include_router(converse.router)
    app.include_router(person.router)
    app.include_router(session.router)
    app.include_router(ws_converse.router)  # WS /ws/converse — the realtime voice loop
    app.include_router(recognition.router)  # M7: face recognition + parental consent

    # The face (vanilla web UI / PWA). Same artifact runs in a Pi Chromium kiosk.
    app.mount("/app", StaticFiles(directory=_WEB_DIR, html=True), name="web")
    # The parent companion app (M9): transparency + control surface, vanilla SPA.
    app.mount("/parent", StaticFiles(directory=_PARENT_DIR, html=True), name="parent")

    return app
