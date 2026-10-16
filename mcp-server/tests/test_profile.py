from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from myspec_mcp_server.profile import (
    MigrationError,
    MigrationResult,
    MySpecProfile,
    ProfileConfigurationError,
    ProfileValidationError,
    _markdown_sections,
    allocate_minutes,
    build_profile,
    extract_preferences,
    extract_skills,
    find_technology_terms,
    get_cli_profile_path,
    get_language,
    get_profile_path,
    load_profile,
    migrate_markdown_profile,
    resource_text,
    save_profile,
    set_cli_profile_path,
    validate_answers,
    validate_pair_answers,
    validate_profile_dict,
)


def _valid_profile_dict(**overrides) -> dict:
    """Return a minimal complete valid profile dict, merging any overrides."""
    base = {
        "schema_version": 1,
        "completed_at": "2024-06-01T12:00:00+00:00",
        "status": "partial",
        "completion_rate": 0.0,
        "output_preference": "english_only",
        "language": "en",
        "skipped_fields": [],
        "identity": {},
        "current_skills": {},
        "learning_in_progress": {},
        "limitations": {},
        "communication_prefs": {},
        "work_context": {},
        "growth_goals": {},
    }
    base.update(overrides)
    return base


class ProfileLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_missing_profile_is_classified_without_crashing(self) -> None:
        snapshot = load_profile(self.root / "missing.json")
        self.assertEqual(snapshot.status, "missing")
        self.assertIn("missing", resource_text(snapshot, "full"))
        not_a_file = self.root / "directory"
        not_a_file.mkdir()
        self.assertEqual(load_profile(not_a_file).status, "unreadable")

    def test_empty_and_malformed_json_profiles_are_classified(self) -> None:
        empty = self.root / "empty.json"
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
                    "schema_version": 1,
                    "completed_at": "2026-10-16T12:00:00+00:00",
                    "status": "partial",
                    "completion_rate": 0.5,
                    "output_preference": "english_only",
                    "language": "en",
                    "skipped_fields": [],
                    "identity": {"role": "Engineer"},
                    "current_skills": {"Python": "proficient"},
                    "learning_in_progress": {"Rust": "beginner"},
                    "limitations": {},
                    "communication_prefs": {"style": "concise"},
                    "work_context": {},
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

    def test_legacy_markdown_triggers_migration_required_and_does_not_return_content(self) -> None:
        legacy_md = self.root / "profile.md"
        legacy_md.write_text(
            "# Profile\n## Skills\n- Python: proficient\n## Communication Preferences\n- Concise\n",
            encoding="utf-8",
        )
        # Explicit call with .md path returns migration_required
        snapshot_md = load_profile(legacy_md)
        self.assertEqual(snapshot_md.status, "migration_required")
        self.assertEqual(snapshot_md.format, "markdown")
        self.assertNotIn("Python", resource_text(snapshot_md, "skills"))

        # Sibling profile.json check when json missing but md exists
        target_json = self.root / "profile.json"
        snapshot_json = load_profile(target_json)
        self.assertEqual(snapshot_json.status, "migration_required")
        self.assertIn("migration", snapshot_json.detail.lower())

    def test_environment_overrides_and_language_fallback(self) -> None:
        self.assertEqual(get_profile_path({}), (Path.home() / ".myspec" / "profile.json").resolve())
        configured = get_profile_path({"MYSPEC_PROFILE_PATH": "~/custom/profile.json"})
        self.assertTrue(str(configured).endswith(str(Path.home() / "custom" / "profile.json")))
        self.assertEqual(get_language({"MYSPEC_LANG": "ar-MSA"}), "ar")
        self.assertEqual(get_language({"MYSPEC_LANG": "unsupported"}), "en")
        self.assertEqual(get_language({}), "en")

        # Setting .md in MYSPEC_PROFILE_PATH raises ProfileConfigurationError
        with self.assertRaises(ProfileConfigurationError) as ctx:
            get_profile_path({"MYSPEC_PROFILE_PATH": "~/custom/profile.md"})
        self.assertIn("migrate", str(ctx.exception))

    def test_path_precedence_cli_env_config_default(self) -> None:
        with tempfile.TemporaryDirectory() as fake_home:
            fake_home_path = Path(fake_home)
            myspec_dir = fake_home_path / ".myspec"
            myspec_dir.mkdir()

            config_file = myspec_dir / "config.json"
            config_file.write_text(
                json.dumps({"profile_path": str(fake_home_path / "from_config.json")}),
                encoding="utf-8",
            )

            with mock.patch("pathlib.Path.home", return_value=fake_home_path):
                # 4. Default: ~/.myspec/profile.json when no config, env, or CLI
                resolved_default = get_profile_path({}, config_path=fake_home_path / "nonexistent_config.json")
                self.assertEqual(resolved_default, (myspec_dir / "profile.json").resolve())

                # 3. Config file takes precedence over default
                resolved_cfg = get_profile_path({}, config_path=config_file)
                self.assertEqual(resolved_cfg, (fake_home_path / "from_config.json").resolve())

                # 2. Environment takes precedence over config
                env_override = {"MYSPEC_PROFILE_PATH": str(fake_home_path / "from_env.json")}
                resolved_env = get_profile_path(environ=env_override, config_path=config_file)
                self.assertEqual(resolved_env, (fake_home_path / "from_env.json").resolve())

                # 1. CLI takes precedence over env and config
                cli_override = fake_home_path / "from_cli.json"
                resolved_cli = get_profile_path(cli_path=cli_override, environ=env_override, config_path=config_file)
                self.assertEqual(resolved_cli, cli_override.resolve())

    def test_config_file_validation_and_errors(self) -> None:
        # Malformed JSON in config
        cfg_bad_json = self.root / "bad_config.json"
        cfg_bad_json.write_text("{invalid json", encoding="utf-8")
        with self.assertRaises(ProfileConfigurationError) as ctx:
            get_profile_path({}, config_path=cfg_bad_json)
        self.assertIn("Malformed MySpec config file", str(ctx.exception))

        # Config root not a dict
        cfg_array = self.root / "array_config.json"
        cfg_array.write_text("[\"profile.json\"]", encoding="utf-8")
        with self.assertRaises(ProfileConfigurationError):
            get_profile_path({}, config_path=cfg_array)

        # profile_path is .md
        cfg_md = self.root / "md_config.json"
        cfg_md.write_text(json.dumps({"profile_path": "profile.md"}), encoding="utf-8")
        with self.assertRaises(ProfileConfigurationError) as ctx:
            get_profile_path({}, config_path=cfg_md)
        self.assertIn("migrate", str(ctx.exception))

        # profile_path not a string
        cfg_int = self.root / "int_config.json"
        cfg_int.write_text(json.dumps({"profile_path": 12345}), encoding="utf-8")
        with self.assertRaises(ProfileConfigurationError):
            get_profile_path({}, config_path=cfg_int)

    def test_minutes_are_distributed_exactly_and_terms_are_local(self) -> None:
        for total in (5, 60, 137, 480):
            self.assertEqual(sum(allocate_minutes(total)), total)
            self.assertTrue(all(value >= 1 for value in allocate_minutes(total)))
        terms = find_technology_terms("Build a FastAPI service with PostgreSQL and React.")
        self.assertEqual(terms, ["postgresql", "fastapi", "react"])

    def test_technology_terms_avoids_substring_collisions(self) -> None:
        terms_single = find_technology_terms("Build a modern mobile app with React Native and PostgreSQL.")
        self.assertEqual(terms_single, ["react native", "postgresql"])
        self.assertNotIn("react", terms_single)

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
        sections = _markdown_sections(raw_md)
        titles = [s[0] for s in sections]
        self.assertIn("Developer Profile - Skills", titles)
        body = dict(sections)["Developer Profile - Skills"]
        self.assertIn("# Configure database connection", body)
        self.assertIn("Python: proficient", body)

    def test_migration_happy_path_with_sections_and_fenced_json(self) -> None:
        # Section-based markdown
        legacy_file = self.root / "legacy_profile.md"
        legacy_file.write_text(
            "# Developer Profile\n"
            "## Skills\n"
            "- Python: proficient\n"
            "- React: intermediate\n"
            "## Communication Preferences\n"
            "- Style: concise\n"
            "## Work Context\n"
            "- Environment: remote agile\n",
            encoding="utf-8",
        )
        dest_json = self.root / "migrated_profile.json"
        result = migrate_markdown_profile(source_path=legacy_file, dest_path=dest_json)
        self.assertEqual(result.status, "migrated")
        self.assertTrue(dest_json.is_file())
        self.assertTrue(result.archive.is_file())
        # Original markdown preserved
        self.assertTrue(legacy_file.is_file())

        # Verify destination is loadable canonical JSON
        snapshot = load_profile(dest_json)
        self.assertEqual(snapshot.status, "available")
        self.assertEqual(snapshot.format, "json")
        self.assertIn("Python", resource_text(snapshot, "skills"))

        # Repeat migration must refuse overwrite
        with self.assertRaises(MigrationError) as ctx:
            migrate_markdown_profile(source_path=legacy_file, dest_path=dest_json)
        self.assertIn("already exists", str(ctx.exception))

    def test_migration_failure_leaves_source_intact(self) -> None:
        empty_file = self.root / "empty_legacy.md"
        empty_file.write_text("   \n", encoding="utf-8")
        dest_json = self.root / "should_not_exist.json"

        with self.assertRaises(MigrationError):
            migrate_markdown_profile(source_path=empty_file, dest_path=dest_json)

        self.assertTrue(empty_file.is_file())
        self.assertFalse(dest_json.exists())

    def test_atomic_save_profile_and_failure_safety(self) -> None:
        target = self.root / "atomic.json"
        profile_data = _valid_profile_dict(identity={"role": "Original"})
        save_profile(profile_data, target)
        self.assertTrue(target.is_file())

        # Simulate failure during validation before save
        bad_profile_data = {"invalid": "missing required schema"}
        with self.assertRaises(ProfileValidationError):
            save_profile(bad_profile_data, target)

        # Target file remains valid and unmodified
        snapshot = load_profile(target)
        self.assertEqual(snapshot.status, "available")
        self.assertEqual(snapshot.data["identity"]["role"], "Original")


    def test_allocate_minutes_lower_bound_safety(self) -> None:
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
        self.assertIn("completed_at", profile)
        self.assertNotIn("updated_at", profile)

        for module in (
            "identity", "work_context", "communication_prefs",
            "current_skills", "learning_in_progress", "limitations", "growth_goals",
        ):
            self.assertIn(module, profile)
            self.assertIsInstance(profile[module], dict)
            self.assertTrue(len(profile[module]) > 0)

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

    def test_build_profile_output_preference(self) -> None:
        answers = {"Q01": "Test"}
        for pref in ("bilingual", "english_only", "arabic_only", "none"):
            p = build_profile(answers, output_preference=pref)
            self.assertEqual(p["output_preference"], pref)
        # Unknown pref falls back to english_only
        p_fallback = build_profile(answers, output_preference="invalid_pref")
        self.assertEqual(p_fallback["output_preference"], "english_only")

    def test_save_profile_atomic_and_dir_creation(self) -> None:
        target_dir = self.root / "nested" / "deep"
        target_file = target_dir / "profile.json"
        data = build_profile({f"Q{i:02d}": f"A{i}" for i in range(1, 51)})

        saved_path = save_profile(data, target_file)
        self.assertEqual(saved_path, target_file.resolve())
        self.assertTrue(saved_path.is_file())

        tmp_file = saved_path.with_suffix(".json.tmp")
        self.assertFalse(tmp_file.exists())

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

    def test_save_profile_rejects_invalid_data(self) -> None:
        """save_profile must not write anything when data fails canonical validation."""
        target_file = self.root / "bad_profile.json"
        # An extra undocumented field violates extra="forbid"
        invalid_data = _valid_profile_dict(undocumented_extra_field="should_fail")
        with self.assertRaises(ProfileValidationError):
            save_profile(invalid_data, target_file)
        # File must NOT have been created.
        self.assertFalse(target_file.exists())

    def test_load_profile_rejects_unsupported_schema_version(self) -> None:
        profile_file = self.root / "old_version.json"
        profile_file.write_text(
            json.dumps({"schema_version": 99, "status": "complete"}),
            encoding="utf-8",
        )
        snapshot = load_profile(profile_file)
        self.assertEqual(snapshot.status, "malformed")
        self.assertIn("unsupported schema_version", snapshot.detail)


class MySpecProfileModelTests(unittest.TestCase):
    """Unit tests for the canonical profile Pydantic model contract."""

    def test_valid_complete_profile_validates_successfully(self) -> None:
        data = _valid_profile_dict(status="complete", completion_rate=1.0)
        model = validate_profile_dict(data)
        self.assertEqual(model.status, "complete")
        self.assertEqual(model.completion_rate, 1.0)
        self.assertEqual(model.output_preference, "english_only")

    def test_valid_partial_profile_validates_successfully(self) -> None:
        data = _valid_profile_dict(status="partial", completion_rate=0.5, skipped_fields=["Q01"])
        model = validate_profile_dict(data)
        self.assertEqual(model.status, "partial")
        self.assertIn("Q01", model.skipped_fields)

    def test_invalid_field_type_fails_with_details(self) -> None:
        # schema_version must be an int; pass a string to trigger a type error
        data = _valid_profile_dict(schema_version="not_an_int")
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_dict(data)
        self.assertIn("Profile validation failed", str(ctx.exception))
        self.assertIn("schema_version", str(ctx.exception))

    def test_extra_top_level_fields_are_rejected(self) -> None:
        data = _valid_profile_dict(undocumented_field="oops")
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_dict(data)
        self.assertIn("undocumented_field", str(ctx.exception))

    def test_invalid_status_enum_is_rejected(self) -> None:
        data = _valid_profile_dict(status="unknown_state")
        with self.assertRaises(ProfileValidationError):
            validate_profile_dict(data)

    def test_invalid_output_preference_enum_is_rejected(self) -> None:
        data = _valid_profile_dict(output_preference="pdf_only")
        with self.assertRaises(ProfileValidationError):
            validate_profile_dict(data)

    def test_completion_rate_out_of_range_is_rejected(self) -> None:
        for bad_rate in (-0.1, 1.1, 2.0):
            data = _valid_profile_dict(completion_rate=bad_rate)
            with self.assertRaises(ProfileValidationError):
                validate_profile_dict(data)

    def test_timezone_naive_completed_at_is_rejected(self) -> None:
        data = _valid_profile_dict(completed_at="2024-01-01T00:00:00")  # no tz
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_dict(data)
        self.assertIn("completed_at", str(ctx.exception))

    def test_unsupported_schema_version_is_rejected(self) -> None:
        data = _valid_profile_dict(schema_version=99)
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_dict(data)
        self.assertIn("schema_version", str(ctx.exception))

    def test_skipped_fields_are_deduplicated(self) -> None:
        data = _valid_profile_dict(skipped_fields=["Q01", "Q02", "Q01"])
        model = validate_profile_dict(data)
        self.assertEqual(model.skipped_fields.count("Q01"), 1)

    def test_module_dicts_accept_dynamic_content(self) -> None:
        data = _valid_profile_dict(
            identity={"Q01": "Software Engineer", "Q02": "FinTech"},
            current_skills={"Q19": "Python (advanced)", "Q20": "TypeScript"},
        )
        model = validate_profile_dict(data)
        self.assertEqual(model.identity["Q01"], "Software Engineer")
        self.assertEqual(model.current_skills["Q19"], "Python (advanced)")


class AnswerValidationTests(unittest.TestCase):
    """Unit tests for validate_answers and validate_pair_answers helpers."""

    def test_valid_answers_return_no_errors(self) -> None:
        answers = {"Q01": "Software Engineer", "Q02": "FinTech", "Q11": "__SKIPPED__"}
        self.assertEqual(validate_answers(answers), [])

    def test_unknown_question_id_produces_error(self) -> None:
        errors = validate_answers({"Q99": "bad", "Q01": "good"})
        self.assertEqual(len(errors), 1)
        self.assertIn("Q99", errors[0])

    def test_empty_string_answer_produces_error(self) -> None:
        errors = validate_answers({"Q01": "   "})
        self.assertEqual(len(errors), 1)
        self.assertIn("Q01", errors[0])

    def test_valid_disposition_sentinels_are_accepted(self) -> None:
        for sentinel in ("__SKIPPED__", "__DECLINED__", "__UNKNOWN__", "__NA__", "__UNRESOLVED__"):
            self.assertEqual(validate_answers({"Q01": sentinel}), [])

    def test_pair_advance_requires_both_questions_answered(self) -> None:
        # Only Q01 answered, Q02 missing
        errors = validate_pair_answers(0, {"Q01": "yes"})
        self.assertEqual(len(errors), 1)
        self.assertIn("Q02", errors[0])

    def test_pair_advance_allows_disposition_sentinels(self) -> None:
        errors = validate_pair_answers(0, {"Q01": "__SKIPPED__", "Q02": "Some answer"})
        self.assertEqual(errors, [])

    def test_pair_advance_rejects_empty_answer_values(self) -> None:
        errors = validate_pair_answers(0, {"Q01": "yes", "Q02": "   "})
        self.assertEqual(len(errors), 1)
        self.assertIn("Q02", errors[0])

    def test_pair_advance_at_last_pair_index(self) -> None:
        # Pair 24: Q49 and Q50
        errors = validate_pair_answers(24, {"Q49": "answer", "Q50": "__DECLINED__"})
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
