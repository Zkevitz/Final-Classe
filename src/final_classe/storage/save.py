"""La sauvegarde : l'équipe et la progression, dans un fichier JSON."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from final_classe.characters import Party
from final_classe.storage.errors import SaveError

SAVES = Path("sauvegardes")  # le dossier, là où l'on lance le jeu
SLOTS = 3  # bonus ★ 2 : trois emplacements
VERSION = 1  # bonus ★★ 3 : le format du fichier


def slot_path(slot: int) -> Path:
    """Bonus ★ 2 : le fichier d'un emplacement."""
    return SAVES / f"partie-{slot}.json"


def save_game(party: Party, zone: int, wave: int = 0, slot: int = 1) -> None:
    """Écrit la partie : la zone et la vague où reprendre, puis l'équipe."""
    data = {
        "version": VERSION,  # bonus ★★ 3
        "date": datetime.now().isoformat(sep=" ", timespec="minutes"),  # bonus ★ 1
        "zone": zone,
        "wave": wave,  # bonus ★★ 4
        "party": party.to_dict(),
    }
    SAVES.mkdir(exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    slot_path(slot).write_text(text, encoding="utf-8")


def peek(slot: int = 1) -> dict[str, Any]:
    """Le contenu d'une sauvegarde, sans recréer l'équipe ; SaveError si on ne peut pas la lire."""
    path = slot_path(slot)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SaveError(f"Aucune sauvegarde dans l'emplacement {slot}.") from error
    except json.JSONDecodeError as error:  # une ValueError : le fichier n'est pas du JSON
        raise SaveError(f"La sauvegarde {path.name} est abîmée.") from error
    if data.get("version") != VERSION:  # bonus ★★ 3
        raise SaveError(f"La sauvegarde {path.name} vient d'une autre version du jeu.")
    if not {"date", "zone", "wave", "party"} <= data.keys():
        raise SaveError(f"La sauvegarde {path.name} est incomplète.")
    return data


def load_game(slot: int = 1) -> tuple[Party, int, int]:
    """Relit la partie : l'équipe, la zone et la vague où reprendre."""
    data = peek(slot)
    try:
        return Party.from_dict(data["party"]), data["zone"], data["wave"]
    except (KeyError, ValueError, TypeError) as error:  # une clé manque, un job inconnu…
        raise SaveError(f"La sauvegarde {slot_path(slot).name} est incomplète.") from error
