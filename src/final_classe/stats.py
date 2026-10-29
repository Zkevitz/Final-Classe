"""Stats : les cinq statistiques, rangées ensemble.

Ni personnage ni objet : items/ et characters/ s'en servent tous les deux. Ce module
n'importe rien du jeu, il ne peut donc pas créer d'import circulaire.
"""

from dataclasses import asdict, dataclass
from typing import Any, Self


@dataclass(frozen=True)
class Stats:
    """FOR, MAG, DÉF, RÉS et VIT. Gelée : on ne la modifie pas, on en crée une autre."""

    strength: int = 0
    magic: int = 0
    defense: int = 0
    resistance: int = 0
    speed: int = 0

    def __add__(self, other: Stats) -> Stats:
        """Additionne champ à champ : la base, plus le bonus d'une pièce."""
        return Stats(
            self.strength + other.strength,
            self.magic + other.magic,
            self.defense + other.defense,
            self.resistance + other.resistance,
            self.speed + other.speed,
        )

    def to_dict(self) -> dict[str, int]:
        """Les cinq valeurs, dans un dictionnaire : prêt pour le JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Le constructeur inverse : une Stats, à partir de son dictionnaire."""
        return cls(**data)

    def bonus_text(self) -> str:
        """Les seuls bonus non nuls, pour l'étal de Cid : « FOR +8, RÉS +6 »."""
        values = {
            "FOR": self.strength,
            "MAG": self.magic,
            "DÉF": self.defense,
            "RÉS": self.resistance,
            "VIT": self.speed,
        }
        return ", ".join(f"{label} +{value}" for label, value in values.items() if value)

    def __str__(self) -> str:
        """La ligne de la fiche : FOR 25  MAG 21  DÉF 25  RÉS 21  VIT 12."""
        return (
            f"FOR {self.strength}  MAG {self.magic}  DÉF {self.defense}  "
            f"RÉS {self.resistance}  VIT {self.speed}"
        )
