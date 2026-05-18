from __future__ import annotations

from incluia.app import create_server
from incluia.config import AppConfig


def test_health_endpoint_reports_runtime_status() -> None:
    cfg = AppConfig(
        driver="simulator",
        simulator_interval_s=999.0,
        history_size=20,
    )
    app, _socketio, _cfg = create_server(cfg)
    with app.app_context():
        response = app.view_functions["health"]()
    payload = response.get_json()

    assert payload["ok"] is True
    assert payload["driver"] == "simulator"
    assert payload["active_source"] in {"simulator", "faster_whisper", "whisper_cpp"}
    assert payload["status"]["state"] in {"idle", "listening", "transcribing", "error"}
