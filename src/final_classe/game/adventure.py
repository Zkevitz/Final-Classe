"""Le déroulement de la partie : nouvelle partie ou reprise, puis les zones, dans l'ordre."""

from final_classe.characters import Monster, Party, Sephiroth, Soldier
from final_classe.game.battle import fight
from final_classe.game.creation import ask_int, ask_name, create_hero
from final_classe.game.display import banner, console, hero_sheet
from final_classe.game.recruit import recruit
from final_classe.game.zones import ZONES
from final_classe.storage import SLOTS, SaveError, load_game, peek, save_game


def prologue() -> None:
    """Nibelheim, il y a cinq ans : un duel perdu d'avance."""
    console.print("[italic]Nibelheim, il y a cinq ans…[/]\n")
    # Cloud, cinq ans plus tôt : moins aguerri que la recrue qu'on rencontrera ensuite.
    cloud = Soldier("Cloud", strength=20, magic=12, defense=15, resistance=13)
    sephiroth = Sephiroth()
    while cloud.is_alive:
        damage = cloud.attack(sephiroth)
        console.print(f"Cloud frappe Sephiroth : [bold]{damage}[/] dégât(s).")
        damage = sephiroth.attack(cloud)
        console.print(f"Sephiroth frappe Cloud : [bold red]{damage}[/] dégâts.")
    console.print(f"\n{hero_sheet(cloud)}")
    console.print(f"Sephiroth : PV {sephiroth.hp}/{sephiroth.max_hp}")
    console.print("\nSephiroth : « Tu n'es qu'une marionnette. »")
    console.print("[italic]Un jour, tu reviendras. Et cette fois, tu seras prêt.[/]")


def reward(party: Party, monsters: list[Monster]) -> None:
    """Le butin : l'équipe s'en charge, le jeu l'affiche."""
    xp = sum(monster.xp for monster in monsters)
    gil = party.gil
    leveled = party.reward(monsters)
    console.print(
        f"Butin : [yellow]+{xp} XP[/] pour chaque héros debout, [yellow]+{party.gil - gil} gils[/]"
    )
    for hero in leveled:
        console.print(f"[bold yellow]{hero.name} passe au niveau {hero.level} ![/]")


def cross(index: int, party: Party, slot: int, first_wave: int = 0) -> bool:
    """Traverse une zone, vague après vague ; renvoie False si l'équipe tombe."""
    zone = ZONES[index]
    console.print(f"\n[bold cyan]=== {zone.name} ===[/]")
    waves = zone.waves()
    for number in range(first_wave, len(waves)):
        monsters = waves[number]
        if not fight(party, monsters):
            console.print("[bold red]=== Game over ===[/]")
            return False
        reward(party, monsters)
        party.rest()
        console.print("L'équipe se repose : PV et PM au maximum.")
        if number + 1 < len(waves):  # bonus ★★ 4 : on reprendra à la vague suivante
            save_game(party, index, number + 1, slot)
    console.print(f"\n[bold green]{zone.name} : traversée ![/]")
    return True


def describe(slot: int) -> str:
    """Bonus ★ 1 : le résumé d'une sauvegarde, ou la raison de son absence."""
    try:
        party, zone, _ = load_game(slot)
        date = peek(slot)["date"]
    except SaveError as error:
        return f"[dim]{error}[/]"
    heroes = ", ".join(f"{hero.name} niv. {hero.level}" for hero in party.heroes)
    return f"{date}  {ZONES[zone].name}  ({heroes})"


def choose_slot() -> int:
    """Bonus ★ 2 : les emplacements, chacun avec son résumé."""
    for slot in range(1, SLOTS + 1):
        console.print(f"  {slot}. {describe(slot)}")
    return ask_int("Emplacement : ", 1, SLOTS)


def new_game() -> Party:
    """Le prologue, la création du héros et le recrutement."""
    prologue()
    console.print("\n[bold]Cinq ans plus tard…[/]")
    party = Party(recruit(create_hero(ask_name())))
    for hero in party.heroes:
        console.print(hero_sheet(hero))
    return party


def start_game(slot: int) -> tuple[Party, int, int]:
    """Nouvelle partie, ou reprise : l'équipe, la zone et la vague où commencer."""
    console.print("1. Nouvelle partie  2. Continuer")
    if ask_int("> ", 1, 2) == 2:
        try:
            party, zone, wave = load_game(slot)
        except SaveError as error:
            console.print(f"[red]{error}[/] Une nouvelle partie commence.")
        else:
            console.print(f"[green]Partie chargée : {ZONES[zone].name}.[/]")
            return party, zone, wave
    return new_game(), 0, 0


def run() -> None:
    """Le menu de départ, puis chaque zone, avec une sauvegarde après chacune."""
    console.print(banner())
    slot = choose_slot()  # bonus ★ 2
    party, start, wave = start_game(slot)
    for index in range(start, len(ZONES)):
        zone = ZONES[index]
        if zone.before is not None and wave == 0:  # au milieu d'une zone, c'est déjà fait
            zone.before(party)
        if not cross(index, party, slot, wave):
            return
        wave = 0
        if index + 1 < len(ZONES):
            save_game(party, index + 1, slot=slot)
            console.print("[dim]Partie sauvegardée.[/]")
    console.print("\n[bold cyan]Sephiroth est vaincu. Le monde est sauvé ![/]")
