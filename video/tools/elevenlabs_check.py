"""ElevenLabs for the clip: the plan, the credits left, what one take of the script costs, and the voices the key can
use. With --samples [names...], reads a few lines of the clip in those voices into tools/samples/eleven_<name>.wav.

  tools/.venv/Scripts/python tools/elevenlabs_check.py
  tools/.venv/Scripts/python tools/elevenlabs_check.py --samples Brian Daniel George
"""

import json
import sys
import wave
from datetime import datetime

import numpy as np

from voice import ROOT, eleven_client, sentence_texts, speaker

script = json.loads((ROOT / "scripts" / "A.json").read_text(encoding="utf-8"))
texts = sentence_texts(script)
client = eleven_client()

sub = client.user.subscription.get()
reset = f", resets {datetime.fromtimestamp(sub.next_character_count_reset_unix):%Y-%m-%d}" \
    if sub.next_character_count_reset_unix else ""
print(f"plan: {sub.tier}, credits used {sub.character_count:,} of {sub.character_limit:,}{reset}")
print(f"one take of script A: {len(' '.join(texts))} characters (about as many credits)")

voices = client.voices.get_all().voices
print(f"\n{len(voices)} voices:")
for v in sorted(voices, key=lambda v: (v.category != "premade", v.name)):
    labels = ", ".join(str(x) for x in (v.labels or {}).values())
    print(f"  {v.name[:40]:40} {v.voice_id}  {v.category}: {labels}")

if "--samples" in sys.argv:
    wanted = sys.argv[sys.argv.index("--samples") + 1:]
    # The opening, the method, and a result with a number: enough to judge tone and pace.
    text = " ".join([texts[0], texts[1], texts[5]])
    out = ROOT / "tools" / "samples"
    out.mkdir(exist_ok=True)
    for v in voices:
        name = v.name.split(" ")[0]
        if name not in wanted:
            continue
        say, rate = speaker({**script, "engine": "elevenlabs", "voice": v.voice_id})
        audio = say(text)
        path = out / f"eleven_{name}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        print(f"sample: {path} ({len(audio) / rate:.1f} s, {len(text)} credits)")
