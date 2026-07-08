"""
semantic_search.py
--------------------
Prend une question utilisateur en langage naturel, l'encode avec le
meme modele que celui utilise a l'indexation, et interroge ChromaDB
pour recuperer les Top-K chemins de menu les plus proches.
"""

from src.config import TOP_K
from src.embedding.model import get_model
from src.database.chroma_manager import get_collection


def search(query: str, top_k: int = TOP_K):
    """
    Retourne une liste de resultats tries par pertinence :
    [
        {"id": ..., "label": ..., "path_str": ..., "distance": 0.12},
        ...
    ]
    Plus la distance est faible, plus le resultat est pertinent
    (distance cosinus : 0 = identique).
    """
    model = get_model()
    collection = get_collection()

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    output = []
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for _id, meta, dist in zip(ids, metadatas, distances):
        output.append({
            "id": _id,
            "label": meta["label"],
            "path_str": meta["path_str"],
            "path_ids": meta["path_ids"],
            "distance": round(dist, 4),
        })

    return output


if __name__ == "__main__":
    query = "je veux gerer les actes RO"
    results = search(query)
    print(f"Requete : {query}\n")
    for r in results:
        print(f"  [{r['distance']}] {r['path_str']}  (id: {r['id']})")
