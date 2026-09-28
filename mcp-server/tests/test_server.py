from __future__ import annotations

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
        self.profile_path = Path(self.temp_dir.name) / "profile.md"
        self.profile_path.write_text(
            "# Developer Profile\n## Skills\n- Python: proficient\n- React: learning\n"
            "## Communication Preferences\n- Concise answers\n",
            encoding="utf-8",
        )
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
                {"get_gap_analysis", "get_onboarding_plan"},
            )
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

    async def test_tools_return_graceful_results_for_missing_and_invalid_inputs(self) -> None:
        self.profile_path.unlink()
        async with Client(mcp) as client:
            gap = await client.call_tool("get_gap_analysis", {"project_description": "Build a Python app."})
            self.assertEqual(gap.structured_content["profile_status"], "missing")
            self.assertIsNotNone(gap.structured_content["profile_warning"])

            empty_topic = await client.call_tool("get_onboarding_plan", {"topic": "  "})
            self.assertIn("error", empty_topic.structured_content)
            too_short = await client.call_tool("get_onboarding_plan", {"topic": "Python", "minutes": 4})
            self.assertIn("error", too_short.structured_content)


if __name__ == "__main__":
    unittest.main()
