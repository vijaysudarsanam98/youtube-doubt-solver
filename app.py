from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from utils.ai import ask_gemini
from utils.transcript import get_transcript_context


app = FastAPI(title="YouTube Doubt Solver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskDoubtRequest(BaseModel):
    videoUrl: str | None = None
    videoId: str | None = None
    minute: float = Field(..., ge=0)
    question: str = Field(..., min_length=1)


def extract_video_id(video_url: str) -> str:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return video_id

    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id

        path_parts = [part for part in parsed.path.split("/") if part]
        if "shorts" in path_parts:
            idx = path_parts.index("shorts")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]

    raise ValueError("Could not extract a YouTube video ID from the provided URL")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>YouTube Doubt Solver</title>
      <style>
        :root {
          color-scheme: light;
          --bg: #0f172a;
          --panel: #111827;
          --card: #1f2937;
          --text: #e5e7eb;
          --muted: #9ca3af;
          --accent: #38bdf8;
          --accent-2: #22c55e;
          --border: rgba(255,255,255,0.08);
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: radial-gradient(circle at top, #1e293b 0%, var(--bg) 45%, #020617 100%);
          color: var(--text);
          min-height: 100vh;
          display: grid;
          place-items: center;
          padding: 24px;
        }
        .wrap {
          width: min(920px, 100%);
          display: grid;
          gap: 20px;
        }
        .hero, .panel {
          background: rgba(17, 24, 39, 0.9);
          border: 1px solid var(--border);
          border-radius: 24px;
          box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(14px);
        }
        .hero {
          padding: 28px;
        }
        .hero h1 {
          margin: 0 0 8px;
          font-size: clamp(2rem, 4vw, 3.5rem);
          line-height: 1;
        }
        .hero p { margin: 0; color: var(--muted); max-width: 70ch; }
        .panel {
          padding: 24px;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
        }
        .field { display: grid; gap: 8px; }
        .field.full { grid-column: 1 / -1; }
        label { font-size: 0.9rem; color: var(--muted); }
        input, textarea {
          width: 100%;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.04);
          color: var(--text);
          border-radius: 14px;
          padding: 14px 16px;
          font: inherit;
          outline: none;
        }
        textarea { min-height: 140px; resize: vertical; }
        input:focus, textarea:focus { border-color: rgba(56, 189, 248, 0.8); box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.14); }
        .actions {
          display: flex;
          gap: 12px;
          align-items: center;
          margin-top: 18px;
          flex-wrap: wrap;
        }
        button {
          border: 0;
          border-radius: 14px;
          padding: 14px 20px;
          background: linear-gradient(135deg, var(--accent), #818cf8);
          color: #fff;
          font-weight: 700;
          cursor: pointer;
        }
        button:disabled { opacity: 0.7; cursor: not-allowed; }
        .hint { color: var(--muted); font-size: 0.92rem; }
        pre {
          margin: 18px 0 0;
          background: #0b1220;
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 16px;
          white-space: pre-wrap;
          word-wrap: break-word;
          min-height: 120px;
        }
        @media (max-width: 720px) {
          .grid { grid-template-columns: 1fr; }
          .hero, .panel { border-radius: 18px; }
        }
      </style>
    </head>
    <body>
      <main class="wrap">
        <section class="hero">
          <h1>YouTube Doubt Solver</h1>
          <p>Paste a YouTube URL, set the minute mark, and ask your question. The backend will grab the transcript from that minute and ask Gemini for a simple explanation.</p>
        </section>
        <section class="panel">
          <form id="doubtForm">
            <div class="grid">
              <div class="field full">
                <label for="videoUrl">YouTube URL</label>
                <input id="videoUrl" placeholder="https://www.youtube.com/watch?v=..." required />
              </div>
              <div class="field">
                <label for="minute">Minute</label>
                <input id="minute" type="number" min="0" step="1" value="0" required />
              </div>
              <div class="field">
                <label for="question">Your doubt</label>
                <input id="question" placeholder="What does the speaker mean here?" required />
              </div>
            </div>
            <div class="actions">
              <button id="submitBtn" type="submit">Ask Gemini</button>
              <span class="hint">Tip: enter the minute where the doubt starts (e.g. 3 for the 3rd minute).</span>
            </div>
          </form>
          <pre id="result">Your answer will appear here.</pre>
        </section>
      </main>
      <script>
        const form = document.getElementById('doubtForm');
        const result = document.getElementById('result');
        const button = document.getElementById('submitBtn');

        form.addEventListener('submit', async (event) => {
          event.preventDefault();
          button.disabled = true;
          result.textContent = 'Thinking...';

          try {
            const response = await fetch('/ask-doubt', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                videoUrl: document.getElementById('videoUrl').value.trim(),
                minute: Number(document.getElementById('minute').value),
                question: document.getElementById('question').value.trim()
              })
            });

            const data = await response.json();
            if (!response.ok) {
              throw new Error(data.detail || 'Request failed');
            }

            result.textContent = data.answer;
          } catch (error) {
            result.textContent = 'Error: ' + error.message;
          } finally {
            button.disabled = false;
          }
        });
      </script>
    </body>
    </html>
    """


@app.post("/ask-doubt")
def ask_doubt(payload: AskDoubtRequest):
    try:
        video_id = payload.videoId or (extract_video_id(payload.videoUrl) if payload.videoUrl else None)
        if not video_id:
            raise ValueError("Provide either videoId or videoUrl")

        timestamp = payload.minute * 60.0
        context = get_transcript_context(video_id, timestamp)
        answer = ask_gemini(payload.question, context)
        return {
            "videoId": video_id,
            "minute": payload.minute,
            "timestamp": timestamp,
            "question": payload.question,
            "context": context,
            "answer": answer,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
