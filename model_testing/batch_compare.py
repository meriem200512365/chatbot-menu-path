"""
batch_compare.py
======================================

Script autonome (pas besoin de lancer l'API) pour comparer rapidement
le modele de base et le modele fine-tune sur une liste de questions
de test, avec les 1382 chemins reels comme corpus.

Usage :
    cd day2_model_testing
    python batch_compare.py

Ajoutez vos propres questions dans QUESTIONS_TEST ci-dessous.
"""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer, util

ROOT_DIR = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT_DIR / "dataset" / "menu_paths_clean.json"
FINE_TUNED_MODEL_PATH = ROOT_DIR / "models" / "cegedim-menu-embedding"
BASE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Questions manuelles a adapter / completer selon vos besoins de demo.
# Format : (question, mot-cle attendu dans le chemin correct, pour verif visuelle rapide)
QUESTIONS_TEST = [
    ("je n'arrive pas a retrouver l'ecran des actes de remboursement obligatoire", "Actes RO"),
    ("comment on fait pour parametrer les couleurs de l'appli", "Couleurs"),
    ("y a un endroit pour gerer les cheques ?", "Cheques"),
    ("je veux voir les infos de sortie des batchs", "Sortie"),
    ("ou puis-je consulter les regles de gestion ?", "Regles de gestion"),
]


def main():
    print("Chargement du corpus...")
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus_data = json.load(f)
    corpus_paths = [d["path_str"] for d in corpus_data]
    print(f"  -> {len(corpus_paths)} chemins.\n")

    print("Chargement des deux modeles (peut prendre 1-2 min)...")
    model_base = SentenceTransformer(BASE_MODEL_NAME)
    model_ft = SentenceTransformer(str(FINE_TUNED_MODEL_PATH))

    emb_base = model_base.encode(corpus_paths, convert_to_tensor=True, show_progress_bar=True)
    emb_ft = model_ft.encode(corpus_paths, convert_to_tensor=True, show_progress_bar=True)
    print()

    for question, expected_keyword in QUESTIONS_TEST:
        print("=" * 80)
        print(f"QUESTION : {question}")
        print(f"(mot-cle attendu dans la bonne reponse : « {expected_keyword} »)")
        print("-" * 80)

        for label, model, emb in [("MODELE DE BASE", model_base, emb_base),
                                   ("MODELE FINE-TUNE", model_ft, emb_ft)]:
            q_emb = model.encode(question, convert_to_tensor=True)
            sims = util.cos_sim(q_emb, emb)[0]
            top3 = sims.argsort(descending=True)[:3]
            print(f"\n  {label} :")
            for rank, idx in enumerate(top3, 1):
                marker = " <-- contient le mot-cle" if expected_keyword.lower() in corpus_paths[idx.item()].lower() else ""
                print(f"    {rank}. {corpus_paths[idx.item()]}  (score={sims[idx].item():.3f}){marker}")
        print()

    print("=" * 80)
    print("Fin de la comparaison. Verifiez a l'oeil que le modele fine-tune")
    print("retrouve le bon chemin en position 1 (ou au moins dans le top-3)")
    print("plus souvent / avec un score plus net que le modele de base.")


if __name__ == "__main__":
    main()