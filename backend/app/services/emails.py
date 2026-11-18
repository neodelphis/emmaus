from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """L'acheminement du courriel a échoué."""


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _send(self, *, to: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = formataddr(("Emmaus", self.settings.smtp_from))
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)

        try:
            with smtplib.SMTP(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=self.settings.smtp_timeout_seconds,
            ) as smtp:
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            # Ne jamais journaliser le contenu du message ni l'adresse du destinataire.
            logger.warning("Échec de l'envoi d'un courriel (%s).", type(exc).__name__)
            raise EmailDeliveryError("Le courriel n'a pas pu être envoyé.") from exc

    def send_volunteer_link(self, *, to: str, name: str, link: str) -> None:
        self._send(
            to=to,
            subject="Vos disponibilités Emmaüs",
            text=(
                f"Bonjour {name},\n\n"
                "Voici votre lien personnel pour indiquer vos disponibilités :\n"
                f"{link}\n\n"
                "Ce lien est personnel : ne le transmettez pas. "
                "Si vous pensez l'avoir reçu par erreur, ignorez ce message.\n\n"
                "À bientôt,\nL'équipe Emmaüs"
            ),
        )

    def send_password_reset(self, *, to: str, link: str) -> None:
        self._send(
            to=to,
            subject="Réinitialisation de votre mot de passe Emmaüs",
            text=(
                "Bonjour,\n\n"
                "Une réinitialisation de mot de passe a été demandée pour votre compte "
                "d'administration. Ce lien est valable une heure :\n"
                f"{link}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
                "À bientôt,\nL'équipe Emmaüs"
            ),
        )
