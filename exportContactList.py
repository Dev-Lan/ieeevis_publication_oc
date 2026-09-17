"""Build one compact contact list across every track's camera-ready metadata.

Reads the PCS metadata exports for all tracks — full papers, short papers,
VISions, and the associated events — and writes a single spreadsheet with one
row per paper: which event it belongs to, its paper ID, its title, and the
contact author's name and email. Standard library only.

The per-paper parsing, the JSON-escape repair, and the CSV/XLSX writers are
shared with parseCameraReadyMetadata.py.
"""

import argparse
import glob
import json
import os
import re
import sys

from parseCameraReadyMetadata import (
    clean,
    load_papers,
    output_paths,
    write_csv,
    write_xlsx,
)

COLUMNS = ["Event", "Paper ID", "Title", "Contact Name", "Contact Email"]

# The working folder this repo keeps its camera-ready data in (see .gitignore).
# Nothing below it is named for a year, so this default holds for VIS27 and on.
DEFAULT_ROOT = "data"

# The renamed convention (vis26_beliv_metadata.json) and the raw PCS export name
# (vis26_camera.json, vis26c_camera.json) — see renameCameraReadyFiles.py.
METADATA_PATTERNS = ["*_metadata.json", "*_camera.json"]

# Directories never worth descending into: the extracted camera archives hold a
# JSON file per submission, and none of them are metadata exports.
SKIP_DIRECTORIES = re.compile(r"^(\..*|__pycache__|.*_camera_archive.*|subs)$")


def metadata_files(root):
    """Metadata exports under a path, as (event name, file path) pairs.

    A path can be a single metadata file, a single event folder, or any parent
    above them — the tree is walked to whatever depth the exports sit at, so
    the folder layout can change from year to year. Directories are visited in
    name order, so the row order follows the tree rather than the filesystem.
    """
    if os.path.isfile(root):
        return [(os.path.basename(os.path.dirname(os.path.abspath(root))), root)]

    if not os.path.isdir(root):
        raise SystemExit(f"{root}: no such file or directory")

    found = []
    for folder, subdirectories, _ in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if not SKIP_DIRECTORIES.match(name)
        )
        for pattern in METADATA_PATTERNS:
            for path in sorted(glob.glob(os.path.join(folder, pattern))):
                found.append((os.path.basename(os.path.abspath(folder)), path))
    return found


def paper_sort_key(row):
    """Sort within an event by paper ID, numerically where PCS uses numbers."""
    paper_id = row[1]
    try:
        return (0, int(paper_id), "")
    except ValueError:
        return (1, 0, paper_id)


def collect(path, event, args, problems):
    """Rows for one metadata export, or an empty list if it could not be read."""
    try:
        papers = load_papers(path, args.only_complete, args.repair_escapes)
    except SystemExit as error:
        # One unreadable export should not hide the other tracks, so the file is
        # reported and skipped; the exit status still reflects the failure.
        print(f"error: {error}", file=sys.stderr)
        problems.append(path)
        return []
    except json.JSONDecodeError as error:
        print(f"error: {path}: {error}", file=sys.stderr)
        problems.append(path)
        return []

    rows = []
    for paper in papers:
        name = clean(paper.get("Contact Name"))
        email = clean(paper.get("Contact Email"))
        paper_id = clean(paper.get("Paper ID"))
        if not email:
            print(f"warning: {event} paper {paper_id} has no contact email")
        rows.append([event, paper_id, clean(paper.get("Title")), name, email])

    rows.sort(key=paper_sort_key)
    print(f"{event}: {len(rows)} papers from {path}")
    return rows


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build one compact contact list (event, paper ID, title, contact "
            "name, contact email) across every track's camera-ready metadata."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[DEFAULT_ROOT],
        help=(
            "Metadata files, event folders, or any parent above them; the tree "
            f"is searched to any depth (default: {DEFAULT_ROOT})"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join("out", "contacts.csv"),
        help=(
            "Output file; a .csv or .xlsx extension selects the format "
            "(default: out/contacts.csv)"
        ),
    )
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "xlsx", "both"],
        default="auto",
        help="Output format (default: from the output file extension)",
    )
    parser.add_argument(
        "--sort",
        choices=["tree", "event", "name"],
        default="tree",
        help=(
            "Row order: tree follows the folder tree, event sorts events "
            "alphabetically, name sorts by contact name (default: tree)"
        ),
    )
    parser.add_argument(
        "--only-complete",
        action="store_true",
        help="Skip papers whose PCS status is not 'complete'",
    )
    parser.add_argument(
        "--repair-escapes",
        action="store_true",
        help=(
            "Read an export whose backslashes are not valid JSON escapes "
            "(LaTeX typed into a title or abstract) by doubling them"
        ),
    )
    parser.add_argument(
        "--unique-contacts",
        action="store_true",
        help="Keep only the first row for each contact email (a mailing list)",
    )
    parser.add_argument(
        "--sheet-name",
        default="Contacts",
        help="Worksheet name for xlsx output (default: Contacts)",
    )
    args = parser.parse_args()

    targets = output_paths(args.output, args.format)

    sources = []
    for path in args.paths:
        sources.extend(metadata_files(path))
    if not sources:
        raise SystemExit(f"no metadata exports found under: {', '.join(args.paths)}")

    problems = []
    rows = []
    for event, path in sources:
        rows.extend(collect(path, event, args, problems))

    if args.sort == "event":
        rows.sort(key=lambda row: (row[0].lower(), paper_sort_key(row)))
    elif args.sort == "name":
        rows.sort(key=lambda row: (row[3].lower(), row[0].lower()))

    if args.unique_contacts:
        seen = set()
        unique = []
        for row in rows:
            key = row[4].lower()
            if key and key in seen:
                continue
            seen.add(key)
            unique.append(row)
        print(f"kept {len(unique)} of {len(rows)} rows after de-duplicating contacts")
        rows = unique

    for path, output_format in targets:
        # The repo is for processing, not for holding data, so the output
        # usually lands in a gitignored working folder that may not exist yet.
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if output_format == "csv":
            write_csv(path, COLUMNS, rows)
        else:
            write_xlsx(path, COLUMNS, rows, args.sheet_name)
        tracks = "track" if len(sources) == 1 else "tracks"
        print(f"wrote {len(rows)} papers from {len(sources)} {tracks} to {path}")

    if problems:
        raise SystemExit(
            f"{len(problems)} export(s) could not be read: {', '.join(problems)}"
        )


if __name__ == "__main__":
    main()
