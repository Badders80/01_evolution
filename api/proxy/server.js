/**
 * Evolution API Proxy — Cloud Run
 *
 * Sits between Vercel and Cloud Functions.
 * Accepts Firebase ID tokens from the browser for its own auth,
 * then calls Cloud Functions using the website-api@ service account (ADC).
 *
 * Browser → Vercel → Cloud Run (this) → Cloud Functions
 */

const express = require("express");
const { GoogleAuth } = require("google-auth-library");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const PORT = process.env.PORT || 8080;

const CF_BASE = "https://australia-southeast1-evolution-engine.cloudfunctions.net";

// Google Auth client — uses ADC from Cloud Run runtime
const auth = new GoogleAuth();

// CORS Configuration - Restrict to known domains
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "http://localhost:3000,http://localhost:5000,https://evolutionstables.nz,https://evolution.2.0.vercel.app,https://02website-pearl.vercel.app").split(",");

function addCorsHeaders(res, origin) {
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Credentials", "true");
  } else if (origin && origin.includes("localhost")) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Credentials", "true");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Firebase-Token");
}

/**
 * Verify Firebase ID token from the request.
 * Accepts: X-Firebase-Token header or Authorization: Bearer <token>
 */
async function verifyFirebaseToken(req) {
  let idToken = req.headers["x-firebase-token"];
  if (!idToken) {
    const authHeader = req.headers["authorization"] || "";
    if (authHeader.startsWith("Bearer ")) {
      idToken = authHeader.split("Bearer ")[1];
    }
  }
  if (!idToken) return null;

  try {
    const { initializeApp, getApps, cert } = require("firebase-admin/app");
    const { getAuth } = require("firebase-admin/auth");

    if (getApps().length === 0) {
      initializeApp({ projectId: "evolution-engine" });
    }

    const decoded = await getAuth().verifyIdToken(idToken);
    return decoded;
  } catch {
    return null;
  }
}

/**
 * Attach a GCP identity token to every outgoing request.
 */
async function authMiddleware(req, res, next) {
  try {
    // Verify Firebase token for proxy auth
    const user = await verifyFirebaseToken(req);
    if (!user) {
      return res.status(401).json({ error: "Missing or invalid Firebase token" });
    }

    // Get GCP identity token for Cloud Function calls
    const targetAudience = CF_BASE;
    const client = await auth.getIdTokenClient(targetAudience);
    const headers = await client.getRequestHeaders(targetAudience);

    // Forward Firebase user token to Cloud Functions
    const firebaseToken = req.headers["x-firebase-token"] || req.headers["authorization"]?.replace("Bearer ", "");
    if (firebaseToken) {
      headers["X-Firebase-Token"] = firebaseToken;
    }

    req.gcpHeaders = headers;
    next();
  } catch (err) {
    console.error("Auth middleware error:", err);
    res.status(500).json({ error: "Failed to authenticate" });
  }
}

// Proxy /ssot/* → Cloud Functions SSOT
app.use(
  "/ssot",
  (req, res, next) => {
    const origin = req.headers.origin;
    addCorsHeaders(res, origin);
    if (req.method === "OPTIONS") {
      return res.status(200).end();
    }
    next();
  },
  authMiddleware,
  createProxyMiddleware({
    target: `${CF_BASE}/ssot`,
    changeOrigin: true,
    pathRewrite: { "^/ssot": "/" },
    on: {
      proxyReq: (proxyReq, req) => {
        if (req.gcpHeaders) {
          Object.entries(req.gcpHeaders).forEach(([key, val]) => {
            proxyReq.setHeader(key, val);
          });
        }
      },
    },
  })
);

// Proxy /assets/* → Cloud Functions Assets
app.use(
  "/assets",
  (req, res, next) => {
    const origin = req.headers.origin;
    addCorsHeaders(res, origin);
    if (req.method === "OPTIONS") {
      return res.status(200).end();
    }
    next();
  },
  authMiddleware,
  createProxyMiddleware({
    target: `${CF_BASE}/assets`,
    changeOrigin: true,
    pathRewrite: { "^/assets": "/" },
    on: {
      proxyReq: (proxyReq, req) => {
        if (req.gcpHeaders) {
          Object.entries(req.gcpHeaders).forEach(([key, val]) => {
            proxyReq.setHeader(key, val);
          });
        }
      },
    },
  })
);

// Proxy /kyc/* → Cloud Functions KYC
app.use(
  "/kyc",
  (req, res, next) => {
    const origin = req.headers.origin;
    addCorsHeaders(res, origin);
    if (req.method === "OPTIONS") {
      return res.status(200).end();
    }
    next();
  },
  authMiddleware,
  createProxyMiddleware({
    target: `${CF_BASE}/kyc`,
    changeOrigin: true,
    pathRewrite: { "^/kyc": "/" },
    on: {
      proxyReq: (proxyReq, req) => {
        if (req.gcpHeaders) {
          Object.entries(req.gcpHeaders).forEach(([key, val]) => {
            proxyReq.setHeader(key, val);
          });
        }
      },
    },
  })
);

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`Evolution API Proxy running on port ${PORT}`);
});
