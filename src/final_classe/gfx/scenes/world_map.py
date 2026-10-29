"""Carte du monde : cinq zones reliées par un chemin, curseur, menu (préparation, boutique, sauvegarde)."""

import math
from typing import override

import pygame

from final_classe.game.zones import ZONES
from final_classe.gfx.engine import Game, Scene, make_demo_party, register_scene
from final_classe.gfx.engine.registry import SCENES
from final_classe.gfx.scenes import flow
from final_classe.gfx.scenes._demo import hero_image
from final_classe.gfx.ui import Banner, Menu, draw_text, draw_window, is_cancel, theme
from final_classe.gfx.ui.gauges import draw_bar

# Position des zones sur bg_world_map (1280x720) : désert au sud-ouest, forêt au centre,
# grotte dans les montagnes, temple sur l'île à l'est, cratère au nord.
NODES = [(267, 507), (560, 267), (847, 300), (1133, 307), (827, 62)]


class WorldMapScene(Scene):
    """Choisir la prochaine zone ; le menu donne accès à la préparation et à la sauvegarde (pas de boutique sur la carte : le terminal n'en a pas)."""

    def __init__(self, game: Game, cleared: bool = False) -> None:
        super().__init__(game)
        if game.party is None:
            game.party = make_demo_party()
        self.sel = min(game.zone, len(ZONES) - 1)
        self.time = 0.0
        self.focus = "map"
        self.menu = Menu(["Préparation", "Sauvegarder", "Retour au titre"], (40, 110),
                         width=300, row_h=44)
        self.banner: Banner | None = None
        self._demo_t = 0.0
        if cleared and game.zone > 0:
            name = ZONES[min(game.zone, len(ZONES)) - 1].name
            self.banner = Banner(f"{name} : traversée !", seconds=3.0, y=90, size=36)

    # --- état --------------------------------------------------------------------------
    def state(self, index: int) -> str:
        """« done », « open » ou « locked »."""
        if index < self.game.zone:
            return "done"
        return "open" if index == self.game.zone else "locked"

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("world_map")

    @override
    def on_resume(self) -> None:
        self.game.audio.play_music("world_map")

    @override
    def on_back(self) -> None:
        self._toggle_menu()

    def _toggle_menu(self) -> None:
        a = self.game.audio
        if self.focus == "map":
            self.focus = "menu"
            a.play_sfx("menu_open")
        else:
            self.focus = "map"
            a.play_sfx("cancel")

    def _say(self, text: str, color=theme.GOLD) -> None:
        self.banner = Banner(text, color=color, seconds=1.8, y=90, size=32)

    # --- entrées -----------------------------------------------------------------------
    def _menu_choice(self, i: int) -> None:
        g, a = self.game, self.game.audio
        if i == 0 and "prepare" in SCENES:
            a.play_sfx("confirm")
            g.push(SCENES["prepare"](g, []), transition="fade")
        elif i == 1:
            ok = g.save()
            a.play_sfx("save" if ok else "error")
            self._say("Partie sauvegardée" if ok else "Sauvegarde impossible", theme.HP if ok else theme.HP_LOW)
            self.focus = "map"
        elif i == 2 and "title" in SCENES:
            g.replace_all(SCENES["title"](g, []))

    def _enter_zone(self) -> None:
        a = self.game.audio
        st = self.state(self.sel)
        if st == "open":
            a.play_sfx("confirm")
            flow.start_zone(self.game, self.sel)
        else:
            a.play_sfx("error")
            self._say("Zone déjà traversée" if st == "done" else "Zone verrouillée", theme.TEXT_DIM)

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        a = self.game.audio
        if self.focus == "menu":
            if is_cancel(event):
                self._toggle_menu()
                return
            before = self.menu.cursor
            chosen = self.menu.handle_event(event)
            if self.menu.cursor != before:
                a.play_sfx("cursor")
            if chosen is not None:
                self._menu_choice(chosen)
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE) \
                    and not self.menu.enabled[self.menu.cursor]:
                a.play_sfx("error")
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(ZONES)
                a.play_sfx("cursor")
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_q, pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(ZONES)
                a.play_sfx("cursor")
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
                self._enter_zone()
            elif event.key in (pygame.K_TAB, pygame.K_m) or is_cancel(event):
                self._toggle_menu()
        elif event.type == pygame.MOUSEMOTION:
            for i, p in enumerate(NODES):
                if math.dist(p, event.pos) < 30 and i != self.sel:
                    self.sel = i
                    a.play_sfx("cursor")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, p in enumerate(NODES):
                if math.dist(p, event.pos) < 30:
                    self.sel = i
                    self._enter_zone()

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.menu.update(dt)
        if self.banner and not self.banner.update(dt):
            self.banner = None
        if self.game.demo and not self.game.transitioning and self.focus == "map":
            self._demo_t += dt
            if self._demo_t > 2.0:  # la démo choisit la prochaine zone ouverte et y entre
                self._demo_t = -99.0
                self.sel = min(self.game.zone, len(ZONES) - 1)
                self._enter_zone()

    # --- dessin ------------------------------------------------------------------------
    def _draw_path(self, surface: pygame.Surface) -> None:
        for i in range(len(NODES) - 1):
            a, b = NODES[i], NODES[i + 1]
            open_ = i + 1 <= self.game.zone
            color = theme.GOLD if open_ else (150, 160, 190)
            length = math.dist(a, b)
            n = int(length // 16)
            for k in range(n):
                t = k / n
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                pygame.draw.circle(surface, (10, 14, 36), (p[0] + 1, p[1] + 2), 5)
                pygame.draw.circle(surface, color, p, 4 if open_ else 3)

    def _draw_node(self, surface: pygame.Surface, i: int) -> None:
        x, y = NODES[i]
        st = self.state(i)
        fill = {"done": (74, 222, 128), "open": theme.GOLD, "locked": (90, 98, 130)}[st]
        pulse = 1 + 0.12 * math.sin(self.time * 4) if st == "open" else 1
        r = int(24 * pulse)
        surface.blit(flow.glow_disc(56, fill, 22 if st != "locked" else 8), (x - 56, y - 56))
        pygame.draw.circle(surface, (10, 14, 36), (x, y + 2), r + 3)
        pygame.draw.circle(surface, fill, (x, y), r)
        pygame.draw.circle(surface, theme.WHITE, (x, y), r, 2)
        if st == "done":
            pygame.draw.lines(surface, (10, 40, 20), False, [(x - 9, y), (x - 2, y + 8), (x + 10, y - 8)], 4)
        elif st == "locked":
            pygame.draw.rect(surface, (30, 36, 64), (x - 8, y - 2, 16, 12), border_radius=2)
            pygame.draw.arc(surface, (30, 36, 64), (x - 6, y - 12, 12, 16), 0, math.pi, 3)
        else:
            draw_text(surface, str(i + 1), (x, y), 26, (40, 28, 6), "center", shadow=False, bold=True)
        if i == self.sel and self.focus == "map":
            ring = int(r + 10 + math.sin(self.time * 6) * 3)
            pygame.draw.circle(surface, theme.WHITE, (x, y), ring, 2)
            pts = [(x, y - ring - 4), (x - 10, y - ring - 20), (x + 10, y - ring - 20)]
            pygame.draw.polygon(surface, theme.GOLD, pts)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        flow.draw_backdrop(surface, assets, "bg_world_map")
        self._draw_path(surface)
        for i in range(len(NODES)):
            self._draw_node(surface, i)
        # le groupe se tient sur la prochaine zone
        spot = NODES[min(self.game.zone, len(NODES) - 1)]
        bob = abs(math.sin(self.time * 3)) * 6
        lead = self.game.party.leader
        assets.draw_sprite(surface, hero_image(lead), (spot[0] + 38, spot[1] - 26 - bob), 0.32, flip=True)
        # fenêtre de la zone choisie
        zone = ZONES[self.sel]
        label = {"done": "Terminée", "open": "Prochaine destination", "locked": "Verrouillée"}[self.state(self.sel)]
        color = {"done": theme.HP, "open": theme.GOLD, "locked": theme.TEXT_DIM}[self.state(self.sel)]
        draw_window(surface, (340, 606, 600, 74))
        draw_text(surface, zone.name, (640, 630), 30, theme.TEXT, "center", bold=True, title=True)
        draw_text(surface, label, (640, 660), 18, color, "center")
        # équipe
        party = self.game.party
        h = 40 + 46 * len(party.heroes)
        draw_window(surface, (960, 20, 290, h))
        for k, hero in enumerate(party.heroes):
            y = 20 + 22 + k * 46
            draw_text(surface, f"{hero.name}", (980, y), 22)
            draw_text(surface, f"{hero.title}  Niv. {hero.level}", (980, y + 22), 15, theme.TEXT_DIM)
            draw_bar(surface, pygame.Rect(1120, y + 6, 110, 10), hero.hp_ratio, theme.HP)
            draw_bar(surface, pygame.Rect(1120, y + 22, 110, 8), hero.mp / max(1, hero.max_mp), theme.MP)
        # bourse et aide
        draw_window(surface, (1000, 650, 250, 50))
        flow.draw_icon(surface, assets, "icon_gil", (1030, 675), 34)
        draw_text(surface, f"{party.gil} gils", (1230, 675), 24, theme.GOLD, "midright")
        draw_text(surface, "←/→ : zone   Entrée : partir   Échap : menu", (640, 704), 16, theme.TEXT, "center")
        if self.focus == "menu":
            self.menu.draw(surface, assets)
        if self.banner:
            self.banner.draw(surface)


@register_scene("world_map")
def make_world_map(game: Game, args: list[str]) -> Scene:
    """Fabrique de la carte du monde (`world_map:cleared` affiche la bannière de zone traversée)."""
    return WorldMapScene(game, cleared="cleared" in args)
