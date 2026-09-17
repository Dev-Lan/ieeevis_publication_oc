This repo is for the IEEE VIS Publication chairs to help organizing existing code/scripts.

## ./parsePcsSetupFormResponses.py

1. update year specific variables at top of script (CONF_NAME, CONF_DATE, DEADLINE_TIME, ALL_CHAIRS, ALL_PUBCHAIRS)

2. Run script:
   `python parsePcsSetupFormResponses.py input_filename outputfilename`

- the `input_filename` must be a csv of responses from the output of the "VIS PCS Setup Form"
- the `output_filename` is the name of the processed csv file to be shared with PCS coordinator.

3. Share output CSV file with contact at precisionconference.

## ./parseCameraReadyMetadata.py

Converts a PCS camera-ready metadata JSON export (e.g. `vis26c_camera.json`) into
the CPS metadata spreadsheet: one row per paper with title, abstract, keywords,
author names, emails, and affiliations. Uses only the Python standard library —
no `pip install` needed.

1. Run script:
   `python parseCameraReadyMetadata.py input_filename output_filename`

- the `input_filename` must be the JSON metadata export from PCS (a JSON list of
  paper records, with `Title`, `Abstract`, and `Author N - ...` fields)
- the `output_filename` extension picks the format: `.xlsx` for Excel, `.csv` for
  CSV. Use `--format both` to write both at once, or `--format csv`/`--format
  xlsx` to override the extension.

The shape of the output follows the input:

- the number of `Author ...` column blocks is the highest author count in the
  JSON file, so nothing is truncated and no unused author blocks are added
- columns that are empty for every paper are dropped (`Author ORCID N`, and the
  columns CPS fills in later such as `Status`, `DOI`, and `CPS Id`). Pass
  `--keep-empty-columns` to keep the full set of template columns.

Examples:

```sh
# Excel workbook
python parseCameraReadyMetadata.py "VIS26 Data/Full Papers/vis26c_camera.json" vis26_full_papers_metadata.xlsx

# CSV
python parseCameraReadyMetadata.py "VIS26 Data/Short Papers/vis26d_camera.json" vis26_short_papers_metadata.csv

# both a .csv and an .xlsx from one run
python parseCameraReadyMetadata.py "VIS26 Data/Short Papers/vis26d_camera.json" vis26_short_papers_metadata.xlsx --format both
```

2. Check the warnings the script prints (papers whose PCS status is not
   `complete` are flagged but still included; pass `--only-complete` to drop
   them).

If the script stops with a JSON decode error, the export contains a backslash
that is not a valid JSON escape — PCS copies author text through verbatim, so
LaTeX in an abstract (`\emph{...}`, `\&`) or a Unicode code point
(`\U00000431`) breaks the file. Re-run with `--repair-escapes` to double those
backslashes and read it anyway; the script prints how many it repaired. The real
fix belongs upstream in PCS.

There is also a `parse-camera-ready-metadata` skill in `.claude/skills/` for
invoking this in plain language from Claude Code.

3. Share the output file with the contact at IEEE CPS.

### Options

| option | default | what it does |
| --- | --- | --- |
| `--format {auto,csv,xlsx,both}` | `auto` | Output format. `auto` reads it from the output file extension; `both` writes a `.csv` and an `.xlsx`. |
| `--affiliation {institution,department,full}` | `institution` | How much of each affiliation to include. `department` prepends the dept/school/lab; `full` also appends city, state/province, and country. |
| `--email {institution,account}` | `institution` | Which author email to prefer; the other is used as a fallback. |
| `--keep-empty-columns` | off | Keep template columns that are empty for every paper instead of dropping them. |
| `--class VALUE` | blank | Value for the `Class` column (e.g. `SB`). Left blank, the column is dropped as empty. |
| `--type VALUE` | blank | Value for the `Type` column (e.g. `AP`). Left blank, the column is dropped as empty. |
| `--start-sequence N` | `1` | First value for the `Sequence` column, which then counts up in file order. |
| `--no-sequence` | off | Leave the `Sequence` column blank, which drops it. |
| `--no-pdf-file-name` | off | Leave `Article Pdf File Name` blank instead of deriving it from the PCS document URL. |
| `--only-complete` | off | Skip papers whose PCS status is not `complete`. |
| `--repair-escapes` | off | Read an export whose backslashes are not valid JSON escapes (LaTeX typed into a title or abstract) by doubling them. |
| `--sheet-name NAME` | `Metadata` | Worksheet name for `.xlsx` output. |

### Notes on the mapping

- Column names and their order match the `metadata template.xlsx` header row,
  minus the columns that came out empty for every paper.
- `Author GivenName N` is first + middle name. The PCS `prefix` field is
  deliberately ignored, because authors put titles like "Dr." or even job titles
  in it.
- `Author Surname N` is the last name plus any generational suffix (e.g. "III").
- There are no `Author ORCID N` columns: PCS does not collect ORCIDs, so they
  are always empty and get dropped.
- Authors with more than one affiliation in PCS get all of them, joined with
  `; `.
- `Submitter Name` / `Submitter Email` come from the PCS contact author, so
  unlike PCS's own "ACM Author Emails, excluding contact email" field, the
  contact author's email does appear in their `Author Email N` column.

## ./pruneCameraReadySubmissions.py

Removes submissions from a PCS camera-ready export folder — the ones an
associated event did not accept for publication. Deletes them from
`vis26_camera.json` and from `vis26_camera_archive/subs/<paper id>/`, and leaves
the archive's `index.html` files alone so the pruned submissions stay in the
listing. Standard library only.

1. Run the script against the event folder (the one holding `vis26_camera.json`
   and `vis26_camera_archive/`), with either an include or an exclude list:

```sh
# drop two submissions
python pruneCameraReadySubmissions.py "VIS26 Data Associated Events/Uncertainty Vis" --exclude 1017 1003

# keep only the accepted papers, listed one ID per line in a file
python pruneCameraReadySubmissions.py "VIS26 Data Associated Events/BELIV" --include @accepted.txt
```

Exactly one of `--include` (keep only these paper IDs) or `--exclude` (drop
these paper IDs) is required. Both take IDs as `1001 1003`, `1001,1003`, or
`@path/to/ids.txt` — one ID per line, with `#` comments and any text after the
ID ignored, so a copy-pasted "ID  Title" list works.

2. Add `-n` for a dry run first. The script prints the IDs it would prune, warns
   about IDs found in neither the metadata nor `subs/`, and refuses to run if the
   selection would remove everything.

Deletion is irreversible: the metadata is backed up to `vis26_camera.json.bak`
(pass `--no-backup` to skip), and `--move-to DIR` moves the pruned submission
folders aside instead of deleting them.

There is also a `prune-submissions` skill in `.claude/skills/`, so in Claude Code
this can be asked for in plain language ("remove 1017 and 1003 from Uncertainty
Vis").

### Options

| option | default | what it does |
| --- | --- | --- |
| `--include ID [ID ...]` | — | Keep only these paper IDs; everything else is removed. |
| `--exclude ID [ID ...]` | — | Remove these paper IDs and keep the rest. |
| `--json PATH` | `<folder>/vis26_camera.json` | Path to the metadata JSON. |
| `--subs PATH` | `<folder>/vis26_camera_archive/subs` | Path to the submissions directory. |
| `--move-to DIR` | off | Move pruned submission folders here instead of deleting them. |
| `--no-backup` | off | Skip the `vis26_camera.json.bak` copy. |
| `-n`, `--dry-run` | off | Report what would be removed and change nothing. |

## ./renameCameraReadyFiles.py

PCS names every camera-ready export `vis26_camera.json`, so the associated event
folders all look alike and the files are ambiguous once moved out of their
folder. This renames them to the per-track convention that Full Papers and Short
Papers already use:

```
Full Papers/vis26_full_papers_metadata.json
Uncertainty Vis/vis26_uncertainty_vis_metadata.json
Uncertainty Vis/vis26_uncertainty_vis_camera_archive.zip
```

The slug comes from the folder name — lowercased, with runs of non-alphanumeric
characters collapsed to `_`, so "Bio+MedVis Challenge" becomes
`bio_medvis_challenge`. The conference prefix (`vis26`) is kept from the existing
file name; the per-track letter PCS sometimes appends to it (`vis26c_camera.json`,
`vis26o_camera.json`) is dropped, since the slug already names the track — which
is how `vis26_full_papers_metadata.json` is named. Files whose names the script
does not recognize are reported and left alone. Standard library only.

1. Point it at a parent folder to do every track at once, or at a single track
   folder. Add `-n` for a dry run first:

```sh
# every event folder under the parent
python renameCameraReadyFiles.py "VIS26 Data Associated Events" -n

# one folder
python renameCameraReadyFiles.py "VIS26 Data Associated Events/Uncertainty Vis"
```

Both the metadata files (`.json`, `.csv`, `.xlsx`) and the camera archive zips
are renamed, so `vis26_camera_archive.zip` becomes
`vis26_uncertainty_vis_camera_archive.zip` and a `_part_01` suffix is kept where
PCS split the archive. Pass `--keep-archive-names` to leave the zips at their PCS
names, which is what Full Papers and Short Papers do. The extracted
`vis26_camera_archive/` directory and its contents are never touched.

Re-running is a no-op, and a rename that would overwrite an existing file is
skipped with a message instead. `pruneCameraReadySubmissions.py` accepts either
the PCS name or the renamed one, so the two scripts can be run in either order.

There is also a `rename-camera-ready-files` skill in `.claude/skills/` for
invoking this in plain language from Claude Code.

### Options

| option | default | what it does |
| --- | --- | --- |
| `--slug NAME` | derived from the folder name | File-name slug to use instead. Only valid for a single track folder. |
| `--prefix VALUE` | kept from the existing file name | Conference prefix for the new names (e.g. `vis27`). |
| `--keep-archive-names` | off | Leave the camera archive zips at their PCS names. |
| `-n`, `--dry-run` | off | Report the renames and change nothing. |

## ./exportContactList.py

Builds one compact contact list across every track — full papers, short papers,
VISions, and the associated events — from the PCS camera-ready metadata
exports. Five columns, one row per paper:

```
Event,Paper ID,Title,Contact Name,Contact Email
Full Papers,1004,NEXO: Adaptive Visualization for Comparative Exploration...,Reza Shahriari,reza.sh44@gmail.com
BELIV,1002,...,...,...
```

`Event` is the folder name, so it reads as "Full Papers", "BELIV",
"Bio+MedVis Challenge". This is the cross-track companion to
`parseCameraReadyMetadata.py`: that script makes the full CPS spreadsheet for
one track, this one makes a roll-up for chasing down contact authors. It shares
that script's parsing and its CSV/XLSX writers, so both must stay importable
from the repo root. Standard library only.

1. Run it with no paths to do the whole conference:

```sh
# every track under data/, to out/contacts.csv
python exportContactList.py

# just the associated events, as a mailing list (one row per email)
python exportContactList.py "data/VIS26 Data Associated Events" -o out/workshops.csv --unique-contacts
```

With no paths it reads `data/`, the working folder this repo keeps camera-ready
exports in — no year or folder name is baked into the default, so it keeps
working as the contents change from one conference to the next. A path can also
be a single event folder or a single metadata file.

Inputs are `*_metadata.json` (the renamed convention) or `*_camera.json` (the
raw PCS name), found at any depth below the path, so a parent, a year folder,
and an event folder all work. Extracted `*_camera_archive/` trees are skipped
and folders holding no export are passed over. `Event` is the name of the folder
each export sits in.

Output defaults to `out/contacts.csv`, and the folder is created if missing.
Keep outputs in `out/`, `data/`, or `temp/`: this repo holds the processing
scripts, not the data, which is why those folders are gitignored.

2. Check the output. Per-event paper counts are printed as it goes, and papers
   with no contact email are warned about. An export that cannot be read is
   reported and skipped so one bad file does not hide the other tracks — the run
   still exits nonzero at the end. A JSON decode error is the same bad-escape
   problem described above; re-run with `--repair-escapes`.

There is also an `export-contact-list` skill in `.claude/skills/` for invoking
this in plain language from Claude Code.

### Options

| option | default | what it does |
| --- | --- | --- |
| `-o`, `--output PATH` | `out/contacts.csv` | Output file; a `.csv` or `.xlsx` extension selects the format. |
| `--format {auto,csv,xlsx,both}` | `auto` | Output format. `auto` reads it from the output file extension; `both` writes a `.csv` and an `.xlsx`. |
| `--sort {tree,event,name}` | `tree` | Row order. `tree` follows the folder tree (path order, folders alphabetically at each level, papers by ID); `event` sorts events alphabetically regardless of path; `name` sorts by contact name. |
| `--unique-contacts` | off | Keep only the first row for each contact email, for a mailing list. |
| `--only-complete` | off | Skip papers whose PCS status is not `complete`. |
| `--repair-escapes` | off | Read an export whose backslashes are not valid JSON escapes by doubling them. |
| `--sheet-name NAME` | `Contacts` | Worksheet name for `.xlsx` output. |
