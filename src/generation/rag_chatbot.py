"""
rag_chatbot.py
---------------
Implemente le schema demande :

    Question -> Retrieval (ChromaDB) -> contexte trouve + question
             -> LLM -> reponse redigee

A la difference de src/chatbot/chatbot.py (qui renvoie juste LE chemin
via un template fixe), ce module laisse le LLM REDIGER une reponse en
langage naturel, en s'appuyant STRICTEMENT sur les chemins recuperes
par ChromaDB (pour eviter les hallucinations de chemins qui n'existent
pas dans le menu).

Usage :
    from src.generation.rag_chatbot import repondre_rag
    resultat = repondre_rag("comment gerer les actes RO ?")
"""
import os
from src.config import RAG_TOP_K
from src.search.semantic_search import search
from src.generation.llm_client import generate


SEUIL_CONTEXTE_PERTINENT = 0.60  # au-dela, on considere le contexte trop eloigne


SYSTEM_PROMPT = """Tu es l'assistant de navigation de l'application "Active Premium".

Ton role : aider les employes a comprendre OU se trouve une fonctionnalite dans le
menu de l'application, et a comprendre A QUOI SERT cette fonctionnalite, en te basant
UNIQUEMENT sur les chemins de menu fournis en contexte ci-dessous.

Regles strictes :
- N'invente JAMAIS un chemin de menu qui n'est pas dans le contexte fourni.
- Si le contexte ne permet pas de repondre avec certitude, dis-le clairement
  et propose a l'utilisateur de reformuler sa question.
- Reponds en francais, de maniere concise et professionnelle.
- Quand tu cites un chemin, ecris-le exactement comme fourni dans le contexte
  (avec les ">" separant chaque niveau), par exemple : Prestations > Referentiel > Actes.
- Tu peux legerement reformuler ou expliquer, mais le CHEMIN lui-meme doit rester
  identique a celui fourni (ne le traduis pas, ne le raccourcis pas).
"""


def build_context(resultats: list) -> str:
    """Formate les resultats de la recherche vectorielle en texte pour le prompt."""
    lignes = []
    for i, r in enumerate(resultats, start=1):
        lignes.append(f"{i}. Chemin : {r['path_str']}  (pertinence: {1 - r['distance']:.2f})")
    return "\n".join(lignes)


def repondre_rag(question: str, top_k: int = RAG_TOP_K) -> dict:
    """
    Retourne :
    {
        "reponse": "texte redige par le LLM",
        "chemins_sources": [...],   # les chemins utilises comme contexte
        "type": "rag_reponse" | "rag_hors_contexte"
    }
    """
    # --- Etape 1 : Retrieval ---
    resultats = search(question, top_k=top_k)

    if not resultats or resultats[0]["distance"] >= SEUIL_CONTEXTE_PERTINENT:
        return {
            "reponse": "Je n'ai trouve aucune fonctionnalite du menu correspondant "
                       "a ta question. Peux-tu reformuler avec d'autres mots ?",
            "chemins_sources": [],
            "type": "rag_hors_contexte",
        }

    # --- Etape 2 : construction du contexte ---
    contexte = build_context(resultats)

    user_prompt = f"""Contexte (chemins du menu trouves comme pertinents) :
{contexte}

Question de l'utilisateur : {question}

Reponds a la question en t'appuyant sur le contexte ci-dessus."""

    # --- Etape 3 : Generation ---
    reponse_llm = generate(SYSTEM_PROMPT, user_prompt)

    return {
        "reponse": reponse_llm,
        "chemins_sources": resultats,
        "type": "rag_reponse",
    }


if __name__ == "__main__":
    for q in [
        "comment gerer les actes RO ?",
        "je cherche a annuler un cheque, comment faire ?",
    ]:
        print(f"\nQ: {q}")
        res = repondre_rag(q)
        print(f"R: {res['reponse']}")
        print("Sources :")
        for s in res["chemins_sources"]:
            print(f"   - {s['path_str']}")
