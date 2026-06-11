"""Append-only JSONL audit logger for the approval gate demo.

Records every tool call to logs/audit.jsonl, one JSON object per line.
Each entry captures the tool name, its arguments, the risk level, the
decision (auto, approved, or denied), the outcome, and a UTC timestamp.
The file is append-only: existing entries are never modified, so the
log is a complete history of what the agent did and who allowed it.

Author: Fay F.
"""

import json
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
LOG_PATH = os.path.join(LOG_DIR, "audit.jsonl")

# Keep very long tool outputs readable in the log.
MAX_OUTCOME_LENGTH = 2000


def _timestamp() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str) -> str:
    """Trim overly long outcome strings so log lines stay manageable."""
    if len(text) <= MAX_OUTCOME_LENGTH:
        return text
    return text[:MAX_OUTCOME_LENGTH] + " ...[truncated]"


def log_event(
    tool: str,
    args: dict,
    risk: str,
    decision: str,
    outcome: str,
) -> None:
    """Append one audit entry to logs/audit.jsonl.

    Arguments:
        tool: Name of the tool that was called.
        args: Arguments the model supplied for the call.
        risk: Risk level of the tool (safe or high_stakes).
        decision: How the call was handled: "auto" for safe tools,
            "approved" or "denied" for high stakes tools.
        outcome: Result string, error message, or denial reason.

    Logging failures are reported to the terminal but never raised, so
    a problem writing the log cannot crash the agent loop.
    """
    entry = {
        "timestamp": _timestamp(),
        "tool": tool,
        "args": args,
        "risk": risk,
        "decision": decision,
        "outcome": _truncate(str(outcome)),
    }

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"[audit] Warning: could not write audit log: {exc}")


def read_log() -> list:
    """Return all audit entries as a list of dicts.

    Useful for reviewing a session after it ends. Returns an empty list
    if the log file does not exist yet. Lines that fail to parse are
    skipped rather than raising, so a partially written line at the end
    of the file cannot break review.
    """
    if not os.path.exists(LOG_PATH):
        return []

    entries = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
