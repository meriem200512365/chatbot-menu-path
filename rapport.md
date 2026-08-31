# Rapport de projet — Chatbot de Navigation Menu (Activ'Premium)

**Stage :** Cegedim — Assistant IA de navigation pour l'application interne
de gestion d'assurance **Activ'Premium**
**Depot :** https://github.com/meriem200512365/chatbot-menu-path

---

## 1. Contexte et objectif

Activ'Premium est une application desktop metier avec un menu de
navigation profond (182 blocs de menu, 1383 chemins de navigation
possibles). Retrouver le bon ecran a partir d'une intention exprimee en
langage naturel ("je veux gerer les actes RO") demande de connaitre le
menu par cœur.

**Objectif du projet** : construire un chatbot qui prend une question en
langage naturel et retourne le chemin exact de navigation dans le menu,
avec deux niveaux de reponse (chemin brut / reponse redigee par un LLM),
une interface utilisateur complete (authentification, historique,
administration), et une base technique testee et documentee.

## 2. Structure du projet

```
chatbot-menu-path/
├── assets/                   # logo Cegedim
├── config/
│   └── auth_config.yaml      # comptes utilisateurs (non versionne)
├── data/
│   ├── menu.xml               # source : export du menu MMB
│   ├── chemins/
│   │   ├── menu_index.json    # base de connaissance {id, label, chemin}
│   │   └── liens_casses.json  # rapport d'anomalies
│   ├── chroma_db/              # base vectorielle (non versionnee)
│   └── history.db              # historique conversations (non versionne)
├── src/
│   ├── config.py               # configuration centralisee
│   ├── extraction/             # XML -> chemins -> JSON
│   ├── embedding/              # texte -> vecteurs
│   ├── database/                # ChromaDB + historique SQLite
│   ├── search/                 # recherche semantique Top-K
│   ├── chatbot/                # mode "chemin direct"
│   ├── generation/              # mode RAG + LLM + vision
│   ├── files/                  # lecture de documents uploades
│   ├── admin/                  # gestion des utilisateurs
│   ├── ui/                     # interface Streamlit (chat + admin)
│   └── api/                    # API FastAPI (integration externe)
├── scripts/                    # indexation, reindexation, outils admin
├── tests/                      # tests unitaires pytest
├── notebooks/                  # exploration et evaluation (Google Colab)
└── docs/ARCHITECTURE.md        # detail des choix techniques
```

## 3. Pipeline general

```
menu.xml
   │  xml_parser.py (parse le XML plat, non imbrique)
   ▼
menus{} (dict {nom_menu: [items]})
   │  path_builder.py (parcours DFS depuis MainMenu, detecte boucles/liens casses)
   ▼
chemins[] + anomalies[]
   │  generate_json.py
   ▼
menu_index.json + liens_casses.json
   │  embed_documents.py (SentenceTransformer)
   ▼
ChromaDB (vecteurs persistants)
   │  semantic_search.py (au runtime, question -> Top-K chemins)
   ▼
chatbot.py (mode direct)  OU  rag_chatbot.py (mode RAG + LLM)
   ▼
Reponse a l'utilisateur (via Streamlit ou API FastAPI)
```

## 4. Modules et fonctions principales

| Fichier | Fonction(s) cle(s) | Role |
|---|---|---|
| `src/extraction/xml_parser.py` | parse le XML | Lit `menu.xml`, retourne le menu racine et le dict de tous les menus |
| `src/extraction/path_builder.py` | parcours DFS | Reconstruit tous les chemins complets, detecte liens casses/orphelins/boucles |
| `src/extraction/generate_json.py` | serialisation | Ecrit `menu_index.json` et `liens_casses.json` |
| `src/embedding/model.py` | chargement modele | Singleton SentenceTransformer, mis en cache |
| `src/embedding/embed_documents.py` | indexation | Encode chaque chemin, l'insere dans ChromaDB |
| `src/database/chroma_manager.py` | acces DB vectorielle | Client persistant, get/reset collection |
| `src/database/history_manager.py` | `creer_conversation`, `ajouter_message`, `get_conversations`, `get_messages`, `definir_feedback`, `supprimer_conversation` | Historique des conversations + feedback, SQLite |
| `src/search/semantic_search.py` | `search(question)` | Encode la question, retourne le Top-K ChromaDB (distance cosinus) |
| `src/chatbot/chatbot.py` | `repondre(question)` | Decide : reponse directe / ambigue / aucun resultat, selon seuils |
| `src/generation/llm_client.py` | `generate(...)` | Appel API Groq (texte) |
| `src/generation/vision_client.py` | `analyser_image(...)` | Appel API Groq (vision), image encodee en base64 |
| `src/generation/rag_chatbot.py` | `repondre_rag(question, document_context)` | Retrieval + generation LLM, assistant generaliste + resolution de chemin |
| `src/files/document_reader.py` | `read_document(...)` | Extrait le texte d'un PDF/Excel/CSV/fichier code uploade |
| `src/admin/user_manager.py` | `ajouter_utilisateur`, `reinitialiser_mot_de_passe`, `modifier_role`, `supprimer_utilisateur` | CRUD utilisateurs sur `auth_config.yaml` |
| `src/api/app.py` | `POST /chat`, `GET /health` | API FastAPI (pour integration externe, ex. appli desktop) |
| `src/ui/streamlit_app.py` | interface principale | Chat, auth, historique, upload, feedback |
| `src/ui/pages/1_Administration.py` | interface admin | Reservee au role `admin` |

## 5. Modeles utilises

| Usage | Modele | Fournisseur | Remarque |
|---|---|---|---|
| Embeddings (recherche semantique) | `paraphrase-multilingual-MiniLM-L12-v2` | SentenceTransformers (local, CPU) | Leger (~470 Mo), supporte le francais, pas besoin de GPU |
| Base vectorielle | ChromaDB | Local, persistant | Metrique cosinus, suffisant pour ~1400 documents |
| Generation de texte (mode RAG) | `openai/gpt-oss-120b` | Groq (cloud, via API) | Configurable via `.env` (`GROQ_MODEL`) |
| Analyse d'image (mode vision) | `qwen/qwen3.6-27b` | Groq (cloud, via API) | Seul modele du catalogue Groq avec `input_modalities` incluant `image` (confirme le 18/08/2026) |
| Authentification | bcrypt (via `streamlit-authenticator`) | Local | Hashage des mots de passe, jamais stockes en clair |

## 6. Fonctionnalites livrees

- Recherche semantique du chemin de menu (mode direct, rapide, sans LLM).
- Mode RAG : assistant generaliste qui repond a toute question, et
  resout un chemin de menu quand c'est pertinent.
- Upload de document (PDF/Excel/CSV/code) comme contexte supplementaire.
- Upload d'image (capture d'ecran, schema) analysee par un modele vision.
- Authentification par compte (nom d'utilisateur + mot de passe hashe).
- Page d'administration : creation de comptes, reset de mot de passe,
  gestion des roles (`admin` / `user`), sans editer de fichier a la main.
- Historique organise par conversations (creation, recherche, reprise,
  suppression), comme une interface de chat classique.
- Feedback 👍/👎 par reponse, stocke en base pour analyse future.
- Detection automatique des liens casses et menus orphelins dans le XML
  source (0 detecte sur le menu reel).
- Suite de tests automatises (pytest) + integration continue (GitHub
  Actions) sur chaque push.

## 7. Problemes rencontres et solutions apportees

| # | Probleme | Cause | Solution |
|---|---|---|---|
| 1 | Workflow CI (`tests.yml`) ne s'executait pas correctement | Melange de syntaxe GitLab CI (`stages:`) et GitHub Actions, indentation invalide | Reecriture du fichier en syntaxe GitHub Actions valide |
| 2 | Fichiers `_init_.py` sans effet | Typo : un seul underscore de chaque cote au lieu de deux (`__init__.py`) | Renommage correct dans `src/generation/` et `src/ui/` |
| 3 | `.env.example` absent alors que reference dans le README | Fichier jamais cree | Creation du fichier avec les variables necessaires et leur usage |
| 4 | Seuils de confiance incoherents entre les deux modes | `chatbot.py` utilisait `distance >= 0.55` (non fiable), `rag_chatbot.py` utilisait `1 - distance >= 0.40` (soit `distance <= 0.60`) — deux seuils differents non partages | Centralisation des seuils dans `src/config.py`, memes constantes importees par les deux modules |
| 5 | `Hasher.__init__() takes 1 positional argument but 2 were given` | API de `streamlit-authenticator` changee entre versions (0.3.x -> 0.4.x) : `Hasher([mdp]).generate()` remplace par `Hasher.hash(mdp)` | Script `generate_password.py` adapte a la nouvelle API ; version de la librairie figee dans `requirements.txt` pour eviter la regression |
| 6 | `LoginError: User not authorized` au demarrage | Cookie de session (navigateur) reference un utilisateur qui n'existe plus dans `auth_config.yaml` | Renommage du `cookie.name` (invalide l'ancien cookie) ou suppression manuelle du cookie navigateur |
| 7 | `.env` provoque des erreurs `python-dotenv could not parse` | Le contenu du README (instructions d'installation) avait ete colle par erreur dans `.env` au lieu des variables d'environnement | Remplacement par le contenu attendu (`GROQ_API_KEY=...`) |
| 8 | Connexion refusee alors que le mot de passe est correct | Confusion entre le champ "Username" (attendu : identifiant, ex. `meriem`) et l'email (`meriem@cegedim.com`) | Clarification : connexion par username, pas par email |
| 9 | Secrets exposes publiquement sur GitHub | Aucun `.gitignore` dans le depot initialement ; `auth_config.yaml` commit avec un vrai hash de mot de passe et la cle de signature de cookie laissee a sa valeur par defaut | Creation d'un `.gitignore` complet, retrait du fichier du suivi git (`git rm --cached`), rotation du mot de passe et de la cle de cookie |
| 10 | Chemins candidats "disparaissent" apres une reponse ambigue | Le message sauvegarde en session/historique ne contenait pas la liste des chemins candidats (seul le cas "reponse directe" les ajoutait), et un `st.rerun()` systematique effacait l'affichage temporaire | Ajout des chemins candidats au message sauvegarde pour le cas "ambigu" egalement |
| 11 | Erreur RAG invisible ("aucune reponse") | `st.rerun()` execute juste apres un message d'erreur, qui n'etait jamais persiste -> l'erreur disparaissait avant d'etre lue | Ajout d'un `st.stop()` apres affichage de l'erreur pour interrompre le rerun et garder le message visible |
| 12 | `Error 404 : model llama-3.3-70b-versatile does not exist` | Groq a deprecie ce modele cote serveur, hors du controle du projet | Passage a `openai/gpt-oss-120b` (verifie disponible via `GET /openai/v1/models`), modele rendu configurable via `.env` pour absorber les futurs changements sans toucher au code |
| 13 | Analyse d'image en echec | Le modele vision precedent (`llama-3.2-11b-vision-preview`) egalement deprecie par Groq, aucun remplaçant evident dans la documentation publique | Interrogation directe de l'API `/models` pour lister les modeles actifs sur le compte ; identification de `qwen/qwen3.6-27b` comme seul modele avec modalite `image` en entree |
| 14 | Erreur `git push` : `Could not resolve host: github.com` | Probleme reseau local (DNS/VPN), sans rapport avec git ou le commit lui-meme | Diagnostic reseau (ping/nslookup), le commit local restait intact en attendant la reconnexion |

## 8. Resultats mesures sur le menu reel (MENU_PREMIUM)

- 182 blocs `<Menu>` extraits du XML
- 1383 chemins de navigation valides reconstruits
- 0 lien casse, 0 menu orphelin detecte

## 9. Limites actuelles et pistes d'amelioration

- **Evaluation chiffree** : les notebooks d'exploration/evaluation
  existent et ont ete executes (Google Colab), mais aucune metrique de
  precision formelle (ex. precision@1 sur un jeu de questions etiquete)
  n'est encore integree au rapport de maniere continue.
- **Synonymes et acronymes metier** (ex. "RO", "RC") : geres uniquement
  par ce que le modele d'embeddings capture nativement, pas de
  dictionnaire d'expansion dedie.
- **Feedback 👍/👎** : collecte en base mais pas encore exploite dans un
  tableau de bord (la fonction `get_stats_feedback()` existe cote
  backend, l'affichage cote admin reste a construire).
- **Logs** : le projet utilise encore `print()` dans les scripts hors
  interface, a remplacer par un module `logging` pour un usage en
  production plus large.
- **Alternative "Classical RAG"** (Meilisearch + Ollama/Phi-4-mini, sans
  GPU) etudiee mais non implementee dans ce depot.

## 10. Conclusion

Le projet couvre l'ensemble de la chaine, depuis l'extraction du menu XML
source jusqu'a une interface utilisateur complete avec authentification,
gestion des utilisateurs, historique de conversations et feedback,
en passant par deux modes de reponse (recherche directe et RAG avec
LLM generaliste). Les problemes rencontres ont majoritairement ete lies
a des changements externes (evolution des API tierces comme Groq et
streamlit-authenticator) plutot qu'a des erreurs de conception, ce qui a
motive le choix de rendre la configuration (modeles LLM, seuils de
confiance) externalisable plutot que codee en dur, pour absorber ce type
de changement a l'avenir sans regression.