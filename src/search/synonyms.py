"""
synonyms.py
------------
Dictionnaire de synonymes / alias metier (ex. "RO" -> "Regime Obligatoire").

Remplace l'edition directe de menu.xml pour resoudre le probleme du
jargon Cegedim que le modele d'embeddings/LLM ne connait pas nativement :
sans risque pour la source de verite du menu, stocke a part dans
data/synonymes.json.

Utilise a la fois :
    - par le pipeline de recherche (src/chatbot/chatbot.py et
      src/generation/rag_chatbot.py), via etendre_question(), pour enrichir
      la question avant la recherche semantique et avant le prompt LLM.
    - par la page admin (src/ui/pages/4_Gestion_Menu.py) pour le CRUD.
"""

import json
import os
import re

from src.config import SYNONYMES_JSON


def lire_synonymes() -> dict:
    """Retourne le dictionnaire {terme: expansion}. Dict vide si le fichier n'existe pas encore."""
    if not os.path.exists(SYNONYMES_JSON):
        return {}
    with open(SYNONYMES_JSON, encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder_synonymes(synonymes: dict):
    os.makedirs(os.path.dirname(SYNONYMES_JSON), exist_ok=True)
    with open(SYNONYMES_JSON, "w", encoding="utf-8") as f:
        json.dump(synonymes, f, ensure_ascii=False, indent=2, sort_keys=True)


def ajouter_synonyme(terme: str, expansion: str):
    if not terme or not expansion:
        raise ValueError("Le terme et l'expansion sont obligatoires.")
    synonymes = lire_synonymes()
    synonymes[terme.strip()] = expansion.strip()
    _sauvegarder_synonymes(synonymes)


def supprimer_synonyme(terme: str):
    synonymes = lire_synonymes()
    if terme in synonymes:
        del synonymes[terme]
        _sauvegarder_synonymes(synonymes)


def etendre_question(question: str) -> str:
    """
    Ajoute entre parentheses l'expansion des termes/acronymes metier
    reconnus dans la question, sur une correspondance de mot entier
    (insensible a la casse), pour aider a la fois la recherche semantique
    et le LLM a comprendre le jargon.

    Exemple : "je veux gerer les actes RO"
           -> "je veux gerer les actes RO (Regime Obligatoire)"

    N'ajoute rien si le terme n'est pas trouve, et n'ajoute jamais deux
    fois la meme expansion.
    """
    synonymes = lire_synonymes()
    if not synonymes:
        return question

    ajouts = []
    for terme, expansion in synonymes.items():
        motif = r"\b" + re.escape(terme) + r"\b"
        if re.search(motif, question, flags=re.IGNORECASE) and expansion not in question:
            ajouts.append(expansion)

    if not ajouts:
        return question

    return f"{question} ({', '.join(ajouts)})"