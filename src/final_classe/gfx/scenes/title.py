"""Écran titre : fond, emblème, titre rendu par le code, menu, emplacements de sauvegarde."""

import math
import random
from typing import override

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.ui import (
    Banner, Menu, draw_text, draw_window, get_font, is_cancel, theme, vertical_gradient,
)
from final_classe.gfx.scenes._demo import DemoScript, key_event
from final_classe.storage import SLOTS, SaveError, peek

_title_cache: dict[str, pygame.Surface] = {}
_sparks: dict[tuple[int, int], pygame.Surface] = {}
_pulses: dict[int, pygame.Surface] = {}


def _spark(size: int, alpha: int) -> pygame.Surface:
    """Une étincelle dorée (taille, alpha quantifié) mise en cache."""
    key = (size, alpha)
    if key not in _sparks:
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*theme.GOLD, min(255, alpha)), (4, 4), size)
        _sparks[key] = surf
    return _sparks[key]


def _pulsed_title(title: pygame.Surface, step: int) -> pygame.Surface:
    """Le titre à l'une de 8 tailles (de 1,0 à 1,024), mis en cache."""
    if step not in _pulses:
        k = 1.0 + 0.024 * step / 7 - 0.012
        _pulses[step] = pygame.transform.smoothscale(
            title, (int(title.get_width() * k), int(title.get_height() * k)))
    return _pulses[step]


def _title_surface(text: str, size: int) -> pygame.Surface:
    """Le titre : lettres à dégradé or, contour sombre, éclat doux (mis en cache)."""
    key = f"{text}/{size}"
    if key in _title_cache:
        return _title_cache[key]
    font = get_font(size, bold=True, title=True)
    glyph = font.render(text, True, (255, 255, 255))
    w, h = glyph.get_size()
    pad = 40
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    # éclat : copie réduite puis agrandie, teintée or, en additif
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    glow.blit(glyph, (0, 0))
    glow.fill((*theme.GOLD, 255), special_flags=pygame.BLEND_RGBA_MULT)
    small = pygame.transform.smoothscale(glow, (max(1, w // 6), max(1, h // 6)))
    big = pygame.transform.smoothscale(small, (w + 20, h + 20))
    out.blit(big, (pad - 10, pad - 10), special_flags=pygame.BLEND_RGBA_ADD)
    # contour
    dark = font.render(text, True, (12, 16, 48))
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 10:
                out.blit(dark, (pad + dx, pad + dy + 3))
    # lettres en dégradé
    fill = glyph.copy()
    grad = vertical_gradient((w, h), (255, 250, 225), (226, 150, 40))
    fill.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    out.blit(fill, (pad, pad))
    _title_cache[key] = out
    return out


_cache: dict[str, pygame.Surface] = {}
_sparks: dict[tuple[int, int], pygame.Surface] = {}
_pulses: dict[int, pygame.Surface] = {}


def _spark(size: int, alpha: int) -> pygame.Surface:
    """Une étincelle dorée (taille, alpha quantifié) mise en cache."""
    key = (size, alpha)
    if key not in _sparks:
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*theme.GOLD, min(255, alpha)), (4, 4), size)
        _sparks[key] = surf
    return _sparks[key]


def _pulsed_title(title: pygame.Surface, step: int) -> pygame.Surface:
    """Le titre à l'une de 8 tailles (de 1,0 à 1,024), mis en cache."""
    if step not in _pulses:
        k = 1.0 + 0.024 * step / 7 - 0.012
        _pulses[step] = pygame.transform.smoothscale(
            title, (int(title.get_width() * k), int(title.get_height() * k)))
    return _pulses[step]


def _shade_surface() -> pygame.Surface:
    """Voile qui assombrit le bas de l'écran (calculé une fois)."""
    if "shade" not in _cache:
        shade = pygame.Surface((1280, 720), pygame.SRCALPHA)
        for y in range(720):
            pygame.draw.line(shade, (4, 8, 28, int(max(0, (y - 380) / 340) * 150)), (0, y), (1280, y))
        _cache["shade"] = shade
    return _cache["shade"]


def _halo_surface() -> pygame.Surface:
    """Halo doré à dégradé radial doux (calculé une fois)."""
    if "halo" not in _cache:
        halo = pygame.Surface((420, 420), pygame.SRCALPHA)
        for r in range(210, 0, -3):
            a = int(30 * (1 - r / 210) ** 2)
            pygame.draw.circle(halo, (*theme.GOLD, a), (210, 210), r)
        _cache["halo"] = halo
    return _cache["halo"]


def _slot_summary(slot: int) -> tuple[str, bool]:
    """Le résumé d'un emplacement et s'il est utilisable."""
    try:
        data = peek(slot)
    except SaveError as error:
        text = "Vide" if "Aucune" in str(error) else "Illisible"
        return (text, False)
    heroes = data["party"].get("heroes", [])
    lead = heroes[0] if heroes else {}
    zone = data["zone"]
    return (
        f"{lead.get('name', '?')}  {lead.get('job', '')}  niv. {lead.get('level', '?')}"
        f"   zone {zone + 1}   {data['date']}",
        True,
    )


class TitleScene(Scene):
    """Nouvelle partie / Continuer / Options / Quitter."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.time = 0.0
        self.menu = Menu(["Nouvelle partie", "Continuer", "Options", "Quitter"],
                         (490, 470), width=300, row_h=44, font_size=28, align="center")
        self.slot_menu: Menu | None = None
        self.slot_ok: list[bool] = []
        self.slot_mode = "load"  # « new » : où commencer ; « load » : quoi reprendre
        self.banner: Banner | None = None
        rng = random.Random(7)
        # étincelles : (x, y, vitesse, phase, taille)
        self.sparks = [
            [rng.uniform(0, 1280), rng.uniform(0, 720), rng.uniform(12, 40),
             rng.uniform(0, 6.28), rng.uniform(1.2, 3.2)]
            for _ in range(55)
        ]
        self._refresh_continue()
        self.script = DemoScript(game, [
            (1.5, lambda: self.handle_event(key_event(pygame.K_RETURN))),
            (2.5, lambda: self.handle_event(key_event(pygame.K_RETURN))),
        ]) if game.demo else None

    def _open_slots(self, mode: str) -> None:
        """Ouvre la liste des emplacements (nouvelle partie : tous choisissables, écrasement signalé)."""
        self.slot_mode = mode
        infos = [_slot_summary(s) for s in range(1, SLOTS + 1)]
        labels = []
        for number, (text, ok) in enumerate(infos, start=1):
            suffix = "   (sera écrasé)" if mode == "new" and ok else ""
            labels.append(f"{number}.  {text}{suffix}")
        self.slot_menu = Menu(labels, (190, 450), width=900, row_h=44, font_size=24)
        self.slot_ok = [ok for _, ok in infos]
        if mode == "new":
            self.slot_menu.cursor = self.slot_ok.index(False) if False in self.slot_ok else 0
        else:
            self.slot_menu.enabled = list(self.slot_ok)
            self.slot_menu.cursor = self.slot_ok.index(True) if True in self.slot_ok else 0

    def _refresh_continue(self) -> None:
        has_save = any(_slot_summary(s)[1] for s in range(1, SLOTS + 1))
        self.menu.enabled[1] = has_save

    @override
    def on_enter(self) -> None:
        preload = getattr(self.game.audio, "preload", None)
        if callable(preload):
            try:
                preload()
            except Exception:
                pass
        self.game.audio.play_music("title")

    @override
    def on_resume(self) -> None:
        self._refresh_continue()
        self.game.audio.play_music("title")

    @override
    def on_back(self) -> None:
        if self.slot_menu is not None:
            self.slot_menu = None

    def _go(self, name: str, *fallbacks: str) -> bool:
        for candidate in (name, *fallbacks):
            if candidate in SCENES:
                self.game.replace(SCENES[candidate](self.game, []))
                return True
        self.banner = Banner("Cette scène arrive bientôt", seconds=1.6, y=300, size=34)
        self.game.audio.play_sfx("error")
        return False

    def _confirm(self, index: int) -> None:
        audio = self.game.audio
        if index == 0:
            audio.play_sfx("menu_open")
            self._open_slots("new")
        elif index == 1:
            audio.play_sfx("menu_open")
            self._open_slots("load")
        elif index == 2:
            audio.play_sfx("confirm")
            if "options" in SCENES:
                self.game.push(SCENES["options"](self.game, []), transition="fade")
        elif index == 3:
            self.game.quit()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.slot_menu is not None:
            if self.game.transitioning:
                return
            if is_cancel(event):
                self.slot_menu = None
                self.game.audio.play_sfx("cancel")
                return
            chosen = self.slot_menu.handle_event(event)
            if chosen is not None and self.slot_mode == "new":
                self.game.audio.play_sfx("confirm")
                self.game.party = None
                self.game.slot = chosen + 1
                self.game.zone = self.game.wave = 0
                self.slot_menu = None
                self._go("prologue", "creation")
            elif chosen is not None:
                if self.game.load(chosen + 1):
                    self.game.audio.play_sfx("confirm")
                    self._go("world_map")
                else:
                    self.game.audio.play_sfx("error")
            return
        before = self.menu.cursor
        chosen = self.menu.handle_event(event)
        if self.menu.cursor != before:
            self.game.audio.play_sfx("cursor")
        if chosen is not None:
            self._confirm(chosen)
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE) \
                and not self.menu.enabled[self.menu.cursor]:
            self.game.audio.play_sfx("error")

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        if self.script:
            self.script.update(dt)
        self.menu.update(dt)
        if self.slot_menu:
            self.slot_menu.update(dt)
        for s in self.sparks:
            s[1] -= s[2] * dt
            s[0] += math.sin(self.time * 0.8 + s[3]) * 10 * dt
            if s[1] < -10:
                s[0], s[1] = random.uniform(0, 1280), 730
        if self.banner and not self.banner.update(dt):
            self.banner = None

    def _draw_background(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        if assets.exists("bg_title"):
            surface.blit(assets.image("bg_title"), (0, 0))
            shade = _shade_surface()
            surface.blit(shade, (0, 0))
        else:
            surface.blit(vertical_gradient((1280, 720), (10, 16, 60), (40, 30, 90)), (0, 0))
            rng = random.Random(3)
            for _ in range(90):
                x, y = rng.randrange(1280), rng.randrange(420)
                b = 120 + int(100 * (0.5 + 0.5 * math.sin(self.time * 2 + x)))
                pygame.draw.circle(surface, (b, b, min(255, b + 30)), (x, y), rng.choice((1, 1, 2)))

    def _draw_emblem(self, surface: pygame.Surface, center: tuple[int, int]) -> None:
        assets = self.game.assets
        bob = math.sin(self.time * 1.6) * 5
        cx, cy = center[0], center[1] + bob
        surface.blit(_halo_surface(), (cx - 210, cy - 210))
        if assets.exists("ui_emblem"):
            img = assets.image("ui_emblem")
            h = 210
            w = int(img.get_width() * h / img.get_height())
            surface.blit(assets.scaled("ui_emblem", (w, h)), (cx - w // 2, cy - h // 2))
        else:  # cristal dessiné par le code
            pts = [(cx, cy - 90), (cx + 50, cy - 10), (cx, cy + 90), (cx - 50, cy - 10)]
            pygame.draw.polygon(surface, (120, 190, 255), pts)
            pygame.draw.polygon(surface, (220, 240, 255), [pts[0], pts[1], (cx, cy - 10)])
            pygame.draw.polygon(surface, (70, 120, 220), [pts[2], pts[3], (cx, cy - 10)])
            pygame.draw.polygon(surface, theme.WHITE, pts, 2)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_background(surface)
        for x, y, _v, ph, size in self.sparks:
            a = int(110 + 100 * math.sin(self.time * 2 + ph))
            surface.blit(_spark(int(size), max(0, min(255, a)) // 32 * 32 + 16), (x, y))
        self._draw_emblem(surface, (640, 150))
        title = _title_surface("FINAL CLASSE", 104)
        step = round((math.sin(self.time * 2) * 0.5 + 0.5) * 7)  # 8 tailles pré-rendues
        title = _pulsed_title(title, step)
        surface.blit(title, title.get_rect(center=(640, 335)))
        draw_text(surface, "un RPG à la façon des grands classiques", (640, 410), 20,
                  theme.TEXT_DIM, "center")
        if self.slot_menu is None:
            self.menu.draw(surface, self.game.assets)
        else:
            draw_window(surface, (170, 400, 940, 40))
            head = "Où commencer l'aventure ?" if self.slot_mode == "new" else "Quelle partie reprendre ?"
            draw_text(surface, f"{head}  (Retour arrière : annuler)", (640, 420),
                      20, theme.GOLD, "center")
            self.slot_menu.draw(surface, self.game.assets)
        draw_text(surface, "Entrée : valider   Flèches : choisir   F11 : plein écran",
                  (640, 696), 16, theme.TEXT_DIM, "center")
        if self.banner:
            self.banner.draw(surface)


@register_scene("title")
def make_title(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène titre."""
    return TitleScene(game)
