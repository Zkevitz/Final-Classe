"""Equipment : une pièce d'équipement, ses bonus, et ses emplacements de materia."""

from dataclasses import dataclass, field
from typing import Any, Self

from final_classe.items.kinds import Slot
from final_classe.items.materia import Materia, materia_from_dict
from final_classe.stats import Stats


@dataclass
class Equipment:
    """Une arme, une armure… : un emplacement, un prix, des bonus, et des materias.

    @dataclass écrit __init__, __repr__ et __eq__ à partir des champs annotés.
    """

    name: str
    slot: Slot
    price: int
    stats: Stats = field(default_factory=Stats)  # les bonus ; aucun par défaut
    slots: int = 0  # le nombre d'emplacements de materia
    materias: list[Materia] = field(default_factory=list)  # une liste neuve par pièce

    def __str__(self) -> str:
        """Pour le joueur : « Épée de mythril (arme, FOR +8, 2 emplacements) »."""
        details = [self.slot.value, self.stats.bonus_text()]
        if self.slots:
            details.append(f"{self.slots} emplacement{'s' if self.slots > 1 else ''}")
        return f"{self.name} ({', '.join(detail for detail in details if detail)})"

    def __lt__(self, other: Equipment) -> bool:
        """Plus petite si elle coûte moins cher : sorted() s'en sert."""
        return self.price < other.price

    def to_dict(self) -> dict[str, Any]:
        """La pièce en dictionnaire : l'Enum par sa valeur, les objets par leur to_dict."""
        return {
            "name": self.name,
            "slot": self.slot.value,
            "price": self.price,
            "stats": self.stats.to_dict(),
            "slots": self.slots,
            "materias": [materia.to_dict() for materia in self.materias],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Le chemin inverse : chaque valeur retrouve son type."""
        return cls(
            data["name"],
            Slot(data["slot"]),
            data["price"],
            Stats.from_dict(data["stats"]),
            data["slots"],
            [materia_from_dict(materia) for materia in data["materias"]],
        )

    def attach(self, materia: Materia) -> bool:
        """Monte une materia ; renvoie False s'il n'y a plus d'emplacement libre."""
        if len(self.materias) >= self.slots:
            return False
        self.materias.append(materia)
        return True

    def detach(self, materia: Materia) -> bool:
        """Retire une materia ; renvoie False si elle n'est pas montée ici."""
        if materia not in self.materias:
            return False
        self.materias.remove(materia)
        return True
