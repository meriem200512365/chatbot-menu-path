"""
test_chatbot.py
-----------------
Teste la logique de decision de src.chatbot.chatbot.repondre() : elle ne
doit PAS appeler le vrai modele d'embeddings / ChromaDB, on simule donc
la fonction search() (monkeypatch) pour tester uniquement les seuils de
confiance et la detection d'ambiguite.
"""

import src.chatbot.chatbot as chatbot_module


def _resultat(path_str, distance, id_="ID1"):
    return {"id": id_, "label": path_str.split(" > ")[-1], "path_str": path_str,
            "path_ids": id_, "distance": distance}


def test_aucun_resultat_si_recherche_vide(monkeypatch):
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: [])
    rep = chatbot_module.repondre("question quelconque")
    assert rep["type"] == "aucun_resultat"


def test_aucun_resultat_si_distance_trop_elevee(monkeypatch):
    resultats = [_resultat("Prestations > Actes", 0.80)]
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: resultats)
    rep = chatbot_module.repondre("hors sujet")
    assert rep["type"] == "aucun_resultat"


def test_reponse_directe_confiance_haute(monkeypatch):
    resultats = [
        _resultat("Prestations > Actes > Gestion des Actes RO", 0.10),
        _resultat("Prestations > Devis", 0.50),
    ]
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: resultats)
    rep = chatbot_module.repondre("je veux gerer les actes RO")

    assert rep["type"] == "reponse_directe"
    assert rep["confiance"] == "haute"
    assert "Gestion des Actes RO" in rep["message"]


def test_reponse_directe_confiance_moyenne(monkeypatch):
    resultats = [_resultat("Prestations > Actes", 0.40)]
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: resultats)
    rep = chatbot_module.repondre("actes")

    assert rep["type"] == "reponse_directe"
    assert rep["confiance"] == "moyenne"


def test_ambiguite_detectee_si_deux_resultats_tres_proches(monkeypatch):
    resultats = [
        _resultat("Prestations > Actes RO", 0.20),
        _resultat("Prestations > Actes RC", 0.22),  # ecart 0.02 < ECART_AMBIGUITE (0.05)
    ]
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: resultats)
    rep = chatbot_module.repondre("actes")

    assert rep["type"] == "ambigu"
    assert len(rep["resultats"]) == 2


def test_pas_ambigu_si_ecart_suffisant(monkeypatch):
    resultats = [
        _resultat("Prestations > Actes RO", 0.15),
        _resultat("Prestations > Actes RC", 0.40),  # ecart 0.25 > seuil
    ]
    monkeypatch.setattr(chatbot_module, "search", lambda q, **kw: resultats)
    rep = chatbot_module.repondre("actes")

    assert rep["type"] == "reponse_directe"
