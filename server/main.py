"""Application factory. Binds loopback, migrates on start, serves the built frontend if present."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path as _Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import paths
from server.agents import loop as agent_loop
from server.agents.approvals import Approvals
from server.agents.scheduler import JobScheduler
from server.api import (
    agents,
    chat,
    chat_agent,
    client_errors,
    connections,
    context,
    conversations,
    council,
    data,
    files,
    forecast,
    hardware,
    home,
    hud,
    knowledge,
    local_models,
    memory,
    memory_timeline,
    messages,
    models_api,
    prefs,
    search,
    tools,
    trading,
    updates,
    voice,
    workflows,
    xray,
)
from server.api import attachments as attachments_api
from server.api import briefing as briefing_api
from server.api import images as images_api
from server.api import phone as phone_api
from server.api import wake as wake_api
from server.briefing.service import Briefings
from server.chat.agentic import ChatAgents
from server.chat.live import LiveRuns
from server.db import repo
from server.db.connection import Database
from server.db.migrate import migrate
from server.deps import AppState, State
from server.errors import SovereignError, handle_sovereign_error
from server.files.propose import Proposals
from server.files.workspace import Workspace
from server.forecast import engine as forecast_engine
from server.forecast.jobs import ForecastJobs
from server.forecast.pack import ForecastPack
from server.hardware.downloader import Downloader
from server.home.hub import Hub
from server.imagegen.engine import ImageEngine
from server.knowledge import retrieval
from server.knowledge.indexer import Indexer
from server.knowledge.watcher import Watcher
from server.phone.gate import Gate
from server.phone.listener import PhoneListener
from server.phone.pairing import Pairing
from server.providers.launcher import LlamaServer
from server.providers.registry import ProviderRegistry
from server.settings import Settings, load_settings
from server.trading.copilot import Copilot
from server.updates.updater import Updater
from server.version import VERSION
from server.voice.pack import VoicePack

WEB_DIST = paths.resource("web", "dist")


class Health(BaseModel):
    status: str
    version: str
    migrations_applied: list[str]
    sqlite_vec: bool
    sqlite_vec_error: str = ""
    bind: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    db = Database(settings.paths.db_path)
    registry = ProviderRegistry.from_settings(settings)
    live = LiveRuns()
    indexer = Indexer(db, live)

    def reindex(source_id: str) -> None:
        """A watched file changed. Reindexing goes through the same indexer, so it inherits the
        pause switch and the rule about never competing with generation for the GPU."""
        path = _source_path(db, source_id)
        embedder = retrieval.embedder_for(settings)
        asyncio.create_task(indexer.index(source_id, path, embedder))

    approvals = Approvals()
    state = AppState(
        settings=settings,
        db=db,
        registry=registry,
        live=live,
        indexer=indexer,
        watcher=Watcher(reindex),
        approvals=approvals,
        llama=LlamaServer(settings, db),
        downloader=Downloader(db, settings.paths.models_dir),
        voice_pack=VoicePack(settings),
        home=Hub(settings.paths.data_dir),
        forecasts=ForecastJobs(db, forecast_engine.shared(settings)),
        forecast_pack=ForecastPack(settings),
        updater=Updater(settings),
        files=Proposals(Workspace(settings.paths.data_dir), registry),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        with db.session() as conn:
            app.state.migrations = migrate(conn)
            # A run that was mid-generation when the process died cannot be resumed: the task is
            # gone. Say so in the row rather than leaving it looking alive forever.
            for stale in repo.agents.stale_runs(conn):
                repo.agents.set_status(conn, stale, "failed", error="the server restarted")
        runtime = agent_loop.Runtime(db, registry, settings, live, approvals)
        state.scheduler = JobScheduler(runtime)
        state.chat_agents = ChatAgents(runtime)
        state.briefings = Briefings(state)
        state.copilot = Copilot(db, settings)
        with db.session() as conn:
            if chosen := repo.settings.get(conn, images_api.CHOSEN):
                settings.images.model = str(chosen)
        state.images = ImageEngine(settings)
        state.phone, state.pairing = PhoneListener(), Pairing()
        with db.session() as conn:
            phone_on = bool(repo.settings.get(conn, phone_api.ENABLED))
        if phone_on:
            await phone_api.switch(state, app, True)
        watching = asyncio.create_task(state.copilot.run_forever())
        state.scheduler.start()
        briefing_api.schedule(state)
        # Loading a model takes tens of seconds, and the app must not be unreachable for them: the
        # launcher runs in the background and the provider list reports what it is doing.
        assert state.llama is not None
        launching = asyncio.create_task(state.llama.start())
        assert state.updater is not None
        checking = asyncio.create_task(state.updater.run_forever())
        try:
            yield
        finally:
            state.scheduler.shutdown()
            launching.cancel()
            checking.cancel()
            watching.cancel()
            await state.phone.stop()
            await state.llama.stop()

    app = FastAPI(
        title="Jarvis",
        version=VERSION,
        summary="A local-first AI workspace",
        lifespan=lifespan,
    )
    app.state.app = state
    app.state.migrations = []
    app.add_exception_handler(SovereignError, handle_sovereign_error)
    # Outermost: nothing from the network reaches a route without a paired device's token.
    app.add_middleware(Gate)

    @app.get("/api/health", tags=["health"])
    def health(state: State) -> Health:
        return Health(
            status="ok",
            version=VERSION,
            migrations_applied=list(app.state.migrations),
            sqlite_vec=state.db.vec_available,
            sqlite_vec_error=state.db.vec_error,
            bind=f"{state.settings.server.host}:{state.settings.server.port}",
        )

    for router in (
        conversations.router,
        chat.router,
        models_api.router,
        hardware.router,
        messages.router,
        context.router,
        xray.router,
        hud.router,
        memory_timeline.router,
        briefing_api.router,
        workflows.router,
        trading.router,
        wake_api.router,
        attachments_api.router,
        images_api.router,
        phone_api.router,
        memory.router,
        knowledge.router,
        search.router,
        council.router,
        voice.router,
        agents.router,
        tools.router,
        tools.audit_router,
        home.router,
        forecast.router,
        updates.router,
        files.router,
        local_models.router,
        chat_agent.router,
        client_errors.router,
        connections.router,
        data.router,
        prefs.router,
    ):
        app.include_router(router)

    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return app


def _source_path(db: Database, source_id: str) -> _Path:
    with db.session() as conn:
        row = conn.execute("SELECT path FROM sources WHERE id = ?", (source_id,)).fetchone()
    return _Path(row["path"] if row else ".")


app = create_app()
