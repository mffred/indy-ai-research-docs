// Gates /indy-pulse behind Google sign-in, limited to one Gmail address.
// Runs on Vercel before the static file is served, so the page is never sent to a signed-out visitor.
//
// Env vars (set in the Vercel dashboard or with `vercel env add`; never commit them):
//   INDY_PULSE_GOOGLE_CLIENT_ID, INDY_PULSE_GOOGLE_CLIENT_SECRET  - Google OAuth web client
//   INDY_PULSE_ALLOWED_EMAIL  - the one Google account allowed in
//   INDY_PULSE_SESSION_SECRET - random string used to sign the session cookie
// If any are missing, nobody can sign in (fails closed).

const BASE = "/indy-pulse";
const SESSION_COOKIE = "indy_pulse_session";
const STATE_COOKIE = "indy_pulse_oauth_state";
const SESSION_SECONDS = 60 * 60 * 12;
const enc = new TextEncoder();

export const config = { matcher: ["/indy-pulse/:path*"] };

export default async function middleware(request) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "");

  if (path === `${BASE}/auth/login`) return startLogin(url);
  if (path === `${BASE}/auth/callback`) return finishLogin(request, url);
  if (path === `${BASE}/auth/logout`) return logout();

  if (await isSignedIn(request)) return; // continue to the static page
  return loginPage(401);
}

async function startLogin(url) {
  const clientId = process.env.INDY_PULSE_GOOGLE_CLIENT_ID;
  if (!clientId || !process.env.INDY_PULSE_ALLOWED_EMAIL) return loginPage(503);

  const state = randomHex(32);
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: `${url.origin}${BASE}/auth/callback`,
    response_type: "code",
    scope: "openid email",
    state,
    prompt: "select_account",
  });
  return new Response(null, {
    status: 302,
    headers: {
      location: `https://accounts.google.com/o/oauth2/v2/auth?${params}`,
      "set-cookie": cookie(STATE_COOKIE, state, 600, `${BASE}/auth`),
      "cache-control": "private, no-store",
    },
  });
}

async function finishLogin(request, url) {
  const clientId = process.env.INDY_PULSE_GOOGLE_CLIENT_ID;
  const clientSecret = process.env.INDY_PULSE_GOOGLE_CLIENT_SECRET;
  const allowed = (process.env.INDY_PULSE_ALLOWED_EMAIL || "").toLowerCase();
  if (!clientId || !clientSecret || !allowed) return loginPage(503);

  const state = url.searchParams.get("state");
  const expected = readCookie(request, STATE_COOKIE);
  if (!state || !expected || state !== expected) return message(400, "Sign-in expired. Please try again.");
  if (url.searchParams.get("error")) return message(403, "Google sign-in was cancelled.");

  const code = url.searchParams.get("code");
  if (!code) return message(400, "Missing sign-in code.");

  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: `${url.origin}${BASE}/auth/callback`,
      grant_type: "authorization_code",
    }),
  });
  if (!tokenRes.ok) return message(502, "Could not verify the Google sign-in. Please try again.");
  const { id_token } = await tokenRes.json();

  // The id_token came straight from Google's token endpoint over TLS, so reading its claims here is enough.
  const claims = decodeJwtPayload(id_token);
  const email = String(claims?.email || "").toLowerCase();
  const issuerOk = claims?.iss === "https://accounts.google.com" || claims?.iss === "accounts.google.com";
  if (!issuerOk || claims?.aud !== clientId || claims?.email_verified !== true) {
    return message(403, "This Google account could not be verified.");
  }
  if (email !== allowed) {
    return message(403, "This Google account is not allowed to view this page.");
  }

  const token = await createSession(email);
  const headers = new Headers({ location: `${BASE}/`, "cache-control": "private, no-store" });
  headers.append("set-cookie", cookie(SESSION_COOKIE, token, SESSION_SECONDS, BASE));
  headers.append("set-cookie", cookie(STATE_COOKIE, "", 0, `${BASE}/auth`));
  return new Response(null, { status: 302, headers });
}

function logout() {
  const headers = new Headers({ location: `${BASE}/`, "cache-control": "private, no-store" });
  headers.append("set-cookie", cookie(SESSION_COOKIE, "", 0, BASE));
  return new Response(null, { status: 302, headers });
}

async function isSignedIn(request) {
  const token = readCookie(request, SESSION_COOKIE);
  if (!token) return false;
  const [payload, sig] = token.split(".");
  const secret = process.env.INDY_PULSE_SESSION_SECRET;
  const allowed = (process.env.INDY_PULSE_ALLOWED_EMAIL || "").toLowerCase();
  if (!payload || !sig || !secret || !allowed) return false;

  try {
    const key = await hmacKey(secret);
    const valid = await crypto.subtle.verify("HMAC", key, fromB64url(sig), enc.encode(payload));
    if (!valid) return false;

    const data = JSON.parse(new TextDecoder().decode(fromB64url(payload)));
    return data.e === allowed && data.x > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

async function createSession(email) {
  const exp = Math.floor(Date.now() / 1000) + SESSION_SECONDS;
  const payload = b64url(enc.encode(JSON.stringify({ e: email, x: exp })));
  const key = await hmacKey(process.env.INDY_PULSE_SESSION_SECRET);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  return `${payload}.${b64url(sig)}`;
}

function hmacKey(secret) {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

function readCookie(request, name) {
  const header = request.headers.get("cookie") || "";
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return null;
}

function cookie(name, value, maxAge, path) {
  return `${name}=${value}; Path=${path}; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Lax`;
}

function decodeJwtPayload(jwt) {
  try {
    return JSON.parse(new TextDecoder().decode(fromB64url(jwt.split(".")[1])));
  } catch {
    return null;
  }
}

function randomHex(bytes) {
  return [...crypto.getRandomValues(new Uint8Array(bytes))].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function b64url(buffer) {
  let binary = "";
  for (const byte of new Uint8Array(buffer)) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromB64url(text) {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(text.length / 4) * 4, "=");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

function page(status, title, body) {
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>${title}</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; box-sizing: border-box;
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; background: #f6f5f1; color: #1d1d1b; }
  main { max-width: 380px; width: 100%; background: #fff; border: 1px solid #d8d5cc; border-radius: 10px; padding: 28px 24px; text-align: center; }
  h1 { font-size: 22px; margin: 0 0 10px; }
  p { margin: 0 0 20px; color: #4a4a45; }
  a.button { display: inline-block; padding: 11px 18px; border-radius: 6px; background: #1d1d1b; color: #fff; text-decoration: none; font-weight: 600; }
</style>
</head>
<body>
<main>${body}</main>
</body>
</html>`;
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "private, no-store",
      "x-robots-tag": "noindex, nofollow",
    },
  });
}

function loginPage(status) {
  const body =
    status === 503
      ? `<h1>Sign-in not set up</h1><p>This page is not configured for sign-in yet.</p>`
      : `<h1>Indy Public Safety Pulse</h1><p>This page is limited to an authorized account. Sign in with Google to continue.</p><a class="button" href="${BASE}/auth/login">Sign in with Google</a>`;
  return page(status, "Sign in", body);
}

function message(status, text) {
  return page(status, "Sign in", `<h1>Sign-in failed</h1><p>${text}</p><a class="button" href="${BASE}/auth/login">Try again</a>`);
}
