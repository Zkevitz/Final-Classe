"""Les erreurs du stockage."""


class SaveError(Exception):
    """Une sauvegarde absente, abîmée ou incomplète : le jeu l'attrape, et explique."""
