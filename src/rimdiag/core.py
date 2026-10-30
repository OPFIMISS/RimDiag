from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
import xml.etree.ElementTree as ET


class DiagnosticError(ValueError):
    pass


MAX_LINE = 65536
MAX_EVENT = 16384
MAX_EVENTS = 100000
MAX_BYTES = 1024 * 1024 * 1024
MAX_METADATA = 1024 * 1024
ERROR = re.compile(
    r"(?:\b[\w.]*Exception\b|\b(?:ERROR|FATAL)\b|\bConfig error\b|"
    r"Could not (?:resolve|load|find)|Could not find type|Failed to (?:load|apply|initialize)|"
    r"Patch operation .*failed|XML error|XML format error|Duplicate (?:mod|package)|"
    r"duplicate packageId|Could not instantiate)", re.I)
START = re.compile(r"^(?:\[?\d{2}:\d{2}:\d{2}(?:\.\d+)?\]?\s*|\[(?:Error|Fatal|Warning|Info)\]\s*)", re.I)
STACK = re.compile(r"(?:^\s*(?:at |\(wrapper)|\b[\w.]+:[\w.]+\s*\()")
NAMESPACE = re.compile(r"(?:\bat\s+|^\s*)([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+)\s*[:.(]", re.M)


def bounded_xml(path: Path) -> ET.Element:
    # Only caller-selected ModsConfig and exact About metadata paths reach here.
    with path.open("rb") as stream:
        raw = stream.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise DiagnosticError("oversized_or_unsafe_metadata")
    return ET.fromstring(raw)


def normalize(text: str) -> str:
    text = START.sub("", text.strip())
    text = re.sub(r"\[Ref [A-Fa-f0-9]+\]", "[Ref <id>]", text)
    return re.sub(r"0x[A-Fa-f0-9]{6,}", "0x<address>", text)


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()[:24]


def category(text: str) -> dict:
    """Heuristic triage only; guidance never authorizes implementation access."""
    rules = [
        (r"MissingMethodException|MissingFieldException", "api_signature", "Check the named member against the matching vanilla version; do not guess a Mod owner."),
        (r"TypeLoadException|Could not find type|Could not (?:load|resolve).*type", "type_resolution", "Check version and declared dependencies; the type namespace is not a verified Mod ID."),
        (r"Patch operation.*failed|Failed to apply|XML error|XML format error", "xml_or_patch", "Inspect the logged operation and original error; reading Mod XML needs explicit authorization."),
        (r"Could not resolve.*(?:reference|Def)|Could not find.*(?:Def|defName)", "def_reference", "Check metadata dependencies and version; do not delete the referenced definition to hide errors."),
        (r"duplicate (?:mod|package)|duplicate packageId", "duplicate_identity", "Compare identity metadata; do not delete or disable installations automatically."),
        (r"NullReferenceException", "null_reference", "Read the inner evidence and plan a controlled reproduction; stack presence does not establish responsibility."),
        (r"TypeInitializationException|static constructor", "initialization", "Look for an inner failure; downstream initialization errors may be related but causality is unverified."),
    ]
    for pattern, name, guidance in rules:
        if re.search(pattern, text, re.I):
            return {"category": name, "next_check": guidance}
    return {"category": "unclassified", "next_check": "Read selected evidence; do not infer a culprit from a stack symbol."}


def limit(value: int, maximum: int = 20) -> int:
    if not 1 <= value <= maximum:
        raise DiagnosticError(f"limit_must_be_1_to_{maximum}")
    return value


class Diagnostics:
    def __init__(self, store: Path, logs: list[Path], config: Path | None = None,
                 mod_roots: list[Path] | None = None):
        self.store = store.resolve()
        self.store.mkdir(parents=True, exist_ok=True)
        self.logs = [p.resolve() for p in logs]
        if any(p.suffix.lower() not in (".log", ".txt") for p in self.logs):
            raise DiagnosticError("only_explicit_log_or_txt_inputs_allowed")
        self.config = config.resolve() if config else None
        self.mod_roots = [p.resolve() for p in mod_roots or []]

    @contextmanager
    def db(self, run_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise DiagnosticError("invalid_run_id")
        path = self.store / (run_id + ".db")
        if not path.is_file() or path.is_symlink():
            raise DiagnosticError("unknown_run")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def inventory(self) -> dict:
        active = []
        if self.config:
            root = bounded_xml(self.config)
            active = [(item.text or "").strip().lower() for item in root.findall("./activeMods/li")]
            if len(active) > 10000:
                raise DiagnosticError("active_list_too_large")
        records, warnings = [], []
        metadata_bytes = 0
        for directory in self.mod_roots:
            for index, child in enumerate(directory.iterdir()):
                if index >= 20000:
                    raise DiagnosticError("metadata_directory_limit")
                # No recursive source/Defs/Assemblies discovery. Reject redirected metadata.
                about = child / "About" / "About.xml"
                if not child.is_dir() or not about.is_file():
                    continue
                resolved = about.resolve()
                if not resolved.is_relative_to(directory):
                    warnings.append({"code": "metadata_outside_root", "folder": child.name[:120]})
                    continue
                metadata_bytes += resolved.stat().st_size
                if metadata_bytes > 32 * 1024 * 1024 or len(records) >= 4096:
                    raise DiagnosticError("metadata_budget_exceeded")
                try:
                    root = bounded_xml(resolved)
                    package = (root.findtext("packageId") or "").strip().lower()
                    if not package or len(package) > 200:
                        continue
                    dependencies = [x.text.strip().lower() for x in root.findall("./modDependencies/li/packageId") if x.text]
                    if len(dependencies) > 100 or any(len(x) > 200 for x in dependencies):
                        raise DiagnosticError("dependency_metadata_budget_exceeded")
                    records.append({"package_id": package, "name": (root.findtext("name") or "")[:160],
                                    "path": str(child.resolve()), "identity_source": "About/About.xml",
                                    "dependencies": dependencies,
                                    "versions": [(x.text or "")[:32] for x in root.findall("./supportedVersions/li")][:20]})
                except (OSError, ET.ParseError, DiagnosticError):
                    warnings.append({"code": "unreadable_about", "folder": child.name[:120]})
        return {"active_order": active, "records": records, "warnings": warnings,
                "scope": "identity_metadata_only", "actual_loaded_order_verified": False}

    def analyze(self, log_index: int = 0) -> dict:
        if not 0 <= log_index < len(self.logs):
            raise DiagnosticError("unknown_configured_log")
        inventory = self.inventory()
        run_id = uuid.uuid4().hex
        path = self.store / (run_id + ".db")
        db = sqlite3.connect(path)
        try:
            db.executescript("""CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE events(id INTEGER PRIMARY KEY, fingerprint TEXT, line INTEGER, end_line INTEGER,
                    headline TEXT, evidence TEXT, truncated INTEGER);
                CREATE INDEX event_fp ON events(fingerprint);
                CREATE TABLE groups(fingerprint TEXT PRIMARY KEY, count INTEGER, first_line INTEGER, last_line INTEGER,
                    headline TEXT, sample_id INTEGER);""")
            digest = hashlib.sha256()
            lines = total = event_count = clipped_lines = replacement_lines = 0
            incomplete = False
            pending = None

            def flush():
                nonlocal event_count, pending
                if pending is None:
                    return
                event_count += 1
                fp = fingerprint(pending["headline"])
                db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)", (event_count, fp, pending["line"],
                           pending["end"], pending["headline"], pending["text"], int(pending["truncated"])))
                db.execute("""INSERT INTO groups VALUES(?,1,?,?,?,?)
                    ON CONFLICT(fingerprint) DO UPDATE SET count=count+1,last_line=excluded.last_line""",
                           (fp, pending["line"], pending["end"], pending["headline"], event_count))
                pending = None

            with self.logs[log_index].open("rb") as stream:
                initial = stream.seek(0, 2)
                stream.seek(0)
                while total < min(initial, MAX_BYTES):
                    raw = stream.readline(min(MAX_LINE + 1, min(initial, MAX_BYTES) - total))
                    if not raw:
                        break
                    digest.update(raw)
                    total += len(raw)
                    lines += 1
                    clipped = len(raw) > MAX_LINE
                    clipped_lines += int(clipped)
                    # Consume long physical lines without loading them in memory.
                    if clipped and not raw.endswith(b"\n"):
                        while total < min(initial, MAX_BYTES):
                            tail = stream.readline(min(MAX_LINE, min(initial, MAX_BYTES) - total))
                            digest.update(tail)
                            total += len(tail)
                            if not tail or tail.endswith(b"\n"):
                                break
                    text = raw[:MAX_LINE].decode("utf-8-sig" if lines == 1 else "utf-8", "replace").rstrip()
                    replacement_lines += int("\ufffd" in text)
                    message = START.sub("", text)
                    if ERROR.search(text) and not STACK.search(message):
                        flush()
                        if event_count >= MAX_EVENTS:
                            incomplete = True
                            break
                        pending = {"headline": message[:2048], "line": lines, "end": lines,
                                   "text": text[:MAX_EVENT], "truncated": clipped or len(text) > MAX_EVENT}
                    elif pending is not None and (STACK.search(message) or message.startswith(("[Ref ", "--->", "   ", "  "))):
                        pending["end"] = lines
                        remaining = MAX_EVENT - len(pending["text"])
                        pending["text"] += ("\n" + text)[:max(0, remaining)]
                        pending["truncated"] |= clipped or len(text) + 1 > remaining
                    else:
                        flush()
                flush()
                final_size = stream.seek(0, 2)
            incomplete |= total < initial
            meta = {"run_id": run_id, "inventory": inventory, "bytes_read": total, "initial_bytes": initial,
                    "lines_read": lines, "sha256_of_read_bytes": digest.hexdigest(),
                    "input_changed_during_scan": final_size != initial, "incomplete": incomplete,
                    "truncated_line_count": clipped_lines, "decoding_replacement_lines": replacement_lines,
                    "source_policy": "no_implementation_access", "functional_status": "not_tested",
                    "encoding": "UTF-8 with replacement; non-UTF8 logs may lose identity text"}
            for key, value in meta.items():
                db.execute("INSERT INTO meta VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))
            db.commit()
        finally:
            db.close()
        return self.summary(run_id)

    def metadata(self, db) -> dict:
        return {row[0]: json.loads(row[1]) for row in db.execute("SELECT key,value FROM meta")}

    def summary(self, run_id: str) -> dict:
        with self.db(run_id) as db:
            meta = self.metadata(db)
            row = db.execute("SELECT COUNT(*),COALESCE(SUM(count),0) FROM groups").fetchone()
            active = meta["inventory"]["active_order"]
            known = {r["package_id"] for r in meta["inventory"]["records"]}
            return {k: meta[k] for k in ("run_id", "bytes_read", "lines_read", "incomplete", "input_changed_during_scan", "functional_status")} | {
                "recognized_error_events": row[1], "error_groups": row[0], "active_packages": len(active),
                "truncated_line_count": meta.get("truncated_line_count", 0),
                "decoding_replacement_lines": meta.get("decoding_replacement_lines", 0),
                "truncated_event_count": db.execute("SELECT COUNT(*) FROM events WHERE truncated=1").fetchone()[0],
                "unresolved_active_packages": sum(p not in known for p in active),
                "metadata_warnings": len(meta["inventory"]["warnings"]),
                "diagnosis": "candidates_only_no_causality", "actual_loaded_order_verified": False,
                "next": "list_errors then read_evidence for selected groups; never infer identity from namespaces"}

    def identity(self, text: str, inventory: dict) -> list[dict]:
        matches = []
        active = inventory["active_order"]
        for record in inventory["records"]:
            package = record["package_id"]
            explicit = re.search(r"(?<![\w.])" + re.escape(package) + r"(?![\w.])", text, re.I)
            # Paths must be full recorded installation roots, not assembly/namespace guesses.
            path = record["path"].replace("\\", "/").rstrip("/") + "/"
            path_hit = path.casefold() in text.replace("\\", "/").casefold()
            if explicit or path_hit:
                matches.append({"package_id": package, "name": record["name"],
                                "active_in_config": package in active, "basis": "exact_package_token" if explicit else "exact_install_path",
                                "causality": "unconfirmed", "duplicate_identity": sum(r["package_id"] == package for r in inventory["records"]) > 1})
            if len(matches) == 8:
                break
        return matches

    def list_errors(self, run_id: str, offset: int = 0, count: int = 10) -> dict:
        limit(count)
        if offset < 0:
            raise DiagnosticError("negative_offset")
        with self.db(run_id) as db:
            rows = db.execute("SELECT * FROM groups ORDER BY first_line,fingerprint LIMIT ? OFFSET ?", (count + 1, offset)).fetchall()
            result = []
            for row in rows[:count]:
                result.append({k: row[k] for k in ("fingerprint", "count", "first_line", "last_line")} |
                              {"headline": row["headline"][:360], "attribution": "not_established"} | category(row["headline"]))
            return {"run_id": run_id, "groups": result, "next_offset": offset + count if len(rows) > count else None,
                    "grouping": "same normalized headline, not proven same root cause", "order": "first occurrence, not causal order"}

    def evidence(self, run_id: str, group_id: str, occurrence: int = 0) -> dict:
        if not re.fullmatch(r"[a-f0-9]{24}", group_id) or not 0 <= occurrence < MAX_EVENTS:
            raise DiagnosticError("invalid_evidence_selector")
        with self.db(run_id) as db:
            row = db.execute("SELECT * FROM events WHERE fingerprint=? ORDER BY id LIMIT 1 OFFSET ?", (group_id, occurrence)).fetchone()
            if row is None:
                raise DiagnosticError("unknown_occurrence")
            inventory = self.metadata(db)["inventory"]
            return {"run_id": run_id, "group_id": group_id, "occurrence": occurrence,
                    "lines": [row["line"], row["end_line"]], "text": row["evidence"], "truncated": bool(row["truncated"]),
                    "identity_references": self.identity(row["evidence"], inventory),
                    "unverified_symbols": sorted(set(NAMESPACE.findall(row["evidence"])))[:12],
                    "causality": "unconfirmed", "content_is_untrusted_data": True}

    def list_inventory(self, run_id: str, offset: int = 0, count: int = 10) -> dict:
        limit(count)
        if offset < 0:
            raise DiagnosticError("negative_offset")
        with self.db(run_id) as db:
            inventory = self.metadata(db)["inventory"]
            active = inventory["active_order"]
            items = []
            for index, package in enumerate(active[offset:offset + count], offset):
                records = [r for r in inventory["records"] if r["package_id"] == package]
                compact = [{k: r[k] for k in ("package_id", "name", "identity_source")} |
                           {"dependency_count": len(r["dependencies"]), "dependencies_sample": r["dependencies"][:8],
                            "versions": r["versions"][:4]} for r in records[:3]]
                items.append({"order": index, "package_id": package, "matches": compact,
                              "identity_status": "ambiguous" if len(records) > 1 else "metadata_match" if records else "unresolved"})
            return {"items": items, "next_offset": offset + count if offset + count < len(active) else None,
                    "actual_loaded_order_verified": False, "warnings": inventory["warnings"][:10]}

    def compare(self, baseline_id: str, candidate_id: str) -> dict:
        with self.db(baseline_id) as base, self.db(candidate_id) as candidate:
            a = {r[0]: r[1] for r in base.execute("SELECT fingerprint,count FROM groups")}
            b = {r[0]: r[1] for r in candidate.execute("SELECT fingerprint,count FROM groups")}
            ma, mb = self.metadata(base), self.metadata(candidate)
            ia, ib = ma["inventory"], mb["inventory"]
            return {"shared_groups": len(a.keys() & b.keys()), "baseline_only_groups": len(a.keys() - b.keys()),
                    "candidate_only_groups": len(b.keys() - a.keys()), "candidate_only_sample": sorted(b.keys() - a.keys())[:20],
                    "increased_count_sample": [{"group": k, "baseline": a[k], "candidate": b[k]} for k in sorted(a.keys() & b.keys()) if b[k] > a[k]][:20],
                    "active_order_equal": ia["active_order"] == ib["active_order"],
                    "same_environment_proven": False, "shared_errors_ignored": False,
                    "baseline_incomplete": ma["incomplete"], "candidate_incomplete": mb["incomplete"],
                    "scope": "retained recognized error headlines only; consult summaries for truncation and input changes",
                    "causality": "not_established", "functional_status": "not_tested"}

    def isolation(self, run_id: str, remove_packages: list[str]) -> dict:
        if not 1 <= len(remove_packages) <= 100:
            raise DiagnosticError("select_1_to_100_packages")
        with self.db(run_id) as db:
            inventory = self.metadata(db)["inventory"]
        active = inventory["active_order"]
        records = inventory["records"]
        grouped = {p: [r for r in records if r["package_id"] == p] for p in active}
        if any(len(v) != 1 for v in grouped.values()) or len(set(active)) != len(active):
            return {"status": "unsupported", "reason": "active_metadata_missing_or_ambiguous", "files_modified": False}
        remove = set(p.lower() for p in remove_packages)
        if remove - set(active):
            raise DiagnosticError("package_not_in_snapshot")
        if any(p == "ludeon.rimworld" or p.startswith("ludeon.rimworld.") for p in remove):
            raise DiagnosticError("core_and_dlc_are_not_removal_candidates")
        changed = True
        while changed:
            previous = len(remove)
            for package in active:
                if set(grouped[package][0]["dependencies"]) & remove:
                    remove.add(package)
            changed = len(remove) != previous
        if any(p == "ludeon.rimworld" or p.startswith("ludeon.rimworld.") for p in remove):
            raise DiagnosticError("dependency_closure_would_remove_core_or_dlc")
        return {"status": "proposal_only", "files_modified": False,
                "removed_count": len(remove), "retained_count": len(active) - len(remove),
                "removed_including_dependents": [p for p in active if p in remove][:20],
                "proposed_order": [p for p in active if p not in remove][:20],
                "output_truncated": len(remove) > 20 or len(active) - len(remove) > 20,
                "limitations": ["metadata dependency closure only; optional/implicit/version dependencies unknown",
                                "not executed; not a culprit finding; use disposable RimProbe profiles only"],
                "game_launch_supported": False}
