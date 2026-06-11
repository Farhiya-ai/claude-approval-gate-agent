"""Entry point for the claude-approval-gate-agent demo.

Loads environment variables, takes a task from the command line (or uses
a default demo task), and runs the agent loop against the mock CRM tools.

Author: Fay F.
"""

import os
import sys

from dotenv import load_dotenv

from src.agent import run_agent

DEFAULT_TASK = (
    "Find the contact named Dana Reyes and email her a meeting reminder "
    "for Thursday."
)

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def main() -> int:
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print(
            "Error: ANTHROPIC_API_KEY is not set.\n"
            "Copy .env.example to .env and add your API key.",
            file=sys.stderr,
        )
        return 1

    model = os.getenv("MODEL_NAME", DEFAULT_MODEL)

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:]).strip()
    else:
        task = DEFAULT_TASK

    if not task:
        print("Error: task is empty.", file=sys.stderr)
        return 1

    print(f"Task: {task}\n")

    try:
        final_text = run_agent(task=task, api_key=api_key, model=model)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError while running agent: {exc}", file=sys.stderr)
        return 1

    print("\n--- Final response ---")
    print(final_text)
    print("\nAudit log written to logs/audit.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
