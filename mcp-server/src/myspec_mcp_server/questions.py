from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TypedDict

__all__ = [
    "Question",
    "CATEGORIES_METADATA",
    "get_questions_root",
    "load_category_questions",
    "load_all_questions",
    "get_question_pair",
]


class Question(TypedDict):
    id: str
    category_id: int
    category_name: str
    title: str
    prompt: str
    language: str
    target_modules: list[str]


CATEGORIES_METADATA: dict[int, dict] = {
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

_HEADER_PATTERN = re.compile(r"^##\s+Q(\d+):\s*(.+)$")
_EN_PROMPT_PATTERN = re.compile(r"^\*\*Question:\*\*\s*(.+)$")
_AR_PROMPT_PATTERN = re.compile(r"^\*\*السؤال:\*\*\s*(.+)$")


def get_questions_root() -> Path:
    """Resolve the canonical questions root directory.

    Checks MYSPEC_QUESTIONS_PATH environment variable override.
    Falls back to package-relative path: <package_root>/../../../questions
    """
    env_override = os.environ.get("MYSPEC_QUESTIONS_PATH")
    if env_override:
        return Path(env_override).resolve()
    return Path(__file__).resolve().parents[3] / "questions"


def _normalize_language(lang: str) -> str:
    cleaned = (lang or "en").strip().lower()
    return "ar" if cleaned in {"ar", "ar-msa", "arabic"} else "en"


def parse_question_file(file_path: Path, category_id: int, lang: str = "en") -> list[Question]:
    """Parse a single category markdown file into a list of Question objects."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Question file not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    metadata = CATEGORIES_METADATA.get(category_id, {})
    category_name = metadata.get("name_ar" if lang == "ar" else "name_en", f"Category {category_id}")
    target_modules = metadata.get("target_modules", [])

    questions: list[Question] = []
    current_id: str | None = None
    current_title: str | None = None
    current_prompt: str | None = None

    def commit_current():
        nonlocal current_id, current_title, current_prompt
        if current_id and current_title and current_prompt:
            questions.append(
                Question(
                    id=current_id,
                    category_id=category_id,
                    category_name=category_name,
                    title=current_title.strip(),
                    prompt=current_prompt.strip(),
                    language=lang,
                    target_modules=list(target_modules),
                )
            )
        current_id = None
        current_title = None
        current_prompt = None

    for line in lines:
        stripped = line.strip()
        header_match = _HEADER_PATTERN.match(stripped)
        if header_match:
            commit_current()
            q_num = int(header_match.group(1))
            current_id = f"Q{q_num:02d}"
            current_title = header_match.group(2)
            continue

        if current_id is not None and current_prompt is None:
            if lang == "ar":
                ar_match = _AR_PROMPT_PATTERN.match(stripped)
                if ar_match:
                    current_prompt = ar_match.group(1)
                    continue
            en_match = _EN_PROMPT_PATTERN.match(stripped)
            if en_match:
                current_prompt = en_match.group(1)
                continue

    commit_current()
    return questions


def load_category_questions(category_id: int, lang: str = "en") -> list[Question]:
    """Load questions for a specific category ID (1-7)."""
    norm_lang = _normalize_language(lang)
    if category_id not in CATEGORIES_METADATA:
        raise ValueError(f"Invalid category_id: {category_id}. Expected 1-7.")

    meta = CATEGORIES_METADATA[category_id]
    lang_dir = "AR-MSA" if norm_lang == "ar" else "EN"
    filename = meta["file_ar"] if norm_lang == "ar" else meta["file_en"]

    file_path = get_questions_root() / lang_dir / filename
    return parse_question_file(file_path, category_id, norm_lang)


_CACHE: dict[str, dict[str, Question]] = {}


def load_all_questions(lang: str = "en") -> dict[str, Question]:
    """Load all 50 questions for a given language, keyed by question ID ("Q01".."Q50")."""
    norm_lang = _normalize_language(lang)
    if norm_lang in _CACHE:
        return _CACHE[norm_lang]

    result: dict[str, Question] = {}
    for cat_id in sorted(CATEGORIES_METADATA.keys()):
        for q in load_category_questions(cat_id, norm_lang):
            result[q["id"]] = q

    _CACHE[norm_lang] = result
    return result


def get_question_pair(pair_index: int, lang: str = "en") -> list[Question]:
    """Retrieve the pair of questions for a specific turn index (0-24).

    Index 0 returns [Q01, Q02].
    Index 24 returns [Q49, Q50].
    Raises IndexError if pair_index is out of range.
    """
    if pair_index < 0 or pair_index >= 25:
        raise IndexError(f"pair_index {pair_index} out of range (expected 0 to 24).")

    all_questions = load_all_questions(lang)
    first_id = f"Q{(pair_index * 2) + 1:02d}"
    second_id = f"Q{(pair_index * 2) + 2:02d}"

    pair: list[Question] = []
    if first_id in all_questions:
        pair.append(all_questions[first_id])
    if second_id in all_questions:
        pair.append(all_questions[second_id])

    return pair
