"""Compares Kokoro voices (Apache 2.0, runs locally): how well Whisper understands them, pace and pitch.

Writes tools/samples/kokoro_<voice>.wav to listen to.
"""

import difflib
import re
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

from voice_test import load16k, pitch

HERE = Path(__file__).parent
TEXT = ("Do finance YouTubers move stock prices? I took the three biggest stock-picking channels in the U.S. "
        "and in Poland. AI read more than twenty-five hundred of their videos, and tagged every call as bullish "
        "or bearish. Too small to trade on. But big enough to measure.")
VOICES = ["am_michael", "am_fenrir", "am_onyx", "am_puck", "am_echo", "am_eric", "am_liam", "bm_george", "bm_fable",
          "bm_lewis", "af_heart", "af_bella"]


def words(s: str) -> list[str]:
    return re.findall(r"[a-z]+", s.lower().replace("u.s.", "us"))


kokoro = Kokoro(str(HERE / "voices" / "kokoro" / "kokoro-v1.0.onnx"), str(HERE / "voices" / "kokoro" / "voices-v1.0.bin"))
model = WhisperModel("small", device="cpu", compute_type="int8")
out_dir = HERE / "samples"
out_dir.mkdir(exist_ok=True)
for name in VOICES:
    audio, rate = kokoro.create(TEXT, voice=name, speed=1.0, lang="en-us")
    out = out_dir / f"kokoro_{name}.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    seconds = len(audio) / rate
    segments, _ = model.transcribe(load16k(out), language="en")
    heard = " ".join(s.text for s in segments)
    ratio = difflib.SequenceMatcher(None, words(TEXT), words(heard)).ratio()
    print(f"{name:11} {seconds:5.1f}s {len(words(TEXT)) / seconds:.2f} w/s pitch {pitch(out):5.0f} Hz "
          f"understood {ratio:.0%} | {heard.strip()[:90]}", flush=True)
