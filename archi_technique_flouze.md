# Architecture Technique — Flouze
### Application de Suivi des Dépenses · v1.0 · Avril 2026
> Stack : React · FastAPI · PostgreSQL · Docker Compose

---

## 1. Architecture Globale

### 1.1 Schéma global

```
┌─────────────────────────────────────────────────────────────────┐
│                      NAVIGATEUR (SPA)                           │
│           React + React Query + Zustand + Recharts              │
│               WebSocket client (notifications)                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTPS / WSS
┌───────────────────────▼─────────────────────────────────────────┐
│                    REVERSE PROXY                                 │
│              Nginx (routing + TLS termination)                   │
└───────┬─────────────────────────┬───────────────────────────────┘
        │ /api/*                  │ /*
┌───────▼───────┐       ┌─────────▼──────────────────────────────┐
│   FastAPI     │       │         Static Assets                   │
│   (Python)    │       │    React build (HTML / JS / CSS)         │
│               │       └─────────────────────────────────────────┘
│  Auth / JWT   │
│  REST API     │──────────────────────────────┐
│  WebSocket    │                              │
└───────┬───────┘                     ┌────────▼────────┐
        │                             │  Services tiers  │
┌───────▼───────┐                     │  · ExchangeRate  │
│  PostgreSQL   │                     │  · OAuth2 IDP    │
│  (données)    │                     └─────────────────┘
└───────────────┘
        ▲
┌───────┴───────┐
│     Redis     │
│  Cache + WS   │
│  Pub/Sub      │
└───────────────┘

Tout orchestré par Docker Compose (dev) → déployable sur VPS / Cloud
```

### 1.2 Conteneurs Docker Compose

| Service    | Rôle et image de base |
|------------|----------------------|
| `nginx`    | Reverse proxy, TLS termination, serving SPA — `nginx:alpine` |
| `frontend` | Build React statique (multi-stage) — `node:20-alpine` |
| `backend`  | API FastAPI, WebSocket, workers — `python:3.12-slim` |
| `db`       | Base de données principale — `postgres:16-alpine` |
| `redis`    | Cache sessions, broker SSE/WS, rate-limiting — `redis:7-alpine` |

> **Note :** Redis est introduit dès la V1 pour le cache des taux de change (TTL 1h), le broker de notifications temps réel, et le rate-limiting des endpoints sensibles. Le déploiement production réutilise les mêmes images sans modification.

---

## 2. Authentification et Sécurité

### 2.1 Flux JWT + OAuth2

```
── Flux natif (email / mot de passe) ──────────────────────────────
  Client ──POST /auth/login──▶ FastAPI
         ◀── access_token (15 min) + refresh_token (30 j, httpOnly) ──

── Flux OAuth2 (Google) ────────────────────────────────────────────
  Client ──▶ Google OAuth2 ──▶ code
  Client ──POST /auth/oauth/google {code}──▶ FastAPI
         ◀── access_token + refresh_token (même structure) ──

── Renouvellement silencieux ────────────────────────────────────────
  Client ──POST /auth/refresh {refresh_token cookie}──▶ FastAPI
         ◀── nouveau access_token ──

── Révocation ───────────────────────────────────────────────────────
  Refresh token stocké en Redis avec TTL → invalidable côté serveur
```

### 2.2 Décisions d'authentification

| Élément | Décision |
|---------|----------|
| Access token    | JWT signé RS256 · durée 15 min · payload : user_id, space_ids, role |
| Refresh token   | Opaque token (UUID) stocké Redis · httpOnly cookie · 30 jours |
| OAuth2 provider | Google en V1 · extensible (GitHub, Apple) via python-social-auth |
| Hachage mdp     | bcrypt (work factor 12) via passlib |
| CORS            | Origines autorisées configurées par variable d'environnement |
| Rate limiting   | slowapi (Redis backend) · 5 tentatives/min sur /auth/login |

---

## 3. Modèle de Données

### 3.1 Entités et relations

```
users ────< space_members >──── spaces
  │                                │
  └──< categories (owner: user │ space)
            │
            └──< expenses
                    │
                    ├── attachments (fichiers justificatifs)
                    └── currency (devise + taux snapshot)

users ──< budgets (global ou par category)
spaces ──< budgets

recurring_rules ──▶ expenses (génération automatique)
exchange_rate_cache (Redis, TTL 1h) — pas en DB
notifications ──< users
```

### 3.2 Schéma des tables principales

| Table | Colonnes clés | Notes |
|-------|--------------|-------|
| `users` | id, email, hashed_pwd, oauth_provider, oauth_sub, created_at | oauth_sub nullable pour comptes natifs |
| `spaces` | id, name, owner_id, created_at | Espace partagé (couple, équipe) |
| `space_members` | space_id, user_id, role (admin\|member), joined_at | Table de jointure avec rôle |
| `categories` | id, name, emoji, color, owner_id, space_id, archived_at | owner_id XOR space_id |
| `expenses` | id, title, amount, currency, amount_mad, date, category_id, user_id, space_id, note, recurring_rule_id | amount_mad = montant converti en devise de référence |
| `attachments` | id, expense_id, file_path, mime_type, size_bytes | Chemin relatif vers volume Docker ou S3 en V2 |
| `budgets` | id, user_id, space_id, category_id, amount, month (YYYY-MM) | category_id nullable = budget global mensuel |
| `recurring_rules` | id, user_id, title, amount, currency, category_id, frequency, next_run, active | Cron APScheduler |
| `notifications` | id, user_id, type, payload (JSONB), read_at, created_at | Envoyées via WebSocket |

> **Sécurité :** PostgreSQL Row-Level Security (RLS) activé sur `expenses`, `categories`, `budgets`. Index composites : `(user_id, date)`, `(category_id, month)`, `(space_id, date)`.

---

## 4. Flux de Données Principaux

### 4.1 Ajout d'une dépense (avec devise étrangère)

```
  React UI                  FastAPI               PostgreSQL   Redis
     │                         │                      │          │
     │──POST /expenses──────▶  │                      │          │
     │  {title, amount,        │──GET rate:EUR:MAD──────────────▶│
     │   currency:'EUR',       │  (cache miss)                   │
     │   category_id, date}    │──GET exchangerate.host API ──▶  │
     │                         │◀─ {rate: 10.85}                 │
     │                         │──SET rate:EUR:MAD TTL:1h───────▶│
     │                         │                      │          │
     │                         │  amount_mad =        │          │
     │                         │  amount * rate       │          │
     │                         │──INSERT expense─────▶│          │
     │                         │◀─ {id, ...}          │          │
     │                         │──check budget────────▶│         │
     │                         │◀─ {spent, limit}     │          │
     │                         │  if spent > 80% :               │
     │                         │──PUBLISH notif─────────────────▶│
     │◀─ 201 {expense}─────────│     (channel: user:{id})        │
     │                         │                                  │
     │◀─ WebSocket BUDGET_ALERT│◀──WS subscriber─────────────────│
```

### 4.2 Consultation du tableau de bord

```
  React UI                  FastAPI               PostgreSQL   Redis
     │                         │                      │          │
     │──GET /dashboard─────▶   │                      │          │
     │  ?month=2026-05         │──GET dash:uid:2026-05─────────▶ │
     │  Authorization: Bearer  │  (cache miss)        │          │
     │                         │──SELECT expenses     │          │
     │                         │  + budgets (JOIN)───▶│          │
     │                         │◀─ rows               │          │
     │                         │  agrégation Python   │          │
     │                         │──SET dash:uid:month  │          │
     │                         │   TTL: 5 min────────────────── ▶│
     │◀─ 200 {                 │                      │          │
     │    total, restant,      │                      │          │
     │    by_category[],       │                      │          │
     │    monthly_trend[],     │                      │          │
     │    budget_progress[]    │                      │          │
     │  }──────────────────────│                      │          │
```

> **Double cache :** Redis (serveur, 5 min) + React Query (client, staleTime 2 min). Invalidation immédiate du cache Redis à chaque POST/PATCH/DELETE sur `/expenses`.

---

## 5. Fonctionnalités Avancées — Architecture

### 5.1 Notifications temps réel (WebSocket)

```
  Client ──WSS /ws?token=xxx──▶ FastAPI WS Manager
  WS Manager ──SUBSCRIBE user:{id}──▶ Redis Pub/Sub

  [Événement déclencheur : ex. budget dépassé]
  FastAPI ──PUBLISH user:{id} {type, payload}──▶ Redis
  Redis ──▶ WS Manager ──▶ Client WebSocket

  Types d'événements V1 :
  · BUDGET_ALERT     — seuil 80% ou dépassement
  · EXPENSE_ADDED    — nouvelle dépense dans espace partagé
  · MEMBER_JOINED    — invitation acceptée
```

### 5.2 Export PDF / Excel côté serveur

```
  Client ──POST /exports {type:'pdf', month:'2026-05'}──▶ FastAPI
         ◀── 202 {job_id: 'abc123'} ──

  FastAPI ──▶ APScheduler / BackgroundTask
               · PDF   : WeasyPrint (HTML → PDF)
               · Excel : openpyxl
               · Fichier → volume Docker /exports/{job_id}.pdf

  [Fin de génération]
  FastAPI ──PUBLISH user:{id} {type:EXPORT_READY, url}──▶ Redis ──▶ WS
  Client ──GET /exports/abc123/download──▶ FastAPI ──▶ StreamingResponse
```

### 5.3 Import bancaire (CSV / OFX)

```
  Client ──POST /imports/upload (multipart)──▶ FastAPI
         ◀── 202 {import_id, preview: [10 lignes]} ──

  Client ──POST /imports/{id}/confirm {mapping: {col→field}}──▶ FastAPI
  FastAPI ──parsing (ofxparse / csv)──▶ expenses[] (dry-run)
  FastAPI ──INSERT expenses (bulk)──▶ PostgreSQL
         ◀── 200 {imported: N, skipped: K, duplicates: D} ──

  Détection des doublons : hash(date + amount + description)
```

### 5.4 Taux de change (API externe)

| Aspect | Décision |
|--------|----------|
| Fournisseur V1   | exchangerate.host (gratuit, 250 req/mois) — clé API en variable d'env |
| Fournisseur V2   | Open Exchange Rates (plan Startup) si volume > seuil |
| Cache            | Redis · clé `rate:{FROM}:{TO}` · TTL 1 heure |
| Fallback         | Si API indisponible : dernier taux connu en DB (table `exchange_rates_log`) |
| Snapshot         | Le taux utilisé est enregistré sur la dépense (`amount_mad`) — pas recalculé |

---

## 6. Diagrammes d'États

### 6.1 États d'une dépense

```
                     ┌─────────────┐
                     │    DRAFT    │  (formulaire en cours, état local React)
                     └──────┬──────┘
                            │ POST /expenses (validation OK)
                     ┌──────▼──────┐
                     │   ACTIVE    │  (persistée en DB)
                     └──┬──────┬───┘
           PATCH /edit  │      │  DELETE
                     ┌──▼──┐  ┌▼──────────┐
                     │EDIT │  │  DELETED   │  (soft delete : deleted_at,
                     │(tmp)│  │            │   récupérable 30 j)
                     └──┬──┘  └────────────┘
              confirm   │
                     ┌──▼──────┐
                     │ ACTIVE  │  (mise à jour appliquée)
                     └─────────┘
```

### 6.2 États d'une règle récurrente

```
  ┌──────────┐   activate    ┌──────────┐   cron trigger    ┌──────────────┐
  │ INACTIVE │ ────────────▶ │  ACTIVE  │ ────────────────▶ │  GENERATING  │
  └──────────┘               └────┬─────┘                   └──────┬───────┘
        ▲                         │ pause                           │ success
        │ resume                  │                         ┌───────▼──────┐
        └─────────────────────────┘                         │  expense     │
                                                            │  créée (ACTIVE)
  ACTIVE ────── delete ──────────────────────────────────▶ DELETED
```

### 6.3 États d'un import bancaire

```
  UPLOADED ──parse──▶ PREVIEW ──confirm──▶ IMPORTING ──▶ COMPLETED
                                                    └──▶ FAILED
  PREVIEW ──cancel──▶ CANCELLED
```

---

## 7. Structure de l'API REST

| Méthode + Endpoint | Description | Spécificités |
|--------------------|-------------|--------------|
| `POST /auth/login` | Authentification native | Retourne access + refresh token |
| `POST /auth/oauth/google` | Authentification Google | Échange code → tokens |
| `POST /auth/refresh` | Renouvellement access token | Refresh token en httpOnly cookie |
| `POST /auth/logout` | Révocation du refresh token | Suppression Redis |
| `GET  /users/me` | Profil utilisateur courant | |
| `GET  /spaces` | Liste des espaces | |
| `POST /spaces` | Créer un espace partagé | |
| `POST /spaces/{id}/invite` | Inviter un membre | |
| `GET  /expenses` | Liste paginée des dépenses | Filtres : month, category_id, space_id, q |
| `POST /expenses` | Créer une dépense | Conversion devise auto si currency ≠ MAD |
| `PATCH /expenses/{id}` | Modifier une dépense | Invalide le cache dashboard |
| `DELETE /expenses/{id}` | Soft delete | deleted_at = now() |
| `GET  /categories` | Liste des catégories accessibles | Perso + espaces partagés |
| `POST /categories` | Créer une catégorie | |
| `PATCH /categories/{id}` | Modifier nom, emoji, couleur | |
| `GET  /budgets` | Budgets du mois courant ou ?month= | |
| `PUT  /budgets/{category_id}` | Définir/modifier un budget | Upsert par (user_id, category_id, month) |
| `GET  /dashboard` | Agrégats tableau de bord | Cache Redis 5 min |
| `POST /exports` | Déclencher export PDF ou Excel | Asynchrone → 202 + job_id |
| `GET  /exports/{id}/download` | Télécharger le fichier généré | StreamingResponse |
| `POST /imports/upload` | Upload fichier bancaire | Multipart, max 10 Mo |
| `POST /imports/{id}/confirm` | Valider l'import après preview | |
| `GET  /recurring` | Liste des règles récurrentes | |
| `POST /recurring` | Créer une règle récurrente | |
| `PATCH /recurring/{id}` | Modifier / pause / reprendre | |
| `WSS  /ws` | Canal WebSocket temps réel | Auth par query param token= |

---

## 8. Structure des Projets

### 8.1 Frontend React

```
flouze-frontend/
├── src/
│   ├── api/          # clients axios par domaine (expenses, budgets…)
│   ├── components/   # composants UI réutilisables
│   ├── features/     # modules métier (dashboard, depenses, budgets…)
│   │   └── dashboard/
│   │       ├── DashboardPage.tsx
│   │       ├── hooks/useDashboard.ts   # React Query hooks
│   │       └── components/
│   ├── store/        # Zustand (état global UI, user session)
│   ├── ws/           # WebSocket manager (singleton)
│   └── main.tsx
├── Dockerfile        # multi-stage : build → nginx serve
└── nginx.conf
```

### 8.2 Backend FastAPI

```
flouze-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py, expenses.py, budgets.py…
│   │       └── ws.py       # WebSocket endpoint
│   ├── core/               # config, security, database session
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic schemas (request/response)
│   ├── services/           # logique métier (budget_service, export…)
│   ├── workers/            # APScheduler jobs (recurring, exports)
│   └── main.py
├── alembic/                # migrations de schéma
├── tests/
├── Dockerfile
└── requirements.txt
```

### 8.3 Docker Compose

```
docker-compose.yml
├── services:
│   ├── nginx        # ports: 80:80, 443:443
│   ├── frontend     # build context: ./flouze-frontend
│   ├── backend      # build context: ./flouze-backend
│   │                # depends_on: db, redis
│   ├── db           # image: postgres:16-alpine
│   │                # volumes: pgdata:/var/lib/postgresql/data
│   └── redis        # image: redis:7-alpine
├── volumes:
│   ├── pgdata
│   └── exports      # fichiers générés PDF/Excel
└── .env             # DATABASE_URL, REDIS_URL, JWT_SECRET,
                     # GOOGLE_CLIENT_ID, EXCHANGERATE_API_KEY…
```

---

## 9. Choix Techniques Justifiés

| Composant | Choix retenu | Justification |
|-----------|-------------|---------------|
| Frontend framework  | React 18 + Vite           | Écosystème mature, Vite pour DX optimale |
| État serveur        | React Query (TanStack)    | Cache automatique, invalidation fine, synchronisation optimiste — élimine Redux pour la donnée serveur |
| État UI global      | Zustand                   | Léger, sans boilerplate, suffisant pour session user et préférences UI |
| Graphiques          | Recharts                  | Composants React natifs, customisables, bundle raisonnable |
| API framework       | FastAPI (Python 3.12)     | Async natif, validation Pydantic, OpenAPI auto, WebSocket natif |
| ORM                 | SQLAlchemy 2.0 + asyncpg  | Async I/O, mapping déclaratif, migrations Alembic |
| Base de données     | PostgreSQL 16             | JSONB, RLS, full-text search, ACID pour les finances |
| Cache / broker      | Redis 7                   | Dual rôle : cache taux de change + broker Pub/Sub WebSocket |
| Auth JWT            | python-jose + passlib     | Standards IETF, RS256, révocation via Redis |
| OAuth2              | Authlib                   | Robuste, supporte Google/GitHub, extensible |
| Taux de change      | exchangerate.host + Redis | Gratuit en V1, swappable, cache évite les timeouts réseau |
| Export PDF          | WeasyPrint                | HTML/CSS → PDF natif Python, sans dépendance binaire (Chromium) |
| Export Excel        | openpyxl                  | Standard de facto Python pour .xlsx |
| Import bancaire     | ofxparse + csv stdlib     | Léger, couvre OFX/QFX et CSV |
| Cron / tâches async | APScheduler (in-process)  | Suffit en V1, migreable vers Celery si charge augmente |
| Reverse proxy       | Nginx                     | Serving SPA + proxy /api/* + TLS en un seul conteneur |
| Orchestration local | Docker Compose v2         | Démarrage en une commande, reproductible, compatible VPS et cloud |
| Migrations DB       | Alembic                   | Versionning du schéma, rollback, intégré à SQLAlchemy |

---

## 10. Points d'Attention et Décisions Différées

### 10.1 Décisions à prendre avant le démarrage

| Sujet | Question ouverte |
|-------|-----------------|
| Hébergement production  | VPS (Hetzner, OVH) ou cloud managé (Railway, Render) — impact sur TLS et volumes persistants |
| Stockage justificatifs  | Volume Docker local ou S3-compatible (Cloudflare R2) — recommandé S3 si multi-instance |
| Multi-tenant futur      | Architecture row-level tient jusqu'à ~10 000 utilisateurs. Au-delà, envisager schéma PostgreSQL par organisation |
| Internationalisation    | i18next à prévoir si expansion hors Maroc |
| RGPD / CNDP             | Politique de rétention à définir — droit à l'oubli implique suppression physique, pas seulement soft delete |

### 10.2 Évolutions architecturales identifiées pour V2

- Remplacement d'APScheduler par **Celery + Redis Beat** si volume de tâches async augmente.
- Migration vers un stockage objet **S3-compatible** pour justificatifs et exports.
- Ajout d'un **CDN (Cloudflare)** devant Nginx pour les assets statiques React.
- **Vues matérialisées PostgreSQL** pour le dashboard si les agrégats deviennent coûteux.
- Pipeline **CI/CD (GitHub Actions)** avec déploiement automatique sur VPS via SSH.
- **Tests de charge (Locust)** sur `/dashboard` et `/expenses` avant mise en production.

---

*Architecture Technique Flouze v1.0 — Confidentiel — Avril 2026*
