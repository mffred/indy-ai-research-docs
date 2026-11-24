# District 19 turnout data

`data.json` fed the old District 19 page (`/district-19-turnout`, now redirected to `/turnout?district=19`). It's kept for its 2015–2023 District 19 history, which the countywide map doesn't include; nothing builds from it now.

## What's in it

- `precincts`: the 24 voting precincts in City-County Council District 19. Each has its shape (`type`, `coords`, WGS84 lon/lat) and its 2023 counts:
  - `reg`, `pBal`: registered voters and ballots cast (all parties) in the May 2023 primary
  - `dem`, `rep`: votes cast in the Democratic and Republican Indianapolis mayor primaries
  - `gReg`, `gBal`: registered voters and ballots cast in the November 2023 general
  - `bg`: inside the city of Beech Grove (the precinct has Beech Grove city votes in 2023)
- `district`: the District 19 boundary. `bgOutline`: the outer edge of the six Beech Grove precincts.
- `roads`: major-road centerlines (freeways, arterials, primary collectors) around the district, grouped by street name. `c` is the class: 0 freeway/expressway, 1 primary arterial, 2 secondary arterial, 3 collector.
- `history`: registered voters and ballots cast for 2015, 2019 and 2023, for the District 19 area (old District 21 in 2015 and 2019), the city of Beech Grove (9 precincts) and Marion County.

## Sources (pulled November 23, 2026)

- Precinct results: Indianapolis Open Data election results archive. 2023 primary: `2023P_Precinct_Results.xlsx`. 2023 general: `2023GeneralElectionResults.xlsx` (Turnout tab for registered voters and ballots). 2015 and 2019: `2015PrimaryElectionResults.xls`, `2015MunicipalElectionResults.xls`, `2019PrimaryElectionResults.xls` and `2019GeneralElectionResults.xlsm`.
- Shapes: City of Indianapolis GIS, `OpenData_Political/MapServer/2` (precincts) and `/1` (council districts). The 24 precinct areas sum to the district's area, so the current precinct map matches the 2023 district.
- Roads: `OpenData_Transportation/MapServer/13`, major classes only, no ramps.

## Checks

- District totals: 21,133 registered and 2,366 ballots in the primary, 21,321 registered and 4,682 ballots in the general. These match the sum of the precinct rows in the source files.
- Old District 21 (2015, 2019) = the precincts with votes in that council race. Beech Grove (2015, 2019, 2023) = the precincts with votes in the Beech Grove mayor race.

# Countywide turnout map data (`city/`)

`city/data.json` and `city/d/<n>.json` feed `/turnout`. Built by `build_city.py` (run `python3 _src/turnout-data/build_city.py`; raw downloads are cached in `raw/`, which is git-ignored), then copied by `build.py`.

## What's in it

- `elections`: the six elections, with the race used for the Democratic share in each (2023 primary: mayor primaries; 2023 general: mayor; 2024 primary: party ballots; 2024 general: president; 2026 primary: the two unopposed prosecutor nominees; 2026 general: Secretary of State).
- `precincts`: all 621 precincts. `d` council district, `t` township, `c` city or town (a precinct with votes in Beech Grove's, Lawrence's, Southport's or Speedway's own 2023 race). Per election `[registered, ballots, Democratic votes, Republican votes, other votes]`; null where the source has no figure.
- `districts`: the 25 council districts, outline (simplified to about 40 m), councilor (from `council-data/members.json`), totals per election, and the 2023 council race.
- `mayor`: the 2023 mayor's race with every candidate: `races` (general, Democratic primary, Republican primary, each with its candidates and map colors) and `county` totals. Each precinct has `my` (votes per candidate, per race) and each district has the same sums. County totals match the published results: general Hogsett 97,807 / Shreve 66,781; Democratic primary Hogsett 28,320 / Shackleford 18,359; Republican primary Shreve 19,170 / Shabazz 7,639.
- `county`: Marion County totals per election. `freeways`: freeway lines for the citywide view.
- `d/<n>.json`: one district's precinct shapes (simplified to about 3 m) and major roads (freeways to primary collectors, from the city's street centerline thoroughfare class).

## Sources (pulled November 23, 2026)

- 2023 primary, 2023 general, 2024 primary, 2024 general, 2026 primary: Indianapolis Open Data "Election Results" items (URLs in `build_city.py`).
- 2026 general: the Election Board's certified results by precinct from indy.gov/workflow/election-results (run date 11/23/2026). Not yet on the open data portal.
- The 2026 primary file has candidate votes only: no registered voters or ballots by precinct. The county row's registered voters and ballots (632,168 / 99,923) come from the Election Board's county-wide figures at indy.gov/activity/marion-county-voter-turnout; districts and precincts have no 2026 primary turnout.
- Precinct-to-district: the 2023 council race sheets, which list every precinct under its district. Shapes: city GIS `OpenData_Political/MapServer/2` and `/1`.

## Checks

- All six files cover the same 621 precincts as the current precinct map (2026 general has no rows for PE007, WY043 and WY056, which have no voters).
- 2026 general county totals, 640,323 registered and 262,042 ballots, match the Election Board's certified summary.
- District 19's 2023 totals (21,133 / 2,366 primary; 21,321 / 4,682 general) match the old District 19 page.
- Each precinct is in exactly one district; district sizes run from 17 to 34 precincts.
