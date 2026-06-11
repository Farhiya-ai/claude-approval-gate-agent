"""Terminal approval gate for high stakes tool calls.

Prints the pending tool call with its arguments, then prompts the human
reviewer to approve, deny, or deny with feedback. The decision is
returned to the agent loop so denials (and any feedback) flow back to
the model as tool results.

Author: Fay F.

"""

import json

PROMPT = (
    "  [a] approve and run\n"
    "  [d] deny\n"
    "  [f] deny with feedback\n"
    "Decision (a/d/f): "
)


def _format_args(args: dict) -> str:
    """Pretty-print tool arguments for human review."""
    if not args:
        return "  (no arguments)"
    try:
        rendered = json.dumps(args, indent=2)
    except (TypeError, ValueError):
        rendered = str(args)
    return "\n".join(f"  {line}" for line in rendered.splitlines())


def request_approval(tool_name: str, args: dict) -> tuple:
    """Ask the human reviewer to approve or deny a pending tool call.

    Returns a tuple of (approved, feedback):
      - (True, "") if the call is approved.
      - (False, "") if denied with no feedback.
      - (False, "<text>") if denied with feedback for the model.
    """
    print("\n" + "=" * 60)
    print("APPROVAL REQUIRED: high stakes tool call")
    print("=" * 60)
    print(f"Tool: {tool_name}")
    print("Arguments:")
    print(_format_args(args))
    print("-" * 60)

    while True:
        try:
            choice = input(PROMPT).strip().lower()
        except EOFError:
            # No interactive input available; treat as a denial so the
            # model knows the action was not carried out.
            print("\nNo input available. Treating as denied.")
            return False, "No human reviewer available to approve."

        if choice in ("a", "approve", "y", "yes"):
            print("Approved. Running tool.\n")
            return True, ""

        if choice in ("d", "deny", "n", "no"):
            print("Denied.\n")
            return False, ""

        if choice in ("f", "feedback"):
            try:
                feedback = input("Feedback for the model: ").strip()
            except EOFError:
                feedback = ""
            print("Denied with feedback.\n")
            return False, feedback

        print("Invalid choice. Enter 'a', 'd', or 'f'.")
