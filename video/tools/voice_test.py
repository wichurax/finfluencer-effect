"""Compares the Polish Piper voices: how well Whisper understands them and how high they sound."""

import difflib
import re
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from piper import PiperVoice

HERE = Path(__file__).parent
TEXT = ("Czy youtuberzy od giełdy ruszają kursami akcji? Sprawdziłem dwa tysiące pięćset trzydzieści trzy filmy. "
        "W Polsce efekt zostaje, nawet bez newsów, mocniej na małych spółkach.")


def words(s: str) -> list[str]:
    return re.findall(r"[a-ząćęłńóśźż]+", s.lower())


def load16k(path: Path) -> np.ndarray:
    """The wav as float32 mono at 16 kHz, the input Whisper expects (no ffmpeg/av needed)."""
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(len(x) * 16000 / rate)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def pitch(path: Path) -> float:
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    estimates = []
    for start in range(0, len(x) - 2048, 1024):
        frame = x[start:start + 2048]
        if np.abs(frame).mean() < 500:
            continue
        corr = np.correlate(frame, frame, "full")[2047:]
        lo, hi = rate // 300, rate // 70  # 70-300 Hz
        lag = lo + int(np.argmax(corr[lo:hi]))
        if corr[lag] > 0.3 * corr[0]:
            estimates.append(rate / lag)
    return float(np.median(estimates)) if estimates else float("nan")


if __name__ == "__main__":  # the English tests import load16k and pitch from here
    model = WhisperModel("small", device="cpu", compute_type="int8")
    for name in ("gosia", "darkman", "mc_speech"):
        voice = PiperVoice.load(str(HERE / "voices" / f"pl_PL-{name}-medium.onnx"))
        out = HERE / f"sample_{name}.wav"
        with wave.open(str(out), "wb") as w:
            voice.synthesize_wav(TEXT, w)
        with wave.open(str(out)) as w:
            seconds = w.getnframes() / w.getframerate()
        segments, _ = model.transcribe(load16k(out), language="pl")
        heard = " ".join(s.text for s in segments)
        ratio = difflib.SequenceMatcher(None, words(TEXT), words(heard)).ratio()
        print(f"{name:10} {seconds:5.1f}s  {len(words(TEXT)) / seconds:.2f} words/s  pitch {pitch(out):5.0f} Hz  "
              f"understood {ratio:.0%} | {heard.strip()[:110]}")
