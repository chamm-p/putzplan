import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm", content_type: str = "audio/webm") -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{settings.STT_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.STT_API_KEY}"},
            files={"file": (filename, audio_bytes, content_type)},
            data={"model": settings.STT_MODEL},
        )
        if r.status_code >= 400:
            logger.error("STT upstream %s: %s", r.status_code, r.text[:500])
            raise RuntimeError(f"STT {r.status_code}: {r.text[:200]}")
        return r.json().get("text", "")
