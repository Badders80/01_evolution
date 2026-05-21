# Extraction Report: Evolution_CRM

**Source:** `/home/evo/workspace/projects/Evolution_CRM`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Lead tracking records | Prospect lifecycle from interest → KYC → investment | Firestore collection `leads` |
| Investor communication history | Emails, calls, meetings log | Firestore collection `communications` |
| Pipeline reports | Capital raising progress and status | Firestore collection `pipeline` |
| CRM data | Contact details, relationship status, notes | Firestore collection `contacts` |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| TBD | CRM platform not yet chosen | Options: Twenty (open-source), HubSpot, or Firestore + Cloud Functions |

**This project is the least mature in the ecosystem.** No code, no database, no deployment. Only architecture docs and a `Client_Template/` directory.

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| TBD | Depends on CRM platform choice | — |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| None | No code to validate |

---

## Key Business Logic / Pipeline Milestones

1. **Lead Capture** — Receive leads from Evolution_Platform (public site forms)
2. **Lead Qualification** — Track leads through pipeline stages (new → contacted → qualified → converted)
3. **KYC Status Tracking** — Link to Evolution_Token KYC verification status
4. **Investment Tracking** — Link to Evolution_Token investment records
5. **Communication Logging** — Record all investor communications
6. **Pipeline Reporting** — Capital raising progress dashboard

### Critical Business Rules

- Lead tracking and pipeline stages are non-negotiable
- Investor communication history is non-negotiable
- Reporting for capital raising progress is non-negotiable
- Automated marketing campaigns are explicitly excluded
- Public-facing CRM portal is excluded
- Real-time chat or support ticketing is excluded

### Data Flow (Unidirectional)

```
SSOT_Build → Evolution_CRM (horse/customer data)
Evolution_Token → Evolution_CRM (investor data, KYC status, holdings)
Evolution_Platform → Evolution_CRM (lead capture from public site)
Evolution_CRM → Evolution_Ops (investor financial history)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| No code exists | Starting from scratch | Build Firestore + Cloud Functions from the start |
| CRM platform not chosen | Decision paralysis | Start with Firestore + Cloud Functions (keeps data in-stack) |
| No data model | No schema defined | Use Pydantic models from vertex_workspace as starting point |
| Bi-directional sync risk | CRM might try to write back to SSOT | Enforce unidirectional flow: CRM is a client of SSOT API |
| No tests | Nothing to test yet | Define test requirements before building |