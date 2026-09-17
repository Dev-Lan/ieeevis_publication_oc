"""Prune submissions out of a PCS camera-ready export folder.

Associated event exports come with more submissions than the event actually
accepted for publication. This removes the unwanted ones from both halves of
the export: the `vis26_camera.json` metadata list and the
`vis26_camera_archive/subs/<paper id>/` directories.

The `index.html` files inside the archive are left alone, so the pruned
submissions stay visible in the archive listing.

Takes either an include list (keep only these paper IDs) or an exclude list
(drop these paper IDs). IDs can be given on the command line or read from a
file, one ID per line.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

JSON_NAME = "vis26_camera.json"
# What renameCameraReadyFiles.py renames the PCS export to.
JSON_GLOB = "*_metadata.json"
ARCHIVE_NAME = "vis26_camera_archive"
ID_FIELD = "Paper ID"

# A line of an ID file: the ID, optionally followed by a comment or a title.
ID_LINE = re.compile(r"^\s*([A-Za-z]*[0-9]+)\b")

# Some tracks prefix their PCS paper IDs ("bmv3310") while the submission
# folders are named with the bare number ("3310"), so IDs are matched on their
# trailing digits.
ID_DIGITS = re.compile(r"([0-9]+)$")


def fail(message):
    sys.exit(f"error: {message}")


def parse_ids(values, label):
    """Turn CLI arguments into a set of paper ID strings.

    Each value is either a literal list of IDs ("1001,1003" or "1001 1003") or
    `@path`, a file with one ID per line (blank lines and `#` comments skipped).
    """
    ids = []
    for value in values:
        if value.startswith("@"):
            ids.extend(read_id_file(value[1:]))
            continue
        for token in re.split(r"[,\s]+", value.strip()):
            if token:
                ids.append(normalize_id(token, label))
    if not ids:
        fail(f"no paper IDs found in the {label} list")
    return {canonical(paper) for paper in ids}


def read_id_file(path):
    if not os.path.isfile(path):
        fail(f"ID file not found: {path}")
    ids = []
    with open(path, encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = ID_LINE.match(line)
            if not match:
                fail(f"{path}:{number}: expected a paper ID, got {line!r}")
            ids.append(canonical(match.group(1)))
    return ids


def normalize_id(token, label):
    if not re.fullmatch(r"[A-Za-z]*[0-9]+", token):
        fail(f"{label} list: {token!r} is not a paper ID")
    return token


def canonical(value):
    """The form two paper IDs are compared on: their trailing digits.

    "bmv3310" and "3310" are the same submission, one as PCS writes it in the
    metadata and one as it names the folder in the archive.
    """
    text = str(value).strip().lower()
    match = ID_DIGITS.search(text)
    return match.group(1) if match else text


def paper_id(paper):
    value = paper.get(ID_FIELD)
    return "" if value is None else str(value).strip()


def find_json(folder):
    """The metadata file in an event folder: the PCS name, else a renamed one."""
    default = os.path.join(folder, JSON_NAME)
    if os.path.isfile(default):
        return default
    renamed = sorted(glob.glob(os.path.join(folder, JSON_GLOB)))
    if len(renamed) == 1:
        return renamed[0]
    if renamed:
        fail(
            f"{folder} holds several metadata files; pass --json to pick one: "
            + ", ".join(os.path.basename(path) for path in renamed)
        )
    return default


def locate(folder, json_path, subs_path):
    """Resolve the metadata file and subs directory for an event folder."""
    if json_path is None:
        json_path = find_json(folder)
    if subs_path is None:
        subs_path = os.path.join(folder, ARCHIVE_NAME, "subs")
    if not os.path.isfile(json_path):
        fail(f"metadata file not found: {json_path}")
    if not os.path.isdir(subs_path):
        fail(f"subs directory not found: {subs_path}")
    return json_path, subs_path


def load_papers(json_path):
    with open(json_path, encoding="utf-8-sig") as handle:
        papers = json.load(handle)
    if not isinstance(papers, list):
        fail(f"{json_path}: expected a JSON list of paper records")
    for paper in papers:
        if not isinstance(paper, dict) or not paper_id(paper):
            fail(f"{json_path}: every record needs a numeric {ID_FIELD!r} field")
    return papers


def sub_dirs(subs_path):
    """Paper IDs that have a submission directory, in listing order."""
    return sorted(
        entry
        for entry in os.listdir(subs_path)
        if os.path.isdir(os.path.join(subs_path, entry))
    )


def select(known_ids, include, exclude):
    """Split the known IDs into the ones to keep and the ones to remove."""
    if include is not None:
        keep = {paper for paper in known_ids if paper in include}
        drop = {paper for paper in known_ids if paper not in include}
    else:
        keep = {paper for paper in known_ids if paper not in exclude}
        drop = {paper for paper in known_ids if paper in exclude}
    return keep, drop


def prune_json(json_path, papers, drop, backup, dry_run):
    kept = [paper for paper in papers if canonical(paper_id(paper)) not in drop]
    removed = len(papers) - len(kept)
    if dry_run:
        return removed

    if backup:
        backup_path = json_path + ".bak"
        shutil.copy2(json_path, backup_path)
        print(f"backed up metadata to {backup_path}")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(kept, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return removed


def prune_subs(subs_path, drop, move_to, dry_run):
    removed = []
    for paper in sub_dirs(subs_path):
        if canonical(paper) not in drop:
            continue
        source = os.path.join(subs_path, paper)
        removed.append(paper)
        if dry_run:
            continue
        if move_to:
            os.makedirs(move_to, exist_ok=True)
            destination = os.path.join(move_to, paper)
            if os.path.exists(destination):
                shutil.rmtree(destination)
            shutil.move(source, destination)
        else:
            shutil.rmtree(source)
    return removed


def main():
    parser = argparse.ArgumentParser(
        description="Prune submissions from a camera-ready export folder",
    )
    parser.add_argument(
        "folder",
        help=(
            "event folder holding vis26_camera.json and vis26_camera_archive/"
            " (e.g. 'VIS26 Data Associated Events/Uncertainty Vis')"
        ),
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--include",
        nargs="+",
        metavar="ID",
        help="Keep only these paper IDs; everything else is removed. "
        "Accepts '1001 1003', '1001,1003', or '@ids.txt'",
    )
    selection.add_argument(
        "--exclude",
        nargs="+",
        metavar="ID",
        help="Remove these paper IDs and keep the rest. Same formats as --include",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help=f"Path to the metadata JSON (default: <folder>/{JSON_NAME}, or the "
        f"one {JSON_GLOB} file if it has been renamed)",
    )
    parser.add_argument(
        "--subs",
        dest="subs_path",
        help=f"Path to the subs directory (default: <folder>/{ARCHIVE_NAME}/subs)",
    )
    parser.add_argument(
        "--move-to",
        metavar="DIR",
        help="Move pruned submission folders here instead of deleting them",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help=f"Do not write a {JSON_NAME}.bak copy before rewriting the metadata",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Report what would be removed and change nothing",
    )
    args = parser.parse_args()

    include = parse_ids(args.include, "include") if args.include else None
    exclude = parse_ids(args.exclude, "exclude") if args.exclude else None

    json_path, subs_path = locate(args.folder, args.json_path, args.subs_path)
    papers = load_papers(json_path)

    json_ids = [paper_id(paper) for paper in papers]
    dir_ids = sub_dirs(subs_path)
    known_ids = {canonical(paper) for paper in json_ids} | {
        canonical(paper) for paper in dir_ids
    }

    keep, drop = select(known_ids, include, exclude)
    # How each pruned submission is named, for the report.
    dropped_names = sorted(
        {paper for paper in json_ids if canonical(paper) in drop}
        | {paper for paper in dir_ids if canonical(paper) in drop}
    )

    unknown = sorted((include or exclude) - known_ids)
    if unknown:
        label = "include" if include else "exclude"
        print(
            f"warning: {len(unknown)} {label} ID(s) are in neither the metadata "
            f"nor the subs directory: {', '.join(unknown)}"
        )
    if not drop:
        print("nothing to prune")
        return
    if not keep:
        fail("that would remove every submission; check the include/exclude list")

    verb = "would remove" if args.dry_run else "removing"
    print(f"{verb} {len(drop)} of {len(known_ids)} submissions, keeping {len(keep)}")
    print(f"  pruned: {', '.join(dropped_names)}")

    removed_papers = prune_json(json_path, papers, drop, not args.no_backup, args.dry_run)
    removed_dirs = prune_subs(subs_path, drop, args.move_to, args.dry_run)

    tense = "would drop" if args.dry_run else "dropped"
    print(f"{tense} {removed_papers} of {len(papers)} records from {json_path}")
    destination = f" to {args.move_to}" if args.move_to else ""
    print(f"{tense} {len(removed_dirs)} submission folder(s) from {subs_path}{destination}")

    dir_canon = {canonical(paper) for paper in dir_ids}
    missing_dirs = sorted(paper for paper in drop if paper not in dir_canon)
    if missing_dirs:
        print(
            f"note: no subs folder existed for {', '.join(missing_dirs)} "
            "(metadata only)"
        )
    print("index.html files were left untouched")


if __name__ == "__main__":
    main()
