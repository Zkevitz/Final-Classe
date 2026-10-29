"""Boutique de Cid : acheter, vendre, objets (logique de `game/shop.py`, sans `input()`)."""

from typing import override

import pygame

from final_classe.gfx.engine import Game, Scene, make_demo_party, register_scene
from final_classe.gfx.engine.registry import SCENES
from final_classe.gfx.scenes import flow
from final_classe.gfx.scenes.flow import Row, ScrollList
from final_classe.gfx.ui import Banner, Menu, draw_text, draw_window, is_cancel, theme, wrap_text

GOODS_TEXT = {
    "Potion": "Rend 400 PV à un allié.",
    "Éther": "Rend 60 PM à un allié.",
    "Queue de phénix": "Relève un allié K.O. avec la moitié de ses PV.",
    "Élixir": "Rend tous les PV et tous les PM à un allié.",
}
RED = (255, 120, 120)


class ShopScene(Scene):
    """Menu (Acheter / Vendre / Objets / Partir) à gauche, liste à droite, détail en bas."""

    def __init__(self, game: Game, which: str = "first") -> None:
        super().__init__(game)
        if game.party is None:
            game.party = make_demo_party()
        self.party = game.party
        self.shop = flow.get_shop(game, which)
        self.menu = Menu(["Acheter", "Vendre", "Objets", "Partir"], (30, 30), width=290, row_h=44)
        self.list = ScrollList((340, 30, 910, 420), empty="Rien ici.",
                               on_move=lambda: self.game.audio.play_sfx("cursor"))
        self.focus = "menu"
        self.quip = "Approchez ! Du solide, et pas cher."
        self.banner: Banner | None = None
        self.time = 0.0
        self.pilot = flow.KeyPilot(game, [
            pygame.K_RETURN, pygame.K_RETURN, pygame.K_BACKSPACE, pygame.K_DOWN, pygame.K_DOWN,
            pygame.K_RETURN, pygame.K_RETURN, pygame.K_BACKSPACE, pygame.K_UP, pygame.K_UP, pygame.K_UP,
            pygame.K_RETURN,
        ], period=1.0, start=0.8)
        self._refresh()

    # --- contenu -----------------------------------------------------------------------
    @property
    def mode(self) -> str:
        """« buy », « sell », « goods » ou « leave » selon la ligne du menu."""
        return ("buy", "sell", "goods", "leave")[self.menu.cursor]

    def _refresh(self) -> None:
        gil = self.party.gil
        rows: list[Row] = []
        if self.mode == "buy":
            for item in self.shop.shelf:
                rows.append(Row(item.name, flow.equipment_icon(item), self._stats_text(item),
                                f"{item.price} gils", item.price <= gil,
                                theme.GOLD if item.price <= gil else RED))
        elif self.mode == "sell":
            for item in self.party.bag:
                rows.append(Row(item.name, flow.equipment_icon(item), self._stats_text(item),
                                f"{item.price // 2} gils"))
        elif self.mode == "goods":
            counts = self.party.items.counts()
            for kind in self.shop.goods:
                rows.append(Row(kind.name, flow.usable_icon(kind.name), f"En sac : {counts.get(kind.name, 0)}",
                                f"{kind.PRICE} gils", kind.PRICE <= gil, theme.GOLD if kind.PRICE <= gil else RED))
        self.list.set_rows(rows)
        self.list.empty = "Le sac est vide." if self.mode == "sell" else (
            "L'étal est vide." if self.mode == "buy" else "À bientôt !")

    @staticmethod
    def _stats_text(item) -> str:
        text = item.stats.bonus_text()
        if item.slots:
            text += f"  ◆×{item.slots}"
        return text

    def _say(self, text: str, error: bool = False) -> None:
        self.quip = text
        self.game.audio.play_sfx("error" if error else "buy")

    # --- actions -----------------------------------------------------------------------
    def _act(self, i: int) -> None:
        mode, party, shop = self.mode, self.party, self.shop
        if mode == "buy":
            item = shop.shelf[i]
            if not party.buy(item):
                self._say("Pas assez de gils !", True)
            else:
                shop.stock.remove(item)
                self._say(f"{item.name} rejoint le sac. Excellent choix !")
                self.banner = Banner(f"- {item.price} gils", color=theme.GOLD, seconds=1.2, y=330, size=30)
        elif mode == "sell":
            item = party.bag[i]
            gain = party.sell(item)
            shop.stock.append(item)
            self.game.audio.play_sfx("coins")
            self.quip = f"{item.name} vendu : +{gain} gils. Affaire conclue !"
            self.banner = Banner(f"+ {gain} gils", color=theme.HP, seconds=1.2, y=330, size=30)
        elif mode == "goods":
            kind = shop.goods[i]
            if party.gil < kind.PRICE:
                self._say("Pas assez de gils !", True)
            else:
                party.gil -= kind.PRICE
                party.items.add(kind())
                self._say(f"{kind.name} rejoint le sac ({len(party.items)} objets).")
        self._refresh()
        if not self.list.rows and mode == "sell":
            self.focus = "menu"

    def _leave(self) -> None:
        self.game.audio.play_sfx("cancel")
        if len(self.game.stack) > 1:
            self.game.pop(transition="fade")
        elif "world_map" in SCENES:
            self.game.replace(SCENES["world_map"](self.game, []))

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("shop")

    @override
    def on_back(self) -> None:
        if self.focus == "list":
            self.focus = "menu"
            self.game.audio.play_sfx("cancel")
        else:
            self._leave()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        a = self.game.audio
        if self.focus == "menu":
            before = self.menu.cursor
            chosen = self.menu.handle_event(event)
            if self.menu.cursor != before:
                a.play_sfx("cursor")
                self._refresh()
            if chosen == 3:
                self._leave()
            elif chosen is not None:
                if self.list.rows:
                    self.focus = "list"
                    a.play_sfx("confirm")
                else:
                    a.play_sfx("error")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT and self.list.rows and self.mode != "leave":
                self.focus = "list"
            return
        if is_cancel(event):
            self.on_back()
            return
        res = self.list.handle_event(event)
        if res == -1:
            self._say("Pas assez de gils !", True)
        elif res is not None:
            self._act(res)

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
    def _detail_lines(self) -> list[tuple[str, tuple[int, int, int]]]:
        row = self.list.current()
        mode = self.mode
        if mode == "leave" or row is None:
            return [("Choisissez une action, ou partez quand vous voulez.", theme.TEXT_DIM)]
        idx = self.list.cursor
        if mode == "goods":
            kind = self.shop.goods[idx]
            return [(GOODS_TEXT.get(kind.name, ""), theme.TEXT)]
        item = self.shop.shelf[idx] if mode == "buy" else self.party.bag[idx]
        lines: list[tuple[str, tuple[int, int, int]]] = [(str(item), theme.TEXT)]
        for hero in self.party.heroes:
            after = flow.stats_with(hero, item)
            delta = flow.delta_text(hero.stats, after)
            lines.append((f"{hero.name} : {delta or 'aucun changement'}",
                          theme.HP if delta and not any(c == "-" for c in delta) else (theme.TEXT_DIM if not delta else theme.GOLD)))
        return lines

    @override
    def draw(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        flow.draw_backdrop(surface, assets, "bg_shop", 0.12)
        self.menu.draw(surface, assets, show_cursor=self.focus == "menu")
        # bourse
        draw_window(surface, (30, 250, 290, 76))
        flow.draw_icon(surface, assets, "icon_gil", (68, 288), 40)
        draw_text(surface, f"{self.party.gil}", (290, 288), 30, theme.GOLD, "midright", bold=True)
        # marchand
        draw_window(surface, (30, 346, 290, 344))
        draw_text(surface, self.shop.merchant, (50, 364), 26, theme.GOLD, bold=True)
        for k, line in enumerate(wrap_text(self.quip, 22, 250)):
            draw_text(surface, line, (50, 408 + k * 30), 22)
        self.list.draw(surface, assets, active=self.focus == "list")
        draw_window(surface, (340, 470, 910, 220))
        for k, (text, color) in enumerate(self._detail_lines()[:6]):
            draw_text(surface, text, (366, 490 + k * 32), 22 if k else 24, color if k else theme.TEXT)
        draw_text(surface, "Entrée : valider   Retour arrière : revenir", (790, 704), 16, theme.TEXT_DIM, "center")
        if self.banner:
            self.banner.draw(surface)


@register_scene("shop")
def make_shop(game: Game, args: list[str]) -> Scene:
    """Fabrique : `shop` ou `shop:first` / `shop:second`."""
    return ShopScene(game, args[0] if args else "first")
