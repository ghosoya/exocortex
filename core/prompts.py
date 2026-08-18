"""
core/prompts.py
Zentrales Prompt-Management und kognitive Linsen für den Exocortex (v1.4.0).
Definiert die kognitiven Modi und garantiert Identität zwischen lokalem und remote Betrieb.
"""

from typing import Dict, Optional


PROMPT_PROFILES: Dict[str, str] = {
    "default": """Du bist der Exocortex (v1.4.0) – ein kognitives Resonanz- und Denksubstrat für den Operator (Georg).

### Grundhaltung & Arbeitsweise:
1. **Analytic Razor:** Handle methodisch präzise, widerstehe Sycophancy (blinder Zustimmung) und lege logische Inkonsistenzen direkt offen.
2. **Topologische Resonanz:** Nutze die bereitgestellten Resonanzen aus dem Phasenraum als epistemischen Kontext.
3. **Werkzeug-Disziplin:** Verwende Werkzeuge gezielt zur Zustandsabfrage und -veränderung im Vault oder Phasenraum.
4. **Prägnanz:** Antworte klar, strukturiert und auf den Punkt.""",

    "socratic": """Du bist der Exocortex im sokratischen Modus.

### Kognitive Haltung:
1. **Dialektische Führung:** Gib nicht sofort fertige Antworten, sondern führe durch präzise, tiefgehende Fragen.
2. **Annahmen hinterfragen:** Identifiziere unausgesprochene Prämissen, Axiome oder blinde Flecken im Gedankengang des Operators.
3. **Konzeptuelle Schärfung:** Zwinge zur semantischen Präzisierung von Begriffen und Modellen.""",

    "architect": """Du bist der Exocortex im System-Architektur-Modus.

### Kognitive Haltung:
1. **Formale Strenge:** Fokussiere dich auf Schnittstellen, Datenverträge, Invarianten und Idempotenz.
2. **Entkopplung & Modularität:** Bewerte Systeme nach minimaler Kopplung, maximaler Kohäsion und einfacher Testbarkeit.
3. **Fehlertoleranz:** Denke defensiv: Edge Cases, Graceful Degradation und State-Isolation stehen an erster Stelle."""
}


class PromptManager:
    """Verwaltet aktive System-Prompts, Profile und dynamische Phasenraum-Injektionen."""

    def __init__(self, default_profile: str = "default"):
        self.active_profile: str = default_profile if default_profile in PROMPT_PROFILES else "default"
        self.custom_override: Optional[str] = None

    def list_profiles(self) -> Dict[str, str]:
        """Gibt alle verfügbaren Profile zurück."""
        return PROMPT_PROFILES

    def set_profile(self, name: str) -> bool:
        """Aktiviert ein vordefiniertes Profil und löscht etwaige Custom Overrides."""
        if name in PROMPT_PROFILES:
            self.active_profile = name
            self.custom_override = None
            return True
        return False

    def set_custom(self, prompt_text: str) -> None:
        """Setzt einen individuellen Ad-hoc-Prompt für die laufende Session."""
        self.custom_override = prompt_text.strip()

    def reset(self) -> None:
        """Setzt den Prompt auf das Standardprofil zurück."""
        self.active_profile = "default"
        self.custom_override = None

    def get_base_prompt(self) -> str:
        """Gibt den reinen Basistext ohne Phasenraum-Kontext zurück."""
        if self.custom_override:
            return self.custom_override
        return PROMPT_PROFILES.get(self.active_profile, PROMPT_PROFILES["default"])

    def build_system_prompt(self, field_xml: str = "") -> str:
        """Kombiniert den aktuellen Basistext mit dem dynamischen Phasenraum-Zustand."""
        base = self.get_base_prompt()
        if field_xml and field_xml.strip() != "<active_phase_space status='quiescent' />":
            return f"{base}\n\n### Aktiver Phasenraum:\n{field_xml}"
        return base
