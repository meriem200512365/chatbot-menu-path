"""
chatbot.py
----------
Orchestre la reponse finale : appelle la recherche semantique,
puis decide comment formuler la reponse selon le niveau de confiance
et l'ecart entre les resultats (gestion de l'ambiguite).

Les seuils sont centralises dans src/config.py (partages avec
src/generation/rag_chatbot.py, pour eviter toute incoherence entre
les deux modes de reponse).
"""

from src.config import SEUIL_DISTANCE_CONFIANT, SEUIL_DISTANCE_FIABLE, ECART_AMBIGUITE
from src.search.semantic_search import search



def repondre(question: str) -> dict:
    resultats = search(question)

    if not resultats:
        return {
            "type": "aucun_resultat",
            "message": "Je n'ai trouve aucun chemin correspondant a ta demande. "
                       "Peux-tu reformuler ?",
            "resultats": [],
        }

    meilleur = resultats[0]

    # Cas 1 : rien de fiable
    if meilleur["distance"] >= SEUIL_DISTANCE_FIABLE:
        return {
            "type": "aucun_resultat",
            "message": "Je ne suis pas sur de comprendre ta demande. "
                       "Peux-tu preciser ou utiliser d'autres mots ?",
            "resultats": resultats,
        }

    # Cas 2 : ambiguite -> plusieurs resultats tres proches
    if len(resultats) > 1:
        ecart = resultats[1]["distance"] - meilleur["distance"]
        if ecart < ECART_AMBIGUITE and meilleur["distance"] < SEUIL_DISTANCE_FIABLE:
            candidats = [r for r in resultats if r["distance"] - meilleur["distance"] < ECART_AMBIGUITE]
            return {
                "type": "ambigu",
                "message": "Plusieurs chemins possibles correspondent a ta demande, "
                           "peux-tu preciser lequel tu veux ?",
                "resultats": candidats,
            }

    # Cas 3 : reponse directe (confiante ou moyennement confiante)
    confiance = "haute" if meilleur["distance"] < SEUIL_DISTANCE_CONFIANT else "moyenne"
    return {
        "type": "reponse_directe",
        "message": f"Le chemin est : {meilleur['path_str']}",
        "confiance": confiance,
        "resultats": [meilleur],
    }


if __name__ == "__main__":
    for q in [
        "je veux gerer les actes RO",
        "comment voir le nombre total de produits dans un depot",
        "xyzabc totalement hors sujet",
    ]:
        rep = repondre(q)
        print(f"\nQ: {q}")
        print(f"R: {rep['message']}")
        for r in rep["resultats"]:
            print(f"   - {r['path_str']}  (distance={r['distance']})")