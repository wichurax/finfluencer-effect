"""Writing the files a later step, or a person with a spreadsheet, reads back."""

import os
import re
from pathlib import Path

import pandas as pd

# Free text that a spreadsheet would run as a formula if it started with one of these characters.
_FORMULA = re.compile(r"^('*)[=+\-@\t\r]")


def write_whole(path: Path, text: str) -> None:
    """Writes the file all at once, so a run killed midway leaves no half-written file that a rerun takes as done."""
    tmp = path.with_name(path.name + ".tmp")  # not matched by the steps' *.json globs
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def escape_formulas(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Puts an apostrophe before a leading =, +, -, @, tab or CR (and before an apostrophe already in front of one)."""
    frame = frame.copy()
    for c in columns:
        if c in frame:
            frame[c] = frame[c].map(lambda v: "'" + v if isinstance(v, str) and _FORMULA.match(v) else v)
    return frame


def unescape_formulas(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """The reverse of escape_formulas: takes one apostrophe off a text that has them in front of a formula character."""
    frame = frame.copy()
    for c in columns:
        if c in frame:
            frame[c] = frame[c].map(lambda v: v[1:] if isinstance(v, str) and v.startswith("'") and _FORMULA.match(v)
                                    else v)
    return frame
