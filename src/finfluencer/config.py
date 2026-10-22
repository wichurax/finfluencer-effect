"""Study settings: channels, study window, markets and paths."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Channel:
    key: str
    name: str
    handle: str
    country: str  # "US" or "PL"
    lang: str  # transcript language
    subscribers: int  # from yt-dlp on 2026-10-20, for the report only


CHANNELS = [
    # USA: the three biggest channels that regularly give opinions on named stocks.
    # Graham Stephan (5.2M) and Andrei Jikh (3.4M) are bigger but almost never name a stock.
    Channel("meetkevin", "Meet Kevin", "MeetKevin", "US", "en", 2_050_000),
    Channel("financialeducation", "Financial Education", "FinancialEducation", "US", "en", 953_000),
    Channel("tomnash", "Tom Nash", "TomNashTV", "US", "en", 699_000),
    # Poland: the biggest finance channels (Marcin Iwuć, Phil Konieczny, Kuba Midel) do not name
    # stocks; these are the three biggest that do. Next in line: Albert Rokicki (@AlbertRokicki, 22k).
    Channel("zawodinwestor", "Zawód Inwestor", "ZawodInwestor", "PL", "pl", 206_000),
    Channel("merytorycznie", "Merytorycznie o Finansach (Piotr Cymcyk)", "DNARynkow", "PL", "pl", 120_000),
    Channel("squaber", "Squaber", "Squaber", "PL", "pl", 44_500),
]

STUDY_START = date(2024, 10, 1)
# Leave room for the +3 trading day window and late price prints.
STUDY_END = date(2026, 10, 13)


@dataclass(frozen=True)
class Market:
    tz: str
    open: str
    close: str
    benchmark: str  # Yahoo symbol of the market proxy


MARKETS = {
    "US": Market("America/New_York", "09:30", "16:00", "SPY"),
    # Yahoo has no WIG index; the Beta ETF on WIG20TR is the closest daily proxy it carries.
    "GPW": Market("Europe/Warsaw", "09:00", "17:05", "ETFBW20TR.WA"),
}


def market_of(symbol: str) -> str | None:
    if symbol.endswith(".WA"):
        return "GPW"
    if "." in symbol or "=" in symbol or symbol.startswith("^"):
        return None  # other exchanges, currencies and indices are out of scope
    return "US"
