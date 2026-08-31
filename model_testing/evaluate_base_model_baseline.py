"""
evaluate_base_model_baseline.py
=======================================================

Calcule EXACTEMENT les memes metriques (Top-1, Top-3, MRR, par
profondeur) que celles deja obtenues pour le modele fine-tune en
Etape 7 (notebook Colab), mais pour le modele de base
(paraphrase-multilingual-MiniLM-L12-v2), sur le MEME test set
(test.csv, 1382 questions jamais vues).

Objectif : obtenir une comparaison avant/apres rigoureusement
appariee (memes questions, meme corpus, memes seuils) pour le
tableau de soutenance -- pas une comparaison approximative entre
deux mesures faites differemment.

Usage :
    cd day2_model_testing (ou model_testing selon votre nommage)
    python evaluate_base_model_baseline.py

Ne modifie rien dans src/ ni data/chroma_db/.
"""

import json
from pathlib import Path

import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

ROOT_DIR = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT_DIR / "dataset" / "menu_paths_clean.json"
TEST_PATH = ROOT_DIR / "dataset" / "test.csv"
FINE_TUNED_MODEL_PATH = ROOT_DIR / "models" / "cegedim-menu-embedding"
BASE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

OUTPUT_JSON = Path(__file__).resolve().parent / "comparison_report.json"


def evaluate(model: SentenceTransformer, model_label: str, corpus_df, test_df):
    corpus_paths = corpus_df["path_str"].tolist()
    corpus_ids = corpus_df["path_id"].tolist()

    print(f"  Encodage du corpus ({len(corpus_paths)} chemins)...")
    corpus_emb = model.encode(corpus_paths, convert_to_tensor=True, show_progress_bar=False)

    print(f"  Encodage des questions de test ({len(test_df)} questions)...")
    query_emb = model.encode(test_df["query"].tolist(), convert_to_tensor=True, show_progress_bar=False)

    sims = cos_sim(query_emb, corpus_emb)
    ranked = torch.argsort(sims, dim=1, descending=True).cpu()
    corpus_ids_t = torch.tensor(corpus_ids)

    rows = []
    for i, row in test_df.reset_index(drop=True).iterrows():
        true_pid = row["path_id"]
        rank_pos = (corpus_ids_t[ranked[i]] == true_pid).nonzero()[0].item()
        top1_pid = corpus_ids[ranked[i][0].item()]
        top3_pids = [corpus_ids[j.item()] for j in ranked[i][:3]]
        rows.append({
            "path_id": true_pid,
            "correct_top1": top1_pid == true_pid,
            "correct_top3": true_pid in top3_pids,
            "reciprocal_rank": 1 / (rank_pos + 1),
        })

    eval_df = pd.DataFrame(rows).merge(corpus_df[["path_id", "depth"]], on="path_id")

    depth_report = eval_df.groupby("depth").agg(
        n=("path_id", "count"),
        top1_acc=("correct_top1", "mean"),
        top3_acc=("correct_top3", "mean"),
        mrr=("reciprocal_rank", "mean"),
    ).round(4)

    summary = {
        "model": model_label,
        "top1_accuracy": round(float(eval_df["correct_top1"].mean()), 4),
        "top3_accuracy": round(float(eval_df["correct_top3"].mean()), 4),
        "mrr": round(float(eval_df["reciprocal_rank"].mean()), 4),
        "never_found_top3": int((~eval_df["correct_top3"]).sum()),
        "n_test_questions": len(eval_df),
        "n_paths_covered": int(eval_df["path_id"].nunique()),
        "depth_report": depth_report.reset_index().to_dict(orient="records"),
    }
    return summary


def main():
    print("Chargement du corpus et du test set (les memes que l'Etape 7)...")
    corpus_df = pd.read_json(CORPUS_PATH)
    test_df = pd.read_csv(TEST_PATH)
    assert test_df["path_id"].nunique() == 1382, "Le test set doit couvrir les 1382 chemins"

    print("\n=== MODELE DE BASE (avant fine-tuning) ===")
    model_base = SentenceTransformer(BASE_MODEL_NAME)
    summary_base = evaluate(model_base, "base (paraphrase-multilingual-MiniLM-L12-v2)", corpus_df, test_df)

    print("\n=== MODELE FINE-TUNE (cegedim-menu-embedding) ===")
    model_ft = SentenceTransformer(str(FINE_TUNED_MODEL_PATH))
    summary_ft = evaluate(model_ft, "fine-tune (cegedim-menu-embedding)", corpus_df, test_df)

    report = {"base_model": summary_base, "finetuned_model": summary_ft}
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("COMPARAISON AVANT / APRES (meme test set, 1382 questions)")
    print("=" * 70)
    print(f"{'Metrique':<20}{'Base':>15}{'Fine-tune':>15}{'Gain':>15}")
    for key, fmt_pct in [("top1_accuracy", True), ("top3_accuracy", True), ("mrr", False)]:
        b, ft = summary_base[key], summary_ft[key]
        gain = ft - b
        if fmt_pct:
            print(f"{key:<20}{b*100:>14.2f}%{ft*100:>14.2f}%{gain*100:>+14.2f}pt")
        else:
            print(f"{key:<20}{b:>15.4f}{ft:>15.4f}{gain:>+15.4f}")
    print(f"{'never_found_top3':<20}{summary_base['never_found_top3']:>15}{summary_ft['never_found_top3']:>15}")
    print("=" * 70)
    print(f"\nRapport complet sauvegarde : {OUTPUT_JSON}")


if __name__ == "__main__":
    main()