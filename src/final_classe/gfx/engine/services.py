"""Services tolérants : audio et effets, avec repli muet / minimal si leurs modules manquent."""

import sys
from typing import Any


class NullAudio:
    """Audio muet : mêmes méthodes que `gfx.audio.Audio`, ne fait rien (retient la piste demandée)."""

    MUSIC_IDS: tuple[str, ...] = ()
    SFX_IDS: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.music_volume = 0.8
        self.sfx_volume = 0.8
        self.current_music: str | None = None

    def play_sfx(self, name: str, volume: float = 1.0, pan: float = 0.0) -> None:
        """Ne joue rien."""

    def play_music(self, track: str, fade_ms: int = 800) -> None:
        """Retient la piste, sans la jouer."""
        self.current_music = track

    def stop_music(self, fade_ms: int = 800) -> None:
        """Ne fait rien."""
        self.current_music = None

    def duck(self, level: float = 0.35, seconds: float = 1.0) -> None:
        """Ne fait rien."""

    def update(self, dt: float) -> None:
        """Ne fait rien."""


class FallbackFxManager:
    """FxManager minimal : même surface d'appel que le vrai, effets dessinés par calques."""

    LAYERS = ("back", "front", "overlay")

    def __init__(self) -> None:
        self.effects: list[Any] = []
        self.shake_offset: tuple[float, float] = (0.0, 0.0)
        self.hide_ui = False

    def add(self, effect: Any, layer: str | None = None, tag: str | None = None) -> Any:
        """Ajoute un effet (`update(dt) -> bool`, `draw(surface, layer)`)."""
        if layer:
            effect.layer = layer
        if tag:
            effect.tag = tag
        self.effects.append(effect)
        return effect

    play = add

    def clear(self) -> None:
        """Retire tous les effets."""
        self.effects.clear()
        self.hide_ui = False

    def kill(self, tag: str) -> None:
        """Termine les effets portant ce tag."""
        for fx in self.effects:
            if getattr(fx, "tag", None) == tag:
                fx.dead = True

    @property
    def busy(self) -> bool:
        """Des effets sont encore actifs."""
        return any(not getattr(fx, "dead", False) for fx in self.effects)

    def update(self, dt: float) -> None:
        """Met à jour les effets et retire ceux qui sont finis."""
        self.effects = [
            fx for fx in self.effects if not getattr(fx, "dead", False) and fx.update(dt)
        ]

    def draw(self, surface: Any, layer: str) -> None:
        """Dessine les effets d'un calque."""
        for fx in self.effects:
            fx.draw(surface, layer)

    def abandon(self, effects: list[Any]) -> None:
        """Reprise après panne du vrai FxManager : ses effets en cours sont déclarés terminés."""
        for fx in effects:
            fx.dead = True
            fx.done = True

    # raccourcis du vrai FxManager : sans effet ici (ne bloquent jamais)
    def burst(self, *args: Any, **kwargs: Any) -> None:
        """Sans effet."""

    emitter = text = shake = flash = tint = ring = burst


def make_audio() -> Any:
    """`final_classe.gfx.audio.Audio()` si disponible, sinon `NullAudio`."""
    try:
        from final_classe.gfx.audio import Audio

        return Audio()
    except Exception as error:  # module absent, incomplet ou mixer en panne
        if not isinstance(error, ImportError):
            print(f"[audio] indisponible : {error!r}", file=sys.stderr)
        return NullAudio()


def make_fx() -> Any:
    """`final_classe.gfx.fx.FxManager()` si disponible, sinon `FallbackFxManager`."""
    try:
        from final_classe.gfx.fx import FxManager

        return FxManager()
    except Exception as error:
        if not isinstance(error, ImportError):
            print(f"[fx] indisponible : {error!r}", file=sys.stderr)
        return FallbackFxManager()
