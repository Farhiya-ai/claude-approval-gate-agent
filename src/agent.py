"""Claude tool-use agent loop with a human approval gate.

Sends the task to Claude, executes tool calls from the model, and routes
each call through the approval gate based on its risk level. Safe tools
run automatically. High stakes tools pause for a human decision in the
terminal. Denials are returned to the model as tool results so it can
adjust its plan. Every call and decision is written to the audit log.

Author: Fay F.
"""

import json

from anthropic import Anthropic

from src.approval import request_approval
from src.audit import log_event
from src.tools import execute_tool, get_risk_level, get_tool_schemas

SYSTEM_PROMPT = (
    "You are an assistant working with a small CRM. Use the available "
    "tools to complete the user's task. Some tools require human "
    "approval before they run. If a tool call is denied, respect the "
    "denial: do not retry the same call unchanged. If the human gives "
    "feedback, incorporate it. When the task is done, summarize what "
    "you did in plain language."
)

MAX_TURNS = 15
MAX_TOKENS = 1024


def _handle_tool_call(name: str, args: dict) -> str:
    """Run a single tool call through the approval gate and execute it.

    Returns the result string to send back to the model.
    """
    risk = get_risk_level(name)

    if risk == "high_stakes":
        decision, feedback = request_approval(name, args)
        if not decision:
            reason = feedback or "No reason given."
            log_event(
                tool=name,
                args=args,
                risk=risk,
                decision="denied",
                outcome=f"Denied by human. Feedback: {reason}",
            )
            return (
                "Tool call denied by human reviewer. "
                f"Feedback: {reason}"
            )
        decision_label = "approved"
    else:
        decision_label = "auto"

    try:
        result = execute_tool(name, args)
    except Exception as exc:
        log_event(
            tool=name,
            args=args,
            risk=risk,
            decision=decision_label,
            outcome=f"Error: {exc}",
        )
        return f"Tool error: {exc}"

    log_event(
        tool=name,
        args=args,
        risk=risk,
        decision=decision_label,
        outcome=result,
    )
    return result


def run_agent(task: str, api_key: str, model: str) -> str:
    """Run the agent loop until the model finishes or MAX_TURNS is hit.

    Returns the final text response from the model.
    """
    client = Anthropic(api_key=api_key)
    tools = get_tool_schemas()
    messages = [{"role": "user", "content": task}]
    final_text = ""

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Collect text and tool_use blocks from the response.
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if text_parts:
            final_text = "\n".join(text_parts)

        if response.stop_reason != "tool_use" or not tool_calls:
            break

        # Add the assistant turn (including tool_use blocks) to history.
        messages.append({"role": "assistant", "content": response.content})

        # Execute each requested tool and build tool_result blocks.
        tool_results = []
        for call in tool_calls:
            args = call.input if isinstance(call.input, dict) else {}
            print(f"[tool request] {call.name} {json.dumps(args)}")
            result = _handle_tool_call(call.name, args)
            print(f"[tool result] {result}\n")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": result,
                }
            )

        messages.append({"role": "user", "content": tool_results})
    else:
        final_text = (
            final_text
            or "Stopped: reached the maximum number of agent turns."
        )

    return final_text or "The model returned no final text."
