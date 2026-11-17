# Crew form setup (/crew)

The form at `/crew` posts to `/api/crew`, which appends one row per submission to a Google Sheet. Do these steps once. Nothing here goes in the repo.

## 1. Create the Sheet

1. Go to sheets.google.com and create a blank spreadsheet, e.g. "Crew interest responses".
2. Rename the first tab to **Responses**. (Google names it "Sheet1" by default. If you'd rather keep another name, set `GOOGLE_SHEET_TAB` to match it in step 4.)
3. Copy the ID from the URL: `https://docs.google.com/spreadsheets/d/<THIS PART>/edit`.

The header row is written automatically on the first submission if row 1 is empty.

## 2. Create a service account and enable the Sheets API

1. Go to console.cloud.google.com. Use an existing project (the one for the Places key is fine) or create a new one.
2. **APIs & Services > Library**: search "Google Sheets API" and click **Enable**.
3. **IAM & Admin > Service Accounts > Create service account**. Name it something like `crew-form`. No project roles are needed.
4. Open the new account, go to **Keys > Add key > Create new key > JSON**. A JSON file downloads.
5. From that file you need two values: `client_email` and `private_key`. Keep the file somewhere private and do not commit it.

## 3. Share the Sheet with the service account

1. In the Sheet, click **Share**.
2. Paste the service account's `client_email` (ends in `.iam.gserviceaccount.com`).
3. Give it **Editor** access. Uncheck "Notify people". Click **Share**.

## 4. Add environment variables in Vercel

In the Vercel dashboard, open this site's project (`indy-ai-research-docs`) and go to **Settings > Environment Variables**. Add each of these for **Production** and **Preview**:

| Name | Value |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | the `client_email` from the JSON key |
| `GOOGLE_PRIVATE_KEY` | the `private_key` from the JSON key, pasted as-is (the `\n` sequences are fine) |
| `GOOGLE_SHEET_ID` | the ID from step 1 |
| `GOOGLE_SHEET_TAB` | optional, only if the tab is not called `Responses` |

Or from a terminal inside the repo, one at a time (each prompts for the value):

```bash
npx vercel@latest env add GOOGLE_SERVICE_ACCOUNT_EMAIL production
npx vercel@latest env add GOOGLE_PRIVATE_KEY production
npx vercel@latest env add GOOGLE_SHEET_ID production
npx vercel@latest env add GOOGLE_SHEET_TAB production
```

Repeat with `preview` in place of `production`.

Then redeploy so the function picks them up: push to `main`, or run `npx vercel@latest --prod --yes`.

## 5. Test against the real Sheet

After the deploy:

1. Open https://airesearch.myfriendfred.org/crew/ and submit a test entry (use a made-up name and an address you can recognise).
2. Check the **Responses** tab. There should be a header row and one new row, with the timestamp in Indiana time.
3. If nothing appears, open Vercel > the project > **Logs** and filter for `crew:`. The log line gives the Google error code (for example `403` means the Sheet is not shared with the service account, and `404` means the Sheet ID or tab name is wrong). Credentials are never logged.

Delete the test row afterward.

## Local testing

```bash
cd ~/Projects/indy-ai-docs
npm install
npm test            # 23 checks against a mocked Sheets client; no Google account needed
```

To try the real Sheet from your Mac, copy `.env.example` to `.env.local`, fill in the values, and run `npx vercel@latest dev`, which serves the page and `/api/crew` together. The `.env*` pattern is gitignored, so the file stays off GitHub.

## Notes

- Rate limiting is per warm instance and in memory. It slows a casual flood but is not a hard limit. The honeypot field and strict option validation handle most bots.
- Pages are rebuilt with `python3 _src/build.py`. Edit the questions or options in `lib/crew-options.json` only: the page and the server both read that file.
- The Sheet stores answers as text. A value starting with `=`, `+`, `-` or `@` gets an apostrophe, so it can't run as a formula.
