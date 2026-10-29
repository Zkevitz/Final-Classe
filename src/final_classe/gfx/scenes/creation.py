"""Création du héros : le nom (saisie au clavier), le job (sprite, stats, description), les points."""

from typing import override

import pygame

from final_classe.characters import JOBS, Hero, Party
from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes._demo import (
    JOB_TEXT, DemoScript, draw_backdrop, hero_image, key_event,
)
from final_classe.gfx.ui import (
    Banner, Menu, TextInput, draw_bar, draw_text, draw_window, is_confirm, nav, theme, wrap_text,
)

POINTS = 20      # les points à répartir (comme la version terminal)
BASE_STAT = 10   # la valeur de départ de chaque statistique
STATS = ("FOR", "MAG", "DÉF")  # la RÉS reçoit le reste


class CreationScene(Scene):
    """Trois étapes : `name`, `job`, `points`. Retour arrière/Échap : étape précédente."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.stage = "name"
        self.time = 0.0
        self.name_input = TextInput("Nom de votre héros :", rect=(340, 280, 600, 130), max_len=12)
        self.jobs = list(JOBS)
        self.menu = Menu([f"{j.JOB_NAME}" for j in self.jobs], (60, 120), width=320, row_h=60,
                         font_size=28)
        self.name = ""
        self.bonus = [0, 0, 0]
        self.row = 0
        self.banner: Banner | None = None
        self.script = DemoScript(game, self._demo_steps()) if game.demo else None

    def _demo_steps(self) -> list:
        steps: list = []
        t = 0.6
        for ch in "aldric":
            steps.append((t, lambda c=ch: self.handle_event(key_event(ord(c), c))))
            t += 0.15
        steps.append((t + 0.4, lambda: self.handle_event(key_event(pygame.K_RETURN))))
        t += 1.0
        for _ in range(2):
            t += 0.6
            steps.append((t, lambda: self.handle_event(key_event(pygame.K_DOWN))))
        steps.append((t + 1.2, lambda: self.handle_event(key_event(pygame.K_RETURN))))
        t += 2.2
        for _ in range(8):
            steps.append((t, lambda: self.handle_event(key_event(pygame.K_RIGHT))))
            t += 0.12
        steps.append((t, lambda: self.handle_event(key_event(pygame.K_DOWN))))
        for _ in range(5):
            t += 0.12
            steps.append((t, lambda: self.handle_event(key_event(pygame.K_RIGHT))))
        steps.append((t + 0.8, lambda: self.handle_event(key_event(pygame.K_RETURN))))
        return steps

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("title")

    @property
    def remaining(self) -> int:
        """Points encore à répartir."""
        return POINTS - sum(self.bonus)

    @property
    def job(self) -> type[Hero]:
        """Le job sous le curseur."""
        return self.jobs[self.menu.cursor]

    @override
    def on_back(self) -> None:
        audio = self.game.audio
        audio.play_sfx("cancel")
        if self.stage == "points":
            self.stage = "job"
        elif self.stage == "job":
            self.stage = "name"
            self.name_input.submitted = False
        elif "title" in SCENES:
            self.game.replace(SCENES["title"](self.game, []))

    # --- évènements ---------------------------------------------------------------------
    def _handle_name(self, event: pygame.event.Event) -> None:
        self.name_input.handle_event(event)
        if self.name_input.submitted:
            self.name_input.submitted = False
            self.name = self.name_input.value.strip().title()
            self.game.audio.play_sfx("confirm")
            self.stage = "job"

    def _handle_job(self, event: pygame.event.Event) -> None:
        before = self.menu.cursor
        chosen = self.menu.handle_event(event)
        if self.menu.cursor != before:
            self.game.audio.play_sfx("cursor")
        if chosen is not None:
            self.game.audio.play_sfx("confirm")
            self.stage = "points"
            self.bonus = [0, 0, 0]
            self.row = 0

    def _handle_points(self, event: pygame.event.Event) -> None:
        dx, dy = nav(event)
        audio = self.game.audio
        if dy:
            self.row = (self.row + dy) % 4
            audio.play_sfx("cursor")
        elif dx and self.row < 3:
            value = self.bonus[self.row] + dx
            if 0 <= value and self.remaining - dx >= 0 and value <= POINTS:
                self.bonus[self.row] = value
                audio.play_sfx("cursor")
            else:
                audio.play_sfx("error")
        elif is_confirm(event):
            self._finish()

    def _finish(self) -> None:
        res = self.remaining
        stats = [BASE_STAT + b for b in self.bonus] + [BASE_STAT + res]
        hero = self.job(self.name, strength=stats[0], magic=stats[1], defense=stats[2],
                        resistance=stats[3])
        self.game.audio.play_sfx("confirm")
        self.game.party = Party([hero])
        self.game.zone = self.game.wave = 0
        target = "recruit" if "recruit" in SCENES else "world_map"
        if target in SCENES:
            self.game.replace(SCENES[target](self.game, []))
        else:
            self.banner = Banner("La suite arrive bientôt", seconds=1.6, y=300, size=34)

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.game.transitioning:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE and self.stage != "name":
            self.on_back()
        elif self.stage == "name":
            self._handle_name(event)
        elif self.stage == "job":
            self._handle_job(event)
        else:
            self._handle_points(event)

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        if self.script:
            self.script.update(dt)
        self.name_input.update(dt)
        self.menu.update(dt)
        if self.banner and not self.banner.update(dt):
            self.banner = None

    # --- dessin ---------------------------------------------------------------------------
    def _draw_job_panel(self, surface: pygame.Surface) -> None:
        job = self.job
        panel = pygame.Rect(400, 120, 820, 500)
        draw_window(surface, panel)
        assets = self.game.assets
        image = hero_image(job)
        # le sprite regarde à gauche : vers le menu
        assets.draw_sprite(surface, image, (panel.x + 190, panel.bottom - 50), 1.25)
        x = panel.x + 380
        draw_text(surface, job.JOB_NAME, (x, panel.y + 24), 36, theme.GOLD, bold=True, title=True)
        rows = (("PV", job.BASE_HP, 900, theme.HP), ("PM", job.BASE_MP, 100, theme.MP),
                ("VIT", job.SPEED, 20, theme.ATB))
        for i, (label, value, top, color) in enumerate(rows):
            y = panel.y + 90 + i * 40
            draw_text(surface, label, (x, y), 24, theme.TEXT_DIM)
            draw_bar(surface, (x + 70, y + 6, 220, 16), value / top, color)
            draw_text(surface, str(value), (x + 310, y), 24)
        y = panel.y + 225
        draw_text(surface, f"Compétence : {job.SKILL_NAME}", (x, y), 26, theme.GOLD)
        draw_text(surface, f"Coût : {job.SKILL_COST} PM", (x, y + 34), 22, theme.TEXT_DIM)
        for i, line in enumerate(wrap_text(JOB_TEXT.get(job.__name__, ""), 22, panel.right - x - 30)):
            draw_text(surface, line, (x, y + 80 + i * 30), 22)

    def _draw_points(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(300, 130, 680, 460)
        draw_window(surface, panel)
        self.game.assets.draw_sprite(surface, hero_image(self.job), (panel.x + 130, panel.bottom - 40), 1.0)
        draw_text(surface, f"{self.name}  —  {self.job.JOB_NAME}", (panel.x + 260, panel.y + 24), 30,
                  theme.GOLD, bold=True)
        draw_text(surface, f"Chaque stat vaut {BASE_STAT}. Répartissez {POINTS} points.",
                  (panel.x + 260, panel.y + 70), 20, theme.TEXT_DIM)
        values = [BASE_STAT + b for b in self.bonus] + [BASE_STAT + self.remaining]
        labels = (*STATS, "RÉS")
        for i, label in enumerate(labels):
            y = panel.y + 120 + i * 62
            sel = i == self.row
            color = theme.GOLD if sel else theme.TEXT
            draw_text(surface, label, (panel.x + 270, y), 28, color)
            draw_bar(surface, (panel.x + 350, y + 8, 200, 16), values[i] / (BASE_STAT + POINTS), theme.MP)
            suffix = f"  (+{self.bonus[i]})" if i < 3 else "  (le reste)"
            draw_text(surface, f"{values[i]}{suffix}", (panel.x + 570, y), 26, color)
            if sel and i < 3:
                draw_text(surface, "◄  ►", (panel.x + 270, y + 30), 16, theme.TEXT_DIM)
        draw_text(surface, f"Points restants : {self.remaining}", (panel.x + 270, panel.y + 380), 26,
                  theme.GOLD if self.remaining else theme.TEXT_DIM)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        draw_backdrop(surface, self.game, 140)
        titles = {"name": "Création du héros", "job": f"Choisissez le job de {self.name}",
                  "points": "Répartition des points"}
        draw_text(surface, titles[self.stage], (640, 60), 40, theme.GOLD, "center", bold=True, title=True)
        hint = "Entrée : valider   Échap : retour"
        if self.stage == "name":
            self.name_input.draw(surface)
            draw_text(surface, "Les accents sont acceptés (12 lettres au plus).", (640, 440), 20,
                      theme.TEXT_DIM, "center")
        elif self.stage == "job":
            self.menu.draw(surface, self.game.assets)
            self._draw_job_panel(surface)
            hint = "Haut / bas : choisir   Entrée : valider   Retour arrière : changer de nom"
        else:
            self._draw_points(surface)
            hint = "Haut / bas : statistique   Gauche / droite : ajuster   Entrée : valider"
        draw_text(surface, hint, (640, 696), 16, theme.TEXT_DIM, "center")
        if self.banner:
            self.banner.draw(surface)


@register_scene("creation")
def make_creation(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène de création."""
    return CreationScene(game)
