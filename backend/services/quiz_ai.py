import json
import re

from backend.services.model_service import generate_ai_response


def _extract_json(text: str):
    """Parse a JSON object, allowing surrounding Markdown fences or prose."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("AI returned an empty response.")

    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Recover a JSON object if the provider adds text around it.
    start = text.find("{")
    if start >= 0:
        try:
            parsed, _ = json.JSONDecoder().raw_decode(text[start:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "AI did not return a complete valid JSON object. The response may be "
        "truncated or malformed. Check the model output-token limit and provider logs."
    )


def generate_quiz(subject: str, topic: str) -> dict:
    system_prompt = """
You are AcadAI, an intelligent academic quiz generator.

Generate a useful practice quiz based on any valid subject and topic provided by the student.

TOPIC FLEXIBILITY:
1. Do not impose artificial restrictions on the topic or its scope.
2. Explore relevant concepts, related topics, prerequisites, advanced concepts,
   real-world applications, examples, and connected subject areas.
3. Interpret broad or narrow topics reasonably and generate useful questions.
4. Do not restrict questions to the exact words used in the topic.
5. Do not reject a topic simply because it is broad, unfamiliar, or interdisciplinary.
6. Keep questions meaningfully connected to the student's subject and topic.
7. Avoid unrelated questions, fabricated facts, and ambiguous answers.

QUIZ FORMAT:
1. Generate EXACTLY 5 questions.
2. Every question must have EXACTLY 4 options.
3. Option keys must be A, B, C, and D.
4. Each question must have exactly ONE correct answer.
5. correct_answer must be A, B, C, or D.
6. Include a clear, concise explanation for every answer.
7. Mix conceptual, analytical, and application-based questions where appropriate.
8. Do not use "All of the above" or "None of the above".
9. Return ONLY valid JSON without Markdown or code fences.

REQUIRED JSON FORMAT:
{
  "title": "5-Question Practice Quiz",
  "subject": "subject",
  "topic": "topic",
  "questions": [
    {
      "id": 1,
      "question": "Question text",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      },
      "correct_answer": "A",
      "explanation": "Explanation of the correct answer."
    }
  ]
}
"""

    prompt = f"""SUBJECT:\n{subject}\n\nTOPIC:\n{topic}\n\nGenerate the quiz now using the required JSON format. Return all 5 complete questions. Ensure the JSON is complete, with no text before or after it."""
    # Five complete multiple-choice questions with explanations need more than
    # the generic 300-token default.
    raw = generate_ai_response(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=2500
    )
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
