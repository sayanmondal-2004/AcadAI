import os
import requests


# ============================================================
# AI PROVIDER CONFIGURATION
# ============================================================

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "ollama"
).lower()

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b"
)

# OpenRouter Free Models Router
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# ============================================================
# CONCISE RESPONSE INSTRUCTION
# ============================================================

CONCISE_INSTRUCTION = """
Answer the user's actual question directly and helpfully.
Use a length appropriate to the question; include steps or examples when useful.
Do not output safety classifications or internal labels instead of an answer.
Use supplied personal data only when relevant and never invent it.
"""


# ============================================================
# BUILD MESSAGES
# ============================================================

def build_messages(
    prompt: str,
    system_prompt: str = ""
):

    messages = []

    combined_system_prompt = (
        system_prompt.strip()
    )

    # Respect task-specific system prompts (e.g. strict JSON output). Appending
    # generic prose instructions can conflict with structured-output requirements.
    if not combined_system_prompt:
        combined_system_prompt = CONCISE_INSTRUCTION.strip()

    messages.append({
        "role": "system",
        "content": combined_system_prompt
    })

    messages.append({
        "role": "user",
        "content": prompt
    })

    return messages


# ============================================================
# OLLAMA
# ============================================================

def generate_with_ollama(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1200
) -> str:

    import ollama

    messages = build_messages(
        prompt,
        system_prompt
    )

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={
            "temperature": 0.2,
            "num_predict": max_tokens
        }
    )

    content = response["message"]["content"]

    if not content:

        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return content.strip()


# ============================================================
# OPENROUTER
# ============================================================

def generate_with_openrouter(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1200
) -> str:

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is not set."
        )

    messages = build_messages(
        prompt,
        system_prompt
    )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://acad-ai.vercel.app",
        "X-Title": "AcadAI"
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=180
    )

    if not response.ok:

        raise RuntimeError(
            f"OpenRouter API error "
            f"{response.status_code}: {response.text}"
        )

    data = response.json()

    choices = data.get("choices")

    if not choices:

        raise RuntimeError(
            f"OpenRouter returned no choices: {data}"
        )

    message = choices[0].get(
        "message",
        {}
    )

    content = message.get(
        "content"
    )

    # Some models return content as a list.
    if isinstance(content, list):

        text_parts = []

        for part in content:

            if isinstance(part, dict):

                if part.get("type") == "text":

                    text_parts.append(
                        part.get("text", "")
                    )

                elif "text" in part:

                    text_parts.append(
                        part["text"]
                    )

        content = "".join(
            text_parts
        )

    if not content or not str(content).strip():
        choice = choices[0] if choices else {}
        message = choice.get("message", {}) or {}
        usage = data.get("usage", {}) or {}
        details = {
            "model_requested": OPENROUTER_MODEL,
            "model_used": data.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "reasoning": message.get("reasoning"),
            "usage": usage,
            "provider_error": data.get("error"),
        }
        print("OpenRouter empty-response details:", details)
        raise RuntimeError(
            "OpenRouter returned no text. "
            f"Model: {data.get('model', OPENROUTER_MODEL)}; "
            f"finish_reason: {choice.get('finish_reason')}; "
            f"usage: {usage}"
        )

    return str(
        content
    ).strip()


# ============================================================
# MAIN AI FUNCTION
# ============================================================

def generate_ai_response(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1200
) -> str:

    if AI_PROVIDER == "ollama":

        return generate_with_ollama(
            prompt,
            system_prompt,
            max_tokens
        )

    elif AI_PROVIDER == "openrouter":

        return generate_with_openrouter(
            prompt,
            system_prompt,
            max_tokens
        )

    else:

        raise RuntimeError(
            f"Unsupported AI_PROVIDER: {AI_PROVIDER}"
        )