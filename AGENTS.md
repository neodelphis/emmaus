# Consignes pour les agents de code

## Contexte du projet

Cette application Emmaüs permet aux bénévoles de déclarer leurs disponibilités pour des périodes de service du mardi au samedi. Avant toute modification fonctionnelle, consulter la feuille de route dans [`roadmaps/version-de-travail.md`](roadmaps/version-de-travail.md) et respecter ses règles métier.

La V1 est locale : Docker Compose, PostgreSQL, FastAPI, React/Vite et MailHog. Les déploiements distants via GitHub Actions sont une évolution ultérieure, pas une tâche implicite de la V1.

## Règles métier à préserver

- Les bénévoles n’ont pas de compte ; ils accèdent à leurs seules données par un lien personnel sécurisé.
- Les périodes de service vont du mardi au samedi. Le bénévole peut renseigner la période en cours si elle est encore ouverte et les quatre suivantes.
- Pour chaque jour, une réponse vide signifie indisponible ; une journée sans soumission reste distincte et doit apparaître comme « sans réponse » côté administration.
- Une disponibilité quotidienne est soit vide, soit toute la journée, soit un créneau continu unique. Les heures personnalisées suivent un pas de 30 minutes et les bornes d’ouverture configurées.
- Les heures d’ouverture initiales sont 08:00-18:00 pour chaque jour, modifiables par l’administration. Une modification ne réécrit pas les réponses déjà enregistrées.
- La modification d’un jour ferme à 23 h 59 la veille, dans le fuseau `Europe/Paris`.
- Les propositions réutilisent les quatre dernières périodes passées renseignées, jamais les déclarations futures. Les jours vides sont ignorés ; toute la journée est distincte des créneaux. Deux créneaux sont proches si leurs bornes de début et de fin sont chacune à 30 minutes ou moins. Le choix le plus fréquent est repris ; les égalités sont départagées par la réponse la plus récente. Sans historique pour un jour, ne rien préremplir.
- Un lien est créé automatiquement pour chaque bénévole et reste stable lors d’un renvoi. Une révocation suivie d’une régénération invalide l’ancien lien.
- La désactivation d’un bénévole conserve ses réponses. Une suppression définitive retire le bénévole, son lien et toutes ses déclarations.

## Sécurité et données

- Utiliser PostgreSQL uniquement ; ne pas introduire de fallback SQLite.
- Ne jamais coder en dur des mots de passe, clés, jetons, secrets SMTP ou paramètres de déploiement.
- Générer les jetons avec un générateur cryptographiquement sûr, les protéger au repos et ne jamais les écrire dans les journaux. Ne pas exposer les données d’un autre bénévole via un lien individuel.
- Protéger les mots de passe et les opérations d’administration avec les mécanismes de sécurité adaptés ; appliquer les permissions côté serveur, pas seulement dans l’interface.
- Ne pas journaliser les mots de passe, jetons ou données personnelles inutiles.
- Garder MailHog pour les courriels de développement local. Ne pas configurer un fournisseur de production ou un déploiement distant sans instruction explicite.

## Interface et langue

- Rédiger en français l’interface, les erreurs et les messages destinés aux utilisateurs. La V1 n’est pas multilingue.
- Concevoir les parcours bénévole et administration d’abord pour mobile, sans négliger l’usage sur ordinateur.
- Réutiliser Tailwind CSS et Lucide React conformément à la feuille de route et aux dépendances réellement présentes.
- Distinguer visuellement et dans les données les jours indisponibles des bénévoles qui n’ont pas répondu à une période.

## Changements et validation

- Examiner les fichiers, dépendances et scripts existants avant de choisir une approche ou une commande. Ne pas présumer que des composants décrits dans la feuille de route sont déjà implémentés.
- Faire des changements ciblés, suivre les conventions existantes et garder les types et validations cohérents entre l’API et l’interface.
- Ajouter des tests ciblés pour toute nouvelle règle métier ou correction. Ne pas conserver ni réintroduire de logique ou de tests liés aux QCM.
- Exécuter les vérifications pertinentes définies par le dépôt : tests backend, lint et build frontend, puis tests d’intégration Docker lorsque les services concernés sont modifiés.
- Ne pas inventer de commandes de test lorsque les scripts du dépôt ne sont pas encore établis ; les définir avec le socle technique et les garder documentées.
- Mettre à jour la feuille de route lorsque des décisions de périmètre ou des règles métier changent.

