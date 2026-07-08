"""
llm_client.py
-------------
Wrapper minimal autour de l'API Groq (llama-3.3-70b-versatile).
Isole l'appel au LLM du reste du code : si demain tu changes de
fournisseur (Claude, OpenAI, Ollama...), tu ne modifies QUE ce fichier.
"""

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL


def get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY n'est pas definie. "
            "Definis-la comme variable d'environnement avant de lancer l'appli "
            "(voir commentaire dans src/config.py)."
        )
    return Groq(api_key=GROQ_API_KEY)


def generate(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Appelle le LLM avec un prompt systeme (instructions) + un prompt
    utilisateur (question + contexte), et retourne le texte genere.

    temperature basse (0.2) par defaut : on veut des reponses factuelles
    et stables, pas creatives (evite les hallucinations sur les chemins).
    """
    client = get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    reponse = generate(
        system_prompt="Tu es un assistant concis.",
        user_prompt="Dis bonjour en une phrase.",
    )
    print(reponse)
