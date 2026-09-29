from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from myspec_mcp_server.profile import (
    allocate_minutes,
    find_technology_terms,
    get_language,
    get_profile_path,
    load_profile,
    resource_text,
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


if __name__ == "__main__":
    unittest.main()
