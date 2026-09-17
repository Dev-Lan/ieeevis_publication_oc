---
name: export-contact-list
description: Build one compact contact list across all VIS tracks — event, paper ID, title, contact name, contact email — from the PCS camera-ready metadata exports. Use when the user wants a combined list of contact authors or a mailing list spanning tracks (e.g. "give me a csv of every contact author", "one list of all papers and their contacts", "who do I email about camera-ready across all tracks", "contact list for full, short, VISions and the workshops").
---

# Export contact list

Wraps `exportContactList.py` at the repo root. Run it from the repo root with
`python3`; no dependencies to install.

This is the cross-track companion to `parse-camera-ready-metadata`. That skill
makes the full CPS spreadsheet for one track; this one makes a five-column
roll-up across every track, for chasing down contact authors.

## Columns

`Event`, `Paper ID`, `Title`, `Contact Name`, `Contact Email` — one row per
paper. `Event` is the folder name, so it reads as "Full Papers", "BELIV",
"Bio+MedVis Challenge".

## Command shape

```sh
# every track under data/
python3 exportContactList.py

# a subset, to a named output
python3 exportContactList.py "data/VIS26 Data Associated Events" -o out/workshops.csv
```

With no paths it reads `data/`, the working folder this repo keeps camera-ready
exports in. Nothing about that default is tied to a year, so it keeps working
as the folders inside change — do not hard-code a year's folder names into an
invocation unless the user is deliberately narrowing to one.

A path can also be a single event folder or a single metadata file. Quote
paths, they have spaces.

Inputs are `*_metadata.json` (the renamed convention) or `*_camera.json` (the
raw PCS name), found at any depth below the path, so a parent, a year folder,
and an event folder all work. Extracted `*_camera_archive/` trees are skipped,
and folders with no export are passed over silently. `Event` is the name of the
folder the export sits in.

Useful flags: `--format {csv,xlsx,both}`, `--sort {tree,event,name}`,
`--unique-contacts` (one row per email — the mailing-list form),
`--only-complete`, `--repair-escapes`. Output defaults to `out/contacts.csv`.
Default order is `tree`: path order, then folders alphabetically at each level,
then papers by ID within an event.

## How to handle a request

1. Default to all tracks. Only narrow the paths if the user names specific
   events.
2. Pass `--unique-contacts` when the ask is about emailing people rather than
   about papers — without it a contact who submitted twice appears twice.
3. Write the output into `out/` (the default), or `data/` or `temp/`. This repo
   is for the processing scripts, never for the data — those three folders are
   gitignored for that reason. Never write the list to the repo root. The
   script creates the output folder if it is missing.
4. Read the run output, not just the exit status:
   - the per-event paper counts, which should match what each event should have
     (the readmes under `data/` list them), and the track count — a missing
     track means its export is not under the path that was searched
   - `warning: <event> paper N has no contact email` — worth surfacing, it means
     nobody can be reached about that paper
   - `warning: paper N has status '...'` — a paper PCS does not consider
     complete, still included
   - an `error:` line names an export that could not be read; the run continues
     through the other tracks and exits nonzero at the end. A JSON decode error
     here means the same bad-escape problem described in
     `parse-camera-ready-metadata`; re-run with `--repair-escapes`.
5. Report the total row count and the number of tracks.

## Notes

- Re-running just overwrites the output, and it reads only the metadata JSON,
  never the camera archives. Re-run after any prune — the list is a snapshot of
  the JSON at the time it was generated.
- The parsing, the escape repair, and the CSV/XLSX writers are imported from
  `parseCameraReadyMetadata.py`, so the two scripts stay consistent. Keep them
  importable from the repo root.
