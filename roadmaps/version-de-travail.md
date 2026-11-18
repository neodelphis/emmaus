# Feuille de route de travail — V1 locale

Ce document est le suivi opérationnel de la
[`feuille de route initiale`](feuille-de-route-initiale.md). Il consigne les décisions
d'implémentation, l'avancement et les points en attente. Les règles métier de la feuille
initiale et de [`AGENTS.md`](../AGENTS.md) restent la référence.

## État d'avancement

| Phase | État | Commit de référence |
| --- | --- | --- |
| 0. Socle local et documentation | Terminé | à compléter |
| 1. Modèle, sécurité et authentification | Terminé | à compléter |
| 2. API bénévole et règles métier | Terminé | à compléter |
| 3. API d'administration | Terminé | à compléter |
| 4. Interface bénévole | En cours | — |
| 5. Interface d'administration | À faire | — |
| 6. Validation et finition | À faire | — |

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

## Points d'attention restants

- Vérifier les parcours mobile et ordinateur dans un navigateur (phase 6).
- Ajouter le test de fumée Docker et l'exécuter sur une pile vierge.
- Contrôler la documentation OpenAPI et les messages d'erreur en français.
- Décider si les bénévoles désactivés doivent rester visibles par défaut dans la vue
  hebdomadaire (actuellement masqués, option `include_inactive` disponible).
- La rotation de `SECRET_KEY` rend les liens existants illisibles ; elle nécessiterait une
  régénération assistée. À documenter avant un déploiement futur.

## Validation

Les commandes exactes sont documentées dans le [`README.md`](../README.md) : tests
pytest avec PostgreSQL, `ruff check`, `npm run lint`, `npm run build` et script de fumée
Docker.

## Rapport final

À compléter à la fin de la phase 6 (fait, en attente, questions).
