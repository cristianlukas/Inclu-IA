from __future__ import annotations

import os
import queue
import tempfile
import time
from threading import Event
from typing import Any

from ..events import CaptionEvent, StatusEvent
from .base import CaptionCallback, StatusCallback, Transcriber


class FasterWhisperTranscriber(Transcriber):
    source_name = "faster_whisper"

    def __init__(
        self,
        model_size: str,
        compute_type: str,
        language: str,
        phrase_time_limit_s: int,
        vad_filter: bool,
        device_index: int | None,
        sample_rate: int | None,
        queue_max_chunks: int,
    ) -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self.language = language
        self.phrase_time_limit_s = phrase_time_limit_s
        self.vad_filter = vad_filter
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.queue_max_chunks = max(1, queue_max_chunks)

    def _open_microphone(self, sample_rate: int | None) -> Any:
        import speech_recognition as sr_module

        return sr_module.Microphone(
            sample_rate=sample_rate,
            device_index=self.device_index,
        )

    def _transcribe_audio(
        self,
        model: Any,
        audio: Any,
        on_caption: CaptionCallback,
        on_status: StatusCallback,
    ) -> None:
        tmp_path = ""
        try:
            on_status(StatusEvent(state="transcribing", detail="Procesando audio"))

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio.get_wav_data())
                tmp_path = tmp.name

            segments, _ = model.transcribe(
                tmp_path,
                language=self.language,
                vad_filter=self.vad_filter,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
            )

            partial = ""
            first_ms: int | None = None
            last_ms: int | None = None

            for segment in segments:
                seg_text = segment.text.strip()
                if not seg_text:
                    continue

                partial = f"{partial} {seg_text}".strip()
                if first_ms is None:
                    first_ms = int(segment.start * 1000)
                last_ms = int(segment.end * 1000)

                on_caption(
                    CaptionEvent(
                        text=partial,
                        is_final=False,
                        source=self.source_name,
                        t0_ms=first_ms,
                        t1_ms=last_ms,
                    )
                )

            if partial:
                on_caption(
                    CaptionEvent(
                        text=partial,
                        is_final=True,
                        source=self.source_name,
                        t0_ms=first_ms,
                        t1_ms=last_ms,
                    )
                )
                on_status(StatusEvent(state="listening", detail="Esperando audio"))
            else:
                on_status(StatusEvent(state="listening", detail="Sin voz detectada"))

        except Exception as exc:
            on_status(StatusEvent(state="error", detail=f"Transcripcion: {exc}"))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def run(
        self,
        stop_event: Event,
        on_caption: CaptionCallback,
        on_status: StatusCallback,
    ) -> None:
        try:
            import speech_recognition as sr
            from faster_whisper import WhisperModel
        except ImportError as exc:
            on_status(StatusEvent(state="error", detail=f"Dependencia faltante: {exc}"))
            raise RuntimeError("Missing dependencies for faster_whisper driver") from exc

        on_status(
            StatusEvent(
                state="idle",
                detail=f"Cargando modelo {self.model_size} ({self.compute_type})",
            )
        )

        model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type=self.compute_type,
        )

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True

        source_context = None
        requested_sample_rate = self.sample_rate
        try:
            source_context = self._open_microphone(requested_sample_rate)
            source = source_context.__enter__()
        except Exception as exc:
            if requested_sample_rate is None:
                on_status(
                    StatusEvent(
                        state="error",
                        detail=f"Audio: no se pudo abrir microfono ({exc})",
                    )
                )
                return

            on_status(
                StatusEvent(
                    state="idle",
                    detail=(
                        f"Fallo audio con {requested_sample_rate} Hz; reintentando con frecuencia automatica"
                    ),
                )
            )
            try:
                source_context = self._open_microphone(None)
                source = source_context.__enter__()
            except Exception as retry_exc:
                on_status(
                    StatusEvent(
                        state="error",
                        detail=(
                            "Audio: no se pudo abrir microfono. "
                            f"device_index={self.device_index}, sample_rate={requested_sample_rate}, "
                            f"error={retry_exc}"
                        ),
                    )
                )
                return

        stop_listening = None
        audio_queue: queue.Queue[Any] = queue.Queue(maxsize=self.queue_max_chunks)
        dropped_chunks = 0
        last_drop_notice_ms = 0

        def _on_audio(_recognizer: Any, audio: Any) -> None:
            nonlocal dropped_chunks, last_drop_notice_ms

            if stop_event.is_set():
                return

            try:
                audio_queue.put_nowait(audio)
                return
            except queue.Full:
                pass

            # If queue is full, drop oldest to keep the stream moving.
            try:
                _ = audio_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                audio_queue.put_nowait(audio)
            except queue.Full:
                dropped_chunks += 1
                return

            dropped_chunks += 1
            now = int(time.time() * 1000)
            if now - last_drop_notice_ms > 4000:
                last_drop_notice_ms = now
                on_status(
                    StatusEvent(
                        state="idle",
                        detail=(
                            "Audio en cola saturado: se descartaron chunks viejos para mantener streaming"
                        ),
                    )
                )

        try:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            on_status(
                StatusEvent(
                    state="listening",
                    detail=(
                        f"Microfono listo ({source.SAMPLE_RATE} Hz, mono). "
                        "Captura continua activa"
                    ),
                )
            )

            stop_listening = recognizer.listen_in_background(
                source,
                _on_audio,
                phrase_time_limit=self.phrase_time_limit_s,
            )

            while not stop_event.is_set():
                try:
                    audio = audio_queue.get(timeout=0.25)
                except queue.Empty:
                    continue

                self._transcribe_audio(model, audio, on_caption, on_status)

        finally:
            if stop_listening is not None:
                try:
                    stop_listening(wait_for_stop=False)
                except Exception:
                    pass

            if source_context is not None:
                source_context.__exit__(None, None, None)
