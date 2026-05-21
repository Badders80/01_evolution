# Extraction Report: Evolution_Ops

**Source:** `/home/evo/workspace/projects/Evolution_Ops`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| GST reports (XLSX/JSON) | IRD-ready GST returns | Cloud Storage bucket → download |
| Bank reconciliation reports | Matched transactions with anomaly flags | Firestore collection `transactions` |
| Processed cheque data | BNZ cheque CSV processing output | Firestore collection `banking` |
| Payroll calculations | Pay slips and deduction records | Firestore collection `payroll` |
| Compliance documentation | Audit-ready financial records | Cloud Storage bucket |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Python 3 | Scripting runtime | All scripts are Python |
| pandas | Data processing | Core data manipulation library |
| openpyxl | Excel handling | For GST XLSX generation |
| Ollama (local) | OCR for financial documents | Must stay local for data sensitivity |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `OLLAMA_HOST` | Local Ollama API endpoint | Yes (for OCR) |
| Various banking credentials | Bank statement access | Sensitive — must stay local |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | Placeholder — no real checks defined |
| `python scripts/gst_wizard.py` | GST processing script |
| `python scripts/process_cheque_v2.py` | Cheque processing |
| `python scripts/merge_gst_v2.py` | GST report merging |

**Critical Gap:** Zero automated tests. No CI/CD. No linting.

---

## Key Business Logic / Pipeline Milestones

1. **Bank Statement Ingestion** — Ingest bank statements (CSV, PDF, scanned) into processing pipeline
2. **Transaction Categorization** — AI-assisted categorization of transactions (GST vs non-GST)
3. **GST Calculation** — Calculate GST returns from categorized transactions
4. **Report Generation** — Generate IRD-ready GST reports (XLSX + JSON)
5. **Reconciliation** — Match bank transactions against expected entries, flag anomalies
6. **Payroll Processing** — Calculate pay, deductions, generate payslips

### Critical Business Rules

- GST reports must be accurate and IRD-compliant (non-negotiable)
- Bank statement ingestion must handle multiple formats (CSV, PDF, scanned)
- Financial documents must stay local (Ollama OCR, not cloud)
- Payroll must be accurate and documented

### Data Flow (Unidirectional)

```
Evolution_Token → Evolution_Ops (financial data: payments, holdings)
Evolution_Platform → Evolution_Ops (traffic/analytics for cost attribution)
Evolution_Ops → Evolution_CRM (investor financial history)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| No automated tests | Financial calculations are high-risk without tests | Add pytest suite for GST calculations |
| Local Python scripts only | No cloud deployment, no scheduling | Move to Cloud Functions or Cloud Run |
| No structured data store | Files in `banking/raw/` and `gst/raw/` | Migrate to Firestore collections |
| Sensitive financial data on local machine | No backup, no access control | Cloud Storage with IAM + encryption |
| No OCR pipeline for scanned PDFs | Manual processing bottleneck | Vertex AI Document AI for cloud, Ollama for local |
| No CI/CD | Manual execution only | Add Cloud Build pipeline |
| No input validation | Garbage in, garbage out | Add Pydantic models for all inputs |