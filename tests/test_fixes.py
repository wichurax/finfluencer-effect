"""Run with: python -m unittest discover tests"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from finfluencer import analyze, classify, files, labels, prices
from finfluencer.classify import codex_defaults


def events(n: int) -> pd.DataFrame:
    return pd.DataFrame({"sign": 1, "video_id": [f"v{i}" for i in range(n)], "day0": range(n),
                         "car_d0": 0.01, "car_pre": 0.0})


def series(start: str, end: str, ar: float) -> analyze.Series:
    """A stock trading every weekday from start to end, with the same abnormal return each session."""
    dates = np.arange(np.datetime64(start), np.datetime64(end), dtype="datetime64[D]")
    dates = dates[np.is_busday(dates)]
    a = np.full(len(dates), ar)
    cs = np.concatenate([[0.0], np.cumsum(a)])
    return analyze.Series(dates=dates, ar=a, cs=cs, csb=cs, abvol=np.full(len(dates), 0.1),
                          turnover=np.ones(len(dates)), nob=np.zeros(len(dates) + 1, dtype=int))


class AllNanPlacebo(unittest.TestCase):
    def test_group_and_momentum_return_counts_only(self):
        # Named test_* in analyze.py, so called through the module: a test runner would collect them.
        for fn, n in ((analyze.test_group, 6), (analyze.test_momentum, 30)):
            ev = events(n)
            null = {"car_d0": np.full((3, n), np.nan), "car_pre": np.full((3, n), np.nan)}
            res = fn(ev, pd.Series(True, index=ev.index), "car_d0", null)
            self.assertEqual(res, {"n_events": n, "n_videos": n})


class PlaceboHitRate(unittest.TestCase):
    def test_placebo_hit_rate_excludes_missing_returns(self):
        ev = events(6)
        nan = np.nan
        # Every return a draw has is positive; the missing ones are stocks without history on the date drawn.
        null = {"car_d0": np.array([[0.02, 0.01, 0.03, 0.02, 0.01, 0.02],
                                    [0.02, nan, 0.01, nan, nan, 0.03],
                                    [nan, nan, nan, nan, nan, 0.01]])}
        res = analyze.test_group(ev, pd.Series(True, index=ev.index), "car_d0", null)
        self.assertEqual(res["placebo_hit_rate"], 1.0)


class PlaceboPaths(unittest.TestCase):
    def run_paths(self, ser: analyze.Series, draws: int = 50) -> dict[str, np.ndarray]:
        ev = pd.DataFrame({"video_id": ["v0"], "symbol": ["AAA"], "sign": [1]})
        out = analyze.placebo_paths(ev, {"AAA": ser}, {"g": np.array([True])}, draws, np.random.default_rng(3))
        return out["g"]

    def test_placebo_paths_keep_unavailable_draws_nan(self):
        # History ends before the study window, so no random date in the window has a value.
        paths = self.run_paths(series("2023-01-02", "2023-06-30", 0.01))
        self.assertTrue(np.isnan(paths["car"]).all())
        self.assertTrue(np.isnan(paths["vol"]).all())

    def test_placebo_paths_average_only_the_draws_that_have_values(self):
        # History covers the first half of the window: draws there have the stock's path, the rest none.
        paths = self.run_paths(series("2024-09-01", "2025-10-01", 0.01))
        car, vol = paths["car"], paths["vol"]
        drawn = ~np.isnan(car).all(axis=1)
        self.assertTrue(drawn.any() and (~drawn).any())
        # 1% a session in the call's direction: -4% five sessions before, 0 at the close before day 0, +6% at day 5.
        expected = np.array([-0.04, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06])
        np.testing.assert_allclose(car[drawn], np.broadcast_to(expected, car[drawn].shape), atol=1e-12)
        np.testing.assert_allclose(vol[drawn], 0.1)
        self.assertTrue(np.isnan(car[~drawn]).all() and np.isnan(vol[~drawn]).all())


class TiedTurnover(unittest.TestCase):
    def test_tied_turnover_does_not_abort_event_building(self):
        self.assertIsNone(analyze._liquidity_terciles(pd.Series(np.full(30, 5.0))))
        thirds = analyze._liquidity_terciles(pd.Series(np.arange(30.0)))
        self.assertEqual(thirds.value_counts().to_dict(), {"low": 10, "mid": 10, "high": 10})
        # As build_events calls it, per market: one market's ties leave the other's terciles in place.
        ev = pd.DataFrame({"market": ["GPW"] * 30 + ["US"] * 30, "turnover": np.r_[np.full(30, 5.0), np.arange(30.0)]})
        liquidity = ev.groupby("market")["turnover"].transform(analyze._liquidity_terciles)
        self.assertTrue(liquidity[:30].isna().all())
        self.assertEqual((liquidity == "low").sum(), 10)


class PartialRefresh(unittest.TestCase):
    def test_partial_refresh_preserves_saved_history(self):
        dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
        saved_close = pd.DataFrame({"AAA": [1.0, 2, 3, 4, 5, 6], "BBB": 1.0, "CCC": 7.0, "GONE": 1.0}, index=dates)
        saved_volume = saved_close * 100
        # Yahoo answers for AAA with only its last three prices, for BBB in full (revised), not at all for CCC.
        close = pd.DataFrame({"AAA": [np.nan, np.nan, np.nan, 40.0, 50, 60], "BBB": 2.0, "NEW": 3.0}, index=dates)
        volume = close * 10
        out_close, out_volume, kept = prices._keep_saved(close, volume, saved_close, saved_volume,
                                                         {"AAA", "BBB", "CCC", "NEW"})
        self.assertEqual(sorted(kept), ["AAA", "CCC"])
        pd.testing.assert_series_equal(out_close["AAA"], saved_close["AAA"])
        pd.testing.assert_series_equal(out_volume["AAA"], saved_volume["AAA"])
        pd.testing.assert_series_equal(out_close["BBB"], close["BBB"])
        pd.testing.assert_series_equal(out_close["CCC"], saved_close["CCC"])
        self.assertEqual(sorted(out_close.columns), ["AAA", "BBB", "CCC", "NEW"])  # GONE is no longer labelled


class LabelWrites(unittest.TestCase):
    VIDEO = {"id": "abc", "channel": "meetkevin", "title": "t", "published_utc": "2026-01-02T15:00:00+00:00",
             "published_ts": 1767366000, "transcript": "x"}
    STOCKS = [{"company": "Nvidia", "yahoo_symbol": "NVDA", "asset_type": "stock", "stance": "bullish",
               "conviction": 2, "focus": "main", "evidence": "buy it"}]

    def test_failed_label_write_is_retried(self):
        real_write = Path.write_text

        def torn(path, text, *args, **kwargs):  # the disk fills up halfway through the record
            real_write(path, text[:20], *args, **kwargs)
            raise OSError("No space left on device")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.multiple(classify, DATA=Path(tmp), MENTIONS=Path(tmp) / "mentions",
                                    load_videos=lambda: [self.VIDEO]), \
                mock.patch("shutil.which", return_value="claude"), \
                mock.patch.object(classify, "_classify_cli", return_value=({"stocks": self.STOCKS}, "m")):
            record = Path(tmp) / "mentions" / "abc.json"
            with mock.patch.object(Path, "write_text", torn), self.assertRaises(OSError):
                classify.classify_all("cli", "m", "low", 1, None, None)
            self.assertFalse(record.exists())  # so the rerun does not take the video as done
            classify.classify_all("cli", "m", "low", 1, None, None)
            self.assertEqual(json.loads(record.read_text(encoding="utf-8"))["stocks"], self.STOCKS)
            self.assertEqual(list(record.parent.glob("*.tmp")), [])


class CodexDefaults(unittest.TestCase):
    def test_reads_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config.toml").write_text('model = "x"\nmodel_reasoning_effort = "high"\n')
            with mock.patch.dict(os.environ, {"CODEX_HOME": tmp}):
                self.assertEqual(codex_defaults(), ("x", "high"))

    def test_falls_back_to_home(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"HOME": tmp, "USERPROFILE": tmp}):
            os.environ.pop("CODEX_HOME", None)
            self.assertEqual(codex_defaults(), ("default", "default"))


class FormulaCells(unittest.TestCase):
    TITLES = ['=WEBSERVICE("http://x")', "+1", "-25% drop", "@sum", "\t=x", "'=already quoted", "plain", "'plain", ""]

    def assertNoFormula(self, frame: pd.DataFrame, columns: list[str]) -> None:
        for c in columns:
            self.assertFalse(any(isinstance(v, str) and v[:1] in "=+-@\t\r" and v for v in frame[c]), c)

    def test_round_trip_and_no_formula_cell(self):
        frame = pd.DataFrame({"title": self.TITLES, "company": self.TITLES, "yahoo_symbol": self.TITLES})
        escaped = files.escape_formulas(frame, labels.TEXT_COLUMNS)
        self.assertNoFormula(escaped, labels.TEXT_COLUMNS)
        self.assertEqual(files.unescape_formulas(escaped, labels.TEXT_COLUMNS).to_dict(), frame.to_dict())

    def test_events_csv_round_trip_with_missing_text(self):
        # As charts.py and video_data.py read events.csv back: missing text comes back as NaN.
        frame = pd.DataFrame({"title": self.TITLES, "company": self.TITLES, "evidence": [None, *self.TITLES[1:]],
                              "symbol": self.TITLES, "car_d0": 0.01})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            files.escape_formulas(frame, analyze.EVENT_TEXT).to_csv(path, index=False)
            raw = pd.read_csv(path, low_memory=False)
        self.assertNoFormula(raw, analyze.EVENT_TEXT)
        back = files.unescape_formulas(raw, analyze.EVENT_TEXT)
        self.assertEqual(back.fillna("").to_dict(), frame.fillna("").to_dict())

    def test_symbol_check_has_no_formula_cell(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prices, "PRICES", Path(tmp)), \
                mock.patch.object(prices, "_yahoo_name", return_value='=HYPERLINK("http://x")'):
            prices.verify_names({"AAA": {"=cmd|' /C calc'!A0", "Plain Inc"}})
            table = pd.read_csv(Path(tmp) / "symbol_check.csv")
        self.assertNoFormula(table, ["symbol", "yahoo_name", "labeller_names"])
        self.assertEqual(table.loc[0, "yahoo_name"], "'=HYPERLINK(\"http://x\")")


if __name__ == "__main__":
    unittest.main()
