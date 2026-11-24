# FiduIA — MVP Backend FastAPI

FiduIA est un backend professionnel de traitement comptable automatisé. Il extrait intelligemment les données des factures marocaines à l'aide de l'IA (Google Gemini 2.5 Flash Vision) et réalise une imputation comptable automatique selon le Plan Comptable Général Marocain (PCGM). L'application génère ensuite des écritures comptables compatibles avec les standards d'import du logiciel Sage.

##  Fonctionnalités

- **Extraction IA des factures** : Analyse des images et PDF via Google Gemini 2.5 Flash (Nouveau SDK google-genai) pour extraire les montants (HT, TVA, TTC) et les informations fournisseur (ICE, RC, IF, Nom).
- **Imputation Comptable (PCGM)** : Attribution automatique du compte comptable feuille approprié parmi les 465 comptes du référentiel PCGM inclus.
- **Score de Confiance Déterministe** : Algorithme vérifiant la cohérence mathématique des montants extraits (HT + TVA = TTC) et la validité du compte PCGM.
- **Validation Humaine** : Endpoint dédié pour qu'un comptable puisse corriger et valider manuellement les données avant export.
- **Export Sage** : Génération de fichiers CSV conformes au format d'import Sage, incluant la logique TVA marocaine (classe 2 pour les immobilisations).
- **Architecture Conteneurisée** : Déploiement simplifié via Docker et Docker Compose.

## 🛠️ Stack Technique

- **Framework Web** : FastAPI
- **Base de Données** : PostgreSQL 15, interfacé via SQLModel / SQLAlchemy
- **IA** : Google GenAI SDK (`google-genai`), modèle `gemini-2.5-flash`
- **Validation** : Pydantic v2 (Pydantic-Settings pour l'environnement)
- **Traitement d'Image** : Pillow (PIL)
- **Déploiement** : Docker & Docker Compose

##  Installation & Démarrage (Local)

### 1. Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et en cours d'exécution.
- Une clé API Google Gemini (générée via [Google AI Studio](https://aistudio.google.com/)).

### 2. Configuration
Créez un fichier `.env` à la racine du projet (vous pouvez copier `.env.example`) :

```env
# URL de connexion PostgreSQL (Docker)
DATABASE_URL=postgresql://fiduia_user:fiduia_pass@db:5432/fiduia_db

# Votre clé API Google Gemini (Ex: AQ.Ab8RN...)
GEMINI_API_KEY=votre_cle_api_ici

# Dossier interne du conteneur pour les uploads
DOSSIER_STOCKAGE_UPLOADS=/app/stockage_fichiers
```

### 3. Lancement
Démarrez les conteneurs PostgreSQL et FastAPI avec Docker Compose :

```bash
docker-compose up --build -d
```

### 4. Accès à l'Application
- **Documentation interactive Swagger** : [http://localhost:8000/docs](http://localhost:8000/docs)
- Les modifications du code dans le dossier `app/` sont synchronisées en temps réel dans le conteneur pour faciliter le développement.

##  API Endpoints

Voici les principales routes de l'API :

### Gestion des Dossiers Clients
- `POST /api/v1/clients/` : Créer un nouveau dossier client (Nom, ICE).
- `GET /api/v1/clients/` : Lister les dossiers clients existants.

### Traitement des Factures
- `POST /api/v1/factures/extraire` : Uploader une facture (Image/PDF). L'IA extrait les données, attribue un code PCGM, et sauvegarde le document.
- `POST /api/v1/factures/{id}/valider` : Valider ou corriger manuellement les champs d'une facture. Le statut passe à `VALIDE`.

### Export Comptable
- `GET /api/v1/export/sage/{client_dossier_id}` : Télécharge un fichier CSV contenant les écritures comptables Sage (Crédit Fournisseur, Débit Charge, Débit TVA) de toutes les factures validées non encore exportées.

##  Structure du Projet

```text
Comptable Ai/
├── .env.example                      # Template des variables d'environnement
├── Dockerfile                        # Configuration de l'image Python
├── docker-compose.yml                # Configuration des services (api + db)
├── requirements.txt                  # Dépendances Python
├── pcgm_invoice_mapping_leaf.toon    # Base de données brute des 465 comptes PCGM
└── app/
    ├── main.py                       # Point d'entrée FastAPI (Lifespan, Routeurs)
    ├── config.py                     # Chargement robuste de l'environnement
    ├── base_donnees.py               # Engine SQLAlchemy
    ├── modeles.py                    # Tables de la BDD (Client, Facture)
    ├── schemas.py                    # Définitions Pydantic
    ├── service_gemini.py             # Logique d'appel IA (Prompt, Redimensionnement)
    ├── service_pcgm.py               # Parsing du fichier .toon
    ├── service_export.py             # Logique de génération CSV Sage
    └── routes/                       # Contrôleurs API (factures, export)
```
