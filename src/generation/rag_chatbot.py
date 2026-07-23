"""
rag_chatbot.py
---------------
Pipeline RAG :

    Question -> Retrieval (ChromaDB) -> contexte trouve + question
             -> LLM -> reponse redigee

Le LLM est un assistant GENERALISTE pour l'entreprise (repond a toute
question, y compris technique/generale, avec ses propres connaissances).
La resolution de chemin de menu Active Premium est une FONCTIONNALITE EN
PLUS qu'il utilise quand c'est pertinent, pas une restriction.

Support egalement un contexte de document uploade (voir document_context
dans repondre_rag) : le texte extrait d'un PDF/Excel/CSV/fichier texte est
alors injecte dans le prompt, en plus (ou a la place) du contexte de menu.
"""

from src.config import RAG_TOP_K
from src.search.semantic_search import search
from src.generation.llm_client import generate


SEUIL_PERTINENCE_FIABLE = 0.40


SYSTEM_PROMPT = """Tu es l'assistant IA interne de l'entreprise, utilise par les employes
au quotidien (utilisateurs metier, developpeurs, etc.).

Ton fonctionnement :

1. QUESTION GENERALE (technique, metier, quotidienne, salutation...) :
   Reponds normalement en utilisant tes propres connaissances, comme le
   ferait un assistant IA generaliste. Tu n'es PAS limite a l'application
   Active Premium : code, bases de donnees, outils, methodologie, questions
   diverses des developpeurs ou de n'importe quel employe -> tu reponds
   normalement, sans jamais refuser sous pretexte que ca ne concerne pas
   le menu.

2. QUESTION DE NAVIGATION dans l'application "Active Premium" :
   Si un contexte de chemins de menu t'est fourni ET qu'il est pertinent,
   utilise-le pour indiquer le chemin exact. N'invente JAMAIS un chemin qui
   n'est pas dans le contexte fourni. Ecris-le exactement comme fourni
   (avec les ">" separant chaque niveau), par exemple :
   Prestations > Referentiel > Actes.

3. DOCUMENT JOINT (si un contenu de fichier est fourni ci-dessous) :
   Utilise ce contenu en priorite pour repondre si la question porte dessus
   (resumer, expliquer, extraire une info precise, etc.).

Dans tous les cas : reponds en francais, de maniere naturelle, concise et
professionnelle -- comme un collegue competent, pas comme un moteur de
recherche restreint.
"""


def build_menu_context(resultats: list) -> str:
    if not resultats:
        return ""
    lignes = []
    for i, r in enumerate(resultats, start=1):
        pertinence = 1 - r["distance"]
        lignes.append(f"{i}. Chemin : {r['path_str']}  (pertinence: {pertinence:.2f})")
    return "\n".join(lignes)


def repondre_rag(question: str, top_k: int = RAG_TOP_K, document_context: str = None) -> dict:
    """
    document_context : texte deja extrait d'un fichier uploade (voir
    src/files/document_reader.py), ou None s'il n'y a pas de fichier joint.

    Retourne :
    {
        "reponse": "...",
        "chemins_sources": [...],   # vide si la question n'etait pas liee au menu
        "type": "rag_reponse",
    }
    """
    # --- Etape 1 : Retrieval sur le menu ---
    resultats = search(question, top_k=top_k)
    pertinent = bool(resultats) and (1 - resultats[0]["distance"]) >= SEUIL_PERTINENCE_FIABLE
    chemins_sources = resultats if pertinent else []

    # --- Etape 2 : construction du prompt ---
    blocs = []
    if pertinent:
        blocs.append(
            "Contexte (chemins du menu Active Premium recuperes automatiquement, "
            f"a utiliser SEULEMENT si pertinent) :\n{build_menu_context(resultats)}"
        )
    if document_context:
        blocs.append(f"Contenu du document joint par l'utilisateur :\n{document_context}")

    blocs.append(f"Question de l'utilisateur : {question}")
    blocs.append("Reponds a la question.")
    user_prompt = "\n\n".join(blocs)

    # --- Etape 3 : Generation ---
    reponse_llm = generate(SYSTEM_PROMPT, user_prompt)

    return {
        "reponse": reponse_llm,
        "chemins_sources": chemins_sources,
        "type": "rag_reponse",
    }


if __name__ == "__main__":
    for q in [
        "bonjour",
        "peux tu me dire comment creer une base de donnees dans mongodb ?",
        "comment gerer les actes RO ?",
    ]:
        print(f"\nQ: {q}")
        res = repondre_rag(q)
        print(f"R: {res['reponse']}")
        if res["chemins_sources"]:
            print("Sources :")
            for s in res["chemins_sources"]:
                print(f"   - {s['path_str']}")