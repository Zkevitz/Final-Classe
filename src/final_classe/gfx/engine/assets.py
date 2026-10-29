"""Chargement des images : manifeste, cache, placeholders, ancrage aux pieds."""

import colorsys
import json
import zlib
from typing import Any

import pygame
from pygame import Vector2

from final_classe.gfx.engine.paths import IMG_DIR, MANIFEST
from final_classe.gfx.ui.draw import render_text, vertical_gradient
from final_classe.gfx.ui.fonts import get_font


class Assets:
    """Images du jeu par id du manifeste ; une image absente donne un placeholder, jamais d'erreur."""

    def __init__(self) -> None:
        self.manifest: dict[str, dict[str, Any]] = {}
        try:
            data = json.loads(MANIFEST.read_text(encoding="utf-8"))
            self.manifest = {entry["id"]: entry for entry in data.get("assets", [])}
        except (OSError, ValueError, KeyError):
            pass
        self._images: dict[str, pygame.Surface] = {}
        self._real: dict[str, bool] = {}
        self._scaled: dict[tuple, pygame.Surface] = {}
        self._feet: dict[str, pygame.Rect] = {}
        self._boxes: dict[tuple[str, str], pygame.Rect] = {}
        self._sheets: dict[str, dict[str, tuple[pygame.Surface, Vector2]]] = {}

    # --- infos du manifeste -------------------------------------------------
    def info(self, asset_id: str) -> dict[str, Any]:
        """L'entrée du manifeste ({} si l'id est inconnu)."""
        return self.manifest.get(asset_id, {})

    def is_floating(self, asset_id: str) -> bool:
        """Créature volante : le jeu la fait léviter."""
        return bool(self.info(asset_id).get("floating", False))

    def facing(self, asset_id: str) -> str:
        """« left » (héros) ou « right » (monstres)."""
        return self.info(asset_id).get("facing", "right")

    def exists(self, asset_id: str) -> bool:
        """Vrai si le vrai fichier est présent et lisible (pas le placeholder)."""
        self.image(asset_id)
        return self._real.get(asset_id, False)

    # --- images -------------------------------------------------------------
    def image(self, asset_id: str) -> pygame.Surface:
        """L'image (chargée une seule fois) ou son placeholder."""
        img = self._images.get(asset_id)
        if img is not None:
            return img
        path = IMG_DIR / f"{asset_id}.png"
        img = None
        if path.is_file():
            try:
                loaded = pygame.image.load(str(path))
                img = loaded.convert_alpha() if pygame.display.get_surface() else loaded
            except (pygame.error, OSError):
                img = None
        self._real[asset_id] = img is not None
        if img is None:
            img = self._placeholder(asset_id)
        self._images[asset_id] = img
        return img

    def _cache_get(self, key: tuple) -> pygame.Surface | None:
        """Lecture du cache redimensionné ; une entrée lue redevient la plus récente (LRU)."""
        surf = self._scaled.pop(key, None)
        if surf is not None:
            self._scaled[key] = surf
        return surf

    def _cache_put(self, key: tuple, surf: pygame.Surface) -> None:
        """Ajoute au cache ; au-delà de 300 entrées, évince les 60 plus anciennes (pas tout)."""
        if len(self._scaled) >= 300:
            for old in list(self._scaled)[:60]:
                del self._scaled[old]
        self._scaled[key] = surf

    def scaled(self, asset_id: str, size: tuple[int, int], flip: bool = False) -> pygame.Surface:
        """L'image redimensionnée (cache) ; `flip` la retourne horizontalement."""
        size = (max(1, int(size[0])), max(1, int(size[1])))
        key = (asset_id, size, flip)
        surf = self._cache_get(key)
        if surf is None:
            base = self.image(asset_id)
            surf = pygame.transform.smoothscale(base, size) if size != base.get_size() else base
            if flip:
                surf = pygame.transform.flip(surf, True, False)
            self._cache_put(key, surf)
        return surf

    def scaled_factor(self, asset_id: str, factor: float, flip: bool = False) -> pygame.Surface:
        """L'image multipliée par `factor`."""
        w, h = self.image(asset_id).get_size()
        return self.scaled(asset_id, (w * factor, h * factor), flip)

    def feet_rect(self, asset_id: str) -> pygame.Rect:
        """Boîte réelle du sujet (sans la marge transparente), calculée une fois."""
        rect = self._feet.get(asset_id)
        if rect is None:
            rect = self.image(asset_id).get_bounding_rect()
            if rect.width == 0 or rect.height == 0:
                rect = self.image(asset_id).get_rect()
            self._feet[asset_id] = rect
        return rect

    # --- poses (planches) ---------------------------------------------------
    def _sheet(self, asset_id: str) -> dict[str, tuple[pygame.Surface, Vector2]]:
        """Les poses de `assets/img/<id>/` ({} sans planche) : surface et ancre (pieds), en cache."""
        sheet = self._sheets.get(asset_id)
        if sheet is not None:
            return sheet
        sheet = {}
        folder = IMG_DIR / asset_id
        try:
            data = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
            for pose, entry in data.get("frames", {}).items():
                try:
                    img = pygame.image.load(str(folder / entry["file"]))
                    img = img.convert_alpha() if pygame.display.get_surface() else img
                    ax, ay = entry["anchor"]
                    sheet[pose] = (img, Vector2(float(ax), float(ay)))
                except (pygame.error, OSError, KeyError, ValueError, TypeError):
                    continue
        except (OSError, ValueError, AttributeError):
            sheet = {}
        self._sheets[asset_id] = sheet
        return sheet

    def has_sheet(self, asset_id: str) -> bool:
        """Vrai si une planche de poses exploitable existe (au moins `idle`)."""
        return "idle" in self._sheet(asset_id)

    def frame(self, asset_id: str, pose: str) -> pygame.Surface:
        """L'image d'une pose ; repli : `idle` de la planche, sinon le sprite simple."""
        sheet = self._sheet(asset_id)
        entry = sheet.get(pose) or sheet.get("idle")
        return entry[0] if entry else self.image(asset_id)

    def frame_anchor(self, asset_id: str, pose: str) -> Vector2:
        """Le point des pieds d'une pose (dans l'image de la pose) ; repli : `feet_rect`."""
        sheet = self._sheet(asset_id)
        entry = sheet.get(pose) or sheet.get("idle")
        if entry:
            return Vector2(entry[1])
        box = self.feet_rect(asset_id)
        return Vector2(box.centerx, box.bottom)

    def frame_box(self, asset_id: str, pose: str) -> pygame.Rect:
        """Boîte opaque d'une pose, relative aux pieds (ancre = origine) ; repli : `feet_rect`."""
        key = (asset_id, pose)
        box = self._boxes.get(key)
        if box is None:
            anchor = self.frame_anchor(asset_id, pose)
            if self.has_sheet(asset_id):
                rect = self.frame(asset_id, pose).get_bounding_rect()
            else:
                rect = self.feet_rect(asset_id)
                if pose == "ko":  # sans planche, le K.O. est un sprite aplati à 60 %
                    rect = pygame.Rect(rect.x, rect.bottom - int(rect.height * 0.6), rect.width, int(rect.height * 0.6))
            box = pygame.Rect(round(rect.x - anchor.x), round(rect.y - anchor.y), rect.width, rect.height)
            self._boxes[key] = box
        return box.copy()

    def scaled_frame(self, asset_id: str, pose: str, size: tuple[int, int]) -> pygame.Surface:
        """L'image d'une pose redimensionnée (cache)."""
        size = (max(1, int(size[0])), max(1, int(size[1])))
        key = (asset_id, pose, size)
        surf = self._cache_get(key)
        if surf is None:
            base = self.frame(asset_id, pose)
            surf = pygame.transform.smoothscale(base, size) if size != base.get_size() else base
            self._cache_put(key, surf)
        return surf

    def draw_sprite(
        self,
        surface: pygame.Surface,
        asset_id: str,
        feet: tuple[float, float],
        scale: float = 1.0,
        flip: bool = False,
        alpha: int = 255,
        scale_y: float | None = None,
    ) -> pygame.Rect:
        """Dessine un sprite dont les pieds réels (bas du sujet, centré) sont en `feet`.

        `scale_y` permet l'étirement de respiration (±2 %). Renvoie le rect dessiné.
        """
        img = self.image(asset_id)
        box = self.feet_rect(asset_id)
        sy = scale if scale_y is None else scale_y
        w, h = img.get_size()
        surf = self.scaled(asset_id, (w * scale, h * sy), flip)
        cx = (box.centerx if not flip else w - box.centerx) * scale
        bottom = box.bottom * sy
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        rect = surf.get_rect(topleft=(round(feet[0] - cx), round(feet[1] - bottom)))
        surface.blit(surf, rect)
        return rect

    def text(self, text: str, size: int = 24, color=(255, 255, 255), **kwargs: Any) -> pygame.Surface:
        """Texte rendu (ombre portée) mis en cache."""
        return render_text(text, size, color, **kwargs)

    # --- placeholders -------------------------------------------------------
    def _placeholder(self, asset_id: str) -> pygame.Surface:
        info = self.info(asset_id)
        kind = info.get("kind", "icon")
        seed = zlib.crc32(asset_id.encode())
        hue = (seed % 360) / 360
        base = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.75))
        dark = tuple(int(c * 0.45) for c in base)
        if kind == "background":
            size = tuple(info.get("size", (1280, 720)))
            surf = vertical_gradient(size, base, dark).copy()
            for x in range(0, size[0], 80):
                pygame.draw.line(surf, dark, (x, 0), (x, size[1]))
            for y in range(0, size[1], 80):
                pygame.draw.line(surf, dark, (0, y), (size[0], y))
            label = render_text(asset_id, 36)
            surf.blit(label, label.get_rect(center=(size[0] // 2, size[1] // 2)))
            return surf.convert() if pygame.display.get_surface() else surf
        if kind == "sprite":
            h = int(info.get("height", 200))
            w = int(h * (0.8 if asset_id.startswith("summon") else 0.6))
            surf = pygame.Surface((w + 20, h + 10), pygame.SRCALPHA)
            ox = 10
            body = pygame.Rect(ox + w // 6, h // 4, w * 2 // 3, h * 3 // 4)
            pygame.draw.ellipse(surf, base, pygame.Rect(ox + w // 3, 4, w // 3, h // 4))
            pygame.draw.rect(surf, base, body, border_radius=w // 5)
            pygame.draw.rect(surf, dark, body, 3, border_radius=w // 5)
            label = get_font(max(12, min(18, w // 7))).render(asset_id, True, (255, 255, 255))
            surf.blit(label, label.get_rect(center=(surf.get_width() // 2, h // 2)))
            return surf.convert_alpha() if pygame.display.get_surface() else surf
        size = int(info.get("size", 96))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, base, (2, 2, size - 4, size - 4), border_radius=size // 5)
        pygame.draw.rect(surf, dark, (2, 2, size - 4, size - 4), 3, border_radius=size // 5)
        label = get_font(max(10, size // 7)).render(asset_id.replace("_", " ", 1).split()[-1], True, (255, 255, 255))
        surf.blit(label, label.get_rect(center=(size // 2, size // 2)))
        return surf.convert_alpha() if pygame.display.get_surface() else surf
