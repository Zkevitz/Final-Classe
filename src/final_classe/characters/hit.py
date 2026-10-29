"""Hit : un coup porté pendant un combat."""

from dataclasses import dataclass

from final_classe.characters.base import Character


@dataclass(frozen=True)
class Hit:
    """Un coup porté : le nom de l'action, la cible, et les PV qu'elle a perdus."""

    action: str
    target: Character
    damage: int
