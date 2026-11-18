// Run: npm test   (uses Node's built-in test runner; no network, no Google credentials needed)
const test = require("node:test");
const assert = require("node:assert/strict");
const SPEC = require("../../lib/crew-options.json");
const { validateSubmission, buildRow, sheetHeader, safeCell, indyTimestamp, isHoneypotHit } = require("../../lib/crew-validate");
const { makeSheetWriter } = require("../../lib/crew-sheets");
const { createCrewHandler, createRateLimiter } = require("../../api/crew");

function validPayload() {
  return {
    name: "Jordan Lee",
    email: "jordan@example.com",
    based: "Garfield Park",
    roles: ["Camera operator", "Video editor"],
    motivation: "Build my reel or portfolio",
    experience: "Comfortable",
    cameras: ["Mirrorless"],
    multicam: "A few times",
    mixer: "Never, but I am down to learn",
    sync: "Somewhat",
    software: ["Premiere", "Other"],
    own_camera: "Not sure yet",
    produce: "Maybe, tell me more",
    availability: ["Weekend mornings"],
    commitment: "A few sessions",
    needs: ["No, I am good"],
    consent: SPEC.questions.find((q) => q.id === "consent").options[0],
    worth: ["Portfolio footage", "Experience"],
    heard: "Instagram",
  };
}

// Minimal stand-ins for Node's request and response objects.
function fakeReq({ method = "POST", headers = {}, body, ip = "10.0.0.1" } = {}) {
  return { method, headers: { "content-type": "application/json", ...headers }, body, socket: { remoteAddress: ip } };
}
function fakeRes() {
  const res = { statusCode: 200, headers: {}, body: "" };
  res.setHeader = (k, v) => (res.headers[k.toLowerCase()] = v);
  res.end = (chunk) => {
    res.body = chunk === undefined ? res.body : String(chunk);
    res.ended = true;
  };
  return res;
}
function fakeSheets({ headerRow = [] } = {}) {
  const calls = { get: [], update: [], append: [] };
  let header = headerRow;
  return {
    calls,
    spreadsheets: {
      values: {
        get: async (args) => {
          calls.get.push(args);
          return { data: { values: header.length ? [header] : [] } };
        },
        update: async (args) => {
          calls.update.push(args);
          header = args.requestBody.values[0];
        },
        append: async (args) => calls.append.push(args),
      },
    },
  };
}
function silentLog(fn) {
  const original = console.error;
  console.error = () => {};
  return Promise.resolve(fn()).finally(() => (console.error = original));
}

test("accepts a complete valid submission", () => {
  const r = validateSubmission(validPayload());
  assert.equal(r.ok, true);
  assert.deepEqual(r.values.roles, ["Camera operator", "Video editor"]);
});

test("required fields are enforced", () => {
  for (const key of ["name", "email", "roles", "experience", "availability", "consent"]) {
    const p = validPayload();
    delete p[key];
    const r = validateSubmission(p);
    assert.equal(r.ok, false, `${key} should be required`);
    assert.ok(r.fields[key], `${key} should have a field error`);
  }
});

test("optional single-choice fields may be left out", () => {
  const p = validPayload();
  delete p.based;
  delete p.heard;
  assert.equal(validateSubmission(p).ok, true);
});

test("rejects a bad email format", () => {
  const p = validPayload();
  p.email = "not-an-email";
  const r = validateSubmission(p);
  assert.equal(r.ok, false);
  assert.match(r.fields.email, /valid email/);
});

test("rejects any value that is not in the allowed options", () => {
  const p = validPayload();
  p.experience = "Expert wizard";
  p.roles = ["Camera operator", "Drummer"];
  const r = validateSubmission(p);
  assert.equal(r.ok, false);
  assert.ok(r.fields.experience);
  assert.ok(r.fields.roles);
});

test("rejects consent that is not the exact agreed statement", () => {
  const p = validPayload();
  p.consent = "yes";
  assert.equal(validateSubmission(p).ok, false);
});

test("rejects unknown fields", () => {
  const p = validPayload();
  p.notes = "hello";
  const r = validateSubmission(p);
  assert.equal(r.ok, false);
  assert.match(r.general, /do not recognize/);
});

test("a single ticked checkbox sent as a bare string is accepted", () => {
  const p = validPayload();
  p.roles = "Lighting";
  const r = validateSubmission(p);
  assert.equal(r.ok, true);
  assert.deepEqual(r.values.roles, ["Lighting"]);
});

test("caps string length and rejects control characters", () => {
  const long = validPayload();
  long.name = "x".repeat(SPEC.maxTextLength + 1);
  assert.equal(validateSubmission(long).ok, false);

  const ctrl = validPayload();
  ctrl.name = "Jordan\nDROP";
  assert.equal(validateSubmission(ctrl).ok, false);
});

test("formula triggers are neutralised with an apostrophe", () => {
  assert.equal(safeCell('=HYPERLINK("http://evil","x")'), `'=HYPERLINK("http://evil","x")`);
  assert.equal(safeCell("+1+1"), "'+1+1");
  assert.equal(safeCell("-2"), "'-2");
  assert.equal(safeCell("@SUM(A1)"), "'@SUM(A1)");
  assert.equal(safeCell("  =1+1"), "'  =1+1");
  assert.equal(safeCell("Jordan Lee"), "Jordan Lee");
});

test("buildRow matches the header order and joins checkboxes with '; '", () => {
  const { values } = validateSubmission(validPayload());
  const row = buildRow(values, new Date("2026-11-17T19:03:22Z"));
  assert.equal(row.length, sheetHeader().length);
  assert.equal(row[0], "2026-11-17T14:03:22-05:00");
  assert.equal(row[sheetHeader().indexOf("Which roles are you interested in?")], "Camera operator; Video editor");
  assert.equal(row[sheetHeader().indexOf("Name")], "Jordan Lee");
});

test("timestamps use Indiana time with the right offset in summer and winter", () => {
  assert.equal(indyTimestamp(new Date("2026-01-15T12:00:00Z")), "2026-01-15T07:00:00-05:00");
  assert.equal(indyTimestamp(new Date("2026-07-15T12:00:00Z")), "2026-07-15T08:00:00-04:00");
});

test("honeypot detection", () => {
  assert.equal(isHoneypotHit({ company_website: "http://spam" }), true);
  assert.equal(isHoneypotHit({ company_website: "" }), false);
  assert.equal(isHoneypotHit({}), false);
});

test("sheet writer creates the header on first write when row 1 is empty", async () => {
  const sheets = fakeSheets({ headerRow: [] });
  const writer = makeSheetWriter({ sheets, spreadsheetId: "sheet1", tab: "Responses" });
  await writer.appendRow(["a"]);
  assert.equal(sheets.calls.update.length, 1);
  assert.deepEqual(sheets.calls.update[0].requestBody.values[0], sheetHeader());
  assert.equal(sheets.calls.append[0].valueInputOption, "USER_ENTERED");
  assert.equal(sheets.calls.append[0].range, "Responses!A:A");
});

test("sheet writer leaves an existing header alone", async () => {
  const sheets = fakeSheets({ headerRow: sheetHeader() });
  const writer = makeSheetWriter({ sheets, spreadsheetId: "sheet1", tab: "Responses" });
  await writer.appendRow(["a"]);
  await writer.appendRow(["b"]);
  assert.equal(sheets.calls.update.length, 0);
  assert.equal(sheets.calls.append.length, 2);
});

test("handler: valid JSON submission appends one row and returns ok", async () => {
  const rows = [];
  const handler = createCrewHandler({ writeRow: async (row) => rows.push(row) });
  const res = fakeRes();
  await handler(fakeReq({ body: validPayload() }), res);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(JSON.parse(res.body), { ok: true });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].length, sheetHeader().length);
});

test("handler: honeypot hit returns a generic success and writes nothing", async () => {
  const rows = [];
  const handler = createCrewHandler({ writeRow: async (row) => rows.push(row) });
  const res = fakeRes();
  await handler(fakeReq({ body: { ...validPayload(), company_website: "http://bot" } }), res);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(JSON.parse(res.body), { ok: true });
  assert.equal(rows.length, 0);
});

test("handler: invalid submission returns 400 with field errors and writes nothing", async () => {
  const rows = [];
  const handler = createCrewHandler({ writeRow: async (row) => rows.push(row) });
  const res = fakeRes();
  const p = validPayload();
  p.email = "bad";
  await handler(fakeReq({ body: p }), res);
  const body = JSON.parse(res.body);
  assert.equal(res.statusCode, 400);
  assert.equal(body.ok, false);
  assert.ok(body.fields.email);
  assert.equal(rows.length, 0);
});

test("handler: sheet failure returns a generic 503 with no credential or stack detail", async () => {
  const handler = createCrewHandler({
    writeRow: async () => {
      throw Object.assign(new Error("PERMISSION_DENIED for service-account@x.iam.gserviceaccount.com key=-----BEGIN PRIVATE KEY"), { code: 403 });
    },
  });
  const res = await silentLog(async () => {
    const r = fakeRes();
    await handler(fakeReq({ body: validPayload() }), r);
    return r;
  });
  assert.equal(res.statusCode, 503);
  assert.ok(!res.body.includes("PRIVATE KEY"));
  assert.ok(!res.body.includes("iam.gserviceaccount"));
  assert.ok(!res.body.includes("at "));
});

test("handler: form-encoded POST parses repeated keys and bare single values", async () => {
  const rows = [];
  const handler = createCrewHandler({ writeRow: async (row) => rows.push(row) });
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(validPayload())) {
    if (Array.isArray(v)) v.forEach((item) => params.append(k, item));
    else params.append(k, v);
  }
  const res = fakeRes();
  await handler(fakeReq({ headers: { "content-type": "application/x-www-form-urlencoded" }, body: params.toString() }), res);
  assert.equal(res.statusCode, 200);
  assert.equal(rows.length, 1);
});

test("handler: plain HTML form POST redirects to the thank-you state", async () => {
  const handler = createCrewHandler({ writeRow: async () => {} });
  const res = fakeRes();
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(validPayload())) {
    if (Array.isArray(v)) v.forEach((item) => params.append(k, item));
    else params.append(k, v);
  }
  await handler(fakeReq({ headers: { accept: "text/html", "content-type": "application/x-www-form-urlencoded" }, body: params.toString() }), res);
  assert.equal(res.statusCode, 303);
  assert.equal(res.headers.location, "/crew/?sent=1");
});

test("handler: rejects GET with 405", async () => {
  const handler = createCrewHandler({ writeRow: async () => {} });
  const res = fakeRes();
  await handler(fakeReq({ method: "GET" }), res);
  assert.equal(res.statusCode, 405);
});

test("handler: rate limits a single IP after the allowance", async () => {
  let t = 0;
  const limiter = createRateLimiter({ windowMs: 60000, max: 2, now: () => t });
  const handler = createCrewHandler({ writeRow: async () => {}, rateLimiter: limiter });
  const statuses = [];
  for (let i = 0; i < 3; i++) {
    const res = fakeRes();
    await handler(fakeReq({ body: validPayload(), ip: "1.2.3.4" }), res);
    statuses.push(res.statusCode);
  }
  assert.deepEqual(statuses, [200, 200, 429]);
  t = 61000; // window passes
  const res = fakeRes();
  await handler(fakeReq({ body: validPayload(), ip: "1.2.3.4" }), res);
  assert.equal(res.statusCode, 200);
});
