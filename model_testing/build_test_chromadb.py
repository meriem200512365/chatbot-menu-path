"""
build_test_chromadb.py
=============================================

Reproduit EXACTEMENT la logique de production
(src/embedding/embed_documents.py + src/search/semantic_search.py)
mais avec :
    - le modele fine-tune (models/cegedim-menu-embedding)
    - une collection ChromaDB SEPAREE, stockee dans
      day2_model_testing/chroma_db_test/ (jamais data/chroma_db/ de prod)

Objectif : verifier que le modele fine-tune se comporte de la meme
facon une fois branche sur le vrai moteur de recherche (ChromaDB +
HNSW cosine) que dans le test simplifie de test_api.py (cosinus
calcule directement en memoire). Si les deux concordent, on peut
integrer le modele dans src/ en confiance.

Usage :
    cd day2_model_testing
    python build_test_chromadb.py

Ne touche a AUCUN fichier de src/ ni de data/chroma_db/ (prod).
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT_DIR = Path(__file__).resolve().parent.parent
MENU_INDEX_JSON = ROOT_DIR / "data" / "chemins" / "menu_index.json"  # source reelle de prod (1383 entrees brutes)
FINE_TUNED_MODEL_PATH = ROOT_DIR / "models" / "cegedim-menu-embedding"

# Stockage ISOLE, a cote de ce script, jamais dans data/chroma_db/
TEST_CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db_test"
TEST_COLLECTION_NAME = "menu_premium_finetuned_test"

# Seuils repris tels quels de src/config.py pour rester coherent avec
# la logique metier de chatbot.py / rag_chatbot.py (NE PAS dupliquer
# des valeurs differentes ici).
SEUIL_DISTANCE_CONFIANT = 0.30
SEUIL_DISTANCE_FIABLE = 0.55

TOP_K = 5

QUESTIONS_TEST = [
    "je veux gérer les actes RO",
    "où puis-je voir constitution des groupes de traitements ?",
    "comment on fait pour paramétrer les couleurs de l'appli",
    "gestion des variables",
]


def load_menu_index():
    if not MENU_INDEX_JSON.exists():
        raise FileNotFoundError(
            f"Introuvable : {MENU_INDEX_JSON}\n"
            "Ce script attend le vrai menu_index.json de production "
            "(data/chemins/menu_index.json), pas la version dedupliquee "
            "du dataset d'entrainement — c'est volontaire, pour tester "
            "exactement les conditions reelles de l'app."
        )
    with open(MENU_INDEX_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_collection():
    """Reproduit embed_documents.py, avec le modele fine-tune et une
    collection de test isolee."""
    print(f"Chargement du modele fine-tune depuis {FINE_TUNED_MODEL_PATH} ...")
    model = SentenceTransformer(str(FINE_TUNED_MODEL_PATH))

    kb = load_menu_index()
    print(f"{len(kb)} entrees chargees depuis menu_index.json (source reelle de prod).")

    client = chromadb.PersistentClient(path=str(TEST_CHROMA_DIR))
    try:
        client.delete_collection(TEST_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=TEST_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # identique a la prod
    )

    ids = [entry["id"] for entry in kb]
    documents = [entry["search_text"] for entry in kb]
    metadatas = [
        {
            "label": entry["label"],
            "path_str": entry["path_str"],
            "path_ids": " > ".join(entry["path_ids"]),
        }
        for entry in kb
    ]

    print(f"Encodage de {len(documents)} chemins avec le modele fine-tune...")
    embeddings = model.encode(documents, batch_size=64, show_progress_bar=True).tolist()

    # Meme logique de deduplication des IDs que embed_documents.py
    seen = {}
    unique_ids = []
    for _id in ids:
        if _id not in seen:
            seen[_id] = 0
            unique_ids.append(_id)
        else:
            seen[_id] += 1
            unique_ids.append(f"{_id}__{seen[_id]}")

    collection.add(
        ids=unique_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"✅ {len(unique_ids)} chemins indexes dans la collection de test '{TEST_COLLECTION_NAME}'.")
    print(f"   Stockage : {TEST_CHROMA_DIR} (isole de data/chroma_db/ de production)")
    return model, collection


def search(model, collection, query: str, top_k: int = TOP_K):
    """Reproduit semantic_search.py."""
    query_embedding = model.encode(query).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    output = []
    for _id, meta, dist in zip(results["ids"][0], results["metadatas"][0], results["distances"][0]):
        output.append({"id": _id, "path_str": meta["path_str"], "distance": round(dist, 4)})
    return output


def classify_confidence(distance: float) -> str:
    if distance < SEUIL_DISTANCE_CONFIANT:
        return "CONFIANT"
    if distance < SEUIL_DISTANCE_FIABLE:
        return "FIABLE"
    return "PAS FIABLE / hors sujet"


def main():
    model, collection = build_collection()

    print("\n" + "=" * 80)
    print("TEST DE RECHERCHE VIA CHROMADB (moteur reel, modele fine-tune)")
    print("=" * 80)

    for question in QUESTIONS_TEST:
        print(f"\nQUESTION : {question}")
        results = search(model, collection, question)
        for rank, r in enumerate(results, 1):
            confiance = classify_confidence(r["distance"])
            print(f"  {rank}. {r['path_str']}  (distance={r['distance']}, {confiance})")

    print("\n" + "=" * 80)
    print("A VERIFIER : le resultat #1 de chaque question doit correspondre a ce")
    print("que vous obteniez deja via test_api.py (colonne verte, cosinus direct).")
    print("Les scores ne sont pas directement comparables (ChromaDB = distance,")
    print("test_api.py = similarite), mais le CLASSEMENT (quel chemin est #1, #2...)")
    print("doit etre identique -- c'est ca qui confirme que l'integration ChromaDB")
    print("ne degrade pas la qualite du modele.")


if __name__ == "__main__":
    main()