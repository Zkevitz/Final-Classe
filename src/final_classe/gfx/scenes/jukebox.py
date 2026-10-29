"""Test son : liste des musiques et des bruitages (docs/AUDIO.md §3-4), lecture, arrêt, volumes.

Tolérant : sans audio (ou sans la liste d'ids), la scène affiche des listes de repli et reste muette.
"""

import math
from typing import Any, override

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes._demo import DemoScript, key_event
from final_classe.gfx.scenes.flow import solid
from final_classe.gfx.ui import (
    draw_bar, draw_cursor, draw_text, draw_window, is_confirm, nav, theme, vertical_gradient,
)

FALLBACK_MUSIC = (
    "title", "prologue", "world_map", "battle", "boss", "final_boss", "victory", "victory_loop",
    "shop", "ending", "game_over",
)
FALLBACK_SFX = (
    "cursor", "confirm", "cancel", "error", "menu_open", "text_blip", "save", "buy", "transition",
    "slash", "slash_heavy", "staff_hit", "impact", "punch", "dagger", "katana_draw", "wind_slash",
    "arrow", "arrow_power", "shuriken", "claw", "crit", "cast", "charge", "charge_big", "fire",
    "fire_pillar", "ice_form", "ice_shatter", "thunder", "thunder_big", "heal", "chakra",
    "armor_break", "coins", "summon", "roar", "explosion", "mega_flare", "potion", "elixir",
    "revive", "defend", "ko_monster", "ko_hero", "level_up", "supernova", "needles", "poison_gas",
    "flame_breath",
)
MUSIC_NAMES = {
    "title": "Titre (création, recrutement)", "prologue": "Nibelheim", "world_map": "Carte du monde",
    "battle": "Combat", "boss": "Boss", "final_boss": "Sephiroth", "victory": "Victoire (jingle)",
    "victory_loop": "Butin", "shop": "Boutique", "ending": "Fin", "game_over": "Game over",
}
PANELS = ("Musiques", "Bruitages", "Volumes")
ROW_H = 34
VISIBLE = 13


class JukeboxScene(Scene):
    """Trois panneaux : musiques, bruitages, volumes. Tab ou gauche/droite pour changer de panneau."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        audio: Any = game.audio
        music_ids: tuple[str, ...] = tuple(getattr(audio, "MUSIC_IDS", ()))
        sfx_ids: tuple[str, ...] = tuple(getattr(audio, "SFX_IDS", ()))
        try:  # les listes sont des constantes du module audio
            from final_classe.gfx.audio import MUSIC_IDS, SFX_IDS

            music_ids, sfx_ids = music_ids or tuple(MUSIC_IDS), sfx_ids or tuple(SFX_IDS)
        except ImportError:
            pass
        self.music = music_ids or FALLBACK_MUSIC
        self.sfx = sfx_ids or FALLBACK_SFX
        self.muted = type(audio).__name__ == "NullAudio" or not getattr(audio, "available", True)
        self.panel = 0
        self.cursor = [0, 0, 0]
        self.scroll = [0, 0]
        self.playing: str | None = getattr(audio, "current_music", None)
        self.previous = self.playing
        self.last_sfx: str | None = None
        self.sfx_flash = 0.0
        self.time = 0.0
        self.script = DemoScript(game, [
            (0.8, lambda: self._key(pygame.K_RETURN)), (2.0, lambda: self._key(pygame.K_DOWN)),
            (2.6, lambda: self._key(pygame.K_RETURN)), (3.6, lambda: self._key(pygame.K_TAB)),
            (4.2, lambda: self._key(pygame.K_DOWN)), (4.6, lambda: self._key(pygame.K_RETURN)),
            (5.6, lambda: self._key(pygame.K_TAB)), (6.2, lambda: self._key(pygame.K_LEFT)),
        ]) if game.demo else None

    def _key(self, key: int) -> None:
        self.handle_event(key_event(key))

    @override
    def on_exit(self) -> None:
        """À la sortie, on rend la musique qui jouait avant."""
        audio = self.game.audio
        if self.previous and self.previous != self.playing:
            audio.play_music(self.previous)
        elif not self.previous:
            audio.stop_music()

    # --- actions ---------------------------------------------------------------------------
    def _items(self, panel: int) -> tuple[str, ...]:
        return self.music if panel == 0 else self.sfx

    def _play(self, panel: int, index: int) -> None:
        audio = self.game.audio
        name = self._items(panel)[index]
        if panel == 0:
            self.playing = name
            audio.play_music(name)
        else:
            self.last_sfx, self.sfx_flash = name, 0.4
            audio.play_sfx(name)

    def _stop(self) -> None:
        self.game.audio.stop_music()
        self.playing = None

    def _volume(self, row: int, delta: float) -> None:
        audio = self.game.audio
        attr = "music_volume" if row == 0 else "sfx_volume"
        value = round(max(0.0, min(1.0, getattr(audio, attr, 0.8) + delta)), 2)
        setattr(audio, attr, value)
        if row == 1:
            audio.play_sfx("cursor")

    def _move(self, dy: int) -> None:
        if self.panel == 2:
            self.cursor[2] = (self.cursor[2] + dy) % 2
            return
        n = len(self._items(self.panel))
        i = (self.cursor[self.panel] + dy) % n
        self.cursor[self.panel] = i
        s = self.scroll[self.panel]
        if i < s:
            s = i
        elif i >= s + VISIBLE:
            s = i - VISIBLE + 1
        self.scroll[self.panel] = max(0, min(n - VISIBLE, s))

    def _row_rect(self, panel: int, row: int) -> pygame.Rect:
        x = 40 if panel == 0 else 480
        return pygame.Rect(x + 14, 150 + row * ROW_H, 400, ROW_H)

    # --- évènements ------------------------------------------------------------------------
    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        audio = self.game.audio
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.panel = (self.panel + 1) % 3
            return
        if event.type == pygame.MOUSEWHEEL and self.panel < 2:
            n = len(self._items(self.panel))
            self.scroll[self.panel] = max(0, min(n - VISIBLE, self.scroll[self.panel] - event.y))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for panel in (0, 1):
                s = self.scroll[panel]
                for row in range(VISIBLE):
                    i = s + row
                    if i < len(self._items(panel)) and self._row_rect(panel, row).collidepoint(event.pos):
                        self.panel, self.cursor[panel] = panel, i
                        self._play(panel, i)
                        return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_BACKSPACE, pygame.K_x):
            self._stop()
            return
        dx, dy = nav(event)
        if self.panel == 2:
            if dy:
                self._move(dy)
            elif dx:
                self._volume(self.cursor[2], 0.1 * dx)
            return
        if dy:
            self._move(dy)
            if self.panel == 0:
                audio.play_sfx("cursor")
        elif dx:
            self.panel = (self.panel + dx) % 3
        elif is_confirm(event):
            self._play(self.panel, self.cursor[self.panel])

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.sfx_flash = max(0.0, self.sfx_flash - dt)
        if self.script:
            self.script.update(dt)

    # --- dessin ----------------------------------------------------------------------------
    def _draw_list(self, surface: pygame.Surface, panel: int) -> None:
        x = 40 if panel == 0 else 480
        rect = pygame.Rect(x, 100, 430, 36 + VISIBLE * ROW_H + 24)
        draw_window(surface, rect)
        focus = self.panel == panel
        draw_text(surface, PANELS[panel], (x + 24, 110), 24, theme.GOLD if focus else theme.TEXT_DIM, bold=True)
        items = self._items(panel)
        s = self.scroll[panel]
        for row in range(VISIBLE):
            i = s + row
            if i >= len(items):
                break
            name = items[i]
            r = self._row_rect(panel, row)
            active = (panel == 0 and name == self.playing) or (
                panel == 1 and name == self.last_sfx and self.sfx_flash > 0)
            selected = focus and i == self.cursor[panel]
            if active:
                surface.blit(solid(r.size, (*theme.GOLD, 60)), r)
            color = theme.GOLD if selected else (theme.TEXT if not active else theme.GOLD)
            label = MUSIC_NAMES.get(name, name) if panel == 0 else name
            draw_text(surface, label, (r.x + 34, r.centery), 20, color, "midleft")
            if selected:
                draw_cursor(surface, self.game.assets, (r.x + 28, r.centery), self.time)
            if panel == 0 and active:
                self._draw_bars(surface, r.right - 40, r.bottom - 6)
        if len(items) > VISIBLE:  # ascenseur
            track = pygame.Rect(rect.right - 12, 140, 4, VISIBLE * ROW_H)
            pygame.draw.rect(surface, (30, 40, 90), track, border_radius=2)
            h = max(20, track.height * VISIBLE // len(items))
            y = track.y + (track.height - h) * s // max(1, len(items) - VISIBLE)
            pygame.draw.rect(surface, theme.INNER_LINE, (track.x, y, 4, h), border_radius=2)

    def _draw_bars(self, surface: pygame.Surface, x: int, base: int) -> None:
        """Petit égaliseur animé à côté de la piste en cours."""
        for k in range(4):
            h = 6 + int(12 * abs(math.sin(self.time * (5 + k * 1.7) + k)))
            pygame.draw.rect(surface, theme.GOLD, (x + k * 7, base - h, 4, h))

    def _draw_volumes(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(920, 100, 320, 200)
        draw_window(surface, rect)
        focus = self.panel == 2
        draw_text(surface, PANELS[2], (rect.x + 24, 110), 24, theme.GOLD if focus else theme.TEXT_DIM, bold=True)
        audio = self.game.audio
        for i, (label, attr) in enumerate((("Musique", "music_volume"), ("Bruitages", "sfx_volume"))):
            y = 160 + i * 60
            value = getattr(audio, attr, 0.8)
            sel = focus and self.cursor[2] == i
            draw_text(surface, label, (rect.x + 40, y), 20, theme.GOLD if sel else theme.TEXT)
            draw_bar(surface, (rect.x + 40, y + 28, 200, 12), value, theme.GOLD)
            draw_text(surface, f"{int(value * 100)}", (rect.x + 255, y + 24), 18, theme.TEXT_DIM)
            if sel:
                draw_cursor(surface, self.game.assets, (rect.x + 34, y + 12), self.time)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(vertical_gradient((1280, 720), (10, 16, 52), (28, 22, 70)), (0, 0))
        draw_text(surface, "Test son", (640, 50), 42, theme.GOLD, "center", bold=True, title=True)
        self._draw_list(surface, 0)
        self._draw_list(surface, 1)
        self._draw_volumes(surface)
        info = draw_window(surface, (920, 320, 320, 230))
        now = MUSIC_NAMES.get(self.playing or "", self.playing) if self.playing else "—"
        draw_text(surface, "En cours", (info.x + 24, info.y + 14), 20, theme.TEXT_DIM)
        draw_text(surface, now or "—", (info.x + 24, info.y + 44), 24, theme.GOLD)
        draw_text(surface, "Dernier bruitage", (info.x + 24, info.y + 100), 20, theme.TEXT_DIM)
        draw_text(surface, self.last_sfx or "—", (info.x + 24, info.y + 130), 24)
        if self.muted:
            draw_text(surface, "Audio indisponible : liste seule", (info.x + 24, info.y + 185), 18,
                      theme.HP_LOW)
        draw_text(surface, "Entrée : jouer   Retour arrière : arrêter la musique   Tab : panneau   "
                           "Gauche / droite : volume   Échap : retour", (640, 696), 16, theme.TEXT_DIM,
                  "center")


@register_scene("jukebox")
def make_jukebox(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène Test son."""
    return JukeboxScene(game)
