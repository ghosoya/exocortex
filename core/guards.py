"""
core/guards.py
Defensive Schranken: Token-Budgeting, History-Pruning und Embedding-Slicing.
"""

from typing import Any, Dict, List
import re


def slice_for_embedding(text: str, max_chars: int = 1500) -> str:
    """
    Entfernt Code-Blöcke und schneidet Text ab, damit das Embedding-Modell
    (z. B. bge-m3) niemals das Kontext-Limit überschreitet (Fix für HTTP 500).
    """
    # Große Code-Blöcke durch Platzhalter ersetzen, da Embeddings die Absicht brauchen
    cleaned = re.sub(r"```[\s\S]*?```", "[Code Block]", text)
    # Zeilenumbrüche und Whitespace normalisieren
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_chars].strip()


def estimate_tokens(text: str) -> int:
    """Pragmatische Heuristik für Token-Schätzung (ca. 3.5 Zeichen pro Token)."""
    return max(1, int(len(text) / 3.5))


def calculate_history_tokens(messages: List[Dict[str, Any]]) -> int:
    """Berechnet die geschätzte Tokenanzahl eines Chatverlaufs."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += estimate_tokens(content)
        # Tool-Calls und Tool-Responses mit einberechnen
        if "tool_calls" in msg:
            total += estimate_tokens(str(msg["tool_calls"]))
    return total


def prune_history_if_needed(
    messages: List[Dict[str, Any]],
    max_tokens: int = 48000,
    keep_recent_turns: int = 6
) -> List[Dict[str, Any]]:
    """
    Prunt ältere Nachrichten im Arbeitsspeicher, wenn das Token-Budget
    überschritten wird. Behält System-Prompt und die letzten N Züge intakt.
    """
    current_tokens = calculate_history_tokens(messages)
    if current_tokens <= max_tokens or len(messages) <= (keep_recent_turns * 2 + 1):
        return messages

    # System-Nachricht(en) am Anfang isolieren
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation_msgs = [m for m in messages if m.get("role") != "system"]

    # Nur die jüngsten N Züge behalten
    pruned_conv = conversation_msgs[-(keep_recent_turns * 2):]

    return system_msgs + pruned_conv
