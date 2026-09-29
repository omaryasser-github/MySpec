"""Read-only loading and focused extraction of the local MySpec profile."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": "en", "english": "en", "ar": "ar", "msa": "ar", "ar-msa": "ar"}
MAX_PROFILE_BYTES = 2_000_000

MESSAGES = {
    "en": {
        "missing": "MySpec profile is missing.",
        "unreadable": "MySpec profile could not be read.",
        "malformed": "MySpec profile is empty or malformed.",
        "summary": "MySpec profile summary",
        "skills": "MySpec skills and learning context",
        "preferences": "MySpec communication preferences",
        "full": "Full MySpec profile",
        "no_extract": "No matching structured profile content was found.",
        "gap_title": "Local project-to-profile evidence",
        "plan_title": "Personalized pre-flight learning plan",
        "agenda": [
            "Clarify the outcome and success check",
            "Connect the topic to existing profile evidence",
            "Study the highest-priority concepts",
            "Practice on a small, relevant example",
            "Review takeaways and identify the next step",
        ],
        "no_profile_warning": "Profile context is unavailable; avoid personalized proficiency claims.",
        "assessment_guidance": "Classify skill levels from the supplied profile evidence; lexical matches are mentions, not proficiency proof.",
    },
    "ar": {
        "missing": "ملف MySpec غير موجود.",
        "unreadable": "تعذرت قراءة ملف MySpec.",
        "malformed": "ملف MySpec فارغ أو غير صالح.",
        "summary": "ملخص ملف MySpec",
        "skills": "مهارات MySpec وسياق التعلم",
        "preferences": "تفضيلات التواصل في MySpec",
        "full": "ملف MySpec الكامل",
        "no_extract": "لم يُعثر على محتوى منظم مطابق في الملف.",
        "gap_title": "أدلة محلية لمقارنة المشروع بالملف",
        "plan_title": "خطة تعلم تمهيدية مخصصة",
        "agenda": [
            "تحديد النتيجة ومعيار النجاح",
            "ربط الموضوع بالأدلة الموجودة في الملف",
            "دراسة المفاهيم ذات الأولوية الأعلى",
            "التدرب على مثال صغير وذي صلة",
            "مراجعة الخلاصات وتحديد الخطوة التالية",
        ],
        "no_profile_warning": "سياق الملف غير متاح؛ تجنب ادعاءات مخصصة عن مستوى الإتقان.",
        "assessment_guidance": "صنّف مستوى المهارة استنادًا إلى أدلة الملف؛ فالتطابق اللفظي ذكرٌ للمهارة وليس دليلًا على إتقانها.",
    },
}

SKILL_MODULES = ("current_skills", "learning_in_progress", "limitations")
CONTEXT_MODULES = (
    "identity",
    "current_skills",
    "learning_in_progress",
    "limitations",
    "communication_prefs",
    "work_context",
    "growth_goals",
)


@dataclass(frozen=True)
class ProfileSnapshot:
    """One request-scoped view of the configured local profile."""

    path: Path
    status: str
    raw_text: str = ""
    data: dict[str, Any] | None = None
    format: str = "unknown"
    detail: str = ""


def get_language(environ: Mapping[str, str] | None = None) -> str:
    """Return the supported UI language, defaulting safely to English."""

    env = os.environ if environ is None else environ
    configured = env.get("MYSPEC_LANG", DEFAULT_LANGUAGE).strip().lower()
    return SUPPORTED_LANGUAGES.get(configured, DEFAULT_LANGUAGE)


def get_profile_path(environ: Mapping[str, str] | None = None) -> Path:
    """Resolve the configured profile path without creating or modifying it.

    Checks MYSPEC_PROFILE_PATH first, then ~/.myspec/profile.md, falling back
    automatically to ~/.myspec/profile.json if profile.md is absent.
    """

    env = os.environ if environ is None else environ
    override = env.get("MYSPEC_PROFILE_PATH", "").strip()
    if override:
        expanded = os.path.expandvars(os.path.expanduser(override))
        return Path(expanded).resolve()

    default_md = (Path.home() / ".myspec" / "profile.md").resolve()
    default_json = (Path.home() / ".myspec" / "profile.json").resolve()
    if not default_md.exists() and default_json.exists():
        return default_json
    return default_md


def _extract_json_payload(text: str) -> str | None:
    """Return a fenced JSON payload, if one is present in a Markdown file."""

    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def load_profile(path: Path | None = None) -> ProfileSnapshot:
    """Read Markdown or JSON profile text and classify failures gracefully."""

    resolved = get_profile_path() if path is None else path.expanduser().resolve()
    try:
        if not resolved.exists():
            return ProfileSnapshot(resolved, "missing", detail="file does not exist")
        if not resolved.is_file():
            return ProfileSnapshot(resolved, "unreadable", detail="configured path is not a file")
        if resolved.stat().st_size > MAX_PROFILE_BYTES:
            return ProfileSnapshot(resolved, "malformed", detail="profile exceeds the 2 MB read limit")
        raw_text = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return ProfileSnapshot(resolved, "unreadable", detail=type(exc).__name__)

    stripped = raw_text.strip()
    if not stripped:
        return ProfileSnapshot(resolved, "malformed", raw_text, detail="file is empty")

    json_payload = stripped if stripped.startswith("{") else _extract_json_payload(stripped)
    if resolved.suffix.lower() == ".json" and json_payload is None:
        json_payload = stripped
    if json_payload is not None:
        try:
            parsed = json.loads(json_payload)
        except json.JSONDecodeError as exc:
            return ProfileSnapshot(resolved, "malformed", raw_text, format="json", detail=f"invalid JSON at line {exc.lineno}")
        if not isinstance(parsed, dict):
            return ProfileSnapshot(resolved, "malformed", raw_text, format="json", detail="JSON profile root must be an object")
        return ProfileSnapshot(resolved, "available", raw_text, parsed, "json")

    return ProfileSnapshot(resolved, "available", raw_text, None, "markdown")


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    """Parse Markdown text into sections, respecting code blocks and header hierarchy."""

    sections: list[tuple[str, str]] = []
    current_title = "Profile"
    current_lines: list[str] = []
    in_code_block = False
    header_stack: list[tuple[int, str]] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if not in_code_block and line.lstrip().startswith("#"):
            hashes = len(line.lstrip()) - len(line.lstrip().lstrip("#"))
            title_text = line.lstrip()[hashes:].strip()

            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_title, body))
                current_lines = []

            while header_stack and header_stack[-1][0] >= hashes:
                header_stack.pop()
            header_stack.append((hashes, title_text))

            if len(header_stack) > 1:
                current_title = " - ".join(h[1] for h in header_stack if h[1])
            else:
                current_title = title_text
        else:
            current_lines.append(line)

    body = "\n".join(current_lines).strip()
    if body:
        sections.append((current_title, body))

    return sections


def _markdown_view(snapshot: ProfileSnapshot, keywords: tuple[str, ...]) -> str:
    sections = _markdown_sections(snapshot.raw_text)
    selected = [f"## {title}\n{body}" for title, body in sections if any(term in title.lower() for term in keywords)]
    if selected:
        return "\n\n".join(selected)
    return ""


def extract_skills(snapshot: ProfileSnapshot) -> str:
    if snapshot.status != "available":
        return ""
    if snapshot.data is None:
        return _markdown_view(
            snapshot,
            ("skill", "knowledge", "technology", "technologies", "tool", "stack", "مهار", "معرف", "تقني", "أدوات"),
        )
    modules = {name: snapshot.data.get(name, {}) for name in SKILL_MODULES if name in snapshot.data}
    work_context = snapshot.data.get("work_context")
    if isinstance(work_context, dict):
        tools = {key: value for key, value in work_context.items() if any(term in key.lower() for term in ("tool", "stack", "technology", "platform"))}
        if tools:
            modules["work_context_tools"] = tools
    return _json_block(modules) if modules else ""


def extract_preferences(snapshot: ProfileSnapshot) -> str:
    if snapshot.status != "available":
        return ""
    if snapshot.data is None:
        return _markdown_view(
            snapshot,
            ("communication", "preference", "style", "format", "تواصل", "تفضيل", "أسلوب"),
        )
    modules = {}
    for key in ("communication_prefs", "output_preference"):
        if key in snapshot.data:
            modules[key] = snapshot.data[key]
    return _json_block(modules) if modules else ""


def _summary_content(snapshot: ProfileSnapshot) -> str:
    if snapshot.data is None:
        sections = _markdown_sections(snapshot.raw_text)
        return "\n\n".join(f"## {title}\n{body}" for title, body in sections[:4]) or snapshot.raw_text[:4000]
    summary = {key: snapshot.data[key] for key in ("identity", "current_skills", "work_context", "growth_goals") if key in snapshot.data}
    metadata = {key: snapshot.data[key] for key in ("status", "completion_rate") if key in snapshot.data}
    if metadata:
        summary["profile_status"] = metadata
    return _json_block(summary) if summary else ""


def resource_text(snapshot: ProfileSnapshot, view: str, language: str | None = None) -> str:
    """Format one of the four resource views without exposing parser errors."""

    lang = language or get_language()
    messages = MESSAGES[lang]
    title = messages.get(view, messages["summary"])
    if snapshot.status != "available":
        status_message = messages.get(snapshot.status, messages["malformed"])
        detail = f"\n{snapshot.detail}" if snapshot.detail else ""
        return f"{title}\n\n{status_message}{detail}"

    if view == "full":
        return f"{title}\n\n{snapshot.raw_text}"
    if view == "skills":
        body = extract_skills(snapshot)
    elif view == "preferences":
        body = extract_preferences(snapshot)
    else:
        body = _summary_content(snapshot)
    return f"{title}\n\n{body or messages['no_extract']}"


TECH_TERMS = (
    "react native", "javascript", "typescript", "postgresql", "kubernetes", "graphql",
    "fastapi", "next.js", "node.js", "express", "django", "flask", "angular", "svelte",
    "mongodb", "sqlite", "redis", "terraform", "playwright", "pytest", "docker",
    "python", "react", "vue", "rust", "golang", "java", "aws", "azure", "gcp",
    "rest", "git", "ci/cd",
)


def find_technology_terms(text: str) -> list[str]:
    """Find a small, explicit built-in vocabulary without network lookups or substring collisions."""

    lowered = text.lower()
    terms_by_length = sorted(TECH_TERMS, key=len, reverse=True)
    claimed_spans: list[tuple[int, int]] = []
    matched_terms: set[str] = set()

    for term in terms_by_length:
        pattern = rf"(?<![\w]){re.escape(term)}(?![\w])"
        valid_term_match = False
        for match in re.finditer(pattern, lowered):
            start, end = match.span()
            if not any(cs[0] <= start and end <= cs[1] for cs in claimed_spans):
                claimed_spans.append((start, end))
                valid_term_match = True
        if valid_term_match:
            matched_terms.add(term)

    return [term for term in TECH_TERMS if term in matched_terms]


def gap_analysis_payload(snapshot: ProfileSnapshot, project_description: str, language: str | None = None) -> dict[str, Any]:
    """Return local evidence and lexical matches for host-assisted analysis."""

    lang = language or get_language()
    skill_context = extract_skills(snapshot)
    project_terms = find_technology_terms(project_description)
    profile_terms = find_technology_terms(skill_context)
    overlap = [term for term in project_terms if term in profile_terms]
    missing_mentions = [term for term in project_terms if term not in profile_terms]
    return {
        "profile_status": snapshot.status,
        "profile_format": snapshot.format,
        "profile_source": "configured local file",
        "language": lang,
        "project_description": project_description,
        "profile_skill_context": skill_context or MESSAGES[lang]["no_extract"],
        "technology_terms_in_project": project_terms,
        "terms_mentioned_in_both": overlap,
        "project_terms_without_profile_mention": missing_mentions,
        "interpretation_note": (
            "Lexical overlap indicates a profile mention only; inspect the evidence and classify proficiency "
            "before recommending a learning path."
        ),
        "assessment_guidance": MESSAGES[lang]["assessment_guidance"],
        "profile_warning": MESSAGES[lang]["no_profile_warning"] if snapshot.status != "available" else None,
    }


def allocate_minutes(total: int) -> list[int]:
    """Distribute a session duration across five weighted stages, enforcing a minimum of 5 minutes."""

    if total < 5:
        total = 5

    weights = (10, 15, 40, 25, 10)
    allocated = [1] * len(weights)
    remaining = total - len(weights)
    raw = [remaining * weight / 100 for weight in weights]
    weighted_minutes = [int(value) for value in raw]
    remainder = remaining - sum(weighted_minutes)
    order = sorted(range(len(weights)), key=lambda idx: (raw[idx] - int(raw[idx]), -idx), reverse=True)
    for idx in order[:remainder]:
        weighted_minutes[idx] += 1
    allocated = [base + weighted for base, weighted in zip(allocated, weighted_minutes)]
    return allocated
