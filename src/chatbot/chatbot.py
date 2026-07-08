"""
chatbot.py
----------
Orchestre la reponse finale : appelle la recherche semantique,
puis decide comment formuler la reponse selon le niveau de confiance
et l'ecart entre les resultats (gestion de l'ambiguite).

Seuils de distance cosinus (a ajuster empiriquement selon tes tests) :
    - distance < 0.30           -> reponse directe, tres confiante
    - 0.30 <= distance < 0.55   -> reponse avec confirmation
    - distance >= 0.55          -> aucun resultat fiable trouve
"""

from src.search.semantic_search import search

SEUIL_CONFIANT = 0.30
SEUIL_INCERTAIN = 0.55
ECART_AMBIGUITE = 0.05  # si le 2e resultat est tres proche du 1er -> ambigu


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
    if meilleur["distance"] >= SEUIL_INCERTAIN:
        return {
            "type": "aucun_resultat",
            "message": "Je ne suis pas sur de comprendre ta demande. "
                       "Peux-tu preciser ou utiliser d'autres mots ?",
            "resultats": resultats,
        }

    # Cas 2 : ambiguite -> plusieurs resultats tres proches
    if len(resultats) > 1:
        ecart = resultats[1]["distance"] - meilleur["distance"]
        if ecart < ECART_AMBIGUITE and meilleur["distance"] < SEUIL_INCERTAIN:
            candidats = [r for r in resultats if r["distance"] - meilleur["distance"] < ECART_AMBIGUITE]
            return {
                "type": "ambigu",
                "message": "Plusieurs chemins possibles correspondent a ta demande, "
                           "peux-tu preciser lequel tu veux ?",
                "resultats": candidats,
            }

    # Cas 3 : reponse directe (confiante ou moyennement confiante)
    confiance = "haute" if meilleur["distance"] < SEUIL_CONFIANT else "moyenne"
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
