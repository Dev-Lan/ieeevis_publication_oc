"""Build the one-row-per-event summary table for the camera-ready records.

Reads the PCS metadata exports the same way exportContactList.py does, but
rolls each one up to a single row: the event and how many papers it has. The
Record Number, the Dropbox link, and the Event Type for anything but the full
and short paper tracks are filled in by hand afterwards, so those columns come
out empty.

The export discovery is shared with exportContactList.py, and the parsing and
the CSV/XLSX writers with parseCameraReadyMetadata.py.
"""

import argparse
import json
import os
import re
import sys

from exportContactList import DEFAULT_ROOT, metadata_files
from parseCameraReadyMetadata import load_papers, output_paths, write_csv, write_xlsx

COLUMNS = [
    "Event",
    "Record Number",
    "Event Type",
    "Paper Count",
    "PDF and Supplemental Files Dropbox Link",
]

# Columns nothing in the exports supplies; they are filled in by hand after the
# fact. Event Type is only partly manual — see event_type below.
MANUAL_COLUMNS = [
    "Record Number",
    "Event Type (except the paper tracks)",
    "PDF and Supplemental Files Dropbox Link",
]

# The only two event types the folder tree can be trusted to name. Everything
# else — which associated events are workshops, contests, arts programs — is a
# judgement call the folder names do not encode, so it is left blank rather than
# guessed at.
FULL_PAPERS = re.compile(r"full\s*papers?", re.IGNORECASE)
SHORT_PAPERS = re.compile(r"short\s*papers?", re.IGNORECASE)


def event_type(event):
    """The Event Type for one event, or "" where it has to be filled in."""
    if FULL_PAPERS.search(event):
        return "Full Paper"
    if SHORT_PAPERS.search(event):
        return "Short Paper"
    return ""


def paper_count(path, event, args, problems):
    """Number of papers in one metadata export, or None if it could not be read."""
    try:
        papers = load_papers(path, args.only_complete, args.repair_escapes)
    except SystemExit as error:
        # One unreadable export should not hide the other events, so the file is
        # reported and skipped; the exit status still reflects the failure.
        print(f"error: {error}", file=sys.stderr)
        problems.append(path)
        return None
    except json.JSONDecodeError as error:
        print(f"error: {path}: {error}", file=sys.stderr)
        problems.append(path)
        return None

    print(f"{event}: {len(papers)} papers from {path}")
    return len(papers)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build the one-row-per-event summary table (event, record number, "
            "event type, paper count, Dropbox link) for the camera-ready records."
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
        default=os.path.join("out", "events.csv"),
        help=(
            "Output file; a .csv or .xlsx extension selects the format "
            "(default: out/events.csv)"
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
        choices=["tree", "event", "count"],
        default="tree",
        help=(
            "Row order: tree follows the folder tree, event sorts by name, "
            "count sorts by paper count, largest first (default: tree)"
        ),
    )
    parser.add_argument(
        "--total",
        action="store_true",
        help="Append a Total row summing the paper counts",
    )
    parser.add_argument(
        "--only-complete",
        action="store_true",
        help="Count only papers whose PCS status is 'complete'",
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
        "--sheet-name",
        default="Events",
        help="Worksheet name for xlsx output (default: Events)",
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
        count = paper_count(path, event, args, problems)
        if count is None:
            continue
        rows.append([event, "", event_type(event), str(count), ""])

    if args.sort == "event":
        rows.sort(key=lambda row: row[0].lower())
    elif args.sort == "count":
        rows.sort(key=lambda row: (-int(row[3]), row[0].lower()))

    total = sum(int(row[3]) for row in rows)
    if args.total:
        rows.append(["Total", "", "", str(total), ""])

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
        print(f"wrote {len(rows)} events, {total} papers total to {path}")

    print(f"fill in by hand: {', '.join(MANUAL_COLUMNS)}")

    if problems:
        raise SystemExit(
            f"{len(problems)} export(s) could not be read: {', '.join(problems)}"
        )


if __name__ == "__main__":
    main()
