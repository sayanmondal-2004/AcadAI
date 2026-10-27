from fastapi import APIRouter, HTTPException
import pandas as pd

from backend.database import get_connection
from backend.services.study_planner import generate_study_plan
from backend.services.study_plan_ai import (
    generate_ai_study_plan,
    build_fallback_weekly_schedule,
)


router = APIRouter(
    prefix="/students",
    tags=["Study Plan"]
)


# ============================================================
# GET PERSONALIZED STUDY PLAN
# ============================================================

@router.get("/{student_id}/study-plan")
def get_study_plan(
    student_id: str,
    weekly_hours: float = 10
):
    """
    Generate a personalized study plan using the student's
    CURRENT academic profile and subject data from SQLite.

    Data source:
        academic_profiles
        academic_subjects

    The old academic_records.csv is NOT used.
    """

    # --------------------------------------------------------
    # Validate student ID
    # --------------------------------------------------------

    student_id = student_id.strip().upper()

    if not student_id:
        raise HTTPException(
            status_code=400,
            detail="Student ID is required."
        )

    # --------------------------------------------------------
    # Validate weekly hours
    # --------------------------------------------------------

    try:
        weekly_hours = float(weekly_hours)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="weekly_hours must be a number."
        )

    if weekly_hours <= 0:
        raise HTTPException(
            status_code=400,
            detail="weekly_hours must be greater than 0."
        )

    # --------------------------------------------------------
    # Connect to database
    # --------------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # ====================================================
        # GET ACADEMIC PROFILE
        # ====================================================

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
            raise HTTPException(
                status_code=404,
                detail=(
                    "Academic profile not found. "
                    "Please complete your Academic Profile first."
                )
            )

        # ====================================================
        # GET CURRENT SUBJECT DATA
        # ====================================================

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

    finally:
        connection.close()

    # --------------------------------------------------------
    # Make sure subjects exist
    # --------------------------------------------------------

    if not subject_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                "No subjects found for this student. "
                "Please add your subjects, marks and attendance "
                "in Academic Profile."
            )
        )

    # --------------------------------------------------------
    # Convert SQLite rows to DataFrame
    #
    # study_planner.py expects:
    # marks
    # attendance_percent
    # course_code
    # course_name
    # --------------------------------------------------------

    records = pd.DataFrame(
        [
            {
                "student_id": student_id,
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "marks": row["marks"],
                "attendance_percent": row["attendance_percent"],
                "status": row["status"],
            }
            for row in subject_rows
        ]
    )

    # --------------------------------------------------------
    # Clean numeric values
    # --------------------------------------------------------

    records["marks"] = pd.to_numeric(
        records["marks"],
        errors="coerce"
    )

    records["attendance_percent"] = pd.to_numeric(
        records["attendance_percent"],
        errors="coerce"
    )

    # Remove invalid subject records
    records = records.dropna(
        subset=[
            "marks",
            "attendance_percent"
        ]
    )

    if records.empty:
        raise HTTPException(
            status_code=400,
            detail="No valid subject marks or attendance data found."
        )

    # ========================================================
    # GENERATE DETERMINISTIC STUDY PLAN
    # ========================================================

    plan = generate_study_plan(
        records,
        weekly_hours
    )

    if not plan:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate study plan."
        )

    # ========================================================
    # GENERATE AI STUDY PLAN
    # ========================================================

    ai_plan = None
    ai_error = None

    try:

        ai_plan = generate_ai_study_plan(
            plan,
            weekly_hours
        )

    except Exception as e:

        ai_error = str(e)
        # Keep the AI section useful even when the model provider fails.
        ai_plan = build_fallback_weekly_schedule(plan, weekly_hours)

    # ========================================================
    # CALCULATE SUMMARY
    # ========================================================

    total_subjects = len(plan)

    highest_priority_subject = max(
        plan,
        key=lambda subject: subject["priority"]
    )

    total_allocated_hours = round(
        sum(
            float(subject["weekly_hours"])
            for subject in plan
        ),
        1
    )

    average_marks = round(
        records["marks"].mean(),
        2
    )

    average_attendance = round(
        records["attendance_percent"].mean(),
        2
    )

    # ========================================================
    # RETURN COMPLETE PERSONALIZED RESPONSE
    # ========================================================

    response = {
        "success": True,

        "student_id": student_id,

        # ----------------------------------------------------
        # Academic Profile
        # ----------------------------------------------------

        "academic_profile": {
            "cgpa": profile["cgpa"],
            "target_cgpa": profile["target_cgpa"],
            "career_goal": profile["career_goal"],
            "current_semester": profile["current_semester"],
            "academic_year": profile["academic_year"],
        },

        # ----------------------------------------------------
        # Study Plan Settings
        # ----------------------------------------------------

        "weekly_hours": weekly_hours,

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        "summary": {
            "total_subjects": total_subjects,
            "total_allocated_hours": total_allocated_hours,
            "average_marks": average_marks,
            "average_attendance": average_attendance,

            "highest_priority_subject": {
                "course_code": highest_priority_subject[
                    "course_code"
                ],
                "course_name": highest_priority_subject[
                    "course_name"
                ],
                "priority": highest_priority_subject[
                    "priority"
                ],
            },
        },

        # ----------------------------------------------------
        # Personalized deterministic plan
        # ----------------------------------------------------

        "study_plan": plan,

        # ----------------------------------------------------
        # AI-generated explanation/schedule
        # ----------------------------------------------------

        "ai_study_plan": ai_plan,
    }

    # Include AI provider error for debugging when fallback is used
    if ai_error:
        response["ai_error"] = ai_error

    return response