"""
Service PCGM — Plan Comptable Général Marocain.

Charge et parse le fichier .toon contenant les 465 comptes feuilles du PCGM.
Fournit les fonctions de validation et de formatage pour le prompt Gemini.
"""

import logging
from pathlib import Path

logger = logging.getLogger("fiduia.pcgm")

# Dictionnaire global : {"6111": "Achats de marchandises groupe A", ...}
COMPTES_PCGM: dict[str, str] = {}


def charger_pcgm(chemin_fichier: str) -> None:
    """
    Parse le fichier .toon et charge les comptes PCGM en mémoire.

    Le fichier .toon a le format suivant :
        Ligne 1 : en-tête (ignorée) — accounts[465]{code,label,class,level}:
        Lignes 2+ : "  code,label,class,level"

    Les labels entre guillemets sont gérés correctement.

    Args:
        chemin_fichier: Chemin vers le fichier pcgm_invoice_mapping_leaf.toon

    Raises:
        FileNotFoundError: Si le fichier .toon n'est pas trouvé
    """
    global COMPTES_PCGM

    chemin = Path(chemin_fichier)
    if not chemin.exists():
        raise FileNotFoundError(
            f"Fichier PCGM introuvable : {chemin_fichier}. "
            f"Vérifiez que le fichier est présent dans le conteneur."
        )

    comptes_charges = {}

    with open(chemin, "r", encoding="utf-8") as fichier:
        lignes = fichier.readlines()

    for numero_ligne, ligne in enumerate(lignes, start=1):
        ligne = ligne.strip()

        # Ignorer la ligne d'en-tête et les lignes vides
        if not ligne or ligne.startswith("accounts["):
            continue

        # Parser la ligne : "code,label,class,level"
        # Le label peut contenir des virgules s'il est entre guillemets
        try:
            code, label = _parser_ligne_pcgm(ligne)
            comptes_charges[code] = label
        except ValueError as e:
            logger.warning(f"Ligne {numero_ligne} ignorée (format invalide) : {e}")
            continue

    COMPTES_PCGM.clear()
    COMPTES_PCGM.update(comptes_charges)
    logger.info(f"PCGM chargé avec succès : {len(COMPTES_PCGM)} comptes feuilles")


def _parser_ligne_pcgm(ligne: str) -> tuple[str, str]:
    """
    Parse une ligne du fichier .toon et retourne (code, label).

    Gère les labels entre guillemets contenant des virgules.

    Args:
        ligne: Ligne brute du fichier .toon (ex: '6111,Achats de marchandises,6,4')

    Returns:
        Tuple (code, label) — ex: ("6111", "Achats de marchandises")
    """
    ligne = ligne.strip()

    if not ligne:
        raise ValueError("Ligne vide")

    # Cas 1 : Label entre guillemets → "code,"label avec virgules",class,level"
    if '"' in ligne:
        # Extraire le code avant le premier guillemet
        premier_guillemet = ligne.index('"')
        partie_avant = ligne[:premier_guillemet].rstrip(",").strip()
        code = partie_avant

        # Extraire le label entre guillemets
        dernier_guillemet = ligne.rindex('"')
        label = ligne[premier_guillemet + 1 : dernier_guillemet]
    else:
        # Cas 2 : Pas de guillemets → split simple par virgule
        parties = ligne.split(",")
        if len(parties) < 2:
            raise ValueError(f"Format inattendu : {ligne}")
        code = parties[0].strip()
        label = parties[1].strip()

    if not code:
        raise ValueError(f"Code vide dans la ligne : {ligne}")

    return code, label


def valider_code_pcgm(code: str) -> bool:
    """
    Vérifie si un code PCGM existe dans le dictionnaire des comptes feuilles.

    La validation se fait EXCLUSIVEMENT par appartenance au dictionnaire,
    sans filtre sur la longueur du code (4 ou 5 chiffres sont valides).

    Args:
        code: Code PCGM à valider (ex: "6111", "61251")

    Returns:
        True si le code est un compte feuille PCGM valide
    """
    return code in COMPTES_PCGM


def obtenir_libelle_pcgm(code: str) -> str:
    """
    Retourne le libellé d'un code PCGM.

    Args:
        code: Code PCGM (ex: "6111")

    Returns:
        Libellé du compte ou chaîne vide si non trouvé
    """
    return COMPTES_PCGM.get(code, "")


def obtenir_liste_pcgm_pour_prompt() -> str:
    """
    Formate la liste complète des comptes PCGM pour injection dans le prompt Gemini.

    Returns:
        Chaîne formatée avec un compte par ligne : "code : label"
    """
    lignes = [f"{code} : {label}" for code, label in sorted(COMPTES_PCGM.items())]
    return "\n".join(lignes)
