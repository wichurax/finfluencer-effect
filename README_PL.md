# Czy youtuberzy giełdowi ruszają kursami akcji?

Kiedy duży youtuber od giełdy mówi „kupuj” albo „sprzedawaj”, czy kurs idzie za jego słowami? To repozytorium
sprawdza to na 2533 filmach z trzech największych kanałów o akcjach w USA i trzech w Polsce, opublikowanych
od października 2024 do października 2026 roku.

**Krótka odpowiedź:**
- **W USA:** kursy idą za opiniami, ale tylko wtedy, gdy są świeże wiadomości o spółce (np. wyniki kwartalne).
  To wiadomość rusza kursem, a youtuber o niej opowiada.
- **W Polsce:** kursy idą za opiniami także w spokojne dni, średnio o pół punktu procentowego. Najmocniej w małych
  spółkach.
- **W obu krajach:** efekt mieści się w jednej sesji i jest za mały, żeby na nim zarabiać, ale wyraźnie
  mierzalny.

- **Raport** z wykresami, metodą i wszystkimi wynikami: [Finfluencers vs Stock Prices](https://claude.ai/artifact/7pWWoxVyAwVcENWMcNSWmW)
  (po angielsku i po polsku, z przełącznikiem języka)
- **English**: [README.md](README.md)

## Słowniczek

- **Opinia:** to, co youtuber mówi o konkretnej spółce: pozytywnie (kupować, trzymać) albo negatywnie
  (sprzedawać, unikać). Opinie z transkrypcji wyciągał model AI.
- **Pierwsza sesja po filmie:** pierwsza sesja giełdowa, która kończy się po publikacji filmu. Jeśli film
  pojawił się w trakcie sesji, liczy się już ta sesja.
- **Ruch ponad rynek:** o ile spółka zmieniła się bardziej niż cały rynek. Rynek to w USA fundusz SPY, w
  Polsce fundusz na indeks WIG20TR (Yahoo nie ma indeksu WIG).
- **Punkt procentowy (pkt proc.):** różnica dwóch procentów. Spółka rośnie o 3,1%, rynek o 0,2%: ruch ponad rynek
  to 2,9 pkt proc.
- **W stronę opinii:** spadek po opinii negatywnej liczy się jako trafienie, tak samo jak wzrost po pozytywnej.
- **Losowe dni:** te same filmy przeniesione na przypadkowe daty z okresu badania, 2000 razy. Pokazują, ile
  „efektu” daje sam przypadek.
- **p:** jaka część losowań dała wynik co najmniej tak duży jak prawdziwy. Im mniejsze p, tym trudniej wynik
  wytłumaczyć przypadkiem. p = 0,06 znaczy, że tak duży wynik zdarza się przypadkiem w 6 losowaniach na 100.
- **Test bez newsów:** tylko opinie z filmów opublikowanych poza sesją, o spółkach, które w tygodniu przed
  filmem były spokojne (kurs zmienił się o mniej niż 3%, a obroty w trzech sesjach przed filmem były normalne), z filmów, w których tytule nie ma
  słów o wiadomościach (wyniki, raport, dywidenda, przejęcie...).

## Wyniki

Polska i USA są liczone zawsze osobno: amerykańscy youtuberzy i spółki z USA, polscy youtuberzy i spółki z GPW.
To zbyt różne rynki, żeby je łączyć. Liczby to średni ruch ponad rynek w stronę opinii, ponad to, co dają losowe
dni.

| | USA | Polska |
|---|---|---|
| Liczba opinii | 2240 (z 714 filmów) | 1197 (z 320 filmów) |
| Pierwsza sesja po filmie | **+0,81 pkt proc.**, p < 0,001 | **+0,36 pkt proc.**, p < 0,001 |
| Przy wynikach kwartalnych (±3 sesje) | +1,78 pkt proc. (387 opinii) | za mało opinii (28) |
| W pozostałe dni | +0,61 pkt proc. | +0,22 pkt proc. |
| **Test bez newsów** | **+0,25 pkt proc., p = 0,06: w granicach przypadku** | **+0,49 pkt proc., p = 0,001** |
| Opinie o spółkach z najmniejszymi obrotami (trzecia część opinii) | +1,38 pkt proc. | +0,58 pkt proc. |
| Opinie o spółkach z największymi obrotami (trzecia część opinii) | +0,31 pkt proc. | +0,25 pkt proc. |
| Trzy kolejne sesje | −0,03 pkt proc., p = 0,82 | +0,18 pkt proc., p = 0,13 |
| Pięć sesji *przed* filmem | +0,40 pkt proc., p = 0,035 | +0,89 pkt proc., p < 0,001 |

Co z tego wynika:

- **USA.** Kursy idą za opiniami, ale efekt skupia się w dniach z wiadomościami. Przy wynikach kwartalnych jest
  prawie trzy razy większy niż w pozostałe dni, a w teście bez newsów mieści się w granicach przypadku.
  Ten test wykryłby jednak dopiero efekt rzędu 0,4 pkt proc., więc mniejszego nie da się wykluczyć.
- **Polska.** Efekt zostaje także w spokojne dni: około pół punktu procentowego. W spółkach z najmniejszymi
  obrotami jest ponad dwa razy większy niż w tych z największymi.
- **Efekt nie trwa.** Trzy kolejne sesje nie dokładają nic, co dałoby się zmierzyć.
- **To korelacja, nie dowód.** W Polsce kurs rusza się w stronę opinii już w tygodniu *przed* filmem
  (+0,89 pkt proc.). Youtuberzy często mówią o spółkach, które już są w ruchu.

## Korekty

**26 października 2026.** Przegląd kodu znalazł trzy błędy. Liczby powyżej są poprawione, żaden wniosek się nie
zmienia: wyniki dla USA przesunęły się najwyżej o 0,02 pkt proc., p w teście bez newsów z 0,07 na 0,06, wyniki
dla Polski się nie zmieniły.

- W pięć dni, w które giełda w Nowym Jorku zamyka się o 13:00 (dzień po Święcie Dziękczynienia, Wigilia,
  3 lipca), film opublikowany po zamknięciu liczył się do tej sesji; teraz do następnej. 23 opinie z 7 filmów.
- Filtr tytułów w teście bez newsów znał polskie słowo „dywidenda”, ale nie angielskie „dividend”; tytuły
  amerykańskich filmów o dywidendzie liczą się teraz jako newsy.
- Test z betą liczył dni bez dość długiej historii do oszacowania bety jako zerowy zwrot; teraz je pomija.

Opublikowany klip pokazuje liczby z pierwszej wersji (+0,82 pkt proc., 2238 opinii).

## Jak powtórzyć wyniki

Wystarczy [uv](https://docs.astral.sh/uv/) i około 40 minut, z czego większość zajmuje pobieranie dat wyników
kwartalnych. Etykiety są w folderze [labels/](labels/), więc nie potrzebujesz ani transkrypcji, ani modelu AI.

```sh
git clone https://github.com/wichurax/finfluencer-effect && cd finfluencer-effect
uv run finfluencer load-labels   # odtwarza data/ z publicznych etykiet (kilka sekund)
uv run finfluencer prices        # dzienne kursy z Yahoo Finance (ok. 4 minut)
uv run finfluencer earnings      # daty wyników kwartalnych do testu dni z wiadomościami (ok. 30 minut)
uv run finfluencer analyze       # wszystkie testy, wykresy, results/report.md i results/index.html (ok. 2 minut)
```

Przy tych samych danych `analyze` daje dokładnie liczby z tabeli, bo losowe dni są losowane ze stałym ziarnem
(`--seed 7`). Yahoo poprawia jednak historyczne kursy (dywidendy, splity, korekty) i swój kalendarz wyników.
Opublikowane wyniki liczyłem na danych pobranych 21 października 2026. Próbne uruchomienie od zera dzień później:
- wyniki z USA wyszły identyczne;
- polskie przesunęły się o mniej niż 0,01 pkt proc. (wszystkie opinie: +0,364 → +0,366), bo Yahoo poprawiło kilka
  kursów z GPW;
- 37 polskich opinii straciło daty wyników kwartalnych, co zmieniło tylko grupy wyznaczane tymi datami.

Na tych samych danych działają jeszcze dwa sprawdziany:

```sh
uv run finfluencer agreement --compare-only   # jak często Claude i GPT dały tę samą etykietę
uv run finfluencer robustness                 # kluczowe testy na etykietach Claude i na etykietach GPT
```

## Całe badanie od zera

Jeśli chcesz sprawdzić też samo etykietowanie albo rozszerzyć badanie (inne kanały, dłuższy okres), uruchom
wszystko od początku:

```sh
uv run finfluencer videos                   # metadane filmów i transkrypcje z YouTube
uv run finfluencer classify --backend cli   # model AI ocenia każdy film
uv run finfluencer prices
uv run finfluencer earnings
uv run finfluencer analyze
```

- **`videos` trwa długo.** To około 3 sekund na film, a YouTube przy masowym pobieraniu napisów zaczyna
  blokować: licz się z wieloma godzinami. Każdy krok zapisuje postęp i po przerwaniu wznawia pracę od miejsca,
  w którym skończył.
- **`classify` nie da identycznych etykiet.** Modele językowe nie są deterministyczne: ta sama transkrypcja może
  dostać nieco inne etykiety. Dlatego publikuję etykiety, na których liczyłem wyniki.
- **Dostęp do modelu.** `classify` łączy się z modelem na jeden z trzech sposobów:

| `--backend` | Czego używa | Uwagi |
|---|---|---|
| `api` (domyślnie) | klucza `ANTHROPIC_API_KEY` | Opus 5.5 to kilka centów za film; `--model claude-haiku-5-5` jest ok. 40 razy tańszy |
| `cli` | zalogowanego `claude` CLI (subskrypcja) | zużywa limit 5-godzinnego okna |
| `codex` | zalogowanego Codex CLI (ChatGPT) | zapas, gdy skończy się limit Claude |

- **Przydatne opcje:**
  - `--limit 20` ocenia próbne 20 filmów;
  - `--start-at 16:12` czeka do tej godziny, np. do odnowienia limitu;
  - `--shard 0/2` i `--shard 1/2` dzielą filmy losowo na dwie połowy, żeby dwa modele pracowały równolegle.

Opublikowane etykiety pochodzą od Claude Haiku 5.5 (1752 filmy), Claude Opus 5.5 (493) i GPT-6.1 przez Codex
(284). Który model ocenił który film, zapisane jest w `labels/videos.csv`.

## Czego nie ma w repozytorium i dlaczego

- **Transkrypcji i cytatów, które model z nich wybrał.** To słowa youtuberów. `videos` pobiera transkrypcje,
  a analiza cytatów nie używa.
- **Kursów.** Regulamin Yahoo Finance nie pozwala ich rozpowszechniać; `prices` je pobiera.
- **Miniatur i gotowego klipu.** Zawierają materiały kanałów. Kod klipu jest w folderze [video/](video/).

## Metoda w skrócie

- **Analiza zdarzeń** (ang. *event study*): dla każdej opinii liczę ruch spółki ponad rynek w pierwszej sesji po
  filmie i w kilku kolejnych. Przykład: po pozytywnej opinii kanału Financial Education o e.l.f. Beauty spółka
  wzrosła w pierwszej sesji o 3,1%, a rynek o 0,2%. Ruch ponad rynek: +2,9 pkt proc. w stronę opinii.
- **Porównanie z przypadkiem.** Każdy film przenoszę razem ze wszystkimi swoimi opiniami na losowy dzień z okresu
  badania, 2000 razy. Prawdziwy wynik porównuję z tym, co dają losowe dni.
- **Wiele testów naraz.** Przy tylu grupach część wyników wyszłaby „istotna” przez przypadek. Wartości q
  w raporcie to p poprawione na liczbę testów (metoda Benjaminiego-Hochberga).
- **Najmniejszy wykrywalny efekt.** Dla każdego testu raport podaje najmniejszy efekt, który dana próba wykryłaby
  w 80% przypadków. Dzięki temu „brak efektu” da się odróżnić od „za mało danych”.
- **Dodatkowe sprawdziany:**
  - ruch w pięciu sesjach przed filmem;
  - obroty;
  - model uwzględniający betę spółki;
  - tylko filmy spoza sesji;
  - tylko główny temat filmu;
  - regresja z liczbą wyświetleń.

## Ograniczenia

- **Korelacja, nie przyczyna.** Youtuberzy mówią o spółkach, które już są w ruchu. W Polsce kurs przesuwa się
  w stronę opinii o 0,89 pkt proc. jeszcze w tygodniu przed filmem.
- **Etykiety wystawił model AI.** Na filmach ocenionych przez Claude i GPT oba modele wskazują te same spółki
  w około 60% przypadków. Gdy oba wskażą tę samą spółkę, dają ten sam kierunek opinii w 87% przypadków dla
  filmów z USA i w 85% dla polskich. Przeciwne opinie zdarzają się rzadziej niż raz na sto.
- **Kluczowe testy na obu zestawach etykiet.** Na 243 filmach ocenionych przez oba modele wyniki są zbliżone
  (wszystkie opinie w USA: +0,70 pkt proc. na etykietach Claude, +0,83 na etykietach GPT; w Polsce +0,30
  i +0,45). Ta próba jest jednak za mała, żeby osobno sprawdzić na niej polski test bez newsów.
- **Zakres.**
  - Po trzy kanały na kraj i dwa lata.
  - Kursy dzienne, więc nie widać, co dzieje się w trakcie sesji.

## Znalazłeś lukę w rozumowaniu?

Po to kod i etykiety są publiczne. Otwórz zgłoszenie (Issue) i napisz w nim:
- co Twoim zdaniem jest źle;
- gdzie: plik, test albo grupa;
- jeśli się da, komendę, która to pokazuje.

## Co jest gdzie

- `src/finfluencer/config.py`: kanały, okres badania, rynki i indeksy odniesienia.
- `src/finfluencer/classify.py`: polecenie dla modelu (prompt) i format etykiet.
- `src/finfluencer/analyze.py`: zdarzenia, porównanie z losowymi dniami, wszystkie grupy testów.
- `labels/videos.csv`: wszystkie filmy (same metadane) i model, który ocenił każdy z nich.
- `labels/labels.csv`: każda spółka wskazana w filmie, w osobnym wierszu. Zawiera nazwę, ticker, kierunek i siłę
  opinii oraz to, czy spółka była głównym tematem filmu.
  W obu plikach tytuł, nazwa lub ticker zaczynający się od `=`, `+`, `-` albo `@` ma na początku apostrof,
  żeby arkusz nie wykonał go jako formuły; `labels.load()` go zdejmuje.
- `symbol_fixes.json`: ręczne poprawki tickerów, które model podał błędnie, np. `{"DGN.WA": "DIG.WA"}`; pusty
  napis usuwa ticker.
- `data/` (poza gitem): to, co pobierają i tworzą kolejne kroki.
- `results/` (poza gitem): testy, wykresy, `report.md` i `index.html`.
- `video/`: klip zrobiony w [Remotion](https://www.remotion.dev/).

## Licencja

- **Kod:** [MIT](LICENSE).
- **Etykiety w folderze `labels/`:** [CC BY 4.0](labels/LICENSE.md). Możesz z nich korzystać w dowolnym celu,
  podając źródło.
- **Tytuły filmów i same filmy** należą do kanałów.
