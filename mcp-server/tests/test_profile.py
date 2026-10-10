from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from myspec_mcp_server.profile import (
    allocate_minutes,
    build_profile,
    find_technology_terms,
    get_language,
    get_profile_path,
    load_profile,
    resource_text,
    save_profile,
)


class ProfileLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_missing_profile_is_classified_without_crashing(self) -> None:
        snapshot = load_profile(self.root / "missing.md")
        self.assertEqual(snapshot.status, "missing")
        self.assertIn("missing", resource_text(snapshot, "full"))
        not_a_file = self.root / "directory"
        not_a_file.mkdir()
        self.assertEqual(load_profile(not_a_file).status, "unreadable")

    def test_empty_and_malformed_json_profiles_are_classified(self) -> None:
        empty = self.root / "empty.md"
        empty.write_text("  \n", encoding="utf-8")
        self.assertEqual(load_profile(empty).status, "malformed")

        malformed = self.root / "bad.json"
        malformed.write_text("{not-json", encoding="utf-8")
        snapshot = load_profile(malformed)
        self.assertEqual(snapshot.status, "malformed")
        self.assertIn("invalid JSON", snapshot.detail)

    def test_json_profile_extracts_skills_and_preferences(self) -> None:
        profile = self.root / "profile.json"
        profile.write_text(
            json.dumps(
                {
                    "identity": {"role": "Engineer"},
                    "current_skills": {"Python": "proficient"},
                    "learning_in_progress": {"Rust": "beginner"},
                    "communication_prefs": {"style": "concise"},
                    "growth_goals": {"goal": "systems"},
                }
            ),
            encoding="utf-8",
        )
        snapshot = load_profile(profile)
        self.assertEqual(snapshot.status, "available")
        self.assertIn("Python", resource_text(snapshot, "skills"))
        self.assertIn("concise", resource_text(snapshot, "preferences"))
        self.assertIn("Engineer", resource_text(snapshot, "summary"))

    def test_markdown_profile_remains_available_and_sections_are_extractable(self) -> None:
        profile = self.root / "profile.md"
        profile.write_text(
            "# Profile\n## Skills\n- Python: proficient\n## Communication Preferences\n- Concise\n",
            encoding="utf-8",
        )
        snapshot = load_profile(profile)
        self.assertEqual(snapshot.status, "available")
        self.assertEqual(snapshot.format, "markdown")
        self.assertIn("Python", resource_text(snapshot, "skills"))
        self.assertIn("Concise", resource_text(snapshot, "preferences"))
        self.assertIn("ملف MySpec", resource_text(snapshot, "summary", "ar"))

    def test_environment_overrides_and_language_fallback(self) -> None:
        self.assertEqual(get_profile_path({}), (Path.home() / ".myspec" / "profile.md").resolve())
        configured = get_profile_path({"MYSPEC_PROFILE_PATH": "~/custom/profile.md"})
        self.assertTrue(str(configured).endswith(str(Path.home() / "custom" / "profile.md")))
        self.assertEqual(get_language({"MYSPEC_LANG": "ar-MSA"}), "ar")
        self.assertEqual(get_language({"MYSPEC_LANG": "unsupported"}), "en")
        self.assertEqual(get_language({}), "en")

    def test_profile_path_falls_back_to_json_when_md_absent(self) -> None:
        with tempfile.TemporaryDirectory() as fake_home:
            fake_home_path = Path(fake_home)
            myspec_dir = fake_home_path / ".myspec"
            myspec_dir.mkdir()
            json_file = myspec_dir / "profile.json"
            json_file.write_text('{"identity": {}}', encoding="utf-8")

            with unittest.mock.patch("pathlib.Path.home", return_value=fake_home_path):
                resolved = get_profile_path({})
                self.assertEqual(resolved, json_file.resolve())

                # If profile.md is also created, profile.md takes priority
                md_file = myspec_dir / "profile.md"
                md_file.write_text("# Profile", encoding="utf-8")
                resolved_with_md = get_profile_path({})
                self.assertEqual(resolved_with_md, md_file.resolve())

    def test_minutes_are_distributed_exactly_and_terms_are_local(self) -> None:
        for total in (5, 60, 137, 480):
            self.assertEqual(sum(allocate_minutes(total)), total)
            self.assertTrue(all(value >= 1 for value in allocate_minutes(total)))
        terms = find_technology_terms("Build a FastAPI service with PostgreSQL and React.")
        self.assertEqual(terms, ["postgresql", "fastapi", "react"])

    def test_technology_terms_avoids_substring_collisions(self) -> None:
        # "React Native" should only match "react native", not "react"
        terms_single = find_technology_terms("Build a modern mobile app with React Native and PostgreSQL.")
        self.assertEqual(terms_single, ["react native", "postgresql"])
        self.assertNotIn("react", terms_single)

        # If both are independently mentioned, both should match
        terms_both = find_technology_terms("We use React Native for mobile and React for the web portal.")
        self.assertIn("react native", terms_both)
        self.assertIn("react", terms_both)

    def test_markdown_parser_handles_code_blocks_and_nested_headers(self) -> None:
        raw_md = (
            "# Developer Profile\n"
            "## Skills\n"
            "- Python: proficient\n"
            "```python\n"
            "# Configure database connection\n"
            "db = connect(host='localhost')\n"
            "```\n"
            "## Communication\n"
            "- Direct and concise\n"
        )
        profile_file = self.root / "code_block_profile.md"
        profile_file.write_text(raw_md, encoding="utf-8")
        snapshot = load_profile(profile_file)

        self.assertEqual(snapshot.status, "available")
        skills_text = resource_text(snapshot, "skills")
        # Ensure code comment was NOT treated as a separate section header
        self.assertIn("# Configure database connection", skills_text)
        self.assertIn("Python: proficient", skills_text)

        # Communication section is preserved intact
        pref_text = resource_text(snapshot, "preferences")
        self.assertIn("Direct and concise", pref_text)

    def test_allocate_minutes_lower_bound_safety(self) -> None:
        # Sessions below 5 minutes should clamp safely to 5 minutes
        for invalid_total in (4, 1, 0, -10):
            allocated = allocate_minutes(invalid_total)
            self.assertEqual(sum(allocated), 5)
            self.assertTrue(all(v >= 1 for v in allocated))

    def test_build_profile_full_50_questions(self) -> None:
        answers = {f"Q{i:02d}": f"Detailed answer for question {i}" for i in range(1, 51)}
        profile = build_profile(answers, language="en")

        self.assertEqual(profile["status"], "complete")
        self.assertEqual(profile["completion_rate"], 1.0)
        self.assertEqual(profile["language"], "en")
        self.assertEqual(profile["skipped_fields"], [])

        # Verify all 7 module dictionaries are populated
        for module in (
            "identity",
            "work_context",
            "communication_prefs",
            "current_skills",
            "learning_in_progress",
            "limitations",
            "growth_goals",
        ):
            self.assertIn(module, profile)
            self.assertIsInstance(profile[module], dict)
            self.assertTrue(len(profile[module]) > 0)

        # Check module membership mapping
        self.assertEqual(profile["identity"]["Q01"], "Detailed answer for question 1")
        self.assertEqual(profile["communication_prefs"]["Q11"], "Detailed answer for question 11")
        self.assertEqual(profile["growth_goals"]["Q39"], "Detailed answer for question 39")

    def test_build_profile_partial_and_skipped_fields(self) -> None:
        answers = {f"Q{i:02d}": f"Answer {i}" for i in range(1, 26)}
        answers["Q07"] = "__SKIPPED__"
        answers["Q14"] = "__SKIPPED__"
        answers["Q20"] = "__SKIPPED__"
        answers["Q22"] = "__SKIPPED__"
        answers["Q25"] = "__SKIPPED__"
        # 25 total supplied, 5 skipped -> 20 answered out of 50 -> 0.4 completion rate
        profile = build_profile(answers, language="en")

        self.assertEqual(profile["status"], "partial")
        self.assertEqual(profile["completion_rate"], 0.4)
        self.assertEqual(profile["skipped_fields"], ["Q07", "Q14", "Q20", "Q22", "Q25"])

    def test_build_profile_merges_with_existing(self) -> None:
        initial_answers = {"Q01": "Initial role", "Q02": "Initial industry"}
        initial_profile = build_profile(initial_answers)

        update_answers = {"Q01": "Updated senior role", "Q03": "New experience"}
        merged = build_profile(update_answers, existing_profile=initial_profile)

        self.assertEqual(merged["identity"]["Q01"], "Updated senior role")
        self.assertEqual(merged["identity"]["Q02"], "Initial industry")
        self.assertEqual(merged["identity"]["Q03"], "New experience")

    def test_save_profile_atomic_and_dir_creation(self) -> None:
        target_dir = self.root / "nested" / "deep"
        target_file = target_dir / "profile.json"
        data = {"schema_version": 1, "status": "complete", "completion_rate": 1.0}

        saved_path = save_profile(data, target_file)
        self.assertEqual(saved_path, target_file.resolve())
        self.assertTrue(saved_path.is_file())

        # Verify .tmp file was cleaned up by atomic rename
        tmp_file = saved_path.with_suffix(".json.tmp")
        self.assertFalse(tmp_file.exists())

        # Verify contents
        loaded = json.loads(saved_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["status"], "complete")

    def test_save_and_load_round_trip(self) -> None:
        answers = {f"Q{i:02d}": f"Answer {i}" for i in range(1, 51)}
        built = build_profile(answers)

        target_file = self.root / "roundtrip_profile.json"
        save_profile(built, target_file)

        snapshot = load_profile(target_file)
        self.assertEqual(snapshot.status, "available")
        self.assertEqual(snapshot.format, "json")
        self.assertIsNotNone(snapshot.data)
        self.assertEqual(snapshot.data.get("completion_rate"), 1.0)


if __name__ == "__main__":
    unittest.main()
