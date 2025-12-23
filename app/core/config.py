"""Application configuration using Pydantic Settings."""

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    GEMINI_API_KEY: str

    # Email Configuration
    EMAIL_FROM: str = "noreply@petstory.com"
    EMAIL_FROM_NAME: str = "PetStory"

    # SMTP Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # Email do remetente (ex: seu-email@gmail.com)
    SMTP_PASSWORD: str = ""  # Senha de app ou senha do email

    # Application
    APP_NAME: str = "PetStory API"
    DEBUG: bool = False
    API_BASE_URL: str = "http://localhost:8000"  # Base URL da API (para webhooks e redirects)

    # Worker Configuration
    WORKER_SLEEP_SECONDS: float = 2.0  # Delay entre gerações para evitar rate limit

    # Backup/Storage Configuration
    TEMP_DIR: str = "temp"  # Diretório para salvar backups dos arquivos gerados

    # Gemini Model Configuration
    GEMINI_IMAGE_MODEL: str = "gemini-2.5-flash-image"  # ou "gemini-3-pro-image-preview"

    # Mercado Pago Configuration
    MERCADOPAGO_ACCESS_TOKEN: str = ""  # Access token do Mercado Pago
    MERCADOPAGO_PUBLIC_KEY: str = ""  # Public key (opcional, para frontend)
    MERCADOPAGO_PRODUCT_PRICE: float = 47.0  # Preço do produto em reais
    MERCADOPAGO_WEBHOOK_SECRET: str = ""  # Secret para validar webhooks (opcional)

    # CORS Configuration
    # Pode ser uma string JSON ou valores separados por vírgula
    CORS_ORIGINS: str = (
        "https://seu-usuario.github.io,"
        "http://localhost:3000,"
        "http://localhost:8000,"
        "http://127.0.0.1:8000,"
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "null"  # Permite file:// quando o HTML é aberto diretamente
    )

    def _parse_cors_origins(self, value: str | List[str]) -> List[str]:
        """Parse CORS origins from string (JSON array or comma-separated)."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin) for origin in parsed]
            except (json.JSONDecodeError, TypeError):
                pass
            # Fall back to comma-separated values
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            # In debug mode, allow all origins for development
            if self.DEBUG and "*" not in origins:
                origins.append("*")
            return origins
        return []

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return self._parse_cors_origins(self.CORS_ORIGINS)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance
settings = Settings()

