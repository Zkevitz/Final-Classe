"""Version pygame de Final Classe. Point d'entrée : `final-classe-gfx` ou `python -m final_classe.gfx`."""


def main(argv: list[str] | None = None) -> None:
    """Lance le jeu (voir docs/ARCHITECTURE-GFX.md §5 pour les options du mode sans fenêtre)."""
    from final_classe.gfx.engine.runner import run_cli

    code = run_cli(argv)
    if code:
        raise SystemExit(code)
