"""
Schémas Pydantic v2 pour la validation des requêtes et réponses API.

Inclut le schéma d'extraction Gemini (SchemaExtractionFacture) utilisé
comme response_schema pour forcer la sortie JSON structurée de l'IA.
"""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field

from app.modeles import StatutFacture


# ============================================================
# Schéma d'extraction IA (envoyé à Gemini comme response_schema)
# ============================================================

class SchemaExtractionFacture(BaseModel):
    """
    Schéma de sortie structurée pour l'extraction IA Gemini.

    Ce schéma est passé en `response_schema` à l'API Gemini pour
    garantir une réponse JSON conforme et parseable.
    """

    nom_fournisseur: Optional[str] = Field(
        default=None,
        description="Nom ou raison sociale du fournisseur figurant sur la facture",
    )
    ice_fournisseur: Optional[str] = Field(
        default=None,
        description="ICE (Identifiant Commun de l'Entreprise) du fournisseur (15 chiffres)",
    )
    identifiant_fiscal: Optional[str] = Field(
        default=None,
        description="Identifiant fiscal (IF) du fournisseur",
    )
    registre_commerce: Optional[str] = Field(
        default=None,
        description="Numéro de registre de commerce (RC) du fournisseur",
    )
    date_facture: Optional[str] = Field(
        default=None,
        description="Date de la facture au format AAAA-MM-JJ",
    )
    montant_ht: Optional[float] = Field(
        default=None,
        description="Montant hors taxes en dirhams marocains (MAD)",
    )
    montant_tva: Optional[float] = Field(
        default=None,
        description="Montant de la TVA en dirhams marocains (MAD)",
    )
    taux_tva: Optional[float] = Field(
        default=None,
        description="Taux de TVA appliqué en pourcentage (ex: 20.0 pour 20%)",
    )
    montant_ttc: Optional[float] = Field(
        default=None,
        description="Montant toutes taxes comprises en dirhams marocains (MAD)",
    )
    code_compte_pcgm: Optional[str] = Field(
        default=None,
        description="Code du compte feuille PCGM le plus approprié pour cette facture",
    )
    libelle_compte_pcgm: Optional[str] = Field(
        default=None,
        description="Libellé du compte PCGM correspondant au code attribué",
    )


# ============================================================
# Schémas de réponse API
# ============================================================

class SchemaReponseFacture(BaseModel):
    """Schéma de réponse complet pour une facture."""

    id: int
    client_dossier_id: int
    chemin_fichier_original: str
    nom_fournisseur: Optional[str] = None
    ice_fournisseur: Optional[str] = None
    identifiant_fiscal: Optional[str] = None
    registre_commerce: Optional[str] = None
    date_facture: Optional[date] = None
    montant_ht: Optional[float] = None
    montant_tva: Optional[float] = None
    taux_tva: Optional[float] = None
    montant_ttc: Optional[float] = None
    code_compte_pcgm: Optional[str] = None
    libelle_compte_pcgm: Optional[str] = None
    score_confiance: float
    statut: StatutFacture
    date_creation: datetime
    date_export: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================
# Schémas de requête API
# ============================================================

class SchemaValidationFacture(BaseModel):
    """
    Schéma pour la validation/correction manuelle d'une facture.

    Tous les champs sont optionnels : seuls les champs fournis
    seront mis à jour lors de la validation.
    """

    nom_fournisseur: Optional[str] = None
    ice_fournisseur: Optional[str] = None
    identifiant_fiscal: Optional[str] = None
    registre_commerce: Optional[str] = None
    date_facture: Optional[date] = None
    montant_ht: Optional[float] = None
    montant_tva: Optional[float] = None
    taux_tva: Optional[float] = None
    montant_ttc: Optional[float] = None
    code_compte_pcgm: Optional[str] = None
    libelle_compte_pcgm: Optional[str] = None


class SchemaCreationClientDossier(BaseModel):
    """Schéma de création d'un nouveau dossier client."""

    nom_entreprise: str = Field(
        min_length=1,
        description="Raison sociale de l'entreprise",
    )
    ice: str = Field(
        min_length=15,
        max_length=15,
        description="ICE de l'entreprise (exactement 15 chiffres)",
    )


class SchemaReponseClientDossier(BaseModel):
    """Schéma de réponse pour un dossier client."""

    id: int
    nom_entreprise: str
    ice: str

    model_config = {"from_attributes": True}
