# Klip do social mediów

Jedna wersja, po angielsku, pionowa 1080×1920, z lektorem i napisami: `out/finfluencer-en.mp4` (ok. 53 s).

1. **Otwarcie:** pierwsza strona gazety (własna winieta „The Finfluencer Effect”, bez cudzych znaków) z
   nagłówkiem „Do Finance YouTubers Move Stock Prices?”. Nagłówek jest tu napisem, więc pasek napisów się nie
   pokazuje.
2. **Historia:**
   - trzy największe kanały w USA i w Polsce;
   - AI czyta prawdziwy fragment transkrypcji (Financial Education o e.l.f. Beauty), zaznacza opinię i oznacza
     ją jako „bullish”;
   - wykres kursu po filmie;
   - 2000 losowych dni.
3. **Wyniki:** jedna jasna karta z wykresem na każdą tezę, potem plansza końcowa.

Tekst lektora i napisy: `scripts/A.json`. Lektor: głos „Brian” z ElevenLabs. Wcześniej był Kokoro (licencja Apache 2.0, działa lokalnie),
głos „am_michael”. Inny głos to zmiana pola `voice` w skrypcie. Próbki 12 głosów (`tools/samples/kokoro_*.wav`)
tworzy `tools/voice_test_kokoro.py`. Własny głos też zadziała, patrz niżej.

## Głos z ElevenLabs

1. W `video/` uruchom `npx -y @elevenlabs/cli@1.7.1 onboard init` i wykonaj to, co wypisze. Logujesz się w
   przeglądarce, a klucz trafia do `.env.local` (plik jest w `.gitignore`).
2. `tools/.venv/Scripts/python tools/elevenlabs_check.py` pokazuje plan, zostałe kredyty, koszt jednego nagrania
   skryptu (ok. 730 kredytów) i dostępne głosy. Z `--samples Brian Daniel` zapisuje próbki tych głosów do
   `tools/samples/eleven_*.wav` (ok. 200 kredytów za próbkę).
3. W `scripts/A.json` ustaw `"engine": "elevenlabs"`, a w `"voice"` wpisz ID wybranego głosu. Opcjonalnie dodaj
   `"model"` (domyślnie `eleven_v4`). Potem `tools/voice.py A` i `npm run render`.

Plan Free nie daje licencji komercyjnej. Przy publikacji wymaga „elevenlabs.io” albo „11.ai” w tytule.

## Nagranie własnego głosu

1. Przeczytaj na głos zdania z `scripts/A.json`, po kolei, z krótką pauzą między zdaniami. Wystarczy telefon;
   zapisz jako WAV (mono lub stereo).
2. `tools/.venv/Scripts/python tools/voice.py A nagranie.wav` podmienia głos i sam dopasowuje czasy napisów do
   nagrania (rozpoznawanie mowy Whisper).
3. `npm run render`

## Narzędzia

```sh
npm install
npm run studio                                   # podgląd z osią czasu
npm run render                                   # out/finfluencer-en.mp4
tools/.venv/Scripts/python tools/voice.py A      # głos tymczasowy + czasy napisów
../.venv/Scripts/python tools/thumbs.py          # miniatury kanałów i przykładu
uv run finfluencer video-data                    # liczby z wyników eksperymentu (w katalogu głównym)
```

Narzędzia głosowe instaluje się raz:
- `uv venv tools/.venv`;
- `uv pip install --python tools/.venv/Scripts/python.exe -r tools/requirements.txt`;
- model Kokoro (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) pobiera się z
  https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0) do `tools/voices/kokoro/`;
- polskie głosy Piper pobiera się z https://huggingface.co/rhasspy/piper-voices do `tools/voices/`.

Miniatury i fragment transkrypcji należą do autorów filmów; klip używa ich jako cytatu w komentarzu do badania.
Remotion jest darmowy dla osób prywatnych i firm do 3 osób; większa firma potrzebuje licencji.
