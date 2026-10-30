"""Versioned log-format adapters. No Mod implementation or namespace ownership lookup."""
import hashlib
import re

PARSER_VERSION = 3
CLOCK = re.compile(r"^\[?(?:(?:\d{4}-\d{2}-\d{2})[ T])?\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\]?\s*")
LEVEL = re.compile(r"^(?:\[((?i:ERROR|FATAL|WARNING|WARN|INFO|DEBUG|TRACE))\]|(ERROR|FATAL|WARNING|WARN|INFO|DEBUG|TRACE)\b:?)\s*")
THREAD = re.compile(r"^\[(?:메인|Main|主线程)\]\s*", re.I)
STACK = re.compile(r"^(?:at |\(wrapper)|\b[\w.]+:[\w.]+\s*\(")
NAMESPACE = re.compile(r"(?:\bat\s+|^\s*)([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+)\s*[:.(]", re.M)
ERROR = re.compile(
    r"(?:\b[\w.]*Exception\b|\b(?:ERROR|FATAL)\b|\bConfig error\b|"
    r"Could not (?:resolve|load|find)|Failed to (?:load|apply|initialize)|"
    r"Patch operation .*failed|XML error|XML format error|Duplicate (?:mod|package)|"
    r"duplicate packageId|Could not instantiate)", re.I)
ANNOTATION = re.compile(r"^\[[^\]\n]{1,100}\]\s*(?:Likely cause:|Shown \d+ times\.|.*repeats.*hidden)", re.I)
INNER = re.compile(r"(?<![\w.])([A-Za-z_][\w.+`]*Exception)\s*:")
SECTION = re.compile(r"^===\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b.*===\s*$")


def split_prefix(text: str) -> dict:
    message = CLOCK.sub("", text.lstrip(), count=1)
    level = LEVEL.match(message)
    severity = (level.group(1) or level.group(2)).upper() if level else None
    if level:
        message = message[level.end():]
        # Known vanilla logger. Preserve unknown logger/Mod tags in the message.
        if message.startswith("[Verse]"):
            message = message[len("[Verse]"):].lstrip()
    message = THREAD.sub("", message, count=1)
    hint = None
    if message.startswith("[Likely:"):
        depth = 0
        for i, char in enumerate(message[:512]):
            depth += (char == "[") - (char == "]")
            if depth == 0:
                hint = message[len("[Likely:"):i].strip()[:200]
                message = message[i + 1:].lstrip()
                break
    return {"message": message, "severity": severity, "reported_attribution": hint}


def normalize(text: str) -> str:
    text = split_prefix(text)["message"].strip()
    text = re.sub(r"\[Ref [A-Fa-f0-9]+\]", "[Ref <id>]", text)
    return re.sub(r"0x[A-Fa-f0-9]{6,}", "0x<address>", text)


def is_continuation(message: str) -> bool:
    return bool(STACK.search(message) or message.startswith(("--->", "--- End of", "[Ref ")))


RULES = [
    (r"MissingMethodException|MissingFieldException", "api_signature", "Check the named member against the matching vanilla version; do not guess a Mod owner."),
    (r"TypeLoadException|Could not find (?:a )?(?:type|class)|Could not (?:load|resolve).*type", "type_resolution", "Check version and declared dependencies; the type namespace is not a verified Mod ID."),
    (r"Patch operation.*failed|Failed to apply|XML error|XML format error|Start of stack trace", "xml_or_patch", "Inspect the logged operation and original error; reading Mod XML needs explicit authorization."),
    (r"Could not resolve.*(?:reference|Def)|Could not find.*(?:Def|defName)", "def_reference", "Check metadata dependencies and version; do not delete the referenced definition to hide errors."),
    (r"Config error in", "def_configuration", "Check recorded Def validation and preceding type-resolution errors; neither a common cause nor permission to read Mod XML is established."),
    (r"duplicate (?:mod|package)|duplicate packageId", "duplicate_identity", "Compare identity metadata; do not delete or disable installations automatically."),
    (r"Created WorkshopItem .*no folder", "workshop_folder", "Check the recorded Workshop item and installation folder; no Mod identity or responsibility is established."),
    (r"No active language!", "language_not_ready", "Observe language initialization and the original preceding errors; do not automatically ignore diagnostic-tool errors."),
    (r"Error while instantiating a mod|TypeInitializationException|static constructor|post-long-event", "initialization", "Read the entire inner-exception chain; outer initialization errors do not establish responsibility."),
    (r"HarmonyException|Patching exception|InvalidProgramException", "patch_runtime", "Read inner failures and compare controlled runs; a patch stack is not a culprit finding."),
    (r"NullReferenceException", "null_reference", "Read the inner evidence and plan a controlled reproduction; stack presence does not establish responsibility."),
]
CATEGORIES = {rule[1] for rule in RULES} | {"unclassified"}


def category(text: str) -> dict:
    text = split_prefix(text)["message"]
    for pattern, name, guidance in RULES:
        if re.search(pattern, text, re.I):
            return {"category": name, "next_check": guidance}
    return {"category": "unclassified", "next_check": "Read selected evidence; do not infer a culprit from a stack symbol."}


def symptom(text: str) -> tuple[str, str]:
    text = normalize(text)
    missing = re.search(r"Could not find (?:a )?(?:type|class)(?: named)?\s+([\w.+`]+)", text, re.I)
    field = re.search(r"XML error:\s*<([\w]+)[ >].{0,1600}?doesn't correspond to any field in type\s+([\w.+`]+)", text, re.I)
    config = re.search(r"Config error in [^:]{1,160}:\s*(.+)", text)
    if missing:
        key = "missing_type:" + missing.group(1).rstrip(".")
    elif field:
        key = "xml_field:" + field.group(2).rstrip(".") + "." + field.group(1)
    elif "No active language!" in text:
        key = "language_not_ready"
    elif config:
        key = "def_configuration:" + config.group(1)
    elif re.search(r"Created WorkshopItem .*no folder", text):
        key = "workshop_folder_missing"
    else:
        key = text
    return hashlib.sha256(key.encode()).hexdigest()[:24], key[:200]


def annotations(text: str) -> list[dict]:
    hints = []
    for line in text.splitlines():
        parsed = split_prefix(line)
        hint = parsed["reported_attribution"]
        if not hint and ANNOTATION.search(parsed["message"]):
            match = re.search(r"Likely cause:\s*(.*)", parsed["message"], re.I)
            hint = match.group(1)[:200] if match else None
        if hint and hint not in hints:
            hints.append(hint)
    return [{"label": hint, "source": "log_reporter", "verified": False, "causality": "unconfirmed"} for hint in hints[:4]]


def identity_text(text: str) -> str:
    # Third-party diagnostic guesses must not become metadata-backed identity evidence.
    messages = [split_prefix(line)["message"] for line in text.splitlines()]
    return "\n".join(line for line in messages if not ANNOTATION.search(line))
