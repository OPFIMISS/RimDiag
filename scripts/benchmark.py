"""Reproducible synthetic scale check. No game, real mods or private logs are accessed."""
import json
import tempfile
import time
from pathlib import Path
from rimdiag.core import Diagnostics


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for i in range(600):
            about = root / "Mods" / str(i) / "About"
            about.mkdir(parents=True)
            (about / "About.xml").write_text(f"<ModMetaData><name>Fixture {i}</name><packageId>fixture.mod{i}</packageId></ModMetaData>")
        config = root / "ModsConfig.xml"
        config.write_text("<ModsConfigData><activeMods>" + "".join(f"<li>fixture.mod{i}</li>" for i in range(600)) + "</activeMods></ModsConfigData>")
        log = root / "Player.log"
        log.write_text("NullReferenceException: fixture.mod42\n at Unverified.Namespace.Method()\n" * 10000)
        diagnostics = Diagnostics(root / "evidence", [log], config, [root / "Mods"])
        start = time.perf_counter()
        report = diagnostics.analyze()
        elapsed = time.perf_counter() - start
        page = diagnostics.list_errors(report["run_id"])
        evidence = diagnostics.evidence(report["run_id"], page["groups"][0]["fingerprint"])
        print(json.dumps({"synthetic": True, "mod_identities": 600, "error_occurrences": 10000,
            "input_bytes": log.stat().st_size, "groups": report["error_groups"],
            "analysis_seconds": round(elapsed, 3),
            "summary_utf8_bytes": len(json.dumps(report, ensure_ascii=False).encode()),
            "group_page_utf8_bytes": len(json.dumps(page, ensure_ascii=False).encode()),
            "one_evidence_utf8_bytes": len(json.dumps(evidence, ensure_ascii=False).encode()),
            "accuracy_measured": False, "client_tokens_measured": False}, indent=2))


if __name__ == "__main__":
    main()
