"""Canonical Question Bank Engine for MySpec.

Provides strict parsing, schema validation, path-sensitive caching,
and pair extraction for canonical English and Arabic question banks.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "Question",
    "QuestionModel",
    "QuestionBankError",
    "QuestionFileNotFoundError",
    "QuestionParseError",
    "QuestionValidationError",
    "QuestionLanguageError",
    "CANONICAL_QUESTION_IDS",
    "CATEGORIES_METADATA",
    "QUESTION_TO_CATEGORY",
    "QUESTION_TO_TARGET_MODULES",
    "get_questions_root",
    "clear_question_cache",
    "parse_question_file",
    "load_category_questions",
    "load_all_questions",
    "get_question_pair",
    "validate_bank_parity",
]


class QuestionBankError(Exception):
    """Base exception for all question bank loading and validation errors."""


class QuestionFileNotFoundError(QuestionBankError, FileNotFoundError):
    """Raised when questions root, directory, or category file does not exist."""


class QuestionParseError(QuestionBankError):
    """Raised when a Markdown question block or file structure is malformed."""


class QuestionValidationError(QuestionBankError):
    """Raised when question records or bank-level completeness/parity checks fail."""


class QuestionLanguageError(QuestionBankError, ValueError):
    """Raised when an unsupported language code is provided."""


class Question(TypedDict):
    id: str
    category_id: int
    category_name: str
    title: str
    prompt: str
    language: str
    target_modules: list[str]


class QuestionModel(BaseModel):
    """Strict Pydantic model for record-level question validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., pattern=r"^Q\d{2}$")
    category_id: int = Field(..., ge=1, le=7)
    category_name: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    language: Literal["en", "ar"]
    target_modules: list[str] = Field(..., min_length=1)

    @field_validator("title", "prompt", mode="after")
    @classmethod
    def reject_blank_strings(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field must not be empty or whitespace only")
        return trimmed

    def to_question(self) -> Question:
        return Question(
            id=self.id,
            category_id=self.category_id,
            category_name=self.category_name,
            title=self.title,
            prompt=self.prompt,
            language=self.language,
            target_modules=list(self.target_modules),
        )


CATEGORIES_METADATA: dict[int, dict[str, Any]] = {
    1: {
        "name_en": "Identity & Work",
        "name_ar": "الهوية والعمل",
        "file_en": "01-identity-work.md",
        "file_ar": "01-identity-work_MSA.md",
        "id_range": (1, 10),
        "target_modules": ["identity", "work_context"],
    },
    2: {
        "name_en": "Communication Style",
        "name_ar": "أسلوب التواصل",
        "file_en": "02-communication-style.md",
        "file_ar": "02-communication-style_MSA.md",
        "id_range": (11, 18),
        "target_modules": ["communication_prefs"],
    },
    3: {
        "name_en": "Knowledge & Skills",
        "name_ar": "المعرفة والمهارات",
        "file_en": "03-knowledge-and-skills.md",
        "file_ar": "03-knowledge-and-skills_MSA.md",
        "id_range": (19, 25),
        "target_modules": ["current_skills", "learning_in_progress", "limitations"],
    },
    4: {
        "name_en": "Tools & Workflows",
        "name_ar": "الأدوات وسير العمل",
        "file_en": "04-tools-and-workflows.md",
        "file_ar": "04-tools-and-workflows_MSA.md",
        "id_range": (26, 32),
        "target_modules": ["current_skills", "work_context", "limitations"],
    },
    5: {
        "name_en": "Decision-Making",
        "name_ar": "صنع القرار",
        "file_en": "05-decision-making.md",
        "file_ar": "05-decision-making_MSA.md",
        "id_range": (33, 38),
        "target_modules": ["limitations", "communication_prefs", "work_context"],
    },
    6: {
        "name_en": "Goals & Priorities",
        "name_ar": "الأهداف والأولويات",
        "file_en": "06-goals-and-priorities.md",
        "file_ar": "06-goals-and-priorities_MSA.md",
        "id_range": (39, 44),
        "target_modules": ["growth_goals", "work_context"],
    },
    7: {
        "name_en": "Personal Context",
        "name_ar": "السياق الشخصي",
        "file_en": "07-personal-context.md",
        "file_ar": "07-personal-context_MSA.md",
        "id_range": (45, 50),
        "target_modules": ["work_context", "communication_prefs", "limitations"],
    },
}

CANONICAL_QUESTION_IDS: tuple[str, ...] = tuple(f"Q{i:02d}" for i in range(1, 51))

QUESTION_TO_CATEGORY: dict[str, int] = {}
QUESTION_TO_TARGET_MODULES: dict[str, list[str]] = {}
for _cat_id, _meta in CATEGORIES_METADATA.items():
    _start, _end = _meta["id_range"]
    for _num in range(_start, _end + 1):
        _qid = f"Q{_num:02d}"
        QUESTION_TO_CATEGORY[_qid] = _cat_id
        QUESTION_TO_TARGET_MODULES[_qid] = list(_meta["target_modules"])

_HEADER_PATTERN = re.compile(r"^##\s+Q(\d+):\s*(.+)$")
_EN_PROMPT_PATTERN = re.compile(r"^\*\*Question:\*\*\s*(.+)$")
_AR_PROMPT_PATTERN = re.compile(r"^\*\*السؤال:\*\*\s*(.+)$")


def get_questions_root() -> Path:
    """Resolve the canonical questions root directory.

    Checks MYSPEC_QUESTIONS_PATH environment variable override.
    Falls back to package-relative path: <package_root>/../../../questions
    Always returns a fully resolved absolute Path.
    """
    env_override = os.environ.get("MYSPEC_QUESTIONS_PATH", "").strip()
    if env_override:
        return Path(env_override).expanduser().resolve()
    return (Path(__file__).resolve().parents[3] / "questions").resolve()


def _normalize_language(lang: str) -> str:
    cleaned = (lang or "").strip().lower()
    if cleaned in {"en", "english"}:
        return "en"
    if cleaned in {"ar", "ar-msa", "arabic", "msa"}:
        return "ar"
    raise QuestionLanguageError(
        f"Unsupported language code: {lang!r}. Supported values are 'en'/'english' and 'ar'/'arabic'/'ar-msa'."
    )


def parse_question_file(file_path: Path, category_id: int, lang: str = "en") -> list[Question]:
    """Parse a single category markdown file into a list of Question objects.

    Raises:
        QuestionFileNotFoundError: if file_path does not exist.
        QuestionParseError: if markdown format is invalid or has incomplete blocks.
        QuestionValidationError: if parsed IDs don't match expected category range or are duplicated.
    """
    norm_lang = _normalize_language(lang)
    if category_id not in CATEGORIES_METADATA:
        raise ValueError(f"Invalid category_id: {category_id}. Expected 1-7.")

    resolved_path = file_path.expanduser().resolve()
    if not resolved_path.exists():
        raise QuestionFileNotFoundError(f"Question file not found: {resolved_path}")
    if not resolved_path.is_file():
        raise QuestionFileNotFoundError(f"Question path is not a file: {resolved_path}")

    try:
        text = resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise QuestionParseError(f"Invalid UTF-8 encoding in {resolved_path}: {exc}") from exc
    except OSError as exc:
        raise QuestionParseError(f"Failed to read question file {resolved_path}: {exc}") from exc

    metadata = CATEGORIES_METADATA[category_id]
    category_name = metadata["name_ar"] if norm_lang == "ar" else metadata["name_en"]
    target_modules = metadata["target_modules"]
    expected_start, expected_end = metadata["id_range"]
    expected_ids = [f"Q{n:02d}" for n in range(expected_start, expected_end + 1)]

    lines = text.splitlines()
    questions: list[Question] = []
    seen_ids: set[str] = set()

    current_id: str | None = None
    current_title: str | None = None
    current_prompt: str | None = None
    current_header_line: int | None = None

    def commit_current(line_idx: int):
        nonlocal current_id, current_title, current_prompt, current_header_line
        if current_id is not None:
            if current_prompt is None:
                raise QuestionParseError(
                    f"Malformed question block {current_id} in {resolved_path}:{current_header_line}: "
                    f"missing question prompt before line {line_idx}"
                )
            if not current_title:
                raise QuestionParseError(
                    f"Empty question title for {current_id} in {resolved_path}:{current_header_line}"
                )
            if current_id in seen_ids:
                raise QuestionValidationError(
                    f"Duplicate question ID {current_id} in {resolved_path}:{current_header_line}"
                )

            try:
                model = QuestionModel(
                    id=current_id,
                    category_id=category_id,
                    category_name=category_name,
                    title=current_title,
                    prompt=current_prompt,
                    language=norm_lang,  # type: ignore[arg-type]
                    target_modules=list(target_modules),
                )
            except Exception as exc:
                raise QuestionValidationError(
                    f"Validation failed for question {current_id} in {resolved_path}:{current_header_line}: {exc}"
                ) from exc

            questions.append(model.to_question())
            seen_ids.add(current_id)

        current_id = None
        current_title = None
        current_prompt = None
        current_header_line = None

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for heading
        header_match = _HEADER_PATTERN.match(stripped)
        if header_match:
            commit_current(line_no)
            q_num = int(header_match.group(1))
            current_id = f"Q{q_num:02d}"
            current_title = header_match.group(2).strip()
            current_prompt = None
            current_header_line = line_no
            continue

        # Check for prompt
        if norm_lang == "ar":
            ar_match = _AR_PROMPT_PATTERN.match(stripped)
            if ar_match:
                if current_id is None:
                    raise QuestionParseError(
                        f"Unexpected question prompt without heading in {resolved_path}:{line_no}"
                    )
                if current_prompt is not None:
                    raise QuestionParseError(
                        f"Duplicate question prompt for {current_id} in {resolved_path}:{line_no}"
                    )
                prompt_text = ar_match.group(1).strip()
                if not prompt_text:
                    raise QuestionParseError(
                        f"Empty question prompt for {current_id} in {resolved_path}:{line_no}"
                    )
                current_prompt = prompt_text
                continue
        else:
            en_match = _EN_PROMPT_PATTERN.match(stripped)
            if en_match:
                if current_id is None:
                    raise QuestionParseError(
                        f"Unexpected question prompt without heading in {resolved_path}:{line_no}"
                    )
                if current_prompt is not None:
                    raise QuestionParseError(
                        f"Duplicate question prompt for {current_id} in {resolved_path}:{line_no}"
                    )
                prompt_text = en_match.group(1).strip()
                if not prompt_text:
                    raise QuestionParseError(
                        f"Empty question prompt for {current_id} in {resolved_path}:{line_no}"
                    )
                current_prompt = prompt_text
                continue

    # Commit the last block
    commit_current(len(lines) + 1)

    # Validate that parsed IDs match expected category range exactly
    actual_ids = [q["id"] for q in questions]
    if actual_ids != expected_ids:
        raise QuestionValidationError(
            f"Category {category_id} ID mismatch in {resolved_path}: expected {expected_ids}, got {actual_ids}"
        )

    return questions


def _validate_full_bank(assembled: dict[str, Question], lang: str, root: Path) -> None:
    expected_ids = set(CANONICAL_QUESTION_IDS)
    actual_ids = set(assembled.keys())

    missing = expected_ids - actual_ids
    unexpected = actual_ids - expected_ids
    if missing or unexpected:
        msg = f"Bank completeness validation failed for language '{lang}' in {root}:"
        if missing:
            msg += f" missing IDs: {sorted(missing)};"
        if unexpected:
            msg += f" unexpected IDs: {sorted(unexpected)};"
        raise QuestionValidationError(msg)

    if len(assembled) != 50:
        raise QuestionValidationError(
            f"Expected exactly 50 questions for language '{lang}' in {root}, found {len(assembled)}"
        )


_CACHE: dict[tuple[Path, str], dict[str, Question]] = {}


def clear_question_cache() -> None:
    """Clear all in-process question cache entries."""
    _CACHE.clear()


def load_all_questions(lang: str = "en") -> dict[str, Question]:
    """Load and validate all 50 questions for a given language, keyed by question ID ("Q01".."Q50").

    Results are cached by (resolved_root, normalized_language). Returns a deep copy so
    mutations by callers do not poison the cached bank.
    """
    norm_lang = _normalize_language(lang)
    root = get_questions_root()
    cache_key = (root, norm_lang)

    if cache_key in _CACHE:
        return copy.deepcopy(_CACHE[cache_key])

    if not root.is_dir():
        raise QuestionFileNotFoundError(f"Questions root directory not found: {root}")

    lang_dir = "AR-MSA" if norm_lang == "ar" else "EN"
    lang_path = root / lang_dir
    if not lang_path.is_dir():
        raise QuestionFileNotFoundError(f"Language questions directory not found: {lang_path}")

    assembled: dict[str, Question] = {}
    for cat_id in sorted(CATEGORIES_METADATA.keys()):
        meta = CATEGORIES_METADATA[cat_id]
        filename = meta["file_ar"] if norm_lang == "ar" else meta["file_en"]
        file_path = lang_path / filename
        cat_questions = parse_question_file(file_path, cat_id, norm_lang)
        for q in cat_questions:
            if q["id"] in assembled:
                raise QuestionValidationError(
                    f"Duplicate question ID {q['id']} encountered in {file_path}"
                )
            assembled[q["id"]] = q

    _validate_full_bank(assembled, norm_lang, root)
    _CACHE[cache_key] = assembled
    return copy.deepcopy(assembled)


def load_category_questions(category_id: int, lang: str = "en") -> list[Question]:
    """Load questions for a specific category ID (1-7), enforcing full-bank validation."""
    norm_lang = _normalize_language(lang)
    if category_id not in CATEGORIES_METADATA:
        raise ValueError(f"Invalid category_id: {category_id}. Expected 1-7.")

    all_qs = load_all_questions(norm_lang)
    return [q for q in all_qs.values() if q["category_id"] == category_id]


def get_question_pair(pair_index: int, lang: str = "en") -> list[Question]:
    """Retrieve the pair of questions for a specific turn index (0-24).

    Index 0 returns [Q01, Q02].
    Index 24 returns [Q49, Q50].
    Raises:
        IndexError: if pair_index is out of range (< 0 or > 24).
        QuestionValidationError: if either question in the pair is missing.
    """
    if pair_index < 0 or pair_index >= 25:
        raise IndexError(f"pair_index {pair_index} out of range (expected 0 to 24).")

    all_questions = load_all_questions(lang)
    first_id = f"Q{(pair_index * 2) + 1:02d}"
    second_id = f"Q{(pair_index * 2) + 2:02d}"

    if first_id not in all_questions or second_id not in all_questions:
        raise QuestionValidationError(
            f"Question pair {pair_index} incomplete: expected {first_id} and {second_id} in bank"
        )

    return [all_questions[first_id], all_questions[second_id]]


def validate_bank_parity(root: Path | None = None) -> bool:
    """Validate that English and Arabic question banks in root expose identical canonical IDs.

    Returns True if valid; raises QuestionValidationError otherwise.
    """
    orig_env = os.environ.get("MYSPEC_QUESTIONS_PATH")
    try:
        if root is not None:
            os.environ["MYSPEC_QUESTIONS_PATH"] = str(root)
        en_bank = load_all_questions("en")
        ar_bank = load_all_questions("ar")
        en_ids = set(en_bank.keys())
        ar_ids = set(ar_bank.keys())
        if en_ids != ar_ids:
            raise QuestionValidationError(
                f"Bank parity mismatch between EN and AR: EN has {sorted(en_ids)}, AR has {sorted(ar_ids)}"
            )
        return True
    finally:
        if root is not None:
            if orig_env is not None:
                os.environ["MYSPEC_QUESTIONS_PATH"] = orig_env
            else:
                os.environ.pop("MYSPEC_QUESTIONS_PATH", None)
