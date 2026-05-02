# YouTube Doubt Solver Backend

## Setup

1. Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` in your browser to use the simple UI.

## UI

Paste a YouTube URL, enter the timestamp in seconds, and type your doubt.

## API Endpoint

`POST /ask-doubt`

```json
{
  "videoUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "timestamp": 120,
  "question": "What is the speaker explaining here?"
}
```
