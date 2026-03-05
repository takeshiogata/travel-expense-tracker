"""AI API client for Claude and OpenAI."""

import json
import os
import re

from dotenv import load_dotenv

from config import AI_PROVIDERS, SYSTEM_PROMPT

load_dotenv()


def _call_claude(messages: list[dict], model: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(messages: list[dict], model: str) -> str:
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    oai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    oai_messages.extend(messages)
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=oai_messages,
    )
    return response.choices[0].message.content


def chat(messages: list[dict], provider: str = "claude") -> str:
    config = AI_PROVIDERS[provider]
    if provider == "claude":
        return _call_claude(messages, config["model"])
    else:
        return _call_openai(messages, config["model"])


def extract_expenses(text: str) -> list[dict]:
    """Extract expense JSON from AI response text."""
    pattern = r'\{[^{}]*"expenses"\s*:\s*\[.*?\]\s*\}'
    matches = re.findall(pattern, text, re.DOTALL)
    expenses = []
    for match in matches:
        try:
            data = json.loads(match)
            for exp in data.get("expenses", []):
                if all(k in exp for k in ("description", "amount", "category")):
                    expenses.append({
                        "description": str(exp["description"]),
                        "amount": int(exp["amount"]),
                        "category": str(exp["category"]),
                    })
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    return expenses


def extract_edits(text: str) -> list[dict]:
    """Extract edit JSON from AI response text."""
    pattern = r'\{[^{}]*"edits"\s*:\s*\[.*?\]\s*\}'
    matches = re.findall(pattern, text, re.DOTALL)
    edits = []
    for match in matches:
        try:
            data = json.loads(match)
            for edit in data.get("edits", []):
                if all(k in edit for k in ("original_description", "description", "amount", "category")):
                    edits.append({
                        "original_description": str(edit["original_description"]),
                        "description": str(edit["description"]),
                        "amount": int(edit["amount"]),
                        "category": str(edit["category"]),
                    })
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    return edits


def remove_json_blocks(text: str) -> str:
    """Remove JSON blocks from response for display."""
    cleaned = re.sub(r'```json\s*\{[^{}]*"(?:expenses|edits)".*?\}.*?```', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'\{[^{}]*"(?:expenses|edits)"\s*:\s*\[.*?\]\s*\}', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()
