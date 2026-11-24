"""
Routes API pour la gestion des factures.

Endpoints :
    POST /api/v1/factures/extraire     — Upload et extraction IA d'une facture
    POST /api/v1/factures/{id}/valider — Validation/correction manuelle
    POST /api/v1/clients/              — Création d'un dossier client
    GET  /api/v1/clients/              — Liste des dossiers clients
"""

import uuid
import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlmodel import Session, select
from PIL import Image

from app.config import parametres
from app.base_donnees import obtenir_session
from app.modeles import Facture, ClientDossier, StatutFacture
from app.schemas import (
    SchemaReponseFacture,
    SchemaValidationFacture,
    SchemaCreationClientDossier,
    SchemaReponseClientDossier,
)
from app.service_gemini import extraire_facture_avec_gemini
from app.service_pcgm import valider_code_pcgm, obtenir_libelle_pcgm, COMPTES_PCGM

logger = logging.getLogger("fiduia.routes.factures")

routeur = APIRouter(prefix="/api/v1", tags=["Factures"])

# Extensions de fichiers image acceptées
EXTENSIONS_ACCEPTEES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".pdf"}


def calculer_score_confiance(
    montant_ht: float | None,
    montant_tva: float | None,
    montant_ttc: float | None,
    code_compte_pcgm: str | None,
) -> tuple[float, str | None, str | None]:
    """
    Calcule le score de confiance déterministe de l'extraction.

    Algorithme :
        - Score de base = 1.0
        - Pénalité -0.4 si abs((HT + TVA) - TTC) > 1.0 MAD
        - Pénalité -0.3 si le code PCGM n'est pas dans COMPTES_PCGM → forcer à 6111
        - Résultat clampé entre 0.0 et 1.0

    Args:
        montant_ht: Montant hors taxes extrait
        montant_tva: Montant TVA extrait
        montant_ttc: Montant TTC extrait
        code_compte_pcgm: Code PCGM attribué par Gemini

    Returns:
        Tuple (score, code_pcgm_corrigé, libellé_pcgm_corrigé)
    """
    score = 1.0
    code_corrige = code_compte_pcgm
    libelle_corrige = None

    # Vérification de la cohérence des montants
    if montant_ht is not None and montant_tva is not None and montant_ttc is not None:
        ecart = abs((montant_ht + montant_tva) - montant_ttc)
        if ecart > 1.0:
            score -= 0.4
            logger.warning(
                f"Incohérence montants détectée : HT({montant_ht}) + TVA({montant_tva}) "
                f"= {montant_ht + montant_tva} ≠ TTC({montant_ttc}), écart = {ecart:.2f} MAD"
            )

    # Validation du code PCGM
    if code_compte_pcgm and not valider_code_pcgm(code_compte_pcgm):
        score -= 0.3
        logger.warning(
            f"Code PCGM invalide '{code_compte_pcgm}' → forcé à '6111' "
            f"(Achats de marchandises groupe A)"
        )
        code_corrige = "6111"
    elif not code_compte_pcgm:
        score -= 0.3
        code_corrige = "6111"

    # Mettre à jour le libellé selon le code corrigé
    if code_corrige:
        libelle_corrige = obtenir_libelle_pcgm(code_corrige)

    # Clamper le score entre 0.0 et 1.0
    score = max(0.0, min(1.0, score))

    return score, code_corrige, libelle_corrige


# ============================================================
# Endpoint : Extraction IA d'une facture
# ============================================================

@routeur.post(
    "/factures/extraire",
    response_model=SchemaReponseFacture,
    status_code=status.HTTP_201_CREATED,
    summary="Extraire et imputer une facture via IA",
    description="Upload une image de facture, l'envoie à Gemini 2.0 Flash pour extraction, "
                "calcule le score de confiance et enregistre le tout en base de données.",
)
async def extraire_facture(
    fichier: UploadFile = File(..., description="Image de la facture (JPG, PNG, PDF)"),
    client_dossier_id: int = Form(..., description="ID du dossier client"),
    session: Session = Depends(obtenir_session),
):
    """
    Endpoint principal d'extraction de facture.

    Workflow :
        1. Vérifie l'existence du dossier client
        2. Sauvegarde le fichier uploadé sur le volume Docker
        3. Ouvre et redimensionne l'image avec Pillow
        4. Appelle Gemini 2.0 Flash pour l'extraction structurée
        5. Calcule le score de confiance déterministe
        6. Enregistre la facture en base de données
    """
    # Vérifier que le dossier client existe
    client = session.get(ClientDossier, client_dossier_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier client introuvable (id={client_dossier_id})",
        )

    # Vérifier l'extension du fichier
    nom_fichier = fichier.filename or "inconnu"
    extension = Path(nom_fichier).suffix.lower()
    if extension not in EXTENSIONS_ACCEPTEES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format de fichier non supporté : '{extension}'. "
                   f"Formats acceptés : {', '.join(EXTENSIONS_ACCEPTEES)}",
        )

    # ---- Étape 1 : Persistance du document uploadé ----
    identifiant_unique = uuid.uuid4().hex
    nom_fichier_stocke = f"{identifiant_unique}{extension}"
    dossier_stockage = Path(parametres.DOSSIER_STOCKAGE_UPLOADS)
    dossier_stockage.mkdir(parents=True, exist_ok=True)
    chemin_fichier = dossier_stockage / nom_fichier_stocke

    contenu_fichier = await fichier.read()
    with open(chemin_fichier, "wb") as f:
        f.write(contenu_fichier)

    logger.info(f"Fichier sauvegardé : {chemin_fichier} ({len(contenu_fichier)} octets)")

    # ---- Étape 2 : Extraction IA avec résilience ----
    try:
        # Ouvrir l'image avec Pillow
        image_pil = Image.open(chemin_fichier)

        # Convertir en RGB si nécessaire (ex: PNG avec transparence)
        if image_pil.mode not in ("RGB", "L"):
            image_pil = image_pil.convert("RGB")

        # Appeler Gemini pour l'extraction
        extraction = extraire_facture_avec_gemini(image_pil)

    except Exception as erreur:
        # Résilience : enregistrer avec statut ECHEC_EXTRACTION
        logger.error(f"Échec de l'extraction IA : {erreur}", exc_info=True)

        facture_echec = Facture(
            client_dossier_id=client_dossier_id,
            chemin_fichier_original=str(chemin_fichier),
            statut=StatutFacture.ECHEC_EXTRACTION,
            score_confiance=0.0,
        )
        session.add(facture_echec)
        session.commit()
        session.refresh(facture_echec)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "L'extraction IA a échoué. La facture a été enregistrée avec le statut ECHEC_EXTRACTION.",
                "facture_id": facture_echec.id,
                "erreur": str(erreur),
            },
        )

    # ---- Étape 3 : Calcul du score de confiance ----
    score, code_pcgm_final, libelle_pcgm_final = calculer_score_confiance(
        montant_ht=extraction.montant_ht,
        montant_tva=extraction.montant_tva,
        montant_ttc=extraction.montant_ttc,
        code_compte_pcgm=extraction.code_compte_pcgm,
    )

    # Parser la date de facture (Gemini retourne une chaîne AAAA-MM-JJ)
    date_facture_parsee = None
    if extraction.date_facture:
        try:
            date_facture_parsee = date.fromisoformat(extraction.date_facture)
        except ValueError:
            logger.warning(f"Date de facture non parseable : '{extraction.date_facture}'")

    # ---- Étape 4 : Enregistrement en base de données ----
    facture = Facture(
        client_dossier_id=client_dossier_id,
        chemin_fichier_original=str(chemin_fichier),
        nom_fournisseur=extraction.nom_fournisseur,
        ice_fournisseur=extraction.ice_fournisseur,
        identifiant_fiscal=extraction.identifiant_fiscal,
        registre_commerce=extraction.registre_commerce,
        date_facture=date_facture_parsee,
        montant_ht=extraction.montant_ht,
        montant_tva=extraction.montant_tva,
        taux_tva=extraction.taux_tva,
        montant_ttc=extraction.montant_ttc,
        code_compte_pcgm=code_pcgm_final,
        libelle_compte_pcgm=libelle_pcgm_final or extraction.libelle_compte_pcgm,
        score_confiance=score,
        statut=StatutFacture.EN_ATTENTE_VALIDATION,
    )

    session.add(facture)
    session.commit()
    session.refresh(facture)

    logger.info(
        f"Facture #{facture.id} créée — Score : {score:.2f}, "
        f"PCGM : {code_pcgm_final}, Statut : {facture.statut}"
    )

    return facture


# ============================================================
# Endpoint : Validation/correction manuelle d'une facture
# ============================================================

@routeur.post(
    "/factures/{facture_id}/valider",
    response_model=SchemaReponseFacture,
    summary="Valider ou corriger une facture",
    description="Met à jour une facture avec les corrections manuelles du comptable "
                "et passe son statut à VALIDE.",
)
async def valider_facture(
    facture_id: int,
    corrections: SchemaValidationFacture,
    session: Session = Depends(obtenir_session),
):
    """
    Endpoint de validation manuelle.

    Le comptable peut corriger les champs extraits par l'IA
    avant de valider définitivement la facture.
    """
    facture = session.get(Facture, facture_id)
    if not facture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facture introuvable (id={facture_id})",
        )

    # Appliquer les corrections fournies (seuls les champs non-None sont mis à jour)
    donnees_corrections = corrections.model_dump(exclude_unset=True)

    for champ, valeur in donnees_corrections.items():
        setattr(facture, champ, valeur)

    # Passer le statut à VALIDE
    facture.statut = StatutFacture.VALIDE

    session.add(facture)
    session.commit()
    session.refresh(facture)

    logger.info(
        f"Facture #{facture_id} validée — "
        f"Champs corrigés : {list(donnees_corrections.keys())}"
    )

    return facture


# ============================================================
# Endpoints : Gestion des dossiers clients
# ============================================================

@routeur.post(
    "/clients/",
    response_model=SchemaReponseClientDossier,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un dossier client",
    description="Enregistre un nouveau dossier client avec son ICE.",
)
async def creer_client_dossier(
    client: SchemaCreationClientDossier,
    session: Session = Depends(obtenir_session),
):
    """Crée un nouveau dossier client en base de données."""
    nouveau_client = ClientDossier(
        nom_entreprise=client.nom_entreprise,
        ice=client.ice,
    )
    session.add(nouveau_client)
    session.commit()
    session.refresh(nouveau_client)

    logger.info(f"Client #{nouveau_client.id} créé : {nouveau_client.nom_entreprise}")
    return nouveau_client


@routeur.get(
    "/clients/",
    response_model=list[SchemaReponseClientDossier],
    summary="Lister les dossiers clients",
    description="Retourne la liste de tous les dossiers clients enregistrés.",
)
async def lister_clients(session: Session = Depends(obtenir_session)):
    """Retourne tous les dossiers clients."""
    clients = session.exec(select(ClientDossier)).all()
    return clients
