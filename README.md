# Finova — AI-Powered Finance Controller & Reconciliation Platform

Finova is an enterprise-grade, high-performance financial reconciliation, exceptions management, and cash forecasting platform designed for modern finance teams and payment operations.

---

## 🌟 Core Architectural Highlights

1. **Deterministic Multi-Stage Finance Engine**:
   - Exact and fuzzy reference matching (RRN, UTR, Order ID, Cheque number).
   - Weighted multi-signal confidence scoring (`reference`, `amount`, `customer`, `date`, `invoice`, `description`).
   - Configurable organizational tolerances (amount, date drift, gateway fee deductions, GST/TDS tolerances).
   - Strict currency validation and Decimal arithmetic to prevent floating-point drift.

2. **Enterprise Multi-Tenancy & RBAC**:
   - Native organization-level data partitioning (`organization_id` scoping on every collection and query).
   - Role-Based Access Control (`OWNER`, `ADMIN`, `FINANCE_MANAGER`, `FINANCE_ANALYST`, `VIEWER`).
   - Secure bcrypt password hashing and JWT access & refresh token authentication.
   - Dynamic organization switcher and multi-org membership support.

3. **Ingestion Engine & Intelligent Column Mapper**:
   - Flexible CSV/JSON statement ingestion with auto-detection of canonical column mappings.
   - Pre-validation hygiene reporting (valid row count, invalid row error diagnostics, duplicate detection).
   - Provable data provenance (raw ingested fields preserved in `_raw`).

4. **Cryptographic SHA-256 Hash-Chained Audit Trail**:
   - Immutable, append-only event ledger.
   - Sequential block-level cryptographic verification (`current_hash = SHA256(prev_hash + payload)`).
   - Real-time tamper detection via `/api/v1/audit-logs/verify`.
   - Automatic masking and scrubbing of API keys, card numbers, passwords, and secrets.

5. **AI Investigation Guardrails (Gemini Integration)**:
   - Automated forensic investigation of ledger discrepancies, timing differences, and fee deductions.
   - Strict prompt versioning (`finance-investigator-v1`) and prompt SHA-256 hash tracking.
   - Latency tracking (`latency_ms`) and transparent fallback labeling.
   - Advisory-only role: deterministic finance engine remains the immutable source of financial truth.

6. **Human-in-the-Loop (HITL) Finance Operations**:
   - Interactive exceptions triage queue with severity badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
   - Task assignment to finance officers, comment discussion threads, and audited ledger adjustments.
   - Single-click approvals, rejections, and ignore actions with automatic audit event generation.

7. **Real Payment Integrations & Export Capabilities**:
   - Modular `IntegrationProvider` supporting Razorpay (Live and Sandbox modes).
   - Test ping and on-demand payment & settlement synchronization into the reconciliation workflow.
   - Standardized CSV and JSON exports for Reconciliation Ledgers, Exceptions, Audit Trails, and Batch Runs.

8. **Dynamic Cash Forecasting & Real-Time Analytics**:
   - 14-day rolling cash projection engine factoring in daily transaction volume, moving averages, and expected gateway settlements.
   - Tenant-scoped KPI analytics (match rates, precision, recall, F1 scores, processing time).
   - Graceful `INSUFFICIENT_DATA` handling when historical observations are scarce.

---

## 🏗️ System Architecture

```
                                  ┌──────────────────────────┐
                                  │   React 18 + Tailwind    │
                                  │  Finance Console (Vite)  │
                                  └─────────────┬────────────┘
                                                │ REST / JWT
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Backend Server                                 │
│                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐  │
│  │   Auth & RBAC Layer   │   │  Ingestion & Mapping  │   │  Reconciliation Pipeline │  │
│  │  (JWT, Bcrypt, Orgs)  │   │  (Column Detection)   │   │  (Multi-Signal Scoring)  │  │
│  └───────────────────────┘   └───────────────────────┘   └──────────────────────────┘  │
│                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐  │
│  │  Audit Logger (SHA)   │   │  AI Engine (Gemini)   │   │   Integrations Hub       │  │
│  │ (Hash-Chained Proof)  │   │  (Latency & Version)  │   │   (Razorpay Provider)    │  │
│  └───────────────────────┘   └───────────────────────┘   └──────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │       MongoDB Multi-Tenant Store        │
                       │    (Compound Indexes + In-Memory Fallback)   │
                       └─────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The web console will be accessible at `http://localhost:5173`.

---

## 🧪 Testing & Benchmark Results

### Automated Test Suite
The test suite validates multi-tenancy, authentication, hash-chain integrity, AI guardrails, payment integrations, and reconciliation:

```bash
.\backend\.venv\Scripts\python -m pytest backend/tests -v
```
**Status: 80 / 80 Tests Passing (100% Pass Rate)**

### Performance Benchmark
Run the high-volume reconciliation benchmark:

```bash
.\backend\.venv\Scripts\python backend/scripts/run_benchmark.py
```

**Benchmark Highlights**:
- **Dataset Size**: 250 records
- **Processing Time**: ~0.072 seconds (>3,400 transactions/sec)
- **Match Rate**: 79.20%
- **F1 Score**: 93.87% (Precision: 88.89%, Recall: 99.44%)
- **Cryptographic Audit Log Generation**: Sub-millisecond latency per event
