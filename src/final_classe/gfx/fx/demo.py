"""Démo des effets et chorégraphies sur des acteurs factices (sans `engine/`).

    uv run python -m final_classe.gfx.fx.demo --headless [--only <clé ou préfixe>]
        [--shots shots/fx] [--shot-every 0.25] [--shot-scale 0.5] [--seconds 8]

Sans `--headless`, ouvre une fenêtre et joue les chorégraphies en temps réel.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

W, H = 1280, 720
HEAL_KEYS = ("spell.cure", "skill.monk", "item.", "state.level_up", "state.ko_hero", "action.")
MONSTER_KEYS = ("attack.monster", "monster.")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--headless", action="store_true", help="sans fenêtre, dt fixe 1/60")
    p.add_argument("--only", default=None, help="clé ou préfixe de clé (ex. attack.)")
    p.add_argument("--shots", default=None, help="dossier des captures (défaut shots/fx en headless)")
    p.add_argument("--shot-every", type=float, default=0.25)
    p.add_argument("--shot-scale", type=float, default=0.5)
    p.add_argument("--seconds", type=float, default=8.0, help="durée maximale par chorégraphie")
    p.add_argument("--list", action="store_true", help="liste les clés et quitte")
    p.add_argument("--seed", type=int, default=1)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    import random

    import pygame
    from pygame import Vector2

    from . import FxManager, BattleTransition, font
    from .choreo import ActionContext, REGISTRY, play, scripted, Seq, Par, Call, Wait

    random.seed(args.seed)
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Final Classe : démo des effets")

    # ---------------------------------------------------------- doublures
    class FakeActor:
        def __init__(self, name: str, home, size, color) -> None:
            self.name, self.home, self.size, self.color = name, Vector2(home), size, color
            self.reset()
            self.image = self._make()

        def reset(self) -> None:
            self.offset, self.scale, self.rotation = Vector2(), 1.0, 0.0
            self.alpha, self.visible, self.tint, self._flash = 255, True, None, 0.0
            self._flash_color = (255, 255, 255)

        def _make(self):
            w, h = self.size
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, self.color, (w * 0.25, 0, w * 0.5, h * 0.35))
            pygame.draw.rect(s, self.color, (w * 0.12, h * 0.3, w * 0.76, h * 0.7), border_radius=int(w * 0.2))
            pygame.draw.rect(s, (255, 255, 255), (w * 0.12, h * 0.3, w * 0.76, h * 0.7), 2, border_radius=int(w * 0.2))
            t = font(15).render(self.name, True, (255, 255, 255))
            s.blit(t, (w / 2 - t.get_width() / 2, h * 0.55))
            return s

        @property
        def rect(self) -> pygame.Rect:
            w, h = self.size[0] * self.scale, self.size[1] * self.scale
            p = self.home + self.offset
            return pygame.Rect(p.x - w / 2, p.y - h, w, h)

        def flash(self, color=(255, 255, 255), seconds: float = 0.12) -> None:
            self._flash, self._flash_color = seconds, color

        def set_pose(self, pose: str, hold: float | None = None) -> None:
            self.pose, self.pose_hold = pose, hold

        def draw(self, surface: pygame.Surface, dt: float) -> None:
            self._flash = max(0.0, self._flash - dt)
            if not self.visible:
                return
            img = self.image
            if self.scale != 1.0 or self.rotation:
                img = pygame.transform.rotozoom(img, -self.rotation, self.scale)
            else:
                img = img.copy()
            if self.tint:
                img.fill(self.tint + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            if self._flash > 0:
                img.fill(self._flash_color + (0,), special_flags=pygame.BLEND_RGB_ADD)
            img.set_alpha(self.alpha)
            r = self.rect
            surface.blit(img, img.get_rect(midbottom=r.midbottom))

    class FakeAudio:
        def __init__(self) -> None:
            self.played: list[str] = []

        def play_sfx(self, name, volume=1.0, pan=0.0) -> None:
            self.played.append(name)

        def duck(self, *a, **k) -> None:
            pass

    class FakeAssets:
        def image(self, ident: str) -> pygame.Surface:
            s = pygame.Surface((96, 96), pygame.SRCALPHA)
            pygame.draw.circle(s, (111, 128, 200), (48, 48), 46)
            s.blit(font(12).render(ident, True, (255, 255, 255)), (6, 40))
            return s

    heroes = [FakeActor("Héros", (280, 470), (110, 150), (74, 130, 200)),
              FakeActor("Allié", (200, 600), (110, 150), (74, 160, 120)),
              FakeActor("Mage", (380, 640), (100, 140), (150, 90, 190))]
    monsters = [FakeActor("Monstre A", (900, 450), (140, 170), (170, 70, 70)),
                FakeActor("Monstre B", (1040, 560), (150, 180), (190, 90, 60)),
                FakeActor("Monstre C", (880, 650), (130, 160), (150, 70, 110))]
    actors = heroes + monsters

    # ---------------------------------------------------------- scénarios de test des briques
    @scripted("demo.bricks")
    def bricks(c):
        from . import (Beam, EnergyOrb, GlassShards, LightColumn, Lightning, MagicCircle, Projectile,
                       Slash, Shockwave, ParticleEmitter, PRESETS, FIRE, ICE, HOLY, GOLD, THUNDER, GREEN)
        fx = c.fx
        t = c.targets[0]
        tc, mc = c.center(t), c.center(c.caster)
        names = list(PRESETS)

        def presets():
            for i, n in enumerate(names):
                fx.add(ParticleEmitter((120 + i * 135, 300), n, rate=60, duration=1.6, radius=18))
        return Seq(
            Call(presets),
            c.add(MagicCircle(c.feet(c.caster), 130, HOLY, life=2.2)),
            c.add(Lightning((tc.x, 0), tc, THUNDER)), 0.3,
            c.add(Projectile(mc, tc, 0.5, "orb", FIRE, arc=60, wobble=(30, 3))),
            c.add(Projectile(mc, tc + Vector2(0, 80), 0.5, "arrow", ICE, arc=40)),
            c.add(Projectile(mc, tc - Vector2(0, 80), 0.5, "shuriken", GREEN)), 0.6,
            c.add(Beam(mc, tc, ICE, 50, 0.8)),
            c.add(Slash.arc(tc, 100, -120, 60, ry=120, duration=0.2, width=26, color=ICE)), 0.3,
            c.add(GlassShards(tc, 30)), c.add(LightColumn(tc.x, t.rect.bottom, 420, 120, GOLD, 1.0)),
            c.add(EnergyOrb(mc, 36, HOLY, life=1.2)), 1.4,
        )

    @scripted("demo.transition_spiral")
    def tspiral(c):
        return Seq(c.add(BattleTransition("spiral", 1.0, hold=0.2)), 1.3)

    @scripted("demo.transition_shards")
    def tshards(c):
        return Seq(c.add(BattleTransition("shards", 1.0, hold=0.2)), 1.3)

    keys = sorted(REGISTRY)
    if args.list:
        print("\n".join(keys))
        return 0
    if args.only:
        sel = [k for k in keys if k == args.only or k.startswith(args.only)]
        if not sel:
            print(f"(clé inconnue « {args.only} » : chorégraphie générique)")
            sel = [args.only]
        keys = sel
    else:
        keys = [k for k in keys if k != "generic"] + ["generic"]

    shots_dir = Path(args.shots) if args.shots else (Path("shots/fx") if args.headless else None)
    if shots_dir:
        shots_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------- boucle
    fx = FxManager()
    audio, assets = FakeAudio(), FakeAssets()
    bg = pygame.Surface((W, H))
    for y in range(H):
        k = y / H
        bg.fill((int(20 + 25 * k), int(30 + 30 * k), int(70 + 40 * k)), (0, y, W, 1))
    pygame.draw.ellipse(bg, (30, 45, 80), (-100, 420, W + 200, 400))
    canvas = pygame.Surface((W, H))
    ui = font(20)
    clock = pygame.time.Clock()
    frames, spent, shots = 0, 0.0, []
    quit_all = False

    for key in keys:
        if quit_all:
            break
        for a in actors:
            a.reset()
        fx.clear()
        audio.played.clear()
        if key.startswith(MONSTER_KEYS):
            caster, targets = monsters[0], heroes[:]
        elif key.startswith(HEAL_KEYS):
            caster = heroes[0]
            targets = [caster] if key in ("action.defend", "state.level_up", "state.ko_hero") else [heroes[1]]
        else:
            caster, targets = heroes[0], monsters[:]
        if key.startswith("skill.thief") or key == "attack.monk":
            pass
        impacts = []
        values = [137, 88, 245][: len(targets)]
        ctx = ActionContext(caster, targets, values, [i == 0 for i in range(len(targets))],
                            impacts.append, fx, audio, assets, {"gil": 120, "stolen": "Potion"})
        choreo = play(key, ctx)
        t, next_shot, n = 0.0, 0.0, 0
        tail = 0.0
        while t < args.seconds and not quit_all:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    quit_all = True
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and choreo.skippable:
                    choreo.skip()
            dt = 1 / 60 if args.headless else min(clock.tick(60) / 1000, 1 / 30)
            t0 = time.perf_counter()
            alive = choreo.update(dt)
            fx.update(dt)
            canvas.blit(bg, (0, 0))
            fx.draw(canvas, "back")
            for a in sorted(actors, key=lambda a: a.home.y):
                a.draw(canvas, dt)
            fx.draw(canvas, "front")
            if not fx.hide_ui:
                pygame.draw.rect(canvas, (20, 30, 90), (0, H - 70, W, 70))
                pygame.draw.rect(canvas, (232, 236, 248), (0, H - 70, W, 70), 2)
                canvas.blit(ui.render(f"{key}   t={t:4.2f}s   impacts={sorted(impacts)}", True, (255, 255, 255)), (20, H - 50))
            fx.draw(canvas, "overlay")
            screen.fill((0, 0, 0))
            screen.blit(canvas, (int(fx.shake_offset.x), int(fx.shake_offset.y)))
            if not args.headless:
                pygame.display.flip()
            spent += time.perf_counter() - t0
            frames += 1
            if shots_dir and t >= next_shot - 1e-9:
                img = screen
                if args.shot_scale != 1.0:
                    img = pygame.transform.smoothscale(screen, (int(W * args.shot_scale), int(H * args.shot_scale)))
                path = shots_dir / f"{key.replace('.', '_')}_{n:03d}.png"
                pygame.image.save(img, str(path))
                shots.append(path)
                n += 1
                next_shot += args.shot_every
            t += dt
            if not alive:
                tail += dt
                if tail > 0.5 and not fx.busy:
                    break
                if tail > 2.5:
                    break
        missing = [i for i in range(len(targets)) if impacts.count(i) != 1]
        sounds = ",".join(dict.fromkeys(audio.played))
        print(f"{key:28s} {t:4.1f}s  impacts={'OK' if not missing else 'ERREUR ' + str(impacts)}  sons: {sounds}")

    if shots:
        print(f"{len(shots)} captures dans {shots_dir}")
    fps = frames / spent if spent > 0 else 0.0
    print(f"FPS moyen: {fps:.0f}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
