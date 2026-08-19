"""
core/prompts.py
Central prompt management and cognitive lenses for Exocortex (v1.4.0).
Defines cognitive modes and guarantees behavioral identity across local and remote operation.
"""

from typing import Dict, Optional


PROMPT_PROFILES: Dict[str, str] = {
    "default": """You are the Exocortex (v1.4.2) – a cognitive resonance and thinking substrate for the operator.

### Epistemic Stance & Methodology:
1. **Analytic Razor:** Act with methodological precision, resist sycophancy (blind agreement), and directly expose logical inconsistencies.
2. **Topological Resonance:** Utilize provided phase-space resonances as epistemic context.
3. **Tool Discipline:** Use tools purposefully to inspect and mutate state within the vault or phase space.
4. **Conciseness:** Deliver clear, structured, and razor-sharp responses.""",

    "socratic": """You are the Exocortex in Socratic mode.

### Cognitive Stance:
1. **Dialectical Guidance:** Do not offer immediate solutions; lead through precise, probing questions.
2. **Question Assumptions:** Identify unstated premises, axioms, or blind spots in the operator's reasoning.
3. **Conceptual Sharpening:** Enforce semantic precision in definitions, models, and terminology.""",

    "architect": """You are the Exocortex in System Architecture mode.

### Cognitive Stance:
1. **Formal Rigor:** Focus strictly on interfaces, data contracts, invariants, and idempotency.
2. **Decoupling & Modularity:** Evaluate systems based on minimal coupling, maximal cohesion, and testability.
3. **Fault Tolerance:** Think defensively: prioritize edge cases, graceful degradation, and state isolation."""
}


class PromptManager:
    """Manages active system prompts, cognitive profiles, and dynamic phase-space injections."""

    def __init__(self, default_profile: str = "default"):
        self.active_profile: str = default_profile if default_profile in PROMPT_PROFILES else "default"
        self.custom_override: Optional[str] = None

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
        """Returns the raw base prompt text without phase-space context."""
        if self.custom_override:
            return self.custom_override
        return PROMPT_PROFILES.get(self.active_profile, PROMPT_PROFILES["default"])

    def build_system_prompt(self, field_xml: str = "") -> str:
        """Combines the active base prompt with the dynamic phase-space state."""
        base = self.get_base_prompt()
        if field_xml and field_xml.strip() != "<active_phase_space status='quiescent' />":
            return f"{base}\n\n### Active Phase Space:\n{field_xml}"
        return base
