import os

import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()


def ask_gemini(question: str, context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    prompt = (
        "You are a helpful YouTube tutor.\n"
        "Use the transcript context to answer the user's doubt in a simple, clear way.\n"
        "If the context is insufficient, say that briefly and explain what is missing.\n\n"
        f"Transcript context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )

    try:
        response = model.generate_content(prompt)
        return getattr(response, "text", None) or "No answer returned by Gemini."
    except Exception as exc:
        message = str(exc)
        if "CONSUMER_SUSPENDED" in message or "Permission denied" in message or "403" in message:
            raise ValueError(
                "Your Gemini API key/project is blocked or suspended. Create a new key in Google AI Studio, "
                "put it in GEMINI_API_KEY, and restart the app."
            ) from exc
        raise
