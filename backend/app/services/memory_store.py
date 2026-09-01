"""Finova — In-Memory Store for Testing and Disconnected Operation."""
from __future__ import annotations

from typing import Any, Dict, List

memory_users: Dict[str, dict] = {}
memory_orgs: Dict[str, dict] = {}
memory_memberships: List[dict] = []
memory_datasets: Dict[str, dict] = {}
memory_dataset_records: Dict[str, list] = {}
memory_runs: Dict[str, dict] = {}
memory_results: Dict[str, list] = {}
memory_exceptions: Dict[str, dict] = {}
memory_notes: List[dict] = []
memory_adjustments: List[dict] = []
memory_audit_logs: List[dict] = []
memory_integrations: Dict[str, dict] = {}
