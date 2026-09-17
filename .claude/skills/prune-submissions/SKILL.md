---
name: prune-submissions
description: Remove submissions from a VIS camera-ready export folder — deletes them from vis26_camera.json and from vis26_camera_archive/subs/, leaving index.html alone. Use when the user wants to prune, drop, remove, or keep-only certain paper IDs in an event folder (e.g. "remove 1017 and 1003 from Uncertainty Vis", "in BELIV keep only these papers", "prune the VISAP export to the accepted list").
---

# Prune camera-ready submissions

Wraps `pruneCameraReadySubmissions.py` at the repo root. Run it from the repo
root with `python3`; no dependencies to install.

## Command shape

```sh
python3 pruneCameraReadySubmissions.py "<event folder>" --exclude 1017 1003
python3 pruneCameraReadySubmissions.py "<event folder>" --include @accepted.txt
```

The event folder is the one holding `vis26_camera.json` and
`vis26_camera_archive/`, normally under `VIS26 Data Associated Events/<event>`.
Quote it — the paths have spaces.

Exactly one of `--include` (keep only these IDs) or `--exclude` (drop these
IDs) is required. Both accept `1001 1003`, `1001,1003`, or `@path/to/ids.txt`
(one ID per line, `#` comments and trailing text after the ID are ignored).

Useful flags: `-n` / `--dry-run` (report and change nothing), `--move-to DIR`
(move pruned folders there instead of deleting), `--no-backup` (skip the
`vis26_camera.json.bak` copy, which is written by default), `--json` /
`--subs` to point at non-default paths.

## How to handle a request

1. Work out which event folder is meant. If the user names an event ("Uncertainty
   Vis", "BELIV"), match it against the directories in
   `VIS26 Data Associated Events/`; ask only if the name is genuinely ambiguous.
2. Work out whether the user gave IDs to remove (`--exclude`) or the full set to
   keep (`--include`). A phrase like "keep only" or "the accepted list" means
   `--include`. If it's unclear which way a list runs, ask — the two produce
   opposite results.
3. Run with `-n` first and show the user the planned removals.
4. Run for real once the plan looks right. Deletion is irreversible, so if the
   user has not clearly approved the specific list, confirm before the real run,
   or use `--move-to` so the folders are recoverable.
5. Report the counts the script prints (records dropped, folders removed) and
   note that the `.bak` metadata copy exists unless `--no-backup` was used.

## Notes

- The script warns about IDs that are in neither the metadata nor `subs/`
  (usually a typo in the list) — surface that warning to the user.
- It refuses to run if the selection would remove every submission.
- `index.html` in the archive is intentionally left as-is, so pruned
  submissions still appear in the archive listing. Don't "fix" that.
- These export folders are large and untracked by git; there is no commit to
  fall back on, so prefer a dry run and the default backup.
