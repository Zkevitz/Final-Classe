"""Les objets du jeu : ils ne dépendent d'aucun autre package de Final Classe."""

from final_classe.items.consumables import Elixir, Ether, PhoenixDown, Potion, Usable
from final_classe.items.equipment import Equipment
from final_classe.items.fighter import Fighter
from final_classe.items.inventory import Inventory
from final_classe.items.kinds import Element, Slot, Target
from final_classe.items.materia import (
    AttackMateria,
    HealMateria,
    Materia,
    SummonMateria,
    materia_from_dict,
)
from final_classe.items.shop import Shop

__all__ = [
    "AttackMateria",
    "Element",
    "Elixir",
    "Equipment",
    "Ether",
    "Fighter",
    "HealMateria",
    "Inventory",
    "Materia",
    "PhoenixDown",
    "Potion",
    "Shop",
    "Slot",
    "SummonMateria",
    "Target",
    "Usable",
    "materia_from_dict",
]
