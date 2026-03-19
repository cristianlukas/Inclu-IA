from __future__ import annotations

from collections import deque
from pathlib import Path
from threading import Event, Lock
from typing import Any

import os
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
from flask_socketio import SocketIO

from .config import AppConfig
from .events import CaptionEvent, StatusEvent, now_ms
from .transcribers import build_transcriber
from .transcribers.simulator import SimulatorTranscriber


def create_server(config: AppConfig | None = None) -> tuple[Flask, SocketIO, AppConfig]:
    cfg = config or AppConfig.from_env()

    root_dir = Path(__file__).resolve().parents[2]
    template_dir = root_dir / "web" / "templates"
    static_dir = root_dir / "web" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.config["SECRET_KEY"] = "inclu-ia-dev"

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=False,
        engineio_logger=False,
    )

    history: deque[dict[str, Any]] = deque(maxlen=max(20, cfg.history_size))
    runtime: dict[str, Any] = {
        "driver": cfg.driver,
        "active_source": cfg.driver,
        "status": StatusEvent(state="idle", detail="Inicializando").to_dict(),
        "started": False,
    }

    stop_event = Event()
    start_lock = Lock()

    def emit_status(event: StatusEvent) -> None:
        payload = event.to_dict()
        runtime["status"] = payload
        socketio.emit("status", payload)

    def emit_caption(event: CaptionEvent) -> None:
        payload = event.to_dict()
        if payload.get("is_final"):
            history.append(payload)
        socketio.emit("caption", payload)

    def run_transcriber() -> None:
        try:
            transcriber = build_transcriber(cfg)
            runtime["active_source"] = transcriber.source_name
            transcriber.run(stop_event, emit_caption, emit_status)
        except Exception as exc:
            emit_status(StatusEvent(state="error", detail=f"Driver fallo: {exc}"))

            should_fallback = cfg.fallback_to_simulator and cfg.driver != "simulator"
            if not should_fallback or stop_event.is_set():
                return

            emit_status(StatusEvent(state="idle", detail="Fallback a simulador"))
            runtime["active_source"] = "simulator"
            simulator = SimulatorTranscriber(
                interval_s=cfg.simulator_interval_s,
                lines=cfg.simulator_lines,
            )
            simulator.run(stop_event, emit_caption, emit_status)

    def ensure_background_started() -> None:
        with start_lock:
            if runtime["started"]:
                return
            runtime["started"] = True
            socketio.start_background_task(run_transcriber)

    @app.before_request
    def _start_once() -> None:
        ensure_background_started()

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/_health")
    def health() -> Any:
        return jsonify(
            {
                "ok": True,
                "driver": runtime["driver"],
                "active_source": runtime["active_source"],
                "status": runtime["status"],
                "history_items": len(history),
                "t_server_ms": now_ms(),
            }
        )

    @app.get("/api/config")
    def get_config() -> Any:
        return jsonify(
            {
                "driver": runtime["driver"],
                "active_source": runtime["active_source"],
                "ap_ssid": cfg.ap_ssid,
                "ap_url": cfg.ap_url,
                "history_size": cfg.history_size,
                "status": runtime["status"],
            }
        )

    @app.get("/api/history")
    def get_history() -> Any:
        return jsonify({"items": list(history), "t_server_ms": now_ms()})

    @app.post("/api/clear")
    def clear_history() -> Any:
        history.clear()
        payload = {"t_server_ms": now_ms()}
        socketio.emit("history_cleared", payload)
        return jsonify(payload)

    @socketio.on("connect")
    def on_connect() -> None:
        ensure_background_started()
        socketio.emit("status", runtime["status"], to=request.sid)
        socketio.emit("history", {"items": list(history)}, to=request.sid)

    @socketio.on("clear_history")
    def on_clear_history() -> None:
        history.clear()
        socketio.emit("history_cleared", {"t_server_ms": now_ms()})
        
    return app, socketio, cfg