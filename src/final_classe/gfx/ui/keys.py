"""Aides d'entrée : touches de confirmation et de navigation."""

import pygame

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z)
CANCEL_KEYS = (pygame.K_BACKSPACE, pygame.K_x)


def is_confirm(event: pygame.event.Event) -> bool:
    """Entrée, Espace ou Z."""
    return event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS


def is_cancel(event: pygame.event.Event) -> bool:
    """Retour arrière ou X (Échap passe par `Scene.on_back`)."""
    return event.type == pygame.KEYDOWN and event.key in CANCEL_KEYS


def nav(event: pygame.event.Event) -> tuple[int, int]:
    """Direction pressée (dx, dy) : flèches ou ZQSD/WASD ; (0, 0) sinon."""
    if event.type != pygame.KEYDOWN:
        return (0, 0)
    table = {
        pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
        pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
        pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_q: (-1, 0),
        pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
    }
    return table.get(event.key, (0, 0))
