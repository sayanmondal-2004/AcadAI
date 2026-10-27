"""Deterministic subject-priority and weekly-hour allocation for AcadAI."""

import pandas as pd


def generate_study_plan(records, weekly_hours=10):
    """Prioritize subjects by marks and attendance, then allocate weekly hours.

    The rounded allocations are adjusted so their sum equals weekly_hours to
    one decimal place, preventing small rounding differences in the UI.
    """
    if records is None or records.empty:
        return []

    try:
        weekly_hours = float(weekly_hours)
    except (TypeError, ValueError):
        raise ValueError("weekly_hours must be a number")
    if weekly_hours <= 0:
        raise ValueError("weekly_hours must be greater than zero")

    subjects = []
    for _, record in records.iterrows():
        marks = float(record["marks"])
        attendance = float(record["attendance_percent"])
        priority = 5

        if marks < 60:
            priority += 50
        elif marks < 70:
            priority += 30
        elif marks < 80:
            priority += 15

        if attendance < 75:
            priority += 30
        elif attendance < 80:
            priority += 15

        subjects.append({
            "course_code": str(record["course_code"]),
            "course_name": str(record["course_name"]),
            "marks": marks,
            "attendance": attendance,
            "priority": priority,
        })

    subjects.sort(key=lambda item: item["priority"], reverse=True)
    total_priority = sum(item["priority"] for item in subjects)
    target_tenths = round(weekly_hours * 10)
    allocated_tenths = []

    for subject in subjects:
        share = (target_tenths * subject["priority"] / total_priority) if total_priority else 0
        allocated_tenths.append(int(round(share)))

    # Correct rounding drift on the highest-priority subject.
    if allocated_tenths:
        allocated_tenths[0] += target_tenths - sum(allocated_tenths)

    plan = []
    for subject, tenths in zip(subjects, allocated_tenths):
        plan.append({
            **subject,
            "weekly_hours": round(max(0, tenths) / 10, 1),
        })
    return plan
