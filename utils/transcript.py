import os
from typing import Any

import requests
from youtube_transcript_api import YouTubeTranscriptApi


LOOKBACK_SECONDS = 10
LOOKAHEAD_SECONDS = 60

RAPIDAPI_HOST = "youtube-transcript3.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/api/transcript"


def _normalize_entries(raw_entries: Any) -> list[dict]:
    entries = []
    for item in raw_entries:
        if isinstance(item, dict):
            start = item.get("start", item.get("offset", 0.0))
            duration = item.get("duration", item.get("dur", 0.0))
            text = item.get("text", item.get("subtitle", ""))
        else:
            start = getattr(item, "start", 0.0)
            duration = getattr(item, "duration", 0.0)
            text = getattr(item, "text", "")

        try:
            start = float(start)
        except (TypeError, ValueError):
            start = 0.0
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 0.0

        entries.append(
            {
                "start": start,
                "duration": duration,
                "text": str(text).strip(),
            }
        )
    return entries


def _fetch_via_rapidapi(video_id: str) -> list[dict]:
    api_key = os.environ["RAPIDAPI_KEY"]
    response = requests.get(
        RAPIDAPI_URL,
        params={"videoId": video_id},
        headers={
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": RAPIDAPI_HOST,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        for key in ("transcript", "data", "result", "captions"):
            if key in data and isinstance(data[key], list):
                return _normalize_entries(data[key])
        raise RuntimeError(f"Unexpected RapidAPI response shape: keys={list(data.keys())}")
    if isinstance(data, list):
        return _normalize_entries(data)
    raise RuntimeError("Unexpected RapidAPI response type")


def _fetch_via_library(video_id: str) -> list[dict]:
    try:
        api = YouTubeTranscriptApi()
    except TypeError:
        api = None

    if api is not None and hasattr(api, "fetch"):
        raw = api.fetch(video_id)
        return _normalize_entries(raw)

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        raw = YouTubeTranscriptApi.get_transcript(video_id)
        return _normalize_entries(raw)

    raise RuntimeError("Unsupported youtube-transcript-api version")


def fetch_transcript(video_id: str) -> list[dict]:
    if os.environ.get("RAPIDAPI_KEY"):
        return _fetch_via_rapidapi(video_id)
    return _fetch_via_library(video_id)


def get_transcript_context(video_id: str, timestamp: float) -> str:
    transcript = fetch_transcript(video_id)
    start_time = max(0.0, timestamp - LOOKBACK_SECONDS)
    end_time = timestamp + LOOKAHEAD_SECONDS

    relevant_lines = [
        f"[{entry['start']:.1f}s] {entry['text']}"
        for entry in transcript
        if entry["start"] <= end_time and (entry["start"] + entry["duration"]) >= start_time
    ]

    if not relevant_lines:
        raise ValueError("No transcript found around the provided timestamp")

    return "\n".join(relevant_lines)
