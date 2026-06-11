"""Tool registry and mock implementations for the approval gate demo.

Maps each tool name to a handler, a JSON schema for Claude, and a risk
level. Read-only tools (search_contacts, get_record) are marked safe and
run automatically. Tools with side effects (send_email, update_record)
are marked high_stakes and require human approval before running.

All tools operate on the local sample dataset in data/sample_records.json
so the demo runs end to end with no external services.

Author: Fay F.
"""

import json
import os

DATA_PATH = os.path.join("data", "sample_records.json")

RISK_SAFE = "safe"
RISK_HIGH = "high_stakes"


def _load_data() -> dict:
    """Load the sample dataset from disk."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Sample data not found at {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(data: dict) -> None:
    """Write the sample dataset back to disk."""
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def search_contacts(query: str) -> str:
    """Return contacts whose name, email, or company matches the query."""
    data = _load_data()
    query_lower = query.lower().strip()
    matches = []
    for contact in data.get("contacts", []):
        haystack = " ".join(
            str(contact.get(field, ""))
            for field in ("name", "email", "company")
        ).lower()
        if query_lower in haystack:
            matches.append(contact)
    if not matches:
        return f"No contacts found matching '{query}'."
    return json.dumps(matches, indent=2)


def get_record(record_id: str) -> str:
    """Return the full record for a contact by its id."""
    data = _load_data()
    for contact in data.get("contacts", []):
        if contact.get("id") == record_id:
            return json.dumps(contact, indent=2)
    return f"No record found with id '{record_id}'."


def send_email(to: str, subject: str, body: str) -> str:
    """Mock email send. Prints the email instead of sending it."""
    print("\n[mock email sent]")
    print(f"  To:      {to}")
    print(f"  Subject: {subject}")
    print(f"  Body:    {body}\n")
    return f"Email sent to {to} with subject '{subject}'."


def update_record(record_id: str, field: str, value: str) -> str:
    """Update one field on a contact record and save the dataset."""
    if field == "id":
        return "Error: the id field cannot be changed."
    data = _load_data()
    for contact in data.get("contacts", []):
        if contact.get("id") == record_id:
            old_value = contact.get(field, "<unset>")
            contact[field] = value
            _save_data(data)
            return (
                f"Record {record_id} updated: {field} changed from "
                f"'{old_value}' to '{value}'."
            )
    return f"No record found with id '{record_id}'."


TOOLS = {
    "search_contacts": {
        "handler": search_contacts,
        "risk": RISK_SAFE,
        "schema": {
            "name": "search_contacts",
            "description": (
                "Search contacts by name, email, or company. Returns "
                "matching contact records as JSON."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to match against contacts.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    "get_record": {
        "handler": get_record,
        "risk": RISK_SAFE,
        "schema": {
            "name": "get_record",
            "description": (
                "Fetch the full record for a single contact by its id."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "The contact id, for example c-001.",
                    }
                },
                "required": ["record_id"],
            },
        },
    },
    "send_email": {
        "handler": send_email,
        "risk": RISK_HIGH,
        "schema": {
            "name": "send_email",
            "description": (
                "Send an email to a contact. Requires human approval "
                "before it runs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Plain text email body.",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    "update_record": {
        "handler": update_record,
        "risk": RISK_HIGH,
        "schema": {
            "name": "update_record",
            "description": (
                "Update one field on a contact record. Requires human "
                "approval before it runs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "The contact id, for example c-001.",
                    },
                    "field": {
                        "type": "string",
                        "description": (
                            "Field to update, for example notes or email."
                        ),
                    },
                    "value": {
                        "type": "string",
                        "description": "New value for the field.",
                    },
                },
                "required": ["record_id", "field", "value"],
            },
        },
    },
}


def get_tool_schemas() -> list:
    """Return the JSON schemas for all tools, for the Claude API."""
    return [entry["schema"] for entry in TOOLS.values()]


def get_risk_level(name: str) -> str:
    """Return the risk level for a tool. Unknown tools are high stakes."""
    entry = TOOLS.get(name)
    if entry is None:
        return RISK_HIGH
    return entry["risk"]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with the given arguments.

    Raises ValueError for unknown tools or bad arguments.
    """
    entry = TOOLS.get(name)
    if entry is None:
        raise ValueError(f"Unknown tool: {name}")
    try:
        return entry["handler"](**args)
    except TypeError as exc:
        raise ValueError(f"Bad arguments for {name}: {exc}") from exc
