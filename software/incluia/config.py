from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_opt_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _as_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.split("|") if line.strip()]


@dataclass(slots=True)
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    driver: str = "simulator"
    history_size: int = 200

    simulator_interval_s: float = 1.2
    simulator_lines: list[str] | None = None

    faster_model_size: str = "tiny"
    faster_compute_type: str = "int8"
    faster_language: str = "es"
    faster_phrase_time_limit_s: int = 4
    faster_vad_filter: bool = True
    faster_device_index: int | None = None
    faster_sample_rate: int | None = None
    faster_queue_max_chunks: int = 8

    whisper_cpp_binary: str = "./whisper.cpp/build/bin/whisper-stream"
    whisper_cpp_model: str = "./whisper.cpp/models/ggml-base.bin"
    whisper_cpp_threads: int = 4
    whisper_cpp_step_ms: int = 2000
    whisper_cpp_length_ms: int = 8000
    whisper_cpp_vad_threshold: float = 0.6

    fallback_to_simulator: bool = True

    ap_ssid: str = "Inclu-IA_Classroom"
    ap_url: str = "http://192.168.4.1:5000"
    socket_transport: str = "polling"

    @staticmethod
    def from_env() -> "AppConfig":
        simulator_lines = _as_lines(os.getenv("INCLUIA_SIM_LINES"))

        return AppConfig(
            host=os.getenv("INCLUIA_HOST", "0.0.0.0"),
            port=_as_int(os.getenv("INCLUIA_PORT"), 5000),
            debug=_as_bool(os.getenv("INCLUIA_DEBUG"), False),
            driver=os.getenv("INCLUIA_DRIVER", "simulator").strip(),
            history_size=_as_int(os.getenv("INCLUIA_HISTORY_SIZE"), 200),
            simulator_interval_s=_as_float(os.getenv("INCLUIA_SIM_INTERVAL_S"), 1.2),
            simulator_lines=simulator_lines or None,
            faster_model_size=os.getenv("INCLUIA_FW_MODEL", "tiny"),
            faster_compute_type=os.getenv("INCLUIA_FW_COMPUTE_TYPE", "int8"),
            faster_language=os.getenv("INCLUIA_FW_LANGUAGE", "es"),
            faster_phrase_time_limit_s=_as_int(os.getenv("INCLUIA_FW_PHRASE_LIMIT_S"), 4),
            faster_vad_filter=_as_bool(os.getenv("INCLUIA_FW_VAD"), True),
            faster_device_index=_as_opt_int(os.getenv("INCLUIA_AUDIO_DEVICE_INDEX")),
            faster_sample_rate=_as_opt_int(os.getenv("INCLUIA_AUDIO_SAMPLE_RATE")),
            faster_queue_max_chunks=_as_int(os.getenv("INCLUIA_FW_QUEUE_MAX_CHUNKS"), 8),
            whisper_cpp_binary=os.getenv(
                "INCLUIA_WCPP_BIN", "./whisper.cpp/build/bin/whisper-stream"
            ),
            whisper_cpp_model=os.getenv(
                "INCLUIA_WCPP_MODEL", "./whisper.cpp/models/ggml-base.bin"
            ),
            whisper_cpp_threads=_as_int(os.getenv("INCLUIA_WCPP_THREADS"), 4),
            whisper_cpp_step_ms=_as_int(os.getenv("INCLUIA_WCPP_STEP_MS"), 2000),
            whisper_cpp_length_ms=_as_int(os.getenv("INCLUIA_WCPP_LENGTH_MS"), 8000),
            whisper_cpp_vad_threshold=_as_float(
                os.getenv("INCLUIA_WCPP_VAD_THRESHOLD"), 0.6
            ),
            fallback_to_simulator=_as_bool(os.getenv("INCLUIA_FALLBACK_SIM"), True),
            ap_ssid=os.getenv("INCLUIA_AP_SSID", "Inclu-IA_Classroom"),
            ap_url=os.getenv("INCLUIA_AP_URL", "http://192.168.4.1:5000"),
            socket_transport=os.getenv("INCLUIA_SOCKET_TRANSPORT", "polling").strip().lower(),
        )
