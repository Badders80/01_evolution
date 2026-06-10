# Evolution — Stripe Integration Rules

**Version:** 1.0
**Created:** 2026-06-10
**Status:** ✅ Active

---

## Architecture

```
02_website (Next.js)             01_evolution (Cloud Functions)         Stripe
─────────────────                ─────────────────────────────         ──────
User clicks "Verify ID"  ──→  POST /kyc/sessions  ──→  Stripe Identity
User completes KYC       ←──  Stripe redirects back to 02_website
Stripe webhook           ──→  POST /kyc/webhook    ←──  Stripe servers
                                    ↓
                              Firestore: users/{uid}.kyc_status = "verified"
                              Firebase: custom claims updated

User clicks "Invest"     ──→  POST /payments/sessions ──→ Stripe Checkout
User pays                ←──  Stripe redirects back to 02_website  
Stripe webhook           ──→  POST /payments/webhook   ←──  Stripe servers
                                    ↓
                              Firestore: holdings/{id} created
                              Firestore: hlts/{id}.shares_sold incremented
```

**Rule:** `01_evolution` is the **only writer** to Firestore. `02_website` never touches Stripe or Firestore directly.

---

## KYC (Stripe Identity)

### Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/kyc/sessions` | Firebase ID token | Create Stripe Identity verification session |
| `POST` | `/kyc/webhook` | Stripe signature | Receive verification results |

### Create Session (`api/kyc/routes/create_session.py`)

**Request:**
```json
{
  "user_id": "firebase-auth-uid",
  "email": "investor@example.com",
  "return_url": "https://evolution.nz/auth/verify"
}
```

**Response (200):**
```json
{
  "session_id": "vs_xxx",
  "url": "https://verify.stripe.com/...",
  "status": "requires_input"
}
```

**Side effects:**
- Creates `users/{user_id}` document if it doesn't exist (lazy creation)
- Sets `users/{user_id}.kyc_status = "pending"`
- Sets `users/{user_id}.stripe_identity_session_id = session.id`

### Webhook (`api/kyc/routes/webhook.py`)

**Events handled:**

| Stripe Event | Firestore Update | Firebase Claims |
|-------------|-----------------|-----------------|
| `identity.verification_session.verified` | `kyc_status = "verified"` | `role = "investor"` |
| `identity.verification_session.requires_input` | `kyc_status = "requires_input"` | `kyc_status = "requires_input"` |
| `identity.verification_session.canceled` | `kyc_status = "canceled"` | `kyc_status = "canceled"` |

**Firestore collection:** `users/{user_id}`
**Fields written:** `kyc_status`, `updated_at`
**Firebase custom claims:** `kyc_status`, `role`

---

## Payments (Stripe Checkout)

### Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/payments/sessions` | Firebase ID token | Create Stripe Checkout session |
| `POST` | `/payments/webhook` | Stripe signature | Process completed payments |

### Create Session (`api/payments/routes/create_session.py`)

**Request:**
```json
{
  "user_id": "firebase-auth-uid",
  "hlt_id": "hlt-document-id",
  "shares_to_buy": 10,
  "success_url": "https://evolution.nz/invest/success",
  "cancel_url": "https://evolution.nz/invest/cancel",
  "bypass_kyc": false
}
```

**Validation gates (in order):**
1. All required fields present → 400
2. `shares_to_buy` is positive integer → 400
3. User exists in Firestore → 404
4. **KYC check:** `kyc_status == "verified"` → 403 (bypassable in test mode with `bypass_kyc: true`)
5. HLT exists → 404
6. HLT status is `published` or `publish_ready` → 400
7. `shares_to_buy <= shares_available` → 400
8. `share_price_cents > 0` → 400

**Stripe Checkout metadata (attached to session):**
```
user_id, hlt_id, shares_to_buy, horse_microchip, percentage_owned, purchase_price_cents
```

### Webhook (`api/payments/routes/webhook.py`)

**Events handled:**

| Stripe Event | Action |
|-------------|--------|
| `checkout.session.completed` | Firestore transaction: increment `hlts/{id}.shares_sold` + create `holdings/{id}` |

**Firestore transaction (atomic):**
1. Re-read HLT, verify shares still available (concurrency guard)
2. Increment `hlts/{id}.shares_sold`
3. Create `holdings/{id}` document

**Holding record shape:**
```json
{
  "id": "auto-generated",
  "user_id": "firebase-auth-uid",
  "hlt_id": "hlt-document-id",
  "horse_microchip": "985125000126462",
  "shares_owned": 10,
  "percentage_owned": 2.5,
  "purchase_price_cents": 50000,
  "stripe_session_id": "cs_xxx",
  "status": "paid",
  "document_acknowledgements": {
    "term_sheet": true,
    "pds": true,
    "sa": true
  }
}
```

---

## KYC → Payment Eligibility

```
kyc_status          Can invest?
─────────          ──────────
none                ❌ 403
pending             ❌ 403
requires_input      ❌ 403
canceled            ❌ 403
verified            ✅ Allowed
```

**Dev bypass:** Set `bypass_kyc: true` in the request body. Only works when `STRIPE_SECRET_KEY` starts with `sk_test_`.

---

## Error Handling

| Scenario | HTTP | Response |
|----------|------|----------|
| Missing required field | 400 | `{"error": "user_id is required"}` |
| User not found | 404 | `{"error": "User {uid} not found"}` |
| KYC not verified | 403 | `{"error": "User KYC status is '{status}'. Verification is required before purchase."}` |
| HLT not available | 400 | `{"error": "HLT is not available for purchase (status: {status})"}` |
| Insufficient shares | 400 | `{"error": "Requested {n} shares, but only {m} are available"}` |
| Stripe API error | 400 | `{"error": "Stripe error: {message}"}` |
| Invalid webhook signature | 400 | `{"error": "Invalid signature"}` |
| Concurrency conflict | 500 | `{"error": "Transaction failed: {message}"}` |

---

## Idempotency & Retry

- **Checkout sessions:** Stripe handles idempotency via `Idempotency-Key` header (not currently set — add for production)
- **Webhooks:** Stripe retries webhooks for up to 3 days with exponential backoff. The payments webhook uses a **Firestore transaction** to prevent double-counting shares.
- **KYC webhook:** Idempotent — setting `kyc_status` to the same value is safe.

---

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `STRIPE_SECRET_KEY` | kyc, payments | Stripe API authentication |
| `STRIPE_WEBHOOK_SECRET` | kyc, payments | Webhook signature verification |
| `GOOGLE_CLOUD_PROJECT` | kyc | Firebase Admin project ID |

---

## Firestore Collections

| Collection | Written By | Key Fields |
|-----------|-----------|------------|
| `users/{uid}` | KYC create_session, KYC webhook | `kyc_status`, `stripe_identity_session_id`, `email` |
| `holdings/{id}` | Payments webhook | `user_id`, `hlt_id`, `shares_owned`, `status` |
| `hlts/{id}` | Payments webhook | `shares_sold` (incremented) |
