"""
Service Gemini — Extraction IA des factures via Google Gemini 2.0 Flash.

Utilise le nouveau SDK google-genai (2025/2026) pour envoyer une image
de facture et obtenir une extraction JSON structurée conforme au PCGM.
"""

import json
import logging
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from app.config import parametres
from app.schemas import SchemaExtractionFacture
from app.service_pcgm import obtenir_liste_pcgm_pour_prompt

logger = logging.getLogger("fiduia.gemini")

# Client Gemini initialisé au niveau du module
_client_gemini: genai.Client | None = None


def obtenir_client_gemini() -> genai.Client:
    """Retourne le client Gemini, initialisé de manière paresseuse (lazy)."""
    global _client_gemini
    if _client_gemini is None:
        _client_gemini = genai.Client(api_key=parametres.GEMINI_API_KEY)
        logger.info("Client Gemini initialisé avec succès")
    return _client_gemini


def redimensionner_image(image_pil: Image.Image, taille_max: int = 1500) -> Image.Image:
    """
    Redimensionne une image en conservant le ratio d'aspect.

    Si aucune dimension ne dépasse taille_max, l'image est retournée telle quelle.

    Args:
        image_pil: Image PIL à redimensionner
        taille_max: Dimension maximale en pixels (largeur ou hauteur)

    Returns:
        Image PIL redimensionnée (ou originale si déjà assez petite)
    """
    largeur, hauteur = image_pil.size

    if largeur <= taille_max and hauteur <= taille_max:
        return image_pil

    # Calculer le ratio de redimensionnement
    ratio = min(taille_max / largeur, taille_max / hauteur)
    nouvelle_largeur = int(largeur * ratio)
    nouvelle_hauteur = int(hauteur * ratio)

    image_redim = image_pil.resize(
        (nouvelle_largeur, nouvelle_hauteur),
        Image.LANCZOS,
    )
    logger.info(
        f"Image redimensionnée : {largeur}x{hauteur} → {nouvelle_largeur}x{nouvelle_hauteur}"
    )
    return image_redim


def construire_prompt_systeme() -> str:
    """
    Construit le prompt système complet pour l'extraction de facture.

    Inclut la liste des comptes PCGM et les instructions d'extraction.

    Returns:
        Prompt système formaté en français
    """
    liste_pcgm = obtenir_liste_pcgm_pour_prompt()

    prompt = f"""Tu es un expert-comptable marocain spécialisé dans l'analyse de factures.

MISSION : Analyse l'image de la facture fournie et extrais TOUTES les informations demandées en JSON structuré.

INSTRUCTIONS D'EXTRACTION :
1. Extrais les informations du fournisseur : nom, ICE (15 chiffres), identifiant fiscal, registre de commerce.
2. Extrais la date de la facture au format AAAA-MM-JJ (année-mois-jour).
3. Extrais les montants financiers : montant HT, montant TVA, taux TVA (en %), montant TTC.
4. Attribue le code du compte PCGM feuille le plus approprié parmi la liste ci-dessous.
5. Fournis le libellé exact correspondant au code PCGM choisi.

RÈGLES IMPORTANTES :
- Les montants doivent être des nombres décimaux (pas de texte).
- Le taux TVA doit être un pourcentage (ex: 20.0 pour 20%).
- La date doit être au format AAAA-MM-JJ.
- Le code PCGM doit être choisi EXCLUSIVEMENT parmi la liste ci-dessous.
- Si une information n'est pas visible ou lisible sur la facture, retourne null.

LISTE DES COMPTES PCGM FEUILLES (code : libellé) :
{liste_pcgm}

Analyse maintenant la facture et retourne les données extraites en JSON."""

    return prompt


def extraire_facture_avec_gemini(image_pil: Image.Image) -> SchemaExtractionFacture:
    """
    Envoie une image de facture à Gemini 2.0 Flash et retourne l'extraction structurée.

    Args:
        image_pil: Image PIL de la facture (sera redimensionnée si nécessaire)

    Returns:
        SchemaExtractionFacture contenant les données extraites

    Raises:
        Exception: En cas d'erreur réseau, API, ou JSON invalide
    """
    client = obtenir_client_gemini()

    # Redimensionner l'image pour l'envoi
    image_optimisee = redimensionner_image(image_pil)

    # Construire le prompt
    prompt_systeme = construire_prompt_systeme()

    logger.info("Envoi de la facture à Gemini 2.0 Flash pour extraction...")

    # Appel à l'API Gemini avec le nouveau SDK google-genai
    reponse = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[image_optimisee, prompt_systeme],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SchemaExtractionFacture,
            temperature=0.1,
        ),
    )

    # Parser la réponse JSON
    donnees_json = json.loads(reponse.text)
    resultat = SchemaExtractionFacture(**donnees_json)

    logger.info(
        f"Extraction réussie — Fournisseur : {resultat.nom_fournisseur}, "
        f"TTC : {resultat.montant_ttc}, PCGM : {resultat.code_compte_pcgm}"
    )

    return resultat
