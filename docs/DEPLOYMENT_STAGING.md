# Déploiement staging — GitHub Actions, GHCR et Traefik

Ce document décrit le premier déploiement de l’application Emmaüs sur
`emmaus-staging.neodelphis.ovh`. Le staging tourne sur le même VPS que les autres
projets, derrière le Traefik du dépôt `vps-reverse-proxy`.

> **Important** : la fusion de la pull request de déploiement sur `main` déclenche
> immédiatement le workflow. Configure d’abord le serveur et les secrets GitHub,
> puis fusionne la PR.

## 1. Vue d’ensemble

```text
Internet
   │ 443 (HTTPS)
   ▼
Traefik (proxy-net)
   └── emmaus-staging.neodelphis.ovh → emmaus-staging-web:80
                                           └── /api → emmaus-staging-api:8000
                                                         └── emmaus-staging-db:5432
```

- **Une seule origine publique** : le frontend Nginx sert l’interface et relaie
  `/api` vers l’API. Il n’y a pas de CORS à configurer.
- **Aucun port applicatif publié** : seul Traefik expose 80/443. PostgreSQL reste
  sur le réseau interne du projet Compose.
- **Images GHCR** : GitHub Actions construit `backend` et `frontend`, les publie
  sur GitHub Container Registry, puis le serveur les récupère.
- **Courriels OVH** : le staging utilise le SMTP OVH (`ssl0.ovh.net:465`) pour
  envoyer réellement les liens et les réinitialisations de mot de passe.
- **Tests avant déploiement** : le workflow exécute le lint, les tests backend
  sur PostgreSQL et le build frontend avant de construire les images.

## 2. Fichiers concernés

| Fichier | Rôle |
| --- | --- |
| `.github/workflows/deploy-staging.yml` | Tests, build GHCR, déploiement SSH et vérification HTTPS |
| `docker-compose.staging.yml` | Services staging, réseau Traefik et labels |
| `.env.staging.example` | Modèle des variables de l’environnement staging |
| `docs/DEPLOYMENT_STAGING.md` | Ce guide |

Le fichier réel `.env.staging` reste **uniquement sur le serveur**. Il n’est ni
versionné ni copié par la CI.

## 3. Prérequis

### 3.1 DNS

`emmaus-staging.neodelphis.ovh` doit pointer vers `51.89.151.178` avant le
déploiement :

```sh
dig +short emmaus-staging.neodelphis.ovh
# attendu : 51.89.151.178
```

Si le domaine est derrière Cloudflare, utiliser un enregistrement **DNS only**
(nuage gris) au moins pendant la première émission du certificat Let’s Encrypt.
Les ports **80** et **443** doivent être joignables depuis Internet.

### 3.2 Accès SSH

L’accès manuel utilise l’alias SSH local `staging`, configuré sur le Mac :

```sh
ssh staging
```

L’alias contient l’hôte, le port `49094`, l’utilisateur et la clé personnelle.
Toutes les commandes manuelles de ce document utilisent cet alias.

GitHub Actions ne lit pas `~/.ssh/config` : les secrets `STAGING_HOST`,
`STAGING_USER` et `STAGING_PORT` doivent contenir les valeurs réelles (voir § 5.3).

### 3.3 Traefik et Docker

Sur le serveur :

```sh
docker network inspect proxy-net
docker ps --filter name=traefik
```

Le réseau `proxy-net` doit exister et Traefik doit utiliser le resolver
`letsencrypt` et l’entrypoint `websecure`. Les labels du Compose staging sont
prévus pour cette configuration. Si les noms diffèrent, adapte les labels du
service `web` dans `docker-compose.staging.yml`.

L’utilisateur SSH doit pouvoir exécuter `docker` et `docker compose`.

## 4. Préparer le serveur

### 4.1 Créer le répertoire de déploiement

```sh
ssh staging 'mkdir -p ~/emmaus'
```

Le chemin utilisé par défaut est `/home/debian/emmaus`. La CI y copie
`docker-compose.staging.yml` ; elle ne touche jamais à `.env.staging` ni aux
volumes.

### 4.2 Créer le fichier d’environnement

Depuis la racine du dépôt local :

```sh
scp .env.staging.example staging:~/emmaus/.env.staging

ssh -t staging \
  'nano ~/emmaus/.env.staging && chmod 600 ~/emmaus/.env.staging'
```

Remplir au minimum :

- `POSTGRES_PASSWORD` : mot de passe solide, sans caractères spéciaux
  problématiques dans une URL (`:@/#?%…`) ;
- `SECRET_KEY` : `openssl rand -hex 32` ;
- `ADMIN_EMAIL` et `ADMIN_PASSWORD` : premier administrateur du staging, mot de
  passe de 12 caractères minimum, différent du développement ;
- `FRONTEND_URL` : `https://emmaus-staging.neodelphis.ovh` (déjà dans le modèle) ;
- `SMTP_USERNAME` et `SMTP_PASSWORD` : compte SMTP OVH expéditeur.

Le premier compte créé par le staging est administrateur principal. Il est créé
au premier démarrage uniquement ; ensuite, les comptes se gèrent dans **Compte**.

> Les courriels sont réellement envoyés depuis le staging via OVH. Utiliser une
> adresse de test pour les premières vérifications.

## 5. Configurer GitHub Actions

### 5.1 Créer l’environnement `staging`

```sh
gh api --method PUT repos/neodelphis/emmaus/environments/staging
```

### 5.2 Créer une clé SSH dédiée à la CI

Ne pas réutiliser la clé personnelle. Depuis le poste local :

```sh
ssh-keygen -t ed25519 -N "" \
  -C "github-actions-emmaus-staging" \
  -f ~/.ssh/emmaus_staging_deploy

cat ~/.ssh/emmaus_staging_deploy.pub | ssh staging \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Tester la clé dédiée à travers l’alias :

```sh
ssh -i ~/.ssh/emmaus_staging_deploy staging true
```

### 5.3 Ajouter les secrets à l’environnement

GitHub Actions ne lit pas l’alias `staging` : ces secrets contiennent les
valeurs réelles de la configuration SSH.

```sh
gh secret set STAGING_HOST --env staging --body "51.89.151.178"
gh secret set STAGING_USER --env staging --body "debian"
gh secret set STAGING_PORT --env staging --body "49094"
gh secret set STAGING_DEPLOY_PATH --env staging --body "/home/debian/emmaus"
gh secret set STAGING_SSH_KEY --env staging < ~/.ssh/emmaus_staging_deploy
```

Le workflow utilise aussi `GITHUB_TOKEN` pour pousser et tirer les images GHCR ;
il n’y a pas de secret à créer pour cela.

Vérifier :

```sh
gh secret list --env staging
```

## 6. Déployer

### 6.1 Fusionner la pull request

Une fois le DNS, le serveur, `.env.staging` et les secrets prêts, fusionner la PR
`feat/deploy-staging` sur `main`. Le push sur `main` déclenche :

1. **Tests et lint** : backend PostgreSQL + frontend ;
2. **Build** : images backend/frontend poussées sur GHCR avec les tags
   `staging` et `sha-<commit>` ;
3. **Deploy** : copie du Compose, connexion GHCR, `pull`, `up -d`, attente des
   healthchecks, vérification de `https://emmaus-staging.neodelphis.ovh/api/health`.

Suivre l’exécution :

```sh
gh run list --workflow deploy-staging.yml
gh run watch
```

Après le premier déploiement, se connecter avec les identifiants
`ADMIN_EMAIL` / `ADMIN_PASSWORD` du fichier `.env.staging`.

### 6.2 Redéploiement manuel

```sh
gh workflow run deploy-staging.yml --ref main
```

## 7. Courriels OVH

Le staging n’utilise pas MailHog : les courriels partent réellement via OVH.

```dotenv
SMTP_HOST=ssl0.ovh.net
SMTP_PORT=465
SMTP_USERNAME=ne-pas-repondre@neodelphis.ovh
SMTP_PASSWORD=...
SMTP_USE_SSL=true
SMTP_FROM="Emmaus <ne-pas-repondre@neodelphis.ovh>"
```

Le compte expéditeur OVH doit être autorisé à envoyer avec cette adresse. Tester
avec une adresse de test avant de communiquer le lien de staging.

## 8. Rollback

Chaque déploiement publie un tag `sha-<commit>`. Pour redéployer une version
précédente sans reconstruire :

```sh
gh workflow run deploy-staging.yml \
  --ref main \
  -f image_tag=sha-<commit>
```

Le workflow saute alors les tests et le build, et déploie l’image demandée.

## 9. Dépannage

### Le workflow échoue avant le déploiement

- Vérifier que l’environnement `staging` et ses cinq secrets existent :
  `gh secret list --env staging`.
- Vérifier que la clé privée correspond à la clé publique ajoutée sur le serveur.
- Vérifier que `STAGING_DEPLOY_PATH` existe et que l’utilisateur SSH peut écrire.

### Le serveur refuse le déploiement

```sh
ssh staging
cd ~/emmaus
docker compose --env-file .env.staging -f docker-compose.staging.yml config
docker compose --env-file .env.staging -f docker-compose.staging.yml ps
docker compose --env-file .env.staging -f docker-compose.staging.yml logs --tail=100
```

Messages fréquents :

- `.env.staging manquant` : le créer sur le serveur ;
- `proxy-net introuvable` : Traefik n’est pas installé/configuré comme prévu ;
- `healthcheck unhealthy` : consulter les logs du conteneur indiqué.

### HTTPS ou domaine incorrect

```sh
dig +short emmaus-staging.neodelphis.ovh
docker logs --tail=100 traefik
```

Le certificat Let’s Encrypt n’est émis qu’après la création du routeur Traefik et
la résolution DNS correcte. Le workflow attend jusqu’à 300 secondes.

### Les courriels ne partent pas

Vérifier dans `.env.staging` :

- `SMTP_HOST=ssl0.ovh.net` ;
- `SMTP_PORT=465` ;
- `SMTP_USE_SSL=true` ;
- `SMTP_USERNAME` et `SMTP_PASSWORD` du compte OVH ;
- `SMTP_FROM` avec l’adresse expéditrice autorisée.

Les logs de l’API indiquent le type d’échec sans révéler le mot de passe. Vérifier
aussi que le compte OVH n’est pas bloqué et que l’adresse expéditrice est
autorisée.

## 10. Sécurité

- `.env.staging` n’est jamais versionné et doit être en `chmod 600`.
- La clé SSH de la CI est dédiée au staging.
- PostgreSQL n’est pas exposé sur Internet.
- Les identifiants SMTP OVH restent dans `.env.staging` sur le serveur.
- Seul Traefik publie 80/443.
- Les secrets de staging sont différents de ceux du développement et de la
  production.
