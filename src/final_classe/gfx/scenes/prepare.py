"""Préparation : équiper, monter et retirer des materias, avec les stats avant/après (logique de `game/preparation.py`)."""

from typing import override

import pygame

from final_classe.gfx.engine import Game, Scene, make_demo_party, register_scene
from final_classe.gfx.engine.registry import SCENES
from final_classe.gfx.scenes import flow
from final_classe.gfx.scenes._demo import hero_image
from final_classe.gfx.scenes.flow import Row, ScrollList
from final_classe.gfx.ui import Banner, Menu, draw_text, draw_window, is_cancel, theme
from final_classe.gfx.ui.gauges import draw_bar
from final_classe.gfx.ui.menu import draw_cursor
from final_classe.items import Equipment, Slot

SLOT_NAMES = {Slot.WEAPON: "Arme", Slot.ARMOR: "Armure", Slot.ACCESSORY: "Accessoire"}
ACTIONS = ("equip", "attach", "detach")
HINTS = {
    "main": "←/→ : changer de héros   Entrée : choisir   Échap : partir",
    "hero": "↑/↓ : choisir le héros   Entrée : valider   Retour arrière : annuler",
    "list": "↑/↓ : choisir   Entrée : valider   Retour arrière : annuler",
}


class PrepareScene(Scene):
    """Menu à gauche, équipe sous le menu, fiche du héros en haut, liste contextuelle en bas."""

    def __init__(self, game: Game, in_flow: bool = False) -> None:
        super().__init__(game)
        if game.party is None:
            game.party = make_demo_party()
        self.party = game.party
        self.in_flow = in_flow
        self.menu = Menu(["Équiper", "Monter une materia", "Retirer une materia", "Partir"], (30, 30),
                         width=310, row_h=44, font_size=24)
        self.list = ScrollList((360, 380, 890, 310), row_h=46, empty="(vide)", sub_x=330,
                               on_move=lambda: self.game.audio.play_sfx("cursor"))
        self.mode = "main"  # main | hero | list
        self.action = "equip"
        self.stage = "materia"  # pour « monter » : materia puis piece
        self.picked = None
        self.hero_i = 0
        self.time = 0.0
        self.banner: Banner | None = None
        K = pygame
        self.pilot = flow.KeyPilot(game, [
            K.K_RETURN, K.K_RETURN, K.K_RETURN, K.K_BACKSPACE, K.K_BACKSPACE, K.K_DOWN, K.K_RETURN,
            K.K_RETURN, K.K_RETURN, K.K_RETURN, K.K_BACKSPACE, K.K_BACKSPACE, K.K_BACKSPACE,
        ], period=1.0, start=0.9)

    @property
    def hero(self):
        """Le héros en cours."""
        return self.party.heroes[self.hero_i]

    # --- listes ------------------------------------------------------------------------
    def _rows(self) -> list[Row]:
        hero, party = self.hero, self.party
        if self.action == "equip":
            return [Row(i.name, flow.equipment_icon(i), i.stats.bonus_text(), SLOT_NAMES[i.slot]) for i in party.bag]
        if self.action == "attach" and self.stage == "materia":
            return [Row(m.name, flow.materia_icon(m), f"{m.cost} PM", "") for m in party.materias]
        if self.action == "attach":
            return [Row(i.name, flow.equipment_icon(i), SLOT_NAMES[i.slot], f"{len(i.materias)}/{i.slots}",
                        len(i.materias) < i.slots, theme.GOLD) for i in hero.equipment]
        return [Row(m.name, flow.materia_icon(m), f"{m.cost} PM") for m in hero.spells]

    def _reload(self) -> None:
        self.list.set_rows(self._rows())
        self.list.empty = {
            "equip": "Le sac est vide.", "attach": "Aucune materia en réserve." if self.stage == "materia" else "Ce héros ne porte rien.",
            "detach": "Ce héros n'a aucune materia.",
        }[self.action]

    def _say(self, text: str, ok: bool = False) -> None:
        self.banner = Banner(text, color=theme.HP if ok else theme.HP_LOW, seconds=1.6, y=300, size=30)
        self.game.audio.play_sfx("confirm" if ok else "error")

    def _preview_item(self) -> Equipment | None:
        if self.mode == "list" and self.action == "equip" and self.list.rows:
            return self.party.bag[self.list.cursor]
        return None

    # --- navigation --------------------------------------------------------------------
    def _leave(self) -> None:
        self.game.audio.play_sfx("cancel")
        if self.in_flow:
            flow.prepare_done(self.game)
        elif len(self.game.stack) > 1:
            self.game.pop(transition="fade")
        elif "world_map" in SCENES:
            self.game.replace(SCENES["world_map"](self.game, []))

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("world_map")

    @override
    def on_back(self) -> None:
        if self.mode == "list" and self.action == "attach" and self.stage == "piece":
            self.stage = "materia"
            self._reload()
        elif self.mode == "list":
            self.mode = "hero"
        elif self.mode == "hero":
            self.mode = "main"
        else:
            self._leave()
            return
        self.game.audio.play_sfx("cancel")

    def _enter_list(self) -> None:
        self.stage = "materia"
        self._reload()
        if not self.list.rows:
            self._say(self.list.empty)
            return
        self.mode = "list"
        self.game.audio.play_sfx("confirm")

    def _list_confirm(self, i: int) -> None:
        hero, party = self.hero, self.party
        if self.action == "equip":
            item = party.bag.pop(i)
            previous = hero.equip(item)
            if previous is not None:
                party.bag.append(previous)
            self._say(f"{item.name} équipé", True)
        elif self.action == "attach":
            if self.stage == "materia":
                if not hero.equipment:
                    self._say("Ce héros ne porte rien.")
                    return
                self.picked = party.materias[i]
                self.stage = "piece"
                self.game.audio.play_sfx("confirm")
            else:
                item = hero.equipment[i]
                if item.attach(self.picked):
                    party.materias.remove(self.picked)
                    self._say(f"{self.picked.name} montée sur {item.name}", True)
                    self.stage = "materia"
                else:
                    self._say(f"{item.name} n'a plus d'emplacement libre.")
        else:
            materia = hero.spells[i]
            for item in hero.equipment:
                if item.detach(materia):
                    party.materias.append(materia)
                    self._say(f"{materia.name} retourne dans la réserve", True)
                    break
        self._reload()
        if not self.list.rows and not (self.action == "attach" and self.stage == "piece"):
            self.mode = "main"

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        a = self.game.audio
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_BACKSPACE, pygame.K_x):
            self.on_back()
            return
        if self.mode == "main":
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_q):
                self.hero_i = (self.hero_i - 1) % len(self.party.heroes)
                a.play_sfx("cursor")
                return
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RIGHT, pygame.K_d):
                self.hero_i = (self.hero_i + 1) % len(self.party.heroes)
                a.play_sfx("cursor")
                return
            before = self.menu.cursor
            chosen = self.menu.handle_event(event)
            if self.menu.cursor != before:
                a.play_sfx("cursor")
            if chosen == 3:
                self._leave()
            elif chosen is not None:
                self.action = ACTIONS[chosen]
                self.mode = "hero"
                a.play_sfx("confirm")
        elif self.mode == "hero":
            n = len(self.party.heroes)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.hero_i = (self.hero_i - 1) % n
                    a.play_sfx("cursor")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.hero_i = (self.hero_i + 1) % n
                    a.play_sfx("cursor")
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
                    self._enter_list()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i in range(n):
                    if self._card_rect(i).collidepoint(event.pos):
                        self.hero_i = i
                        self._enter_list()
        else:
            res = self.list.handle_event(event)
            if res is not None and res >= 0:
                self._list_confirm(res)
            elif res == -1:
                a.play_sfx("error")

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        self.menu.update(dt)
        self.list.update(dt)
        if self.banner and not self.banner.update(dt):
            self.banner = None
        key = self.pilot.update(dt)
        if key is not None:
            flow.press(self, key)

    # --- dessin ------------------------------------------------------------------------
    def _card_rect(self, i: int) -> pygame.Rect:
        n = len(self.party.heroes)
        h = min(108, 420 // max(1, n))
        return pygame.Rect(30, 262 + i * (h + 4), 310, h)

    def _draw_cards(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        for i, hero in enumerate(self.party.heroes):
            r = self._card_rect(i)
            draw_window(surface, r)
            if i == self.hero_i:
                pygame.draw.rect(surface, theme.GOLD, r, 2, border_radius=theme.RADIUS)
            box = pygame.Rect(r.x + 8, r.y + 6, 70, r.height - 12)
            flow.draw_portrait(surface, assets, hero_image(hero), box)
            draw_text(surface, hero.name, (r.x + 90, r.y + 14), 22, theme.GOLD if i == self.hero_i else theme.TEXT)
            draw_text(surface, f"{hero.title}  Niv. {hero.level}", (r.x + 90, r.y + 40), 15, theme.TEXT_DIM)
            draw_bar(surface, pygame.Rect(r.x + 90, r.y + 64, 200, 8), hero.hp_ratio, theme.HP)
            if self.mode == "hero" and i == self.hero_i:
                draw_cursor(surface, assets, (r.x + 8, r.centery), self.time)

    def _draw_sheet(self, surface: pygame.Surface) -> None:
        assets, hero = self.game.assets, self.hero
        draw_window(surface, (360, 30, 890, 330))
        flow.draw_portrait(surface, assets, hero_image(hero), pygame.Rect(376, 50, 210, 290))
        draw_text(surface, hero.name, (610, 48), 28, theme.GOLD, bold=True)
        draw_text(surface, f"{hero.title}   Niv. {hero.level}", (610, 84), 18, theme.TEXT_DIM)
        before = hero.stats
        preview = self._preview_item()
        after = flow.stats_with(hero, preview) if preview is not None else None
        for k, (attr, label) in enumerate(flow.STAT_LABELS):
            y = 128 + k * 40
            cur = getattr(before, attr)
            draw_text(surface, label, (610, y), 22, theme.TEXT_DIM)
            draw_text(surface, str(cur), (730, y), 24, anchor="topright")
            if after is not None:
                new = getattr(after, attr)
                color = theme.HP if new > cur else (theme.HP_LOW if new < cur else theme.TEXT_DIM)
                draw_text(surface, "→", (755, y), 22, theme.TEXT_DIM)
                draw_text(surface, str(new), (840, y), 24, color, "topright", bold=new != cur)
        draw_text(surface, f"PV {hero.hp}/{hero.max_hp}", (610, 332), 16, theme.TEXT_DIM, "bottomleft")
        # emplacements
        for k, slot in enumerate((Slot.WEAPON, Slot.ARMOR, Slot.ACCESSORY)):
            y = 56 + k * 100
            item = hero.gear.get(slot)
            hl = preview is not None and preview.slot is slot
            if hl:
                surface.blit(flow.solid((370, 90), (242, 193, 78, 40)), (870, y - 6))
            draw_text(surface, SLOT_NAMES[slot], (880, y), 16, theme.TEXT_DIM)
            if item is None:
                draw_text(surface, "— aucun —", (880, y + 28), 20, (110, 118, 150))
                continue
            flow.draw_icon(surface, assets, flow.equipment_icon(item), (900, y + 44), 40)
            draw_text(surface, item.name, (930, y + 26), 20)
            draw_text(surface, item.stats.bonus_text(), (930, y + 50), 14, theme.TEXT_DIM)
            for s in range(item.slots):
                cx = 1214 - (item.slots - 1 - s) * 30
                pygame.draw.circle(surface, (10, 14, 36), (cx, y + 36), 12)
                pygame.draw.circle(surface, theme.INNER_LINE, (cx, y + 36), 12, 2)
                if s < len(item.materias):
                    flow.draw_icon(surface, assets, flow.materia_icon(item.materias[s]), (cx, y + 36), 22)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        flow.draw_backdrop(surface, assets, "bg_world_map", 0.55)
        self.menu.draw(surface, assets, show_cursor=self.mode == "main")
        self._draw_cards(surface)
        self._draw_sheet(surface)
        self.list.draw(surface, assets, active=self.mode == "list")
        title = {"equip": "Sac d'équipement", "attach": "Materias en réserve" if self.stage == "materia" else "Sur quelle pièce ?",
                 "detach": "Materias montées"}[self.action]
        if self.mode != "main":
            draw_text(surface, title, (1230, 360), 16, theme.GOLD, "bottomright")
        draw_text(surface, HINTS[self.mode], (805, 704), 16, theme.TEXT_DIM, "center")
        if self.banner:
            self.banner.draw(surface)


@register_scene("prepare")
def make_prepare(game: Game, args: list[str]) -> Scene:
    """Fabrique : `prepare` (depuis la carte, Échap revient) ou `prepare:flow` (avant une zone)."""
    return PrepareScene(game, in_flow="flow" in args)
