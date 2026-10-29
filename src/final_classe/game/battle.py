"""Le combat : l'équipe contre un groupe de monstres, dans l'ordre de la VIT."""

from collections.abc import Callable, Sequence

from final_classe.characters import Character, Hero, Monster, Party
from final_classe.game.creation import ask_int
from final_classe.game.display import console, hero_line, monster_line
from final_classe.items import Target


def standing(characters: Sequence[Character]) -> list[Character]:
    """Les personnages encore debout."""
    return [character for character in characters if character.is_alive]


def by_speed(character: Character) -> int:
    """La clé de tri du tour : la VIT."""
    return character.speed


def choose_target(characters: Sequence[Character], prompt: str = "Cible") -> Character:
    """Le joueur choisit une cible ; pas de question s'il n'y en a qu'une."""
    if len(characters) == 1:
        return characters[0]
    for number, character in enumerate(characters, start=1):
        console.print(f"  {number}. {character.name} (PV {character.hp}/{character.max_hp})")
    return characters[ask_int(f"{prompt} : ", 1, len(characters)) - 1]


def choose_option(labels: list[str], prompt: str) -> int | None:
    """Le joueur choisit dans une liste ; renvoie l'indice, ou None pour revenir au menu."""
    for number, label in enumerate(labels, start=1):
        console.print(f"  {number}. {label}")
    console.print("  0. Retour")
    choice = ask_int(f"{prompt} : ", 0, len(labels))
    return None if choice == 0 else choice - 1


def targets_for(kind: Target, party: Party, monsters: list[Monster]) -> list[Character]:
    """Les cibles d'une compétence, d'un sort ou d'un objet, d'après son genre de cible."""
    if kind is Target.ENEMIES:
        return standing(monsters)
    if kind is Target.ALLY:
        return [choose_target(party.standing, "Allié")]
    if kind is Target.KNOCKED_OUT:
        return [choose_target(party.knocked_out, "Allié K.O.")] if party.knocked_out else []
    return [choose_target(standing(monsters))]


def report_defeated(targets: list[Character], monsters: list[Monster]) -> None:
    """Annonce les monstres que l'action vient de vaincre."""
    for target in targets:
        if target in monsters and not target.is_alive:
            console.print(f"[green]{target.name} est vaincu ![/]")


def attack_action(hero: Hero, party: Party, monsters: list[Monster]) -> bool:
    """Attaquer un monstre ; renvoie True si le héros a agi."""
    target = choose_target(standing(monsters))
    damage = hero.attack(target)
    console.print(f"{hero.name} attaque {target.name} : [bold]{damage}[/] dégâts.")
    report_defeated([target], monsters)
    return True


def skill_action(hero: Hero, party: Party, monsters: list[Monster]) -> bool:
    """La compétence du job ; renvoie False si les PM manquent."""
    if not hero.can_use_skill:
        console.print("[red]Pas assez de PM ![/]")
        return False
    targets = targets_for(hero.SKILL_TARGET, party, monsters)
    value = hero.use_skill(*targets)
    names = ", ".join(target.name for target in targets)
    console.print(
        hero.SKILL_TEXT.format(user=hero.name, skill=hero.SKILL_NAME, target=names, value=value)
    )
    report_defeated(targets, monsters)
    return True


def magic_action(hero: Hero, party: Party, monsters: list[Monster]) -> bool:
    """Un sort, donné par une materia de l'équipement ; renvoie False si le joueur renonce."""
    if not hero.spells:
        console.print("[red]Aucune materia équipée ![/]")
        return False
    labels = [f"{materia.name} ({materia.cost} PM)" for materia in hero.spells]
    index = choose_option(labels, "Sort")
    if index is None:
        return False
    materia = hero.spells[index]
    if not hero.can_cast(materia):
        console.print("[red]Pas assez de PM ![/]")
        return False
    targets = targets_for(materia.TARGET, party, monsters)
    value = hero.cast(materia, *targets)
    names = ", ".join(target.name for target in targets)
    effect = f"+{value} PV" if materia.TARGET is Target.ALLY else f"{value} dégâts"
    console.print(f"{hero.name} lance {materia.name} sur {names} : [bold]{effect}[/].")
    report_defeated(targets, monsters)
    return True


def item_action(hero: Hero, party: Party, monsters: list[Monster]) -> bool:
    """Un objet du sac ; renvoie False si le joueur renonce, ou si personne n'en a besoin."""
    if not party.items:
        console.print("[red]Plus aucun objet ![/]")
        return False
    counts = party.items.counts()  # {"Potion": 3, …} : une ligne par sorte d'objet
    names = list(counts)
    index = choose_option([f"{name} x{counts[name]}" for name in names], "Objet")
    if index is None:
        return False
    item = party.items.take(names[index])
    if item is None:
        return False
    targets = targets_for(item.TARGET, party, monsters)
    if not targets:
        party.items.add(item)  # personne n'en a besoin : l'objet retourne dans le sac
        console.print("[red]Personne n'est K.O.[/]")
        return False
    value = item.use(targets[0])
    console.print(f"{hero.name} utilise {item.name} sur {targets[0].name} : [green]+{value}[/].")
    return True


# Chaque action est une fonction, rangée dans un dictionnaire : le menu ne fait que choisir.
ACTIONS: dict[int, Callable[[Hero, Party, list[Monster]], bool]] = {
    1: attack_action,
    2: skill_action,
    3: magic_action,
    4: item_action,
}


def hero_turn(hero: Hero, party: Party, monsters: list[Monster]) -> None:
    """Le tour d'un héros : le joueur choisit son action, jusqu'à ce qu'il agisse."""
    hero.start_turn()
    skill = f"{hero.SKILL_NAME} ({hero.SKILL_COST} PM)"
    menu = f"[bold]{hero.name}[/] : 1. Attaquer  2. {skill}  3. Magie  4. Objet  5. Se défendre"
    while True:
        console.print(menu)
        choice = ask_int("> ", 1, 5)
        if choice == 5:
            hero.defend()
            console.print(f"{hero.name} se met en garde : les coups reçus sont divisés par deux.")
            return
        if ACTIONS[choice](hero, party, monsters):
            return


def monster_turn(monster: Monster, heroes: list[Hero]) -> None:
    """Le tour d'un monstre : il agit, et le combat affiche chaque coup."""
    for hit in monster.act(heroes):
        damage = f"[bold red]{hit.damage}[/] dégâts"
        console.print(f"{monster.name} : {hit.action} sur {hit.target.name}, {damage}.")
        if not hit.target.is_alive:
            console.print(f"[red]{hit.target.name} est K.O.[/]")
    if monster.is_alive and monster.warning:
        console.print(f"[yellow]{monster.warning}[/]")


def fight(party: Party, monsters: list[Monster]) -> bool:
    """Le combat d'équipe ; renvoie True si l'équipe gagne."""
    heroes = party.heroes
    names = ", ".join(monster.name for monster in monsters)
    console.print(f"\n[bold red]Combat contre {names}[/]")
    turn = 0
    while standing(heroes) and standing(monsters):
        turn += 1
        console.print(f"\n[bold]--- Tour {turn} ---[/]")
        for hero in heroes:
            console.print(hero_line(hero))
        for monster in standing(monsters):
            console.print(monster_line(monster))
        order = sorted([*heroes, *monsters], key=by_speed, reverse=True)
        queue = " → ".join(character.name for character in standing(order))
        console.print(f"[dim]Ordre du tour : {queue}[/]")
        for character in order:
            if not character.is_alive or not standing(heroes) or not standing(monsters):
                continue
            # Pas une cascade de cas par espèce : on sépare les deux camps.
            # Pour un héros, le joueur décide ; un monstre décide seul.
            if isinstance(character, Hero):
                hero_turn(character, party, monsters)
            else:
                monster_turn(character, heroes)
    won = bool(standing(heroes))
    console.print("\n[bold green]Victoire ![/]" if won else "\n[bold red]L'équipe est K.O…[/]")
    return won
