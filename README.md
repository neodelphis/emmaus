# Disponibilités des bénévoles Emmaüs

Application locale permettant aux bénévoles de déclarer leurs disponibilités pour les
périodes de service du **mardi au samedi**, sans créer de compte : chacun reçoit un lien
personnel sécurisé. L'association intervient sur deux sites, **Vairé** et **Les Essarts**.
Chaque site possède son propre planning et ses propres horaires d'ouverture.

Le planning affiche une colonne par jour avec deux listes, **Matin** et **Après-midi**,
un créneau **Repas** et les horaires de chacun. Les disponibilités « toute la journée »
apparaissent sur fond vert dans les deux listes et sont inscrites par défaut au repas de
12:30–13:30. Seuls les bénévoles ayant répondu avec une disponibilité apparaissent dans
cette vue : les bénévoles sans réponse n'y sont plus signalés. L'administration reprend
par défaut le dernier site qu'elle a consulté.

L'espace personnel du bénévole ne montre que les jours encore modifiables. Les choix
sont sur une ligne en trois colonnes : **Toute la journée** à gauche, **Matin / Après-midi**
empilés au centre, **Indisponible** à droite. Les horaires des demi-journées sont
préremplis et ajustables.

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

Le fichier `.env.example` commente chaque variable. Renseignez dans `.env` :

- `POSTGRES_PASSWORD` : un mot de passe solide ;
- `SECRET_KEY` : 64 caractères aléatoires (`openssl rand -hex 32`) ;
- `ADMIN_EMAIL` et `ADMIN_PASSWORD` : identifiants du premier administrateur, créé au
  premier démarrage si aucun compte n'existe encore. Le mot de passe doit contenir au
  moins 12 caractères ;
- `ADMIN_GENDER` : `homme` ou `femme`, utilisé pour le libellé « Connecté » ou
  « Connectée » du premier compte ;
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
Bénévole). Les profils sont répartis entre Vairé et Les Essarts, et certains jours
illustrent l'intervention sur l'autre site. Il refuse de s'exécuter si
`APP_ENV=production`.

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
- Deux sites : Vairé et Les Essarts. Chaque bénévole a un site d'affectation par défaut
  et peut choisir l'autre site pour une journée donnée. Une seule disponibilité et un
  seul site sont possibles par jour.
- Réponse par jour : vide, toute la journée, ou **Matin / Après-midi**. Chaque demi-journée
  préremplit un créneau continu (08:00–12:00 ou 14:00–18:00, adapté aux horaires du site),
  que le bénévole peut ajuster par pas de 30 minutes. Les jours clôturés ne sont pas
  affichés dans son espace personnel.
- Horaires par défaut 08:00–18:00 du mardi au samedi, propres à chaque site et modifiables
  sans réécrire les réponses existantes.
- Propositions : créneau le plus fréquent parmi les quatre dernières périodes **achevées**
  renseignées, jamais les périodes futures ; jours vides ignorés ; « toute la journée »
  distincte ; créneaux proches si début et fin diffèrent d'au plus 30 minutes ; égalités
  départagées par la réponse la plus récente. Sans historique, aucun préremplissage.
- Lien créé automatiquement, stable lors d'un renvoi, révocable puis régénérable (l'ancien
  lien devient invalide).
- Désactivation : historique conservé, accès au lien refusé. Suppression définitive :
  bénévole, lien et réponses supprimés en cascade.
- Repas de midi (12:30–13:30) : les bénévoles disponibles toute la journée y sont inscrits
  par défaut. L'administration peut les retirer avec confirmation et les réinscrire ; les
  bénévoles ayant seulement un créneau ne sont pas inscrits automatiquement.

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
- Le genre du compte administrateur (`homme` ou `femme`) est stocké sur le compte, requis
  à la création et modifiable dans la page Compte ; il détermine le libellé « Connecté »
  ou « Connectée ».
- Le genre des bénévoles est renseigné dans le formulaire d'administration et stocké sur
  la fiche. Les fiches existantes sans genre portent le badge « Genre à renseigner ».
- Le site d'affectation par défaut est stocké sur la fiche bénévole. Le site choisi pour
  chaque disponibilité est conservé séparément ; le planning administrateur et les repas
  sont filtrés par site.
- Les journaux d'accès Uvicorn sont désactivés dans Compose ; les courriels et erreurs ne
  contiennent jamais de mot de passe ni de jeton.

## Workflow Git

`main` est la branche stable et ne reçoit jamais de commit direct. Toute modification,
même documentaire, passe par une branche dédiée puis une pull request :

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/nom-court

# ... modifications, tests et commits ...

git push -u origin feat/nom-court
gh pr create --base main --head feat/nom-court
```

Après validation de la pull request, la fusion se fait en squash et la branche est
supprimée :

```bash
gh pr merge --squash --delete-branch
git switch main
git pull --ff-only origin main
```

Conventions de nommage : `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`.
Le dépôt distant est [neodelphis/emmaus](https://github.com/neodelphis/emmaus). Le
modèle de pull request rappelle les vérifications à effectuer.

## Dépannage navigateur (Firefox)

La politique de sécurité du contenu (CSP) est volontairement stricte : l'application ne
charge qu'un script externe et n'utilise ni `eval`, ni script intégré, ni URL `file://`.
Si Firefox affiche un message du type « script intégré bloqué (`sandbox eval`) » ou
« ne peut pas charger de données vers `file:///` », il s'agit d'une **extension du
navigateur** (React DevTools, gestionnaire de mots de passe, traducteur, bloqueur de
publicités, etc.) qui tente d'injecter du code ou d'accéder à un fichier local.

Plusieurs bloqueurs de publicités actifs simultanément sont une cause fréquente. Pour
le vérifier : ouvrir Firefox en **mode de dépannage** (menu Aide → Mode de dépannage),
désactiver les extensions une par une, ou ajouter `http://localhost:8080` à la liste
d'autorisation du bloqueur, puis recharger la page. Un test de l'administration dans un
Firefox sans extension ne produit aucun message de ce type. Il ne faut pas ajouter
`'unsafe-inline'` à la CSP pour faire taire ces avertissements : cela affaiblirait la
sécurité de l'application.

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
