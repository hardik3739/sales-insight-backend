"""
AI service — calls Groq Cloud API (Llama 3.3 70B Versatile).
Only structured metrics are embedded in the prompt, never raw CSV content.
"""
import os
import json
from groq import Groq
from fastapi import HTTPException

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="GROQ_API_KEY not configured on server.",
            )
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are a senior business analyst preparing an executive briefing.
You will receive structured sales metrics as JSON.
Write a professional, data-driven narrative summary suitable for C-suite leadership.
Rules:
- Maximum 200 words
- Highlight the single most important performance insight first
- Use specific numbers from the metrics
- Flag any concerns (e.g. cancellations, underperforming regions)
- End with one forward-looking recommendation
- Write in confident, clear prose — no bullet points, no headers"""


def generate_summary(metrics: dict) -> str:
    """
    Send aggregated metrics to Groq and return an executive summary string.
    """
    client = _get_client()

    user_content = (
        "Here are the sales metrics extracted from the uploaded file:\n\n"
        + json.dumps(metrics, indent=2)
        + "\n\nWrite the executive summary now."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
            max_tokens=350,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {exc}",
        )

    summary = response.choices[0].message.content.strip()
    if not summary:
        raise HTTPException(
            status_code=502,
            detail="AI returned an empty response. Please try again.",
        )
    return summary
