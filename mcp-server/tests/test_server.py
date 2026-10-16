from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from myspec_mcp_server.server import mcp

SERVER_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SERVER_ROOT / "src"


class McpSurfaceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=SERVER_ROOT)
        self.addCleanup(self.temp_dir.cleanup)
        self.profile_path = Path(self.temp_dir.name) / "profile.json"
        profile_data = {
            "schema_version": 1,
            "completed_at": "2026-10-16T12:00:00+00:00",
            "status": "partial",
            "completion_rate": 0.5,
            "output_preference": "english_only",
            "language": "en",
            "skipped_fields": [],
            "identity": {"role": "Developer Profile"},
            "current_skills": {"Q03": "Python", "Q04": "React"},
            "learning_in_progress": {},
            "limitations": {},
            "communication_prefs": {"Q05": "Concise answers"},
            "work_context": {"Q07": "Python and React stack"},
            "growth_goals": {},
        }
        self.profile_path.write_text(json.dumps(profile_data, indent=2), encoding="utf-8")
        self.env = patch.dict(os.environ, {"MYSPEC_PROFILE_PATH": str(self.profile_path), "MYSPEC_LANG": "en"})
        self.env.start()
        self.addCleanup(self.env.stop)


    async def test_all_resources_tools_and_prompts_are_registered_and_usable(self) -> None:
        async with Client(mcp) as client:
            resources = await client.list_resources()
            self.assertEqual(
                {str(resource.uri) for resource in resources.resources},
                {
                    "myprofile://summary",
                    "myprofile://skills",
                    "myprofile://preferences",
                    "myprofile://full",
                },
            )

            skill_result = await client.read_resource("myprofile://skills")
            self.assertIn("Python", skill_result.contents[0].text)
            summary_result = await client.read_resource("myprofile://summary")
            self.assertIn("Python", summary_result.contents[0].text)
            preferences_result = await client.read_resource("myprofile://preferences")
            self.assertIn("Concise", preferences_result.contents[0].text)
            full_result = await client.read_resource("myprofile://full")
            self.assertIn("Developer Profile", full_result.contents[0].text)

            tools = await client.list_tools()
            self.assertEqual(
                {tool.name for tool in tools.tools},
                {
                    "get_gap_analysis",
                    "get_onboarding_plan",
                    "start_interview",
                    "advance_interview",
                    "finalize_interview",
                },
            )

            # Test start_interview tool (language=None uses MYSPEC_LANG)
            start = await client.call_tool("start_interview", {})
            start_data = start.structured_content
            self.assertEqual(start_data["pair_index"], 0)
            self.assertEqual(start_data["status"], "in_progress")
            self.assertEqual([q["id"] for q in start_data["questions"]], ["Q01", "Q02"])
            self.assertEqual(start_data["category_name"], "Identity & Work")

            # Explicit language still works
            start_explicit = await client.call_tool("start_interview", {"language": "en"})
            self.assertEqual(start_explicit.structured_content["pair_index"], 0)

            # Test advance_interview tool
            advance = await client.call_tool(
                "advance_interview",
                {
                    "pair_index": 0,
                    "answers_so_far": {"Q01": "Software Engineer", "Q02": "Tech"},
                },
            )
            advance_data = advance.structured_content
            self.assertEqual(advance_data["pair_index"], 1)
            self.assertEqual([q["id"] for q in advance_data["questions"]], ["Q03", "Q04"])

            # Test advance_interview completion boundary (pair 24 requires Q49+Q50 answered)
            all_answers = {f"Q{i:02d}": f"Answer {i}" for i in range(1, 51)}
            complete = await client.call_tool(
                "advance_interview",
                {
                    "pair_index": 24,
                    "answers_so_far": all_answers,
                },
            )
            self.assertEqual(complete.structured_content["status"], "interview_complete")
            self.assertTrue(complete.structured_content["ready_to_finalize"])

            # Test finalize_interview tool
            mock_answers = {f"Q{i:02d}": f"Mock answer {i}" for i in range(1, 51)}
            finalize = await client.call_tool(
                "finalize_interview",
                {"answers": mock_answers, "language": "en", "output_preference": "english_only"},
            )
            finalize_data = finalize.structured_content
            self.assertEqual(finalize_data["status"], "saved")
            self.assertEqual(finalize_data["completion_rate"], 1.0)
            self.assertTrue(Path(finalize_data["path"]).is_file())

            gap = await client.call_tool(
                "get_gap_analysis",
                {"project_description": "Build a Python and FastAPI service with React."},
            )
            gap_data = gap.structured_content
            self.assertEqual(gap_data["terms_mentioned_in_both"], ["python", "react"])
            self.assertEqual(gap_data["project_terms_without_profile_mention"], ["fastapi"])

            plan = await client.call_tool("get_onboarding_plan", {"topic": "React forms"})
            plan_data = plan.structured_content
            self.assertEqual(plan_data["total_minutes"], 60)
            self.assertEqual(sum(item["minutes"] for item in plan_data["agenda"]), 60)
            short_plan = await client.call_tool("get_onboarding_plan", {"topic": "Python", "minutes": 30})
            self.assertEqual(short_plan.structured_content["total_minutes"], 30)

            prompts = await client.list_prompts()
            self.assertEqual({prompt.name for prompt in prompts.prompts}, {"onboarding", "gap_check"})
            prompt = await client.get_prompt("onboarding", {"project_description": "Build a local tool."})
            self.assertIn("Build a local tool", prompt.messages[0].content.text)
            self.assertIn("Python", prompt.messages[0].content.text)
            gap_prompt = await client.get_prompt("gap_check", {"project_description": "Build a local tool."})
            self.assertIn("Local gap-check evidence", gap_prompt.messages[0].content.text)

            with patch.dict(os.environ, {"MYSPEC_LANG": "ar"}):
                localized = await client.read_resource("myprofile://summary")
                self.assertIn("ملخص ملف MySpec", localized.contents[0].text)

    async def test_stdio_child_process_serves_profile_without_a_custom_client_app(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "myspec_mcp_server"],
            env={
                "PYTHONPATH": str(SRC_ROOT),
                "MYSPEC_PROFILE_PATH": str(self.profile_path),
                "MYSPEC_LANG": "en",
            },
            cwd=SERVER_ROOT,
        )
        async with Client(params) as client:
            result = await client.read_resource("myprofile://summary")
            self.assertIn("Python", result.contents[0].text)

    async def test_tools_return_is_error_for_invalid_inputs(self) -> None:
        """Validation failures must surface as isError=True tool results, not {"error": ...} dicts."""
        self.profile_path.unlink()
        async with Client(mcp) as client:
            # get_gap_analysis: missing profile returns structured data (not an error)
            gap = await client.call_tool("get_gap_analysis", {"project_description": "Build a Python app."})
            self.assertFalse(gap.is_error)
            self.assertEqual(gap.structured_content["profile_status"], "missing")
            self.assertIsNotNone(gap.structured_content["profile_warning"])

            # get_gap_analysis: empty description is a ToolError -> isError=True
            empty_gap = await client.call_tool("get_gap_analysis", {"project_description": "  "})
            self.assertTrue(empty_gap.is_error)

            # get_onboarding_plan: empty topic is a ToolError
            empty_topic = await client.call_tool("get_onboarding_plan", {"topic": "  "})
            self.assertTrue(empty_topic.is_error)

            # get_onboarding_plan: out-of-range minutes is a ToolError
            too_short = await client.call_tool("get_onboarding_plan", {"topic": "Python", "minutes": 4})
            self.assertTrue(too_short.is_error)

    async def test_advance_interview_rejects_unanswered_pair(self) -> None:
        """advance_interview must return isError=True when the current pair lacks answers."""
        async with Client(mcp) as client:
            # Pair 0 requires Q01 and Q02; supply only Q01
            result = await client.call_tool(
                "advance_interview",
                {
                    "pair_index": 0,
                    "answers_so_far": {"Q01": "Software Engineer"},
                },
            )
            self.assertTrue(result.is_error)
            error_text = result.content[0].text
            self.assertIn("Q02", error_text)

    async def test_advance_interview_accepts_disposition_sentinels(self) -> None:
        """Disposition sentinels count as explicit answers for the pair-advance gate."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "advance_interview",
                {
                    "pair_index": 0,
                    "answers_so_far": {"Q01": "Software Engineer", "Q02": "__SKIPPED__"},
                },
            )
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["pair_index"], 1)

    async def test_finalize_interview_rejects_unknown_question_ids(self) -> None:
        """finalize_interview must return isError=True for answers with invalid question IDs."""
        async with Client(mcp) as client:
            bad_answers = {"Q99": "invalid", "Q01": "valid answer"}
            result = await client.call_tool("finalize_interview", {"answers": bad_answers})
            self.assertTrue(result.is_error)
            self.assertIn("Q99", result.content[0].text)

    async def test_finalize_interview_output_preference_is_persisted(self) -> None:
        """output_preference supplied to finalize_interview should be stored in the saved profile."""
        async with Client(mcp) as client:
            answers = {f"Q{i:02d}": f"Answer {i}" for i in range(1, 51)}
            result = await client.call_tool(
                "finalize_interview",
                {"answers": answers, "output_preference": "bilingual"},
            )
            self.assertFalse(result.is_error)
            saved_path = Path(result.structured_content["path"])
            import json
            saved_data = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_data["output_preference"], "bilingual")


    async def test_read_after_write_consistency(self) -> None:
        """Saving a profile via finalize_interview must immediately be reflected in subsequent reads."""
        async with Client(mcp) as client:
            answers = {f"Q{i:02d}": f"Hardened Answer {i}" for i in range(1, 51)}
            finalize = await client.call_tool(
                "finalize_interview",
                {"answers": answers, "output_preference": "english_only"},
            )
            self.assertFalse(finalize.is_error)
            saved_path = Path(finalize.structured_content["path"])
            self.assertEqual(saved_path, self.profile_path.resolve())

            summary = await client.read_resource("myprofile://summary")
            self.assertIn("Hardened Answer 1", summary.contents[0].text)

            full = await client.read_resource("myprofile://full")
            self.assertIn("Hardened Answer 50", full.contents[0].text)

    async def test_legacy_markdown_triggers_migration_required_and_does_not_return_content(self) -> None:
        """When JSON is absent but Markdown exists, reads return migration_required without markdown content."""
        self.profile_path.unlink()
        md_path = self.profile_path.with_suffix(".md")
        md_path.write_text("# Secret Markdown Profile\n## Skills\n- TopSecretSkill\n", encoding="utf-8")
        async with Client(mcp) as client:
            summary = await client.read_resource("myprofile://summary")
            self.assertIn("migration from legacy Markdown", summary.contents[0].text)
            self.assertNotIn("TopSecretSkill", summary.contents[0].text)

    async def test_cli_profile_arg_overrides_env_in_stdio(self) -> None:
        """CLI --profile overrides MYSPEC_PROFILE_PATH in child process launch."""
        cli_profile = Path(self.temp_dir.name) / "cli_override.json"
        cli_data = {
            "schema_version": 1,
            "completed_at": "2026-10-16T12:00:00+00:00",
            "status": "complete",
            "completion_rate": 1.0,
            "output_preference": "english_only",
            "language": "en",
            "skipped_fields": [],
            "identity": {"role": "CLI Profile"},
            "current_skills": {"Q03": "Golang"},
            "learning_in_progress": {},
            "limitations": {},
            "communication_prefs": {},
            "work_context": {},
            "growth_goals": {},
        }
        cli_profile.write_text(json.dumps(cli_data, indent=2), encoding="utf-8")

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "myspec_mcp_server", "--profile", str(cli_profile)],
            env={
                "PYTHONPATH": str(SRC_ROOT),
                "MYSPEC_PROFILE_PATH": str(self.profile_path),
                "MYSPEC_LANG": "en",
            },
            cwd=SERVER_ROOT,
        )
        async with Client(params) as client:
            result = await client.read_resource("myprofile://summary")
            self.assertIn("CLI Profile", result.contents[0].text)
            self.assertNotIn("Developer Profile", result.contents[0].text)


if __name__ == "__main__":
    unittest.main()

