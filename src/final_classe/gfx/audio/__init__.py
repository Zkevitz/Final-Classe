"""Audio du jeu : lecture des musiques et bruitages rendus dans assets/audio/ (jamais d'exception)."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("final_classe.audio")

AUDIO_DIR = Path(__file__).resolve().parents[4] / "assets" / "audio"

MUSIC_IDS = ("title", "prologue", "world_map", "battle", "boss", "final_boss", "victory", "victory_loop",
             "shop", "ending", "game_over")
ORIGINAL_EXTS = ("ogg", "mp3", "flac", "wav")
NON_LOOPING = ("victory", "game_over")

SFX_IDS = (
    "cursor", "confirm", "cancel", "error", "menu_open", "text_blip", "save", "buy", "transition",
    "slash", "slash_heavy", "staff_hit", "impact", "punch", "dagger", "katana_draw", "wind_slash", "arrow",
    "arrow_power", "shuriken", "claw", "crit",
    "cast", "charge", "charge_big", "fire", "fire_pillar", "ice_form", "ice_shatter", "thunder", "thunder_big",
    "heal", "chakra", "armor_break", "coins",
    "summon", "roar", "explosion", "mega_flare",
    "potion", "elixir", "revive", "defend", "ko_monster", "ko_hero", "level_up",
    "supernova", "needles", "poison_gas", "flame_breath",
)


PRELOAD_SFX = ("cursor", "confirm", "cancel", "error", "menu_open", "text_blip", "transition", "slash", "slash_heavy",
               "staff_hit", "impact", "punch", "crit", "cast", "charge", "fire", "ice_form", "thunder", "heal",
               "potion", "defend", "ko_monster", "ko_hero", "level_up", "coins")


class Audio:
    """Service audio : muet sans erreur si le mixer ou un fichier manque."""

    def __init__(self, enabled: bool = True) -> None:
        self._music_volume = 0.7
        self._sfx_volume = 0.8
        self._pg = None
        self._sounds: dict[tuple[str, str], object] = {}
        self._missing: set[tuple[str, str]] = set()
        self._current: str | None = None
        self._channels: list = []
        self._cur_idx = 0
        self._duck = 1.0
        self._duck_left = 0.0
        self._streaming = False  # musique officielle jouée via pygame.mixer.music
        self._fade = [0.0, 0.0]  # [reste, total] du fondu de sortie du flux (non bloquant)
        self._pending = None     # (piste, fade_ms) : flux à lancer quand le précédent a fini de s'éteindre
        if not enabled:
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(2)
            self._channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self._pg = pygame
        except Exception as exc:  # pas de carte son, mixer absent...
            log.warning("audio désactivé : %s", exc)
            self._pg = None

    # ----------------------------------------------------------- volumes
    @property
    def music_volume(self) -> float:
        return self._music_volume

    @music_volume.setter
    def music_volume(self, v: float) -> None:
        self._music_volume = max(0.0, min(1.0, float(v)))
        self._apply_music_volume()

    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, v: float) -> None:
        self._sfx_volume = max(0.0, min(1.0, float(v)))

    def _apply_music_volume(self) -> None:
        try:
            if self._pg and self._current is not None:
                v = self._music_volume * self._duck
                if self._streaming:
                    self._pg.mixer.music.set_volume(v)
                else:
                    self._channels[self._cur_idx].set_volume(v)
        except Exception:
            pass

    # ------------------------------------------------------------ chargement
    @staticmethod
    def _candidates(kind: str, name: str) -> list:
        """Fichier rendu (les originaux de `original/` sont lus en streaming par `_play_stream`)."""
        out = []
        p = AUDIO_DIR / kind / f"{name}.wav"
        if p.is_file():
            out.append(p)
        return out

    def _load(self, kind: str, name: str):
        key = (kind, name)
        if key in self._sounds:
            return self._sounds[key]
        snd = None
        try:
            for path in self._candidates(kind, name):
                try:
                    snd = self._pg.mixer.Sound(str(path))
                    break
                except Exception as exc:  # fichier officiel illisible : on passe au suivant
                    log.warning("lecture impossible de %s : %s", path.name, exc)
            if snd is None and key not in self._missing:
                log.warning("fichier audio absent : %s/%s", kind, name)
        except Exception as exc:
            if key not in self._missing:
                log.warning("chargement impossible de %s : %s", name, exc)
        if snd is None:
            self._missing.add(key)
        self._sounds[key] = snd
        return snd

    # ------------------------------------------------------------------- API
    def play_sfx(self, name: str, volume: float = 1.0, pan: float = 0.0) -> None:
        """Joue un bruitage ; pan de -1 (gauche) à 1 (droite)."""
        try:
            if not self._pg or name not in SFX_IDS:
                return
            snd = self._load("sfx", name)
            if snd is None:
                return
            ch = snd.play()
            if ch is None:
                return
            v = max(0.0, volume) * self._sfx_volume
            pan = max(-1.0, min(1.0, pan))
            ch.set_volume(v * (1.0 - max(0.0, pan)), v * (1.0 - max(0.0, -pan)))
        except Exception:
            pass

    def _stop_current(self, fade_ms: int) -> None:
        """Éteint en fondu la musique en cours. Pour un flux, le fondu est piloté par `update` : mixer.music.fadeout
        ne bloque pas lui-même, mais le `load` suivant attend la fin du fondu (mesuré), d'où ce fondu manuel."""
        self._pending = None
        if self._streaming:
            self._streaming = False
            if fade_ms <= 0:
                self._pg.mixer.music.stop()
                self._fade = [0.0, 0.0]
            else:
                self._fade = [fade_ms / 1000.0, fade_ms / 1000.0]
        else:
            self._channels[self._cur_idx].fadeout(fade_ms)

    def _tick_fade(self, dt: float) -> None:
        """Avance le fondu de sortie du flux, puis lance le flux en attente."""
        if self._fade[0] > 0.0:
            self._fade[0] -= dt
            if self._fade[0] <= 0.0:
                self._fade = [0.0, 0.0]
                self._pg.mixer.music.stop()
            else:
                self._pg.mixer.music.set_volume(self._music_volume * self._duck * self._fade[0] / self._fade[1])
        if self._fade[0] <= 0.0 and self._pending is not None:
            track, fade_ms = self._pending
            self._pending = None
            if self._current == track and self._play_stream(track, fade_ms):
                self._streaming = True
            elif self._current == track:
                self._play_wav(track, fade_ms)

    def _play_stream(self, track: str, fade_ms: int) -> bool:
        """Joue le fichier officiel `original/<id>.*` en streaming ; False s'il n'y en a pas (ou illisible)."""
        for ext in ORIGINAL_EXTS:
            path = AUDIO_DIR / "original" / f"{track}.{ext}"
            if not path.is_file():
                continue
            try:
                m = self._pg.mixer.music
                m.load(str(path))
                m.set_volume(self._music_volume * self._duck)
                m.play(loops=0 if track in NON_LOOPING else -1, fade_ms=fade_ms)
                return True
            except Exception as exc:
                log.warning("lecture impossible de %s : %s", path.name, exc)
        return False

    def play_music(self, track: str, fade_ms: int = 800) -> None:
        """Enchaîne en fondu vers la musique `track` ; ne fait rien si c'est déjà la piste en cours."""
        try:
            if not self._pg or track not in MUSIC_IDS or track == self._current:
                return
            fade_ms = max(0, int(fade_ms))
            self._stop_current(fade_ms)
            self._current = track
            if self._has_original(track):
                if self._fade[0] > 0.0:  # un flux s'éteint encore : on attend la fin du fondu (update)
                    self._pending = (track, fade_ms)
                    return
                if self._play_stream(track, fade_ms):
                    self._streaming = True
                    return
            self._play_wav(track, fade_ms)
        except Exception:
            pass

    @staticmethod
    def _has_original(track: str) -> bool:
        return any((AUDIO_DIR / "original" / f"{track}.{e}").is_file() for e in ORIGINAL_EXTS)

    def _play_wav(self, track: str, fade_ms: int) -> None:
        """Joue le WAV rendu sur le canal de musique (muet si absent)."""
        self._cur_idx = 1 - self._cur_idx
        snd = self._load("music", track)
        if snd is None:
            return
        ch = self._channels[self._cur_idx]
        ch.set_volume(self._music_volume * self._duck)
        ch.play(snd, loops=0 if track in NON_LOOPING else -1, fade_ms=fade_ms)

    def stop_music(self, fade_ms: int = 800) -> None:
        try:
            if self._pg:
                self._stop_current(max(0, int(fade_ms)))
            self._current = None
        except Exception:
            pass

    def duck(self, level: float = 0.35, seconds: float = 1.0) -> None:
        """Baisse la musique à `level` pendant `seconds` secondes (décompte dans update)."""
        try:
            if not self._pg:
                return
            self._duck = max(0.0, min(1.0, level))
            self._duck_left = max(0.0, float(seconds))
            self._apply_music_volume()
        except Exception:
            pass

    def update(self, dt: float) -> None:
        """À appeler à chaque image : fait expirer le duck (thread principal uniquement)."""
        try:
            if self._pg:
                self._tick_fade(dt)
            if self._duck_left > 0.0:
                self._duck_left -= dt
                if self._duck_left <= 0.0:
                    self._duck_left = 0.0
                    self._duck = 1.0
                    self._apply_music_volume()
        except Exception:
            pass

    @property
    def available(self) -> bool:
        """Vrai si le mixer fonctionne."""
        return self._pg is not None

    def preload(self) -> None:
        """Charge à l'avance les bruitages courants et la musique de combat (ne plante jamais)."""
        try:
            if not self._pg:
                return
            for name in PRELOAD_SFX:
                self._load("sfx", name)
            self._load("music", "battle")
        except Exception:
            pass

    @property
    def current_music(self) -> str | None:
        return self._current


__all__ = ["Audio", "MUSIC_IDS", "SFX_IDS", "AUDIO_DIR"]
