"""Événements d'avant-zone : marchand, coffre, Cid, Garland, Sephiroth (refonte de `game/zones.py`).

Un événement est une liste d'étapes (`Talk`, `Ask`, `Do`, `OpenChest`, `ShopVisit`) jouée par `EventScene`.
Les effets sur la `Party` sont ceux du terminal (mêmes fonctions du catalogue) et s'appliquent une seule fois.
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import override

import pygame

from final_classe.characters import Party
from final_classe.gfx.engine import Game, Scene, make_demo_party, register_scene
from final_classe.gfx.scenes import flow
from final_classe.gfx.ui import DialogBox, Menu, draw_text, draw_window, is_cancel, theme
from final_classe.items import Elixir, Ether, PhoenixDown, catalog

Lines = list[tuple[str | None, str]]


@dataclass
class Talk:
    """Des pages de dialogue (`speaker` None = narration)."""

    speaker: str | None
    pages: list[str]
    bg: str | None = None
    portrait: str | None = None
    music: str | None = None
    prop: str | None = None  # « chest » : le coffre reste affiché


@dataclass
class Ask:
    """Un choix ; `pick(i)` renvoie les étapes à jouer ensuite."""

    prompt: str
    options: list[str]
    pick: Callable[[int], "list[Step]"]


@dataclass
class Do:
    """Un effet réel sur l'équipe ; les lignes renvoyées sont montrées dans une fenêtre."""

    effect: Callable[[Party], Lines]
    title: str


@dataclass
class OpenChest:
    """Anime l'ouverture du coffre."""


@dataclass
class ShopVisit:
    """Ouvre la boutique de Cid (« first » ou « second »)."""

    which: str


Step = Talk | Ask | Do | OpenChest | ShopVisit


# --- les effets (mêmes que game/zones.py, sans affichage terminal) ------------------------
def _equip_starters(party: Party) -> Lines:
    """Logique de `equip_starters` : arme selon la meilleure stat, armure de cuir, pour chacun."""
    out: Lines = []
    for hero in party.heroes:
        weapon = catalog.rod() if hero.magic > hero.strength else catalog.bronze_sword()
        armor = catalog.leather_armor()
        hero.equip(weapon)
        hero.equip(armor)
        out.append((flow.equipment_icon(weapon), f"{hero.name} : {weapon.name}, {armor.name}"))
    return out


def _open_chest(party: Party) -> Lines:
    gear = [catalog.mythril_sword(), catalog.mythril_rod(), catalog.mythril_armor(), catalog.ribbon()]
    party.bag.extend(gear)
    party.materias.extend([catalog.fire(), catalog.ice(), catalog.thunder(), catalog.cure()])
    party.materias.extend([catalog.ifrit(), catalog.shiva(), catalog.ramuh()])
    party.items.add(Ether(), Ether(), PhoenixDown(), Elixir())
    return [
        ("icon_sword", "Épée de mythril"), ("icon_rod", "Bâton de mythril"),
        ("icon_armor", "Armure de mythril"), ("icon_accessory", "Ruban"),
        ("icon_materia_green", "Feu, Glace, Foudre, Soin"),
        ("icon_materia_red", "Ifrit, Shiva, Ramuh"),
        ("icon_ether", "Éther ×2"), ("icon_phoenix_down", "Queue de phénix"), ("icon_elixir", "Élixir"),
    ]


def _bahamut(party: Party) -> Lines:
    party.materias.append(catalog.bahamut())
    return [("icon_materia_red", "Materia Bahamut")]


def _signatures(party: Party) -> Lines:
    out: Lines = []
    for hero in party.heroes:
        weapon = catalog.SIGNATURES[hero.JOB_NAME]()
        previous = hero.equip(weapon)
        if previous is not None:
            party.bag.append(previous)
        out.append((flow.equipment_icon(weapon), f"{hero.name} : {weapon.name}"))
    return out


# --- les scénarios ------------------------------------------------------------------------
def _cid_visit(which: str, bg: str) -> list[Step]:
    def pick(i: int) -> list[Step]:
        if i == 0:
            return [ShopVisit(which)]
        return [Talk("Cid", ["Comme vous voudrez. Revenez quand vos poches seront pleines !"], bg=bg)]

    return [Ask("Cid vous tend son étal.", ["Voir l'étal de Cid", "Passer son chemin"], pick)]


def _chest_ask() -> Ask:
    def pick(i: int) -> list[Step]:
        if i == 0:
            return []
        return [Talk(None, ["Rien d'autre que des cristaux qui chantonnent. Le coffre attire tous les regards."]),
                _chest_ask()]

    return Ask("Un vieux coffre scellé.", ["Ouvrir le coffre", "Examiner les alentours"], pick)


def script(index: int, after: bool = False) -> list[Step]:
    """Les étapes de l'événement d'avant-zone `index` (`after` : le dialogue joué après la préparation)."""
    if after:
        if index == 3:
            return [Talk("Garland", ["Moi, Garland, je vais tous vous écraser !"], bg="bg_chaos",
                         portrait="mon_garland", music="boss")]
        return [Talk("Sephiroth", ["Tu es revenu… Cette fois, je vais te montrer le désespoir."], bg="bg_crater",
                     portrait="mon_sephiroth", music="final_boss")]
    if index == 0:
        return [
            Talk(None, ["Les Plaines de Dalmasca s'étendent à perte de vue. Le vent porte une odeur de poussière et de fer.",
                        "Cinq ans après Nibelheim, l'équipe se met en marche. Quelque chose de gélatineux bouge au loin…"],
                 bg="bg_plains", music="shop"),
        ]
    if index == 1:
        def refuse(i: int) -> list[Step]:
            if i == 0:
                return []
            return [Talk("Marchand ambulant", ["Allons, allons ! Dans cette forêt, on ne passe pas les mains vides. Prenez, c'est cadeau !"])]

        return [
            Talk(None, ["À l'orée de la Forêt de Macalania, un marchand ambulant vous fait de grands signes."],
                 bg="bg_forest", music="shop"),
            Talk("Marchand ambulant", ["Ah, des aventuriers ! Les Bombos et les Ahrimans rôdent là-dedans.",
                                       "Un marchand ambulant vous offre de quoi vous équiper : tenez !"]),
            Ask("Que répondez-vous ?", ["Accepter son offre", "Refuser poliment"], refuse),
            Do(_equip_starters, "Équipement reçu"),
        ]
    if index == 2:
        return [
            Talk(None, ["Au fond de la Grotte des cristaux, une alcôve baigne dans une lueur bleutée. Un coffre ancien y repose."],
                 bg="bg_cave", music="shop", prop="chest"),
            _chest_ask(),
            OpenChest(),
            Do(_open_chest, "Contenu du coffre"),
            Talk(None, ["Équipement, materias et objets rejoignent le sac. Un moment pour se préparer."]),
        ]
    if index == 3:
        return [
            Talk(None, ["Un dirigeable cabossé est posé dans la lande, juste avant le Sanctuaire du Chaos : l'atelier de Cid."],
                 bg="bg_shop", music="shop"),
            Talk("Cid", ["Hé ! Des aventuriers, enfin. Approchez : du solide, et pas cher.",
                         "Au Sanctuaire du Chaos, on n'entre pas sans diamant au bras."]),
            *_cid_visit("first", "bg_shop"),
        ]
    return [
        Talk(None, ["Au pied du Cratère Nord, le sol tremble. Un éclat rouge roule jusqu'à vos pieds : la dépouille de Garland."],
             bg="bg_crater", music="shop"),
        Do(_bahamut, "Garland laisse tomber une materia rouge"),
        Talk(None, ["Au pied du Cratère, chacun retrouve son arme légendaire."]),
        Do(_signatures, "Armes légendaires"),
        Talk("Cid", ["Je savais que vous reviendriez ! Dernière tournée : l'étal de cristal."], bg="bg_shop"),
        *_cid_visit("second", "bg_shop"),
    ]


# --- la scène -----------------------------------------------------------------------------
@dataclass
class _Spark:
    x: float
    y: float
    vy: float
    life: float
    size: float = field(default=2.0)


class EventScene(Scene):
    """Joue le scénario de la zone : dialogues, choix, effets, boutique."""

    def __init__(self, game: Game, index: int, after: bool = False) -> None:
        super().__init__(game)
        if game.party is None:
            game.party = make_demo_party()
        self.index = index
        self.after = after
        game.zone = index
        self.queue: list[Step] = script(index, after)
        self.bg = "bg_plains"
        self.portrait: str | None = None
        self.prop: str | None = None
        self.time = 0.0
        self.dialog: DialogBox | None = None
        self.ask: Ask | None = None
        self.menu: Menu | None = None
        self.loot: tuple[str, Lines] | None = None
        self.chest_t = -1.0  # <0 fermé ; 0..1 s ouverture
        self.waiting_shop = False
        self.fade_in = 0.0
        self.sparks: list[_Spark] = []
        self.pilot = flow.KeyPilot(game, [pygame.K_RETURN] * 40, period=1.1, start=1.2)
        self.rng = random.Random(5)
        self.finished = False

    # --- déroulement -------------------------------------------------------------------
    @override
    def on_enter(self) -> None:
        self._next()

    @override
    def on_resume(self) -> None:
        self.game.audio.play_music("shop")
        if self.waiting_shop:
            self.waiting_shop = False
            self._next()

    @override
    def on_back(self) -> None:
        """Échap : sans effet (on ne saute pas un événement)."""

    def _next(self) -> None:
        if self.finished:
            return
        self.dialog = self.ask = self.menu = self.loot = None
        if not self.queue:
            self.finished = True
            flow.event_done(self.game, self.index, self.after)
            return
        step = self.queue.pop(0)
        if isinstance(step, Talk):
            if step.bg and step.bg != self.bg:
                self.bg = step.bg
                self.fade_in = 0.5
            self.portrait = step.portrait
            self.prop = step.prop if step.prop else (self.prop if step.bg is None else None)
            if step.music:
                self.game.audio.play_music(step.music)
            self.dialog = DialogBox(step.pages, step.speaker)
        elif isinstance(step, Ask):
            self.ask = step
            self.menu = Menu(step.options, (90, 584), width=700, row_h=40, window=False)
            self.game.audio.play_sfx("menu_open")
        elif isinstance(step, Do):
            lines = step.effect(self.game.party)
            self.loot = (step.title, lines)
            self.game.audio.play_sfx("confirm")
        elif isinstance(step, OpenChest):
            self.chest_t = 0.0
            self.game.audio.play_sfx("confirm")
        elif isinstance(step, ShopVisit):
            self.waiting_shop = True
            flow.open_shop(self.game, step.which)
            if "shop" not in flow.SCENES:  # pas de boutique : on enchaîne
                self.waiting_shop = False
                self._next()

    def _confirm(self) -> None:
        a = self.game.audio
        if self.dialog is not None:
            was_done = self.dialog.page_complete
            self.dialog.advance()
            if was_done:
                a.play_sfx("confirm")
            if self.dialog.done:
                self._next()
        elif self.loot is not None:
            a.play_sfx("confirm")
            self._next()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.menu is not None and self.ask is not None:
            before = self.menu.cursor
            chosen = self.menu.handle_event(event)
            if self.menu.cursor != before:
                self.game.audio.play_sfx("cursor")
            if chosen is not None:
                self.game.audio.play_sfx("confirm")
                ask = self.ask
                self.queue[0:0] = ask.pick(chosen)
                self._next()
            return
        confirm = (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z)) \
            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        if confirm:
            self._confirm()

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.fade_in = max(0.0, self.fade_in - dt)
        if self.dialog is not None:
            self.dialog.update(dt)
        if self.menu is not None:
            self.menu.update(dt)
        if 0 <= self.chest_t < 1.0:
            self.chest_t += dt / 1.2
            if self.chest_t >= 1.0:
                self.chest_t = 1.0
                self._next()
            for _ in range(2):
                self.sparks.append(_Spark(640 + self.rng.uniform(-80, 80), 420, -self.rng.uniform(40, 140),
                                          self.rng.uniform(0.6, 1.4), self.rng.uniform(2, 4)))
        for s in self.sparks:
            s.y += s.vy * dt
            s.life -= dt
        self.sparks = [s for s in self.sparks if s.life > 0]
        if not self.waiting_shop and not self.finished:
            key = self.pilot.update(dt)
            if key is not None:
                flow.press(self, key)

    # --- dessin ------------------------------------------------------------------------
    def _draw_chest(self, surface: pygame.Surface) -> None:
        o = max(0.0, self.chest_t)
        cx, base = 640, 470
        if o > 0:
            halo = flow.glow_disc(150, theme.ICE, max(4, int(30 * o)) // 4 * 4)
            surface.blit(halo, (cx - 150, base - 190))
        body = pygame.Rect(cx - 100, base - 80, 200, 80)
        pygame.draw.rect(surface, (90, 52, 28), body, border_radius=6)
        pygame.draw.rect(surface, (50, 28, 14), body, 3, border_radius=6)
        pygame.draw.rect(surface, theme.GOLD, (cx - 100, base - 50, 200, 8))
        lift = int(o * 46)
        lid = [(cx - 100, base - 80), (cx + 100, base - 80), (cx + 96, base - 80 - 36 - lift // 3), (cx - 96, base - 80 - 36 - lift)]
        pygame.draw.polygon(surface, (110, 64, 34), lid)
        pygame.draw.polygon(surface, (50, 28, 14), lid, 3)
        pygame.draw.circle(surface, theme.GOLD, (cx, base - 48), 8)
        for s in self.sparks:
            pygame.draw.circle(surface, theme.ICE, (int(s.x), int(s.y)), int(s.size))

    @override
    def draw(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        flow.draw_backdrop(surface, assets, self.bg, 0.15)
        if self.portrait:
            surface.blit(flow.glow_disc(240, (140, 60, 200), 14), (660, 70))
            bob = math.sin(self.time * 1.6) * 4
            flow.draw_portrait(surface, assets, self.portrait, pygame.Rect(780, 50 + bob, 400, 470))
        if self.prop == "chest":
            self._draw_chest(surface)
        if self.dialog is not None:
            self.dialog.draw(surface)
        elif self.ask is not None and self.menu is not None:
            draw_window(surface, (60, 530, 1160, 160))
            draw_text(surface, self.ask.prompt, (90, 548), 24, theme.GOLD, bold=True)
            self.menu.draw(surface, assets)
        elif self.loot is not None:
            title, lines = self.loot
            h = 110 + 44 * len(lines)
            rect = pygame.Rect(340, max(40, 360 - h // 2), 600, h)
            draw_window(surface, rect)
            draw_text(surface, title, (rect.centerx, rect.y + 34), 28, theme.GOLD, "center", bold=True, title=True)
            for k, (icon, text) in enumerate(lines):
                y = rect.y + 84 + k * 44
                if icon:
                    flow.draw_icon(surface, assets, icon, (rect.x + 50, y), 36)
                draw_text(surface, text, (rect.x + 84, y), 22, theme.TEXT, "midleft")
        if self.fade_in > 0:
            surface.blit(flow.solid((1280, 720), (0, 0, 0, int(255 * self.fade_in / 0.5) // 8 * 8)), (0, 0))


@register_scene("event")
def make_event(game: Game, args: list[str]) -> Scene:
    """Fabrique : `event:<clé de zone>` (plains, forest, cave, chaos, crater)."""
    index = flow.ZONE_KEYS.index(args[0]) if args and args[0] in flow.ZONE_KEYS else game.zone
    return EventScene(game, min(max(index, 0), len(flow.ZONE_KEYS) - 1), "after" in args)
