from __future__ import annotations

import queue
import sys
import builtins
from threading import Event
from types import ModuleType
from typing import Any

import pytest

from incluia.transcribers.faster_whisper_driver import FasterWhisperTranscriber


class _FakeMicrophone:
    SAMPLE_RATE = 16_000

    def __init__(self, sample_rate: int | None, device_index: int | None) -> None:
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.stream: object | None = None

    def __enter__(self) -> "_FakeMicrophone":
        assert self.stream is None
        self.stream = object()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.stream = None


class _FakeRecognizer:
    def __init__(self) -> None:
        self.dynamic_energy_threshold = False

    def adjust_for_ambient_noise(self, source: _FakeMicrophone, duration: int = 1) -> None:
        assert source.stream is not None

    def listen_in_background(
        self,
        source: _FakeMicrophone,
        callback: Any,
        phrase_time_limit: int | None = None,
    ) -> Any:
        # Regression guard: source must NOT still be inside a context manager here.
        assert source.stream is None
        return lambda wait_for_stop=False: None


class _FakeWhisperModel:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class _FakeAudio:
    def get_wav_data(self) -> bytes:
        return b"RIFF"


class _FakeSegment:
    def __init__(self, text: str, start: float, end: float) -> None:
        self.text = text
        self.start = start
        self.end = end


def _install_fake_modules(monkeypatch: Any, recognizer_cls: type[Any]) -> None:
    fake_sr = ModuleType("speech_recognition")
    fake_sr.Microphone = _FakeMicrophone
    fake_sr.Recognizer = recognizer_cls
    monkeypatch.setitem(sys.modules, "speech_recognition", fake_sr)

    fake_fw = ModuleType("faster_whisper")
    fake_fw.WhisperModel = _FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_fw)


def _build_transcriber(sample_rate: int | None = 16_000, queue_max_chunks: int = 2) -> FasterWhisperTranscriber:
    return FasterWhisperTranscriber(
        model_size="tiny",
        compute_type="int8",
        language="es",
        phrase_time_limit_s=2,
        vad_filter=True,
        device_index=None,
        sample_rate=sample_rate,
        queue_max_chunks=queue_max_chunks,
    )


def test_faster_whisper_microphone_context_is_not_reused(monkeypatch: Any) -> None:
    _install_fake_modules(monkeypatch, _FakeRecognizer)

    statuses: list[str] = []
    stop_event = Event()
    stop_event.set()

    transcriber = _build_transcriber()

    transcriber.run(
        stop_event=stop_event,
        on_caption=lambda _event: None,
        on_status=lambda event: statuses.append(event.state),
    )

    assert "listening" in statuses


def test_faster_whisper_fallbacks_to_auto_sample_rate(monkeypatch: Any) -> None:
    _install_fake_modules(monkeypatch, _FakeRecognizer)
    requested_rates: list[int | None] = []

    def _fake_open(self: FasterWhisperTranscriber, rate: int | None) -> _FakeMicrophone:
        requested_rates.append(rate)
        if rate is not None:
            raise RuntimeError("unsupported rate")
        return _FakeMicrophone(rate, None)

    monkeypatch.setattr(FasterWhisperTranscriber, "_open_microphone", _fake_open)

    statuses: list[str] = []
    stop_event = Event()
    stop_event.set()
    transcriber = _build_transcriber(sample_rate=48_000)

    transcriber.run(stop_event, lambda _event: None, lambda event: statuses.append(event.detail))

    assert requested_rates == [48_000, None]
    assert any("reintentando con frecuencia automatica" in detail for detail in statuses)


def test_faster_whisper_reports_missing_dependencies(monkeypatch: Any) -> None:
    real_import = builtins.__import__

    def _import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
        if name in {"speech_recognition", "faster_whisper"}:
            raise ImportError(f"missing {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)

    statuses: list[str] = []
    stop_event = Event()
    transcriber = _build_transcriber()

    with pytest.raises(RuntimeError, match="Missing dependencies"):
        transcriber.run(stop_event, lambda _event: None, lambda event: statuses.append(event.detail))

    assert any("Dependencia faltante" in detail for detail in statuses)


def test_transcribe_audio_cleans_tmp_file_on_error(monkeypatch: Any, tmp_path: Any) -> None:
    transcriber = _build_transcriber()

    class _BrokenModel:
        def transcribe(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("boom")

    tmp_file = tmp_path / "chunk.wav"

    class _TmpFile:
        name = str(tmp_file)

        def write(self, data: bytes) -> None:
            tmp_file.write_bytes(data)

        def __enter__(self) -> "_TmpFile":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

    monkeypatch.setattr("tempfile.NamedTemporaryFile", lambda **_kwargs: _TmpFile())
    statuses: list[str] = []
    transcriber._transcribe_audio(
        model=_BrokenModel(),
        audio=_FakeAudio(),
        on_caption=lambda _event: None,
        on_status=lambda event: statuses.append(event.state),
    )

    assert not tmp_file.exists()
    assert "error" in statuses


def test_faster_whisper_queue_saturation_emits_status(monkeypatch: Any) -> None:
    class _BusyQueue:
        def __init__(self, maxsize: int) -> None:
            self.maxsize = maxsize
            self.items: list[Any] = [_FakeAudio()]
            self.reported = False

        def put_nowait(self, item: Any) -> None:
            if len(self.items) >= self.maxsize:
                raise queue.Full
            self.items.append(item)

        def get_nowait(self) -> Any:
            if not self.items:
                raise queue.Empty
            return self.items.pop(0)

        def get(self, timeout: float | None = None) -> Any:
            raise queue.Empty

    class _RecognizerOverflow(_FakeRecognizer):
        def __init__(self) -> None:
            super().__init__()

        def listen_in_background(self, source: _FakeMicrophone, callback: Any, phrase_time_limit: int | None = None) -> Any:
            callback(self, _FakeAudio())
            callback(self, _FakeAudio())
            stop_event.set()
            return lambda wait_for_stop=False: None

    _install_fake_modules(monkeypatch, _RecognizerOverflow)
    monkeypatch.setattr("incluia.transcribers.faster_whisper_driver.queue.Queue", _BusyQueue)
    monkeypatch.setattr("incluia.transcribers.faster_whisper_driver.time.time", lambda: 10_000.0)

    status_details: list[str] = []
    stop_event = Event()
    transcriber = _build_transcriber(queue_max_chunks=1)
    transcriber.run(stop_event, lambda _event: None, lambda event: status_details.append(event.detail))

    assert any("Audio en cola saturado" in detail for detail in status_details)


def test_faster_whisper_emits_transcribing_and_listening(monkeypatch: Any) -> None:
    transcriber = _build_transcriber()

    class _Model:
        def transcribe(self, *_args: Any, **_kwargs: Any) -> Any:
            return iter([_FakeSegment("hola", 0.0, 0.2)]), None

    statuses: list[str] = []
    transcriber._transcribe_audio(
        model=_Model(),
        audio=_FakeAudio(),
        on_caption=lambda _event: None,
        on_status=lambda event: statuses.append(event.state),
    )

    assert statuses[0] == "transcribing"
    assert statuses[-1] == "listening"


@pytest.mark.hardware
def test_faster_whisper_hardware_smoke_placeholder() -> None:
    pytest.skip("Ejecutar manualmente en dispositivo con microfono y dependencias reales")
