"""Finova — Generic Integration Provider Base Class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class IntegrationProvider(ABC):
    """Abstract interface for payment gateway and bank feed providers."""

    @abstractmethod
    async def test_connection(self) -> Tuple[bool, str]:
        """Test authentication and connectivity."""
        pass

    @abstractmethod
    async def fetch_payments(self, count: int = 50, since: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch raw payment transactions."""
        pass

    @abstractmethod
    async def fetch_settlements(self, count: int = 20, since: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetch raw settlement payouts."""
        pass
