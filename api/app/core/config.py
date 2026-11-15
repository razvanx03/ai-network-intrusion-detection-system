from pathlib import Path
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate root directory and ensure .env exists
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"Critical configuration file missing: '{ENV_PATH}'. "
        "A valid .env file is strictly required. No default fallback values are allowed."
    )


class Settings(BaseSettings):
    """
    Application Settings strictly loaded from .env.
    No silent defaults or insecure fallbacks are permitted.
    Missing variables will cause an immediate validation failure on startup.
    """
    PROJECT_NAME: str
    ENVIRONMENT: str
    DEBUG: bool
    API_PREFIX: str

    # Security & JWT (Strictly required from .env - no insecure defaults)
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: str

    # Single Admin User Credentials (Strictly required from .env)
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Database
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: List[str]

    # Sensor VM Agent
    SENSOR_MOCK_MODE: bool
    SENSOR_AGENT_URL: str
    SENSOR_AGENT_API_KEY: str
    SENSOR_CA_CERT: str

    @model_validator(mode="after")
    def validate_sensor_tls(self):
        if not self.SENSOR_MOCK_MODE:
            from urllib.parse import urlsplit
            import ssl
            url = urlsplit(self.SENSOR_AGENT_URL)
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
                raise ValueError("SENSOR_AGENT_URL must be an HTTPS origin without credentials, path, query or fragment.")
            if not self.SENSOR_CA_CERT.strip():
                raise ValueError("SENSOR_CA_CERT is required for a remote sensor.")
            path = Path(self.SENSOR_CA_CERT)
            if not path.is_absolute():
                path = ROOT_DIR / path
            ssl.create_default_context(cafile=str(path))
            self.SENSOR_CA_CERT = str(path)
        return self


    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("["):
                import json
                try:
                    parsed = json.loads(v_stripped)
                    if not isinstance(parsed, list):
                        raise ValueError("CORS_ORIGINS JSON must be a list of origin strings.")
                    return parsed
                except Exception as e:
                    raise ValueError(f"Invalid CORS_ORIGINS JSON format in .env: {e}")
            else:
                origins = [i.strip() for i in v_stripped.split(",") if i.strip()]
                if not origins:
                    raise ValueError("CORS_ORIGINS must contain at least one valid origin.")
                return origins
        elif isinstance(v, list):
            if not v:
                raise ValueError("CORS_ORIGINS list cannot be empty.")
            return v
        raise ValueError(f"Invalid CORS_ORIGINS type: {type(v)}")

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
