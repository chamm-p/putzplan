from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me"

    REGISTRATION_ENABLED: bool = True
    TOKEN_EXPIRE_DAYS: int = 60

    OIDC_ENABLED: bool = False
    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""
    OIDC_SCOPES: str = "openid email profile"
    OIDC_BUTTON_LABEL: str = "Mit Keycloak anmelden"

    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"

    STT_BASE_URL: str = "https://api.openai.com/v1"
    STT_API_KEY: str = ""
    STT_MODEL: str = "whisper-1"

    DATABASE_URL: str = "sqlite:///./data/putzplan.db"
    SEED_FILE: str = "seeds/tasks.yaml"

    LEADERBOARD_DAYS: int = 10  # "Putzkönig" rolling window

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
