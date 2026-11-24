"""
Point d'entrée principal de l'application FiduIA.

Configure FastAPI avec :
    - Lifespan : initialisation de la BDD et chargement du PCGM au démarrage
    - CORS : autorisé pour le développement local
    - Routeurs : montage des routes factures et export
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import parametres
from app.base_donnees import creer_tables
from app import service_pcgm
from app.routes.factures import routeur as routeur_factures
from app.routes.export import routeur as routeur_export

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fiduia.main")


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application (lifespan).

    Au démarrage :
        1. Crée les tables en base de données (si inexistantes)
        2. Charge les 465 comptes PCGM depuis le fichier .toon
        3. Crée le dossier de stockage des uploads (si inexistant)
    """
    logger.info("=" * 60)
    logger.info("  FiduIA — Démarrage de l'application")
    logger.info("=" * 60)

    # Étape 1 : Initialisation de la base de données
    logger.info("Initialisation de la base de données...")
    creer_tables()
    logger.info("Tables créées avec succès ✓")

    # Étape 2 : Chargement du Plan Comptable Général Marocain
    chemin_pcgm = Path("/app/pcgm_invoice_mapping_leaf.toon")
    # Fallback pour le développement local (hors Docker)
    if not chemin_pcgm.exists():
        chemin_pcgm = Path(__file__).parent.parent / "pcgm_invoice_mapping_leaf.toon"

    logger.info(f"Chargement du PCGM depuis : {chemin_pcgm}")
    service_pcgm.charger_pcgm(str(chemin_pcgm))
    logger.info(f"PCGM chargé : {len(service_pcgm.COMPTES_PCGM)} comptes feuilles ✓")

    # Étape 3 : Création du dossier de stockage
    dossier_uploads = Path(parametres.DOSSIER_STOCKAGE_UPLOADS)
    dossier_uploads.mkdir(parents=True, exist_ok=True)
    logger.info(f"Dossier de stockage prêt : {dossier_uploads} ✓")

    logger.info("=" * 60)
    logger.info("  FiduIA — Application prête à recevoir des requêtes")
    logger.info("=" * 60)

    yield  # L'application est en cours d'exécution

    # Nettoyage à l'arrêt (si nécessaire)
    logger.info("FiduIA — Arrêt de l'application")


# ============================================================
# Instance FastAPI
# ============================================================

app = FastAPI(
    title="FiduIA — Imputation Comptable Intelligente",
    description=(
        "API de traitement automatisé des factures marocaines.\n\n"
        "**Fonctionnalités :**\n"
        "- 📄 Extraction IA des données de factures via Google Gemini 2.0 Flash\n"
        "- 🏛️ Imputation comptable automatique selon le PCGM (465 comptes feuilles)\n"
        "- ✅ Validation manuelle avec corrections du comptable\n"
        "- 📊 Export CSV au format Sage avec écritures comptables\n"
        "- 🛡️ Score de confiance déterministe pour chaque extraction\n"
    ),
    version="1.0.0",
    lifespan=cycle_de_vie,
)

# ---- Middleware CORS (développement) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Montage des routeurs ----
app.include_router(routeur_factures)
app.include_router(routeur_export)


# ---- Endpoint de santé ----
@app.get(
    "/",
    tags=["Santé"],
    summary="Vérification de santé",
    description="Endpoint de vérification que l'API est opérationnelle.",
)
async def verification_sante():
    """Retourne le statut de santé de l'application."""
    return {
        "statut": "opérationnel",
        "application": "FiduIA",
        "version": "1.0.0",
        "comptes_pcgm_charges": len(service_pcgm.COMPTES_PCGM),
    }
