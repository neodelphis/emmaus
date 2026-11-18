# Consignes pour les agents de code

## Contexte du projet

Cette application Emmaüs permet aux bénévoles de déclarer leurs disponibilités pour des périodes de service du mardi au samedi. Avant toute modification fonctionnelle, consulter la feuille de route dans [`roadmaps/version-de-travail.md`](roadmaps/version-de-travail.md) et respecter ses règles métier.

La V1 reste développée et testée localement avec Docker Compose, PostgreSQL, FastAPI, React/Vite et MailHog. Un déploiement staging est préparé via GitHub Actions, GHCR et Traefik (voir `docs/DEPLOYMENT_STAGING.md`) ; la production et les workflows de release ne font pas partie de ce périmètre.

## Règles métier à préserver

- Les bénévoles n’ont pas de compte ; ils accèdent à leurs seules données par un lien personnel sécurisé.
- Les périodes de service vont du mardi au samedi. Le bénévole peut renseigner la période en cours si elle est encore ouverte et les quatre suivantes.
- Pour chaque jour, une réponse vide signifie indisponible ; une journée sans soumission reste distincte et doit apparaître comme « sans réponse » côté administration.
- Une disponibilité quotidienne est soit vide, soit toute la journée, soit un créneau continu unique. Les heures personnalisées suivent un pas de 30 minutes et les bornes d’ouverture configurées.
- L’interface bénévole n’affiche que les jours encore modifiables. Les choix apparaissent sur une ligne en trois colonnes : **Toute la journée** à gauche, **Matin** et **Après-midi** empilés au centre, **Indisponible** à droite. Les demi-journées ont des horaires préremplis ajustables, au lieu d’un créneau libre. La sélection des périodes affiche deux semaines à la fois, avec des chevrons pour parcourir les suivantes et revenir en arrière.
- L’association intervient sur deux sites : **Vairé** (`vaire`) et **Les Essarts** (`les-essarts`). Chaque bénévole a un site d’affectation par défaut ; il peut choisir l’autre site pour une journée, mais une seule disponibilité et un seul site sont possibles par jour. Le sélecteur de site est visible sur chaque jour modifiable, y compris tant que la journée est sur « Indisponible », et il est présélectionné sur le site par défaut du bénévole.
- Les heures d’ouverture initiales sont 08:00-18:00 pour chaque site et chaque jour, modifiables par l’administration. Une modification ne réécrit pas les réponses déjà enregistrées.
- Le planning et les horaires sont propres à chaque site. L’administration reprend par défaut le dernier site qu’elle a consulté.
- La modification d’un jour ferme à 23 h 59 la veille, dans le fuseau `Europe/Paris`.
- Les propositions réutilisent les quatre dernières périodes passées renseignées, jamais les déclarations futures. Les jours vides sont ignorés ; toute la journée est distincte des créneaux. Deux créneaux sont proches si leurs bornes de début et de fin sont chacune à 30 minutes ou moins. Le choix le plus fréquent est repris ; les égalités sont départagées par la réponse la plus récente. Sans historique pour un jour, ne rien préremplir.
- Un lien est créé automatiquement pour chaque bénévole et reste stable lors d’un renvoi. Une révocation suivie d’une régénération invalide l’ancien lien.
- La désactivation d’un bénévole conserve ses réponses. Une suppression définitive retire le bénévole, son lien et toutes ses déclarations.
- Le repas de midi (12:30–13:30) concerne les bénévoles disponibles toute la journée. Ils y sont inscrits par défaut ; l’administration peut les retirer avec une confirmation et les réinscrire. Les bénévoles ayant seulement un créneau horaire ne sont pas inscrits automatiquement.

## Sécurité et données

- Utiliser PostgreSQL uniquement ; ne pas introduire de fallback SQLite.
- Ne jamais coder en dur des mots de passe, clés, jetons, secrets SMTP ou paramètres de déploiement.
- Générer les jetons avec un générateur cryptographiquement sûr, les protéger au repos et ne jamais les écrire dans les journaux. Ne pas exposer les données d’un autre bénévole via un lien individuel.
- Protéger les mots de passe et les opérations d’administration avec les mécanismes de sécurité adaptés ; appliquer les permissions côté serveur, pas seulement dans l’interface.
- Ne pas journaliser les mots de passe, jetons ou données personnelles inutiles.
- Garder MailHog pour les courriels de développement local. Le staging utilise le SMTP OVH configuré dans `.env.staging` ; ne pas exposer ses identifiants.

## Interface et langue

- Rédiger en français l’interface, les erreurs et les messages destinés aux utilisateurs. La V1 n’est pas multilingue.
- Concevoir les parcours bénévole et administration d’abord pour mobile, sans négliger l’usage sur ordinateur.
- Réutiliser Tailwind CSS et Lucide React conformément à la feuille de route et aux dépendances réellement présentes.
- Distinguer visuellement et dans les données les jours indisponibles des bénévoles qui n’ont pas répondu à une période.
- Le libellé de connexion de l’administration suit le genre du compte (« Connecté » / « Connectée »). Le genre (`homme` / `femme`) est stocké sur le compte, requis à la création et modifiable dans la page Compte.
- Le prénom et le nom des administrateurs sont stockés sur leur compte, facultatifs, modifiables dans Compte et affichés sous le libellé de connexion dans la barre latérale.
- Deux rôles existent : **Administrateur** (planning, bénévoles, profil) et **Administrateur principal** (ajout de comptes, modification des horaires). Le compte initial est administrateur principal ; les comptes suivants reçoivent le rôle choisi par un administrateur principal.
- Le genre des bénévoles (`homme` / `femme`) est renseigné dans leur fiche d’administration et stocké pour permettre des accords adaptés dans les futurs messages. Les fiches existantes sans genre sont signalées « Genre à renseigner ».
- Le prénom et le nom des bénévoles sont saisis séparément dans leur fiche ; le nom complet reste utilisé dans les plannings, les liens et les courriels.

## Workflow Git

- `main` est la branche stable : ne jamais y travailler directement. La branche locale doit rester alignée sur `origin/main` avec `git pull --ff-only`.
- Pour chaque modification, créer une branche dédiée depuis `main` :
  ```bash
  git switch main
  git pull --ff-only origin main
  git switch -c <type>/<sujet-court>
  ```
  Types usuels : `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`.
- Committer et pousser la branche avec `git push -u origin <branche>`.
- Ouvrir une pull request avec `gh pr create --base main --head <branche>`.
- Après validation, fusionner en squash avec `gh pr merge --squash --delete-branch`, puis revenir sur `main` et exécuter `git pull --ff-only origin main`.
- Ne jamais fusionner sans avoir exécuté les vérifications du dépôt et ne jamais pousser de secret, de jeton ou de donnée personnelle.

## Changements et validation

- Examiner les fichiers, dépendances et scripts existants avant de choisir une approche ou une commande. Ne pas présumer que des composants décrits dans la feuille de route sont déjà implémentés.
- Faire des changements ciblés, suivre les conventions existantes et garder les types et validations cohérents entre l’API et l’interface.
- Ajouter des tests ciblés pour toute nouvelle règle métier ou correction. Ne pas conserver ni réintroduire de logique ou de tests liés aux QCM.
- Exécuter les vérifications pertinentes définies par le dépôt : tests backend, lint et build frontend, puis tests d’intégration Docker lorsque les services concernés sont modifiés.
- Ne pas inventer de commandes de test lorsque les scripts du dépôt ne sont pas encore établis ; les définir avec le socle technique et les garder documentées.
- Mettre à jour la feuille de route lorsque des décisions de périmètre ou des règles métier changent.

