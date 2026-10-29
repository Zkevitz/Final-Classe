"""Le jeu : fenêtre, boucle, pile de scènes, partie courante et services."""

import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pygame

from final_classe.gfx.engine.assets import Assets
from final_classe.gfx.engine.paths import ROOT
from final_classe.gfx.engine.services import make_audio, make_fx
from final_classe.gfx.ui.theme import LOGICAL_SIZE

if TYPE_CHECKING:
    from final_classe.characters import Party
    from final_classe.gfx.engine.scene import Scene

MAX_DT = 1 / 30


class _Transition:
    """Fondu au noir autour d'un changement de pile : sortie, action, entrée."""

    def __init__(self, action: Callable[[], None], seconds: float) -> None:
        self.action = action
        self.half = max(0.01, seconds / 2)
        self.t = 0.0
        self.applied = False

    def apply(self) -> None:
        """Exécute le changement de pile (une seule fois)."""
        if not self.applied:
            self.applied = True
            self.action()

    @property
    def done(self) -> bool:
        return self.t >= self.half * 2

    @property
    def alpha(self) -> int:
        t = self.t / self.half
        return int(255 * (t if t < 1 else max(0.0, 2 - t)))


class Game:
    """Fenêtre 1280×720 (surface logique mise à l'échelle), pile de scènes et services."""

    def __init__(self, headless: bool = False, seed: int | None = None) -> None:
        self.headless = headless
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        if headless:  # les sauvegardes de test ne touchent jamais les vraies
            work = ROOT / "shots" / "headless"
            work.mkdir(parents=True, exist_ok=True)
            os.chdir(work)
        else:
            os.chdir(ROOT)
        if not headless:
            self._set_dpi_awareness()
        pygame.init()
        pygame.display.set_caption("Final Classe")
        self.size = LOGICAL_SIZE
        flags = pygame.RESIZABLE
        self.window = pygame.display.set_mode(self.size, flags)
        self.screen = pygame.Surface(self.size).convert()  # surface logique
        self.fullscreen = False
        self.clock = pygame.time.Clock()
        self.running = True
        self.time = 0.0
        self.seed = seed

        # services (créés après la fenêtre : convert_alpha en dépend)
        self.assets = Assets()
        self.audio: Any = make_audio()
        self.fx: Any = make_fx()

        # partie courante
        self.party: Party | None = None
        self.slot = 1
        self.zone = 0
        self.wave = 0

        # options du mode sans fenêtre (lues par les scènes de combat)
        self.demo = False
        self.force_action: str | None = None

        self.stack: list[Scene] = []
        self._transition: _Transition | None = None
        self._view = pygame.Rect(0, 0, *self.size)
        self._scale = 1.0

    # --- système ------------------------------------------------------------
    @staticmethod
    def _set_dpi_awareness() -> None:
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            pass

    def quit(self) -> None:
        """Demande l'arrêt de la boucle."""
        self.running = False

    def toggle_fullscreen(self) -> None:
        """F11 : plein écran bureau, ou retour à la fenêtre 1280×720."""
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.size, pygame.RESIZABLE)

    # --- pile de scènes -----------------------------------------------------
    @property
    def scene(self) -> "Scene | None":
        """La scène courante (le haut de la pile)."""
        return self.stack[-1] if self.stack else None

    def _schedule(self, action: Callable[[], None], transition: str | None) -> None:
        if self._transition is not None:
            self._transition.apply()  # on termine proprement le précédent changement
            self._transition = None
        if transition in (None, "none"):
            action()
        else:
            self._transition = _Transition(action, 0.5)

    def push(self, scene: "Scene", transition: str | None = None) -> None:
        """Empile une scène (la précédente reste dessous)."""

        def action() -> None:
            self.stack.append(scene)
            scene.on_enter()

        self._schedule(action, transition)

    def pop(self, transition: str | None = None) -> None:
        """Retire la scène courante ; la précédente reprend. Quitte le jeu si la pile est vide."""

        def action() -> None:
            if self.stack:
                self.stack.pop().on_exit()
            if self.stack:
                self.stack[-1].on_resume()
            else:
                self.quit()

        self._schedule(action, transition)

    def replace(self, scene: "Scene", transition: str | None = "fade") -> None:
        """Remplace la scène courante (fondu au noir par défaut)."""

        def action() -> None:
            if self.stack:
                self.stack.pop().on_exit()
            self.stack.append(scene)
            scene.on_enter()
            self._clear_fx()

        self._schedule(action, transition)

    def replace_all(self, scene: "Scene", transition: str | None = "fade") -> None:
        """Vide la pile puis installe `scene` (retour au titre, début de partie…)."""

        def action() -> None:
            while self.stack:
                self.stack.pop().on_exit()
            self.stack.append(scene)
            scene.on_enter()
            self._clear_fx()

        self._schedule(action, transition)

    def _clear_fx(self) -> None:
        clear = getattr(self.fx, "clear", None)
        if callable(clear):
            try:
                clear()
            except Exception:
                pass

    @property
    def transitioning(self) -> bool:
        """Un fondu est en cours (les entrées sont ignorées)."""
        return self._transition is not None

    # --- partie -------------------------------------------------------------
    def save(self) -> bool:
        """Sauvegarde la partie courante dans l'emplacement courant ; False si impossible."""
        if self.party is None:
            return False
        from final_classe.storage import save_game

        try:
            save_game(self.party, self.zone, self.wave, self.slot)
        except OSError:
            return False
        return True

    def load(self, slot: int) -> bool:
        """Charge un emplacement dans `party`, `zone`, `wave` ; False si illisible."""
        from final_classe.storage import SaveError, load_game

        try:
            self.party, self.zone, self.wave = load_game(slot)
        except SaveError:
            return False
        self.slot = slot
        return True

    # --- boucle -------------------------------------------------------------
    def _to_logical(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            x = (event.pos[0] - self._view.x) / self._scale
            y = (event.pos[1] - self._view.y) / self._scale
            try:
                event.pos = (int(x), int(y))
            except AttributeError:
                pass

    def mouse_pos(self) -> tuple[int, int]:
        """La position de la souris en coordonnées logiques."""
        x, y = pygame.mouse.get_pos()
        return (int((x - self._view.x) / self._scale), int((y - self._view.y) / self._scale))

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if self._transition is not None or self.scene is None:
                continue
            self._to_logical(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene.on_back()
            else:
                self.scene.handle_event(event)

    def update(self, dt: float) -> None:
        """Avance les services, la transition et la scène courante."""
        self.time += dt
        update_audio = getattr(self.audio, "update", None)
        if callable(update_audio):
            try:
                update_audio(dt)
            except Exception:
                self._service_failed("audio")
        try:
            self.fx.update(dt)
        except Exception:
            self._service_failed("fx")
        tr = self._transition
        if tr is not None:
            tr.t += dt
            if not tr.applied and tr.t >= tr.half:
                tr.apply()
            if tr.done:
                self._transition = None
        if self.scene is not None:
            self.scene.update(dt)

    def _service_failed(self, name: str) -> None:
        """Un service plante : on le remplace par sa version minimale (le jeu continue)."""
        print(f"[{name}] erreur, repli sur le service minimal :", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        from final_classe.gfx.engine.services import FallbackFxManager, NullAudio

        if name == "audio":
            self.audio = NullAudio()
        else:
            old = list(getattr(self.fx, "effects", []))
            self.fx = FallbackFxManager()
            self.fx.abandon(old)

    def draw(self) -> None:
        """Dessine les scènes, le calque `overlay` des effets et le fondu."""
        surface = self.screen
        surface.fill((0, 0, 0))
        start = len(self.stack) - 1
        while start > 0 and self.stack[start].transparent:
            start -= 1
        for scene in self.stack[max(0, start):]:
            scene.draw(surface)
        try:
            self.fx.draw(surface, "overlay")
        except Exception:
            self._service_failed("fx")
        if self._transition is not None and self._transition.alpha > 0:
            veil = pygame.Surface(self.size)
            veil.set_alpha(self._transition.alpha)
            surface.blit(veil, (0, 0))

    def present(self) -> None:
        """Met la surface logique à l'échelle de la fenêtre (bandes noires si ratio différent)."""
        win = pygame.display.get_surface()
        if win is None:
            return
        ww, wh = win.get_size()
        scale = min(ww / self.size[0], wh / self.size[1])
        w, h = int(self.size[0] * scale), int(self.size[1] * scale)
        self._view = pygame.Rect((ww - w) // 2, (wh - h) // 2, w, h)
        self._scale = scale
        if (w, h) == self.size and (ww, wh) == self.size:
            win.blit(self.screen, (0, 0))
        else:
            win.fill((0, 0, 0))
            win.blit(pygame.transform.smoothscale(self.screen, (w, h)), self._view.topleft)
        pygame.display.flip()

    def step(self, dt: float, render: bool = True) -> None:
        """Une image : évènements, mise à jour, dessin, présentation."""
        self._handle_events()
        self.update(dt)
        if render:
            self.draw()
            self.present()

    def run(self) -> None:
        """Boucle principale (dt plafonné à 1/30 s)."""
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, MAX_DT)
            self.step(dt)
        pygame.quit()

    def screenshot(self, path: str | Path, scale: float = 0.5) -> None:
        """Enregistre la surface logique en PNG (640×360 avec l'échelle 0,5)."""
        surf = self.screen
        if scale != 1.0:
            surf = pygame.transform.smoothscale(
                surf, (int(self.size[0] * scale), int(self.size[1] * scale))
            )
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(path))
