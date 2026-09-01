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
    cors_origins: str = Field(default="http://localhost:5173")

    # Reconciliation thresholds
    auto_reconcile_threshold: float = Field(default=0.90)
    ai_review_threshold: float = Field(default=0.70)

    # Upload limits
    max_upload_size: int = Field(default=52428800)  # 50MB

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
        return [o.strip() for o in self.cors_origins.split(",")]

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
