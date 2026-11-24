# ---- Étape 1 : Image de base Python ----
FROM python:3.11-slim

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Répertoire de travail dans le conteneur
WORKDIR /app

# ---- Étape 2 : Installation des dépendances ----
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Étape 3 : Copie du code source et des données PCGM ----
COPY ./app ./app
COPY pcgm_invoice_mapping_leaf.toon .

# ---- Étape 4 : Exposition du port et lancement ----
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
