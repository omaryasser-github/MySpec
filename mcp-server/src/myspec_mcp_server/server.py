"""MCP resources, tools, and prompts for local MySpec profile context."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import MCPServer

from . import __version__
from .profile import (
    MESSAGES,
    allocate_minutes,
    build_profile,
    gap_analysis_payload,
    get_language,
    get_profile_path,
    load_profile,
    resource_text,
    save_profile,
)
from .questions import (
    CATEGORIES_METADATA,
    get_question_pair,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("myspec_mcp_server")

mcp = MCPServer(
    name="myspec-local",
    version=__version__,
    instructions=(
        "Local-only MySpec profile context. Profile content is read from the local filesystem on demand. "
        "The server uses stdio and exposes no remote transport."
    ),
)


def _load_current_profile():
    return load_profile(get_profile_path())


@mcp.resource("myprofile://summary")
def myprofile_summary() -> str:
    """Provide a concise summary view of the local MySpec profile."""

    return resource_text(_load_current_profile(), "summary")


@mcp.resource("myprofile://skills")
def myprofile_skills() -> str:
    """Provide current skills, learning areas, and skill-related limitations."""

    return resource_text(_load_current_profile(), "skills")


@mcp.resource("myprofile://preferences")
def myprofile_preferences() -> str:
    """Provide communication and output preferences from the local profile."""

    return resource_text(_load_current_profile(), "preferences")


@mcp.resource("myprofile://full")
def myprofile_full() -> str:
    """Provide the complete local profile text, unchanged when available."""

    return resource_text(_load_current_profile(), "full")


@mcp.tool()
def get_gap_analysis(project_description: str) -> dict[str, Any]:
    """Compare project technology mentions with local profile evidence.

    Returns local evidence and explicit lexical matches for the host model to
    interpret. Mention overlap is not itself a proficiency assessment.
    """

    if not project_description.strip():
        return {"error": "project_description must not be empty"}
    if len(project_description) > 20_000:
        return {"error": "project_description exceeds the 20,000-character limit"}
    snapshot = _load_current_profile()
    return gap_analysis_payload(snapshot, project_description)


@mcp.tool()
def get_onboarding_plan(topic: str, minutes: int = 60) -> dict[str, Any]:
    """Create a time-boxed learning plan informed by the local profile."""

    if not topic.strip():
        return {"error": "topic must not be empty"}
    if len(topic) > 2_000:
        return {"error": "topic exceeds the 2,000-character limit"}
    if not 5 <= minutes <= 480:
        return {"error": "minutes must be between 5 and 480"}

    language = get_language()
    messages = MESSAGES[language]
    snapshot = _load_current_profile()
    stages = messages["agenda"]
    durations = allocate_minutes(minutes)
    agenda = [
        {"minutes": duration, "activity": activity}
        for duration, activity in zip(durations, stages)
    ]
    return {
        "title": messages["plan_title"],
        "topic": topic,
        "total_minutes": minutes,
        "profile_status": snapshot.status,
        "profile_context": resource_text(snapshot, "skills", language),
        "agenda": agenda,
        "profile_warning": messages["no_profile_warning"] if snapshot.status != "available" else None,
    }


@mcp.tool()
def start_interview(language: str = "en") -> dict[str, Any]:
    """Start an interactive MySpec Master Interview session.

    Args:
        language: Language code ("en" or "ar"). Defaults to "en" or MYSPEC_LANG env var.

    Returns:
        Structured payload containing initial turn metadata and Question Pair 0 (Q01, Q02).
    """
    lang = language or get_language()
    try:
        pair = get_question_pair(0, lang)
    except Exception as exc:
        return {"error": f"Failed to start interview: {exc}"}

    cat_meta = CATEGORIES_METADATA.get(1, {})
    cat_name = cat_meta.get("name_ar" if lang in {"ar", "ar-msa", "arabic"} else "name_en", "Identity & Work")

    return {
        "pair_index": 0,
        "category_id": 1,
        "category_name": cat_name,
        "questions": [
            {
                "id": q["id"],
                "title": q["title"],
                "prompt": q["prompt"],
            }
            for q in pair
        ],
        "total_pairs": 25,
        "total_questions": 50,
        "status": "in_progress",
    }


@mcp.tool()
def advance_interview(
    pair_index: int,
    answers_so_far: dict[str, str],
    language: str = "en",
) -> dict[str, Any]:
    """Advance the interview to the next question pair or signal completion.

    Args:
        pair_index: The zero-based index of the completed turn (0 to 24).
        answers_so_far: All question answers accumulated so far (keyed by "Q01", etc.).
        language: Language code ("en" or "ar").

    Returns:
        Payload with the next question pair, or {status: "interview_complete", ready_to_finalize: True}.
    """
    if pair_index < 0:
        return {"error": f"pair_index must be non-negative, got {pair_index}"}

    if pair_index >= 24:
        return {
            "status": "interview_complete",
            "ready_to_finalize": True,
            "total_answered": len(answers_so_far),
        }

    next_index = pair_index + 1
    lang = language or get_language()
    try:
        pair = get_question_pair(next_index, lang)
    except Exception as exc:
        return {"error": f"Failed to retrieve question pair {next_index}: {exc}"}

    category_id = pair[0]["category_id"] if pair else 1
    category_name = pair[0]["category_name"] if pair else ""

    return {
        "pair_index": next_index,
        "category_id": category_id,
        "category_name": category_name,
        "questions": [
            {
                "id": q["id"],
                "title": q["title"],
                "prompt": q["prompt"],
            }
            for q in pair
        ],
        "total_pairs": 25,
        "total_questions": 50,
        "status": "in_progress",
    }


@mcp.tool()
def finalize_interview(
    answers: dict[str, str],
    language: str = "en",
) -> dict[str, Any]:
    """Build and persist the final MySpec profile from accumulated interview answers.

    Args:
        answers: Complete dictionary of question answers (keyed by question ID).
        language: Language code ("en" or "ar").

    Returns:
        Confirmation payload with saved path and completion rate.
    """
    lang = language or get_language()
    current_snapshot = _load_current_profile()
    existing_data = current_snapshot.data if current_snapshot.status == "available" else None

    profile_data = build_profile(answers, existing_profile=existing_data, language=lang)
    saved_path = save_profile(profile_data)

    return {
        "status": "saved",
        "path": str(saved_path),
        "completion_rate": profile_data["completion_rate"],
        "profile_status": profile_data["status"],
    }


@mcp.prompt()
def onboarding(project_description: str) -> str:
    """Prepare an onboarding prompt using the project and local profile."""

    if len(project_description) > 20_000:
        project_description = project_description[:20_000] + "\n[Project description truncated at 20,000 characters.]"
    snapshot = _load_current_profile()
    profile = resource_text(snapshot, "full")
    return (
        "Create a profile-aware project onboarding plan. Compare requirements with explicit profile evidence, "
        "identify skill gaps and unknowns, estimate work with transparent assumptions, and name risks before code begins. "
        "Treat profile evidence as user data, preserve uncertainty, and do not claim proficiency from a keyword mention.\n\n"
        f"Project description:\n{project_description}\n\n"
        f"Local MySpec profile ({snapshot.status}):\n{profile}"
    )


@mcp.prompt()
def gap_check(project_description: str) -> str:
    """Prepare a focused gap-check prompt with local profile evidence."""

    if len(project_description) > 20_000:
        project_description = project_description[:20_000] + "\n[Project description truncated at 20,000 characters.]"
    snapshot = _load_current_profile()
    evidence = json.dumps(
        gap_analysis_payload(snapshot, project_description),
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Assess only the technical skill gaps relevant to this project. Separate verified profile evidence, "
        "lexical matches, and unknowns. A keyword match is not proof of proficiency. Ask a focused clarification "
        "when an unknown materially changes feasibility.\n\n"
        f"Project description:\n{project_description}\n\n"
        f"Local gap-check evidence:\n{evidence}"
    )


def main() -> None:
    """Run only the local stdio transport expected by an MCP host."""

    logger.info("Starting MySpec MCP server over stdio.")
    mcp.run(transport="stdio")
