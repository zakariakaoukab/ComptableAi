import os
from google import genai
from app.config import parametres

client = genai.Client(api_key=parametres.GEMINI_API_KEY)

modeles_a_tester = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite"
]

modele_fonctionnel = None

print("=== Début du test des modèles Flash ===")
for modele in modeles_a_tester:
    print(f"Test de {modele}...")
    try:
        reponse = client.models.generate_content(
            model=modele,
            contents="Say simply 'hello' and nothing else."
        )
        if reponse.text:
            print(f"[SUCCÈS] {modele} a répondu : {reponse.text.strip()}")
            modele_fonctionnel = modele
            break
    except Exception as e:
        print(f"[ÉCHEC] {modele} - Erreur : {e}")

if modele_fonctionnel:
    print(f"\n=> LE MODÈLE À UTILISER EST : {modele_fonctionnel}")
else:
    print("\n=> AUCUN MODÈLE N'A FONCTIONNÉ.")
