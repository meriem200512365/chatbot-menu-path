"""
vision_client.py
-----------------
Envoie une image (capture d'ecran, schema, diagramme...) + une question
a un modele Groq capable de comprendre les images (vision).

IMPORTANT : le nom exact du modele vision disponible sur Groq peut changer
au fil du temps (nouveaux modeles ajoutes/retires). Verifie le nom actuel
sur https://console.groq.com/docs/models (section "vision") et mets a jour
GROQ_VISION_MODEL dans src/config.py si l'appel echoue avec une erreur du
type "model not found".
"""

import base64

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_VISION_MODEL


def _encode_image(image_bytes: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def analyser_image(image_bytes: bytes, mime_type: str, question: str) -> str:
    """
    Envoie l'image + la question au modele vision, retourne la reponse texte.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY n'est pas definie (voir src/config.py).")

    client = Groq(api_key=GROQ_API_KEY)
    image_data_url = _encode_image(image_bytes, mime_type)

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question or "Decris cette image en detail."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    with open("exemple.png", "rb") as f:
        img_bytes = f.read()
    print(analyser_image(img_bytes, "image/png", "Que montre cette image ?"))