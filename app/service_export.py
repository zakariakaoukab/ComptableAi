"""
Service d'export — Génération de fichiers CSV au format Sage.

Produit les écritures comptables conformes au format d'import Sage
à partir des factures validées, avec la logique TVA marocaine.
"""

import csv
import io
import logging
from typing import Optional

from app.modeles import Facture

logger = logging.getLogger("fiduia.export")

# Colonnes du fichier CSV Sage
COLONNES_CSV_SAGE = [
    "Code_Journal",
    "Date",
    "N_Compte",
    "N_Piece",
    "Libelle",
    "Debit",
    "Credit",
]

# Code journal par défaut pour les achats
CODE_JOURNAL_ACHATS = "ACH"


def determiner_compte_tva(code_compte_pcgm: str) -> str:
    """
    Détermine le compte de TVA récupérable selon la classe du compte PCGM.

    Logique :
        - Classe 2 (immobilisations) → 34551 (TVA récupérable sur immobilisations)
        - Autres classes → 34552 (TVA récupérable sur charges)

    Args:
        code_compte_pcgm: Code du compte PCGM de la facture

    Returns:
        Code du compte TVA ("34551" ou "34552")
    """
    if code_compte_pcgm and code_compte_pcgm.startswith("2"):
        return "34551"
    return "34552"


def formater_date_sage(date_facture) -> str:
    """
    Formate une date pour le fichier CSV Sage (JJ/MM/AAAA).

    Args:
        date_facture: Objet date de la facture

    Returns:
        Date formatée en chaîne JJ/MM/AAAA ou chaîne vide si None
    """
    if date_facture is None:
        return ""
    return date_facture.strftime("%d/%m/%Y")


def generer_csv_sage(factures: list[Facture]) -> str:
    """
    Génère un fichier CSV au format d'import Sage pour les factures validées.

    Pour chaque facture, 3 lignes d'écriture comptable sont générées :
        1. Crédit du compte fournisseur (4411) pour le montant TTC
        2. Débit du compte PCGM pour le montant HT
        3. Débit du compte TVA (34551 ou 34552) pour le montant TVA

    Args:
        factures: Liste des factures validées à exporter

    Returns:
        Contenu CSV complet sous forme de chaîne de caractères
    """
    buffer = io.StringIO()
    ecrivain = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # En-tête
    ecrivain.writerow(COLONNES_CSV_SAGE)

    for facture in factures:
        date_formatee = formater_date_sage(facture.date_facture)
        numero_piece = f"FACT-{facture.id:06d}"
        libelle = f"{facture.nom_fournisseur or 'Fournisseur'} - Facture {numero_piece}"

        # Déterminer le compte TVA selon la classe du compte PCGM
        compte_tva = determiner_compte_tva(facture.code_compte_pcgm or "6111")

        # Ligne 1 : Crédit fournisseur (4411) — Montant TTC
        ecrivain.writerow([
            CODE_JOURNAL_ACHATS,
            date_formatee,
            "4411",
            numero_piece,
            libelle,
            "",                                            # Débit vide
            f"{facture.montant_ttc:.2f}" if facture.montant_ttc else "0.00",  # Crédit
        ])

        # Ligne 2 : Débit compte PCGM — Montant HT
        ecrivain.writerow([
            CODE_JOURNAL_ACHATS,
            date_formatee,
            facture.code_compte_pcgm or "6111",
            numero_piece,
            libelle,
            f"{facture.montant_ht:.2f}" if facture.montant_ht else "0.00",   # Débit
            "",                                            # Crédit vide
        ])

        # Ligne 3 : Débit TVA récupérable — Montant TVA
        ecrivain.writerow([
            CODE_JOURNAL_ACHATS,
            date_formatee,
            compte_tva,
            numero_piece,
            libelle,
            f"{facture.montant_tva:.2f}" if facture.montant_tva else "0.00",  # Débit
            "",                                            # Crédit vide
        ])

    contenu_csv = buffer.getvalue()
    logger.info(f"CSV Sage généré : {len(factures)} factures, {len(factures) * 3} écritures")
    return contenu_csv
