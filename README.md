# Disponibilités des bénévoles Emmaüs

Application locale permettant aux bénévoles de déclarer leurs disponibilités pour les
périodes de service du **mardi au samedi**, sans créer de compte : chacun reçoit un lien
personnel sécurisé. Une interface d'administration gère les bénévoles, les liens, les
horaires d'ouverture et le planning hebdomadaire des réponses.

Le planning affiche une colonne par jour, des blocs pour les créneaux horaires et un
bandeau pour les disponibilités « toute la journée ». Les bénévoles sans réponse restent
signalés séparément des jours laissés indisponibles.

La feuille de route fonctionnelle est dans
[`roadmaps/feuille-de-route-initiale.md`](roadmaps/feuille-de-route-initiale.md) et son
suivi de réalisation dans [`roadmaps/version-de-travail.md`](roadmaps/version-de-travail.md).

## Pile technique

| Composant | Technologie |
| --- | --- |
| Base de données | PostgreSQL 16 |
| API | Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL uniquement |
| Interface | React 18, TypeScript, Vite, Tailwind CSS, Lucide React |
| Courriels locaux | MailHog |
| Orchestration | Docker Compose |

## Démarrage rapide

Prérequis : Docker et Docker Compose.

```bash
cp .env.example .env
```

Renseignez dans `.env` :

- `POSTGRES_PASSWORD` : un mot de passe solide ;
- `SECRET_KEY` : 64 caractères aléatoires (`openssl rand -hex 32`) ;
- `ADMIN_EMAIL` et `ADMIN_PASSWORD` : identifiants du premier administrateur, créé au
  premier démarrage si aucun compte n'existe encore. Le mot de passe doit contenir au
  moins 12 caractères ;
- éventuellement `FRONTEND_URL` (par défaut `http://localhost:8080`).

Puis :

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| Interface | http://localhost:8080 |
| Espace bénévole | `http://localhost:8080/b#<jeton>` (lien fourni par l'administration) |
| API et documentation | http://localhost:8000/api/docs |
| MailHog (courriels de test) | http://localhost:8025 |
| PostgreSQL (hôte) | `localhost:5433` |

Le port hôte `5433` évite un conflit avec un PostgreSQL déjà installé sur la machine ;
l'API utilise `db:5432` à l'intérieur du réseau Docker.

Pour arrêter : `docker compose down`. Pour repartir d'une base vide :
`docker compose down -v` (destructif).

Le schéma est créé automatiquement au démarrage de l'API (`create_all`). La V1 ne
contient pas encore de migration Alembic : avant un déploiement avec des données
persistantes, il faudra introduire des migrations versionnées.

## Commandes de validation

### Backend

Les tests nécessitent PostgreSQL (aucun repli SQLite). La base `emmaus_test` est créée
automatiquement par le service `db` au premier démarrage.

```bash
# Dans le conteneur API (recommandé)
docker compose run --rm api sh -c 'TEST_DATABASE_URL="$TEST_DATABASE_URL" pytest'

# Lint
docker compose run --rm api ruff check app tests
```

En local, avec un environnement Python 3.12 et `TEST_DATABASE_URL` pointant vers
`localhost:5433/emmaus_test` :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
TEST_DATABASE_URL="postgresql+psycopg://<user>:<motdepasse>@localhost:5433/emmaus_test" \
  pytest
ruff check app tests
```

### Frontend

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Pour développer l'interface avec rechargement à chaud, en gardant l'API Docker sur le
port `8000` :

```bash
cd frontend
npm run dev
```

Vite sert l'interface sur http://localhost:5173 et relaie `/api` vers l'API. Les liens
générés utilisent alors `FRONTEND_URL` ; pour qu'ils pointent vers le serveur Vite,
définissez `FRONTEND_URL=http://localhost:5173` avant de démarrer l'API.

### Données de démonstration

Pour peupler la base avec des bénévoles fictifs et afficher leurs liens personnels :

```bash
docker compose exec api python -m app.seed_demo
```

Le script remplace uniquement les bénévoles dont l'adresse se termine par
`@demo.emmaus.fr`, puis affiche les liens à ouvrir. Les profils couvrent les cas utiles :
propositions issues de l'historique (Marie), réponses enregistrées et jours clôturés
(Jean), absence totale de réponse (Fatima), semaine suivante entièrement disponible
(Paul), créneaux variés (Karim) et bénévole désactivé dont le lien est refusé (Ancien
Bénévole). Il refuse de s'exécuter si `APP_ENV=production`.

### Test de fumée Docker

Une fois la pile démarrée, le script suivant vérifie l'API, PostgreSQL et MailHog de bout
en bout (connexion administrateur, création d'un bénévole, envoi du lien, réception dans
MailHog) :

```bash
python scripts/smoke_test.py
```

Il lit les identifiants dans `.env` et ne doit être utilisé qu'en local.

## Règles métier implémentées

- Période de service du mardi au samedi ; le bénévole voit la période en cours si elle
  est encore ouverte et les quatre suivantes.
- Un jour reste modifiable jusqu'à 23 h 59 la veille, dans le fuseau `Europe/Paris`.
  Une journée non renseignée dans une période **soumise** vaut « indisponible » ; une
  période **non soumise** est affichée « sans réponse » à l'administration.
- Réponse par jour : vide, toute la journée, ou un seul créneau continu par pas de
  30 minutes, dans les heures d'ouverture configurées.
- Horaires par défaut 08:00–18:00 du mardi au samedi, modifiables sans réécrire les
  réponses existantes.
- Propositions : créneau le plus fréquent parmi les quatre dernières périodes **achevées**
  renseignées, jamais les périodes futures ; jours vides ignorés ; « toute la journée »
  distincte ; créneaux proches si début et fin diffèrent d'au plus 30 minutes ; égalités
  départagées par la réponse la plus récente. Sans historique, aucun préremplissage.
- Lien créé automatiquement, stable lors d'un renvoi, révocable puis régénérable (l'ancien
  lien devient invalide).
- Désactivation : historique conservé, accès au lien refusé. Suppression définitive :
  bénévole, lien et réponses supprimés en cascade.

## Sécurité et données

- Aucun secret n'est versionné ; `.env` est ignoré par Git.
- Mots de passe administrateurs hachés avec Argon2 ; sessions signées (JWT HS256) dans un
  cookie `HttpOnly`, `SameSite=Lax`, invalidées par une réinitialisation de mot de passe.
- Jetons de lien générés avec `secrets.token_urlsafe(32)` (256 bits), stockés sous forme
  d'empreinte SHA-256 et chiffrés (Fernet dérivé de `SECRET_KEY`) pour permettre le renvoi.
  Les jetons sont transmis dans le **fragment** de l'URL puis par en-tête HTTP : ils
  n'apparaissent ni dans les journaux d'accès du serveur ni dans les référents.
- Les routes d'administration vérifient l'authentification côté serveur ; l'accès bénévole
  ne permet de lire et modifier que les données du bénévole associé au jeton.
- Les journaux d'accès Uvicorn sont désactivés dans Compose ; les courriels et erreurs ne
  contiennent jamais de mot de passe ni de jeton.

## Structure

```text
backend/
  app/
    domain/          règles métier pures (périodes, créneaux, propositions)
    routers/         API publique bénévole et API administration
    services/        liens, courriels, vues et persistance
    models.py        modèle SQLAlchemy
    security.py      hachage, jetons, sessions
  tests/             tests unitaires et tests d'API sur PostgreSQL
frontend/
  src/               interface React (parcours bénévole et administration)
docker/initdb/       création de la base de test
scripts/             test de fumée Docker
```

## Hors périmètre de la V1

Déploiement distant et workflows GitHub Actions, rappels automatiques, export des
disponibilités, rôles administratifs multiples, interface multilingue, plusieurs créneaux
par jour et gestion de plusieurs fuseaux horaires.
