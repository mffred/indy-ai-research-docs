# District 19 turnout data

`data.json` feeds `/district-19-turnout`. `build.py` copies it to `district-19-turnout/data.json`.

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
