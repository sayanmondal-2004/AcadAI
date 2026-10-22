import secrets
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.quiz_ai import generate_quiz

router = APIRouter(prefix="/quiz", tags=["AI Quiz"])

# Temporary in-memory quiz store only. Nothing is written to PostgreSQL.
# Entries expire automatically after one hour.
QUIZ_TTL_SECONDS = 60 * 60
quiz_store = {}


class QuizRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=150)
    topic: str = Field(..., min_length=2, max_length=200)


class QuizSubmitRequest(BaseModel):
    quiz_id: str = Field(..., min_length=20, max_length=100)
    answers: dict[str, str]


def _cleanup_expired_quizzes():
    now = time.time()
    expired = [
        quiz_id for quiz_id, item in quiz_store.items()
        if now - item["created_at"] > QUIZ_TTL_SECONDS
    ]
    for quiz_id in expired:
        quiz_store.pop(quiz_id, None)


def _public_quiz(quiz: dict) -> dict:
    """Remove answer keys before sending the quiz to the browser."""
    return {
        "title": quiz["title"],
        "subject": quiz["subject"],
        "topic": quiz["topic"],
        "questions": [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"]
            }
            for q in quiz["questions"]
        ]
    }


@router.post("/generate")
def create_quiz(request: QuizRequest):
    """Generate a temporary quiz. It is never saved in the database."""
    subject = request.subject.strip()
    topic = request.topic.strip()

    if not subject or not topic:
        raise HTTPException(status_code=400, detail="Subject and topic are required.")

    try:
        _cleanup_expired_quizzes()
        quiz = generate_quiz(subject, topic)
        quiz_id = secrets.token_urlsafe(32)

        quiz_store[quiz_id] = {
            "created_at": time.time(),
            "quiz": quiz
        }

        return {
            "success": True,
            "quiz_id": quiz_id,
            "quiz": _public_quiz(quiz)
        }

    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to create a valid quiz: {error}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI quiz generation failed: {error}"
        )


@router.post("/submit")
def submit_quiz(request: QuizSubmitRequest):
    """Grade a temporary quiz in memory. Results are not saved to the database."""
    _cleanup_expired_quizzes()

    item = quiz_store.pop(request.quiz_id, None)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="This quiz has expired or is no longer available. Please generate a new quiz."
        )

    quiz = item["quiz"]
    answers = {
        str(key): str(value).strip().upper()
        for key, value in request.answers.items()
    }

    if len(answers) != len(quiz["questions"]):
        raise HTTPException(
            status_code=400,
            detail=f"Please submit answers for all {len(quiz['questions'])} questions."
        )

    score = 0
    review = []

    for index, question in enumerate(quiz["questions"]):
        selected = answers.get(str(index))
        correct = question["correct_answer"]

        if selected == correct:
            score += 1

        review.append({
            "id": question["id"],
            "question": question["question"],
            "options": question["options"],
            "your_answer": selected,
            "correct_answer": correct,
            "explanation": question["explanation"],
            "is_correct": selected == correct
        })

    return {
        "success": True,
        "score": score,
        "total": len(quiz["questions"]),
        "percentage": round(score / len(quiz["questions"]) * 100),
        "subject": quiz["subject"],
        "topic": quiz["topic"],
        "review": review
    }
