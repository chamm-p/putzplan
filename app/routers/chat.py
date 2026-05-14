from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import get_current_user
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import ask
from app.services.stt import transcribe_audio

router = APIRouter()


@router.post("/text", response_model=ChatResponse)
async def chat_text(data: ChatRequest, _: User = Depends(get_current_user)):
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Bitte eine Frage eingeben")
    try:
        answer = await ask(data.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM-Fehler: {e}")
    return ChatResponse(answer=answer)


@router.post("/voice", response_model=ChatResponse)
async def chat_voice(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    audio = await file.read()
    try:
        transcript = await transcribe_audio(audio, file.filename or "audio.webm", file.content_type or "audio/webm")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"STT-Fehler: {e}")
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Keine Sprache erkannt")
    try:
        answer = await ask(transcript)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM-Fehler: {e}")
    return ChatResponse(answer=answer, transcript=transcript)
