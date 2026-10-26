"""Run with: python -m unittest discover tests"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from finfluencer import analyze, labels
from finfluencer.classify import codex_defaults


def events(n: int) -> pd.DataFrame:
    return pd.DataFrame({"sign": 1, "video_id": [f"v{i}" for i in range(n)], "day0": range(n),
                         "car_d0": 0.01, "car_pre": 0.0})


class AllNanPlacebo(unittest.TestCase):
    def test_group_and_momentum_return_counts_only(self):
        # Named test_* in analyze.py, so called through the module: a test runner would collect them.
        for fn, n in ((analyze.test_group, 6), (analyze.test_momentum, 30)):
            ev = events(n)
            null = {"car_d0": np.full((3, n), np.nan), "car_pre": np.full((3, n), np.nan)}
            res = fn(ev, pd.Series(True, index=ev.index), "car_d0", null)
            self.assertEqual(res, {"n_events": n, "n_videos": n})


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

    def test_round_trip_and_no_formula_cell(self):
        frame = pd.DataFrame({"title": self.TITLES, "company": self.TITLES, "yahoo_symbol": self.TITLES})
        escaped = labels._escape(frame)
        for c in labels.TEXT_COLUMNS:
            self.assertFalse(any(v[:1] in "=+-@\t\r" and v for v in escaped[c]))
        self.assertEqual(labels._unescape(escaped).to_dict(), frame.to_dict())


if __name__ == "__main__":
    unittest.main()
