import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserProfile
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services.oidc import get_discovery, make_state, verify_state, exchange_code, fetch_userinfo

router = APIRouter()


@router.get("/config")
def auth_config():
    return {
        "registration_enabled": settings.REGISTRATION_ENABLED,
        "oidc_enabled": settings.OIDC_ENABLED,
        "oidc_button_label": settings.OIDC_BUTTON_LABEL,
    }


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if not settings.REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="Registrierung ist deaktiviert")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username bereits vergeben")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    user = User(username=data.username, email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)):
    return UserProfile(id=user.id, username=user.username, email=user.email)


@router.get("/oidc/login")
async def oidc_login():
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC nicht aktiviert")
    discovery = await get_discovery()
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": settings.OIDC_SCOPES,
        "state": make_state(),
    }
    return RedirectResponse(f"{discovery['authorization_endpoint']}?{urlencode(params)}")


@router.get("/oidc/callback")
async def oidc_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC nicht aktiviert")
    if error:
        return RedirectResponse(f"/?oidc_error={error}")
    if not code or not state or not verify_state(state):
        raise HTTPException(status_code=400, detail="Ungültiger OIDC-Callback")

    try:
        tokens = await exchange_code(code)
        userinfo = await fetch_userinfo(tokens["access_token"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OIDC-Fehler: {e}")

    sub = userinfo.get("sub")
    if not sub:
        raise HTTPException(status_code=502, detail="OIDC: kein 'sub' Claim")
    email = userinfo.get("email") or f"{sub}@oidc.local"
    username = userinfo.get("preferred_username") or userinfo.get("email") or sub

    user = db.query(User).filter(User.oidc_sub == sub).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.oidc_sub = sub
        else:
            base = username
            n = 0
            while db.query(User).filter(User.username == base).first():
                n += 1
                base = f"{username}{n}"
            user = User(
                username=base,
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                oidc_sub=sub,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    return RedirectResponse(f"/?token={create_access_token(user.id)}")
