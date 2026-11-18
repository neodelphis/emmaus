#!/usr/bin/env python3
"""Test de fumée de la pile Docker locale.

Vérifie l'API, PostgreSQL, MailHog et l'interface servie par Nginx :
connexion administrateur, création d'un bénévole, lien personnel,
enregistrement d'une disponibilité, envoi du lien et réception dans MailHog.

Usage : python scripts/smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_URL = os.environ.get("API_URL", "http://localhost:8000")
WEB_URL = os.environ.get("WEB_URL", "http://localhost:8080")
MAILHOG_URL = os.environ.get("MAILHOG_URL", "http://localhost:8025")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise SystemExit("Fichier .env introuvable. Copiez .env.example vers .env.")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


class Client:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def request(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, object]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with self.opener.open(request, timeout=20) as response:
                content = response.read().decode("utf-8")
                return response.status, json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {url} → HTTP {error.code} : {detail}") from error

    def get(self, url: str, headers: dict[str, str] | None = None):
        return self.request("GET", url, headers=headers)

    def post(self, url: str, payload: dict | None = None):
        return self.request("POST", url, payload)

    def put(self, url: str, payload: dict, headers: dict[str, str] | None = None):
        return self.request("PUT", url, payload, headers)

    def delete(self, url: str):
        return self.request("DELETE", url)


def wait_for_mailhog(client: Client, email: str, token: str) -> None:
    query = urllib.parse.quote(email)
    for _ in range(20):
        _, data = client.get(f"{MAILHOG_URL}/api/v2/search?kind=to&query={query}")
        items = (data or {}).get("items") or []
        for item in items:
            body = item.get("Content", {}).get("Body", "")
            if token in body:
                return
        time.sleep(0.5)
    raise RuntimeError("Le courriel contenant le lien n'a pas été trouvé dans MailHog.")


def main() -> int:
    env = load_env()
    client = Client()
    volunteer_id: str | None = None

    try:
        print("1. Connexion administrateur…")
        client.post(
            f"{API_URL}/api/admin/auth/login",
            {"email": env["ADMIN_EMAIL"], "password": env["ADMIN_PASSWORD"]},
        )

        suffix = uuid.uuid4().hex[:8]
        email = f"smoke-{suffix}@example.com"
        print(f"2. Création du bénévole de test ({email})…")
        _, volunteer = client.post(
            f"{API_URL}/api/admin/volunteers",
            {"name": f"Test Fumée {suffix}", "email": email},
        )
        volunteer_id = volunteer["id"]
        token = volunteer["link"].split("#", 1)[1]

        print("3. Lecture de l'espace bénévole…")
        _, access = client.get(
            f"{API_URL}/api/volunteer", headers={"X-Volunteer-Token": token}
        )
        periods = access["periods"]
        if len(periods) < 1 or len(access["opening_hours"]) != 5:
            raise RuntimeError("Les périodes ou horaires renvoyés sont incomplets.")
        period = periods[0]
        editable = [day for day in period["days"] if day["editable"]]
        if not editable:
            raise RuntimeError("Aucun jour modifiable dans la première période.")

        print("4. Enregistrement d'une disponibilité…")
        client.put(
            f"{API_URL}/api/volunteer/periods/{period['start']}",
            {"days": [{"date": editable[0]["date"], "kind": "all_day"}]},
            headers={"X-Volunteer-Token": token},
        )

        print("5. Vérification de la vue administration…")
        _, week = client.get(
            f"{API_URL}/api/admin/week?period_start={period['start']}"
        )
        row = next((item for item in week["volunteers"] if item["id"] == volunteer_id), None)
        if row is None or not row["submitted"]:
            raise RuntimeError("La réponse n'apparaît pas dans la vue de la semaine.")

        print("6. Envoi du lien et réception dans MailHog…")
        client.post(f"{API_URL}/api/admin/volunteers/{volunteer_id}/link/send")
        wait_for_mailhog(client, email, token)

        print("7. Vérification de l'interface servie par Nginx…")
        with urllib.request.urlopen(f"{WEB_URL}/", timeout=20) as response:
            html = response.read().decode("utf-8")
        if 'id="root"' not in html:
            raise RuntimeError("L'interface ne répond pas correctement.")

        print("8. Nettoyage du bénévole de test…")
        client.delete(f"{API_URL}/api/admin/volunteers/{volunteer_id}")
        volunteer_id = None

        print("\nTest de fumée réussi : API, PostgreSQL, MailHog et interface sont opérationnels.")
        return 0
    except (RuntimeError, KeyError, urllib.error.URLError) as error:
        print(f"\nÉchec du test de fumée : {error}", file=sys.stderr)
        return 1
    finally:
        if volunteer_id:
            try:
                client.delete(f"{API_URL}/api/admin/volunteers/{volunteer_id}")
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
