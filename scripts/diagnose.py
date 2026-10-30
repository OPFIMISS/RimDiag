"""Run a bounded diagnostic pass through real MCP stdio and save private evidence locally."""
import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def payload(result):
    data = json.loads(next(item.text for item in result.content if item.type == "text"))
    if result.is_error or data.get("status") == "error":
        raise RuntimeError(data.get("code", "MCP diagnostic request failed"))
    return data


async def diagnose(args):
    command = ["-m", "rimdiag", "--store", str(args.store)]
    for log in args.log:
        command += ["--log", str(log)]
    if args.mods_config:
        command += ["--mods-config", str(args.mods_config)]
    for root in args.mod_root:
        command += ["--mod-root", str(root)]
    report = {"transport": "real_mcp_stdio", "functional_status": "not_tested", "snapshots": []}
    async with stdio_client(StdioServerParameters(command=sys.executable, args=command + ["serve"])) as streams:
        async with ClientSession(*streams, read_timeout_seconds=args.timeout) as session:
            await session.initialize()
            for index in range(len(args.log)):
                summary = payload(await session.call_tool("rimdiag_analyze", {"log_index": index}))
                triage = payload(await session.call_tool("rimdiag_triage", {"run_id": summary["run_id"], "count": 3}))
                snapshot = {"log_index": index, "summary": summary, "triage": triage, "selected_evidence": []}
                for priority in triage["investigation_priorities"][:args.evidence]:
                    group = priority["group_id"]
                    snapshot["selected_evidence"].append(payload(await session.call_tool("rimdiag_read_evidence", {"run_id": summary["run_id"], "group_id": group, "occurrence": priority["occurrence"]})))
                report["snapshots"].append(snapshot)
                # Full evidence stays in the private output, not the console/context.
                print(json.dumps({"log_index": index, "summary": summary,
                    "investigation_priorities": triage["investigation_priorities"],
                    "structural_data_leads": triage["structural_data_leads"],
                    "structural_data_leads": triage["structural_data_leads"],
                    "categories": triage["category_counts"],
                    "top_symptoms": [{k: f[k] for k in ("family_id", "label", "events", "groups")} for f in triage["symptom_families"]]}, ensure_ascii=False))
            if len(report["snapshots"]) == 2:
                report["comparison"] = payload(await session.call_tool("rimdiag_compare", {
                    "baseline_id": report["snapshots"][0]["summary"]["run_id"],
                    "candidate_id": report["snapshots"][1]["summary"]["run_id"]}))
    output = args.store / ("diagnosis-" + uuid.uuid4().hex + ".json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"private_report": str(output), "do_not_upload": True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", required=True,
                        help="Stable log copy; for exactly two inputs the first is baseline, second candidate")
    parser.add_argument("--mods-config", type=Path)
    parser.add_argument("--mod-root", type=Path, action="append", default=[])
    parser.add_argument("--evidence", type=int, choices=range(4), default=0, help="Save up to three selected family examples privately")
    parser.add_argument("--timeout", type=int, choices=range(1, 601), default=120)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(diagnose(args))


if __name__ == "__main__":
    main()
