## Résumé

<!-- Décrire le changement et son objectif. -->

## Vérifications

- [ ] Tests backend : `docker compose run --rm api sh -c 'TEST_DATABASE_URL="$TEST_DATABASE_URL" pytest'`
- [ ] Lint backend : `docker compose run --rm api ruff check app tests scripts`
- [ ] Lint frontend : `npm run lint` dans `frontend/`
- [ ] Build frontend : `npm run build` dans `frontend/`
- [ ] Test de fumée Docker si les services sont modifiés : `python backend/scripts/smoke_test.py`
- [ ] Feuille de route ou documentation mise à jour si le périmètre change
- [ ] Aucun secret, jeton, mot de passe ou donnée personnelle ajouté au dépôt

## Notes

<!-- Points d'attention, décisions de périmètre ou questions restantes. -->
