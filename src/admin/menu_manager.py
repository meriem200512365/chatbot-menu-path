"""
menu_manager.py
-----------------
Gestion du menu Activ Premium depuis l'interface admin :
    - lecture/ecriture de menu.xml avec validation avant toute sauvegarde
    - sauvegardes automatiques horodatees avant chaque modification
    - restauration d'une sauvegarde precedente
    - reindexation complete (XML -> JSON -> ChromaDB) en un clic
    - edition structuree simple (renommer un label) sans toucher au XML brut

SECURITE : menu.xml est la source de verite du menu reel d'Activ Premium.
Toute ecriture est precedee d'une validation stricte (XML bien forme +
structure attendue par xml_parser.py) et d'une sauvegarde automatique,
pour pouvoir revenir en arriere en cas d'erreur.
"""

import os
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

from src.config import XML_PATH, BASE_DIR


BACKUPS_DIR = os.path.join(BASE_DIR, "data", "menu_backups")


def lire_xml_brut() -> str:
    """Retourne le contenu texte brut de menu.xml."""
    with open(XML_PATH, encoding="utf-8") as f:
        return f.read()


def valider_xml(contenu: str) -> tuple:
    """
    Verifie que le contenu est un XML bien forme ET respecte la structure
    attendue par xml_parser.py (MenuModule + MainMenu + au moins un Menu).

    Retourne (est_valide: bool, message: str).
    """
    try:
        root = ET.fromstring(contenu)
    except ET.ParseError as e:
        return False, f"XML mal forme : {e}"

    menu_module = root.find("MenuModule")
    if menu_module is None:
        return False, "Balise <MenuModule> introuvable."

    if not menu_module.get("MainMenu"):
        return False, "Attribut MainMenu manquant sur <MenuModule>."

    menus = menu_module.findall("Menu")
    if not menus:
        return False, "Aucun bloc <Menu> trouve."

    noms_vides = sum(1 for m in menus if not m.get("Name"))
    if noms_vides:
        return False, f"{noms_vides} bloc(s) <Menu> sans attribut Name."

    return True, f"OK : {len(menus)} blocs <Menu> valides."


def creer_backup() -> str:
    """Copie menu.xml actuel dans data/menu_backups/ avec un horodatage.
    Retourne le chemin de la sauvegarde creee."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin_backup = os.path.join(BACKUPS_DIR, f"menu_{horodatage}.xml")
    shutil.copy2(XML_PATH, chemin_backup)
    return chemin_backup


def lister_backups() -> list:
    """Liste les sauvegardes disponibles, plus recentes en premier."""
    if not os.path.exists(BACKUPS_DIR):
        return []
    fichiers = sorted(os.listdir(BACKUPS_DIR), reverse=True)
    return [f for f in fichiers if f.endswith(".xml")]


def ecrire_xml(contenu: str) -> str:
    """
    Valide puis ecrit le nouveau contenu dans menu.xml, apres avoir cree
    une sauvegarde du contenu actuel. Leve une ValueError si invalide
    (rien n'est ecrit dans ce cas).

    Retourne le chemin de la sauvegarde creee.
    """
    est_valide, message = valider_xml(contenu)
    if not est_valide:
        raise ValueError(f"XML invalide, sauvegarde annulee : {message}")

    chemin_backup = creer_backup()

    with open(XML_PATH, "w", encoding="utf-8") as f:
        f.write(contenu)

    return chemin_backup


def restaurer_backup(nom_fichier: str) -> str:
    """Restaure une sauvegarde comme menu.xml actuel (cree d'abord une
    sauvegarde de l'etat courant, pour pouvoir annuler la restauration aussi)."""
    chemin_backup = os.path.join(BACKUPS_DIR, nom_fichier)
    if not os.path.exists(chemin_backup):
        raise ValueError(f"Sauvegarde '{nom_fichier}' introuvable.")

    creer_backup()  # etat actuel sauvegarde avant restauration
    shutil.copy2(chemin_backup, XML_PATH)
    return chemin_backup


def renommer_label(menu_name: str, item_name: str, nouveau_label: str) -> str:
    """
    Edition structuree simple et sure : change uniquement le Label d'un
    MenuItem precis, sans risquer de casser la structure XML.
    Cree une sauvegarde avant modification.
    """
    contenu = lire_xml_brut()
    root = ET.fromstring(contenu)
    menu_module = root.find("MenuModule")

    menu = None
    for m in menu_module.findall("Menu"):
        if m.get("Name") == menu_name:
            menu = m
            break
    if menu is None:
        raise ValueError(f"Menu '{menu_name}' introuvable.")

    item = None
    for it in menu.findall("MenuItem"):
        if it.get("Name") == item_name:
            item = it
            break
    if item is None:
        raise ValueError(f"MenuItem '{item_name}' introuvable dans '{menu_name}'.")

    item.set("Label", nouveau_label)

    chemin_backup = creer_backup()
    ET.indent(root, space="   ")  # garde un formatage lisible
    ET.ElementTree(root).write(XML_PATH, encoding="UTF-8", xml_declaration=True)
    return chemin_backup


def relancer_indexation() -> dict:
    """
    Relance le pipeline complet (extraction + embedding) directement,
    sans passer par un sous-processus. Retourne un resume des resultats.
    """
    from src.extraction.generate_json import generate_menu_index
    from src.embedding.embed_documents import embed_and_store

    kb, report = generate_menu_index()
    nb_indexed = embed_and_store()

    return {
        "nb_chemins": len(kb),
        "nb_liens_casses": report["nb_liens_casses"],
        "nb_menus_orphelins": report["nb_menus_orphelins"],
        "nb_indexed": nb_indexed,
    }