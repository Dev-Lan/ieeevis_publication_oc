---
name: export-event-table
description: Build the one-row-per-event summary table — event, record number, event type, paper count, Dropbox link — from the camera-ready metadata exports. Use when the user wants a table of the events themselves rather than the papers (e.g. "table of all the events and their paper counts", "how many papers per track", "the event summary for the records", "spreadsheet with one row per event").
---

# Export event table

Wraps `exportEventTable.py` at the repo root. Run it from the repo root with
`python3`; no dependencies to install.

The event-level companion to `export-contact-list`: that skill makes one row per
paper, this one makes one row per event.

## Columns

`Event`, `Record Number`, `Event Type`, `Paper Count`, `PDF and Supplemental
Files Dropbox Link`.

`Event` is the folder name and `Paper Count` is the number of records in that
event's metadata export. Those two are the only derived columns.

**`Record Number` and the Dropbox link are always emitted empty**, and so is
**`Event Type` for everything except the two paper tracks** — a folder named
like "Full Papers" or "Short Papers" gets `Full Paper` or `Short Paper`, every
other row is blank. What an associated event *is* — workshop, contest, arts
program, symposium — is not encoded in the folder names, so the script does not
guess; it gets filled in by hand with the other two columns.

Do not add event-type guessing back in, in the script or by hand-filling the
output. The user removed it deliberately: a plausible-looking wrong label is
worse here than an empty cell, because an empty cell is obviously still to do.
Say which columns are blank on purpose when reporting, so nobody takes the
table for finished.

## Command shape

```sh
# every event under data/, to out/events.csv
python3 exportEventTable.py --total

# one parent, sorted biggest first
python3 exportEventTable.py "data/VIS26 Data Associated Events" --sort count -o out/workshops.csv
```

With no paths it reads `data/` and searches to any depth, so no year or folder
name is baked in — the same discovery `export-contact-list` uses. Quote paths,
they have spaces.

Other flags: `--format {csv,xlsx,both}`, `--sort {tree,event,count}`, `--total`
(append a Total row), `--only-complete`, `--repair-escapes`.

## How to handle a request

1. Default to all events. Only narrow the paths if the user names some.
2. Write the output into `out/` (the default), or `data/` or `temp/` — this repo
   holds the processing scripts, never the data, which is why those folders are
   gitignored. Never write to the repo root. The script creates the folder.
3. Read the run output: per-event counts, the total, and any `error:` line
   naming an export that could not be read (the run continues through the rest
   and exits nonzero at the end; a JSON decode error means `--repair-escapes`).
4. Report the event count, the paper total, and which columns are left blank on
   purpose.

## Notes

- Paper counts should match the readmes under `data/`. A count that is off
  usually means the export was pruned (see `prune-submissions`) after the readme
  was written, or the other way round.
- Export discovery is imported from `exportContactList.py` and the writers from
  `parseCameraReadyMetadata.py`, so all three stay consistent. Keep them
  importable from the repo root.
