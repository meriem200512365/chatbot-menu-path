# Notebooks d'exploration et d'évaluation

Ces 5 notebooks documentent la démarche expérimentale derrière le projet :
exploration des données, justification des choix techniques, et mesure
chiffrée de la qualité du chatbot. Ils complètent le code de production
(`src/`) — ils ne sont pas nécessaires pour faire tourner l'application,
mais expliquent **pourquoi** elle est construite ainsi.

## Où les exécuter

**Google Colab**, runtime **CPU standard** (pas de GPU nécessaire — voir
le detail dans chaque notebook). Aucune installation locale requise :
chaque notebook clone le dépôt et installe ses propres dépendances dans sa
première cellule.

**Ouvrir dans Colab :**
- Directement depuis GitHub une fois ce dossier poussé :
  ```
  https://colab.research.google.com/github/meriem200512365/Chat-boot-cegedim/blob/main/notebooks/<nom_du_notebook>.ipynb
  ```
- Ou manuellement : https://colab.research.google.com → `Fichier > Importer un notebook` → uploader le `.ipynb`.

## Les 5 notebooks

| # | Notebook | Contenu | Dépendances installées | Nécessite |
|---|---|---|---|---|
| 1 | `01_exploration_menu_xml.ipynb` | Parcours du `menu.xml` brut : nombre de menus/items, distinction noeud/feuille, profondeur du graphe, items sans label, menus orphelins | `pandas`, `matplotlib` | — |
| 2 | `02_choix_calibrage_embeddings.ipynb` | Comparaison de 3 modèles d'embeddings multilingues sur un jeu de questions test ; distribution des distances pour justifier les seuils de `chatbot.py` | `sentence-transformers` | Compléter `QUESTIONS_TEST` (voir ci-dessous) |
| 3 | `03_evaluation_recherche_semantique.ipynb` | Fait tourner le vrai `semantic_search.py` (réindexation ChromaDB) ; calcule precision@1, precision@3, MRR | `requirements.txt` complet | Compléter `QUESTIONS_TEST` |
| 4 | `04_analyse_liens_casses.ipynb` | Analyse du rapport `liens_casses.json` (liens cassés, menus orphelins) + cellule de détection de régression réutilisable | `pandas`, `matplotlib` | — |
| 5 | `05_comparaison_rag_llm.ipynb` | Comparaison mode direct vs RAG + LLM (Groq) : réponses, latence, vérification anti-hallucination | `requirements.txt` complet | Clé API **GROQ_API_KEY** |

Numérotés dans l'ordre logique de lecture (exploration des données → choix
du modèle → évaluation → qualité des données → variante RAG). Chacun reste
exécutable indépendamment.

## À compléter avant de lancer

- **Notebooks 2 et 3** : la liste `QUESTIONS_TEST` contient des questions
  avec un `id_attendu` à renseigner manuellement (l'`id` du chemin correct
  dans `menu_index.json`). Une cellule d'aide (recherche par mot-clé) est
  fournie dans chacun pour les retrouver rapidement. Plus la liste est
  fournie et variée, plus les métriques du notebook 3 sont représentatives.
- **Notebook 5** : demande une clé Groq (gratuite sur
  https://console.groq.com/keys), saisie de façon sécurisée dans le
  notebook (secret Colab ou saisie masquée) — ne jamais la coller en clair
  dans une cellule.

## Notes

- Chaque notebook est autonome : pas besoin de les exécuter dans l'ordre
  pour que l'un fonctionne, sauf que le notebook 3 réindexe ChromaDB
  (`scripts/index_data.py`), ce que le notebook 5 refait aussi de son côté.
- L'environnement Colab est jetable : à chaque nouvelle session, tout est
  réinstallé/régénéré depuis zéro (dépôt cloné, dépendances, index).
- Voir aussi [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) pour le
  schéma du pipeline complet et le rôle de chaque module `src/`.