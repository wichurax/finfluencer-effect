"""Do the key results hold with GPT's labels? Same videos, labelled by Claude and by GPT.

Writes results/robustness_gpt.csv: per segment, group and window, the test on each label set.
"""

import numpy as np
import pandas as pd

from .agreement import CHECK
from .analyze import (ALL, CLEANEST, PRICES, QUIET, QUIET_NO_NEWS, RESULTS, build_events, build_series, groups,
                      placebo, test_group)

KEY = [ALL, CLEANEST, QUIET, QUIET_NO_NEWS]


def run(draws: int = 1000, seed: int = 13) -> pd.DataFrame:
    overlap = {p.stem for p in (CHECK / "gpt").glob("*.json")}
    close = pd.read_parquet(PRICES / "close.parquet")
    volume = pd.read_parquet(PRICES / "volume.parquet")
    series = build_series(close, volume)
    rows = []
    for labels, directory in (("claude", None), ("gpt", CHECK / "gpt")):
        kwargs = {"only_ids": overlap} if directory is None else {"mentions_dir": directory, "only_ids": overlap}
        events, _ = build_events(series, **kwargs)
        null = placebo(events, series, draws, np.random.default_rng(seed))
        for segment, name, mask in groups(events):
            if name not in KEY:
                continue
            for key in ("car_d0", "car_d0-3"):
                rows.append({"labels": labels, "segment": segment, "group": name, "measure": key,
                             **test_group(events, mask, key, null)})
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "robustness_gpt.csv", index=False)
    print(f"robustness on {len(overlap)} videos labelled by both models written", flush=True)
    return out
