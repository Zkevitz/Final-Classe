"""Le combat : ATB en mode attente, héros à droite, monstres à gauche (docs/ARCHITECTURE-GFX.md §4).

Clés de chorégraphie émises : `attack.<job>`, `skill.<job>`, `spell.fire|ice|thunder|cure`,
`summon.<nom>`, `item.potion|ether|phoenix_down|elixir`, `action.defend`, `attack.monster`,
`monster.supernova|explosion|needles|bad_breath|fire_breath`, `state.ko_hero|ko_monster`.
"""

import random
import sys
from types import SimpleNamespace
from typing import override

import pygame
from pygame import Vector2

from final_classe.characters import Sephiroth
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.battle_actions import (
    Resolved, candidates, resolve_attack, resolve_defend, resolve_item, resolve_monster,
    resolve_skill, resolve_spell,
)
from final_classe.gfx.scenes.battle_actors import (
    ZONE_KEYS, BattleActor, draw_background, monster_positions, place_heroes,
)
from final_classe.gfx.ui import (
    Banner, Menu, draw_atb, draw_bar, draw_cursor, draw_hp, draw_mp, draw_text, draw_window,
    hp_color, is_cancel, is_confirm, nav, render_text, theme,
)
from final_classe.items import Target

try:  # tolérant : fx/ est écrit par un autre agent
    from final_classe.gfx.fx import BattleTransition
    from final_classe.gfx.fx.choreo import ActionContext, play
except Exception:  # noqa: BLE001
    BattleTransition = None  # type: ignore[assignment,misc]
    ActionContext = None  # type: ignore[assignment,misc]
    play = None  # type: ignore[assignment]

MENU_POS = (16, 558)
MENU_W = 490


HEAL_KEYS = {"spell.cure", "item.potion", "item.elixir", "item.phoenix_down", "skill.monk"}


def _value_kind(key: str) -> str:
    """Type des `values` d'une action : `damage`, `heal` ou `mp` (contrat `ActionContext.extra`)."""
    if key == "item.ether":
        return "mp"
    return "heal" if key in HEAL_KEYS else "damage"


class _FallbackChoreo:
    """Repli minimal : flash des cibles, impact, fin."""

    skippable = False
    dead = False
    tag = None
    layer = "none"

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.t = 0.0
        self.done = False
        self.hit = False

    def update(self, dt: float) -> bool:
        self.t += dt
        if not self.hit and self.t > 0.35:
            self.hit = True
            for i, target in enumerate(self.ctx.targets):
                target.flash()
                self.ctx.on_impact(i)
        if self.t > 0.8:
            self.done = True
        return not self.done

    def draw(self, surface, layer) -> None:
        """Rien à dessiner."""

    def skip(self) -> None:
        """Termine tout de suite, en émettant l'impact des cibles restantes."""
        if not self.hit:
            self.hit = True
            for i in range(len(self.ctx.targets)):
                self.ctx.on_impact(i)
        self.done = True


class BattleScene(Scene):
    """Un combat de la zone `zone` (indice), vague `wave` (indice)."""

    def __init__(self, game: Game, zone: int = 0, wave: int = 0) -> None:
        super().__init__(game)
        from final_classe.game.zones import ZONES

        if game.party is None:
            game.party = make_demo_party()
        self.party = game.party
        self.zone = max(0, min(zone, len(ZONES) - 1))
        waves = ZONES[self.zone].waves()
        self.n_waves = len(waves)
        self.wave = max(0, min(wave, self.n_waves - 1))
        self.monsters = waves[self.wave]
        self.is_boss = self.wave == self.n_waves - 1
        self.final = any(isinstance(m, Sephiroth) for m in self.monsters)
        self.heroes = [BattleActor(game, h, "hero", Vector2(), phase=i * 1.3) for i, h in enumerate(self.party.heroes)]
        self.foes = [BattleActor(game, m, "monster", Vector2(), phase=i * 0.9) for i, m in enumerate(self.monsters)]
        place_heroes(game.assets, self.heroes)
        widths = [float(game.assets.feet_rect(a.sprite).width) for a in self.foes]
        for a, pos in zip(self.foes, monster_positions(widths), strict=True):
            a.home = Vector2(pos)
            a.update(0.0)
        for a in self.heroes:
            a.atb = random.uniform(0.25, 0.75)
        for a in self.foes:
            a.atb = random.uniform(0.0, 0.3)
        self.world = pygame.Surface(game.size).convert()
        self.time = 0.0
        self.phase = "intro"
        self.timer = 1.5
        self.gap = 0.0
        self.banners: list[Banner] = []
        self.label: tuple[str, float] | None = None
        self.menu: Menu | None = None
        self.menu_kind = "main"
        self.active: BattleActor | None = None
        self.pending: dict = {}
        self.cands: list[BattleActor] = []
        self.target_all = False
        self.cursor = 0
        self.queue: list[Resolved] = []
        self.current: Resolved | None = None
        self.choreo = None
        self.ko_choreos: list = []
        self._ko_started: set[int] = set()
        self.outcome = ""
        self.ai_timer = 0.0
        self.phase_time = 0.0

    # --- aides --------------------------------------------------------------
    @property
    def everyone(self) -> list[BattleActor]:
        """Tous les combattants."""
        return [*self.heroes, *self.foes]

    def _sfx(self, name: str) -> None:
        try:
            self.game.audio.play_sfx(name)
        except Exception:  # noqa: BLE001
            pass

    def _make_ctx(self, caster, targets, values, critical, on_impact, extra):
        g = self.game
        if ActionContext is None:
            return SimpleNamespace(caster=caster, targets=targets, values=values, critical=critical,
                                   on_impact=on_impact, fx=g.fx, audio=g.audio, assets=g.assets, extra=extra)
        return ActionContext(caster=caster, targets=targets, values=values, critical=critical,
                             on_impact=on_impact, fx=g.fx, audio=g.audio, assets=g.assets, extra=extra)

    def _play(self, key: str, ctx):
        try:
            choreo = play(key, ctx) if play is not None else _FallbackChoreo(ctx)
        except Exception as error:  # noqa: BLE001
            print(f"[battle] {key} : {error!r}", file=sys.stderr)
            choreo = _FallbackChoreo(ctx)
        self.game.fx.add(choreo)
        return choreo

    # --- cycle de vie -------------------------------------------------------
    @override
    def on_enter(self) -> None:
        track = "final_boss" if self.final else "boss" if self.is_boss else "battle"
        self.game.audio.play_music(track)
        self._sfx("transition")
        if BattleTransition is not None:
            try:
                self.game.fx.add(BattleTransition("spiral", 0.9, reverse=True))
            except Exception:  # noqa: BLE001
                pass
        text = f"{self.monsters[0].name} apparaît !" if self.is_boss else "Combat !"
        self.banners.append(Banner(text, theme.GOLD, 1.7, y=90, size=40))

    @override
    def on_back(self) -> None:
        """Échap : annule le dernier choix (jamais de fuite)."""
        self._cancel()

    # --- ATB ----------------------------------------------------------------
    def _update_atb(self, dt: float) -> None:
        if self.gap > 0:
            self.gap -= dt
            return
        for a in self.everyone:
            if a.alive and a.atb < 1.0:
                a.atb = min(1.0, a.atb + dt * (0.06 + 0.045 * a.model.speed))
                if a.atb >= 1.0:
                    a.ready_t = self.time
        ready = [a for a in self.everyone if a.alive and a.atb >= 1.0]
        if not ready:
            return
        who = min(ready, key=lambda a: ((a.ready_t if a.ready_t is not None else 0.0), -a.model.speed))
        if who.side == "hero":
            self._begin_command(who)
        else:
            self._begin_monster(who)

    # --- tour d'un héros ----------------------------------------------------
    def _begin_command(self, actor: BattleActor) -> None:
        self.active = actor
        actor.model.start_turn()
        kill = getattr(self.game.fx, "kill", None)
        if callable(kill):
            kill(f"shield:{id(actor)}")
        self.phase = "command"
        self._main_menu()
        self.ai_timer = 0.9
        self._sfx("menu_open")

    def _main_menu(self) -> None:
        hero = self.active.model  # type: ignore[union-attr]
        items = ["Attaquer", f"{hero.SKILL_NAME} · {hero.SKILL_COST}", "Magie", "Objet", "Défendre"]
        self.menu = Menu(items, MENU_POS, MENU_W, row_h=40, font_size=22, columns=2)
        self.menu.enabled = [True, hero.can_use_skill, bool(hero.spells), bool(self.party.items), True]
        self.menu_kind = "main"

    def _sub_menu(self, kind: str) -> None:
        hero = self.active.model  # type: ignore[union-attr]
        if kind == "magic":
            items = [f"{m.name} · {m.cost}" for m in hero.spells]
            enabled = [hero.can_cast(m) for m in hero.spells]
        else:
            counts = self.party.items.counts()
            items = [f"{name} ×{n}" for name, n in counts.items()]
            enabled = [True] * len(items)
        cols = 1 if len(items) <= 3 else 2 if len(items) <= 6 else 3
        self.menu = Menu(items, MENU_POS, MENU_W, row_h=40, font_size=22, columns=cols)
        self.menu.enabled = enabled
        self.menu_kind = kind

    def _cancel(self) -> None:
        if self.phase == "target":
            self.phase = "command"
            self._sfx("cancel")
        elif self.phase == "command" and self.menu_kind != "main":
            self._main_menu()
            self._sfx("cancel")

    def _select_main(self, idx: int) -> None:
        a = self.active
        assert a is not None
        hero = a.model
        if idx == 0:
            self.pending = {"kind": "attack"}
            self._begin_target(Target.ENEMY)
        elif idx == 1:
            self.pending = {"kind": "skill"}
            self._begin_target(hero.SKILL_TARGET)
        elif idx == 2:
            self._sub_menu("magic")
            self._sfx("confirm")
        elif idx == 3:
            self._sub_menu("item")
            self._sfx("confirm")
        else:
            self._start(resolve_defend(a))

    def _select_sub(self, idx: int) -> None:
        hero = self.active.model  # type: ignore[union-attr]
        if self.menu_kind == "magic":
            m = hero.spells[idx]
            self.pending = {"kind": "spell", "materia": m}
            self._begin_target(m.TARGET)
        else:
            name = list(self.party.items.counts())[idx]
            item = next(i for i in self.party.items if i.name == name)
            self.pending = {"kind": "item", "name": name}
            self._begin_target(item.TARGET)

    def _begin_target(self, kind: Target) -> None:
        cands, whole = candidates(kind, self.heroes, self.foes)
        if not cands:
            self._sfx("error")
            return
        self.cands, self.target_all = cands, whole
        self.cursor = cands.index(self.active) if self.active in cands and kind is Target.ALLY else 0
        self.phase = "target"
        self._sfx("confirm")

    def _confirm_target(self) -> None:
        a = self.active
        assert a is not None
        targets = list(self.cands) if self.target_all else [self.cands[self.cursor]]
        kind = self.pending["kind"]
        r: Resolved | None
        if kind == "attack":
            r = resolve_attack(a, targets[0])
        elif kind == "skill":
            r = resolve_skill(a, targets)
        elif kind == "spell":
            r = resolve_spell(a, self.pending["materia"], targets)
        else:
            r = resolve_item(a, self.party, self.pending["name"], targets[0])
        if r is None:
            self._sfx("error")
            self.phase = "command"
            return
        self._start(r)

    # --- IA de démonstration ------------------------------------------------
    def _ai(self, a: BattleActor) -> Resolved:
        hero = a.model
        foes = [m for m in self.foes if m.alive]
        allies = [h for h in self.heroes if h.alive]
        hurt = min(allies, key=lambda h: h.model.hp_ratio)
        down = [h for h in self.heroes if not h.alive]
        r: Resolved | None = None
        if down and "Queue de phénix" in self.party.items and random.random() < 0.8:
            r = resolve_item(a, self.party, "Queue de phénix", down[0])
        elif hurt.model.hp_ratio < 0.45 and "Potion" in self.party.items and random.random() < 0.7:
            r = resolve_item(a, self.party, "Potion", hurt)
        if r is None:
            x = random.random()
            if x < 0.3 and hero.can_use_skill:
                cs, whole = candidates(hero.SKILL_TARGET, self.heroes, self.foes)
                if cs:
                    ts = cs if whole else [hurt if hero.SKILL_TARGET is Target.ALLY else random.choice(cs)]
                    r = resolve_skill(a, ts)
            elif x < 0.58 and hero.spells:
                m = random.choice(hero.spells)
                cs, whole = candidates(m.TARGET, self.heroes, self.foes)
                if cs and hero.can_cast(m) and (m.TARGET is not Target.ALLY or hurt.model.hp_ratio < 0.8):
                    ts = cs if whole else [hurt if m.TARGET is Target.ALLY else random.choice(cs)]
                    r = resolve_spell(a, m, ts)
            elif 0.58 <= x < 0.64:
                r = resolve_defend(a)
        return r or resolve_attack(a, random.choice(foes))

    # --- tour d'un monstre --------------------------------------------------
    def _begin_monster(self, actor: BattleActor) -> None:
        actor.atb = 0.0
        actor.ready_t = None
        acts = resolve_monster(actor, self.heroes)
        if not acts:
            return
        self.queue = acts[1:]
        self._start(acts[0])

    # --- lancement et fin d'une action --------------------------------------
    def _start(self, r: Resolved) -> None:
        g = self.game
        forced = g.force_action
        if forced:
            r.key = forced
            if forced.startswith(("summon.", "monster.supernova")):
                pool = [m for m in self.foes if m.alive] if r.caster.side == "hero" else [h for h in self.heroes if h.alive]
                if len(pool) > len(r.targets):
                    base = r.values[0] if r.values else 0
                    r.targets = pool
                    r.values = [base] * len(pool)
                    r.critical = [False] * len(pool)
        caster = r.caster
        caster.atb = 0.0
        caster.ready_t = None
        caster.sync(hp=False)
        self.menu = None
        self.active = None
        self.current = r
        if r.label:
            self.label = (r.label, 2.2)

        def on_impact(i: int, r: Resolved = r) -> None:
            if 0 <= i < len(r.targets):
                t = r.targets[i]
                lost = t.model.hp < t.target_hp - 0.5  # dégâts (un soin ne fait pas `hurt`)
                t.sync()
                if lost:  # `hurt` 0,3 s ; s'il tombe, la pose reste jusqu'au K.O.
                    t.set_pose("hurt", hold=0.3 if t.alive else None)

        extra = dict(r.extra)
        extra["kind"] = _value_kind(r.key)
        ctx = self._make_ctx(caster, r.targets, r.values, r.critical, on_impact, extra)
        if r.key.startswith("summon."):
            try:
                g.audio.duck(0.35, 4.0)
            except Exception:  # noqa: BLE001
                pass
        self.choreo = self._play(r.key, ctx)
        self.phase = "action"
        self.phase_time = 0.0

    @staticmethod
    def _force_end(choreo) -> None:
        skip = getattr(choreo, "skip", None)
        if callable(skip):
            skip()
        try:
            choreo.done = True
        except AttributeError:
            pass

    def _action_done(self) -> None:
        r = self.current
        assert r is not None
        for a in [*r.targets, r.caster]:
            a.sync()
        if r.vanish:
            r.caster.visible = False
            self._ko_started.add(id(r.caster))
        self.current = None
        self.choreo = None
        if r.caster.alive:  # filet : le lanceur revient à sa pose de base
            r.caster.set_pose("idle")
        if self.queue:
            self._start(self.queue.pop(0))
            return
        c = r.caster
        if c.side == "monster" and c.alive and getattr(c.model, "warning", None):
            self.banners.append(Banner(c.model.warning, theme.HP_MID, 2.4, y=96, size=32, title=False))
        self.gap = 0.35
        self._ko_pass()

    def _ko_pass(self) -> None:
        self.ko_choreos = []
        for a in self.heroes:
            if a.alive:
                self._ko_started.discard(id(a))  # relevé : un 2e K.O. rejouera l'animation
        for a in self.everyone:
            if a.alive or id(a) in self._ko_started:
                continue
            self._ko_started.add(id(a))
            a.set_pose("ko")
            key = "state.ko_hero" if a.side == "hero" else "state.ko_monster"
            ctx = self._make_ctx(a, [a], [0], [False], lambda i: None, {})
            self.ko_choreos.append(self._play(key, ctx))
        if self.ko_choreos:
            self.phase = "ko"
            self.phase_time = 0.0
        else:
            self._check_end()

    def _finish_ko(self) -> None:
        for a in self.everyone:
            if a.alive:
                continue
            a.sync()
            a.offset.update(0, 0)
            a.rotation, a.scale, a.alpha = 0.0, 1.0, 255
            if a.side == "hero":
                a.ko = True
                a.tint = None
                a.set_pose("idle")  # pose de base = ko
            else:
                a.visible = False
        self.ko_choreos = []
        self._check_end()

    def _check_end(self) -> None:
        if not any(m.alive for m in self.foes):
            self.phase, self.timer, self.outcome = "end", 0.9, "win"
            for h in self.heroes:
                if h.alive:
                    h.set_pose("victory")
        elif not any(h.alive for h in self.heroes):
            self.phase, self.timer, self.outcome = "end", 1.6, "lose"
            self.game.audio.stop_music(1200)
        else:
            self.phase = "idle"

    def _leave(self) -> None:
        if self.outcome == "win":
            from final_classe.gfx.scenes.victory import VictoryScene

            self.game.replace(VictoryScene(self.game, self.monsters, self.zone, self.wave, self.n_waves))
        else:
            from final_classe.gfx.scenes.game_over import GameOverScene

            self.game.replace(GameOverScene(self.game, self.zone, self.wave))

    # --- évènements ---------------------------------------------------------
    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.game.demo:
            return
        if self.phase == "action":
            if is_confirm(event) and self.choreo is not None and getattr(self.choreo, "skippable", False):
                self.choreo.skip()
            return
        if self.phase == "command" and self.menu is not None:
            if is_cancel(event):
                self._cancel()
                return
            before = self.menu.cursor
            idx = self.menu.handle_event(event)
            if self.menu.cursor != before:
                self._sfx("cursor")
            if idx is not None:
                if self.menu_kind == "main":
                    self._select_main(idx)
                else:
                    self._select_sub(idx)
            elif is_confirm(event):
                self._sfx("error")
        elif self.phase == "target":
            if is_cancel(event):
                self._cancel()
                return
            dx, dy = nav(event)
            step = (dx or dy)
            if step and not self.target_all:
                self.cursor = (self.cursor + step) % len(self.cands)
                self._sfx("cursor")
            elif is_confirm(event):
                self._confirm_target()
            elif event.type == pygame.MOUSEMOTION and not self.target_all:
                for i, c in enumerate(self.cands):
                    if c.rect.inflate(30, 30).collidepoint(event.pos) and i != self.cursor:
                        self.cursor = i
                        self._sfx("cursor")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.target_all or any(
                    c.rect.inflate(30, 30).collidepoint(event.pos) for c in self.cands
                ):
                    self._confirm_target()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self._cancel()

    # --- mise à jour --------------------------------------------------------
    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.phase_time += dt
        for a in self.everyone:
            a.lean_target = 26.0 if (a is self.active and self.phase in ("command", "target")) else 0.0
            a.ready_state = a.side == "hero" and a.alive and (a.atb >= 1.0 or a is self.active)
            a.update(dt)
        self.banners = [b for b in self.banners if b.update(dt)]
        if self.label is not None:
            text, left = self.label
            self.label = (text, left - dt) if left - dt > 0 else None
        if self.menu is not None:
            self.menu.update(dt)
        if self.phase == "intro":
            self.timer -= dt
            if self.timer <= 0:
                self.phase = "idle"
        elif self.phase == "idle":
            self._update_atb(dt)
        elif self.phase == "command":
            if self.game.demo and self.active is not None:
                self.ai_timer -= dt
                if self.ai_timer <= 0:
                    self._start(self._ai(self.active))
        elif self.phase == "action":
            if self.choreo is not None and self.phase_time > 15.0 and not getattr(self.choreo, "done", True):
                self._force_end(self.choreo)  # ne jamais bloquer le combat
            if self.choreo is not None and getattr(self.choreo, "done", True):
                self._action_done()
        elif self.phase == "ko":
            if self.phase_time > 8.0:
                for c in self.ko_choreos:
                    if not getattr(c, "done", True):
                        self._force_end(c)
            if all(getattr(c, "done", True) for c in self.ko_choreos):
                self._finish_ko()
        elif self.phase == "end":
            self.timer -= dt
            if self.timer <= 0 and not self.game.transitioning:
                self.phase = "left"
                self._leave()

    # --- dessin -------------------------------------------------------------
    @override
    def draw(self, surface: pygame.Surface) -> None:
        g = self.game
        w = self.world
        draw_background(g, w, self.zone)
        g.fx.draw(w, "back")
        actors = sorted((a for a in self.everyone if a.visible), key=lambda a: (a.draw_front, a.home.y))
        for a in actors:
            a.draw_shadow(w)
        for a in actors:
            a.draw(w)
        for a in self.foes:
            targeted = self.phase == "target" and a in self.cands
            if a.visible and (a.bar_timer > 0 or targeted) and not self.is_boss:
                r = pygame.Rect(0, 0, 110, 8)
                r.midtop = (a.rect.centerx, int(a.home.y) + 12)
                draw_bar(w, r, a.shown_hp / a.model.max_hp, hp_color(a.shown_hp / a.model.max_hp))
        g.fx.draw(w, "front")
        off = getattr(g.fx, "shake_offset", None)
        ox, oy = (int(off[0]), int(off[1])) if off is not None else (0, 0)
        surface.fill((0, 0, 0))
        surface.blit(w, (ox, oy))
        if not getattr(g.fx, "hide_ui", False):
            self._draw_ui(surface)

    def _draw_ui(self, surface: pygame.Surface) -> None:
        if self.is_boss and self.foes and self.foes[0].visible:
            boss = self.foes[0]
            ratio = boss.shown_hp / boss.model.max_hp
            draw_text(surface, boss.model.name, (640, 12), 22, anchor="midtop")
            draw_bar(surface, pygame.Rect(340, 42, 600, 14), ratio, hp_color(ratio))
        self._draw_party(surface)
        if self.menu is not None and self.phase in ("command", "target"):
            self.menu.draw(surface, self.game.assets, show_cursor=self.phase == "command")
        else:
            self._draw_enemy_list(surface)
        if self.phase == "target":
            for i, t in enumerate(self.cands):
                if self.target_all or i == self.cursor:
                    draw_cursor(surface, self.game.assets, (t.rect.left - 6, t.rect.centery), self.time)
            self._draw_target_label(surface)
        if self.label is not None:
            text = render_text(self.label[0], 26, theme.WHITE)
            r = pygame.Rect(0, 0, text.get_width() + 70, 44)
            r.midtop = (640, 70 if self.is_boss else 20)
            draw_window(surface, r)
            surface.blit(text, text.get_rect(center=r.center))
        for b in self.banners:
            b.draw(surface)

    def _draw_enemy_list(self, surface: pygame.Surface) -> None:
        r = draw_window(surface, (*MENU_POS, MENU_W, 148))
        for i, a in enumerate([f for f in self.foes if f.visible][:4]):
            draw_text(surface, a.model.name, (r.x + 28, r.y + 14 + i * 31), 22)

    def _draw_target_label(self, surface: pygame.Surface) -> None:
        if self.target_all:
            text = "Tous les ennemis" if self.cands and self.cands[0].side == "monster" else "Toute l'équipe"
        else:
            t = self.cands[self.cursor]
            text = t.model.name
            if t.side == "monster":
                text += f"   {int(round(t.shown_hp))}/{t.model.max_hp}"
        surf = render_text(text, 24, theme.WHITE)
        r = pygame.Rect(0, 0, surf.get_width() + 70, 44)
        r.midtop = (640, 70 if self.is_boss else 20)
        draw_window(surface, r)
        surface.blit(surf, surf.get_rect(center=r.center))

    def _draw_party(self, surface: pygame.Surface) -> None:
        r = draw_window(surface, (512, 558, 752, 148))
        n = max(1, len(self.heroes))
        row_h = min(40, (r.height - 16) // n)
        for i, a in enumerate(self.heroes):
            y = r.y + 10 + i * row_h
            active = a is self.active
            color = theme.GOLD if active else (theme.TEXT if a.alive else (140, 100, 110))
            if active:
                draw_cursor(surface, self.game.assets, (r.x + 22, y + row_h // 2), self.time)
            draw_text(surface, a.model.name, (r.x + 30, y + row_h // 2), 22, color, "midleft")
            m = a.model
            draw_hp(surface, pygame.Rect(r.x + 190, y + row_h // 2, 190, 11), a.shown_hp, m.max_hp)
            draw_mp(surface, pygame.Rect(r.x + 420, y + row_h // 2, 130, 11), a.shown_mp, m.max_mp)
            ratio = 1.0 if (a is self.active) else (a.atb if a.alive else 0.0)
            draw_atb(surface, pygame.Rect(r.x + 585, y + row_h // 2 + 1, 130, 10), ratio, self.time)


def _parse(game: Game, args: list[str]) -> tuple[int, int]:
    """`battle:plains:1` -> (zone 0, vague 0) ; sans argument : l'état de `game`."""
    zone, wave = game.zone, game.wave
    if args:
        key = args[0].lower()
        zone = ZONE_KEYS.index(key) if key in ZONE_KEYS else int(key) if key.isdigit() else 0
        wave = max(0, int(args[1]) - 1) if len(args) > 1 and args[1].isdigit() else 0
    return zone, wave


@register_scene("battle")
def make_battle(game: Game, args: list[str]) -> Scene:
    """`battle:<zone>:<vague>` (vague comptée à partir de 1)."""
    zone, wave = _parse(game, args)
    return BattleScene(game, zone, wave)
