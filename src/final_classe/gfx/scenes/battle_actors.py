"""Combattants à l'écran (protocole `Actor` des chorégraphies), décors et placement."""

import functools
import math
import re

import pygame
from pygame import Vector2

from final_classe.gfx.scenes._demo import hero_image

ZONE_KEYS = ("plains", "forest", "cave", "chaos", "crater")
ZONE_BG = ("bg_plains", "bg_forest", "bg_cave", "bg_chaos", "bg_crater")

_shadow_cache: dict[int, pygame.Surface] = {}
_tint_cache: dict[tuple, pygame.Surface] = {}
_anchored_cache: dict[tuple, pygame.Surface] = {}
POSE_FADE = 0.07  # durée du fondu enchaîné entre deux poses (s)


def snake(name: str) -> str:
    """`BlackMage` -> `black_mage`."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def job_key(hero: object) -> str:
    """La clé de job d'un héros (`soldier`, `black_mage`…), pour les clés de chorégraphie."""
    return snake(type(hero).__name__)


def monster_image(assets, monster: object) -> str:
    """L'id d'image d'un monstre : sa classe, ou la classe dont il est une variante."""
    first = ""
    for cls in type(monster).__mro__:
        sid = f"mon_{snake(cls.__name__)}"
        first = first or sid
        if sid in assets.manifest:
            return sid
    return first


def hero_positions(n: int, widths: list[float] | None = None) -> list[Vector2]:
    """Les pieds des héros : diagonale FF à droite, du fond (en haut) vers l'avant (en bas).

    Le pas horizontal entre deux voisins garantit un chevauchement d'au plus 1/3 du plus étroit
    (les sprites sont hauts : l'étagement vertical ne les sépare pas).
    """
    if n <= 0:
        return []
    ws = list(widths) if widths else [130.0] * n
    step_y = 66 if n <= 3 else 54
    xs = [0.0] * n
    xs[-1] = 1215 - ws[-1] / 2
    for i in range(n - 2, -1, -1):
        xs[i] = xs[i + 1] - ((ws[i] + ws[i + 1]) / 2 - min(ws[i], ws[i + 1]) / 3)
    return [Vector2(xs[i], 385 + i * step_y) for i in range(n)]


def _union_area(rects: list[pygame.Rect]) -> int:
    """Aire de l'union de rectangles (compression de coordonnées)."""
    rects = [r for r in rects if r.width > 0 and r.height > 0]
    if not rects:
        return 0
    xs = sorted({v for r in rects for v in (r.left, r.right)})
    area = 0
    for x0, x1 in zip(xs, xs[1:]):
        spans = sorted((r.top, r.bottom) for r in rects if r.left <= x0 and r.right >= x1)
        cur_end, covered = None, 0
        start = 0
        for t, bt in spans:
            if cur_end is None or t > cur_end:
                if cur_end is not None:
                    covered += cur_end - start
                start, cur_end = t, bt
            else:
                cur_end = max(cur_end, bt)
        if cur_end is not None:
            covered += cur_end - start
        area += covered * (x1 - x0)
    return area


def occlusion_rates(boxes: list[pygame.Rect]) -> list[float]:
    """Part de chaque boîte cachée par celles dessinées après elle (`boxes` du fond vers l'avant)."""
    out = []
    for i, box in enumerate(boxes):
        if box.width <= 0 or box.height <= 0:
            out.append(0.0)
            continue
        front = [box.clip(o) for o in boxes[i + 1:]]
        out.append(_union_area(front) / (box.width * box.height))
    return out


MAX_HIDDEN = 1 / 3  # part maximale d'un combattant cachée par ceux qui sont devant lui
FORMATION_LEFT = 540  # les héros ne dépassent pas cette limite à gauche (monstres)
FORMATION_RIGHT = 1268
FORMATION_FEET_MAX = 545  # pieds du plus avancé : au-dessus de la fenêtre de commandes


def hero_formation(poses: list[list[pygame.Rect]]) -> list[Vector2]:
    """Mémoïsé : le résultat ne dépend que des boîtes de poses (donc des sprites)."""
    key = tuple(tuple(tuple(r) for r in boxes) for boxes in poses)
    return [Vector2(v) for v in _formation_cached(key)]


@functools.lru_cache(maxsize=64)
def _formation_cached(key: tuple) -> tuple[tuple[float, float], ...]:
    poses = [[pygame.Rect(*r) for r in boxes] for boxes in key]
    return tuple((v.x, v.y) for v in _hero_formation_search(poses))


def _hero_formation_search(poses: list[list[pygame.Rect]]) -> list[Vector2]:
    """Positions des pieds des héros ; `poses[i]` = boîtes (relatives aux pieds) des poses de repos et K.O.

    Fonction pure. Cherche l'ordre de profondeur (les petits devant), l'écart vertical et le pas
    horizontal les plus serrés pour lesquels chaque pose d'un héros est cachée à 1/3 au plus par
    l'union des poses de ceux de devant. Sans solution, garde la moins mauvaise.
    """
    import itertools

    n = len(poses)
    if n == 0:
        return []
    best: tuple | None = None
    y0 = 385 if n <= 3 else 372
    steps = [66, 74, 82, 90] if n <= 3 else [54, 60, 66, 72]
    for step_y in steps:
        if y0 + (n - 1) * step_y > FORMATION_FEET_MAX:
            continue
        for order in itertools.permutations(range(n)):  # order[k] = héros à la profondeur k (0 = fond)
            xs = [0.0] * n
            worst = 0.0
            front_boxes: list[pygame.Rect] = []  # boîtes (union des poses) de ceux de devant, en absolu
            for k in range(n - 1, -1, -1):
                h = order[k]
                y = y0 + k * step_y
                if k == n - 1:
                    x = FORMATION_RIGHT - max(r.right for r in poses[h])
                    rate = 0.0
                else:
                    def rate_at(x: float, h: int = h, y: int = y) -> float:
                        return max(
                            (_union_area([r.move(x, y).clip(f) for f in front_boxes]) / max(1, r.width * r.height))
                            for r in poses[h]
                        )

                    x = xs[order[k + 1]]
                    for _ in range(50):  # recherche grossière (16 px), puis affinage (4 px)
                        rate = rate_at(x)
                        if rate <= MAX_HIDDEN:
                            break
                        x -= 16
                    while rate <= MAX_HIDDEN and x < xs[order[k + 1]]:
                        better = rate_at(x + 4)
                        if better > MAX_HIDDEN:
                            break
                        x, rate = x + 4, better
                xs[h] = x
                worst = max(worst, rate)
                front_boxes.extend(r.move(x, y) for r in poses[h])
            left = min(xs[h] + min(r.left for r in poses[h]) for h in range(n))
            ok = worst <= MAX_HIDDEN and left >= FORMATION_LEFT
            span = -left
            moved = sum(1 for k, h in enumerate(order) if k != h)  # préfère l'ordre naturel
            score = (not ok, worst if not ok else 0.0, step_y, span, moved)
            if best is None or score < best[0]:
                best = (score, order, step_y, xs[:])
    if best is None:  # écran trop petit : repli sur le pas de base
        return hero_positions(n)
    _, order, step_y, xs = best
    pos = [Vector2() for _ in range(n)]
    for k, h in enumerate(order):
        pos[h] = Vector2(xs[h], y0 + k * step_y)
    return pos


def hero_width(assets, sprite: str) -> float:
    """Largeur d'encombrement d'un héros : la plus large de sa pose de repos et de sa pose K.O."""
    w = float(assets.feet_rect(sprite).width)
    if assets.has_sheet(sprite):
        for pose in ("idle", "ko"):
            w = max(w, assets.frame(sprite, pose).get_width() - 8.0)
    return w


def place_heroes(assets, heroes: list) -> None:
    """Place les héros (combat et victoire : mêmes positions)."""
    poses = [[assets.frame_box(a.sprite, "idle"), assets.frame_box(a.sprite, "ko")] for a in heroes]
    for a, pos in zip(heroes, hero_formation(poses), strict=True):
        a.home = Vector2(pos)
        a.update(0.0)


def monster_positions(widths: list[float]) -> list[Vector2]:
    """Les pieds des monstres, selon la largeur réelle des sprites : une rangée, sinon 2 colonnes."""
    n = len(widths)
    if n <= 1:
        return [Vector2(370, 510)] * n
    gap = min(44.0, (690 - sum(widths)) / (n - 1))
    total = sum(widths) + gap * (n - 1)
    if gap >= 14:  # tient en une rangée, sans recouvrement horizontal
        x = 365 - total / 2
        out = []
        for i, w in enumerate(widths):
            out.append(Vector2(x + w / 2, 480 if i % 2 == 0 else 535))
            x += w + gap
        return out
    cols = (list(range(0, n, 2)), list(range(1, n, 2)))
    centers = (370 - max(widths) * 0.55 - 20, 370 + max(widths) * 0.55 + 20)
    out = [Vector2() for _ in widths]
    for c, idxs in enumerate(cols):
        for r, i in enumerate(idxs):
            out[i] = Vector2(centers[c], 455 + r * 75 + c * 20)
    return out


def draw_background(game, surface: pygame.Surface, zone: int) -> None:
    """Le décor de la zone (placeholder si l'image manque)."""
    bg = game.assets.image(ZONE_BG[max(0, min(zone, len(ZONE_BG) - 1))])
    if bg.get_size() != surface.get_size():
        bg = pygame.transform.smoothscale(bg, surface.get_size())
    surface.blit(bg, (0, 0))


class BattleActor:
    """Un combattant : modèle, position, état d'affichage (PV qui glissent, flash, K.O.)."""

    def __init__(self, game, model, side: str, home: Vector2, phase: float = 0.0) -> None:
        self.game = game
        self.assets = game.assets
        self.model = model
        self.side = side  # "hero" ou "monster"
        self.sprite = hero_image(model) if side == "hero" else monster_image(game.assets, model)
        self.home = Vector2(home)
        self.offset = Vector2()
        self.scale = 1.0
        self.rotation = 0.0
        self.alpha = 255
        self.visible = True
        self.tint: tuple[int, int, int] | None = None
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.phase = phase
        self.t = 0.0
        self.lean = 0.0
        self.lean_target = 0.0
        self.floating = self.assets.is_floating(self.sprite)
        self.shown_hp = float(model.hp)
        self.target_hp = float(model.hp)
        self.shown_mp = float(model.mp)
        self.target_mp = float(model.mp)
        self.atb = 0.0
        self.ready_t: float | None = None
        self.ko = False  # pose K.O. persistante (héros)
        self.bar_timer = 0.0
        self.jump = 0.0  # saut de victoire
        self.ready_state = False  # la scène demande la pose `ready` (ATB pleine, menu ouvert)
        self.has_sheet = self.assets.has_sheet(self.sprite)
        self.pose = "idle"  # pose visée
        self._layers: list[list] = [["idle", 1.0]]  # [pose, opacité] : fondus empilés, la dernière est la pose visée
        self._hold: float | None = None  # temps avant le retour à la pose de base
        self._manual = False  # pose imposée de l'extérieur (chorégraphie) : pas de resynchronisation auto
        self._flash = (255, 255, 255)
        self._flash_t = 0.0
        self._flash_d = 0.12
        self.update(0.0)

    # --- protocole Actor ----------------------------------------------------
    @property
    def image(self) -> pygame.Surface:
        """La surface de la pose courante, à l'échelle affichée, ancre au milieu du bas (pour `AfterImage`)."""
        if not self.has_sheet:
            return self.assets.image(self.sprite)
        _, sc, sy = self._geometry()
        pose = self.pose
        w, h = self.assets.frame(self.sprite, pose).get_size()
        size = (max(1, int(w * sc)), max(1, int(h * sy)))
        key = (self.sprite, pose, size)
        out = _anchored_cache.get(key)
        if out is None:
            a = self.assets.frame_anchor(self.sprite, pose)
            src = self.assets.scaled_frame(self.sprite, pose, size)
            ax, ay = a.x * size[0] / w, a.y * size[1] / h
            half = int(max(ax, size[0] - ax)) + 1
            out = pygame.Surface((2 * half, max(1, int(ay) + 1)), pygame.SRCALPHA)
            out.blit(src, (half - round(ax), 0))
            if len(_anchored_cache) > 60:
                _anchored_cache.clear()
            _anchored_cache[key] = out
        return out

    def flash(self, color=(255, 255, 255), seconds: float = 0.12) -> None:
        """Flash coloré du sprite."""
        self._flash = tuple(color)
        self._flash_t = self._flash_d = max(0.02, seconds)

    # --- poses --------------------------------------------------------------
    def base_pose(self) -> str:
        """La pose de repos : `ko` si K.O., `ready` si la scène l'a demandé, sinon `idle`."""
        if self.ko:
            return "ko"
        return "ready" if self.ready_state and self.alive else "idle"

    @property
    def draw_front(self) -> bool:
        """Héros K.O. : dessiné après les autres, jamais caché par une pose large voisine (lisible, §8)."""
        return self.side == "hero" and (self.ko or self.pose == "ko")

    def _switch(self, pose: str, instant: bool = False) -> None:
        """Passe à `pose` avec un fondu enchaîné (ou d'un coup)."""
        if not self.has_sheet:
            self.pose = pose
            return
        if pose != self.pose:
            if instant:
                self._layers = [[pose, 1.0]]
            else:  # un fondu en cours est gelé tel quel : le nouveau part de l'état mélangé courant
                self._layers.append([pose, 0.0])
                if len(self._layers) > 6:  # retire la couche la moins visible (écart imperceptible)
                    n, weights = len(self._layers), []
                    for i in range(1, n - 1):
                        w = self._layers[i][1]
                        for later in self._layers[i + 1:]:
                            w *= 1.0 - later[1]
                        weights.append(w)
                    del self._layers[1 + weights.index(min(weights))]
            self.pose = pose

    def set_pose(self, pose: str, hold: float | None = None, instant: bool = False) -> None:
        """Change de pose (fondu ~70 ms) ; `hold` = durée avant le retour à la pose de base.

        `idle` signifie « pose de base » (ko si K.O.). Sans planche, ne fait rien de visible.
        """
        if pose == "idle":
            self._manual = False
            self._hold = None
            self._switch(self.base_pose(), instant)
            return
        self._manual = True
        self._hold = hold
        self._switch(pose, instant)

    # --- état ---------------------------------------------------------------
    @property
    def alive(self) -> bool:
        """Le modèle est debout."""
        return bool(self.model.is_alive)

    def sync(self, hp: bool = True, mp: bool = True) -> None:
        """Les jauges visent les vraies valeurs du modèle (au moment de l'impact)."""
        if hp:
            self.target_hp = float(self.model.hp)
            self.bar_timer = 2.5
            if self.model.is_alive and self.ko:
                self.ko = False  # relevé
                self.rotation, self.scale, self.tint = 0.0, 1.0, None
                self._manual = False
                self._hold = None
                self._switch(self.base_pose())
        if mp:
            self.target_mp = float(self.model.mp)

    def _glide(self, shown: float, target: float, dt: float) -> float:
        if abs(target - shown) < 0.6:
            return target
        return shown + (target - shown) * min(1.0, dt * 7.0)

    @property
    def _sheet_ko(self) -> bool:
        """Héros en pose `ko` dessinée : les gadgets du code (rotation, grisé, affaissement) sont inutiles."""
        return (self.has_sheet and self.side == "hero" and self.pose == "ko"
                and "ko" in self.assets._sheet(self.sprite))

    def _geometry(self) -> tuple[Vector2, float, float]:
        breath = 1.0 + round(0.02 * math.sin(self.t * 2.1 + self.phase), 2)  # quantifié : le cache d'images reste petit
        scale = 1.0 if self._sheet_ko else self.scale
        sy = scale * breath
        if self.ko and self.side == "hero" and not self.has_sheet:
            sy = scale * 0.6
        lev = 0.0
        if self.floating:
            lev = -18 + 7 * math.sin(self.t * 2.4 + self.phase)
        offset = Vector2() if self._sheet_ko else self.offset
        feet = self.home + offset + Vector2(-self.lean, lev - self.jump)
        return feet, scale, sy

    def update(self, dt: float) -> None:
        """Respiration, lévitation, glissement des jauges, rect à l'écran."""
        self.t += dt
        self.shown_hp = self._glide(self.shown_hp, self.target_hp, dt)
        self.shown_mp = self._glide(self.shown_mp, self.target_mp, dt)
        self._flash_t = max(0.0, self._flash_t - dt)
        self.bar_timer = max(0.0, self.bar_timer - dt)
        self.lean += (self.lean_target - self.lean) * min(1.0, dt * 12)
        top = self._layers[-1]
        if top[1] < 1.0:
            top[1] = min(1.0, top[1] + dt / POSE_FADE)
            if top[1] >= 1.0:
                self._layers = [top]
        if self._hold is not None:
            self._hold -= dt
            if self._hold <= 0:
                self._hold = None
                self._manual = False
        if self.has_sheet and not self._manual and self.pose != self.base_pose():
            self._switch(self.base_pose())
        feet, sx, sy = self._geometry()
        box = self.assets.feet_rect(self.sprite)
        r = pygame.Rect(0, 0, max(1, int(box.width * sx)), max(1, int(box.height * sy)))
        r.midbottom = (round(feet.x), round(feet.y))
        self.rect = r

    # --- dessin -------------------------------------------------------------
    def draw_shadow(self, surface: pygame.Surface) -> None:
        """Ellipse sombre au sol."""
        if not self.visible:
            return
        w = max(40, int(self.rect.width * 0.8))
        sh = _shadow_cache.get(w)
        if sh is None:
            sh = pygame.Surface((w, max(10, w // 5)), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
            _shadow_cache[w] = sh
        base = self.home + self.offset
        s = sh
        if self.alpha < 255:
            s = sh.copy()
            s.set_alpha(self.alpha)
        surface.blit(s, s.get_rect(center=(round(base.x - self.lean), round(base.y - 2))))

    def _pose_surface(self, feet: Vector2, sc: float, sy: float) -> tuple[pygame.Surface, pygame.Rect, bool]:
        """L'image de la pose (ou le fondu entre deux poses), son rect écran, et si elle est partagée (cache)."""
        a = self.assets

        def layer(pose: str) -> tuple[pygame.Surface, pygame.Rect]:
            w, h = a.frame(self.sprite, pose).get_size()
            anchor = a.frame_anchor(self.sprite, pose)
            surf = a.scaled_frame(self.sprite, pose, (w * sc, h * sy))
            sw, sh = surf.get_size()
            top = (round(feet.x - anchor.x * sw / w), round(feet.y - anchor.y * sh / h))
            return surf, surf.get_rect(topleft=top)

        if len(self._layers) == 1:
            surf, rect = layer(self._layers[0][0])
            return surf, rect, True
        parts = [(layer(pose), alpha) for pose, alpha in self._layers]
        union = parts[0][0][1].unionall([p[0][1] for p in parts[1:]])
        comp = pygame.Surface(union.size, pygame.SRCALPHA)
        for n, ((surf, r), alpha) in enumerate(parts):
            surf.set_alpha(255 if n == 0 else int(255 * alpha))
            comp.blit(surf, (r.x - union.x, r.y - union.y))
            surf.set_alpha(255)
        return comp, union, False

    def draw(self, surface: pygame.Surface) -> None:
        """Le sprite (pose courante), ancré sur ses pieds."""
        if not self.visible or self.alpha <= 0:
            return
        feet, sc, sy = self._geometry()
        sheet_ko = self._sheet_ko
        tint = None if sheet_ko else (self.tint or ((105, 105, 125) if (self.ko and self.side == "hero") else None))
        rotation = 0.0 if sheet_ko else self.rotation
        flashing = self._flash_t > 0
        if tint is None and not flashing and rotation == 0 and self.alpha >= 255:
            if self.has_sheet:
                surf, rect, _ = self._pose_surface(feet, sc, sy)
                surface.blit(surf, rect)
            else:
                self.assets.draw_sprite(surface, self.sprite, feet, sc, False, 255, sy)
            return
        if self.has_sheet:
            surf, rect, shared = self._pose_surface(feet, sc, sy)
        else:
            img = self.assets.image(self.sprite)
            box = self.assets.feet_rect(self.sprite)
            w, h = img.get_size()
            surf = self.assets.scaled(self.sprite, (w * sc, h * sy))
            shared = True  # `surf` appartient à un cache : copier avant de modifier
            rect = surf.get_rect(topleft=(round(feet.x - box.centerx * sc), round(feet.y - box.bottom * sy)))
        if tint is not None:
            key = (self.sprite, self.pose, surf.get_size(), tuple(tint))
            cached = _tint_cache.get(key) if shared else None
            if cached is None:
                cached = surf.copy()
                cached.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
                if shared:
                    if len(_tint_cache) > 40:
                        _tint_cache.clear()
                    _tint_cache[key] = cached
            surf = cached
        if flashing:
            surf = surf.copy()
            shared = False
            k = self._flash_t / self._flash_d
            add = tuple(int(c * k) for c in self._flash)
            surf.fill((*add, 0), special_flags=pygame.BLEND_RGB_ADD)
        if rotation:
            surf = pygame.transform.rotozoom(surf, rotation, 1.0)
            rect = surf.get_rect(center=rect.center)
        if self.alpha < 255:
            if shared and not rotation:
                surf = surf.copy()
            surf.set_alpha(self.alpha)
        surface.blit(surf, rect)
