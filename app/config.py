"""
Configuration de l'application FiduIA.

Charge les variables d'environnement depuis le fichier .env
via pydantic-settings pour une validation robuste au démarrage.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Parametres(BaseSettings):
    """Paramètres globaux de l'application FiduIA."""

    # --- Base de données ---
    DATABASE_URL: str

    # --- Clé API Google Gemini ---
    GEMINI_API_KEY: str

    # --- Stockage des fichiers uploadés ---
    DOSSIER_STOCKAGE_UPLOADS: str = "/app/stockage_fichiers"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instance unique des paramètres, importable depuis tout le projet
parametres = Parametres()
