"""
test_api.py
=================================

API de TEST isolee, independante de l'application de production
(src/api/app.py, src/embedding/, ChromaDB de prod).

Objectif :
- recharger le modele fine-tune (models/cegedim-menu-embedding) exactement
  comme le fera l'application plus tard
- le comparer cote a cote avec le modele de base
  (paraphrase-multilingual-MiniLM-L12-v2) sur les 1382 chemins reels
- fournir une petite interface web (page unique, pas de dependance
  supplementaire type Streamlit) pour tester a l'oeil

Lancement :
    cd day2_model_testing
    pip install -r requirements_test.txt
    uvicorn test_api:app --reload --port 8010

Puis ouvrir : http://127.0.0.1:8010

NE TOUCHE A AUCUN FICHIER DE src/. Utilise uniquement :
    ../dataset/menu_paths_clean.json
    ../models/cegedim-menu-embedding/
"""

import json
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util

# --------------------------------------------------------------------------
# Chemins (relatifs a la racine du repo, day2_model_testing/ est un
# sous-dossier de chatbot-menu-path/)
# --------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT_DIR / "dataset" / "menu_paths_clean.json"
FINE_TUNED_MODEL_PATH = ROOT_DIR / "models" / "cegedim-menu-embedding"
BASE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

if not CORPUS_PATH.exists():
    raise FileNotFoundError(
        f"Corpus introuvable : {CORPUS_PATH}\n"
        "Verifiez que dataset/menu_paths_clean.json a bien ete copie a la "
        "racine du repo (a cote de day2_model_testing/)."
    )
if not FINE_TUNED_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Modele fine-tune introuvable : {FINE_TUNED_MODEL_PATH}\n"
        "Verifiez que models/cegedim-menu-embedding a bien ete copie a la "
        "racine du repo."
    )

# --------------------------------------------------------------------------
# Chargement au demarrage (une seule fois, pas a chaque requete)
# --------------------------------------------------------------------------
app = FastAPI(title="Cegedim Menu Embedding - Test A/B (Jour 2)")

print("Chargement du corpus...")
with open(CORPUS_PATH, encoding="utf-8") as f:
    corpus_data = json.load(f)
corpus_paths = [d["path_str"] for d in corpus_data]
print(f"  -> {len(corpus_paths)} chemins charges.")

print("Chargement du modele de base (avant fine-tuning)...")
model_base = SentenceTransformer(BASE_MODEL_NAME)
corpus_emb_base = model_base.encode(
    corpus_paths, convert_to_tensor=True, show_progress_bar=True
)

print("Chargement du modele fine-tune (cegedim-menu-embedding)...")
model_finetuned = SentenceTransformer(str(FINE_TUNED_MODEL_PATH))
corpus_emb_finetuned = model_finetuned.encode(
    corpus_paths, convert_to_tensor=True, show_progress_bar=True
)

print("Pret. Les deux modeles et le corpus (1382 chemins) sont en memoire.")


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class SearchRequest(BaseModel):
    question: str
    top_k: int = 5


class SearchResult(BaseModel):
    path: str
    score: float


class SearchResponse(BaseModel):
    question: str
    base_model_results: List[SearchResult]
    finetuned_model_results: List[SearchResult]
    base_model_latency_ms: float
    finetuned_model_latency_ms: float


# --------------------------------------------------------------------------
# Logique de recherche
# --------------------------------------------------------------------------
def search(model: SentenceTransformer, corpus_emb, question: str, top_k: int):
    t0 = time.perf_counter()
    q_emb = model.encode(question, convert_to_tensor=True)
    sims = util.cos_sim(q_emb, corpus_emb)[0]
    top_idx = sims.argsort(descending=True)[:top_k]
    latency_ms = (time.perf_counter() - t0) * 1000
    results = [
        {"path": corpus_paths[i.item()], "score": round(sims[i].item(), 4)}
        for i in top_idx
    ]
    return results, latency_ms


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "corpus_size": len(corpus_paths),
        "base_model": BASE_MODEL_NAME,
        "finetuned_model": FINE_TUNED_MODEL_PATH.name,
    }


@app.post("/api/search", response_model=SearchResponse)
def api_search(req: SearchRequest):
    base_results, base_latency = search(model_base, corpus_emb_base, req.question, req.top_k)
    ft_results, ft_latency = search(model_finetuned, corpus_emb_finetuned, req.question, req.top_k)
    return {
        "question": req.question,
        "base_model_results": base_results,
        "finetuned_model_results": ft_results,
        "base_model_latency_ms": round(base_latency, 1),
        "finetuned_model_latency_ms": round(ft_latency, 1),
    }


# --------------------------------------------------------------------------
# Interface web minimale (une seule page HTML, aucune dependance externe)
# --------------------------------------------------------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Test A/B - Cegedim Menu Embedding</title>
<style>
  body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 1100px; margin: 40px auto; background:#0f1115; color:#e6e6e6; }
  h1 { font-size: 20px; }
  .sub { color: #9aa0a6; margin-bottom: 24px; }
  input[type=text] { width: 70%; padding: 10px; font-size: 15px; border-radius: 6px; border: 1px solid #333; background:#1a1d23; color:#eee; }
  button { padding: 10px 18px; font-size: 15px; border-radius: 6px; border: none; background: #4f7cff; color: white; cursor: pointer; }
  button:hover { background: #3a63e0; }
  .columns { display: flex; gap: 24px; margin-top: 28px; }
  .col { flex: 1; background: #171a21; border-radius: 8px; padding: 16px; }
  .col h2 { font-size: 15px; margin-top: 0; }
  .col.old h2 { color: #ff9d5c; }
  .col.new h2 { color: #6fd68a; }
  .result { padding: 8px 0; border-bottom: 1px solid #262a33; }
  .result .rank { color: #777; font-size: 12px; }
  .result .score { float: right; color: #9aa0a6; font-size: 13px; }
  .latency { color: #777; font-size: 12px; margin-top: 8px; }
  .examples { margin-top: 10px; font-size: 13px; color: #9aa0a6; }
  .examples span { cursor: pointer; text-decoration: underline; margin-right: 12px; }
</style>
</head>
<body>
  <h1>Test A/B - modele de base vs cegedim-menu-embedding</h1>
  <div class="sub">
    Interface de test isolee (Jour 2) - n'affecte pas l'application de production.
  </div>

  <input type="text" id="question" placeholder="Ex: comment gerer les actes RO ?" />
  <button onclick="runSearch()">Rechercher</button>

  <div class="examples">
    Exemples :
    <span onclick="fill('je n\\'arrive pas a retrouver l\\'ecran des actes de remboursement obligatoire')">actes RO (formulation eloignee)</span>
    <span onclick="fill('comment on fait pour parametrer les couleurs de l\\'appli')">couleurs</span>
    <span onclick="fill('y a un endroit pour gerer les cheques ?')">cheques</span>
  </div>

  <div class="columns">
    <div class="col old">
      <h2>Modele de base (avant fine-tuning)</h2>
      <div id="base-results"></div>
      <div class="latency" id="base-latency"></div>
    </div>
    <div class="col new">
      <h2>Modele fine-tune (cegedim-menu-embedding)</h2>
      <div id="ft-results"></div>
      <div class="latency" id="ft-latency"></div>
    </div>
  </div>

<script>
function fill(text) {
  document.getElementById('question').value = text;
  runSearch();
}

async function runSearch() {
  const question = document.getElementById('question').value.trim();
  if (!question) return;

  document.getElementById('base-results').innerHTML = 'Recherche...';
  document.getElementById('ft-results').innerHTML = 'Recherche...';

  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: question, top_k: 5})
  });
  const data = await resp.json();

  const render = (results) => results.map((r, i) =>
    `<div class="result"><span class="rank">#${i+1}</span> ${r.path} <span class="score">${r.score}</span></div>`
  ).join('');

  document.getElementById('base-results').innerHTML = render(data.base_model_results);
  document.getElementById('ft-results').innerHTML = render(data.finetuned_model_results);
  document.getElementById('base-latency').innerText = `Latence: ${data.base_model_latency_ms} ms`;
  document.getElementById('ft-latency').innerText = `Latence: ${data.finetuned_model_latency_ms} ms`;
}

document.getElementById('question').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') runSearch();
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE