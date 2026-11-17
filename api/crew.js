// POST /api/crew: validates a crew interest form submission and appends one row to a Google Sheet.
// Works with a plain HTML form POST (303 back to /crew/?sent=1) and with fetch (JSON in, JSON out).
// Credentials come only from environment variables; nothing sensitive is logged or returned.

const { validateSubmission, isHoneypotHit, buildRow } = require("../lib/crew-validate");
const { makeSheetWriter, readSheetsEnv, makeSheetsClientFromEnv } = require("../lib/crew-sheets");

const RATE_WINDOW_MS = 10 * 60 * 1000; // 10 minutes
const RATE_MAX_HITS = 5; // submissions per IP per window
const MAX_RAW_BODY = 20000; // characters

// Per-instance, in-memory limiter. Vercel may run several instances, so this is a speed bump,
// not a hard limit. The honeypot and the field validation do the rest.
function createRateLimiter({ windowMs = RATE_WINDOW_MS, max = RATE_MAX_HITS, now = Date.now } = {}) {
  const hits = new Map();
  return {
    allow(ip) {
      const t = now();
      const recent = (hits.get(ip) || []).filter((ts) => t - ts < windowMs);
      if (recent.length >= max) {
        hits.set(ip, recent);
        return false;
      }
      recent.push(t);
      hits.set(ip, recent);
      if (hits.size > 5000) {
        for (const [key, list] of hits) if (!list.length || t - list[list.length - 1] >= windowMs) hits.delete(key);
      }
      return true;
    },
  };
}

function clientIp(req) {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string" && forwarded) return forwarded.split(",")[0].trim();
  return (req.socket && req.socket.remoteAddress) || "unknown";
}

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_RAW_BODY) {
        reject(new Error("too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

// Turns the request into a plain object of strings or string arrays. Vercel usually parses the
// body already; the raw fallback handles JSON and form-encoded bodies the same way.
async function parseBody(req) {
  let body = req.body;
  if (body === undefined) body = await readRawBody(req);
  if (body && typeof body === "object" && !Buffer.isBuffer(body)) return body;
  if (typeof body !== "string") return null;
  if (body.length > MAX_RAW_BODY) throw new Error("too large");

  const type = String(req.headers["content-type"] || "");
  if (type.includes("application/json")) return JSON.parse(body);

  const params = new URLSearchParams(body);
  const out = Object.create(null);
  for (const key of new Set(params.keys())) {
    const all = params.getAll(key);
    out[key] = all.length === 1 ? all[0] : all;
  }
  return out;
}

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.end(JSON.stringify(payload));
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Plain-HTML response for a form POST made without JavaScript.
function sendHtmlError(res, status, messages) {
  res.statusCode = status;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Content-Type-Options", "nosniff");
  const items = messages.map((m) => `<li>${escapeHtml(m)}</li>`).join("");
  res.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Could not send</title></head>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.5"><h1>We could not send that</h1><ul>${items}</ul><p><a href="/crew/">Go back to the form</a></p></body></html>`);
}

function wantsHtml(req) {
  const accept = String(req.headers.accept || "");
  return accept.includes("text/html") && !accept.includes("application/json");
}

function createCrewHandler({ writeRow, rateLimiter = createRateLimiter(), now = () => new Date() }) {
  return async function crewHandler(req, res) {
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      return sendJson(res, 405, { ok: false, error: "Method not allowed." });
    }
    const html = wantsHtml(req);

    if (!rateLimiter.allow(clientIp(req))) {
      if (html) return sendHtmlError(res, 429, ["Too many submissions from this connection. Please try again in a few minutes."]);
      return sendJson(res, 429, { ok: false, error: "Too many submissions. Please try again in a few minutes." });
    }

    let body;
    try {
      body = await parseBody(req);
    } catch (err) {
      const message = "We could not read the form. Please reload and try again.";
      if (html) return sendHtmlError(res, 400, [message]);
      return sendJson(res, 400, { ok: false, error: message });
    }

    // A bot filled the hidden field: pretend it worked, store nothing.
    if (isHoneypotHit(body)) {
      if (html) {
        res.statusCode = 303;
        res.setHeader("Location", "/crew/?sent=1");
        return res.end();
      }
      return sendJson(res, 200, { ok: true });
    }

    const result = validateSubmission(body);
    if (!result.ok) {
      if (html) return sendHtmlError(res, 400, [result.general, ...Object.values(result.fields)]);
      return sendJson(res, 400, { ok: false, error: result.general, fields: result.fields });
    }

    try {
      await writeRow(buildRow(result.values, now()));
    } catch (err) {
      // Log the error type and a short message only: never the credentials or the full stack.
      console.error("crew: sheet write failed", err && err.code, String((err && err.message) || "").slice(0, 200));
      const message = "We could not save your response. Please try again in a few minutes.";
      if (html) return sendHtmlError(res, 503, [message]);
      return sendJson(res, 503, { ok: false, error: message });
    }

    if (html) {
      res.statusCode = 303;
      res.setHeader("Location", "/crew/?sent=1");
      return res.end();
    }
    return sendJson(res, 200, { ok: true });
  };
}

// Production wiring: the Sheets client is created on first use and reused by warm instances.
let sheetWriter = null;
async function writeRowToSheet(row) {
  if (!sheetWriter) {
    const config = readSheetsEnv(process.env);
    if (!config) throw Object.assign(new Error("Sheet environment variables are not set"), { code: "CONFIG" });
    sheetWriter = makeSheetWriter({
      sheets: makeSheetsClientFromEnv(config),
      spreadsheetId: config.spreadsheetId,
      tab: config.tab,
    });
  }
  return sheetWriter.appendRow(row);
}

module.exports = createCrewHandler({ writeRow: writeRowToSheet });
module.exports.createCrewHandler = createCrewHandler;
module.exports.createRateLimiter = createRateLimiter;
