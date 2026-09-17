---
name: rename-camera-ready-files
description: Rename PCS camera-ready exports from the generic vis26_camera.json / vis26_camera_archive.zip to the per-track convention (vis26_<track>_metadata.json, vis26_<track>_camera_archive.zip). Use when the user wants to rename, clean up, or standardize the file names in event/track folders (e.g. "give the associated event exports proper names", "rename vis26_camera.json in every event folder", "name these like the full paper version").
---

# Rename camera-ready exports

Wraps `renameCameraReadyFiles.py` at the repo root. Run it from the repo root
with `python3`; no dependencies to install.

## The convention

PCS names every export `vis26_camera.json`, so all the event folders look
alike. Full Papers and Short Papers instead carry a track slug:

```
Full Papers/vis26_full_papers_metadata.json
Uncertainty Vis/vis26_uncertainty_vis_metadata.json
Uncertainty Vis/vis26_uncertainty_vis_camera_archive.zip
```

The slug is the folder name lowercased with runs of non-alphanumerics collapsed
to `_` ("Bio+MedVis Challenge" -> `bio_medvis_challenge`). The conference prefix
(`vis26`) is kept from the existing file name; the per-track letter PCS sometimes
appends to it (`vis26c`, `vis26o`) is dropped, since the slug already names the
track — which is how Full Papers and Short Papers are named.

Both the metadata files (`.json`, `.csv`, `.xlsx`) and the camera archive zips
are renamed; a `_part_01` suffix is kept where PCS split the archive.
`--keep-archive-names` leaves the zips at their PCS names, which is what Full
Papers and Short Papers do. The extracted `vis26_camera_archive/` directory and
everything inside it is never touched.

## Command shape

```sh
# every track folder under a parent
python3 renameCameraReadyFiles.py "VIS26 Data Associated Events" -n

# one folder
python3 renameCameraReadyFiles.py "VIS26 Data Associated Events/Uncertainty Vis"
```

A path can be a single track folder or a parent; folders holding no exports are
skipped. Quote paths — they have spaces. Flags: `-n` / `--dry-run`,
`--keep-archive-names`, `--slug NAME` (override the derived slug; single folder
only), `--prefix vis27` (change the conference prefix).

## How to handle a request

1. Default to the whole parent (`VIS26 Data Associated Events`) when the user
   speaks of the event folders generally; use a single folder when they name one
   event.
2. Run with `-n` first and show the planned renames — the slug for each folder is
   printed, which is the thing most worth a second look.
3. Run for real. Re-running is a no-op, and a rename that would overwrite an
   existing file is skipped with a message rather than clobbering it.
4. Only pass `--keep-archive-names` if the user wants the zips left alone.
5. If a derived slug reads badly for an event, offer `--slug`.

## Notes

- Renaming is safe to do before or after pruning: `pruneCameraReadySubmissions.py`
  finds the metadata file under either the PCS name or a `*_metadata.json` name.
  See the `prune-submissions` skill.
- Renaming does not rewrite `readme.md`; if the user wants the tree in
  `VIS26 Data/readme.md` to match, update it separately.
