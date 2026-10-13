"""
Google Gemini API Client for QBot.

Replaces OpenAI chat completions using Google Gemini's free tier (gemini-2.5-flash / gemini-1.5-flash).
Reads GEMINI_API_KEY from environment or .env.
"""
import time
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

import config

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free API key at "
            "https://aistudio.google.com/app/apikey and add it to your .env file."
        )
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    """
    Executes a chat completion call using Google Gemini.
    Translates standard OpenAI messages format (system, user, assistant)
    into Gemini contents and system_instruction.
    """
    client = get_client()

    system_instruction = None
    contents = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            if system_instruction:
                system_instruction += "\n\n" + content
            else:
                system_instruction = content
        elif role == "assistant":
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_text(text=content)]
            ))
        else:  # user
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=content)]
            ))

    if not contents:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text="")])]

    config_kwargs = {"temperature": temperature}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    gen_config = types.GenerateContentConfig(**config_kwargs)

    # Try configured model first, then fallback to high-availability Lite and Flash models if high demand (503) or rate limit (429) occurs
    candidates = [
        config.CHAT_MODEL,
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-flash-latest",
    ]
    seen = set()
    ordered_models = []
    for m in candidates:
        if m and m not in seen:
            seen.add(m)
            ordered_models.append(m)

    last_exc = None
    for model_name in ordered_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=gen_config,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as exc:
            last_exc = exc
            time.sleep(0.5)
            continue

    if last_exc:
        raise last_exc

    return "I apologize, but I could not generate a response for this question."
