"""Finova — Mock Razorpay Service.

Provides simulated Razorpay payment/settlement data for development and demo.
Does not require real Razorpay credentials.
"""
from __future__ import annotations

import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List


def get_mock_payments(count: int = 10) -> List[Dict]:
    """Return simulated Razorpay payment objects."""
    payments = []
    for i in range(count):
        amount = random.randint(500, 50000) * 100  # In paise
        payments.append({
            "id": f"pay_{uuid.uuid4().hex[:14]}",
            "entity": "payment",
            "amount": amount,
            "currency": "INR",
            "status": random.choice(["captured", "authorized"]),
            "method": random.choice(["upi", "card", "netbanking"]),
            "description": f"Order payment {i+1}",
            "order_id": f"order_{uuid.uuid4().hex[:14]}",
            "contact": f"+9198765{random.randint(10000,99999)}",
            "email": f"customer{i+1}@example.com",
            "created_at": int((datetime.utcnow() - timedelta(days=random.randint(0,30))).timestamp()),
        })
    return payments


def get_mock_settlements(count: int = 5) -> List[Dict]:
    """Return simulated Razorpay settlement objects."""
    settlements = []
    for i in range(count):
        gross = random.randint(10000, 500000) * 100  # In paise
        fee = int(gross * 0.02)
        tax = int(fee * 0.18)
        net = gross - fee - tax
        settlements.append({
            "id": f"setl_{uuid.uuid4().hex[:14]}",
            "entity": "settlement",
            "amount": net,
            "fees": fee,
            "tax": tax,
            "status": "processed",
            "utr": f"UTR{random.randint(100000000,999999999)}",
            "created_at": int((datetime.utcnow() - timedelta(days=random.randint(1,7))).timestamp()),
        })
    return settlements
