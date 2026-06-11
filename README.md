# claude-approval-gate-agent

A Claude tool-use agent loop in Python where high stakes actions pause for human approval in the terminal, while read-only tools run automatically. Every tool call is recorded in an append-only audit log.

The demo runs end to end against a small mock CRM dataset included in the repo, so the only external service it needs is the Anthropic API.

## What it does

The agent receives a task, then works through it using four tools:

| Tool | Risk level | Behavior |
| --- | --- | --- |
| `search_contacts` | safe | Runs automatically |
| `get_record` | safe | Runs automatically |
| `send_email` | high_stakes | Pauses for human approval |
| `update_record` | high_stakes | Pauses for human approval |

When the model requests a high stakes tool, the loop stops and prints the exact tool call and arguments to the terminal. A human reviewer can approve the call, deny it, or deny it with feedback. Denials and feedback flow back to the model as tool results, so it can adjust its plan instead of failing silently.

Every call, automatic or gated, is appended to `logs/audit.jsonl` with the tool name, arguments, risk level, decision, outcome, and a UTC timestamp.

## Why approval gates matter

Agentic systems are most useful when they can take real actions: sending emails, updating records, moving money. Those are also exactly the actions where a mistake is expensive or irreversible. A practical middle ground is to let the agent read and search freely, but require a human sign-off before anything is written or sent.

This pattern gives you:

- Safety on irreversible actions without slowing down read-only work.
- A clear accountability trail showing what the agent did and who allowed it.
- A feedback channel: a denial with feedback teaches the model what to do instead, within the same session.

## Quickstart

Requires Python 3.10 or newer and an Anthropic API key.

git clone <this repo>
cd claude-approval-gate-agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY to your key
python main.py

Run with a custom task:

python main.py "Find the contact at Northwind Logistics and email them about scheduling the follow-up call they requested."

With no argument, a default demo task is used that exercises both safe and high stakes tools.

## Example terminal session

Task: Find the contact at Northwind Logistics and email them about
scheduling the follow-up call they requested.

[auto] search_contacts {"query": "Northwind Logistics"}
[auto] get_record {"record_id": "c-002"}

============================================================
APPROVAL REQUIRED: high stakes tool call
============================================================
Tool: send_email
Arguments:
  {
    "to": "d.reyes@northwindlogistics.example.com",
    "subject": "Scheduling your follow-up call",
    "body": "Hi Daniel, following up on your request..."
  }
------------------------------------------------------------
  [a] approve and run
  [d] deny
  [f] deny with feedback
Decision (a/d/f): a
Approved. Running tool.

Agent: I found Daniel Reyes at Northwind Logistics and sent him an
email proposing times for the follow-up call he requested.

If you choose `f`, you can type a short note such as "ask for their availability instead of proposing times" and the model receives it as the tool result, then revises its approach.

## How it works

### Agent loop (`src/agent.py`)

The loop sends the conversation to Claude with the tool definitions attached. When the response contains `tool_use` blocks, each one is routed by risk level:

1. Safe tools are executed immediately and logged with decision `auto`.
2. High stakes tools go through the approval gate first. Approved calls execute and log as `approved`. Denied calls return a denial message (plus any feedback) to the model as the tool result and log as `denied`.

Tool results are appended to the conversation and the loop continues until the model produces a final text response with no further tool calls.

### Tool registry (`src/tools.py`)

Tools are defined in a single registry that maps each name to its handler function, JSON schema, and risk level. The agent loop and the approval gate both read from this registry, so adding a new tool means adding one entry: the routing, gating, and logging come for free. The mock handlers read and write `data/sample_records.json`, and `send_email` simulates sending without contacting any real mail service.

### Approval gate (`src/approval.py`)

Prints the pending call with pretty-printed arguments, then prompts for a decision. If no interactive input is available, the call is treated as denied so the agent never proceeds without a human in the loop.

### Audit log (`src/audit.py`)

Appends one JSON object per line to `logs/audit.jsonl`. Entries are never modified after writing. A `read_log` helper is included for reviewing a session after it ends.

Example log line:

{"timestamp": "2025-01-15T14:32:08.421901+00:00", "tool": "send_email", "args": {"to": "d.reyes@northwindlogistics.example.com", "subject": "Scheduling your follow-up call", "body": "Hi Daniel..."}, "risk": "high_stakes", "decision": "approved", "outcome": "Email queued for delivery to d.reyes@northwindlogistics.example.com"}

## Configuration

Set these in `.env` (see `.env.example`):

| Variable | Required | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key. Read from the environment only; never hardcode it. |
| `MODEL_NAME` | No | Override the default Claude model used by the agent loop. |

To change which tools require approval, edit the `risk` field on the relevant entry in the tool registry in `src/tools.py`. Anything marked `high_stakes` is gated; anything marked `safe` runs automatically.

## Project structure

claude-approval-gate-agent/
  main.py                  Entry point: loads env, accepts a task, runs the loop
  requirements.txt         Pinned dependencies
  .env.example             Placeholder environment variables
  src/
    agent.py               Claude tool-use agent loop with approval routing
    tools.py               Tool registry: handlers, schemas, risk levels
    approval.py            Terminal approval gate
    audit.py               Append-only JSONL audit logger
  data/
    sample_records.json    Mock CRM dataset used by the tools
  logs/
    audit.jsonl            Created at runtime; full audit trail

## Author

Fay F.
