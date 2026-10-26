# Do finance YouTubers move stock prices?

When a big finance YouTuber says "buy" or "sell", does the stock follow? This repository tests it on
2,533 videos from the three biggest stock-picking channels in the U.S. and in Poland, published between
October 2024 and October 2026. An AI model read every transcript and labelled each call as bullish or
bearish. Each stock was then compared with its market on the first trading session after the video, and
the result was set against the same videos moved to 2,000 random dates.

- **Report** with charts, method and all results: [Finfluencers vs Stock Prices](https://claude.ai/artifact/7pWWoxVyAwVcENWMcNSWmW)
- **Po polsku**: [README_PL.md](README_PL.md)

The two countries are always tested separately: U.S. channels against U.S. stocks, Polish channels against
stocks listed in Warsaw. The markets are too different in size to pool.

## Results in brief

All numbers are the stock's move minus the market's, in percentage points (pp), in the direction of the
call (a bearish call followed by a drop counts as a hit), averaged over all calls and compared with what
random dates give.

| | U.S. channels, U.S. stocks | Polish channels, Warsaw stocks |
|---|---|---|
| Calls analysed | 2,240 (in 714 videos) | 1,197 (in 320 videos) |
| First session after the video | **+0.81 pp**, p < 0.001 | **+0.36 pp**, p < 0.001 |
| Near quarterly earnings (±3 sessions) | +1.78 pp (387 calls) | too few calls (28) |
| Other days | +0.61 pp | +0.22 pp |
| **No-news test** | **+0.25 pp, p = 0.06: within chance** | **+0.49 pp, p = 0.001** |
| Calls on the least-traded stocks (a third of the calls) | +1.38 pp | +0.58 pp |
| Calls on the most-traded stocks (a third of the calls) | +0.31 pp | +0.25 pp |
| The next three sessions | −0.03 pp, p = 0.82 | +0.18 pp, p = 0.13 |
| The five sessions *before* the video | +0.40 pp, p = 0.035 | +0.89 pp, p < 0.001 |

In plain words:

- **U.S.:** stocks do move with the call, but the move sits on news days. Close to earnings it is three times
  larger than on other days, and in the no-news test it falls within chance. The news moves the stock; the
  YouTuber talks about it. The no-news test could only detect effects of about 0.4 pp or more, so a smaller
  one is not ruled out.
- **Poland:** the move stays on quiet days, about half a point. Across all calls it is about twice as large in
  the least-traded companies as in the most-traded ones.
- **Neither** effect lasts: the three sessions that follow add nothing measurable.
- **Too small to trade on, but big enough to measure.** And it is a correlation, not proof: in Poland, prices
  already moved +0.89 pp in the call's direction during the week *before* the video.

The **no-news test** keeps only calls from videos published outside trading hours, about a stock that moved
less than 3% in the week before and traded at normal volume in the three sessions before, from a video whose title names no news (earnings,
results, dividend, deal, ...).

## Corrections

**26 October 2026.** A review of the code found three faults; the numbers above are corrected, and no conclusion
changes. U.S. numbers moved by at most 0.02 pp, the no-news test's p from 0.07 to 0.06; Polish ones did not move.

- On the five days the New York exchange closes at 1:00 p.m. (the day after Thanksgiving, Christmas Eve, the
  3rd of July), a video after the close counted as published during that day's session; it is now the next
  session's. 23 calls in 7 videos.
- The no-news test's title filter knew the Polish word for dividend but not the English one; U.S. titles about a
  dividend now count as news.
- The beta-adjusted check counted days without enough history for a beta as a zero return; they are now left out.

The published clip shows the numbers as first published (+0.82 pp, 2,238 calls).

## Reproduce the results

You need [uv](https://docs.astral.sh/uv/) and about 40 minutes, most of it spent on the earnings dates. The
labels are in [labels/](labels/), so you need neither the transcripts nor an AI model.

```sh
git clone https://github.com/wichurax/finfluencer-effect && cd finfluencer-effect
uv run finfluencer load-labels   # data/ from the public labels (seconds)
uv run finfluencer prices        # daily prices from Yahoo Finance (about 4 minutes)
uv run finfluencer earnings      # earnings dates, for the news-day test (about 30 minutes)
uv run finfluencer analyze       # all tests, charts, results/report.md and results/index.html (about 2 minutes)
```

With the same prices, `analyze` gives exactly the numbers above, because the random dates are drawn with a
fixed seed (`--seed 7`). But Yahoo revises historical prices (dividends, splits, corrections) and its earnings
calendar. The published results used data downloaded on 21 October 2026. A test run from scratch a day later:
- the U.S. results came out identical;
- the Polish ones moved by less than 0.01 pp (all calls: +0.364 → +0.366), as Yahoo had revised a few Warsaw prices;
- 37 Polish calls had lost their earnings dates, which moved only the groups defined by those dates.

Two more checks run on the same data:

```sh
uv run finfluencer agreement --compare-only   # how often Claude and GPT gave the same label
uv run finfluencer robustness                 # the key tests on Claude's and on GPT's labels of the same videos
```

## The full study, from YouTube

To check the labelling too, or to extend the study (other channels, a longer period), run it from scratch:

```sh
uv run finfluencer videos                   # metadata and transcripts from YouTube
uv run finfluencer classify --backend cli   # the AI labels each video
uv run finfluencer prices
uv run finfluencer earnings
uv run finfluencer analyze
```

- **`videos` is slow.** It takes about 3 seconds per video, and YouTube throttles bulk caption downloads: plan
  for many hours. Every step saves what it has done and resumes where it stopped.
- **`classify` will not give exactly the same labels.** Language models are not deterministic, so the same
  transcript can get slightly different labels. That is why the labels used here are published.
- **Model source.** `classify` reaches the model in one of three ways:

| `--backend` | Uses | Notes |
|---|---|---|
| `api` (default) | an `ANTHROPIC_API_KEY` | Opus 5.5 costs a few cents per video; `--model claude-haiku-5-5` is about 40× cheaper |
| `cli` | the logged-in `claude` CLI (subscription) | counts against the 5-hour usage window |
| `codex` | the logged-in Codex CLI (ChatGPT) | a fallback when Claude's limit runs out |

- **Options:**
  - `--limit 20` labels a trial set of 20 videos;
  - `--start-at 16:12` waits until that time, for example a limit reset;
  - `--shard 0/2` and `--shard 1/2` split the videos at random between two models running side by side.

The published labels came from Claude Haiku 5.5 (1,752 videos), Claude Opus 5.5 (493) and GPT-6.1 through
Codex (284). Each video's model is recorded in `labels/videos.csv`.

## What is not here, and why

- **Transcripts and the models' quotes from them.** They are the YouTubers' words. `videos` downloads the
  transcripts; the analysis does not use the quotes.
- **Prices.** Yahoo Finance's terms do not allow redistributing them; `prices` downloads them.
- **Thumbnails and the rendered clip.** They contain the channels' material. The clip's source code is in
  [video/](video/), with a README in Polish.

## Method in brief

- **First session after the video.** The first trading session that closes after the video is published. A video
  published during a session counts from that same session.
- **Move beyond the market.** The stock's return minus the market's: SPY for the U.S., and for Warsaw an ETF
  on the WIG20TR index (Yahoo has no WIG index). Example: on the first session after a bullish Financial
  Education video, e.l.f. Beauty rose 3.1% while the market rose 0.2%, so the move beyond the market was
  +2.9 pp.
- **Random dates.** Each video is moved, with all its calls, to a random date in the study window,
  2,000 times. The p-value is the share of draws at least as extreme as the real result.
- **Many tests.** The q-values in the report correct for testing many groups at once (Benjamini-Hochberg).
- **Minimum detectable effect.** For every test, the report gives the smallest effect the sample would detect
  80% of the time, so "no effect" can be told apart from "too little data".
- **Other checks:**
  - the move in the five sessions before the video;
  - trading volume;
  - a model with each stock's beta;
  - only videos published outside trading hours;
  - only the video's main topic;
  - a regression on view counts.

## Limitations

- **Correlation, not causation.** YouTubers talk about stocks that are already moving. In Poland, prices move
  +0.89 pp in the call's direction during the week before the video.
- **The labels come from AI models.** On the videos labelled by both Claude and GPT, the two models name the
  same stock about 60% of the time. When both name it, they give the same direction 87% of the time for U.S.
  videos and 85% for Polish ones. Opposite calls are under 1%.
- **The key tests on both label sets.** On the 243 videos labelled by both models, the estimates are close
  (all U.S. calls: +0.70 pp on Claude's labels, +0.83 pp on GPT's; Poland: +0.30 and +0.45 pp). That subsample
  is too small to test the Polish no-news result on its own.
- **Scope.** Three channels per country, two years, daily prices: the effect within a session is not visible.

## Found a hole in the reasoning?

That is why the code and labels are public. Open an issue with what you think is wrong, where (a file, a test,
a group), and if you can, a command that shows it.

## What is where

- `src/finfluencer/config.py`: channels, study window, markets and benchmarks.
- `src/finfluencer/classify.py`: the prompt and the label format.
- `src/finfluencer/analyze.py`: the events, the random-date baseline, every test group.
- `labels/videos.csv`: every video (metadata only) and which model labelled it.
- `labels/labels.csv`: one row per stock named in a video: company, ticker, direction, strength, main topic or not.
- `symbol_fixes.json`: hand corrections of tickers the model got wrong, for example `{"DGN.WA": "DIG.WA"}`;
  an empty string removes one.
- `data/` (not in git): what each step downloads or produces.
- `results/` (not in git): tests, charts, `report.md` and `index.html`.
- `video/`: the clip, made with [Remotion](https://www.remotion.dev/).

## License

- **Code:** [MIT](LICENSE).
- **Labels in `labels/`:** [CC BY 4.0](labels/LICENSE.md).
- **Video titles and the videos themselves** belong to their channels.
