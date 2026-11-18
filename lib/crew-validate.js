// Server-side validation and sheet-row building for the /crew form.
// Pure functions only (no network, no env), so tests can run them directly.
// The field list and every allowed option come from lib/crew-options.json.

const SPEC = require("./crew-options.json");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ZIP_RE = /^\d{5}$/;
// Characters that must never appear in a single-line field (control chars, incl. CR/LF/tab).
const CONTROL_RE = /[\u0000-\u001F\u007F]/;
// Spreadsheet formula triggers. A leading tab/CR can also hide a formula, so they count as well.
const FORMULA_START_RE = /^[\s]*[=+\-@]/;
const INDY_TZ = "America/Indiana/Indianapolis";

const QUESTIONS = SPEC.questions;

function fieldError(fields, id, message) {
  fields[id] = message;
}

// Returns { ok: true, values } or { ok: false, fields, general }.
// `values` maps question id -> string (single) or string[] (checkbox), already normalized.
function validateSubmission(body) {
  const fields = {};
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { ok: false, fields, general: "Please submit the form again." };
  }

  const known = new Set(QUESTIONS.map((q) => q.id));
  known.add(SPEC.honeypot);
  for (const key of Object.keys(body)) {
    if (!known.has(key)) return { ok: false, fields, general: "The form contains a field we do not recognize. Please reload and try again." };
  }

  const values = {};
  for (const q of QUESTIONS) {
    const raw = body[q.id];

    if (q.type === "text" || q.type === "email" || q.type === "zip") {
      if (raw !== undefined && typeof raw !== "string") {
        fieldError(fields, q.id, "Please enter text.");
        continue;
      }
      const value = (raw || "").trim();
      if (!value) {
        if (q.required) fieldError(fields, q.id, "This field is required.");
        values[q.id] = "";
        continue;
      }
      const max = q.type === "email" ? SPEC.maxEmailLength : SPEC.maxTextLength;
      if (value.length > max) {
        fieldError(fields, q.id, `Please keep this under ${max} characters.`);
        continue;
      }
      if (CONTROL_RE.test(value)) {
        fieldError(fields, q.id, "Please remove unusual characters.");
        continue;
      }
      if (q.type === "email" && !EMAIL_RE.test(value)) {
        fieldError(fields, q.id, "Please enter a valid email address.");
        continue;
      }
      if (q.type === "zip" && !ZIP_RE.test(value)) {
        fieldError(fields, q.id, "Please enter a 5-digit zip code.");
        continue;
      }
      values[q.id] = value;
      continue;
    }

    if (q.type === "checkbox") {
      // Form-encoded bodies give a bare string when only one box is ticked.
      const list = raw === undefined ? [] : Array.isArray(raw) ? raw : [raw];
      if (list.some((v) => typeof v !== "string")) {
        fieldError(fields, q.id, "Please choose from the listed options.");
        continue;
      }
      const unique = [...new Set(list)];
      if (unique.some((v) => !q.options.includes(v))) {
        fieldError(fields, q.id, "Please choose from the listed options.");
        continue;
      }
      if (q.required && unique.length === 0) {
        fieldError(fields, q.id, "Please choose at least one option.");
        continue;
      }
      // Keep the order the form shows the options in, not the order they were posted in.
      values[q.id] = q.options.filter((o) => unique.includes(o));
      continue;
    }

    // radio and consent: one option (or nothing, when optional).
    if (raw !== undefined && typeof raw !== "string") {
      fieldError(fields, q.id, "Please choose one of the listed options.");
      continue;
    }
    const value = raw || "";
    if (!value) {
      if (q.required) fieldError(fields, q.id, q.type === "consent" ? "You must agree to continue." : "Please choose an option.");
      values[q.id] = "";
      continue;
    }
    if (!q.options.includes(value)) {
      fieldError(fields, q.id, "Please choose one of the listed options.");
      continue;
    }
    values[q.id] = value;
  }

  if (Object.keys(fields).length > 0) {
    return { ok: false, fields, general: "Please fix the highlighted fields and try again." };
  }
  return { ok: true, values };
}

// True when the submission was a honeypot hit (a bot filled the hidden field).
function isHoneypotHit(body) {
  return !!body && typeof body === "object" && typeof body[SPEC.honeypot] === "string" && body[SPEC.honeypot].trim() !== "";
}

// Stops spreadsheet formula injection: any cell starting with = + - @ gets a leading apostrophe.
function safeCell(value) {
  const text = String(value);
  return FORMULA_START_RE.test(text) ? "'" + text : text;
}

// ISO 8601 timestamp in Indiana time, e.g. 2026-11-17T14:03:22-05:00.
function indyTimestamp(date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: INDY_TZ, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(date);
  const get = (type) => parts.find((p) => p.type === type).value;
  const offsetPart = new Intl.DateTimeFormat("en-US", { timeZone: INDY_TZ, timeZoneName: "longOffset" })
    .formatToParts(date).find((p) => p.type === "timeZoneName").value; // e.g. "GMT-05:00" or "GMT"
  const offset = offsetPart === "GMT" ? "+00:00" : offsetPart.replace("GMT", "");
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}:${get("second")}${offset}`;
}

// Header row, in order: Timestamp, then one column per question.
function sheetHeader() {
  return ["Timestamp", ...QUESTIONS.map((q) => q.column)];
}

// One data row, in the same order as sheetHeader(). Checkbox answers join with "; ".
function buildRow(values, now = new Date()) {
  const cells = [indyTimestamp(now)];
  for (const q of QUESTIONS) {
    const v = values[q.id];
    cells.push(Array.isArray(v) ? v.join("; ") : v || "");
  }
  return cells.map(safeCell);
}

module.exports = {
  QUESTIONS,
  validateSubmission,
  isHoneypotHit,
  safeCell,
  indyTimestamp,
  sheetHeader,
  buildRow,
};
