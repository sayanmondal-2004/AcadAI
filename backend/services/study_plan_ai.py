"""AI-assisted weekly schedule generation for AcadAI."""

import json

from backend.services.model_service import (
    generate_ai_response as generate_model_response,
)


def build_fallback_weekly_schedule(study_plan: list, weekly_hours: float) -> str:
    """Return a usable, deterministic schedule if the AI provider fails."""
    days = [
        "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
        "FRIDAY", "SATURDAY", "SUNDAY",
    ]
    if not study_plan:
        return "No subject data is available to build a weekly schedule."

    sorted_subjects = sorted(
        study_plan,
        key=lambda subject: float(subject.get("priority", 0) or 0),
        reverse=True,
    )
    lines = [
        "AI generation is unavailable, so this is a basic fallback schedule.",
        f"Weekly study target: {float(weekly_hours):g} hours.",
        "Use the subject-hour allocations shown in the study-plan cards as the source of truth.",
        "",
    ]
    for index, day in enumerate(days):
        first = sorted_subjects[index % len(sorted_subjects)]
        second = sorted_subjects[(index + 1) % len(sorted_subjects)] if len(sorted_subjects) > 1 else None
        lines.append(f"{day}:")
        lines.append(
            f"- {first.get('course_code', '')} — {first.get('course_name', 'Subject')}: "
            "review lecture notes and write a short summary."
        )
        if second and second is not first:
            lines.append(
                f"- {second.get('course_code', '')} — {second.get('course_name', 'Subject')}: "
                "solve practice questions and review mistakes."
            )
        else:
            lines.append("- Finish with a short self-test and note topics to revisit.")
        lines.append("")
    return "\n".join(lines).strip()


def generate_ai_study_plan(study_plan: list, weekly_hours: float) -> str:
    """Generate a weekly schedule with predictable weekday headings for the UI."""
    if not study_plan:
        return "No subject data is available to build a weekly schedule."

    system_prompt = """
You are AcadAI, a practical academic study-planning assistant.
Create a realistic Monday-to-Sunday study schedule using only the supplied planner data.

Rules:
- Do not invent subjects, marks, attendance, or course details.
- Treat each subject's weekly_hours in the supplied data as its total weekly allocation.
- Do not increase, decrease, or claim a different allocation for any subject.
- Give higher-priority subjects more attention.
- Suggest specific activities: concept review, active recall, practice questions,
  coding/problem solving, past-paper practice, and weekly revision where appropriate.
- Keep the schedule concise and realistic for a college student.
- Do not include an introduction, conclusion, tables, or unrelated advice.
- Use exactly these seven headings, each on its own line, spelled exactly as shown:
  MONDAY:
  TUESDAY:
  WEDNESDAY:
  THURSDAY:
  FRIDAY:
  SATURDAY:
  SUNDAY:
- Under every heading, write 1-3 bullet points. Every bullet must name a subject
  from the supplied data and give a practical activity.
- Distribute subjects across the week. Do not imply that a daily session changes
  the total weekly hours assigned by the planner.
- Return only the schedule, in plain text with weekday headings and bullet points.
""".strip()

    context = json.dumps(study_plan, indent=2, default=str)
    prompt = f"""
Create a weekly schedule for a student with a total target of {float(weekly_hours):g} study hours per week.

Use this exact planner data. The subject allocations are authoritative:
{context}

Return all seven weekday headings and 1-3 actionable bullets beneath each heading.
Do not output JSON or Markdown tables.
""".strip()

    result = generate_model_response(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=1600,
    )
    result = str(result or "").strip()
    if not result:
        raise RuntimeError("The AI provider returned an empty study schedule.")
    return result
