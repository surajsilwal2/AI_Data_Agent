

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def pick_llm(level: str) -> ChatOpenAI:

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing")

    models = {
        "low": "liquid/lfm-3-1.7b",
        "medium": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "high": "nvidia/nemotron-3-ultra-550b-a55b"
    }

    level = level.lower()

    if level not in models:
        raise ValueError(f"Invalid level: {level}")

    return ChatOpenAI(
        model=models[level],
        temperature=0,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )


