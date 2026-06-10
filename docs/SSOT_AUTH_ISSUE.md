# SSOT API Authentication Issue

**Date:** June 10, 2026  
**Status:** BLOCKED - Auth not working for local development

## Problem

Cloud Functions invoker authentication requires either:
1. **ID token (JWT)** with function URL as audience - requires service account
2. **Unauthenticated function** - blocked by org policy

Current setup:
- ✅ IAM bindings added: `evolution-engine@appspot.gserviceaccount.com` + `alex@evolutionstables.nz` have `roles/cloudfunctions.invoker`
- ✅ Function security level: `SECURE_OPTIONAL`
- ❌ Can't get ID token locally (requires service account)
- ❌ Can't create service account keys (blocked by org policy: `constraints/iam.disableServiceAccountKeyCreation`)
- ❌ Can't impersonate service account (missing `roles/iam.serviceAccountTokenCreator`)
- ❌ Can't make function unauthenticated (blocked by org policy)

## What We Tried

1. ✅ Added IAM policy binding for service account
2. ✅ Added IAM policy binding for user account
3. ❌ Access tokens from user account → 401 Unauthorized
4. ❌ ID token generation → requires service account
5. ❌ Service account key creation → blocked by org policy
6. ❌ Service account impersonation → missing permissions
7. ❌ Making function unauthenticated → blocked by org policy
8. ❌ Deploying function update → wrong source directory

## Current Code State

Updated `trigger_imap.py` to use proper auth headers:
- `get_auth_headers(target_audience=URL)` - tries ID token first, falls back to access token
- Updated `resolve_horse_microchip()` to pass target audience
- Updated `upload_to_assets_api()` to pass auth headers
- Updated `store_content_api()` to pass auth headers

But auth still fails locally because we can't get a valid token.

## Workarounds

### Option 1: Deploy trigger_imap.py as Cloud Function (RECOMMENDED)
Deploy the email ingest pipeline as a Cloud Function that runs with the `evolution-engine` service account identity. Then it can call SSOT/Assets APIs with proper auth.

```bash
# Deploy from api/email-ingest directory
gcloud functions deploy email-ingest \
  --region=australia-southeast1 \
  --runtime=python312 \
  --entry-point=trigger_email \
  --source=. \
  --service-account=evolution-engine@appspot.gserviceaccount.com
```

### Option 2: Manual Firestore Insertion
Write a script that directly inserts documents into Firestore using the service account (if we can get ADC working for Firestore only).

### Option 3: Run with Local Fallbacks (TEMPORARY)
Run `trigger_imap.py` as-is. It will:
- ✅ Download videos
- ✅ Transcribe with quota-tracked engine
- ✅ Save transcripts to local `output/` directory
- ❌ NOT sync to Firestore (uses mock IDs)
- ❌ NOT register assets in Assets API

This completes the pipeline logic but doesn't persist to production databases.

### Option 4: Fix ADC Impersonation
Grant `alex@evolutionstables.nz` the `roles/iam.serviceAccountTokenCreator` role on the `evolution-engine` service account. Then:

```bash
gcloud auth application-default login --impersonate-service-account=evolution-engine@appspot.gserviceaccount.com
```

This would allow local development with proper auth.

## Next Steps

**For Sprint One completion:**
- Run `python trigger_imap.py` with local fallbacks
- Document that transcripts are in `output/` directory
- Mark as "Firestore sync pending auth fix"

**For production:**
- Implement Option 1 (deploy as Cloud Function) OR
- Implement Option 4 (fix ADC impersonation)

## Files Modified

- `/home/evo/evo_01/01_evolution/api/email-ingest/trigger_imap.py`
  - Updated `get_auth_headers()` to support ID tokens
  - Updated all API callers to pass `target_audience`

## Test Commands

```bash
# Test if auth works (currently fails)
cd /home/evo/evo_01/01_evolution/api/email-ingest
python trigger_imap.py

# Expected: 401 errors on SSOT/Assets API calls
# Fallback: local mock IDs and file output
```
