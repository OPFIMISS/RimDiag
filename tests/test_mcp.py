import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def value(result):
    return json.loads(next(item.text for item in result.content if item.type == "text"))


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_wire_discovery_diagnosis_and_denials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / "Player.log"
            log.write_text("NullReferenceException: Test\n at Unknown.Mod.Run()\n" * 30)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            params = StdioServerParameters(command=sys.executable, args=["-m", "rimdiag", "--store", str(root / "runs"), "--log", str(log), "serve"], env=env)
            async with stdio_client(params) as streams:
                async with ClientSession(*streams, read_timeout_seconds=20) as session:
                    init = await session.initialize()
                    self.assertEqual(init.server_info.name, "RimDiag")
                    self.assertIn("Never read third-party", init.instructions)
                    tools = (await session.list_tools()).tools
                    names = {t.name for t in tools}
                    self.assertEqual(len(names), 9)
                    self.assertFalse(any("source" in x or "decomp" in x or "grant" in x for x in names))
                    caps = value(await session.call_tool("rimdiag_capabilities", {}))
                    self.assertFalse(caps["implementation_access"])
                    self.assertEqual(caps['log_inputs'][0]['name'], 'Player.log')
                    self.assertEqual(caps['log_inputs'][0]['log_index'], 0)
                    report = value(await session.call_tool("rimdiag_analyze", {}))
                    self.assertEqual(report["recognized_error_events"], 30)
                    triage = value(await session.call_tool("rimdiag_triage", {"run_id": report["run_id"]}))
                    self.assertEqual(triage['symptom_families'][0]['events'], 30)
                    filtered = value(await session.call_tool("rimdiag_list_errors", {'run_id': report['run_id'], 'category_filter': 'null_reference'}))
                    self.assertEqual(len(filtered['groups']), 1)
                    page = value(await session.call_tool("rimdiag_list_errors", {"run_id": report["run_id"]}))
                    evidence = value(await session.call_tool("rimdiag_read_evidence", {"run_id": report["run_id"], "group_id": page["groups"][0]["fingerprint"]}))
                    self.assertEqual(evidence["identity_references"], [])
                    self.assertEqual(evidence["causality"], "unconfirmed")
                    invalid = value(await session.call_tool("rimdiag_analyze", {"log_index": 99}))
                    self.assertEqual(invalid["code"], "unknown_configured_log")
                    traversal = value(await session.call_tool("rimdiag_summary", {"run_id": "../private"}))
                    self.assertEqual(traversal["code"], "invalid_run_id")
                    injection = await session.call_tool("rimdiag_analyze", {"source_path": "foreign/Mod.cs"})
                    # SDK 2.3 ignores undeclared extra arguments. They cannot change host inputs.
                    self.assertEqual(value(injection)["recognized_error_events"], 30)
                    forbidden = await session.call_tool("rimdiag_decompile_mod", {"path": "foreign/Mod.dll"})
                    self.assertTrue(forbidden.is_error)


if __name__ == "__main__":
    unittest.main()
