# Spécifications Fonctionnelles — Flouze
### Application de Suivi des Dépenses · v1.0 · Avril 2026
> Document de cadrage fonctionnel — Pour validation client et équipe technique

---

## 1. Contexte et Objectifs

Ce document décrit les spécifications fonctionnelles de l'application web de suivi des dépenses Flouze. Il constitue la référence partagée entre le client et l'équipe de réalisation pour valider le périmètre de la version initiale (V1).

### 1.1 Objectif principal

Fournir à des utilisateurs — particuliers ou professionnels — un outil centralisé, collaboratif et multidevise permettant d'enregistrer, catégoriser, analyser et maîtriser leurs dépenses en temps réel.

### 1.2 Problèmes résolus

- Absence de vision consolidée des dépenses personnelles et professionnelles.
- Difficulté à suivre des budgets partagés au sein d'un foyer ou d'une équipe.
- Manque d'alertes proactives en cas de dépassement de budget.
- Saisie manuelle répétitive des dépenses récurrentes (abonnements, loyers...).
- Impossibilité d'importer des relevés bancaires pour éviter la double saisie.

### 1.3 Portée du document

> Ce document couvre exclusivement le cadrage fonctionnel (besoins métier, utilisateurs, fonctionnalités et priorités). Les choix d'architecture, de stack technique et d'implémentation font l'objet d'un document séparé (`archi_technique_flouze.md`).

---

## 2. Utilisateurs Cibles

L'application est conçue pour deux profils principaux qui peuvent coexister au sein d'un même espace partagé :

| Profil | Description | Cas d'usage typique |
|--------|-------------|---------------------|
| **Particulier** | Gestion du budget du foyer, dépenses personnelles | Couple partageant le suivi des courses, loyers, loisirs |
| **Professionnel / Freelance** | Suivi des frais professionnels, multi-devises, export comptable | Équipe partageant un budget projet, frais de déplacement |

Chaque utilisateur dispose de son propre compte. Les **espaces partagés** permettent à plusieurs membres (couple, équipe) de contribuer à un même suivi commun avec des droits configurables.

---

## 3. Fonctionnalités et Priorités

Les fonctionnalités sont classées selon trois niveaux de priorité pour la V1 :

- **P1 – Essentiel :** valeur minimale sans laquelle l'application ne peut pas fonctionner.
- **P2 – Important :** fortement attendu par le client, inclus si la charge le permet.
- **P3 – Souhaitable :** à planifier en V2 si non réalisable dans les délais.

| Fonctionnalité | Priorité | Description courte |
|----------------|----------|--------------------|
| Enregistrement d'une dépense | **P1 – Essentiel** | Saisie : titre, montant, date, catégorie, devise, notes |
| Gestion des catégories | **P1 – Essentiel** | Créer, modifier, supprimer des catégories personnalisées |
| Tableau de bord analytique | **P1 – Essentiel** | Vue synthétique des dépenses avec graphiques |
| Gestion des comptes utilisateurs | **P1 – Essentiel** | Inscription, connexion, profil, espaces partagés |
| Budget prévisionnel par catégorie | **P2 – Important** | Définir un plafond mensuel par catégorie |
| Alertes et notifications | **P2 – Important** | Notification en cas de dépassement de budget |
| Dépenses récurrentes | **P2 – Important** | Automatiser les dépenses répétitives (loyers, abonnements) |
| Export des données | **P2 – Important** | Télécharger les données en PDF ou Excel |
| Multi-devises | **P2 – Important** | Saisie en devises différentes avec conversion automatique |
| Import de relevés bancaires | **P3 – Souhaitable** | Importer un fichier CSV/OFX bancaire pour pré-remplir |

---

## 4. Détail des Fonctionnalités Prioritaires

### 4.1 Enregistrement d'une dépense (P1)

- Formulaire de saisie : titre, montant, devise, date (sélecteur), catégorie (liste), notes libres optionnelles.
- Possibilité d'attacher une photo de justificatif (ticket de caisse, facture).
- Modification et suppression d'une dépense existante.
- Attribution à un espace personnel ou partagé.

### 4.2 Gestion des catégories (P1)

- Catégories prédéfinies fournies par défaut (Alimentation, Transport, Logement, Loisirs, Santé, Professionnel...).
- Création de catégories personnalisées avec nom, icône (emoji) et couleur.
- Possibilité d'archiver une catégorie sans supprimer les dépenses associées.

### 4.3 Tableau de bord analytique (P1)

- Vue récapitulative : total du mois, évolution vs mois précédent, top catégories.
- Graphique en secteurs (répartition par catégorie) et en barres (évolution mensuelle).
- Filtres : période, catégorie, espace (personnel / partagé).
- Indicateur visuel de progression budget vs dépenses réelles par catégorie.

### 4.4 Espaces partagés et gestion des membres (P1)

- Création d'un espace partagé avec invitation par e-mail.
- Rôles : **Administrateur** (lecture + écriture + gestion membres) et **Membre** (lecture + écriture).
- Chaque utilisateur conserve un espace personnel distinct et privé.

### 4.5 Budget prévisionnel et alertes (P2)

- Définir un budget mensuel global et/ou par catégorie.
- Alerte déclenchée à 80% du budget atteint (seuil configurable).
- Alerte de dépassement lors de la saisie d'une dépense qui franchit le plafond.
- Notifications in-app et par e-mail (selon préférence utilisateur).

### 4.6 Dépenses récurrentes (P2)

- Définir une dépense récurrente : montant, catégorie, fréquence (hebdo, mensuelle, annuelle), date de début.
- Génération automatique de la dépense selon la fréquence choisie.
- Possibilité de suspendre ou arrêter une récurrence.

### 4.7 Export des données (P2)

- Export PDF : rapport mensuel ou personnalisé avec graphiques et tableaux.
- Export Excel : données brutes filtrables par période et catégorie.
- Export accessible depuis le tableau de bord et depuis la liste des dépenses.

### 4.8 Multi-devises (P2)

- Saisie d'une dépense dans n'importe quelle devise.
- Conversion automatique vers la devise de référence du compte (taux de change quotidien).
- Affichage du montant d'origine et du montant converti.

---

## 5. User Stories Principales

| En tant que... | Je veux... | Afin de... |
|----------------|-----------|------------|
| Utilisateur connecté | enregistrer rapidement une dépense depuis mon téléphone | ne pas oublier une dépense faite en déplacement |
| Membre d'un espace partagé | voir les dépenses saisies par mon partenaire/équipe | avoir une vision commune et éviter les doublons |
| Utilisateur | définir un budget mensuel par catégorie | contrôler mes postes de dépenses prioritaires |
| Utilisateur | recevoir une alerte quand je dépasse mon budget | réagir avant de perdre le contrôle de mes finances |
| Freelance | saisir des dépenses en devise étrangère | suivre mes frais de missions à l'international |
| Utilisateur | télécharger un rapport PDF de mes dépenses | le partager avec mon comptable ou le conserver |
| Utilisateur | créer une dépense récurrente (loyer) | ne pas avoir à la saisir manuellement chaque mois |
| Administrateur d'espace | inviter un membre et gérer ses accès | contrôler qui peut voir et modifier les dépenses partagées |

---

## 6. Périmètre V1 et Exclusions

| ✅ Inclus en V1 | ❌ Hors périmètre V1 (V2+) |
|-----------------|--------------------------|
| Saisie et gestion des dépenses | Connexion directe aux comptes bancaires (Open Banking) |
| Catégories personnalisées | Application mobile native (iOS / Android) |
| Tableau de bord avec graphiques | Gestion multi-organisations (SaaS) |
| Espaces partagés | Intelligence artificielle de catégorisation automatique |
| Budgets prévisionnels et alertes | Gestion de revenus et de patrimoine |
| Dépenses récurrentes | Module de facturation client |
| Export PDF et Excel | Gestion des notes de frais avec workflow de validation |
| Multi-devises | |

> **Note :** L'import de relevés bancaires (CSV/OFX) est classé P3. Il sera intégré en V1 si la charge estimée le permet, sinon reporté en V2.

---

## 7. Hypothèses et Points en Suspens

### 7.1 Hypothèses retenues

- La devise de référence du compte est configurable par l'utilisateur lors de l'inscription.
- Les taux de change sont fournis par une API publique (ex. Open Exchange Rates) et mis à jour quotidiennement.
- L'application est accessible via navigateur desktop et mobile (responsive design).
- Les données sont hébergées de manière sécurisée avec sauvegarde régulière.
- La langue de l'interface est le français pour la V1.

### 7.2 Points en suspens à valider avec le client

- Nombre maximum de membres par espace partagé.
- Politique de rétention des données (durée de conservation des dépenses archivées).
- Modèle de facturation de l'application (gratuit, freemium, abonnement).
- Exigences de conformité RGPD ou réglementations locales (CNDP Maroc) applicables.
- Formats bancaires supportés pour l'import (CSV, OFX, QIF...).

---

*Document confidentiel — Spécifications fonctionnelles v1.0 — Avril 2026*
