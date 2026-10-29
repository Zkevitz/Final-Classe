"""Les materias : une famille, donc une classe abstraite et des filles."""

from abc import ABC, abstractmethod
from typing import Any, Self, override

from final_classe.items.fighter import Fighter
from final_classe.items.kinds import Element, Target


class Materia(ABC):
    """Une materia, montée sur une pièce d'équipement : elle donne un sort."""

    TARGET = Target.ENEMY

    def __init__(self, name: str, cost: int, power: int) -> None:
        self.name = name
        self.cost = cost  # en PM
        self.power = power

    @abstractmethod
    def cast(self, caster: Fighter, target: Fighter) -> int:
        """Lance le sort sur une cible ; renvoie les dégâts ou les PV rendus."""

    def to_dict(self) -> dict[str, Any]:
        """La materia en dictionnaire ; "kind" dit quelle classe la recréera."""
        return {
            "kind": type(self).__name__,
            "name": self.name,
            "cost": self.cost,
            "power": self.power,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Recrée une materia de la classe cls, celle sur laquelle on l'appelle."""
        return cls(data["name"], data["cost"], data["power"])


class AttackMateria(Materia):
    """Feu, Glace, Foudre : une attaque magique."""

    def __init__(self, name: str, cost: int, power: int, element: Element | None = None) -> None:
        super().__init__(name, cost, power)
        self.element = element

    @override
    def cast(self, caster: Fighter, target: Fighter) -> int:
        """Une attaque magique, avec la puissance de la materia."""
        return caster.magic_attack(target, self.power, self.element)

    @override
    def to_dict(self) -> dict[str, Any]:
        """Celui de la mère, plus l'élément : la valeur de l'Enum, ou None."""
        data = super().to_dict()
        data["element"] = self.element.value if self.element is not None else None
        return data

    @classmethod
    @override
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Element("feu") retrouve le membre de l'Enum à partir de sa valeur."""
        element = Element(data["element"]) if data["element"] is not None else None
        return cls(data["name"], data["cost"], data["power"], element)


class HealMateria(Materia):
    """Soin : rend des PV à un allié."""

    TARGET = Target.ALLY

    @override
    def cast(self, caster: Fighter, target: Fighter) -> int:
        """MAG × puissance PV rendus."""
        return target.heal(caster.magic * self.power)


class SummonMateria(AttackMateria):
    """Une invocation : une attaque magique sur tous les ennemis."""

    TARGET = Target.ENEMIES


# Des classes, rangées par nom : "kind" dit laquelle recrée la materia.
KINDS: dict[str, type[Materia]] = {
    kind.__name__: kind for kind in (AttackMateria, HealMateria, SummonMateria)
}


def materia_from_dict(data: dict[str, Any]) -> Materia:
    """Recrée une materia, quelle que soit sa classe."""
    return KINDS[data["kind"]].from_dict(data)
