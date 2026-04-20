from __future__ import annotations

from ..config import AppConfig
from .base import Transcriber
from .faster_whisper_driver import FasterWhisperTranscriber
from .simulator import SimulatorTranscriber
from .whisper_cpp_driver import WhisperCppTranscriber


def build_transcriber(config: AppConfig) -> Transcriber:
    driver = config.driver.strip().lower()

    if driver == "simulator":
        return SimulatorTranscriber(
            interval_s=config.simulator_interval_s,
            lines=config.simulator_lines,
        )

    if driver in {"faster_whisper", "faster-whisper"}:
        return FasterWhisperTranscriber(
            model_size=config.faster_model_size,
            compute_type=config.faster_compute_type,
            language=config.faster_language,
            phrase_time_limit_s=config.faster_phrase_time_limit_s,
            vad_filter=config.faster_vad_filter,
            device_index=config.faster_device_index,
            sample_rate=config.faster_sample_rate,
            queue_max_chunks=config.faster_queue_max_chunks,
        )

    if driver in {"whisper_cpp", "whisper.cpp", "whisper-cpp"}:
        return WhisperCppTranscriber(
            binary_path=config.whisper_cpp_binary,
            model_path=config.whisper_cpp_model,
            threads=config.whisper_cpp_threads,
            step_ms=config.whisper_cpp_step_ms,
            length_ms=config.whisper_cpp_length_ms,
            vad_threshold=config.whisper_cpp_vad_threshold,
            language=config.faster_language,
        )

    raise ValueError(
        f"INCLUIA_DRIVER invalido: '{config.driver}'. Usa simulator, faster_whisper o whisper_cpp."
    )


__all__ = ["build_transcriber", "Transcriber"]
