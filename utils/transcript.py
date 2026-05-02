from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi


LOOKBACK_SECONDS = 10
LOOKAHEAD_SECONDS = 60


def _normalize_entries(raw_entries: Any) -> list[dict]:
    entries = []
    for item in raw_entries:
        if isinstance(item, dict):
            start = item.get("start", 0.0)
            duration = item.get("duration", 0.0)
            text = item.get("text", "")
        else:
            start = getattr(item, "start", 0.0)
            duration = getattr(item, "duration", 0.0)
            text = getattr(item, "text", "")

        entries.append(
            {
                "start": float(start),
                "duration": float(duration),
                "text": str(text).strip(),
            }
        )
    return entries


def fetch_transcript(video_id: str) -> list[dict]:
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
