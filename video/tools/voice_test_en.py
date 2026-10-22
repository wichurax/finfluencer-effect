"""Compares the English Piper voices: how well Whisper understands them, pace and pitch."""

import difflib
import re
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from piper import PiperVoice

from voice_test import load16k, pitch

HERE = Path(__file__).parent
TEXT = ("Do finance YouTubers move stock prices? I took the three biggest stock-picking channels in the U.S. "
        "and in Poland. Too small to trade on, but big enough to measure.")


def words(s: str) -> list[str]:
    return re.findall(r"[a-z]+", s.lower().replace("u.s.", "us"))


model = WhisperModel("small", device="cpu", compute_type="int8")
for name in ("en_US-joe-medium", "en_US-john-medium", "en_US-norman-medium", "en_US-bryce-medium",
             "en_US-ljspeech-high"):
    voice = PiperVoice.load(str(HERE / "voices" / f"{name}.onnx"))
    out = HERE / f"sample_{name}.wav"
    with wave.open(str(out), "wb") as w:
        voice.synthesize_wav(TEXT, w)
    with wave.open(str(out)) as w:
        seconds = w.getnframes() / w.getframerate()
    segments, _ = model.transcribe(load16k(out), language="en")
    heard = " ".join(s.text for s in segments)
    ratio = difflib.SequenceMatcher(None, words(TEXT), words(heard)).ratio()
    print(f"{name:22} {seconds:5.1f}s {len(words(TEXT)) / seconds:.2f} w/s pitch {pitch(out):5.0f} Hz "
          f"understood {ratio:.0%} | {heard.strip()[:100]}")
