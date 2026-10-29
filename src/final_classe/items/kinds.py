"""Les genres du jeu : des Enum, à la place des chaînes."""

from enum import Enum


class Slot(Enum):
    """L'emplacement d'une pièce d'équipement."""

    WEAPON = "arme"
    ARMOR = "armure"
    ACCESSORY = "accessoire"


class Element(Enum):
    """L'élément d'un sort, et la faiblesse d'un monstre."""

    FIRE = "feu"
    ICE = "glace"
    THUNDER = "foudre"


class Target(Enum):
    """Qui vise une compétence, un sort ou un objet."""

    ENEMY = "un ennemi"
    ENEMIES = "tous les ennemis"
    ALLY = "un allié"
    KNOCKED_OUT = "un allié K.O."
