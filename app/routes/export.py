"""
Routes API pour l'export comptable au format Sage.

Endpoint :
    GET /api/v1/export/sage/{client_dossier_id} — Export CSV des factures validées
"""

import logging
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.base_donnees import obtenir_session
from app.modeles import Facture, ClientDossier, StatutFacture
from app.service_export import generer_csv_sage

logger = logging.getLogger("fiduia.routes.export")

routeur = APIRouter(prefix="/api/v1/export", tags=["Export Sage"])


@routeur.get(
    "/sage/{client_dossier_id}",
    summary="Exporter les factures validées au format CSV Sage",
    description="Génère un fichier CSV au format d'import Sage contenant les écritures "
                "comptables des factures validées pour le dossier client spécifié. "
                "Les factures exportées passent au statut EXPORTEE (anti-doublon).",
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Fichier CSV des écritures comptables Sage",
        },
        404: {"description": "Dossier client introuvable"},
        422: {"description": "Aucune facture validée à exporter"},
    },
)
async def exporter_sage(
    client_dossier_id: int,
    session: Session = Depends(obtenir_session),
):
    """
    Exporte les factures validées d'un dossier client au format CSV Sage.

    Workflow anti-doublon :
        1. Récupère EXCLUSIVEMENT les factures au statut VALIDE
        2. Génère le CSV avec les 3 lignes d'écriture par facture
        3. Passe les factures exportées au statut EXPORTEE
        4. Renseigne la date_export
        5. Retourne le CSV en StreamingResponse
    """
    # Vérifier que le dossier client existe
    client = session.get(ClientDossier, client_dossier_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier client introuvable (id={client_dossier_id})",
        )

    # Récupérer EXCLUSIVEMENT les factures VALIDE
    requete = select(Facture).where(
        Facture.client_dossier_id == client_dossier_id,
        Facture.statut == StatutFacture.VALIDE,
    )
    factures_validees = list(session.exec(requete).all())

    if not factures_validees:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Aucune facture validée à exporter pour le client #{client_dossier_id}. "
                   f"Validez d'abord les factures via POST /api/v1/factures/{{id}}/valider.",
        )

    # Générer le contenu CSV Sage
    contenu_csv = generer_csv_sage(factures_validees)

    # Anti-doublon : passer les factures au statut EXPORTEE
    maintenant = datetime.utcnow()
    for facture in factures_validees:
        facture.statut = StatutFacture.EXPORTEE
        facture.date_export = maintenant
        session.add(facture)

    session.commit()

    logger.info(
        f"Export Sage — Client #{client_dossier_id} ({client.nom_entreprise}) : "
        f"{len(factures_validees)} factures exportées"
    )

    # Nom du fichier CSV pour le téléchargement
    nom_fichier = f"export_sage_{client.nom_entreprise.replace(' ', '_')}_{maintenant.strftime('%Y%m%d_%H%M%S')}.csv"

    # Retourner le CSV en streaming
    return StreamingResponse(
        content=StringIO(contenu_csv),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{nom_fichier}"',
        },
    )
