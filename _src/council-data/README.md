# Council data

Plain-text copies of Indianapolis City-County Council full-council records, 2021 to 2026, kept so they
can be searched and re-parsed without downloading the PDFs again. Not deployed (`.vercelignore` skips `_src`).

- `minutes/YYYY-MM-DD.txt`: the official meeting minutes ("Journal of the City-County Council"), from the
  PDFs' own text layer. Proposal titles, sponsors, committee actions, public testimony and roll-call votes
  written out in full. Posted after the Council approves them, so the newest meetings lag.
- `roll-calls/YYYY-MM-DD.txt`: the roll-call vote sheets, one page per vote. Almost all are scanned images,
  so this text is OCR (tesseract) and can misread names or numbers. The minutes are the primary source for
  votes; these sheets are the cross-check, and the only source for meetings whose minutes aren't posted yet.
- `agendas/YYYY-MM-DD.txt`: meeting agendas, used only for proposal titles ("DIGEST") where the minutes
  aren't posted yet. Currently August and September 2026.
- `city-proposals/YYYY.json`: the city's proposal database (the feed behind indy.gov's Council Proposal
  Search), one file per year, 2020-2026, saved by `tools/fetch_city_proposals.py`. Gives each proposal's short
  summary, committee, initiator, sponsors, date introduced, a link to its full text, and the Council's recorded
  result ("Adopted 17-8"), which `parse_votes.py` uses to check every final vote count.
- `proposals/<no>-<year>.txt`: the full text of each proposal that came up for a roll-call vote (1,677), from
  the document the city's proposal database links to. Most are scans, so this is OCR (tesseract) and can
  misread words, especially in tables and signatures; two were Word files. Saved by
  `tools/fetch_proposal_texts.py` (resumable). The page publishes a cleaned copy of each in
  `council-votes/text/` and builds a word index (`council-votes/search-index.json`) for full-text search.
- `sources.json`: every meeting, with the city's URL for each document, page counts and how the text was made.
- `pdf/`: the downloaded PDFs (git-ignored, re-downloadable from `sources.json`).
- `tools/ocr_roll_calls.py`: re-runs the OCR.
- `tools/parse_votes.py`: builds `votes.json` from all of the above; `topics.py` and `topic-overrides.json` tag
  topics; `members.json` holds display names. Then `python3 _src/build.py` rebuilds the page.

Each file marks page breaks with `=== <date> <document>, page N of M ===` so a search hit can be traced to
a page of the original PDF.

Known gaps: the city posts roll-call sheets for only 5 of 2022's meetings (minutes cover the rest), and its
link for the May 4, 2026 roll call points to an internal CMS page rather than the PDF.
