"""Finova — Core Configuration."""
from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Finova")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="finova")

    # AI
    gemini_api_key: str = Field(default="")
    demo_mode: bool = Field(default=True)

    # Razorpay
    razorpay_key_id: str = Field(default="")
    razorpay_key_secret: str = Field(default="")

    # CORS
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")

    # Authentication & JWT
    jwt_secret_key: str = Field(default="finova-production-secret-key-at-least-32-chars-long-2026")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=1440)  # 24 hours
    jwt_refresh_token_expire_days: int = Field(default=7)

    # Multi-currency & Rates
    base_currency: str = Field(default="INR")
    supported_currencies: str = Field(default="INR,USD,EUR,GBP,JPY,CAD,AUD,SGD")
    exchange_rates_json: str = Field(default='{"USD": 83.5, "EUR": 90.2, "GBP": 106.0, "INR": 1.0, "CAD": 61.2, "AUD": 54.1, "SGD": 62.3, "JPY": 0.55}')

    # AI Prompt Versioning
    prompt_version: str = Field(default="finance-investigator-v1")

    # Rate limiting & Retention
    rate_limit_per_minute: int = Field(default=120)
    audit_retention_days: int = Field(default=2555)  # 7 years financial compliance

    # Reconciliation thresholds
    auto_reconcile_threshold: float = Field(default=0.90)
    ai_review_threshold: float = Field(default=0.70)

    # Upload limits
    max_upload_size: int = Field(default=1073741824)  # 1GB (1024MB)

    # Confidence scoring weights (must sum to 1.0)
    weight_reference: float = Field(default=0.30)
    weight_amount: float = Field(default=0.30)
    weight_customer: float = Field(default=0.15)
    weight_date: float = Field(default=0.10)
    weight_invoice: float = Field(default=0.10)
    weight_description: float = Field(default=0.05)

    # Financial rule tolerances
    fee_tolerance_percent: float = Field(default=0.05)   # 5% max fee
    tax_tolerance_percent: float = Field(default=0.20)   # up to 20% tax
    date_tolerance_days: int = Field(default=3)
    partial_payment_tolerance_percent: float = Field(default=0.10)
    settlement_delay_days: int = Field(default=5)

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supported_currencies_list(self) -> List[str]:
        """Return list of supported currencies."""
        return [c.strip().upper() for c in self.supported_currencies.split(",") if c.strip()]

    @property
    def exchange_rates(self) -> dict:
        """Return exchange rate map to base currency INR."""
        import json
        try:
            return json.loads(self.exchange_rates_json)
        except Exception:
            return {"USD": 83.5, "EUR": 90.2, "GBP": 106.0, "INR": 1.0}

    @property
    def is_demo_mode(self) -> bool:
        """Returns True when in demo mode or no Gemini key configured."""
        return self.demo_mode or not self.gemini_api_key

    @property
    def ai_provider_name(self) -> str:
        """Human-readable AI provider name."""
        if self.is_demo_mode:
            return "DEMO MODE"
        return "gemini"


# Single settings instance
settings = Settings()

