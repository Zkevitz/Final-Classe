"""Le chef d'orchestre de l'aventure (fidèle à `game/adventure.py` et `game/zones.py`) + petits outils d'interface.

CONTRAT (utilisé par la scène de butin `loot`, la carte, les événements) ::

    flow.ZONE_KEYS                   ("plains", "forest", "cave", "chaos", "crater") = clés de `battle:<clé>:<n>`
    flow.start_zone(game, index)     entre dans la zone `index` : événement d'avant-zone -> préparation -> dialogue de fin (Chaos, Cratère) -> vague 1.
                                     Si `game.wave > 0` (reprise de sauvegarde), reprend directement ce combat.
    flow.start_battle(game, index, wave)   ouvre `battle` avec les args [clé de zone, str(wave + 1)]
                                     (numéro de vague 1-based dans les args, `game.wave` reste 0-based).
    flow.after_battle(game)          à appeler quand le butin est validé : repos de l'équipe (`party.rest()`),
                                     puis vague suivante (sauvegarde `game.zone, game.wave+1` comme le terminal),
                                     ou zone terminée (`game.zone += 1`, `game.wave = 0`, `game.save()`, carte
                                     du monde avec bannière) ou, après le Cratère, scène `ending` (sans sauvegarde).
    flow.event_done(game, index, after) / flow.prepare_done(game)   appelés par les scènes `event` et `prepare`.
    flow.open_shop(game, "first" | "second")   empile la boutique de Cid (stock neuf à chaque visite).

Pendant un combat : `game.zone` = index de la zone, `game.wave` = index (0-based) de la vague en cours.
L'attribution de l'XP et des gils (`party.reward`) reste à la scène de butin ; `after_battle` ne la refait pas.
"""

import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, log_error
from final_classe.gfx.scenes._demo import key_event
from final_classe.gfx.ui import draw_text, draw_window, theme
from final_classe.gfx.ui.menu import draw_cursor
from final_classe.items import Equipment, Materia, Slot, SummonMateria
from final_classe.items.shop import Shop
from final_classe.stats import Stats

ZONE_KEYS = ("plains", "forest", "cave", "chaos", "crater")
PREPARE_ZONES = (2, 3, 4)  # comme le terminal : Grotte, Sanctuaire, Cratère
OUTRO_ZONES = (3, 4)  # Garland / Sephiroth parlent après la préparation
STAT_LABELS = (("strength", "FOR"), ("magic", "MAG"), ("defense", "DÉF"), ("resistance", "RÉS"), ("speed", "VIT"))


# --- icônes et images -----------------------------------------------------------------------
def is_staff(item: Equipment) -> bool:
    """Bâton : le nom le dit, ou plus de MAG que de FOR en bonus."""
    return "bâton" in item.name.lower() or item.stats.magic > item.stats.strength


def equipment_icon(item: Equipment) -> str:
    """Id d'icône d'une pièce d'équipement."""
    if item.slot is Slot.WEAPON:
        return "icon_rod" if is_staff(item) else "icon_sword"
    return "icon_armor" if item.slot is Slot.ARMOR else "icon_accessory"


def materia_icon(materia: Materia) -> str:
    """Rouge pour les invocations, verte sinon."""
    return "icon_materia_red" if isinstance(materia, SummonMateria) else "icon_materia_green"


def usable_icon(name: str) -> str:
    """Id d'icône d'un objet consommable, par son nom."""
    return {
        "Potion": "icon_potion", "Éther": "icon_ether",
        "Queue de phénix": "icon_phoenix_down", "Élixir": "icon_elixir",
    }.get(name, "icon_potion")


def draw_icon(surface: pygame.Surface, assets, icon: str, center: tuple[int, int], size: int = 40) -> None:
    """Une icône carrée centrée."""
    surface.blit(assets.scaled(icon, (size, size)), (center[0] - size // 2, center[1] - size // 2))


def draw_backdrop(surface: pygame.Surface, assets, image_id: str, dim: float = 0.0) -> None:
    """Décor plein écran, éventuellement assombri."""
    img = assets.image(image_id)
    if img.get_size() != (1280, 720):
        img = assets.scaled(image_id, (1280, 720))
    surface.blit(img, (0, 0))
    if dim > 0:
        surface.blit(solid((1280, 720), (4, 8, 28, int(255 * dim))), (0, 0))


def draw_portrait(surface: pygame.Surface, assets, image_id: str, box: pygame.Rect, flip: bool = False) -> pygame.Rect:
    """Un sprite ajusté à `box`, pieds au bas de la boîte, centré."""
    real = assets.feet_rect(image_id)
    scale = min(box.width / max(1, real.width), box.height / max(1, real.height))
    return assets.draw_sprite(surface, image_id, (box.centerx, box.bottom), scale, flip=flip)


_cache: dict[tuple, pygame.Surface] = {}


def solid(size: tuple[int, int], rgba: tuple[int, int, int, int]) -> pygame.Surface:
    """Une surface unie translucide, mise en cache."""
    key = ("solid", size, rgba)
    if key not in _cache:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(rgba)
        _cache[key] = surf
    return _cache[key]


def glow_disc(radius: int, rgb: tuple[int, int, int], alpha: int) -> pygame.Surface:
    """Un halo (cercles concentriques translucides), mis en cache."""
    key = ("glow", radius, rgb, alpha)
    if key not in _cache:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for k in range(4):
            pygame.draw.circle(surf, (*rgb, alpha), (radius, radius), radius * (4 - k) // 4)
        _cache[key] = surf
    return _cache[key]


# --- statistiques ---------------------------------------------------------------------------
def stats_with(hero, item: Equipment) -> Stats:
    """Les stats du héros s'il portait `item` à la place de la pièce du même emplacement."""
    cur = hero.stats
    old = hero.gear.get(item.slot)
    old_stats = old.stats if old is not None else Stats()
    return Stats(**{
        f.name: getattr(cur, f.name) - getattr(old_stats, f.name) + getattr(item.stats, f.name)
        for f in dataclasses.fields(Stats)
    })


def delta_text(before: Stats, after: Stats) -> str:
    """« FOR +8  DÉF -2 » (vide si rien ne change)."""
    parts = []
    for attr, label in STAT_LABELS:
        d = getattr(after, attr) - getattr(before, attr)
        if d:
            parts.append(f"{label} {d:+d}")
    return "  ".join(parts)


# --- liste défilante ------------------------------------------------------------------------
@dataclass
class Row:
    """Une ligne de `ScrollList`."""

    label: str
    icon: str | None = None
    sub: str = ""
    right: str = ""
    enabled: bool = True
    right_color: tuple[int, int, int] = theme.GOLD


class ScrollList:
    """Liste verticale dans une fenêtre : icône, libellé, détail, valeur à droite ; clavier, souris, molette."""

    def __init__(self, rect: tuple[int, int, int, int], row_h: int = 50, empty: str = "(vide)",
                 on_move: Callable[[], None] | None = None, sub_x: int = 380) -> None:
        self.rect = pygame.Rect(rect)
        self.row_h = row_h
        self.rows: list[Row] = []
        self.cursor = 0
        self.top = 0
        self.empty = empty
        self.on_move = on_move
        self.sub_x = sub_x
        self.time = 0.0

    @property
    def visible(self) -> int:
        """Nombre de lignes visibles."""
        return max(1, (self.rect.height - 24) // self.row_h)

    def set_rows(self, rows: list[Row]) -> None:
        """Remplace les lignes en gardant le curseur dans les bornes."""
        self.rows = rows
        self.cursor = min(self.cursor, max(0, len(rows) - 1))
        self._scroll()

    def _scroll(self) -> None:
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + self.visible:
            self.top = self.cursor - self.visible + 1
        self.top = max(0, min(self.top, max(0, len(self.rows) - self.visible)))

    def _move(self, d: int) -> None:
        if not self.rows:
            return
        self.cursor = (self.cursor + d) % len(self.rows)
        self._scroll()
        if self.on_move:
            self.on_move()

    def _row_rect(self, slot: int) -> pygame.Rect:
        return pygame.Rect(self.rect.x + 12, self.rect.y + 12 + slot * self.row_h, self.rect.width - 36, self.row_h)

    def current(self) -> Row | None:
        """La ligne sous le curseur."""
        return self.rows[self.cursor] if self.rows else None

    def handle_event(self, event: pygame.event.Event) -> int | None:
        """Renvoie l'index confirmé (ligne active), sinon None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z) and self.rows:
                return self.cursor if self.rows[self.cursor].enabled else -1
        elif event.type == pygame.MOUSEWHEEL:
            self._move(-event.y)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            for slot in range(min(self.visible, len(self.rows) - self.top)):
                if self._row_rect(slot).collidepoint(event.pos):
                    idx = self.top + slot
                    if idx != self.cursor:
                        self.cursor = idx
                        if self.on_move:
                            self.on_move()
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        return idx if self.rows[idx].enabled else -1
        return None

    def update(self, dt: float) -> None:
        """Oscillation du curseur."""
        self.time += dt

    def draw(self, surface: pygame.Surface, assets, active: bool = True) -> None:
        """Dessine la fenêtre et les lignes visibles."""
        draw_window(surface, self.rect)
        if not self.rows:
            draw_text(surface, self.empty, self.rect.center, 24, theme.TEXT_DIM, "center")
            return
        for slot in range(min(self.visible, len(self.rows) - self.top)):
            idx = self.top + slot
            row = self.rows[idx]
            r = self._row_rect(slot)
            selected = idx == self.cursor
            if selected:
                surface.blit(solid(r.size, (255, 255, 255, 34 if active else 14)), r)
            color = theme.GOLD if selected and active else (theme.TEXT if row.enabled else (110, 118, 150))
            x = r.x + 40
            if row.icon:
                draw_icon(surface, assets, row.icon, (x + 18, r.centery), 38)
                x += 50
            draw_text(surface, row.label, (x, r.centery), 24, color, "midleft")
            if row.sub:
                draw_text(surface, row.sub, (r.x + self.sub_x, r.centery), 18, theme.TEXT_DIM, "midleft")
            if row.right:
                rc = row.right_color if row.enabled else (110, 118, 150)
                draw_text(surface, row.right, (r.right - 8, r.centery), 22, rc, "midright")
            if selected and active:
                draw_cursor(surface, assets, (r.x + 30, r.centery), self.time)
        if len(self.rows) > self.visible:
            track = pygame.Rect(self.rect.right - 16, self.rect.y + 14, 6, self.rect.height - 28)
            pygame.draw.rect(surface, (10, 14, 36), track, border_radius=3)
            h = max(20, track.height * self.visible // len(self.rows))
            y = track.y + (track.height - h) * self.top // max(1, len(self.rows) - self.visible)
            pygame.draw.rect(surface, theme.INNER_LINE, (track.x, y, 6, h), border_radius=3)


# --- pilote automatique (--demo) ------------------------------------------------------------
class KeyPilot:
    """Joue une suite de touches à intervalle régulier (mode `--demo`)."""

    def __init__(self, game: Game, keys: list[int], period: float = 0.9, start: float = 1.0) -> None:
        self.game = game
        self.keys = list(keys)
        self.period = period
        self.t = -start

    def update(self, dt: float) -> int | None:
        """Renvoie une touche à jouer, ou None."""
        if not self.game.demo or self.game.transitioning or not self.keys:
            return None
        self.t += dt
        if self.t >= self.period:
            self.t = 0.0
            return self.keys.pop(0)
        return None


def press(scene, key: int) -> None:
    """Envoie une touche fabriquée à une scène."""
    scene.handle_event(key_event(key))


def wobble(time: float, speed: float = 3.0, amp: float = 1.0) -> float:
    """Oscillation sinusoïdale simple."""
    return math.sin(time * speed) * amp


# --- boutiques ------------------------------------------------------------------------------
def get_shop(game: Game, which: str) -> Shop:
    """Une boutique neuve (« first » ou « second »), recréée à chaque visite comme le terminal."""
    from final_classe.game.zones import first_shop, second_shop

    return second_shop() if which == "second" else first_shop()


def open_shop(game: Game, which: str = "first") -> None:
    """Empile la scène de boutique."""
    if "shop" in SCENES:
        game.push(SCENES["shop"](game, [which]), transition="fade")


# --- déroulement de l'aventure --------------------------------------------------------------
def _go(game: Game, name: str, args: list[str], transition: str | None = "fade") -> bool:
    if name not in SCENES:
        log_error(f"[flow] scène « {name} » absente")
        return False
    game.replace(SCENES[name](game, args), transition=transition)
    return True


def open_world_map(game: Game, cleared: bool = False) -> None:
    """Retour à la carte du monde (avec la bannière « zone traversée » si `cleared`)."""
    if not _go(game, "world_map", ["cleared"] if cleared else []) and "title" in SCENES:
        game.replace_all(SCENES["title"](game, []))


def start_zone(game: Game, index: int) -> None:
    """Entre dans une zone : événement, préparation, puis vague 1 (ou reprise de la vague en cours)."""
    game.zone = index
    if game.wave > 0:  # reprise au milieu d'une zone : l'événement est déjà fait
        start_battle(game, index, game.wave)
    elif not _go(game, "event", [ZONE_KEYS[index]]):
        event_done(game, index)


def event_done(game: Game, index: int, after: bool = False) -> None:
    """Un événement est fini : préparation (si prévue), puis dialogue de fin (`after`), puis premier combat."""
    if not after and index in PREPARE_ZONES and "prepare" in SCENES:
        _go(game, "prepare", ["flow"])
    elif not after and index in OUTRO_ZONES:
        prepare_done(game)
    else:
        start_battle(game, index, 0)


def prepare_done(game: Game) -> None:
    """La préparation est finie : dialogue de Garland / Sephiroth s'il y en a un, sinon premier combat."""
    if game.zone in OUTRO_ZONES and "event" in SCENES:
        _go(game, "event", [ZONE_KEYS[game.zone], "after"])
    else:
        start_battle(game, game.zone, 0)


def start_battle(game: Game, index: int, wave: int) -> None:
    """Ouvre la scène de combat de la vague `wave` (0-based) de la zone `index`."""
    game.zone, game.wave = index, wave
    if "battle" in SCENES:
        game.replace(SCENES["battle"](game, [ZONE_KEYS[index], str(wave + 1)]), transition="fade")
    else:  # la scène de combat n'existe pas encore : on reste jouable
        log_error("[flow] scène « battle » absente, retour à la carte")
        open_world_map(game)


def after_battle(game: Game) -> None:
    """Après le butin : vague suivante, zone terminée (sauvegarde + carte) ou fin du jeu."""
    from final_classe.game.zones import ZONES

    if game.party is not None:
        game.party.rest()
    index = game.zone
    number = game.wave + 1
    if number < len(ZONES[index].waves()):
        game.wave = number
        game.save()  # comme le terminal : reprise à la vague suivante
        start_battle(game, index, number)
        return
    game.wave = 0
    game.zone = index + 1
    if index + 1 < len(ZONES):
        game.save()
        open_world_map(game, cleared=True)
    elif not _go(game, "ending", []):
        open_world_map(game)
