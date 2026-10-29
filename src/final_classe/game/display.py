"""L'affichage : le seul module qui connaît rich."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from final_classe.characters import Character, Hero

console = Console()


def banner() -> Panel:
    """L'écran titre."""
    title = Text("F I N A L   C L A S S E", style="bold cyan", justify="center")
    return Panel(title, subtitle="un mini-RPG pour apprendre la POO", border_style="cyan")


def bar(current: int, maximum: int, width: int = 10) -> str:
    """Une jauge en couleur : verte, puis jaune sous la moitié, rouge sous le quart."""
    ratio = current / maximum
    filled = round(width * ratio)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    return f"[{color}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"


def hero_sheet(hero: Hero) -> str:
    """La fiche complète d'un héros : job, niveau, PV, PM, statistiques et équipement."""
    gear = ", ".join(item.name for item in hero.equipment) or "rien"
    return (
        f"[bold]{hero.name}[/] ({hero.title}, niveau {hero.level})\n"
        f"  PV {hero.hp:>4}/{hero.max_hp:<4} {bar(hero.hp, hero.max_hp)}\n"
        f"  PM {hero.mp:>4}/{hero.max_mp:<4} {bar(hero.mp, hero.max_mp)}\n"
        f"  {hero.stats}\n"
        f"  Équipement : {gear}"
    )


def hero_line(hero: Hero) -> str:
    """Une ligne pour un héros, pendant le combat."""
    name = str(hero)
    hp = f"PV {hero.hp:>4}/{hero.max_hp:<4} {bar(hero.hp, hero.max_hp)}"
    return f"[bold]{name:<22}[/] {hp}  PM {hero.mp:>3}/{hero.max_mp:<3}"


def monster_line(monster: Character) -> str:
    """Une ligne pour un monstre : son nom et sa jauge de PV."""
    gauge = bar(monster.hp, monster.max_hp)
    return f"[bold red]{monster.name:<22}[/] PV {monster.hp:>4}/{monster.max_hp:<4} {gauge}"
