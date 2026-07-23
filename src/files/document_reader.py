"""
document_reader.py
-------------------
Extrait le texte d'un fichier uploade (PDF, Excel, CSV, texte/code), pour
le fournir comme contexte supplementaire au LLM.

Le texte extrait est tronque (MAX_CHARS) pour ne pas depasser la fenetre
de contexte du LLM et eviter des couts/latences excessifs.
"""

import io
import os

import pandas as pd
from pypdf import PdfReader

MAX_CHARS = 8000  # limite de securite envoyee au LLM

EXTENSIONS_TEXTE = {".txt", ".py", ".js", ".ts", ".json", ".xml", ".md", ".java", ".sql", ".yaml", ".yml"}


def read_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def read_excel(file_bytes: bytes) -> str:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    parts = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        parts.append(f"--- Feuille : {sheet_name} ---\n{df.to_string(index=False)}")
    return "\n\n".join(parts)


def read_csv(file_bytes: bytes) -> str:
    df = pd.read_csv(io.BytesIO(file_bytes))
    return df.to_string(index=False)


def read_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def read_document(filename: str, file_bytes: bytes) -> dict:
    """
    Retourne :
    {
        "text": "... contenu extrait, tronque ...",
        "truncated": bool,
        "error": None ou message d'erreur,
    }
    """
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == ".pdf":
            text = read_pdf(file_bytes)
        elif ext in (".xlsx", ".xls"):
            text = read_excel(file_bytes)
        elif ext == ".csv":
            text = read_csv(file_bytes)
        elif ext in EXTENSIONS_TEXTE:
            text = read_text(file_bytes)
        else:
            return {"text": "", "truncated": False, "error": f"Extension non supportee : {ext}"}
    except Exception as e:
        return {"text": "", "truncated": False, "error": f"Erreur de lecture : {e}"}

    truncated = len(text) > MAX_CHARS
    return {
        "text": text[:MAX_CHARS],
        "truncated": truncated,
        "error": None,
    }