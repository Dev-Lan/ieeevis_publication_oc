"""Convert PCS camera-ready metadata JSON into the CPS metadata spreadsheet.

Reads a PCS camera-ready export (e.g. vis26c_camera.json) and writes the
columns of the "metadata template" workbook: title, abstract, author names and
affiliations, one row per paper. Output is CSV or XLSX (no third-party
dependencies required).
"""

import argparse
import csv
import json
import os
import re
import zipfile

# Columns before the repeated per-author block, in template order.
LEADING_COLUMNS = [
    "Class",
    "Type",
    "Sequence",
    "Status",
    "Copyright Type",
    "Copyright Line",
    "Article Id (ecopyright id)",
    "Pdf Express",
    "Title",
    "Submitter Name",
    "Submitter Email",
    "Abstract",
    "Keywords",
    "DOI",
    "Chair",
    "Page Number",
    "Page Padding",
    "Is No-Show",
    "Author Change Request (Read Only)",
    "Paper Id",
    "Article Pdf File Name",
    "Article Pdf Export File Name",
    "Article Pdf File Size",
    "Article Pdf File Type",
    "CPS Id",
]

# Repeated once per author, numbered starting at 1.
AUTHOR_COLUMNS = [
    "Author GivenName",
    "Author Surname",
    "Author Email",
    "Author Affiliation",
    "Author ORCID",
]

# PCS names author fields "Author 3 - last", "Author 3 - institution 2", so the
# author and affiliation numbering is read straight off the JSON keys.
AUTHOR_KEY = re.compile(r"^Author (\d+) - (.+)$")
AFFILIATION_KEY = re.compile(r"^institution (\d+)$")


def clean(value):
    """Normalize a PCS field to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def author_field(paper, index, field):
    return clean(paper.get(f"Author {index} - {field}"))


def author_count(paper):
    """Number of authors on a paper (highest author index with a name)."""
    count = 0
    for key, value in paper.items():
        match = AUTHOR_KEY.match(key)
        if match and match.group(2) in ("first", "last") and clean(value):
            count = max(count, int(match.group(1)))
    return count


def affiliation_slots(paper, index):
    """Affiliation numbers PCS recorded for one author, in order."""
    slots = set()
    for key in paper:
        match = AUTHOR_KEY.match(key)
        if not match or int(match.group(1)) != index:
            continue
        affiliation = AFFILIATION_KEY.match(match.group(2))
        if affiliation:
            slots.add(int(affiliation.group(1)))
    return sorted(slots)


def given_name(paper, index):
    """First and middle name.

    The PCS "prefix" field is left out: authors use it for titles such as
    "Dr." or even job titles, which do not belong in a name column.
    """
    parts = [
        author_field(paper, index, "first"),
        author_field(paper, index, "middle"),
    ]
    return " ".join(part for part in parts if part)


def surname(paper, index):
    """Last name, with any generational suffix (e.g. "III")."""
    parts = [
        author_field(paper, index, "last"),
        author_field(paper, index, "suffix"),
    ]
    return " ".join(part for part in parts if part)


def author_email(paper, index, preference):
    """Author email, preferring institution or account address."""
    institution = author_field(paper, index, "institution email 1")
    account = author_field(paper, index, "account email")
    if preference == "account":
        return account or institution
    return institution or account


def author_affiliation(paper, index, detail):
    """Affiliation string for one author, joining multiple affiliations.

    detail controls how much of each affiliation is included:
      institution  institution name only
      department   department, institution
      full         department, institution, city, state/prov, country
    """
    affiliations = []
    for slot in affiliation_slots(paper, index):
        institution = author_field(paper, index, f"institution {slot}")
        if not institution:
            continue
        parts = []
        if detail in ("department", "full"):
            parts.append(author_field(paper, index, f"dept/school/lab {slot}"))
        parts.append(institution)
        if detail == "full":
            parts.append(author_field(paper, index, f"city {slot}"))
            parts.append(author_field(paper, index, f"state/prov {slot}"))
            parts.append(author_field(paper, index, f"country {slot}"))
        affiliations.append(", ".join(part for part in parts if part))
    return "; ".join(affiliations)


def pdf_file_name(paper):
    """The camera-ready PDF file name, taken from the PCS download URL."""
    url = clean(paper.get("The Document"))
    if not url:
        return ""
    path = url.split("?", 1)[0]
    name = os.path.basename(path)
    return name if name.lower().endswith(".pdf") else ""


def build_header(author_slots):
    header = list(LEADING_COLUMNS)
    for index in range(1, author_slots + 1):
        header.extend(f"{column} {index}" for column in AUTHOR_COLUMNS)
    return header


def build_row(paper, header, sequence, args):
    row = {column: "" for column in header}

    row["Class"] = args.paper_class
    row["Type"] = args.paper_type
    if sequence is not None:
        row["Sequence"] = str(sequence)
    row["Title"] = clean(paper.get("Title"))
    row["Submitter Name"] = clean(paper.get("Contact Name"))
    row["Submitter Email"] = clean(paper.get("Contact Email"))
    row["Abstract"] = clean(paper.get("Abstract"))
    row["Keywords"] = clean(paper.get("Keywords"))
    row["Paper Id"] = clean(paper.get("Paper ID"))
    if not args.no_pdf_file_name:
        row["Article Pdf File Name"] = pdf_file_name(paper)

    for index in range(1, author_count(paper) + 1):
        row[f"Author GivenName {index}"] = given_name(paper, index)
        row[f"Author Surname {index}"] = surname(paper, index)
        row[f"Author Email {index}"] = author_email(paper, index, args.email)
        row[f"Author Affiliation {index}"] = author_affiliation(
            paper, index, args.affiliation
        )
        # PCS does not collect ORCIDs, so "Author ORCID N" is left blank.

    return [row[column] for column in header]


def load_papers(path, only_complete):
    with open(path, "r", encoding="utf-8") as infile:
        papers = json.load(infile)

    if not isinstance(papers, list):
        raise SystemExit(f"{path}: expected a JSON list of papers")

    kept = []
    for paper in papers:
        status = clean(paper.get("Status"))
        if status and status.lower() != "complete":
            label = clean(paper.get("Paper ID")) or clean(paper.get("Title"))
            if only_complete:
                print(f"skipping paper {label}: status is '{status}'")
                continue
            print(f"warning: paper {label} has status '{status}'")
        kept.append(paper)
    return kept


def drop_empty_columns(header, rows):
    """Remove columns that are empty on every paper."""
    if not rows:
        return header, rows, []

    keep = [any(row[position] for row in rows) for position in range(len(header))]
    dropped = [name for name, keeping in zip(header, keep) if not keeping]
    header = [name for name, keeping in zip(header, keep) if keeping]
    rows = [
        [value for value, keeping in zip(row, keep) if keeping]
        for row in rows
    ]
    return header, rows, dropped


def convert(papers, args):
    """Build the header and data rows for a list of PCS paper records."""
    # The number of author blocks comes from the paper with the most authors.
    author_slots = max([author_count(paper) for paper in papers], default=0)
    print(f"most authors on a single paper: {author_slots}")

    header = build_header(author_slots)

    rows = []
    for offset, paper in enumerate(papers):
        sequence = None if args.no_sequence else args.start_sequence + offset
        rows.append(build_row(paper, header, sequence, args))

    if not args.keep_empty_columns:
        header, rows, dropped = drop_empty_columns(header, rows)
        if dropped:
            print(f"dropped {len(dropped)} empty columns: {', '.join(dropped)}")

    return header, rows


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)


# --- Minimal XLSX writer (stdlib only) --------------------------------------

# Characters XML 1.0 forbids, which can otherwise corrupt the workbook.
ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Excel's per-cell character limit.
MAX_CELL_LENGTH = 32767


def column_letter(index):
    """1 -> A, 27 -> AA."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def xml_escape(text):
    text = ILLEGAL_XML.sub("", text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def sheet_xml(header, rows, truncated):
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetViews><sheetView workbookViewId="0">',
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>',
        "</sheetView></sheetViews>",
        "<sheetData>",
    ]
    for row_number, values in enumerate([header] + rows, start=1):
        style = ' s="1"' if row_number == 1 else ""
        parts.append(f'<row r="{row_number}">')
        for column_number, value in enumerate(values, start=1):
            value = "" if value is None else str(value)
            if not value:
                continue
            if len(value) > MAX_CELL_LENGTH:
                truncated.append((row_number, column_number))
                value = value[:MAX_CELL_LENGTH]
            reference = f"{column_letter(column_number)}{row_number}"
            parts.append(
                f'<c r="{reference}"{style} t="inlineStr">'
                f"<is><t xml:space=\"preserve\">{xml_escape(value)}</t></is></c>"
            )
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def write_xlsx(path, header, rows, sheet_name):
    truncated = []
    sheet = sheet_xml(header, rows, truncated)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    # Two cell formats: 0 is the default, 1 is the bold header.
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font/><font><b/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)

    for row_number, column_number in truncated:
        print(
            f"warning: truncated cell "
            f"{column_letter(column_number)}{row_number} to {MAX_CELL_LENGTH} characters"
        )


# --- CLI --------------------------------------------------------------------


def output_paths(output, output_format):
    """Resolve the output path(s) and format(s) to write."""
    base, extension = os.path.splitext(output)
    extension = extension.lower()

    if output_format == "auto":
        if extension == ".csv":
            return [(output, "csv")]
        if extension == ".xlsx":
            return [(output, "xlsx")]
        raise SystemExit(
            "cannot infer output format from "
            f"'{output}': use a .csv or .xlsx extension, or pass --format"
        )
    if output_format == "both":
        return [(f"{base}.csv", "csv"), (f"{base}.xlsx", "xlsx")]
    if extension == f".{output_format}":
        return [(output, output_format)]
    return [(f"{base}.{output_format}", output_format)]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert a PCS camera-ready metadata JSON export into the CPS "
            "metadata spreadsheet (title, abstract, authors, affiliations)."
        )
    )
    parser.add_argument("input", help="Input JSON file exported from PCS")
    parser.add_argument(
        "output",
        help="Output spreadsheet; a .csv or .xlsx extension selects the format",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "xlsx", "both"],
        default="auto",
        help="Output format (default: from the output file extension)",
    )
    parser.add_argument(
        "--affiliation",
        choices=["institution", "department", "full"],
        default="institution",
        help="How much of each affiliation to include (default: institution)",
    )
    parser.add_argument(
        "--email",
        choices=["institution", "account"],
        default="institution",
        help="Which author email to prefer (default: institution)",
    )
    parser.add_argument(
        "--keep-empty-columns",
        action="store_true",
        help="Keep template columns that are empty for every paper",
    )
    parser.add_argument(
        "--class",
        dest="paper_class",
        default="",
        help="Value for the Class column (e.g. SB); blank by default",
    )
    parser.add_argument(
        "--type",
        dest="paper_type",
        default="",
        help="Value for the Type column (e.g. AP); blank by default",
    )
    parser.add_argument(
        "--start-sequence",
        type=int,
        default=1,
        help="First value for the Sequence column (default: 1)",
    )
    parser.add_argument(
        "--no-sequence",
        action="store_true",
        help="Leave the Sequence column blank",
    )
    parser.add_argument(
        "--no-pdf-file-name",
        action="store_true",
        help="Leave the Article Pdf File Name column blank",
    )
    parser.add_argument(
        "--only-complete",
        action="store_true",
        help="Skip papers whose PCS status is not 'complete'",
    )
    parser.add_argument(
        "--sheet-name",
        default="Metadata",
        help="Worksheet name for xlsx output (default: Metadata)",
    )
    args = parser.parse_args()

    targets = output_paths(args.output, args.format)
    papers = load_papers(args.input, args.only_complete)
    header, rows = convert(papers, args)

    for path, output_format in targets:
        if output_format == "csv":
            write_csv(path, header, rows)
        else:
            write_xlsx(path, header, rows, args.sheet_name)
        print(f"wrote {len(rows)} papers, {len(header)} columns to {path}")


if __name__ == "__main__":
    main()
