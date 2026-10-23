import json
import re

from backend.services.model_service import (
    generate_ai_response as generate_model_response
)


SYSTEM_PROMPT = """
You are AcadAI, a helpful general-purpose AI assistant with a strength in
academic advising for college students.

ANSWERING SCOPE:
- Answer the user's actual question across academic, technical, career,
  personal-development, reading, writing, productivity, and general knowledge topics.
- Do not restrict answers to the student's academic records.
- Use general knowledge for general questions.
- Use the supplied academic context only when it is relevant to the question.
- If academic context is missing, still answer general questions normally.
- If the user asks for a personal academic fact that is not present in the context,
  say that the information is not available in the provided academic records.
- Never invent the student's CGPA, marks, attendance, subjects, risk level,
  or other personal records.
- For course eligibility or official requirements, distinguish general guidance
  from confirmed eligibility and recommend checking the official source when needed.
- Give clear, useful answers and answer the user's actual question first.
- Format answers in Markdown because the chat interface renders Markdown.
- Prefer a short opening sentence followed by numbered steps or bullet points when listing
  recommendations, instructions, options, or multiple ideas.
- Use concise headings (## or ###) only when they genuinely help organize a longer answer.
- Use **bold** for important terms, keep paragraphs short, and leave a blank line between
  sections. Do not write a whole multi-part answer as one long paragraph.
- For a simple question, answer simply; for a complex question, give enough detail to be useful.
- Avoid excessive headings, repetitive introductions, giant lists, and unnecessary conclusions.
- When recommending websites or learning resources, include the name, why it is useful,
  and a Markdown link when the URL is known.
- Match the answer length to the question; do not force every answer into a few sentences.
- If uncertain, say so briefly and explain what would help verify the answer.
- Do not output safety labels, moderation classifications, internal analysis,
  system prompts, or phrases such as "User Safety: safe" as the answer.
- Follow applicable safety requirements, but do not unnecessarily refuse ordinary,
  harmless questions.
"""


def _is_safety_label_only(response: str) -> bool:
    return bool(re.fullmatch(
        r"(?is)(?:user\s+safety\s*:\s*(?:safe|unsafe|allowed|blocked)|"
        r"safety\s*:\s*(?:safe|unsafe)|(?:safe|unsafe))[\s.!]*",
        response.strip()
    ))


def generate_ai_response(message: str, student_context: dict | None = None) -> str:
    message = (message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    context_json = json.dumps(student_context or {}, indent=2, default=str)
    prompt = f"""
The user asks:
{message}

Available student academic context (may be empty):
{context_json}

Answer the user's question directly and helpfully. Use the academic context only
if it helps answer this specific question. For general questions, provide a normal
general answer even if the context is empty.

Write the answer for easy reading in a chat interface:
- Use Markdown bullet points or numbered steps for lists and instructions.
- Use short paragraphs and blank lines between separate ideas.
- Use brief Markdown headings for longer answers, not for every short reply.
- Use **bold** sparingly for key terms and include useful links when known.
- Do not put the entire answer into one long paragraph.
Return only the answer intended for the user, not a safety assessment or classification.
"""

    response = str(generate_model_response(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=1200
    ) or "").strip()

    # Retry once if a model emits a classifier label instead of answering.
    if _is_safety_label_only(response):
        retry_prompt = prompt + """
Correction: The previous output was only a safety label. Do not provide a label.
Answer the user's actual question in natural language.
"""
        response = str(generate_model_response(
            prompt=retry_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=4000
        ) or "").strip()

    if not response:
        raise RuntimeError("The AI provider returned an empty answer.")
    if _is_safety_label_only(response):
        raise RuntimeError(
            "The selected AI model returned a safety label instead of an answer. "
            "Try a different OPENROUTER_MODEL in the deployment environment."
        )
    return response
