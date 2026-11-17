// Appends crew-form rows to a Google Sheet through the Sheets v4 API.
// `sheets` is a googleapis `sheets` client (or a test double with the same shape).
// The googleapis package is only loaded by makeSheetsClientFromEnv(), so tests never need it.

const { sheetHeader } = require("./crew-validate");

function makeSheetWriter({ sheets, spreadsheetId, tab }) {
  const headerRange = `${tab}!1:1`;
  let headerChecked = false;

  // Writes the header row if row 1 is empty. Runs once per warm instance.
  async function ensureHeader() {
    if (headerChecked) return;
    const res = await sheets.spreadsheets.values.get({ spreadsheetId, range: headerRange });
    const firstRow = (res.data && res.data.values && res.data.values[0]) || [];
    if (firstRow.length === 0) {
      await sheets.spreadsheets.values.update({
        spreadsheetId,
        range: `${tab}!A1`,
        valueInputOption: "RAW",
        requestBody: { values: [sheetHeader()] },
      });
    }
    headerChecked = true;
  }

  // USER_ENTERED so a leading apostrophe marks text instead of being stored as a literal character.
  async function appendRow(row) {
    await ensureHeader();
    await sheets.spreadsheets.values.append({
      spreadsheetId,
      range: `${tab}!A:A`,
      valueInputOption: "USER_ENTERED",
      insertDataOption: "INSERT_ROWS",
      requestBody: { values: [row] },
    });
  }

  return { appendRow, _ensureHeader: ensureHeader };
}

// Reads credentials from the environment. The private key arrives with literal "\n" sequences
// in most hosts' dashboards, so those are turned back into real newlines.
function readSheetsEnv(env) {
  const email = env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
  const key = env.GOOGLE_PRIVATE_KEY;
  const spreadsheetId = env.GOOGLE_SHEET_ID;
  const tab = env.GOOGLE_SHEET_TAB || "Responses";
  if (!email || !key || !spreadsheetId) return null;
  return { email, key: key.replace(/\\n/g, "\n"), spreadsheetId, tab };
}

function makeSheetsClientFromEnv(config) {
  // Loaded here, not at the top, so the rest of this file and the tests do not need googleapis.
  const { google } = require("googleapis");
  const auth = new google.auth.JWT({
    email: config.email,
    key: config.key,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });
  return google.sheets({ version: "v4", auth });
}

module.exports = { makeSheetWriter, readSheetsEnv, makeSheetsClientFromEnv };
