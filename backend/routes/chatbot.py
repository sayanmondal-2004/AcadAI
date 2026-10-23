from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd

from backend.database import get_connection

from backend.services.academic_analyzer import (
    calculate_average_attendance,
    find_weak_subjects,
    calculate_academic_risk,
    generate_recommendations,
)

from backend.services.chatbot_service import generate_ai_response


router = APIRouter(
    prefix="/students",
    tags=["AI Chatbot"]
)


class ChatRequest(BaseModel):
    message: str


def get_student_context(student_id: str):

    student_id = student_id.strip().upper()

    connection = get_connection()
    cursor = connection.cursor()

    # ---------------------------------------------------------
    # GET SAVED ACADEMIC PROFILE
    # ---------------------------------------------------------

    cursor.execute(
        """
        SELECT
            student_id,
            cgpa,
            target_cgpa,
            career_goal,
            current_semester,
            academic_year
        FROM academic_profiles
        WHERE student_id = ?
        """,
        (student_id,)
    )

    profile = cursor.fetchone()

    if not profile:
        connection.close()
        return None


    # ---------------------------------------------------------
    # GET SAVED SUBJECTS
    # ---------------------------------------------------------

    cursor.execute(
        """
        SELECT
            course_code,
            course_name,
            marks,
            attendance_percent,
            status
        FROM academic_subjects
        WHERE student_id = ?
        ORDER BY id
        """,
        (student_id,)
    )

    subject_rows = cursor.fetchall()

    connection.close()


    if not subject_rows:
        return None


    # ---------------------------------------------------------
    # CONVERT SUBJECTS TO DATAFRAME
    # ---------------------------------------------------------

    records = []

    for row in subject_rows:

        records.append({
            "student_id": student_id,
            "course_code": row["course_code"],
            "course_name": row["course_name"],
            "marks": float(row["marks"]),
            "attendance_percent": float(
                row["attendance_percent"]
            )
        })


    records_df = pd.DataFrame(records)


    # ---------------------------------------------------------
    # STUDENT VALUES
    # ---------------------------------------------------------

    cgpa = float(profile["cgpa"])

    target_cgpa = float(
        profile["target_cgpa"]
    )


    # ---------------------------------------------------------
    # CALCULATE ACADEMIC INFORMATION
    # ---------------------------------------------------------

    average_attendance = (
        calculate_average_attendance(
            records_df
        )
    )


    weak_subjects = (
        find_weak_subjects(
            records_df
        )
    )


    academic_risk = (
        calculate_academic_risk(
            records_df,
            cgpa
        )
    )


    recommendations = (
        generate_recommendations(
            records_df,
            cgpa
        )
    )


    # ---------------------------------------------------------
    # WEAK SUBJECTS
    # ---------------------------------------------------------

    weak_subject_data = []


    for _, subject in weak_subjects.iterrows():

        weak_subject_data.append({

            "course_code":
                subject["course_code"],

            "course_name":
                subject["course_name"],

            "marks":
                float(subject["marks"]),

            "attendance":
                float(
                    subject["attendance_percent"]
                )
        })


    # ---------------------------------------------------------
    # COMPLETE STUDENT CONTEXT FOR AI
    # ---------------------------------------------------------

    student_context = {

        "student_id":
            student_id,

        "cgpa":
            cgpa,

        "target_cgpa":
            target_cgpa,

        "career_goal":
            profile["career_goal"],

        "current_semester":
            profile["current_semester"],

        "academic_year":
            profile["academic_year"],

        "average_attendance":
            average_attendance,

        "academic_risk":
            academic_risk,

        "weak_subjects":
            weak_subject_data,

        "subjects":
            records,

        "recommendations":
            recommendations
    }


    return student_context


# =============================================================
# CHAT ENDPOINT
# =============================================================

@router.post("/{student_id}/chat")
def chat_with_advisor(
    student_id: str,
    request: ChatRequest
):

    message = (request.message or "").strip()
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Please enter a message.")

    # Academic context is optional: general questions should still be answered.
    student_context = None
    try:
        student_context = get_student_context(student_id)
    except Exception as context_error:
        print(f"Unable to load academic context for chatbot: {context_error}")

    try:
        ai_response = generate_ai_response(
            message,
            student_context or {}
        )


        return {

            "student_id":
                student_id,

            "message":
                message,

            "response":
                ai_response

        }


    except Exception as e:

        return {

            "error":
                "AI service unavailable",

            "details":
                str(e)

        }