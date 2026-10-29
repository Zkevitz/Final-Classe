"""Moteur de la version pygame : boucle, pile de scènes, assets, registre des scènes.

API pour écrire une scène (un fichier dans `gfx/scenes/`) ::

    from final_classe.gfx.engine import Game, Scene, register_scene

    class ShopScene(Scene):
        def __init__(self, game: Game) -> None:
            super().__init__(game)          # self.game.assets / .audio / .fx / .party
        def on_enter(self): self.game.audio.play_music("shop")
        def handle_event(self, event): ...   # souris déjà en coordonnées logiques
        def update(self, dt): ...            # dt en secondes
        def draw(self, surface): ...         # surface logique 1280x720
        def on_back(self): ...               # Échap (défaut : pop si la pile a > 1 scène)

    @register_scene("shop")                  # nom utilisé par --scene et par SCENES
    def make_shop(game: Game, args: list[str]) -> Scene:   # "shop:x:y" -> args == ["x", "y"]
        return ShopScene(game)

Le module doit être listé dans `scenes/__init__.py` (MODULES). Navigation : `game.push(scene)`,
`game.pop()`, `game.replace(scene, transition="fade")`, `game.replace_all(scene)`, avec
`transition=None` pour un changement immédiat. Pour aller vers une autre scène par nom :
`SCENES["world_map"](game, [])` (tester `"world_map" in SCENES`, les scènes arrivent au fur et à mesure).

État partagé : `game.party` (Party), `game.slot`, `game.zone`, `game.wave`, `game.save()`,
`game.load(slot)`, `game.demo`, `game.force_action` (mode sans fenêtre). Services :
`game.assets` (`image`, `scaled`, `draw_sprite(surface, id, pieds, scale, flip, alpha, scale_y)`,
`exists`, `is_floating`, `facing`), `game.audio` (API de docs/AUDIO.md, muet si absent),
`game.fx` (FxManager ; le jeu dessine seul le calque « overlay », la scène dessine « back » et
« front »). Une scène `transparent = True` laisse voir la scène du dessous (fenêtre modale).
`make_demo_party()` (engine/demo.py) fournit une partie de 3 héros pour les tests.
"""

from final_classe.gfx.engine.assets import Assets
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, SceneFactory, register_scene
from final_classe.gfx.engine.scene import Scene

__all__ = [
    "SCENES", "Assets", "Game", "Scene", "SceneFactory", "make_demo_party", "register_scene",
]
