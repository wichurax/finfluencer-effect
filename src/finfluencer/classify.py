"""Reads each transcript with Claude and lists the stocks the speaker is bullish or bearish on.

One JSON file per video in data/mentions/. Failed videos get no file, so a rerun retries them.
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path

from .config import CHANNELS, DATA
from .videos import load_videos

MENTIONS = DATA / "mentions"

SYSTEM = """You label what a finance YouTuber says about individual stocks, for a study of whether their opinions are followed by price moves.

You get the title and the speech-recognition transcript (English or Polish) of one video. List every company whose stock the speaker gives a view on, and for each:
- company: the company name.
- yahoo_symbol: its Yahoo Finance symbol. US listings as they are (NVDA, BRK-B, GOOGL). Warsaw Stock Exchange with ".WA" (PKN.WA, CDR.WA, XTB.WA, DNP.WA). A foreign company with a US listing or ADR gets the US symbol (TSM, ASML, NVO, BABA). Other exchanges with Yahoo's suffix (.DE, .L, .PA, .AS, .TO). Use "" if you cannot tell which company is meant.
- asset_type: stock, etf, index, crypto or other. Funds, indices, commodities and coins are not stocks.
- stance: the speaker's own view of where the stock price goes from here.
  bullish: buying, adding, holding with conviction, calls it undervalued or a buy, expects it to rise.
  bearish: selling, trimming, shorting, avoiding, calls it overvalued, expects it to fall.
  neutral: reports news, earnings or price moves, or explains a business, without taking a side; or the view is balanced.
- conviction: 1 weak or hedged, 2 clear, 3 emphatic ("my biggest position", "I'm backing up the truck", "get out now").
- focus: main if the stock is a main subject of the video (named in the title or given its own segment), secondary if it comes up in passing or in a list.
- evidence: a short quote (at most 25 words) from the transcript, in its original language, that shows the stance.

Rules:
- Label the host's own opinion. Quoted analysts, guests and viewer questions count only when the host endorses the view.
- A stock that is only named (a list of holdings, an example, an ad read) is neutral; leave it out if the mention carries no information.
- Speech recognition misspells names ("pallet here" for Palantir, "and video" for Nvidia). Infer the company when the context makes it clear; otherwise leave it out.
- One entry per company. If the view changes during the video, use the view the speaker ends with.
- If the video gives no view on any stock, return an empty list."""

SCHEMA = {
    "type": "object",
    "properties": {
        "stocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "yahoo_symbol": {"type": "string"},
                    "asset_type": {"type": "string", "enum": ["stock", "etf", "index", "crypto", "other"]},
                    "stance": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                    "conviction": {"type": "integer", "enum": [1, 2, 3]},
                    "focus": {"type": "string", "enum": ["main", "secondary"]},
                    "evidence": {"type": "string"},
                },
                "required": ["company", "yahoo_symbol", "asset_type", "stance", "conviction", "focus", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["stocks"],
    "additionalProperties": False,
}

# Models that take the server-side refusal fallback; Haiku has none.
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class ClassifyError(Exception):
    pass


class UsageLimitReached(Exception):
    pass


def _user_text(video: dict, channel_name: str) -> str:
    return (
        f"Channel: {channel_name}\n"
        f"Published: {video['published_utc']}\n"
        f"Title: {video['title']}\n\n"
        f"Transcript:\n{video['transcript']}"
    )


def _classify_api(client, model: str, effort: str, text: str) -> tuple[dict, str]:
    import anthropic

    kwargs = dict(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": text}],
    )
    try:
        if model in FALLBACK_MODELS:
            response = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
            )
        else:
            response = client.messages.create(**kwargs)
    except anthropic.BadRequestError as e:
        raise ClassifyError(f"bad request: {e.message}") from e
    except anthropic.RateLimitError as e:
        raise UsageLimitReached(str(e)) from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        raise ClassifyError(f"API error: {e}") from e

    if response.stop_reason in ("refusal", "max_tokens"):
        raise ClassifyError(f"stop_reason {response.stop_reason}")
    text_out = next(b.text for b in response.content if b.type == "text")
    return json.loads(text_out), response.model


def _classify_cli(claude: str, model: str, effort: str, text: str) -> tuple[dict, str]:
    cmd = [
        claude, "-p",
        "--model", model,
        "--effort", effort,
        "--tools", "",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--output-format", "json",
        "--system-prompt", SYSTEM,
        "--json-schema", json.dumps(SCHEMA),
    ]
    # Keeps the user's CLAUDE.md files (personal instructions) out of the labeller's context.
    env = {**os.environ, "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"}
    proc = subprocess.run(
        cmd, input=text, capture_output=True, text=True, encoding="utf-8", env=env, timeout=900
    )
    lines = [line for line in proc.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise ClassifyError(f"no JSON from claude CLI: {(proc.stderr or proc.stdout)[-300:]}")
    out = json.loads(lines[-1])
    if out.get("is_error") or out.get("structured_output") is None:
        result = str(out.get("result"))
        if "limit" in result.lower():
            raise UsageLimitReached(result)
        raise ClassifyError(f"claude CLI: {result[:300]}")
    # modelUsage also lists the small model the CLI uses for its own housekeeping, so the label is
    # attributed to the model that was asked for.
    return out["structured_output"], model


def _classify_codex(codex: str, model: str | None, text: str) -> tuple[dict, str]:
    """GPT through the Codex CLI, for when the Claude subscription window runs out."""
    with tempfile.TemporaryDirectory() as tmp:
        schema, answer = Path(tmp) / "schema.json", Path(tmp) / "answer.json"
        schema.write_text(json.dumps(SCHEMA), encoding="utf-8")
        workdir = Path(tmp) / "empty"  # no AGENTS.md or repo for the agent to pick up
        workdir.mkdir()
        # The transcript is the internet's text, and the labels are published: like the Claude CLI
        # above, the model gets no tools. Read-only alone would still let a transcript with planted
        # instructions have it read a token on this machine into a label. The user's config (its MCP
        # servers) and rules stay out too; its model and effort are passed on, as the label names them.
        default_model, effort = codex_defaults()
        cmd = [codex, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
               "-s", "read-only", "-C", str(workdir), "--output-schema", str(schema), "-o", str(answer),
               "-c", 'web_search="disabled"', *[arg for feature in CODEX_OFF for arg in ("--disable", feature)]]
        if (model or default_model) != "default":
            cmd += ["-m", model or default_model]
        if effort != "default":
            cmd += ["-c", f'model_reasoning_effort="{effort}"']
        cmd.append("-")
        proc = subprocess.run(cmd, input=f"{SYSTEM}\n\n{text}", capture_output=True, text=True,
                              encoding="utf-8", timeout=900)
        if proc.returncode != 0 or not answer.exists():
            message = (proc.stderr or proc.stdout)[-400:]
            if "limit" in message.lower():
                raise UsageLimitReached(message)
            raise ClassifyError(f"codex: {message}")
        return json.loads(answer.read_text(encoding="utf-8")), f"codex:{model or default_model} ({effort})"


#: Codex's tools, off for the labeller: it reads a transcript and answers in JSON, nothing more.
CODEX_OFF = ["shell_tool", "unified_exec", "view_image", "image_generation", "multi_agent", "apps",
             "plugins", "browser_use", "computer_use", "hooks"]


def codex_defaults() -> tuple[str, str]:
    """Model and reasoning effort Codex uses when none is passed, from ~/.codex/config.toml."""
    import tomllib

    path = Path.home() / ".codex" / "config.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return config.get("model", "default"), config.get("model_reasoning_effort", "default")


def _find_codex() -> str | None:
    default = Path.home() / "AppData/Local/Programs/OpenAI/Codex/bin/codex.exe"
    return shutil.which("codex") or (str(default) if default.exists() else None)


def _round_robin(videos: list[dict]) -> list[dict]:
    """Newest first within each channel, channels interleaved, so a partial run stays balanced."""
    by_channel: dict[str, list[dict]] = {}
    for v in sorted(videos, key=lambda v: v["published_ts"] or 0, reverse=True):
        by_channel.setdefault(v["channel"], []).append(v)
    return [v for group in zip_longest(*by_channel.values()) for v in group if v]


def in_shard(video_id: str, shard: str | None) -> bool:
    """shard "i/n" keeps the videos whose id hashes to i mod n, so two labellers split every channel at random."""
    if not shard:
        return True
    i, n = (int(x) for x in shard.split("/"))
    return zlib.crc32(video_id.encode()) % n == i


def classify_all(backend: str, model: str, effort: str, workers: int,
                 limit: int | None, channels: list[str] | None, shard: str | None = None) -> None:
    keys = {c.key for c in CHANNELS}
    todo = [
        v for v in load_videos()
        if v.get("transcript") and v["channel"] in keys
        and (not channels or v["channel"] in channels)
        and in_shard(v["id"], shard)
        and not (MENTIONS / f"{v['id']}.json").exists()
    ]
    todo = _round_robin(todo)[:limit]
    label_videos(todo, backend, model, effort, workers, MENTIONS)


def label_videos(todo: list[dict], backend: str, model: str, effort: str, workers: int,
                 out_dir: Path) -> None:
    """Labels each video and writes out_dir/<id>.json; stops cleanly when the usage limit is spent."""
    out_dir.mkdir(parents=True, exist_ok=True)
    names = {c.key: c.name for c in CHANNELS}
    shown = ("Codex's default GPT model" if backend == "codex" and (model == "default" or model.startswith("claude"))
             else model)
    print(f"{len(todo)} videos to classify with {shown} via {backend}", flush=True)
    if not todo:
        return

    if backend == "api":
        import anthropic
        client = anthropic.Anthropic(max_retries=5)
        run = lambda text: _classify_api(client, model, effort, text)  # noqa: E731
    elif backend == "cli":
        claude = shutil.which("claude")
        if not claude:
            raise SystemExit("claude CLI not found on PATH")
        run = lambda text: _classify_cli(claude, model, effort, text)  # noqa: E731
    else:
        codex = _find_codex()
        if not codex:
            raise SystemExit("codex CLI not found")
        gpt_model = None if model == "default" or model.startswith("claude") else model
        run = lambda text: _classify_codex(codex, gpt_model, text)  # noqa: E731

    stop = threading.Event()
    error_log = DATA / "logs" / "classify-errors.log"
    error_log.parent.mkdir(parents=True, exist_ok=True)
    log_lock = threading.Lock()

    def log_error(video_id: str, error: Exception) -> None:
        with log_lock, error_log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {video_id} {type(error).__name__}: {error}\n")

    def run_with_retry(video: dict) -> tuple[dict, str]:
        text = _user_text(video, names[video["channel"]])
        for wait in (60, 300, None):
            try:
                return run(text)
            except UsageLimitReached as e:
                # Short rate limits pass; a subscription window that is spent does not.
                log_error(video["id"], e)
                if wait is None or stop.is_set():
                    raise
                time.sleep(wait)
        raise AssertionError("unreachable")

    def work(video: dict) -> str:
        if stop.is_set():
            return "skipped"
        labels, used_model = run_with_retry(video)
        record = {
            "video_id": video["id"],
            "channel": video["channel"],
            "model": used_model,
            "backend": backend,
            "effort": codex_defaults()[1] if backend == "codex" else effort,
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "stocks": labels["stocks"],
        }
        (out_dir / f"{video['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
        return f"{len(labels['stocks'])} stocks"

    done = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, v): v for v in todo}
        for future in as_completed(futures):
            video = futures[future]
            try:
                if future.result() == "skipped":
                    continue
                done += 1
                if done % 10 == 0:
                    print(f"{done}/{len(todo)} classified", flush=True)
            except UsageLimitReached as e:
                if not stop.is_set():
                    print(f"usage limit reached, stopping: {str(e)[:300]}", flush=True)
                stop.set()
            except (ClassifyError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                failed += 1
                log_error(video["id"], e)
                print(f"{video['id']} failed: {str(e)[:200]}", flush=True)
    skipped = len(todo) - done - failed
    print(f"finished: {done} classified, {failed} failed, {skipped} not started; "
          f"rerun to retry the rest (errors in {error_log})", flush=True)
