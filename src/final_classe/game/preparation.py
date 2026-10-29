"""La préparation, entre deux zones : équiper l'équipe, et monter les materias."""

from final_classe.characters import Hero, Party
from final_classe.game.creation import ask_int
from final_classe.game.display import console, hero_sheet


def choose_hero(party: Party) -> Hero:
    """Le joueur choisit un héros de l'équipe."""
    for number, hero in enumerate(party.heroes, start=1):
        console.print(f"  {number}. {hero.name} ({hero.title})")
    return party.heroes[ask_int("Quel héros : ", 1, len(party.heroes)) - 1]


def equip_from_bag(party: Party) -> None:
    """Une pièce du sac sur un héros ; celle qu'elle remplace retourne dans le sac."""
    if not party.bag:
        console.print("[red]Le sac est vide.[/]")
        return
    for number, item in enumerate(party.bag, start=1):
        console.print(f"  {number}. {item}")
    item = party.bag.pop(ask_int("Quelle pièce : ", 1, len(party.bag)) - 1)
    hero = choose_hero(party)
    previous = hero.equip(item)
    if previous is not None:
        party.bag.append(previous)
    console.print(hero_sheet(hero))


def attach_materia(party: Party) -> None:
    """Une materia de la réserve, montée sur une pièce portée par un héros."""
    if not party.materias:
        console.print("[red]Aucune materia en réserve.[/]")
        return
    for number, materia in enumerate(party.materias, start=1):
        console.print(f"  {number}. {materia.name} ({materia.cost} PM)")
    materia = party.materias[ask_int("Quelle materia : ", 1, len(party.materias)) - 1]
    hero = choose_hero(party)
    if not hero.equipment:
        console.print("[red]Ce héros ne porte rien.[/]")
        return
    for number, item in enumerate(hero.equipment, start=1):
        console.print(f"  {number}. {item.name} ({len(item.materias)}/{item.slots})")
    item = hero.equipment[ask_int("Sur quelle pièce : ", 1, len(hero.equipment)) - 1]
    if item.attach(materia):
        party.materias.remove(materia)
        console.print(f"[green]{materia.name} est montée sur {item.name}.[/]")
    else:
        console.print(f"[red]{item.name} n'a plus d'emplacement libre.[/]")


def detach_materia(party: Party) -> None:
    """Retire une materia d'une pièce ; elle retourne dans la réserve."""
    hero = choose_hero(party)
    spells = hero.spells
    if not spells:
        console.print("[red]Ce héros n'a aucune materia.[/]")
        return
    for number, materia in enumerate(spells, start=1):
        console.print(f"  {number}. {materia.name}")
    materia = spells[ask_int("Quelle materia : ", 1, len(spells)) - 1]
    for item in hero.equipment:
        if item.detach(materia):
            party.materias.append(materia)
            console.print(f"[green]{materia.name} retourne dans la réserve.[/]")
            return


def prepare(party: Party) -> None:
    """Le menu de préparation, jusqu'au départ."""
    while True:
        console.print(
            "\n[bold]Préparation[/] : 1. Équiper  2. Monter une materia  "
            "3. Retirer une materia  0. Partir"
        )
        choice = ask_int("> ", 0, 3)
        if choice == 0:
            return
        if choice == 1:
            equip_from_bag(party)
        elif choice == 2:
            attach_materia(party)
        else:
            detach_materia(party)
