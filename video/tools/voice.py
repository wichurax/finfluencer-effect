"""Turns a script (scripts/<name>.json) into a voice track and caption timings.

  python tools/voice.py A            # synthetic voice: ElevenLabs, Kokoro or Piper, as the script's "engine" says
  python tools/voice.py A my.wav     # your own recording of the script: only re-times the captions

Writes public/voice-<name>.wav and src/timeline-<name>.json. Caption times come from Whisper's word
timestamps on the audio, so they follow the voice whether it is synthetic or recorded.
"""

import difflib
import hashlib
import json
import os
import re
import sys
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
PIPER_RATE = 22050


def spoken(chunk) -> str:
    return chunk[1] if isinstance(chunk, list) else chunk.replace("*", "")


def shown(chunk) -> str:
    return chunk[0] if isinstance(chunk, list) else chunk


def tokens(s: str) -> list[str]:
    s = re.sub(r"(?<=\d),(?=\d)", "", s.lower())  # "2,500" -> "2500"
    return re.findall(r"[a-ząćęłńóśźż0-9]+", s)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        rate, channels = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return x, rate


def to16k(x: np.ndarray, rate: int) -> np.ndarray:
    n = int(len(x) * 16000 / rate)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def eleven_client():
    """The ElevenLabs client. The SDK reads ELEVENLABS_API_KEY from the environment; `npx @elevenlabs/cli onboard init`
    put it in .env.local (git-ignored), loaded here."""
    from dotenv import load_dotenv
    from elevenlabs import ElevenLabs

    load_dotenv(ROOT / ".env.local")
    # The SDK takes its default key from the environment when it is imported, which may be before load_dotenv.
    if not os.environ.get("ELEVENLABS_API_KEY"):
        sys.exit("No ELEVENLABS_API_KEY: run `npx -y @elevenlabs/cli@latest onboard init` in video/")
    return ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


def cut_leak(audio: np.ndarray, rate: int) -> np.ndarray:
    """ElevenLabs sometimes starts reading next_text at the end of a sentence: after the last word comes a pause and
    a short burst ("...by half a point. Most"), heard as a stutter once the next sentence follows. A burst under
    0.5 s after a pause of 0.25 s or more is cut, along with the pause."""
    step = rate // 50  # 20 ms frames
    loud = np.array([np.sqrt(np.mean(audio[i:i + step] ** 2)) > 0.01 for i in range(0, len(audio), step)])
    if not loud.any():
        return audio
    end = len(loud) - np.argmax(loud[::-1])  # one past the last loud frame
    start = end
    while start > 0 and loud[start - 1]:
        start -= 1
    gap = start
    while gap > 0 and not loud[gap - 1]:
        gap -= 1
    burst, pause = (end - start) * 0.02, (start - gap) * 0.02
    if gap > 0 and burst < 0.5 and pause >= 0.25:
        print(f"  cut {burst:.2f} s of sound after a {pause:.2f} s pause at the end of a sentence")
        return audio[:(gap + 5) * step]  # keep 100 ms of the pause as the word's natural release
    return audio


def eleven_cache(script: dict, text: str) -> Path:
    """Where one sentence read by ElevenLabs is kept (raw 24 kHz PCM), keyed by everything that changes the sound."""
    key = json.dumps([script["voice"], script.get("model", "eleven_v4"), script.get("voiceSettings"), text])
    return ROOT / "tools" / "cache" / "elevenlabs" / f"{hashlib.sha1(key.encode()).hexdigest()[:16]}.pcm"


def speaker(script: dict):
    """A function turning one sentence (with its neighbours, for continuity) into float32 audio, and its sample rate.
    ElevenLabs, Kokoro or Piper, per the script's "engine"."""
    if script.get("engine") == "elevenlabs":
        from elevenlabs import VoiceSettings

        client = eleven_client()

        def say(text: str, before: str = "", after: str = "") -> np.ndarray:
            # Credits are limited: a sentence already read in this voice comes from the cache, so editing one
            # sentence pays for that sentence only. (A cached sentence keeps the neighbours it was read with.)
            cached = eleven_cache(script, text)
            if not cached.exists():
                # previous_text/next_text stitch the sentences: the voice keeps its tone across the joins.
                extra = {"previous_text": before, "next_text": after}
                if script.get("voiceSettings"):
                    extra["voice_settings"] = VoiceSettings(**script["voiceSettings"])
                audio = client.text_to_speech.convert(voice_id=script["voice"], text=text,
                                                      model_id=script.get("model", "eleven_v4"),
                                                      output_format="pcm_24000", **{k: v for k, v in extra.items() if v})
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(b"".join(audio))
                print(f"  read by ElevenLabs ({len(text)} credits): {text}")
            return cut_leak(np.frombuffer(cached.read_bytes(), dtype=np.int16).astype(np.float32) / 32768, 24000)

        return say, 24000
    if script.get("engine") == "kokoro":
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(str(ROOT / "tools" / "voices" / "kokoro" / "kokoro-v1.0.onnx"),
                        str(ROOT / "tools" / "voices" / "kokoro" / "voices-v1.0.bin"))
        lang = "en-us" if script.get("lang", "pl") == "en" else script["lang"]
        return (lambda text, before="", after="":
                kokoro.create(text, voice=script["voice"], speed=script.get("speed", 1.0), lang=lang)[0], 24000)
    from piper import PiperVoice, SynthesisConfig

    voice_name = script["voice"] if "_" in script["voice"] else f"pl_PL-{script['voice']}-medium"
    voice = PiperVoice.load(str(ROOT / "tools" / "voices" / f"{voice_name}.onnx"))
    config = SynthesisConfig(length_scale=script.get("lengthScale", 1.0))
    return (lambda text, before="", after="":
            np.concatenate([np.frombuffer(c.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768
                            for c in voice.synthesize(text, syn_config=config)]), PIPER_RATE)


def sentence_texts(script: dict) -> list[str]:
    return [" ".join(spoken(c) for c in s["chunks"]) for s in script["sentences"]]


def synthesize(script: dict) -> tuple[np.ndarray, int]:
    """One utterance per sentence, joined with pauses. Returns the audio and its sample rate."""
    say, rate = speaker(script)
    pause = np.zeros(int(script.get("pause", 0.3) * rate), dtype=np.float32)
    parts = [np.zeros(int(0.25 * rate), dtype=np.float32)]
    texts = sentence_texts(script)
    for i, text in enumerate(texts):
        parts += [say(text, " ".join(texts[max(0, i - 2):i]), " ".join(texts[i + 1:i + 2])).astype(np.float32), pause]
    parts.append(np.zeros(int(0.6 * rate), dtype=np.float32))
    return np.concatenate(parts), rate


def align(script: dict, audio16k: np.ndarray) -> list[dict]:
    """Start and end of every caption chunk, by matching the script's words to Whisper's word timestamps."""
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio16k, language=script.get("lang", "pl"), word_timestamps=True)
    heard = [(w.word, w.start, w.end) for s in segments for w in s.words]
    # Whisper writes numbers as digits ("2533"); the script says them in words. Expand the digits the
    # script shows back into its spoken words, spreading the time evenly.
    expand = {}
    for sentence in script["sentences"]:
        for chunk in sentence["chunks"]:
            if isinstance(chunk, list):
                for digits in re.findall(r"\d[\d,]*", chunk[0]):
                    digits = digits.replace(",", "")
                    number_words = [t for t in tokens(chunk[1]) if t not in tokens(re.sub(r"\d[\d,]*\+?", "", chunk[0]))]
                    if number_words:
                        expand[digits] = number_words
    heard_tokens, heard_times = [], []
    for word, start, end in heard:
        for tok in tokens(word.replace(" ", "")):
            parts = expand.get(tok, [tok])
            step = (end - start) / len(parts)
            for k, part in enumerate(parts):
                heard_tokens.append(part)
                heard_times.append((start + k * step, start + (k + 1) * step))

    expected, owner = [], []  # script tokens and the (sentence, chunk) each belongs to
    for si, sentence in enumerate(script["sentences"]):
        for ci, chunk in enumerate(sentence["chunks"]):
            for tok in tokens(spoken(chunk)):
                expected.append(tok)
                owner.append((si, ci))

    times: list[tuple[float, float] | None] = [None] * len(expected)
    matcher = difflib.SequenceMatcher(None, expected, heard_tokens, autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            times[block.a + k] = heard_times[block.b + k]
    # Words Whisper heard differently get times interpolated from their neighbours.
    known = [i for i, t in enumerate(times) if t]
    for i, t in enumerate(times):
        if t is None:
            before = max((k for k in known if k < i), default=None)
            after = min((k for k in known if k > i), default=None)
            a = times[before][1] if before is not None else 0.0
            b = times[after][0] if after is not None else a + 0.4
            times[i] = (a, b)

    chunks = []
    for si, sentence in enumerate(script["sentences"]):
        for ci, chunk in enumerate(sentence["chunks"]):
            idx = [i for i, o in enumerate(owner) if o == (si, ci)]
            chunks.append({"sentence": si, "text": shown(chunk), "start": round(times[idx[0]][0], 3),
                           "end": round(times[idx[-1]][1], 3)})
    return chunks


def main() -> None:
    name = sys.argv[1]
    script = json.loads((ROOT / "scripts" / f"{name}.json").read_text(encoding="utf-8"))
    out_wav = ROOT / "public" / f"voice-{name}.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 2:  # a recording of the script
        x, rate = read_wav(Path(sys.argv[2]))
        pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    else:
        x, rate = synthesize(script)
        pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())

    chunks = align(script, to16k(x, rate))
    sentences = []
    for si, sentence in enumerate(script["sentences"]):
        own = [c for c in chunks if c["sentence"] == si]
        sentences.append({"visual": sentence["visual"], "start": own[0]["start"], "end": own[-1]["end"]})
    # A sentence's visual runs until the next sentence starts, so nothing goes blank in the pauses.
    for a, b in zip(sentences, sentences[1:]):
        a["until"] = b["start"]
    duration = len(x) / rate
    sentences[-1]["until"] = duration
    timeline = {"name": name, "duration": round(duration, 3), "audio": f"voice-{name}.wav",
                "sentences": sentences, "chunks": chunks}
    (ROOT / "src" / f"timeline-{name}.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")
    print(f"{name}: {duration:.1f} s, {len(chunks)} captions, voice -> {out_wav.name}")


if __name__ == "__main__":
    main()
