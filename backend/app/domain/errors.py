from __future__ import annotations


class DomainError(Exception):
    """Erreur métier dont le message est destiné à l'utilisateur, en français."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
