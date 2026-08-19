"""
core/guards.py
Defensive guards: token budgeting, history pruning, and embedding slicing.
"""

from typing import Any, Dict, List
import re


def slice_for_embedding(text: str, max_chars: int = 1500) -> str:
    """
    Strips code blocks and truncates text so the embedding model
    (e.g., bge-m3) never exceeds its context limit (prevents HTTP 500 errors).
    """
    # Replace large code blocks with placeholder, as embeddings prioritize intent
    cleaned = re.sub(r"```[\s\S]*?```", "[Code Block]", text)
    # Normalize line breaks and whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_chars].strip()


def estimate_tokens(text: str) -> int:
    """Pragmatic heuristic for token estimation (approx. 3.5 characters per token)."""
    return max(1, int(len(text) / 3.5))


def calculate_history_tokens(messages: List[Dict[str, Any]]) -> int:
    """Calculates the estimated token count of a message history."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += estimate_tokens(content)
        # Account for tool calls and tool responses
        if "tool_calls" in msg:
            total += estimate_tokens(str(msg["tool_calls"]))
    return total


def prune_history_if_needed(
    messages: List[Dict[str, Any]],
    max_tokens: int = 48000,
    keep_recent_turns: int = 6,
) -> List[Dict[str, Any]]:
    """
    Prunes older in-memory messages when the token budget is exceeded.
    Keeps the system prompt and the most recent N turns intact.
    """
    current_tokens = calculate_history_tokens(messages)
    if current_tokens <= max_tokens or len(messages) <= (keep_recent_turns * 2 + 1):
        return messages

    # Isolate initial system message(s)
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation_msgs = [m for m in messages if m.get("role") != "system"]

    # Retain only the most recent N turns
    pruned_conv = conversation_msgs[-(keep_recent_turns * 2):]

    return system_msgs + pruned_conv
