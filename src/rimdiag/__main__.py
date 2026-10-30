import argparse
import json
from pathlib import Path
from .core import Diagnostics


def main():
    parser = argparse.ArgumentParser(description="RimDiag: logs and identity metadata only; no Mod code access")
    parser.add_argument("--store", type=Path, required=True, help="Private local evidence directory; never commit")
    parser.add_argument("--log", type=Path, action="append", default=[], help="Explicit diagnostic log input (repeatable)")
    parser.add_argument("--mods-config", type=Path, help="Read-only ModsConfig.xml")
    parser.add_argument("--mod-root", type=Path, action="append", default=[], help="Read ONLY each immediate child's About/About.xml (repeatable)")
    parser.add_argument("command", choices=["serve", "analyze"])
    args = parser.parse_args()
    diagnostics = Diagnostics(args.store, args.log, args.mods_config, args.mod_root)
    if args.command == "serve":
        from .server import create_server
        create_server(diagnostics).run(transport="stdio")
    else:
        print(json.dumps(diagnostics.analyze(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
