---
name: parse-camera-ready-metadata
description: Convert a PCS camera-ready metadata JSON export into the CPS metadata spreadsheet (.csv / .xlsx) with title, abstract, keywords, and per-author names, emails, and affiliations. Use when the user wants to generate, regenerate, or refresh the CPS spreadsheets for a track or event folder (e.g. "make the CPS spreadsheet for BELIV", "regenerate the full papers xlsx", "run the metadata parser on the associated events").
---

# Parse camera-ready metadata

Wraps `parseCameraReadyMetadata.py` at the repo root. Run it from the repo root
with `python3`; no dependencies to install.

## Command shape

```sh
python3 parseCameraReadyMetadata.py <input.json> <output.xlsx> --format both
```

The input is a PCS metadata export — `vis26_<event>_metadata.json` in an event
folder, or the PCS name `vis26<letter>_camera.json` if it has not been renamed
yet (see the `rename-camera-ready-files` skill). Quote paths, they have spaces.

`--format both` writes a `.csv` and an `.xlsx` from one run, which is what the
Full Papers and Short Papers folders hold. Otherwise the output extension picks
the format.

Write the output next to its input, named to match:
`VIS26 Data Associated Events/BELIV/vis26_beliv_metadata.xlsx`.

Useful flags: `--repair-escapes` (see below), `--affiliation
{institution,department,full}`, `--email {institution,account}`,
`--only-complete` (drop papers whose PCS status is not `complete`; by default
they are kept and warned about), `--keep-empty-columns`, `--class` / `--type`
(fill the CPS `Class` / `Type` columns). The repo readme has the full table.

## Malformed exports: --repair-escapes

PCS copies author text through verbatim, so an abstract containing LaTeX
(`\emph{...}`, `\&`) or a Unicode code point (`\U00000431`) leaves a lone
backslash in the JSON. A lone backslash is not a valid JSON escape, so
`json.load` fails and the whole file is unreadable.

Without the flag the script stops with the decoder error, the byte offset, and a
pointer to `--repair-escapes`. With it, each invalid escape is doubled — the
backslash is text the author meant literally, so this preserves the character —
and the count of repairs is printed.

Only reach for the flag when a run actually fails. It is a workaround for a bad
export, so say which files needed it and how many escapes were repaired; the
fix belongs upstream in PCS.

## How to handle a request

1. Work out which folders are meant. "The associated events" means every
   `*_metadata.json` under `VIS26 Data Associated Events/`; a named event means
   that one folder.
2. Run per input file, writing the `.xlsx` beside it with `--format both`. A
   shell loop over `"VIS26 Data Associated Events"/*/*_metadata.json` does the
   whole set.
3. Read the output of each run, not just the exit status. Worth surfacing:
   - `warning: paper N has status '...'` — a paper PCS does not consider
     complete is still included.
   - `dropped N empty columns` — normal for `Author ORCID N` and the columns CPS
     fills in later. But a dropped **`Abstract`** or **`Keywords`** column means
     the event never collected that field, which is worth telling the user about
     rather than passing over.
   - `warning: truncated cell ...` — an abstract over Excel's 32,767-character
     cell limit.
4. Report the per-file paper and column counts, and check the paper count
   matches what the event should have.

## Notes

- Standard library only, and re-running just overwrites the output, so it is
  safe to re-run after pruning. Do re-run after any prune: the spreadsheet is a
  snapshot of the JSON at the time it was generated.
- No `Author ORCID` columns ever survive — PCS does not collect ORCIDs.
- The parse step reads only the metadata JSON. It never touches the camera
  archive zips.
