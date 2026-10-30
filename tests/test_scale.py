import json
import tempfile
import unittest
from pathlib import Path
from rimdiag.core import Diagnostics


class ScaleTests(unittest.TestCase):
    def test_600_mods_and_10000_errors_stay_compact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mods = root / "Mods"
            for i in range(600):
                about = mods / str(i) / "About"
                about.mkdir(parents=True)
                (about / "About.xml").write_text(f"<ModMetaData><name>Mod {i}</name><packageId>fixture.mod{i}</packageId></ModMetaData>")
            config = root / "ModsConfig.xml"
            config.write_text("<ModsConfigData><activeMods>" + "".join(f"<li>fixture.mod{i}</li>" for i in range(600)) + "</activeMods></ModsConfigData>")
            log = root / "Player.log"
            log.write_text("NullReferenceException: fixture.mod42\n at Wrong.Mod.Name.Run()\n" * 10000)
            engine = Diagnostics(root / "evidence # Unicode 测试", [log], config, [mods])
            report = engine.analyze()
            self.assertEqual(report["active_packages"], 600)
            self.assertEqual(report["unresolved_active_packages"], 0)
            self.assertEqual(report["recognized_error_events"], 10000)
            self.assertEqual(report["error_groups"], 1)
            self.assertLess(len(json.dumps(report).encode()), 1200)
            group = engine.list_errors(report["run_id"])["groups"][0]
            evidence = engine.evidence(report["run_id"], group["fingerprint"])
            self.assertEqual(evidence["identity_references"][0]["package_id"], "fixture.mod42")
            self.assertEqual(evidence["causality"], "unconfirmed")
            self.assertLess(len(json.dumps(engine.list_inventory(report["run_id"])).encode()), 8000)


if __name__ == "__main__":
    unittest.main()
