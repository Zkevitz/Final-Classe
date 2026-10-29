"""Le catalogue : chaque fonction fabrique une pièce neuve."""

from collections.abc import Callable

from final_classe.items.equipment import Equipment
from final_classe.items.kinds import Element, Slot
from final_classe.items.materia import AttackMateria, HealMateria, Materia, SummonMateria
from final_classe.stats import Stats


def bronze_sword() -> Equipment:
    """Une épée simple."""
    return Equipment("Épée de bronze", Slot.WEAPON, 100, Stats(strength=4))


def rod() -> Equipment:
    """Le bâton des mages."""
    return Equipment("Bâton", Slot.WEAPON, 100, Stats(magic=4))


def leather_armor() -> Equipment:
    """Une armure légère."""
    return Equipment("Armure de cuir", Slot.ARMOR, 100, Stats(defense=4))


def chain_mail() -> Equipment:
    """Une armure plus lourde, qui protège aussi un peu de la magie."""
    return Equipment("Cotte de mailles", Slot.ARMOR, 300, Stats(defense=8, resistance=2))


def mythril_sword() -> Equipment:
    """Une épée solide, avec deux emplacements de materia."""
    return Equipment("Épée de mythril", Slot.WEAPON, 600, Stats(strength=8), slots=2)


def mythril_rod() -> Equipment:
    """Un bâton qui canalise la magie, avec deux emplacements."""
    return Equipment("Bâton de mythril", Slot.WEAPON, 600, Stats(magic=8), slots=2)


def mythril_armor() -> Equipment:
    """Une armure de mythril, avec un emplacement."""
    return Equipment("Armure de mythril", Slot.ARMOR, 600, Stats(defense=10, resistance=6), slots=1)


def diamond_sword() -> Equipment:
    """Chez Cid : une épée de diamant."""
    return Equipment("Épée de diamant", Slot.WEAPON, 1500, Stats(strength=14), slots=2)


def diamond_rod() -> Equipment:
    """Chez Cid : un bâton de diamant."""
    return Equipment("Bâton de diamant", Slot.WEAPON, 1500, Stats(magic=14), slots=2)


def diamond_armor() -> Equipment:
    """Chez Cid : une armure de diamant."""
    return Equipment(
        "Armure de diamant", Slot.ARMOR, 1500, Stats(defense=16, resistance=10), slots=2
    )


def power_gauntlets() -> Equipment:
    """Chez Cid : des gantelets qui donnent de la force."""
    return Equipment("Gantelets de force", Slot.ACCESSORY, 1000, Stats(strength=8))


def rune_bracelet() -> Equipment:
    """Chez Cid : un bracelet qui renforce la magie."""
    return Equipment("Bracelet runique", Slot.ACCESSORY, 1000, Stats(magic=8))


def crystal_sword() -> Equipment:
    """Chez Cid, avant le Cratère : une épée de cristal."""
    return Equipment("Épée de cristal", Slot.WEAPON, 4000, Stats(strength=22), slots=3)


def crystal_rod() -> Equipment:
    """Chez Cid, avant le Cratère : un bâton de cristal."""
    return Equipment("Bâton de cristal", Slot.WEAPON, 4000, Stats(magic=22), slots=3)


def crystal_armor() -> Equipment:
    """Chez Cid, avant le Cratère : une armure de cristal."""
    return Equipment(
        "Armure de cristal", Slot.ARMOR, 4000, Stats(defense=24, resistance=16), slots=2
    )


def ribbon() -> Equipment:
    """Le Ruban : l'accessoire légendaire."""
    return Equipment("Ruban", Slot.ACCESSORY, 2000, Stats(resistance=12, speed=2))


def fire() -> Materia:
    """Feu."""
    return AttackMateria("Feu", 8, 12, Element.FIRE)


def ice() -> Materia:
    """Glace."""
    return AttackMateria("Glace", 8, 12, Element.ICE)


def thunder() -> Materia:
    """Foudre."""
    return AttackMateria("Foudre", 8, 12, Element.THUNDER)


def cure() -> Materia:
    """Soin."""
    return HealMateria("Soin", 10, 12)


def ifrit() -> Materia:
    """Ifrit : Flammes de l'enfer sur tous les ennemis."""
    return SummonMateria("Ifrit", 30, 20, Element.FIRE)


def shiva() -> Materia:
    """Shiva : Poussière de diamant sur tous les ennemis."""
    return SummonMateria("Shiva", 30, 20, Element.ICE)


def ramuh() -> Materia:
    """Ramuh : Jugement divin sur tous les ennemis."""
    return SummonMateria("Ramuh", 30, 20, Element.THUNDER)


def bahamut() -> Materia:
    """Bahamut : Méga Flare, sans élément, sur tous les ennemis."""
    return SummonMateria("Bahamut", 60, 30)


# l'arme légendaire de chaque job. Des fonctions, rangées dans un dictionnaire.


def ultima_weapon() -> Equipment:
    """L'arme de Cloud."""
    return Equipment("Ultima Weapon", Slot.WEAPON, 0, Stats(strength=30), slots=4)


def mog_doll() -> Equipment:
    """L'arme de Lulu."""
    return Equipment("Poupée Mog", Slot.WEAPON, 0, Stats(magic=30), slots=4)


def excalibur() -> Equipment:
    """L'arme de Basch."""
    return Equipment("Excalibur", Slot.WEAPON, 0, Stats(strength=26, defense=10), slots=3)


def rune_claws() -> Equipment:
    """L'arme d'Amarant."""
    return Equipment("Griffes runiques", Slot.WEAPON, 0, Stats(strength=22, magic=12), slots=3)


def orichalcum_dagger() -> Equipment:
    """L'arme de Djidane."""
    return Equipment("Dague d'Orichalque", Slot.WEAPON, 0, Stats(strength=24, speed=6), slots=3)


def masamune() -> Equipment:
    """L'arme d'Auron."""
    return Equipment("Masamune", Slot.WEAPON, 0, Stats(strength=32), slots=3)


def yoichi_bow() -> Equipment:
    """L'arme de Fran."""
    return Equipment("Arc Yoichi", Slot.WEAPON, 0, Stats(strength=28, speed=2), slots=3)


def conformer() -> Equipment:
    """L'arme de Youfie."""
    return Equipment("Conformeur", Slot.WEAPON, 0, Stats(strength=24, speed=4), slots=3)


SIGNATURES: dict[str, Callable[[], Equipment]] = {
    "Soldat": ultima_weapon,
    "Mage noir": mog_doll,
    "Chevalier": excalibur,
    "Moine": rune_claws,
    "Voleur": orichalcum_dagger,
    "Samouraï": masamune,
    "Archer": yoichi_bow,
    "Ninja": conformer,
}
