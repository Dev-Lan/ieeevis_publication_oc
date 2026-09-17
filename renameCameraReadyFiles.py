"""Rename PCS camera-ready exports to the per-track file naming convention.

PCS names every export the same thing — `vis26_camera.json` — so the associated
event folders all look alike and the files are ambiguous once moved out of their
folder. The Full Papers and Short Papers folders instead use a track slug taken
from the folder name:

    Full Papers/vis26_full_papers_metadata.json
    Uncertainty Vis/vis26_uncertainty_vis_metadata.json

This renames the exports in one or more track folders to match — both the
metadata files and the camera archive zips, so `vis26_camera_archive.zip`
becomes `vis26_uncertainty_vis_camera_archive.zip` (a `_part_01` suffix is kept
where PCS split the archive). Pass `--keep-archive-names` to leave the zips at
their PCS names, which is what Full Papers and Short Papers do.

Point it at a single track folder or at a parent like
"VIS26 Data Associated Events" and it will find the track folders underneath.
"""

import argparse
import os
import re
import sys

# The PCS export names, and what each becomes: <prefix>_<slug>_<suffix>.
METADATA_STEM = "camera"
METADATA_SUFFIX = "metadata"
ARCHIVE_STEM = "camera_archive"
METADATA_EXTENSIONS = (".json", ".csv", ".xlsx")

# "vis26_camera.json", "vis26o_camera.json", "vis26_camera_archive_part_01.zip",
# "vis26_uncertainty_vis_metadata.json" — the conference prefix, the per-track
# letter PCS sometimes appends to it, the middle, and an optional part number.
# The track letter is dropped from the new name: the slug already says the
# track, which is how Full Papers ("vis26c" -> vis26_full_papers_metadata.json)
# and Short Papers ("vis26d") are named.
EXPORT_NAME = re.compile(
    r"^(?P<prefix>[a-z]+[0-9]{2,4})(?P<track>[a-z]*)_"
    r"(?P<middle>.+?)(?P<part>_part_[0-9]+)?$"
)


def fail(message):
    sys.exit(f"error: {message}")


def slugify(name):
    """Turn a folder name into a file-name slug ("Bio+MedVis" -> bio_medvis")."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        fail(f"cannot build a file-name slug from folder name {name!r}")
    return slug


def is_export(name):
    """Whether a file name is one of the exports this script renames."""
    stem, extension = os.path.splitext(name)
    if extension.lower() == ".zip":
        return True
    return extension.lower() in METADATA_EXTENSIONS and not stem.startswith(".")


def track_folders(path):
    """The track folders to work on: `path` itself, or its immediate children.

    A folder counts as a track folder when it holds at least one export file, so
    a parent directory of many event folders can be passed straight in.
    """
    if not os.path.isdir(path):
        fail(f"not a directory: {path}")
    if any(is_export(name) for name in os.listdir(path)):
        return [path]

    folders = []
    for name in sorted(os.listdir(path)):
        child = os.path.join(path, name)
        if not os.path.isdir(child) or name.startswith("."):
            continue
        if any(is_export(entry) for entry in os.listdir(child)):
            folders.append(child)
    if not folders:
        fail(f"no camera-ready exports found in {path} or its subfolders")
    return folders


def target_name(name, slug, prefix, rename_archive):
    """The convention name for one export file, or None to leave it alone."""
    stem, extension = os.path.splitext(name)
    extension = extension.lower()
    match = EXPORT_NAME.match(stem)
    if not match:
        return None

    middle = match.group("middle")
    part = match.group("part") or ""
    prefix = prefix or match.group("prefix")

    if extension == ".zip":
        # vis26_camera_archive -> vis26_<slug>_camera_archive. An already
        # slugged archive still matches, so --slug can re-slug it.
        if not rename_archive:
            return None
        if middle == ARCHIVE_STEM or middle.endswith(f"_{ARCHIVE_STEM}"):
            return f"{prefix}_{slug}_{ARCHIVE_STEM}{part}{extension}"
        return None

    if extension not in METADATA_EXTENSIONS:
        return None
    # vis26_camera -> vis26_<slug>_metadata. As above, a name that is already
    # slugged matches too: with the same slug it is a no-op, and with --slug it
    # gets the new one.
    if middle == METADATA_STEM or middle.endswith(METADATA_SUFFIX):
        return f"{prefix}_{slug}_{METADATA_SUFFIX}{part}{extension}"
    return None


def plan_folder(folder, slug, prefix, rename_archive):
    """Renames to apply in one folder, plus the export files left unrecognized.

    Returns (renames, unrecognized): (old name, new name) pairs, and the export
    files whose names this script does not know how to map, which are worth
    printing rather than passing over in silence.
    """
    renames = []
    unrecognized = []
    for name in sorted(os.listdir(folder)):
        if not os.path.isfile(os.path.join(folder, name)):
            continue
        new_name = target_name(name, slug, prefix, rename_archive)
        if new_name is None:
            if is_export(name) and not EXPORT_NAME.match(os.path.splitext(name)[0]):
                unrecognized.append(name)
            continue
        if new_name != name:
            renames.append((name, new_name))
    return renames, unrecognized


def apply_renames(folder, renames, dry_run):
    done = 0
    for old_name, new_name in renames:
        source = os.path.join(folder, old_name)
        destination = os.path.join(folder, new_name)
        if os.path.exists(destination):
            print(f"  skipped {old_name}: {new_name} already exists")
            continue
        print(f"  {'would rename' if dry_run else 'renamed'} {old_name} -> {new_name}")
        if not dry_run:
            os.rename(source, destination)
        done += 1
    return done


def main():
    parser = argparse.ArgumentParser(
        description="Rename camera-ready exports to <prefix>_<track>_metadata.<ext>",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "track folders, or a parent holding them "
            "(e.g. 'VIS26 Data Associated Events')"
        ),
    )
    parser.add_argument(
        "--slug",
        help="File-name slug to use instead of one derived from the folder name "
        "(only valid for a single track folder)",
    )
    parser.add_argument(
        "--prefix",
        help="Conference prefix for the new names (default: kept from the "
        "existing file name, e.g. vis26)",
    )
    parser.add_argument(
        "--keep-archive-names",
        action="store_true",
        help="Leave the camera archive zips at their PCS names "
        "(vis26_camera_archive.zip), as Full Papers and Short Papers do",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Report the renames and change nothing",
    )
    args = parser.parse_args()

    folders = []
    for path in args.paths:
        for folder in track_folders(path):
            if folder not in folders:
                folders.append(folder)

    if args.slug and len(folders) > 1:
        fail(
            f"--slug takes a single track folder, but {len(folders)} were found: "
            + ", ".join(os.path.basename(folder) for folder in folders)
        )

    total = 0
    for folder in folders:
        slug = args.slug or slugify(os.path.basename(os.path.abspath(folder)))
        renames, unrecognized = plan_folder(
            folder, slug, args.prefix, not args.keep_archive_names
        )
        if not renames and not unrecognized:
            print(f"{folder}: already named by convention")
            continue
        print(f"{folder}: slug {slug!r}")
        total += apply_renames(folder, renames, args.dry_run)
        for name in unrecognized:
            print(f"  left alone {name}: not a name this script recognizes")

    verb = "would rename" if args.dry_run else "renamed"
    print(f"{verb} {total} file(s) across {len(folders)} folder(s)")


if __name__ == "__main__":
    main()
