"""Finova — AI Provider Abstract Base Class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class AIProvider(ABC):
    """Abstract AI provider interface."""

    @abstractmethod
    async def investigate(
        self,
        context: Dict[str, Any],
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Investigate a financial discrepancy.

        Args:
            context: Structured financial context (transaction, invoice, etc.)
            prompt: Investigation prompt

        Returns:
            Structured investigation result dict
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        raise NotImplementedError
