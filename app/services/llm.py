import httpx

from app.config import settings

SYSTEM_PROMPT = """Du bist ein knapper, sachkundiger Putz- und Reinigungs-Berater für den Haushalt.

REGELN:
- Antworte AUSSCHLIESSLICH zu Themen rund um Haushaltsreinigung, Pflege von Oberflächen, Materialien, Flecken, Werkzeuge, Hausmittel.
- Bei Fragen außerhalb dieses Themas: kurz und höflich darauf hinweisen, dass du nur zum Putzen Auskunft gibst.
- KEINE Aufsätze, KEINE langen Einleitungen, KEINE Disclaimer.
- Antworte direkt, in maximal 4 kurzen Sätzen ODER einer 3–5-Schritte-Aufzählung mit Bindestrichen.
- Nenne konkrete Mittel (z.B. "Essigreiniger 1:5 mit Wasser") und sage was zu vermeiden ist (z.B. "keine Säure auf Naturstein").
- Wenn ein Material kritisch ist (Marmor, Granit, Parkett, Naturstein), warne in einem Halbsatz.
- Sprache: Deutsch."""


async def ask(question: str) -> str:
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            json={
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.3,
            },
        )
        if r.status_code >= 400:
            raise RuntimeError(f"LLM {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"].strip()
