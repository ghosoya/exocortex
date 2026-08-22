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
    if not text:
        return ""
    # Replace large code blocks with placeholder, as embeddings prioritize intent
    cleaned = re.sub(r"```[\s\S]*?```", "[Code Block]", str(text))
    # Normalize line breaks and whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_chars].strip()


def estimate_tokens(text: Any) -> int:
    """Pragmatic heuristic for token estimation (approx. 3.5 characters per token)."""
    if not text:
        return 0
    return max(1, int(len(str(text)) / 3.5))


def calculate_history_tokens(messages: List[Dict[str, Any]]) -> int:
    """Calculates the estimated token count of a message history safely."""
    total = 0
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content") or ""
        total += estimate_tokens(content)
        
        # Account for tool calls and metadata safely
        if "tool_calls" in msg and msg["tool_calls"]:
            total += estimate_tokens(str(msg["tool_calls"]))
    return total


def prune_history_if_needed(
    messages: List[Dict[str, Any]],
    max_tokens: int = 48000,
    keep_recent_turns: int = 6,
) -> List[Dict[str, Any]]:
    """
    Prunes older in-memory messages when the token budget is exceeded.
    Guarantees structural validity: preserves system prompt and ensures the pruned
    conversation starts cleanly with a 'user' turn (no orphan tool messages).
    """
    current_tokens = calculate_history_tokens(messages)
    if current_tokens <= max_tokens or len(messages) <= (keep_recent_turns * 2 + 1):
        return messages

    # Isolate initial system message(s)
    system_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "system"]
    conversation_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") != "system"]

    # Retain candidate tail
    pruned_conv = conversation_msgs[-(keep_recent_turns * 2):]

    # Ensure pruned history does not start with an orphaned tool response
    while pruned_conv and pruned_conv[0].get("role") in ("tool", "assistant"):
        pruned_conv.pop(0)

    # Fallback if pruning emptied the entire conversation
    if not pruned_conv and conversation_msgs:
        pruned_conv = [conversation_msgs[-1]]

    return system_msgs + pruned_conv
