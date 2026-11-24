import os
from google import genai
from app.config import parametres

try:
    client = genai.Client(api_key=parametres.GEMINI_API_KEY)
    print("Modèles disponibles :")
    for m in client.models.list():
        if "generateContent" in m.supported_actions or True:
            print(m.name)
except Exception as e:
    print(f"Erreur : {e}")
