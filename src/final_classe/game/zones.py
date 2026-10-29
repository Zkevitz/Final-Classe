"""Les zones : chacune a un nom, ses vagues, et ce qui se passe avant d'y entrer."""

from collections.abc import Callable
from dataclasses import dataclass

from final_classe.characters import (
    Ahriman,
    Behemoth,
    Bomb,
    Cactuar,
    Chimera,
    Flan,
    Garland,
    Golem,
    Lich,
    Malboro,
    Monster,
    Party,
    RedDragon,
    Sephiroth,
    Tonberry,
    Wolf,
)
from final_classe.game.display import console, hero_sheet
from final_classe.game.preparation import prepare
from final_classe.game.shop import visit
from final_classe.items import Elixir, Ether, PhoenixDown, Potion, Shop, catalog


@dataclass(frozen=True)
class Zone:
    """Une zone : des fonctions rangées dans des champs, appelées au bon moment."""

    name: str
    waves: Callable[[], list[list[Monster]]]  # une fonction : des monstres neufs à chaque passage
    before: Callable[[Party], None] | None = None  # ce qui précède la zone, s'il y a quelque chose


def equip_starters(party: Party) -> None:
    """Avant la Forêt : une arme et une armure pour chacun, selon sa meilleure statistique."""
    for hero in party.heroes:
        hero.equip(catalog.rod() if hero.magic > hero.strength else catalog.bronze_sword())
        hero.equip(catalog.leather_armor())
        console.print(hero_sheet(hero))


def open_chest(party: Party) -> None:
    """À l'entrée de la Grotte, un coffre : de l'équipement, des materias et des objets."""
    party.bag.extend([catalog.mythril_sword(), catalog.mythril_rod(), catalog.mythril_armor()])
    party.bag.append(catalog.ribbon())
    party.materias.extend([catalog.fire(), catalog.ice(), catalog.thunder(), catalog.cure()])
    party.materias.extend([catalog.ifrit(), catalog.shiva(), catalog.ramuh()])
    party.items.add(Ether(), Ether(), PhoenixDown(), Elixir())
    console.print("\n[bold yellow]Un coffre ! Équipement, materias et objets rejoignent le sac.[/]")


def first_shop() -> Shop:
    """Cid, après la Grotte : l'étal de diamant."""
    stock = [
        catalog.diamond_sword(),
        catalog.diamond_sword(),
        catalog.diamond_rod(),
        catalog.diamond_armor(),
        catalog.diamond_armor(),
        catalog.diamond_armor(),
        catalog.power_gauntlets(),
        catalog.rune_bracelet(),
        catalog.chain_mail(),
    ]
    return Shop("Cid", stock, goods=[Potion, Ether, PhoenixDown])  # des classes


def second_shop() -> Shop:
    """Cid, au pied du Cratère : l'étal de cristal."""
    stock = [
        catalog.crystal_sword(),
        catalog.crystal_sword(),
        catalog.crystal_rod(),
        catalog.crystal_armor(),
        catalog.crystal_armor(),
        catalog.crystal_armor(),
    ]
    return Shop("Cid", stock, goods=[Potion, Ether, PhoenixDown])


def give_signatures(party: Party) -> None:
    """Chaque héros reçoit l'arme légendaire de son job ; l'ancienne va au sac."""
    console.print("\n[bold yellow]Au pied du Cratère, chacun retrouve son arme légendaire.[/]")
    for hero in party.heroes:
        weapon = catalog.SIGNATURES[hero.JOB_NAME]()  # la fonction, puis l'appel
        previous = hero.equip(weapon)
        if previous is not None:
            party.bag.append(previous)
        console.print(f"{hero.name} : {weapon}")


def plains() -> list[list[Monster]]:
    """Les Plaines de Dalmasca."""
    return [
        [Flan()],
        [Wolf("Loup A"), Wolf("Loup B")],
        [Flan(), Wolf("Loup alpha", hp=600, strength=20)],
    ]


def forest() -> list[list[Monster]]:
    """La Forêt de Macalania."""
    return [
        [Bomb(), Ahriman()],
        [Cactuar()],
        [Bomb("Bombo A"), Bomb("Bombo B"), Ahriman()],
        [Malboro()],
    ]


def cave() -> list[list[Monster]]:
    """La Grotte des cristaux."""
    return [[Tonberry()], [Golem(), Golem("Golem B")], [Tonberry(), Golem()], [Behemoth()]]


def chaos() -> list[list[Monster]]:
    """Le Sanctuaire du Chaos."""
    return [[Chimera()], [Lich(), Lich("Liche B")], [Chimera(), Lich()], [Garland()]]


def crater() -> list[list[Monster]]:
    """Le Cratère Nord."""
    return [[RedDragon()], [Chimera(), RedDragon("Dragon rouge B")], [Sephiroth()]]


def before_forest(party: Party) -> None:
    """Le marchand ambulant."""
    console.print("\nUn marchand ambulant vous offre de quoi vous équiper :")
    equip_starters(party)


def before_cave(party: Party) -> None:
    """Le coffre, puis la préparation."""
    open_chest(party)
    prepare(party)


def before_chaos(party: Party) -> None:
    """Cid, la préparation, et Garland."""
    visit(first_shop(), party)
    prepare(party)
    console.print("\nGarland : « Moi, Garland, je vais tous vous écraser ! »")


def before_crater(party: Party) -> None:
    """Bahamut, les armes légendaires, Cid, la préparation, et Sephiroth."""
    party.materias.append(catalog.bahamut())
    console.print("[bold yellow]Garland laisse tomber une materia rouge : Bahamut ![/]")
    give_signatures(party)
    visit(second_shop(), party)
    prepare(party)
    console.print("\nSephiroth : « Tu es revenu… Cette fois, je vais te montrer le désespoir. »")


ZONES: list[Zone] = [
    Zone("Les Plaines de Dalmasca", plains),
    Zone("La Forêt de Macalania", forest, before_forest),
    Zone("La Grotte des cristaux", cave, before_cave),
    Zone("Le Sanctuaire du Chaos", chaos, before_chaos),
    Zone("Le Cratère Nord", crater, before_crater),
]
