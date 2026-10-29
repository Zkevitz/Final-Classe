"""Les objets : aucune classe mère, mais tous respectent le même contrat, Usable."""

from typing import Protocol

from final_classe.items.fighter import Fighter
from final_classe.items.kinds import Target


class Usable(Protocol):
    """Un objet qu'on utilise sur une cible."""

    name: str
    TARGET: Target
    PRICE: int  # le prix chez Cid

    def use(self, target: Fighter) -> int:
        """Utilise l'objet ; renvoie les PV ou les PM rendus."""
        ...


class Potion:
    """Rend 400 PV."""

    name = "Potion"
    TARGET = Target.ALLY
    PRICE = 50

    def use(self, target: Fighter) -> int:
        """Soigne la cible."""
        return target.heal(400)


class Ether:
    """Rend 60 PM."""

    name = "Éther"
    TARGET = Target.ALLY
    PRICE = 150

    def use(self, target: Fighter) -> int:
        """Rend des PM à la cible."""
        return target.restore_mp(60)


class PhoenixDown:
    """Relève un allié K.O., avec la moitié de ses PV."""

    name = "Queue de phénix"
    TARGET = Target.KNOCKED_OUT
    PRICE = 300

    def use(self, target: Fighter) -> int:
        """Relève la cible."""
        return target.revive()


class Elixir:
    """Rend tous les PV et tous les PM."""

    name = "Élixir"
    TARGET = Target.ALLY
    PRICE = 3000

    def use(self, target: Fighter) -> int:
        """Remet la cible au maximum ; renvoie les PV rendus."""
        target.restore_mp(9999)
        return target.heal(9999)


# Des classes, rangées par nom : une sauvegarde recrée chaque objet à partir de son nom.
ITEMS: dict[str, type[Usable]] = {kind.name: kind for kind in (Potion, Ether, PhoenixDown, Elixir)}
