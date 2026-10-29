"""Prologue : Nibelheim, il y a cinq ans. Duel scripté, perdu d'avance, contre Sephiroth.

La logique est jouée d'un coup à la création (les PV du modèle sont déjà à jour) ; la scène ne fait
que rejouer les échanges, avec des PV affichés qui glissent vers la vraie valeur.
"""

import math
import random
from dataclasses import dataclass, field
from typing import override

import pygame

from final_classe.characters import Sephiroth, Soldier
from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.flow import solid
from final_classe.gfx.ui import (
    Banner, DialogBox, draw_bar, draw_text, draw_window, hp_color, is_confirm, render_text, theme,
    vertical_gradient,
)

CLOUD_HOME = (400.0, 610.0)
SEPH_HOME = (900.0, 610.0)
CARD_TIME = 3.2
FINAL_TIME = 2.4
OUTRO_TIME = 3.0


@dataclass
class Fighter:
    """Un combattant à l'écran : sprite, position au repos et déplacements temporaires."""

    image: str
    home: tuple[float, float]
    flip: bool
    offset: float = 0.0          # déplacement horizontal (élan)
    flash: float = 0.0           # secondes de flash blanc restantes
    squash: float = 1.0          # écrasement vertical (genou à terre)
    gray: float = 0.0            # 0..1 : grisé du K.O.
    drift: float = 0.0           # recul subi


@dataclass
class Popup:
    """Un chiffre de dégâts qui monte et s'estompe."""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    size: int
    t: float = 0.0


@dataclass
class Round:
    """Un échange : dégâts de Cloud, dégâts de Sephiroth et PV de Cloud ensuite."""

    cloud_damage: int
    seph_damage: int
    cloud_hp: int
    seph_hp: int


@dataclass
class Embers:
    """Braises et flammes de Nibelheim en feu (particules additives)."""

    rng: random.Random = field(default_factory=lambda: random.Random(11))
    parts: list[list[float]] = field(default_factory=list)  # x, y, vx, vy, vie, vie max, taille
    glows: dict[tuple[int, int, int], pygame.Surface] = field(default_factory=dict)

    def _glow(self, size: int, level: int, kind: int) -> pygame.Surface:
        key = (size, level, kind)
        surf = self.glows.get(key)
        if surf is None:
            surf = pygame.Surface((size * 2, size * 2))
            base = ((255, 120, 30), (255, 190, 80))[kind]
            for i in range(size, 0, -2):
                f = (1 - i / size) ** 1.6 * level / 8
                pygame.draw.circle(surf, (int(base[0] * f), int(base[1] * f * 0.8), int(base[2] * f * 0.5)),
                                   (size, size), i)
            self.glows[key] = surf
        return surf

    def update(self, dt: float) -> None:
        """Fait naître et vieillir les particules."""
        for _ in range(int(self.rng.random() + 90 * dt)):
            x = self.rng.uniform(-40, 1320)
            big = self.rng.random() < 0.35
            self.parts.append([
                x, self.rng.uniform(560, 740), self.rng.uniform(-14, 14),
                self.rng.uniform(-90, -40) if big else self.rng.uniform(-170, -80),
                0.0, self.rng.uniform(1.4, 2.8) if big else self.rng.uniform(0.8, 1.8),
                self.rng.uniform(40, 70) if big else self.rng.uniform(5, 12),
            ])
        alive = []
        for p in self.parts:
            p[4] += dt
            if p[4] < p[5]:
                p[0] += (p[2] + math.sin(p[4] * 4 + p[0]) * 18) * dt
                p[1] += p[3] * dt
                alive.append(p)
        self.parts = alive[-260:]

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine les particules en additif."""
        for x, y, _vx, _vy, age, life, size in self.parts:
            ratio = age / life
            level = max(1, min(8, int(8 * math.sin(math.pi * min(1.0, ratio)))))
            s = int(size * (1.1 - 0.5 * ratio))
            if s < 3:
                continue
            glow = self._glow(s // 2 * 2 + 2, level, 1 if size < 15 else 0)
            surface.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2),
                         special_flags=pygame.BLEND_ADD)


_shadow_cache: list[pygame.Surface] = []


def _shadow() -> pygame.Surface:
    """Ombre elliptique au sol (calculée une fois)."""
    if not _shadow_cache:
        surf = pygame.Surface((220, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 110), surf.get_rect())
        _shadow_cache.append(surf)
    return _shadow_cache[0]


def _tri(u: float) -> float:
    """0 → 1 → 0 sur u de 0 à 1 (aller rapide, retour plus doux)."""
    if u <= 0 or u >= 1:
        return 0.0
    if u < 0.4:
        return 1 - (1 - u / 0.4) ** 3
    return 1 - ((u - 0.4) / 0.6) ** 2


class PrologueScene(Scene):
    """Carton-titre → duel → coup final → dialogue → « Cinq ans plus tard… » → création."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        cloud = Soldier("Cloud", strength=20, magic=12, defense=15, resistance=13)
        seph = Sephiroth()
        self.cloud_max = cloud.max_hp
        self.seph_max = seph.max_hp
        self.rounds: list[Round] = []
        while cloud.is_alive:  # la logique du terminal : Cloud frappe, Sephiroth riposte
            d1 = cloud.attack(seph)
            d2 = seph.attack(cloud)
            self.rounds.append(Round(d1, d2, cloud.hp, seph.hp))
        self.round_time = max(0.45, min(0.95, 7.0 / len(self.rounds)))
        self.cloud = Fighter("hero_soldier", CLOUD_HOME, flip=True)   # l'image regarde à gauche
        self.seph = Fighter("mon_sephiroth", SEPH_HOME, flip=True)    # l'image regarde à droite
        self.cloud_hp_shown = float(self.cloud_max)
        self.cloud_hp_target = float(self.cloud_max)
        self.seph_hp_shown = float(self.seph_max)
        self.seph_hp_target = float(self.seph_max)
        self.embers = Embers()
        self.popups: list[Popup] = []
        self.stage = "card"
        self.t = 0.0
        self.index = 0           # échange en cours
        self.fired: set[str] = set()
        self.shake = 0.0
        self.flash = 0.0
        self.fast = False
        self.dialog: DialogBox | None = None
        self.dialog_no = 0
        self.dialog_wait = 0.0
        self.canvas = pygame.Surface((1280, 720))
        self.white = pygame.Surface((1280, 720))
        self.white.fill((255, 255, 255))
        self.black = pygame.Surface((1280, 720))
        self.banner: Banner | None = None
        self.time = 0.0

    # --- cycle de vie ---------------------------------------------------------------
    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("prologue")

    def _go_next(self) -> None:
        for name in ("creation", "world_map"):
            if name in SCENES:
                self.game.replace(SCENES[name](self.game, []))
                return
        self.banner = Banner("La suite arrive bientôt", seconds=2.0, y=300, size=34)

    def _set_stage(self, stage: str) -> None:
        self.stage = stage
        self.t = 0.0
        self.fired.clear()

    @override
    def on_back(self) -> None:
        """Échap : saute le duel (ou la scène entière une fois les dialogues vus)."""
        if self.stage in ("card", "duel"):
            self._finish_duel()
        elif self.stage in ("final", "dialog"):
            self._set_stage("outro")
            self.dialog = None

    def _finish_duel(self) -> None:
        last = self.rounds[-1]
        self.cloud_hp_target = float(last.cloud_hp)
        self.cloud_hp_shown = self.cloud_hp_target
        self.seph_hp_target = self.seph_hp_shown = float(last.seph_hp)
        self.cloud.offset = self.seph.offset = 0.0
        self._set_stage("final")

    # --- évènements -----------------------------------------------------------------
    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.stage == "dialog" and self.dialog is not None:
            self.dialog.handle_event(event)
        elif self.stage == "duel" and is_confirm(event):
            self.fast = not self.fast  # accélère les échanges

    # --- mise à jour ----------------------------------------------------------------
    def _popup(self, text: str, fighter: Fighter, color, size: int) -> None:
        self.popups.append(Popup(text, fighter.home[0] + fighter.offset, fighter.home[1] - 230,
                                 color, size))

    def _hit(self, target: Fighter, damage: int, heavy: bool = False) -> None:
        target.flash = 0.14
        target.drift = 40 if heavy else 14
        self.shake = max(self.shake, 14 if heavy else min(8.0, 2 + damage / 40))
        color = theme.GOLD if heavy else theme.WHITE
        self._popup(str(damage), target, color, 54 if heavy else 40)

    def _update_duel(self, dt: float) -> None:
        if self.index >= len(self.rounds):
            self._set_stage("final")
            return
        rd = self.rounds[self.index]
        last = self.index == len(self.rounds) - 1
        u = self.t / self.round_time
        audio = self.game.audio
        # Cloud charge puis revient (0 → 0,45), Sephiroth riposte (0,5 → 0,95)
        self.cloud.offset = 300 * _tri(u / 0.45)
        self.seph.offset = -(320 if last else 280) * _tri((u - 0.5) / 0.45)
        if u >= 0.18 and "c" not in self.fired:
            self.fired.add("c")
            audio.play_sfx("slash")
            self._hit(self.seph, rd.cloud_damage)
            self.seph_hp_target = float(rd.seph_hp)
        if u >= 0.68 and "s" not in self.fired:
            self.fired.add("s")
            audio.play_sfx("slash_heavy" if last else "impact")
            self._hit(self.cloud, rd.seph_damage, heavy=last)
            self.cloud_hp_target = float(rd.cloud_hp)
            if last:
                self.flash = 1.0
                audio.play_sfx("crit")
        if u >= 1.0:
            self.index += 1
            self.t = 0.0
            self.fired.clear()

    def _update_final(self) -> None:
        audio = self.game.audio
        k = min(1.0, self.t / 0.8)
        self.cloud.squash = 1 - 0.22 * k
        self.cloud.gray = k
        if "ko" not in self.fired:
            self.fired.add("ko")
            audio.play_sfx("ko_hero")
        if self.t >= FINAL_TIME:
            self._start_dialog()

    def _start_dialog(self) -> None:
        self._set_stage("dialog")
        self.dialog_no = 0
        self._next_dialog()

    def _next_dialog(self) -> bool:
        pages = (
            ("Sephiroth", "« Tu n'es qu'une marionnette. »"),
            (None, "Un jour, tu reviendras. Et cette fois, tu seras prêt."),
        )
        if self.dialog_no >= len(pages):
            return False
        speaker, text = pages[self.dialog_no]
        self.dialog = DialogBox(text, speaker=speaker)
        self.game.audio.play_sfx("text_blip")
        self.dialog_no += 1
        self.dialog_wait = 0.0
        return True

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.embers.update(dt)
        step = dt * (3.0 if self.fast else 1.0)
        self.t += step if self.stage == "duel" else dt
        # PV affichés qui glissent
        k = min(1.0, dt * 6)
        self.cloud_hp_shown += (self.cloud_hp_target - self.cloud_hp_shown) * k
        self.seph_hp_shown += (self.seph_hp_target - self.seph_hp_shown) * k
        for f in (self.cloud, self.seph):
            f.flash = max(0.0, f.flash - dt)
            f.drift = max(0.0, f.drift - 120 * dt)
        self.shake = max(0.0, self.shake - 30 * dt)
        self.flash = max(0.0, self.flash - dt * 1.4)
        for p in self.popups:
            p.t += dt
        self.popups = [p for p in self.popups if p.t < 1.1]
        if self.banner and not self.banner.update(dt):
            self.banner = None

        if self.stage == "card" and self.t >= CARD_TIME:
            self._set_stage("duel")
        elif self.stage == "duel":
            self._update_duel(step)
        elif self.stage == "final":
            self._update_final()
        elif self.stage == "dialog" and self.dialog is not None:
            self.dialog.update(dt)
            if self.game.demo and self.dialog.page_complete:
                self.dialog_wait += dt
                if self.dialog_wait > 1.2:
                    self.dialog.advance()
            if self.dialog.done and not self._next_dialog():
                self.dialog = None
                self._set_stage("outro")
        elif self.stage == "outro" and self.t >= OUTRO_TIME and not self.game.transitioning:
            self._set_stage("leaving")
            self._go_next()

    # --- dessin ---------------------------------------------------------------------
    def _draw_fighter(self, surface: pygame.Surface, f: Fighter) -> None:
        assets = self.game.assets
        x = f.home[0] + f.offset + (f.drift if f is self.cloud else -f.drift)
        rect = assets.draw_sprite(surface, f.image, (x, f.home[1]), 1.0, flip=f.flip,
                                  scale_y=f.squash)
        if f.gray > 0:  # K.O. : grisé bleuté
            g = int(255 * (1 - 0.6 * f.gray))
            shade = assets.scaled(f.image, rect.size, f.flip).copy()
            shade.fill((g, g, min(255, g + 20)), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(shade, rect)
        if f.flash > 0:  # flash blanc limité aux pixels du sprite
            add = assets.scaled(f.image, rect.size, f.flip).copy()
            add.fill((200, 200, 200), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(add, rect)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        draw_window(surface, (40, 36, 380, 92))
        draw_text(surface, "Cloud", (64, 50), 24, theme.GOLD, bold=True)
        ratio = self.cloud_hp_shown / self.cloud_max
        draw_bar(surface, (64, 88, 330, 16), ratio, hp_color(ratio))
        draw_text(surface, f"PV {max(0, round(self.cloud_hp_shown))}/{self.cloud_max}", (394, 56), 20,
                  theme.TEXT, "topright")
        draw_window(surface, (860, 36, 380, 92))
        draw_text(surface, "Sephiroth", (884, 50), 24, theme.GOLD, bold=True)
        sr = self.seph_hp_shown / self.seph_max
        draw_bar(surface, (884, 88, 330, 16), sr, hp_color(sr))
        draw_text(surface, f"PV {round(self.seph_hp_shown)}/{self.seph_max}", (1214, 56), 20,
                  theme.TEXT, "topright")

    @override
    def draw(self, surface: pygame.Surface) -> None:
        if self.stage in ("card", "outro", "leaving") and (self.stage != "outro" or self.t > 0.6):
            surface.fill((0, 0, 0))
            if self.stage == "card":
                text, alpha = "Nibelheim, il y a cinq ans…", self._fade(self.t, CARD_TIME)
            elif self.stage == "outro":
                text, alpha = "Cinq ans plus tard…", self._fade(self.t - 0.6, OUTRO_TIME - 0.6)
            else:
                return
            img = render_text(text, 46, theme.TEXT, title=True).copy()
            img.set_alpha(alpha)
            surface.blit(img, img.get_rect(center=(640, 360)))
            if self.banner:
                self.banner.draw(surface)
            return
        canvas = self.canvas
        assets = self.game.assets
        if assets.exists("bg_prologue"):
            canvas.blit(assets.image("bg_prologue"), (0, 0))
        else:
            canvas.blit(vertical_gradient((1280, 720), (60, 14, 10), (190, 70, 20)), (0, 0))
        self.embers.draw(canvas)
        # ombres au sol
        for f in (self.cloud, self.seph):
            canvas.blit(_shadow(), (f.home[0] + f.offset - 110, f.home[1] - 18))
        self._draw_fighter(canvas, self.seph)
        self._draw_fighter(canvas, self.cloud)
        for p in self.popups:
            a = max(0, min(255, int(255 * (1.1 - p.t) / 0.5)))
            bounce = -abs(math.sin(min(p.t, 0.6) * 7)) * 22 * (1 - p.t / 1.1) - p.t * 30
            img = render_text(p.text, p.size, p.color, bold=True).copy()
            img.set_alpha(a)
            canvas.blit(img, img.get_rect(center=(p.x, p.y + bounce)))
        # flash plein écran (coup final)
        if self.flash > 0:
            self.white.set_alpha(int(255 * min(1.0, self.flash)))
            canvas.blit(self.white, (0, 0))
        if self.stage in ("final", "dialog", "outro"):
            a = min(150, int(self.t * 120) // 10 * 10) if self.stage == "final" else 150
            canvas.blit(solid((1280, 720), (40, 0, 0, a)), (0, 0))
        if self.stage == "outro":
            self.black.set_alpha(min(255, int(255 * self.t / 0.6)))
            canvas.blit(self.black, (0, 0))
        sx = sy = 0
        if self.shake > 0:
            sx, sy = random.randint(-1, 1) * int(self.shake), random.randint(-1, 1) * int(self.shake)
        surface.fill((0, 0, 0))
        surface.blit(canvas, (sx, sy))
        self._draw_hud(surface)
        if self.stage == "duel":
            draw_text(surface, "Entrée : accélérer   Échap : passer", (640, 696), 16, theme.TEXT_DIM,
                      "center")
        if self.dialog is not None and self.stage == "dialog":
            self.dialog.draw(surface)

    @staticmethod
    def _fade(t: float, total: float) -> int:
        """Alpha d'un texte qui entre puis sort en fondu."""
        edge = 0.9
        v = min(t / edge, (total - t) / edge, 1.0)
        return max(0, min(255, int(255 * v)))


@register_scene("prologue")
def make_prologue(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène du prologue."""
    return PrologueScene(game)
