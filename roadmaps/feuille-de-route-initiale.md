# Feuille de route — Disponibilités des bénévoles Emmaüs

## Vision

Créer une application Web simple, professionnelle et mobile-first permettant aux bénévoles Emmaüs de déclarer leurs disponibilités pour les périodes de service du mardi au samedi. Les bénévoles accèdent à leur espace au moyen d’un lien personnel sécurisé, sans créer de compte. L’équipe administrative gère les bénévoles, les liens et les réponses.

La V1 est destinée à un usage local. Le dépôt ne contient pas encore d’application implémentée ; les phases ci-dessous décrivent le travail à réaliser, et non des fonctions déjà disponibles.

## Périmètre fonctionnel de la V1

### Déclaration d’un bénévole

- Une période de service va du mardi au samedi.
- Le bénévole peut consulter et renseigner la période en cours lorsqu’elle est encore ouverte, ainsi que les quatre périodes suivantes.
- Pour chaque jour, il peut laisser la réponse vide (indisponible), indiquer qu’il est disponible toute la journée, ou saisir un seul créneau continu.
- Les créneaux personnalisés sont saisis par pas de 30 minutes et doivent être compris dans les heures d’ouverture configurées.
- Le fuseau horaire de l’application est `Europe/Paris`.
- Une réponse pour un jour donné reste modifiable jusqu’à 23 h 59 la veille de ce jour. La limite s’applique séparément à chaque jour et à chaque période.
- L’absence de soumission pour une période est distincte d’une période soumise dont certains jours sont vides.

### Horaires d’ouverture et propositions historiques

- Les heures d’ouverture par défaut sont de 08:00 à 18:00 du mardi au samedi.
- L’administration peut modifier les heures pour chaque jour. Une modification ne réécrit pas les réponses existantes ; les nouvelles saisies et les modifications ultérieures doivent respecter les limites configurées.
- Pour préremplir un jour, l’application recherche le créneau le plus fréquent parmi les quatre dernières périodes passées auxquelles le bénévole a répondu. Les déclarations de périodes futures ne sont pas utilisées pour calculer ces propositions.
- Les jours vides sont ignorés dans ce calcul. « Toute la journée » est une catégorie distincte des créneaux horaires.
- Deux créneaux personnalisés sont considérés proches si leur début et leur fin diffèrent chacun d’au plus 30 minutes. Pour une catégorie ou un groupe le plus fréquent, l’application reprend la réponse réelle la plus récente qui lui appartient. En cas d’égalité entre plusieurs catégories ou groupes les plus fréquents, elle choisit celui contenant la réponse la plus récente.
- Si aucun historique exploitable n’existe pour un jour, le champ reste vide ; aucune disponibilité n’est inventée. Le bénévole peut toujours modifier une proposition avant de soumettre sa réponse.

### Administration

- Les administrateurs se connectent avec un identifiant et un mot de passe. Chaque administrateur a son propre compte et son adresse courriel, et peut réinitialiser son mot de passe par courriel.
- Le premier compte est initialisé de façon sécurisée par la configuration locale. Les administrateurs connectés peuvent créer d’autres comptes. Tous les comptes ont le même rôle en V1.
- L’administration peut ajouter et modifier des bénévoles, et désactiver ceux qui ne participent plus. La désactivation conserve leur historique.
- Une fiche bénévole comprend un nom et une adresse courriel facultative.
- Un lien individuel sécurisé est créé automatiquement à la création du bénévole. L’administration peut le copier ou, si une adresse courriel existe, l’envoyer sur une action explicite. Pour un bénévole sans courriel, l’administration communique le lien hors application.
- Le lien reste stable lors des renvois. L’administration peut séparément révoquer le lien et en générer un nouveau ; l’ancien lien cesse alors de fonctionner.
- L’administration peut supprimer définitivement un bénévole. Cette suppression retire le bénévole, son lien et toutes ses déclarations associées.
- Une vue hebdomadaire, utilisable sur téléphone et ordinateur, permet de consulter les disponibilités et de filtrer par jour. Elle affiche aussi les bénévoles qui n’ont pas soumis de réponse, avec un statut distinct des jours laissés vides. Aucun export n’est prévu en V1.

### Courriels

- L’envoi des liens est déclenché par l’administration ; aucun rappel hebdomadaire automatique n’est envoyé.
- L’envoi utilise une configuration SMTP. En développement local, MailHog reçoit les messages.
- Le fournisseur de courriel de production sera choisi ultérieurement, lorsque le déploiement distant sera défini.

## Architecture et contraintes techniques

- **Développement local :** Docker Compose, avec PostgreSQL, une API Python/FastAPI, une interface React/Vite et MailHog.
- PostgreSQL est l’unique base de données ; ne pas ajouter de fallback SQLite.
- L’interface, les messages d’erreur et les retours API destinés aux utilisateurs sont en français. La V1 est en français uniquement.
- Les interfaces bénévole et administration sont mobile-first et restent utilisables sur ordinateur.
- Utiliser Tailwind CSS pour le style et Lucide React pour les icônes, comme prévu dans le document de travail initial.
- Configurer les services et variables d’environnement sans intégrer de secrets, jetons réels ou paramètres d’un futur déploiement dans le code.
- Ne pas modifier un port sans mettre à jour les configurations Docker et les références correspondantes.

## Étapes de réalisation proposées

1. **Socle local :** établir la structure du dépôt, Docker Compose, PostgreSQL, FastAPI, React/Vite et MailHog ; documenter les variables d’environnement sans secrets.
2. **Modèle et accès :** définir les modèles des administrateurs, bénévoles, périodes, horaires d’ouverture, liens et réponses ; implémenter l’initialisation sécurisée du premier administrateur, l’authentification, les comptes individuels et la récupération de mot de passe.
3. **Parcours bénévole :** implémenter les liens individuels, le formulaire responsive, les périodes autorisées, les limites de modification, les horaires configurables et les propositions basées sur l’historique.
4. **Outils d’administration :** implémenter la gestion des bénévoles et des liens, les courriels sur action explicite, la configuration des heures d’ouverture et la vue hebdomadaire incluant les non-répondants.
5. **Validation et finition :** vérifier les règles métier, les parcours mobile et ordinateur, les erreurs, les permissions et l’intégration des services ; corriger les défauts avant de considérer la V1 prête.
6. **Évolution ultérieure :** préparer les déploiements staging et production par GitHub Actions après définition des environnements, secrets et procédures opérationnelles. Ne pas déployer ni ajouter de workflow de déploiement dans la V1 locale.

## Critères de validation

- Le backend passe ses tests, y compris les règles de période, les limites d’édition, les horaires, les propositions historiques, la révocation des liens et les permissions.
- Le frontend passe les contrôles de lint et de compilation.
- Les tests d’intégration couvrent les échanges entre l’interface, l’API, PostgreSQL et MailHog dans l’environnement Docker Compose.
- La vue administrative distingue clairement une période sans réponse d’une réponse soumise avec un ou plusieurs jours vides.
- Les messages et parcours destinés aux utilisateurs sont en français et utilisables sur téléphone.
- Les commandes de validation exactes seront celles définies par les manifests et scripts du dépôt ; ne pas conserver les anciens tests liés aux QCM.

## Hors périmètre de la V1

- Déploiement staging ou production et workflows GitHub Actions de déploiement.
- Rappels hebdomadaires automatiques.
- Export des disponibilités.
- Plusieurs rôles d’administration, interface multilingue et plusieurs créneaux par jour.
- Une gestion des horaires fondée sur plusieurs fuseaux horaires.

