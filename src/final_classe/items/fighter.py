"""Fighter : ce dont les objets et les materias ont besoin d'un combattant.

items/ ne connaît pas Character : il décrit seulement ce qu'il attend. Tout objet qui a
ces propriétés et ces méthodes convient, sans hériter de rien.
"""

from typing import Protocol

from final_classe.items.kinds import Element


class Fighter(Protocol):
    """Un combattant, vu par un objet ou une materia."""

    @property
    def magic(self) -> int:
        """La MAG."""
        ...

    def magic_attack(self, target: Fighter, power: int, element: Element | None = None) -> int:
        """Une attaque magique ; renvoie les PV perdus par la cible."""
        ...

    def heal(self, amount: int) -> int:
        """Rend des PV ; renvoie les PV rendus."""
        ...

    def restore_mp(self, amount: int) -> int:
        """Rend des PM ; renvoie les PM rendus."""
        ...

    def revive(self) -> int:
        """Relève un combattant K.O. ; renvoie les PV rendus."""
        ...
