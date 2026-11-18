# Feuille de route de travail — V1 locale

Ce document est le suivi opérationnel de la
[feuille de route initiale](feuille-de-route-initiale.md). Il consigne les décisions
d'implémentation, l'avancement et les points en attente. Les règles métier de la feuille
initiale et de [AGENTS.md](../AGENTS.md) restent la référence.

## État d'avancement

| Phase | État | Validation |
| --- | --- | --- |
| 0. Socle local et documentation | Terminé | Docker Compose, README, `.env.example` |
| 1. Modèle, sécurité et authentification | Terminé | Tests API et unitaires |
| 2. API bénévole et règles métier | Terminé | Tests périodes, créneaux, propositions |
| 3. API d'administration | Terminé | Tests liens, semaines, horaires, comptes |
| 4. Interface bénévole | Terminé | Vérification Chromium mobile et bureau |
| 5. Interface d'administration | Terminé | Vérification Chromium mobile et bureau |
| 6. Validation et finition | Terminé | Pile Docker reconstruite depuis un volume vierge |
| 7. Déploiement distant (hors V1) | Non commencé | À planifier ultérieurement |

## Décisions d'implémentation

1. **Semaine de service et périodes visibles.** La période « courante » est le mardi de la
   semaine contenant la date, la semaine de service allant du mardi au samedi. Les
   périodes proposées sont la période courante si au moins un jour est encore modifiable,
   puis les quatre suivantes. Une période est ouverte tant qu'au moins un de ses jours est
   strictement postérieur à la date du jour à Paris. Conséquence assumée : le samedi, la
   période en cours est entièrement close et seules les quatre suivantes sont proposées.
2. **Clôture d'un jour.** Un jour est modifiable si sa date est strictement postérieure à
   la date courante à Paris (fermeture à 23 h 59 la veille). Le jour même n'est plus
   modifiable.
3. **Soumission et jours vides.** Une `AvailabilityResponse` matérialise la soumission
   d'une période. Une journée sans ligne `DayAvailability` dans une réponse soumise vaut
   « indisponible » ; l'absence de réponse pour la période vaut « sans réponse ».
   L'enregistrement met à jour uniquement les jours ouverts envoyés par le formulaire ; les
   jours déjà clos conservent leur valeur.
4. **Historique des propositions.** Seules les périodes dont le samedi est strictement
   antérieur à aujourd'hui sont utilisées, et seulement les quatre plus récentes ayant une
   réponse soumise (même si des jours y sont vides). Les déclarations futures et la
   période en cours sont exclues.
5. **Regroupement des créneaux proches.** La relation « proche » (début et fin à
   ≤ 30 minutes) n'étant pas transitive, les créneaux sont regroupés autour de la réponse
   la plus récente encore libre. Le groupe le plus nombreux gagne, puis la réponse réelle
   la plus récente du groupe est reprise. Égalité entre catégories : réponse la plus
   récente.
6. **Liens personnels.** Le jeton aléatoire est stocké sous forme d'empreinte et chiffré
   pour permettre le renvoi sans régénération. Le lien est envoyé sous la forme
   `FRONTEND_URL/b#<jeton>` ; l'interface lit le fragment et appelle l'API avec l'en-tête
   `X-Volunteer-Token`. Ainsi le jeton n'apparaît pas dans les journaux d'accès. La
   révocation supprime le jeton ; la régénération en crée un nouveau.
7. **Sessions administrateur.** JWT signé dans un cookie `HttpOnly`/`SameSite=Lax`. Un
   compteur `session_version` est incrémenté à chaque réinitialisation de mot de passe,
   ce qui invalide immédiatement les sessions antérieures.
8. **Horaires d'ouverture.** Table par jour de semaine (mardi = 1 … samedi = 5). Une
   modification ne touche pas aux réponses ; les nouvelles saisies sont validées contre
   les horaires courants.
9. **Migrations.** La V1 locale crée le schéma avec `Base.metadata.create_all` au
   démarrage. Aucune migration Alembic n'est introduite à ce stade ; il faudra en ajouter
   une avant tout déploiement avec données persistantes.
10. **Base de test.** Les tests d'API utilisent PostgreSQL uniquement, via
    `TEST_DATABASE_URL` et la base `emmaus_test` créée par le script d'initialisation
    Docker. Aucun repli SQLite.
11. **Port hôte PostgreSQL.** Le port `5433` est exposé côté hôte pour cohabiter avec un
    PostgreSQL local ; l'API utilise `db:5432` dans Compose. Toute modification de port
    devra mettre à jour ce document, le README et les configurations.
12. **Image de build frontend.** Le build utilise `node:24-bookworm-slim` et non Alpine :
    le binaire natif de Rollup employé par Vite échoue sur musl avec la version actuelle.
13. **Planning par demi-journées.** La vue administration présente une carte par jour,
    avec deux listes : **Matin** (avant 13:00) et **Après-midi** (dès 13:00). Chaque
    bénévole y figure avec ses horaires réels, sans positionnement horaire, afin de rester
    lisible avec une quinzaine de personnes par créneau. Un créneau qui chevauche 13:00
    apparaît dans les deux listes. Les journées entières sont affichées dans un bandeau
    vert en haut de chaque jour **et** reprises dans les deux listes. Les bénévoles sans
    réponse sont listés dans un encart distinct et ne sont jamais comptés comme
    indisponibles ; le nombre d'indisponibles est rappelé par jour. Sur mobile, un
    sélecteur de jour affiche une journée à la fois ; sur ordinateur, les cinq cartes sont
    visibles et un filtre permet d'isoler un jour.

## Validation effectuée

- `pytest` : 56 tests backend, exécutés dans le conteneur API avec PostgreSQL.
- `ruff check app tests` : aucune erreur.
- `npm run lint` : aucune erreur ni avertissement.
- `npm run build` : compilation TypeScript et build Vite réussis.
- `python scripts/smoke_test.py` : API, PostgreSQL, MailHog et Nginx validés de bout en
  bout sur une pile reconstruite depuis un volume vierge.
- Vérifications Chromium (bureau et mobile) : connexion, planning par demi-journées,
  filtre par jour, sélecteur mobile, listes denses (16 bénévoles), création,
  modification et suppression d'un bénévole,
  enregistrement d'une disponibilité, modification des horaires, création d'un compte
  administrateur et réinitialisation de mot de passe.
- Jeu de démonstration `app.seed_demo` vérifié sur les cinq profils bénévoles et le cas
  du lien désactivé ; les liens sont affichés à l'exécution et ne sont pas versionnés.

## Points d'attention restants

- Vérifier la rotation de `SECRET_KEY` : les liens existants restent valides par leur
  empreinte, mais l'administration ne peut plus les copier ni les renvoyer avant
  régénération.
- Ajouter des migrations versionnées (Alembic) avant tout déploiement distant.
- Décider des limites de sécurité pour un usage hors réseau local (limitation des essais
  de connexion, en-têtes supplémentaires, sauvegardes).
- Éventuellement ajouter des tests frontend automatisés (Vitest/Playwright) ; la feuille
  de route initiale ne demandait que lint et build.

## Rapport final

### Fait

- Socle Docker Compose local : PostgreSQL 16, API FastAPI, interface React/Vite servie par
  Nginx, MailHog, base de test et documentation.
- Modèle de données complet : administrateurs, jetons de réinitialisation, bénévoles,
  liens chiffrés, réponses et jours, horaires d'ouverture.
- Authentification administrateur, comptes multiples, réinitialisation de mot de passe
  par courriel, invalidation des sessions, premier compte initialisé par `.env`.
- API et interface bénévole : lien personnel, périodes mardi–samedi, clôture à 23 h 59 la
  veille, jour vide / toute la journée / créneau de 30 minutes, propositions historiques.
- Administration : bénévoles, liens (copie, envoi, révocation, régénération), planning
  par jour avec listes matin/après-midi, journées entières reprises dans les deux listes,
  non-répondants distincts, filtres par jour, horaires, comptes administrateurs.
- Validation : 56 tests backend, lint, build, test de fumée Docker et vérifications
  navigateur mobile/bureau.

### En attente

1. **Interprétation des périodes visibles** : le samedi, la période en cours étant
   entièrement close, seules les quatre suivantes sont affichées. Confirmez-vous ce
   comportement, ou faut-il toujours afficher cinq périodes en commençant par la prochaine ?
2. **Historique des propositions** : seules les périodes **achevées** (samedi antérieur à
   aujourd'hui) sont utilisées. Confirmez-vous que la période en cours ne doit jamais
   servir d'historique, même pour préremplir une période future ?
3. **Bénévoles désactivés** : ils sont masqués par défaut dans le planning et
   accessibles via la case « Inclure les bénévoles désactivés ». Ce choix convient-il ?
4. **Vue historique** : l'administration peut consulter les quatre périodes passées, la
   période courante et les périodes ouvertes. Faut-il remonter plus loin en V1 ?
5. **Identité visuelle** : la palette vert Emmaüs / pierre et la mise en page sont à
   valider avec vous ; les écrans peuvent être ajustés sans impact fonctionnel.
6. **Sécurité hors réseau local** : la V1 ne limite pas les tentatives de connexion et
   n'ajoute pas de second facteur. Confirmez-vous que ces sujets restent hors périmètre
   jusqu'au déploiement distant ?
7. **Migrations** : faut-il introduire Alembic dès maintenant ou le réserver à la phase de
   déploiement ?
8. **Tests frontend** : faut-il ajouter Vitest/Playwright en V1, sachant que la feuille de
   route initiale ne demandait que lint et build ?
9. **Coupure matin/après-midi** : elle est fixée à **13:00**. Faut-il la placer à 12:00,
   ou préférer un autre découpage ?

### Informations d'accès locales

Les identifiants du premier administrateur et les secrets locaux sont dans `.env`, qui
n'est pas versionné. Ils sont créés aléatoirement dans cet environnement de travail.
