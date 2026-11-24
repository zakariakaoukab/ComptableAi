"""
Modèles de base de données FiduIA.

Définit les tables SQLModel pour les dossiers clients et les factures,
ainsi que l'énumération des statuts de traitement des factures.
"""

import enum
from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class StatutFacture(str, enum.Enum):
    """Statuts possibles d'une facture dans le workflow de traitement."""

    EN_ATTENTE_VALIDATION = "EN_ATTENTE_VALIDATION"
    VALIDE = "VALIDE"
    EXPORTEE = "EXPORTEE"
    ECHEC_EXTRACTION = "ECHEC_EXTRACTION"
    REJETEE = "REJETEE"


class ClientDossier(SQLModel, table=True):
    """
    Dossier client représentant une entreprise marocaine.

    Chaque client possède un ICE (Identifiant Commun de l'Entreprise)
    de 15 chiffres, unique au Maroc.
    """

    __tablename__ = "client_dossier"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom_entreprise: str = Field(index=True, description="Raison sociale de l'entreprise")
    ice: str = Field(
        max_length=15,
        min_length=15,
        description="Identifiant Commun de l'Entreprise (15 chiffres)",
    )

    # Relation : un client possède plusieurs factures
    factures: list["Facture"] = Relationship(back_populates="client_dossier")


class Facture(SQLModel, table=True):
    """
    Facture extraite et imputée comptablement.

    Contient les données brutes extraites par Gemini, le code PCGM
    attribué, le score de confiance calculé, et le statut de validation.
    """

    __tablename__ = "facture"

    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Relation avec le dossier client ---
    client_dossier_id: int = Field(foreign_key="client_dossier.id", index=True)
    client_dossier: Optional[ClientDossier] = Relationship(back_populates="factures")

    # --- Fichier source ---
    chemin_fichier_original: str = Field(
        description="Chemin du fichier d'origine sauvegardé sur le volume Docker"
    )

    # --- Données fournisseur extraites ---
    nom_fournisseur: Optional[str] = Field(default=None, description="Nom du fournisseur")
    ice_fournisseur: Optional[str] = Field(default=None, description="ICE du fournisseur")
    identifiant_fiscal: Optional[str] = Field(default=None, description="Identifiant fiscal du fournisseur")
    registre_commerce: Optional[str] = Field(default=None, description="Numéro de registre de commerce")

    # --- Données financières extraites ---
    date_facture: Optional[date] = Field(default=None, description="Date de la facture (AAAA-MM-JJ)")
    montant_ht: Optional[float] = Field(default=None, description="Montant hors taxes")
    montant_tva: Optional[float] = Field(default=None, description="Montant de la TVA")
    taux_tva: Optional[float] = Field(default=None, description="Taux de TVA appliqué (%)")
    montant_ttc: Optional[float] = Field(default=None, description="Montant toutes taxes comprises")

    # --- Imputation comptable PCGM ---
    code_compte_pcgm: Optional[str] = Field(default=None, description="Code du compte PCGM attribué")
    libelle_compte_pcgm: Optional[str] = Field(default=None, description="Libellé du compte PCGM")

    # --- Qualité et statut ---
    score_confiance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de confiance de l'extraction (0.0 à 1.0)",
    )
    statut: StatutFacture = Field(
        default=StatutFacture.EN_ATTENTE_VALIDATION,
        description="Statut actuel de la facture dans le workflow",
    )

    # --- Horodatage ---
    date_creation: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date de création de l'enregistrement",
    )
    date_export: Optional[datetime] = Field(
        default=None,
        description="Date d'export vers Sage (renseignée lors de l'export CSV)",
    )
