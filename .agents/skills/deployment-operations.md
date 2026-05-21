# Evolution — Deployment & Operations Skill

**Purpose:** Deploy and manage Evolution Stables infrastructure on GCP.

**When to use:**
- Deploying Cloud Functions
- Managing Firestore
- Managing Cloud Storage buckets
- Setting up environment variables
- Troubleshooting deployment issues

---

## Prerequisites

### GCP Setup

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project evolution-engine

# Enable required APIs
gcloud services enable firestore.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

### Environment Variables

**Location:** `api/.env` (development), GCP Secret Manager (production)

```bash
# GCP
GCP_PROJECT=evolution-engine
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Firebase
NEXT_PUBLIC_FIREBASE_CONFIG='{"projectId":"evolution-engine",...}'

# Stripe (for KYC)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

---

## Firestore

### Create Database

```bash
gcloud firestore databases create \
  --region australia-southeast1 \
  --type FIRESTORE_NATIVE
```

### Security Rules

**Location:** `firestore.rules`

```rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Public read for horses
    match /horses/{microchip} {
      allow read: if true
      allow write: if request.auth != null && request.auth.token.admin == true
    }
    
    // Admin only for owners, trainers, HLTs
    match /owners/{id} {
      allow read, write: if request.auth != null && request.auth.token.admin == true
    }
    
    match /hlts/{id} {
      allow read, write: if request.auth != null && request.auth.token.admin == true
    }
    
    // Assets metadata
    match /assets/{id} {
      allow read: if true
      allow write: if request.auth != null && request.auth.token.admin == true
    }
  }
}
```

**Deploy:**
```bash
gcloud firestore deploy rules firestore.rules
```

---

## Cloud Storage

### Create Buckets

```bash
# Images bucket
gsutil mb -p evolution-engine -l australia-southeast1 gs://evolution-horse-images

# Documents bucket
gsutil mb -p evolution-engine -l australia-southeast1 gs://evolution-horse-docs
```

### Set CORS (for browser uploads)

**Location:** `cors.json`

```json
[
  {
    "origin": ["*"],
    "method": ["GET", "POST", "PUT", "DELETE"],
    "maxAgeSeconds": 3600
  }
]
```

**Apply:**
```bash
gsutil cors set cors.json gs://evolution-horse-images
gsutil cors set cors.json gs://evolution-horse-docs
```

---

## Cloud Functions

### Deploy SSOT API

```bash
cd api/ssot

gcloud functions deploy ssot \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point ssot \
  --region australia-southeast1 \
  --memory 512MB \
  --timeout 60s \
  --set-env-vars GCP_PROJECT=evolution-engine
```

### Deploy Assets API

```bash
cd api/assets

gcloud functions deploy assets \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point assets \
  --region australia-southeast1 \
  --memory 512MB \
  --timeout 60s \
  --set-env-vars GCP_PROJECT=evolution-engine,GCS_BUCKET=evolution-horse-images
```

### Deploy KYC API

```bash
cd api/kyc

gcloud functions deploy kyc \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point kyc \
  --region australia-southeast1 \
  --memory 512MB \
  --timeout 60s \
  --set-env-vars GCP_PROJECT=evolution-engine,STRIPE_SECRET_KEY=sk_test_...
```

### View Logs

```bash
gcloud functions logs read ssot --region australia-southeast1 --limit 50
gcloud functions logs read assets --region australia-southeast1 --limit 50
gcloud functions logs read kyc --region australia-southeast1 --limit 50
```

### Update Environment Variables

```bash
gcloud functions deploy ssot \
  --region australia-southeast1 \
  --update-env-vars KEY1=value1,KEY2=value2
```

---

## Next.js Deployment

### Option 1: Vercel (Recommended)

```bash
cd app

# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

**Environment Variables in Vercel:**
- `NEXT_PUBLIC_API_URL` — SSOT API URL
- `NEXT_PUBLIC_FIREBASE_CONFIG` — Firebase config JSON
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` — Stripe key

### Option 2: Firebase Hosting

```bash
cd app

# Build
npm run build

# Deploy
firebase deploy --only hosting
```

---

## Stripe Webhook

### Configure Webhook

**Dashboard:** https://dashboard.stripe.com/test/webhooks

**Endpoint:** `https://REGION-evolution-engine.cloudfunctions.net/kyc/webhook`

**Events to listen for:**
- `identity.verification_session.created`
- `identity.verification_session.verified`
- `identity.verification_session.failed`

### Test Webhook Locally

```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8082/webhook
```

---

## Monitoring

### Cloud Function Metrics

```bash
gcloud monitoring metrics-descriptors list --filter="cloudfunctions.googleapis.com"
```

### Error Tracking

**Check logs for:**
- 400 errors — Validation failures (check client requests)
- 404 errors — Missing resources (check microchip/ID)
- 500 errors — Server errors (check Cloud Function logs)

### Performance

**Target metrics:**
- Cold start: < 2s
- API response: < 500ms
- Firestore query: < 100ms

---

## Backup & Recovery

### Export Firestore

```bash
gcloud firestore export gs://evolution-backups/firestore/$(date +%Y%m%d)
```

### Import Firestore

```bash
gcloud firestore import gs://evolution-backups/firestore/20260519
```

### Backup Schedule

**Recommended:** Daily exports via Cloud Scheduler

---

## Common Pitfalls

❌ **Never deploy without testing locally first** — Always run `just test-api`  
❌ **Never skip environment variables** — Check all required vars before deploy  
❌ **Never use production data in development** — Use separate projects  
❌ **Never ignore CORS errors** — Configure buckets for browser access  
❌ **Never forget Firestore security rules** — Deploy rules with code  

---

## Troubleshooting

### Function Won't Deploy

```bash
# Check permissions
gcloud projects get-iam-policy evolution-engine

# Check APIs enabled
gcloud services list --enabled

# Check logs
gcloud functions logs read ssot --region australia-southeast1
```

### Firestore Permission Denied

```bash
# Check service account has Firestore role
gcloud projects add-iam-policy-binding evolution-engine \
  --member=serviceAccount:evolution-engine@appspot.gserviceaccount.com \
  --role=roles/datastore.user
```

### CORS Errors

```bash
# Verify CORS config
gsutil cors get gs://evolution-horse-images

# Re-apply if needed
gsutil cors set cors.json gs://evolution-horse-images
```

---

## Related Files

- **Deploy scripts:** `api/ssot/main.py`, `api/assets/main.py`, `api/kyc/main.py`
- **Environment:** `api/.env`, `app/.env.local`
- **Rules:** `firestore.rules`, `storage.rules`
- **Config:** `app/next.config.ts`, `api/env.yaml`

---

## Quick Reference

```bash
# Deploy all functions
just deploy-all  # (create this in Justfile)

# Check function status
gcloud functions describe ssot --region australia-southeast1

# Test endpoint
curl https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot/horses

# View real-time logs
gcloud functions logs read ssot --region australia-southeast1 --follow
```
