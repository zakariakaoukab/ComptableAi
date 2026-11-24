"""
Module de connexion à la base de données PostgreSQL.

Fournit le moteur SQLAlchemy, la création des tables SQLModel,
et le générateur de sessions pour l'injection de dépendances FastAPI.
"""

from sqlmodel import SQLModel, Session, create_engine

from app.config import parametres

# Moteur SQLAlchemy connecté à PostgreSQL
moteur = create_engine(
    parametres.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


def creer_tables() -> None:
    """Crée toutes les tables définies dans les modèles SQLModel."""
    SQLModel.metadata.create_all(moteur)


def obtenir_session():
    """
    Générateur de sessions pour l'injection de dépendances FastAPI.

    Utilisation dans les routes :
        session: Session = Depends(obtenir_session)
    """
    with Session(moteur) as session:
        yield session
