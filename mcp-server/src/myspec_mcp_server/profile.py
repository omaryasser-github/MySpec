"""Read-only loading, discovery precedence, migration, and persistence of the local MySpec profile."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .questions import CANONICAL_QUESTION_IDS, QUESTION_TO_TARGET_MODULES

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": "en", "english": "en", "ar": "ar", "msa": "ar", "ar-msa": "ar"}
MAX_PROFILE_BYTES = 2_000_000
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

MESSAGES = {
    "en": {
        "missing": "MySpec profile is missing.",
        "migration_required": "MySpec profile requires migration from legacy Markdown. Run 'myspec-mcp-server migrate' to create canonical profile.json.",
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
        "migration_required": "يتطلب ملف MySpec الترحيل من ملف Markdown القديم. شغّل 'myspec-mcp-server migrate' لإنشاء profile.json القياسي.",
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

# ---------------------------------------------------------------------------
# Canonical profile contract — Pydantic v2 model (Phase 13)
# ---------------------------------------------------------------------------

_VALID_QUESTION_IDS: frozenset[str] = frozenset(CANONICAL_QUESTION_IDS)

_VALID_DISPOSITION_SENTINELS: frozenset[str] = frozenset(
    {"__SKIPPED__", "__DECLINED__", "__UNKNOWN__", "__NA__", "__UNRESOLVED__"}
)


class MySpecProfile(BaseModel):
    """Canonical, versioned profile contract.

    ``extra="forbid"`` ensures no undocumented top-level keys are silently
    persisted. The seven module dicts are deliberately open (``dict[str, Any]``)
    because their nested content is determined by confirmed interview answers.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["complete", "partial", "stale"] = "partial"
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    output_preference: Literal["bilingual", "english_only", "arabic_only", "none"] = "english_only"
    language: str = "en"
    skipped_fields: list[str] = Field(default_factory=list)

    identity: dict[str, Any] = Field(default_factory=dict)
    current_skills: dict[str, Any] = Field(default_factory=dict)
    learning_in_progress: dict[str, Any] = Field(default_factory=dict)
    limitations: dict[str, Any] = Field(default_factory=dict)
    communication_prefs: dict[str, Any] = Field(default_factory=dict)
    work_context: dict[str, Any] = Field(default_factory=dict)
    growth_goals: dict[str, Any] = Field(default_factory=dict)

    @field_validator("completed_at", mode="after")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("completed_at must include a timezone offset")
        return value

    @field_validator("skipped_fields", mode="after")
    @classmethod
    def unique_skipped_fields(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("schema_version", mode="after")
    @classmethod
    def supported_version(cls, value: int) -> int:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"schema_version {value!r} is not supported. "
                f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        return value

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile to a plain dict suitable for JSON persistence."""
        raw = self.model_dump()
        raw["completed_at"] = self.completed_at.isoformat()
        return raw


class ProfileValidationError(ValueError):
    """Raised when profile data fails canonical model validation."""


class ProfileConfigurationError(ValueError):
    """Raised when profile path or config is invalid, malformed, or unsupported."""


class MigrationError(ValueError):
    """Raised when migration from legacy Markdown fails."""


@dataclass(frozen=True)
class MigrationResult:
    """Summary of a completed Markdown-to-JSON migration."""

    source: Path
    destination: Path
    archive: Path
    status: str
    completion_rate: float


def validate_profile_dict(data: dict[str, Any]) -> MySpecProfile:
    """Parse and validate a raw dict against the canonical profile model.

    Raises:
        ProfileValidationError: with a human-readable description of every
            constraint that was violated.
    """
    try:
        return MySpecProfile.model_validate(data)
    except ValidationError as exc:
        lines = [f"  * {err['loc']}: {err['msg']}" for err in exc.errors()]
        raise ProfileValidationError("Profile validation failed:\n" + "\n".join(lines)) from exc


# ---------------------------------------------------------------------------
# Answer validation helpers
# ---------------------------------------------------------------------------

def validate_answers(answers: dict[str, str]) -> list[str]:
    """Validate a dict of question-ID -> answer/disposition strings.

    Returns a list of human-readable error strings (empty when the answers
    are valid). Does NOT raise; callers decide whether to surface the errors.
    """
    errors: list[str] = []
    for raw_id, value in answers.items():
        q_id = raw_id.strip().upper()
        if q_id not in _VALID_QUESTION_IDS:
            errors.append(f"Unknown question ID {raw_id!r}. Expected Q01-Q50.")
            continue
        if value is None:
            errors.append(
                f"Answer for {q_id} is null; supply a string or a disposition sentinel "
                f"({', '.join(sorted(_VALID_DISPOSITION_SENTINELS))})."
            )
            continue
        if not isinstance(value, str):
            errors.append(
                f"Answer for {q_id} must be a string, got {type(value).__name__!r}."
            )
            continue
        if not value.strip():
            errors.append(
                f"Answer for {q_id} is empty or whitespace only. "
                "Use a disposition sentinel if the question is intentionally skipped."
            )
    return errors


def validate_pair_answers(pair_index: int, answers: dict[str, str]) -> list[str]:
    """Confirm both questions in the current pair have answers or explicit dispositions.

    pair_index 0 covers Q01/Q02, index 1 covers Q03/Q04, index 24 covers Q49/Q50.
    Returns error strings (empty when valid).
    """
    q_ids = [f"Q{(pair_index * 2) + i:02d}" for i in (1, 2)]
    errors: list[str] = []
    upper_answers = {k.strip().upper(): v for k, v in answers.items()}
    for q_id in q_ids:
        if q_id not in upper_answers:
            errors.append(
                f"Question {q_id} in pair {pair_index} has no answer. "
                "Provide a string answer or an explicit disposition sentinel before advancing."
            )
        else:
            val = upper_answers[q_id]
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(
                    f"Answer for {q_id} in pair {pair_index} is empty. "
                    "Provide a non-empty answer or an explicit disposition sentinel before advancing."
                )
    return errors


# ---------------------------------------------------------------------------
# ProfileSnapshot
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Path resolution precedence (Phase 14)
# CLI (--profile) -> MYSPEC_PROFILE_PATH -> ~/.myspec/config.json -> Default
# ---------------------------------------------------------------------------

_CLI_PROFILE_PATH: Path | None = None


def set_cli_profile_path(path: str | Path | None) -> None:
    """Set or clear the process-wide CLI-specified profile path."""
    global _CLI_PROFILE_PATH
    if path is None:
        _CLI_PROFILE_PATH = None
    else:
        _CLI_PROFILE_PATH = _validate_and_resolve_profile_path(path, "CLI --profile")


def get_cli_profile_path() -> Path | None:
    """Return the currently configured CLI profile path, if any."""
    return _CLI_PROFILE_PATH


def _validate_and_resolve_profile_path(raw_path: str | Path, source_name: str) -> Path:
    """Expand, resolve, and validate a canonical profile path.

    Canonical paths must resolve to a .json filename. A .md path is rejected
    with guidance to run migration.
    """
    if raw_path is None:
        raise ProfileConfigurationError(f"{source_name} cannot be None.")
    text = str(raw_path).strip()
    if not text:
        raise ProfileConfigurationError(f"{source_name} cannot be empty.")
    expanded = os.path.expandvars(os.path.expanduser(text))
    resolved = Path(expanded).resolve()

    suffix = resolved.suffix.lower()
    if suffix != ".json":
        if suffix == ".md":
            raise ProfileConfigurationError(
                f"{source_name} path '{raw_path}' specifies a legacy '.md' file. "
                "Canonical profiles must use '.json'. Run 'myspec-mcp-server migrate' "
                "to convert legacy Markdown profiles."
            )
        raise ProfileConfigurationError(
            f"{source_name} path '{raw_path}' must have a '.json' extension, got '{suffix or 'none'}'."
        )
    return resolved


def get_profile_path(
    environ: Mapping[str, str] | None = None,
    cli_path: str | Path | None = None,
    config_path: Path | None = None,
) -> Path:
    """Resolve the canonical profile path according to documented precedence:
    1. CLI (--profile)
    2. Environment variable (MYSPEC_PROFILE_PATH)
    3. MySpec config file (~/.myspec/config.json -> profile_path)
    4. Default (~/.myspec/profile.json)

    Raises:
        ProfileConfigurationError: If an explicit source provides an invalid,
            non-JSON, or malformed path/configuration. Higher-priority failures
            do not fall through to lower-priority sources.
    """
    # 1. CLI
    if cli_path is not None:
        return _validate_and_resolve_profile_path(cli_path, "CLI --profile")
    if _CLI_PROFILE_PATH is not None:
        return _CLI_PROFILE_PATH

    # 2. Environment
    env = os.environ if environ is None else environ
    override = env.get("MYSPEC_PROFILE_PATH", "").strip()
    if override:
        return _validate_and_resolve_profile_path(override, "MYSPEC_PROFILE_PATH")

    # 3. MySpec config file (~/.myspec/config.json)
    cfg_file = (
        config_path.expanduser().resolve()
        if config_path is not None
        else (Path.home() / ".myspec" / "config.json").resolve()
    )
    if cfg_file.exists():
        if not cfg_file.is_file():
            raise ProfileConfigurationError(f"Config path '{cfg_file}' is not a file.")
        try:
            cfg_text = cfg_file.read_text(encoding="utf-8")
            cfg_data = json.loads(cfg_text)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProfileConfigurationError(
                f"Malformed MySpec config file at '{cfg_file}': {exc}"
            ) from exc

        if not isinstance(cfg_data, dict):
            raise ProfileConfigurationError(
                f"MySpec config file at '{cfg_file}' must contain a JSON object."
            )

        if "profile_path" in cfg_data:
            val = cfg_data["profile_path"]
            if not isinstance(val, str) or not val.strip():
                raise ProfileConfigurationError(
                    f"'profile_path' in '{cfg_file}' must be a non-empty string."
                )
            return _validate_and_resolve_profile_path(val, f"Config file ({cfg_file})")

    # 4. Default
    return (Path.home() / ".myspec" / "profile.json").resolve()


def _extract_json_payload(text: str) -> str | None:
    """Return a fenced JSON payload, if one is present in a Markdown file."""
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def load_profile(path: Path | None = None) -> ProfileSnapshot:
    """Read canonical JSON profile and classify failures gracefully.

    JSON profiles must validate against the canonical MySpecProfile schema.
    Ordinary runtime reads never load Markdown files as profile context;
    if canonical JSON is missing but a legacy Markdown profile is found,
    the snapshot returns status 'migration_required'.
    """
    if path is not None:
        raw_p = Path(path).expanduser().resolve()
        if raw_p.suffix.lower() == ".md":
            return ProfileSnapshot(
                raw_p,
                "migration_required",
                detail="Markdown profiles must be migrated to JSON using 'myspec-mcp-server migrate'.",
                format="markdown",
            )
        try:
            resolved = _validate_and_resolve_profile_path(path, "load_profile path")
        except ProfileConfigurationError as exc:
            return ProfileSnapshot(raw_p, "unreadable", detail=str(exc))
    else:
        try:
            resolved = get_profile_path()
        except ProfileConfigurationError as exc:
            return ProfileSnapshot(Path("invalid-config.json"), "unreadable", detail=str(exc))

    try:
        if not resolved.exists():
            legacy_sibling = resolved.with_suffix(".md")
            default_legacy_md = (Path.home() / ".myspec" / "profile.md").resolve()
            if legacy_sibling.exists() or (
                resolved == (Path.home() / ".myspec" / "profile.json").resolve()
                and default_legacy_md.exists()
            ):
                return ProfileSnapshot(
                    resolved,
                    "migration_required",
                    detail="Legacy Markdown profile found. Run migration ('myspec-mcp-server migrate') to create canonical profile.json.",
                    format="markdown",
                )
            return ProfileSnapshot(resolved, "missing", detail="canonical profile.json does not exist")

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

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return ProfileSnapshot(
            resolved, "malformed", raw_text, format="json",
            detail=f"invalid JSON at line {exc.lineno}",
        )

    if not isinstance(parsed, dict):
        return ProfileSnapshot(
            resolved, "malformed", raw_text, format="json",
            detail="JSON profile root must be an object",
        )

    # Version check: reject unsupported schema versions.
    version = parsed.get("schema_version")
    if version is not None and version not in SUPPORTED_SCHEMA_VERSIONS:
        return ProfileSnapshot(
            resolved, "malformed", raw_text, format="json",
            detail=(
                f"unsupported schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            ),
        )

    # Validate against canonical Pydantic model
    try:
        validate_profile_dict(parsed)
    except ProfileValidationError as exc:
        return ProfileSnapshot(
            resolved, "malformed", raw_text, format="json",
            detail=f"Schema validation failed: {exc}",
        )

    return ProfileSnapshot(resolved, "available", raw_text, parsed, "json")



# ---------------------------------------------------------------------------
# Profile extraction helpers
# ---------------------------------------------------------------------------

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
    selected = [
        f"## {title}\n{body}"
        for title, body in sections
        if any(term in title.lower() for term in keywords)
    ]
    return "\n\n".join(selected) if selected else ""


def extract_skills(snapshot: ProfileSnapshot) -> str:
    if snapshot.status != "available":
        return ""
    if snapshot.data is None:
        return _markdown_view(
            snapshot,
            ("skill", "knowledge", "technology", "technologies", "tool", "stack",
             "مهار", "معرف", "تقني", "أدوات"),
        )
    modules: dict[str, Any] = {}
    for name in SKILL_MODULES:
        if name in snapshot.data and isinstance(snapshot.data[name], dict):
            modules[name] = snapshot.data[name]

    # Extract work_context entries whose *values* mention tool/stack/technology keywords.
    work_context = snapshot.data.get("work_context")
    if isinstance(work_context, dict):
        tool_entries: dict[str, Any] = {}
        for q_key, val in work_context.items():
            val_text = str(val).lower() if val is not None else ""
            if any(term in val_text for term in
                   ("tool", "stack", "technolog", "platform", "framework", "library")):
                tool_entries[q_key] = val
        if tool_entries:
            modules["work_context_tools"] = tool_entries

    return _json_block(modules) if modules else ""


def extract_preferences(snapshot: ProfileSnapshot) -> str:
    if snapshot.status != "available":
        return ""
    if snapshot.data is None:
        return _markdown_view(
            snapshot,
            ("communication", "preference", "style", "format", "تواصل", "تفضيل", "أسلوب"),
        )
    modules: dict[str, Any] = {}
    for key in ("communication_prefs", "output_preference"):
        if key in snapshot.data:
            modules[key] = snapshot.data[key]
    return _json_block(modules) if modules else ""


def _summary_content(snapshot: ProfileSnapshot) -> str:
    if snapshot.data is None:
        sections = _markdown_sections(snapshot.raw_text)
        return (
            "\n\n".join(f"## {title}\n{body}" for title, body in sections[:4])
            or snapshot.raw_text[:4000]
        )
    summary = {
        key: snapshot.data[key]
        for key in ("identity", "current_skills", "work_context", "growth_goals")
        if key in snapshot.data
    }
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


# ---------------------------------------------------------------------------
# Technology gap analysis
# ---------------------------------------------------------------------------

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
        pattern = rf"(?<![\\w]){re.escape(term)}(?![\\w])"
        valid_term_match = False
        for match in re.finditer(pattern, lowered):
            start, end = match.span()
            if not any(cs[0] <= start and end <= cs[1] for cs in claimed_spans):
                claimed_spans.append((start, end))
                valid_term_match = True
        if valid_term_match:
            matched_terms.add(term)

    return [term for term in TECH_TERMS if term in matched_terms]


def gap_analysis_payload(
    snapshot: ProfileSnapshot,
    project_description: str,
    language: str | None = None,
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Session planning
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Profile assembly
# ---------------------------------------------------------------------------

def build_profile(
    answers: dict[str, str],
    existing_profile: dict[str, Any] | None = None,
    language: str = "en",
    output_preference: str = "english_only",
) -> dict[str, Any]:
    """Transform collected interview answers into a canonical MySpec profile dict.

    The returned dict is validated against MySpecProfile before being returned.

    Args:
        answers: Mapping of question IDs (e.g. "Q01") to user responses or
            disposition sentinels.
        existing_profile: Optional previous profile dictionary for incremental
            updates.
        language: Language code ("en" or "ar").
        output_preference: One of bilingual, english_only, arabic_only, or none.

    Returns:
        Validated dict adhering to the canonical MySpec profile schema.

    Raises:
        ProfileValidationError: If the assembled profile violates the model.
    """
    valid_prefs = {"bilingual", "english_only", "arabic_only", "none"}
    norm_pref = output_preference.strip().lower() if output_preference else "english_only"
    if norm_pref not in valid_prefs:
        norm_pref = "english_only"

    if existing_profile:
        profile: dict[str, Any] = json.loads(json.dumps(existing_profile))
    else:
        profile = {
            "schema_version": 1,
            "status": "partial",
            "completion_rate": 0.0,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "language": language,
            "output_preference": norm_pref,
            "identity": {},
            "work_context": {},
            "communication_prefs": {},
            "current_skills": {},
            "learning_in_progress": {},
            "limitations": {},
            "growth_goals": {},
            "skipped_fields": [],
        }

    profile["language"] = language
    profile["output_preference"] = norm_pref

    skipped_set = set(profile.get("skipped_fields", []))

    for raw_id, raw_answer in answers.items():
        q_id = raw_id.strip().upper()
        answer_text = str(raw_answer).strip() if raw_answer is not None else ""

        if not answer_text or answer_text in _VALID_DISPOSITION_SENTINELS:
            skipped_set.add(q_id)
            for module_name in QUESTION_TO_TARGET_MODULES.get(q_id, []):
                if module_name not in profile or not isinstance(profile[module_name], dict):
                    profile[module_name] = {}
                profile[module_name][q_id] = answer_text or "__SKIPPED__"
        else:
            skipped_set.discard(q_id)
            for module_name in QUESTION_TO_TARGET_MODULES.get(q_id, []):
                if module_name not in profile or not isinstance(profile[module_name], dict):
                    profile[module_name] = {}
                profile[module_name][q_id] = answer_text

    profile["skipped_fields"] = sorted(skipped_set)

    all_answered_ids: set[str] = set()
    for mod in CONTEXT_MODULES:
        mod_dict = profile.get(mod)
        if isinstance(mod_dict, dict):
            for q_k, val in mod_dict.items():
                val_str = str(val).strip() if val is not None else ""
                if val_str and val_str not in _VALID_DISPOSITION_SENTINELS:
                    all_answered_ids.add(q_k)

    answered_count = len(all_answered_ids)
    completion_rate = round(min(answered_count / 50.0, 1.0), 2)
    profile["completion_rate"] = completion_rate
    profile["status"] = "complete" if completion_rate >= 1.0 else "partial"
    profile["completed_at"] = datetime.now(timezone.utc).isoformat()

    validate_profile_dict(profile)
    return profile


# ---------------------------------------------------------------------------
# Atomic Persistence (Phase 14)
# ---------------------------------------------------------------------------

def save_profile(profile_data: dict[str, Any], target_path: Path | None = None) -> Path:
    """Atomically save profile data to disk in canonical JSON format.

    Validates the supplied data against the canonical MySpecProfile model
    before writing. The destination file is never touched on a validation failure.
    Uses a temporary file in the same directory with flush and fsync, then
    atomically replaces the destination.

    Args:
        profile_data: The profile dictionary to persist.
        target_path: Optional destination path; defaults to get_profile_path().

    Returns:
        Path to the saved profile.json.

    Raises:
        ProfileValidationError: If profile_data fails canonical validation.
        ProfileConfigurationError: If target_path is not a valid JSON path.
        OSError: If filesystem operations fail.
    """
    validate_profile_dict(profile_data)

    if target_path is not None:
        destination_path = _validate_and_resolve_profile_path(target_path, "target_path")
    else:
        destination_path = get_profile_path()

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination_path.with_name(f".{destination_path.name}.{os.getpid()}.tmp")

    payload = json.dumps(profile_data, indent=2, ensure_ascii=False)
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, destination_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

    return destination_path


# ---------------------------------------------------------------------------
# Legacy Markdown Migration (Phase 14)
# ---------------------------------------------------------------------------

def _parse_legacy_markdown_to_profile(raw_text: str) -> dict[str, Any]:
    """Deterministically map legacy Markdown sections to canonical profile modules."""
    sections = _markdown_sections(raw_text)
    if not sections:
        raise MigrationError("Legacy Markdown contains no headings or structured sections.")

    modules: dict[str, dict[str, Any]] = {mod: {} for mod in CONTEXT_MODULES}

    title_to_module = [
        (("identity", "role", "who am i", "about", "هوية", "تعريف"), "identity"),
        (("current skill", "skill", "technolog", "tech stack", "stack", "tool", "مهار", "تقني"), "current_skills"),
        (("learning in progress", "learning", "study", "قيد التعلم", "تعلم"), "learning_in_progress"),
        (("limitation", "constraint", "weakness", "not familiar", "قيود", "حدود"), "limitations"),
        (("communication", "preference", "style", "feedback", "تواصل", "تفضيل"), "communication_prefs"),
        (("work context", "context", "environment", "domain", "سياق العمل", "بيئة العمل"), "work_context"),
        (("growth goal", "goal", "aspiration", "future", "أهداف", "نمو"), "growth_goals"),
    ]

    for title, body in sections:
        norm_title = title.lower()
        target_mod: str | None = None
        for keywords, mod_name in title_to_module:
            if any(k in norm_title for k in keywords):
                target_mod = mod_name
                break

        if target_mod is None:
            # Skip unrecognized high-level wrapper titles like "Developer Profile"
            continue

        for line in body.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            if line_str.startswith(("-", "*")):
                line_str = line_str.lstrip("-*").strip()

            if ":" in line_str:
                k, v = line_str.split(":", 1)
                k = k.strip()
                v = v.strip()
                if k and v:
                    modules[target_mod][k] = v
            elif line_str:
                modules[target_mod][line_str] = "mentioned"

    has_content = any(len(v) > 0 for v in modules.values())
    if not has_content:
        raise MigrationError("No structured profile fields could be extracted from legacy Markdown.")

    active_modules = sum(1 for m in CONTEXT_MODULES if len(modules[m]) > 0)
    completion_rate = round(min(active_modules / 7.0, 1.0), 2)

    return {
        "schema_version": 1,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if completion_rate >= 1.0 else "partial",
        "completion_rate": completion_rate,
        "output_preference": "english_only",
        "language": "ar" if any("\u0600" <= c <= "\u06ff" for c in raw_text) else "en",
        "skipped_fields": [],
        "identity": modules["identity"],
        "current_skills": modules["current_skills"],
        "learning_in_progress": modules["learning_in_progress"],
        "limitations": modules["limitations"],
        "communication_prefs": modules["communication_prefs"],
        "work_context": modules["work_context"],
        "growth_goals": modules["growth_goals"],
    }


def migrate_markdown_profile(
    source_path: Path | str | None = None,
    dest_path: Path | str | None = None,
) -> MigrationResult:
    """Perform a one-time migration of a legacy Markdown profile to canonical JSON.

    1. Selects destination via precedence (dest_path -> CLI -> MYSPEC_PROFILE_PATH -> config -> default).
    2. Refuses to overwrite an existing canonical JSON profile.
    3. Selects source (explicit source_path or default legacy location).
    4. Deterministically parses legacy Markdown.
    5. Validates converted data against canonical MySpecProfile.
    6. Creates a recoverable archive backup (.bak) of the source Markdown.
    7. Atomically saves the validated JSON.

    Returns:
        MigrationResult summary.

    Raises:
        MigrationError: If source is missing/empty, destination exists, or validation fails.
    """
    # 1. Destination
    if dest_path is not None:
        destination = _validate_and_resolve_profile_path(dest_path, "Migration destination")
    else:
        destination = get_profile_path()

    # 2. Refuse overwrite
    if destination.exists():
        raise MigrationError(
            f"Destination canonical profile already exists at '{destination}'. "
            "Migration will not overwrite existing canonical JSON."
        )

    # 3. Source selection
    if source_path is not None:
        expanded_src = os.path.expandvars(os.path.expanduser(str(source_path)))
        source = Path(expanded_src).resolve()
    else:
        sibling_md = destination.with_suffix(".md")
        default_md = (Path.home() / ".myspec" / "profile.md").resolve()
        if sibling_md.exists():
            source = sibling_md
        elif default_md.exists():
            source = default_md
        else:
            raise MigrationError(
                f"No legacy Markdown profile found. Checked '{sibling_md}' and '{default_md}'."
            )

    if not source.exists():
        raise MigrationError(f"Legacy Markdown source does not exist: '{source}'.")
    if not source.is_file():
        raise MigrationError(f"Legacy Markdown source is not a file: '{source}'.")

    # 4. Read source
    try:
        raw_text = source.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise MigrationError(f"Could not read legacy Markdown source at '{source}': {exc}") from exc

    if not raw_text:
        raise MigrationError(f"Legacy Markdown profile at '{source}' is empty.")

    # 5. Parse
    json_payload = _extract_json_payload(raw_text)
    if json_payload is not None:
        try:
            converted = json.loads(json_payload)
        except json.JSONDecodeError as exc:
            raise MigrationError(
                f"Fenced JSON in legacy Markdown at '{source}' is malformed: {exc}"
            ) from exc
    else:
        converted = _parse_legacy_markdown_to_profile(raw_text)

    # 6. Validate
    try:
        validated = validate_profile_dict(converted)
    except ProfileValidationError as exc:
        raise MigrationError(
            f"Converted profile from '{source}' failed schema validation:\n{exc}"
        ) from exc

    # 7. Create archive copy
    archive_path = source.with_name(f"{source.name}.bak")
    if archive_path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive_path = source.with_name(f"{source.name}.{ts}.bak")

    try:
        shutil.copy2(source, archive_path)
    except OSError as exc:
        raise MigrationError(f"Failed to create archive backup of '{source}': {exc}") from exc

    # 8. Atomically save canonical JSON
    try:
        save_profile(validated.to_dict(), destination)
    except Exception as exc:
        raise MigrationError(f"Failed to persist canonical JSON to '{destination}': {exc}") from exc

    return MigrationResult(
        source=source,
        destination=destination,
        archive=archive_path,
        status="migrated",
        completion_rate=validated.completion_rate,
    )

