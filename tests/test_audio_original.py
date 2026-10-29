"""Fichiers officiels `original/` : joués via mixer.music ; illisibles -> repli WAV, jamais d'exception."""

import wave

import pygame
import pytest

from final_classe.gfx import audio as audio_mod


def _wav(path, seconds=0.2):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 2 * int(44100 * seconds))


@pytest.fixture
def audio(game, monkeypatch, tmp_path):
    root = tmp_path / "audio"
    monkeypatch.setattr(audio_mod, "AUDIO_DIR", root)
    a = audio_mod.Audio()
    if a._pg is None:
        pytest.skip("mixer indisponible")
    return a, root


def test_fichier_original_joue_via_mixer_music(audio, monkeypatch):
    a, root = audio
    _wav(root / "original" / "victory.wav")
    loaded: list[str] = []
    played: list[dict] = []
    monkeypatch.setattr(pygame.mixer.music, "load", lambda p: loaded.append(p))
    monkeypatch.setattr(pygame.mixer.music, "play", lambda **kw: played.append(kw))
    a.play_music("victory", fade_ms=0)
    assert len(loaded) == 1 and loaded[0].endswith("victory.wav")
    assert played and played[0]["loops"] == 0  # victory ne boucle pas
    assert a._streaming is True and a.current_music == "victory"


def test_fichier_original_reel_jouable_sans_exception(audio):
    a, root = audio
    _wav(root / "original" / "title.wav")
    a.play_music("title", fade_ms=0)
    assert a._streaming is True
    a.stop_music(0)


def test_fichier_illisible_replie_sur_le_wav(audio):
    a, root = audio
    (root / "original").mkdir(parents=True)
    (root / "original" / "title.wav").write_bytes(b"ceci n'est pas un wav")
    _wav(root / "music" / "title.wav")
    a.play_music("title", fade_ms=0)  # ne doit pas lever
    assert a._streaming is False
    assert a.current_music == "title"
    a.stop_music(0)


def test_fichier_illisible_et_aucun_wav_reste_muet(audio):
    a, root = audio
    (root / "original").mkdir(parents=True)
    (root / "original" / "title.wav").write_bytes(b"\x00\x01")
    a.play_music("title", fade_ms=0)
    a.play_sfx("slash")  # aucun fichier : silence
    a.duck(0.3, 0.1)
    a.update(0.2)


def test_mixer_music_qui_leve_ne_propage_rien(audio, monkeypatch):
    a, root = audio
    _wav(root / "original" / "title.wav")
    _wav(root / "music" / "title.wav")

    def boom(*args, **kwargs):
        raise pygame.error("illisible")

    monkeypatch.setattr(pygame.mixer.music, "load", boom)
    a.play_music("title", fade_ms=0)  # repli sur le WAV rendu
    assert a._streaming is False and a.current_music == "title"


def test_changer_de_musique_pendant_un_flux_ne_bloque_pas(audio, monkeypatch):
    import time

    a, root = audio
    _wav(root / "original" / "title.wav", 2.0)
    _wav(root / "original" / "boss.wav", 2.0)
    monkeypatch.setattr(pygame.mixer.music, "fadeout", lambda ms: pytest.fail("fadeout bloquant appelé"))
    a.play_music("title", fade_ms=800)
    assert a._streaming is True
    start = time.perf_counter()
    a.play_music("boss", fade_ms=800)
    assert time.perf_counter() - start < 0.05
    a.stop_music(800)  # idem pour l'arrêt
    assert a.current_music is None


# --- la boucle du moteur appelle audio.update à chaque image ----------------------------------
class SpyAudio:
    def __init__(self):
        self.updates: list[float] = []

    def update(self, dt):
        self.updates.append(dt)

    def play_music(self, *a, **k):
        pass

    play_sfx = stop_music = duck = play_music


def test_la_boucle_appelle_audio_update_a_chaque_image(game):
    game.audio = SpyAudio()
    for _ in range(5):
        game.step(1 / 60, render=False)
    assert game.audio.updates == [1 / 60] * 5


def test_changement_de_flux_lance_la_piste_en_attente_via_la_boucle(game, audio, monkeypatch):
    a, root = audio
    _wav(root / "original" / "title.wav", 2.0)
    _wav(root / "original" / "boss.wav", 2.0)
    loaded: list[str] = []
    real_load = pygame.mixer.music.load

    def spy(path, *args):
        loaded.append(path)
        return real_load(path, *args)

    monkeypatch.setattr(pygame.mixer.music, "load", spy)
    game.audio = a
    a.play_music("title", fade_ms=0)
    a.play_music("boss", fade_ms=400)  # le flux title s'éteint, boss attend
    assert not any(p.endswith("boss.wav") for p in loaded)
    for _ in range(90):  # 1,5 s de boucle moteur
        game.step(1 / 60, render=False)
    assert any(p.endswith("boss.wav") for p in loaded)
    assert a._streaming is True and a.current_music == "boss"
    a.stop_music(0)


def test_meta_boucle_sans_audio_update(game, audio, monkeypatch):
    from final_classe.gfx.engine.game import Game

    monkeypatch.setattr(Game, "update", lambda self, dt: None)
    with pytest.raises(AssertionError):
        test_la_boucle_appelle_audio_update_a_chaque_image(game)
