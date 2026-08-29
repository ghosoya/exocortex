"""
core/prompts.py
Central prompt management and cognitive lenses for Exocortex.
Defines cognitive modes and guarantees behavioral identity across local and remote operation.
"""

from typing import Dict, Optional
from pathlib import Path
from core.config import settings

PROMPT_PROFILES: Dict[str, str] = {
    "default": """You are in Default Mode — a balanced, pragmatic thinking partner.

Focus:
- Provide clear, direct, and well-structured answers.
- Point out logical flaws, weak arguments, or overlooked trade-offs objectively.
- Use graph memory and the scratchpad when helpful, without adding unnecessary overhead.""",

    "socratic": """You are in Socratic Mode — a reflective sparring partner.

Focus:
- Help the user think things through by asking targeted, insightful questions rather than jumping straight to answers.
- Unpack hidden assumptions, blind spots, and conflicting requirements.
- Challenge vague statements and help clarify concepts step by step.""",

    "architect": """You are in Architect Mode — a technical reviewer for systems, code, and structured workflows.

Focus:
- Prioritize simplicity, modularity, and clean separation of concerns.
- Scrutinize interfaces, edge cases, error handling, and unintended side effects.
- Prefer proven, maintainable, and pragmatic designs over speculative complexity."""
}


class PromptManager:
    """Manages active system prompts, cognitive profiles, and dynamic phase-space injections."""

    def __init__(self, default_profile: str = "default", config_dir: Optional[Path] = None):
        self.active_profile: str = default_profile if default_profile in PROMPT_PROFILES else "default"
        self.custom_override: Optional[str] = None
        self.config_dir = config_dir or (settings.project_root / "config")
        self._system_base_cache: Optional[str] = self._load_system_base()

    def _load_system_base(self) -> Optional[str]:
        """Optionally loads global system base instructions from config/system_base.md."""
        base_file = self.config_dir / "system_base.md"
        if base_file.exists():
            try:
                content = base_file.read_text(encoding="utf-8").strip()
                return content if content else None
            except Exception:
                return None
        return None

    def list_profiles(self) -> Dict[str, str]:
        """Returns all available prompt profiles."""
        return PROMPT_PROFILES

    def set_profile(self, name: str) -> bool:
        """Activates a predefined profile and clears any active custom override."""
        if name in PROMPT_PROFILES:
            self.active_profile = name
            self.custom_override = None
            return True
        return False

    def set_custom(self, prompt_text: str) -> None:
        """Sets a custom ad-hoc prompt for the active session."""
        self.custom_override = prompt_text.strip()

    def reset(self) -> None:
        """Resets the prompt configuration to the default profile."""
        self.active_profile = "default"
        self.custom_override = None

    def get_base_prompt(self) -> str:
        """Returns the raw base prompt text combining system_base.md and the active profile."""
        if self.custom_override:
            return self.custom_override
        
        profile_text = PROMPT_PROFILES.get(self.active_profile, PROMPT_PROFILES["default"])
        if self._system_base_cache:
            return f"{self._system_base_cache}\n\n---\n\n{profile_text}"
        return profile_text

    def build_system_prompt(
        self, 
        field_xml: Optional[str] = "", 
        invariants_xml: Optional[str] = ""
    ) -> str:
        """
        Combines the active base prompt with:
        1. Immutable boundary invariants (always active, via negativa).
        2. Dynamic resonant phase-space state (retrieved per turn).
        """
        sections = [self.get_base_prompt()]

        if invariants_xml and invariants_xml.strip():
            sections.append(f"### Active Boundary Invariants:\n{invariants_xml.strip()}")

        if field_xml and field_xml.strip():
            sections.append(f"### Active Phase Space Topology:\n{field_xml.strip()}")

        return "\n\n".join(sections)
