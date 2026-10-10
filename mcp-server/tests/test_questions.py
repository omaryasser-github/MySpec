from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from myspec_mcp_server.questions import (
    CATEGORIES_METADATA,
    get_question_pair,
    get_questions_root,
    load_all_questions,
    load_category_questions,
)


class QuestionBankTests(unittest.TestCase):
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

    def test_environment_override_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with patch.dict(os.environ, {"MYSPEC_QUESTIONS_PATH": str(temp_path)}):
                resolved = get_questions_root()
                self.assertEqual(resolved, temp_path.resolve())


if __name__ == "__main__":
    unittest.main()
