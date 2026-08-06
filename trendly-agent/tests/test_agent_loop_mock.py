"""
Mocks the Groq client to exercise the actual ReAct loop (message formatting,
tool_call_id round-tripping, multi-iteration chaining, iteration-cap
fallback) without hitting the real API or needing a key. Not a substitute
for tests/test_conversations.py against the real model - this only proves
the plumbing works.

Run with: python tests/test_agent_loop_mock.py
"""
import sys
import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import os
os.environ.setdefault("GROQ_API_KEY", "mock-key-for-offline-test")


def _tool_call(name, args, call_id="call_1"):
    tc = types.SimpleNamespace()
    tc.id = call_id
    tc.function = types.SimpleNamespace(name=name, arguments=json.dumps(args))
    tc.model_dump = lambda: {"id": call_id, "type": "function",
                              "function": {"name": name, "arguments": json.dumps(args)}}
    return tc


def _response(tool_calls=None, content=None):
    msg = types.SimpleNamespace(tool_calls=tool_calls, content=content)
    choice = types.SimpleNamespace(message=msg)
    return types.SimpleNamespace(choices=[choice])


def test_single_tool_call_then_final_answer():
    from app import agent

    call_sequence = [
        _response(tool_calls=[_tool_call("get_order_status",
                   {"order_id": "TRD-1001", "email": "priya.sharma@example.com"})]),
        _response(content="Your order TRD-1001 is delivered."),
    ]
    mock_create = MagicMock(side_effect=call_sequence)

    with patch.object(agent.client.chat.completions, "create", mock_create):
        text, history, trace = agent.run_turn([], "Where's my order TRD-1001, email priya.sharma@example.com?")

    assert "delivered" in text.lower()
    assert len(trace) == 1
    assert trace[0]["tool"] == "get_order_status"
    assert trace[0]["result"]["found"] is True
    assert history[-1]["role"] == "assistant"
    print("PASS: single tool call -> final answer")


def test_iteration_cap_triggers_escalation_fallback():
    from app import agent

    # Model keeps calling a tool forever, never returns a final answer
    infinite_calls = _response(tool_calls=[_tool_call("search_policy", {"query": "x"})])
    mock_create = MagicMock(return_value=infinite_calls)

    with patch.object(agent.client.chat.completions, "create", mock_create):
        text, history, trace = agent.run_turn([], "some looping request")

    assert "escalated" in text.lower()
    assert trace[-1]["tool"].startswith("escalate_to_human")
    assert mock_create.call_count == agent.MAX_TOOL_ITERATIONS
    print("PASS: iteration cap falls back to escalation instead of looping forever")


def test_multi_step_chain_order_then_eligibility():
    from app import agent

    call_sequence = [
        _response(tool_calls=[_tool_call("get_order_status",
                   {"order_id": "TRD-1001", "email": "priya.sharma@example.com"}, "c1")]),
        _response(tool_calls=[_tool_call("check_return_eligibility",
                   {"order_id": "TRD-1001", "request_type": "return", "reason": "changed_mind"}, "c2")]),
        _response(content="Good news, you're eligible for a return."),
    ]
    mock_create = MagicMock(side_effect=call_sequence)

    with patch.object(agent.client.chat.completions, "create", mock_create):
        text, history, trace = agent.run_turn([], "I want to return TRD-1001, email priya.sharma@example.com")

    assert len(trace) == 2
    assert [t["tool"] for t in trace] == ["get_order_status", "check_return_eligibility"]
    print("PASS: multi-step tool chaining (lookup -> eligibility) works")


if __name__ == "__main__":
    test_single_tool_call_then_final_answer()
    test_iteration_cap_triggers_escalation_fallback()
    test_multi_step_chain_order_then_eligibility()
    print("\nAll mock ReAct-loop tests passed.")
