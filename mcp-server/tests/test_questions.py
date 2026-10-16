from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from myspec_mcp_server.questions import (
    CANONICAL_QUESTION_IDS,
    CATEGORIES_METADATA,
    QUESTION_TO_CATEGORY,
    QUESTION_TO_TARGET_MODULES,
    QuestionBankError,
    QuestionFileNotFoundError,
    QuestionLanguageError,
    QuestionModel,
    QuestionParseError,
    QuestionValidationError,
    clear_question_cache,
    get_question_pair,
    get_questions_root,
    load_all_questions,
    load_category_questions,
    parse_question_file,
    validate_bank_parity,
)


def _populate_valid_bank(root: Path, lang: str = "en") -> None:
    """Helper to create a fully valid question bank in a directory."""
    lang_dir = root / ("AR-MSA" if lang == "ar" else "EN")
    lang_dir.mkdir(parents=True, exist_ok=True)

    for cat_id, meta in CATEGORIES_METADATA.items():
        filename = meta["file_ar"] if lang == "ar" else meta["file_en"]
        file_path = lang_dir / filename
        start_id, end_id = meta["id_range"]

        lines = [f"# Category {cat_id}: {meta['name_en'] if lang == 'en' else meta['name_ar']}\n"]
        for q_num in range(start_id, end_id + 1):
            q_id = f"Q{q_num:02d}"
            title = f"Title for {q_id}" if lang == "en" else f"عنوان {q_id}"
            prompt_label = "**Question:**" if lang == "en" else "**السؤال:**"
            prompt_body = f"Prompt for {q_id}?" if lang == "en" else f"سؤال {q_id}؟"
            lines.append(f"## {q_id}: {title}")
            lines.append(f"{prompt_label} {prompt_body}")
            lines.append("- **Context & Guidance:** guidance notes here\n")

        file_path.write_text("\n".join(lines), encoding="utf-8")


class QuestionBankHappyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_question_cache()

    def tearDown(self) -> None:
        clear_question_cache()

    def test_load_all_questions_english(self) -> None:
        questions = load_all_questions("en")
        self.assertEqual(len(questions), 50)

        for i in range(1, 51):
            q_id = f"Q{i:02d}"
            self.assertIn(q_id, questions)
            q = questions[q_id]
            self.assertEqual(q["id"], q_id)
            self.assertTrue(len(q["title"]) > 0)
            self.assertTrue(len(q["prompt"]) > 0)
            self.assertEqual(q["language"], "en")
            self.assertTrue(len(q["target_modules"]) > 0)

    def test_load_all_questions_arabic(self) -> None:
        questions = load_all_questions("ar")
        self.assertEqual(len(questions), 50)

        for i in range(1, 51):
            q_id = f"Q{i:02d}"
            self.assertIn(q_id, questions)
            q = questions[q_id]
            self.assertEqual(q["id"], q_id)
            self.assertTrue(len(q["title"]) > 0)
            self.assertTrue(len(q["prompt"]) > 0)
            self.assertEqual(q["language"], "ar")
            self.assertTrue(len(q["target_modules"]) > 0)

    def test_validate_bank_parity_en_and_ar(self) -> None:
        self.assertTrue(validate_bank_parity())

    def test_category_counts_and_boundaries(self) -> None:
        expected_counts = {
            1: 10,  # Q01-Q10
            2: 8,   # Q11-Q18
            3: 7,   # Q19-Q25
            4: 7,   # Q26-Q32
            5: 6,   # Q33-Q38
            6: 6,   # Q39-Q44
            7: 6,   # Q45-Q50
        }
        for cat_id, expected_count in expected_counts.items():
            cat_qs = load_category_questions(cat_id, "en")
            self.assertEqual(len(cat_qs), expected_count, f"Mismatch in category {cat_id}")
            start_num, end_num = CATEGORIES_METADATA[cat_id]["id_range"]
            self.assertEqual(cat_qs[0]["id"], f"Q{start_num:02d}")
            self.assertEqual(cat_qs[-1]["id"], f"Q{end_num:02d}")

    def test_invalid_category_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            load_category_questions(0)
        with self.assertRaises(ValueError):
            load_category_questions(8)

    def test_get_question_pair_turns(self) -> None:
        pair_0 = get_question_pair(0, "en")
        self.assertEqual(len(pair_0), 2)
        self.assertEqual(pair_0[0]["id"], "Q01")
        self.assertEqual(pair_0[1]["id"], "Q02")

        pair_1 = get_question_pair(1, "en")
        self.assertEqual(len(pair_1), 2)
        self.assertEqual(pair_1[0]["id"], "Q03")
        self.assertEqual(pair_1[1]["id"], "Q04")

        pair_24 = get_question_pair(24, "en")
        self.assertEqual(len(pair_24), 2)
        self.assertEqual(pair_24[0]["id"], "Q49")
        self.assertEqual(pair_24[1]["id"], "Q50")

    def test_get_question_pair_boundaries_raise_index_error(self) -> None:
        with self.assertRaises(IndexError):
            get_question_pair(-1)
        with self.assertRaises(IndexError):
            get_question_pair(25)

    def test_canonical_constants_and_mapping_exports(self) -> None:
        self.assertEqual(len(CANONICAL_QUESTION_IDS), 50)
        self.assertEqual(CANONICAL_QUESTION_IDS[0], "Q01")
        self.assertEqual(CANONICAL_QUESTION_IDS[-1], "Q50")

        self.assertEqual(QUESTION_TO_CATEGORY["Q01"], 1)
        self.assertEqual(QUESTION_TO_CATEGORY["Q10"], 1)
        self.assertEqual(QUESTION_TO_CATEGORY["Q11"], 2)
        self.assertEqual(QUESTION_TO_CATEGORY["Q50"], 7)

        self.assertEqual(QUESTION_TO_TARGET_MODULES["Q01"], ["identity", "work_context"])
        self.assertEqual(QUESTION_TO_TARGET_MODULES["Q11"], ["communication_prefs"])

    def test_unsupported_language_raises_question_language_error(self) -> None:
        with self.assertRaises(QuestionLanguageError):
            load_all_questions("french")
        with self.assertRaises(QuestionLanguageError):
            load_all_questions("de")


class QuestionCacheAndIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_question_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root1 = Path(self.temp_dir.name) / "root1"
        self.root2 = Path(self.temp_dir.name) / "root2"
        _populate_valid_bank(self.root1, "en")
        _populate_valid_bank(self.root1, "ar")
        _populate_valid_bank(self.root2, "en")
        _populate_valid_bank(self.root2, "ar")

    def tearDown(self) -> None:
        clear_question_cache()
        self.temp_dir.cleanup()

    def test_cache_separation_between_distinct_bank_roots(self) -> None:
        # Mutate the source text of Q01 in root2 to differ from root1
        cat1_file = self.root2 / "EN" / "01-identity-work.md"
        content = cat1_file.read_text(encoding="utf-8")
        cat1_file.write_text(content.replace("Title for Q01", "CUSTOM ROOT2 TITLE"), encoding="utf-8")

        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root1)}):
            qs1 = load_all_questions("en")
            self.assertEqual(qs1["Q01"]["title"], "Title for Q01")

        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root2)}):
            qs2 = load_all_questions("en")
            # Must return root2's custom question, NOT cached root1
            self.assertEqual(qs2["Q01"]["title"], "CUSTOM ROOT2 TITLE")

        # Switch back to root1 to ensure cache separation is preserved
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root1)}):
            qs1_again = load_all_questions("en")
            self.assertEqual(qs1_again["Q01"]["title"], "Title for Q01")

    def test_cache_immutability_via_defensive_copies(self) -> None:
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root1)}):
            qs1 = load_all_questions("en")
            original_title = qs1["Q01"]["title"]
            # Attempt to mutate consumer copy
            qs1["Q01"]["title"] = "ATTEMPTED_MUTATION"
            del qs1["Q02"]

            # Subsequent load must return untouched cached state
            qs2 = load_all_questions("en")
            self.assertEqual(qs2["Q01"]["title"], original_title)
            self.assertIn("Q02", qs2)

    def test_failed_load_does_not_poison_cache(self) -> None:
        # Damage root1 by removing a required question prompt
        cat1_file = self.root1 / "EN" / "01-identity-work.md"
        cat1_file.write_text("## Q01: Title\n## Q02: Next\n**Question:** Prompt\n", encoding="utf-8")

        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root1)}):
            with self.assertRaises(QuestionParseError):
                load_all_questions("en")

            # Fix the file
            _populate_valid_bank(self.root1, "en")

            # Must now succeed; cache was not poisoned by the earlier failure
            fixed_qs = load_all_questions("en")
            self.assertEqual(len(fixed_qs), 50)


class QuestionBankFailureAndValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_question_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        _populate_valid_bank(self.root, "en")
        _populate_valid_bank(self.root, "ar")

    def tearDown(self) -> None:
        clear_question_cache()
        self.temp_dir.cleanup()

    def test_missing_questions_root_raises_error(self) -> None:
        bad_root = self.root / "does_not_exist"
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(bad_root)}):
            with self.assertRaises(QuestionFileNotFoundError):
                load_all_questions("en")

    def test_missing_language_directory_raises_error(self) -> None:
        shutil.rmtree(self.root / "AR-MSA")
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root)}):
            with self.assertRaises(QuestionFileNotFoundError):
                load_all_questions("ar")

    def test_missing_category_file_raises_error(self) -> None:
        (self.root / "EN" / "03-knowledge-and-skills.md").unlink()
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root)}):
            with self.assertRaises(QuestionFileNotFoundError):
                load_all_questions("en")

    def test_invalid_utf8_encoding_raises_parse_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        cat_file.write_bytes(b"\xff\xfe\x00\x00\x12\x34\xaa\xbb")
        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root)}):
            with self.assertRaises(QuestionParseError):
                load_all_questions("en")

    def test_missing_prompt_raises_parse_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        # Q01 heading without prompt followed directly by Q02 heading
        cat_file.write_text("## Q01: Missing Prompt\n## Q02: Has Prompt\n**Question:** What is your role?\n", encoding="utf-8")
        with self.assertRaises(QuestionParseError) as ctx:
            parse_question_file(cat_file, 1, "en")
        self.assertIn("missing question prompt", str(ctx.exception))

    def test_prompt_without_heading_raises_parse_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        cat_file.write_text("**Question:** Prompt without heading\n## Q01: Role\n**Question:** My role\n", encoding="utf-8")
        with self.assertRaises(QuestionParseError) as ctx:
            parse_question_file(cat_file, 1, "en")
        self.assertIn("Unexpected question prompt without heading", str(ctx.exception))

    def test_empty_title_raises_parse_or_validation_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        cat_file.write_text("## Q01:   \n**Question:** What is your role?\n", encoding="utf-8")
        with self.assertRaises(QuestionBankError):
            parse_question_file(cat_file, 1, "en")

    def test_empty_prompt_raises_parse_or_validation_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        cat_file.write_text("## Q01: Valid Title\n**Question:**   \n", encoding="utf-8")
        with self.assertRaises(QuestionBankError):
            parse_question_file(cat_file, 1, "en")

    def test_duplicate_question_id_in_file_raises_validation_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        cat_file.write_text(
            "## Q01: First Title\n**Question:** First prompt\n"
            "## Q01: Duplicate Title\n**Question:** Duplicate prompt\n",
            encoding="utf-8",
        )
        with self.assertRaises(QuestionValidationError) as ctx:
            parse_question_file(cat_file, 1, "en")
        self.assertIn("Duplicate question ID", str(ctx.exception))

    def test_category_id_range_mismatch_raises_validation_error(self) -> None:
        cat_file = self.root / "EN" / "01-identity-work.md"
        # Category 1 expects Q01-Q10; give it Q15 instead of Q10
        lines = []
        for i in range(1, 10):
            lines.append(f"## Q{i:02d}: Title {i}\n**Question:** Prompt {i}?\n")
        lines.append("## Q15: Out of range\n**Question:** Unexpected prompt?\n")
        cat_file.write_text("\n".join(lines), encoding="utf-8")

        with self.assertRaises(QuestionValidationError) as ctx:
            parse_question_file(cat_file, 1, "en")
        self.assertIn("Category 1 ID mismatch", str(ctx.exception))

    def test_missing_question_ids_in_full_bank_raises_validation_error(self) -> None:
        # Category 1 has only 9 questions instead of 10
        cat1_file = self.root / "EN" / "01-identity-work.md"
        lines = []
        for i in range(1, 10):
            lines.append(f"## Q{i:02d}: Title {i}\n**Question:** Prompt {i}?\n")
        # Missing Q10
        cat1_file.write_text("\n".join(lines), encoding="utf-8")

        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root)}):
            with self.assertRaises(QuestionValidationError) as ctx:
                load_all_questions("en")
            self.assertIn("Category 1 ID mismatch", str(ctx.exception))

    def test_bank_parity_mismatch_raises_validation_error(self) -> None:
        # In Arabic bank, alter Q50 in Category 7 to Q99
        cat7_ar = self.root / "AR-MSA" / "07-personal-context_MSA.md"
        content = cat7_ar.read_text(encoding="utf-8")
        cat7_ar.write_text(content.replace("## Q50:", "## Q99:"), encoding="utf-8")

        with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(self.root)}):
            with self.assertRaises(QuestionValidationError):
                validate_bank_parity(self.root)


class PromptIntegrityTests(unittest.TestCase):
    def test_prompt_files_contain_no_corrupted_tool_names(self) -> None:
        import re

        prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
        self.assertTrue(prompts_dir.is_dir(), f"Prompts directory not found at {prompts_dir}")

        # Corrupted patterns to guard against (checking for non-printable escapes and corrupted tool prefixes)
        corrupted_regexes = [
            re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]"),  # non-printable control chars (except \t, \n, \r)
            re.compile(rb"\b(?<!a)dvance_interview\b"),
            re.compile(rb"\b(?<!f)inalize_interview\b"),
            re.compile(rb"\b(?<!s)tart_interview\b"),
        ]

        for md_file in prompts_dir.glob("*.md"):
            raw_bytes = md_file.read_bytes()
            for pattern in corrupted_regexes:
                match = pattern.search(raw_bytes)
                self.assertIsNone(
                    match,
                    f"Corrupted pattern {pattern.pattern!r} matched at offset {match.start() if match else -1} in {md_file.name}",
                )

        # Check specifically that master-interview-standalone.md references valid tool names
        standalone = prompts_dir / "master-interview-standalone.md"
        text = standalone.read_text(encoding="utf-8")
        self.assertIn("start_interview", text)
        self.assertIn("advance_interview", text)
        self.assertIn("finalize_interview", text)


if __name__ == "__main__":
    unittest.main()
