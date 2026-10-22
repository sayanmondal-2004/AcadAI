import json
import re

from backend.services.model_service import generate_ai_response


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("AI did not return valid JSON.")
        return json.loads(text[start:end + 1])


def generate_quiz(subject: str, topic: str) -> dict:
    system_prompt = """
You are AcadAI, an academic quiz generator.
Create a college-level practice quiz using the supplied subject and topic as the starting point. Do not restrict questions to only the exact wording or narrow boundaries of the topic: include relevant related concepts, prerequisite knowledge, applications, examples, and connected subtopics when useful. Keep the quiz academically relevant to the supplied subject/topic rather than introducing unrelated material.

STRICT RULES:
1. Generate EXACTLY 5 questions.
2. Every question is multiple-choice with EXACTLY 4 options.
3. Option keys must be A, B, C, D.
4. There must be exactly ONE correct answer.
5. correct_answer must be A, B, C, or D.
6. Include a short explanation for every answer.
7. Questions must be relevant to the supplied subject/topic.
8. Mix conceptual and application/understanding questions where appropriate.
9. Do not use all of the above or none of the above.
10. Return ONLY valid JSON. No Markdown or code fences.

Required format:
{
  "title": "5-Question Practice Quiz",
  "subject": "subject",
  "topic": "topic",
  "questions": [
    {
      "id": 1,
      "question": "Question text",
      "options": {"A":"...", "B":"...", "C":"...", "D":"..."},
      "correct_answer": "A",
      "explanation": "Short explanation."
    }
  ]
}
"""

    prompt = f"""SUBJECT:\n{subject}\n\nTOPIC:\n{topic}\n\nGenerate the quiz now using the required JSON format."""
    raw = generate_ai_response(prompt=prompt, system_prompt=system_prompt)
    data = _extract_json(raw)

    if not isinstance(data, dict):
        raise ValueError("AI quiz response must be a JSON object.")

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        raise ValueError("AI must return exactly 5 questions.")

    cleaned = []
    for index, item in enumerate(questions, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Question {index} has an invalid format.")

        question = str(item.get("question", "")).strip()
        options = item.get("options")
        correct = str(item.get("correct_answer", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if not question:
            raise ValueError(f"Question {index} is missing question text.")
        if not isinstance(options, dict):
            raise ValueError(f"Question {index} has invalid options.")

        options = {k: str(options.get(k, "")).strip() for k in ("A", "B", "C", "D")}
        if any(not v for v in options.values()):
            raise ValueError(f"Question {index} must contain A, B, C and D options.")
        if correct not in ("A", "B", "C", "D"):
            raise ValueError(f"Question {index} has an invalid correct answer.")
        if not explanation:
            raise ValueError(f"Question {index} is missing an explanation.")

        cleaned.append({
            "id": index,
            "question": question,
            "options": options,
            "correct_answer": correct,
            "explanation": explanation
        })

    return {
        "title": "5-Question Practice Quiz",
        "subject": subject,
        "topic": topic,
        "questions": cleaned
    }
