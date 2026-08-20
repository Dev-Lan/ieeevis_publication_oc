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
