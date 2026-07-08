"""
app.py
------
Point d'entree unique de l'API. Expose le chatbot via FastAPI pour que
l'application desktop puisse l'appeler en HTTP.

Lancement :
    uvicorn src.api.app:app --reload --port 8000

Exemple d'appel :
    POST http://localhost:8000/chat
    { "question": "je veux gerer les actes RO" }
"""

from fastapi import FastAPI
from pydantic import BaseModel

from src.chatbot.chatbot import repondre

app = FastAPI(
    title="Chatbot Navigation Menu",
    description="Resout une question en langage naturel vers un chemin de menu.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    type: str
    message: str
    resultats: list


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return repondre(req.question)
