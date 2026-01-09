import csv
import argparse
from datetime import datetime

CONF_NAME = "VIS 2026"
CONF_DATE = "November 9, 2026"
DEADLINE_TIME = "11:59pm (23:59) Anywhere on Earth (AoE)"


def writerow(writer, row):
    while len(row) < 3:
        row.append(None)
    writer.writerow(row)


def date_to_str(d):
    try:
        return datetime.strptime(d, "%m/%d/%Y").strftime("%B %d, %Y")
    except:
        return d


def convert(args):
    with open(args.input, "r") as infile:
        with open(args.output, "w") as outfile:
            reader = csv.DictReader(infile)
            writer = csv.writer(outfile)

            writerow(writer, ["conference", CONF_NAME])

            for row in reader:
                writerow(writer, [])

                writerow(
                    writer, ["track name", row["Track name (e.g., VDS, Vis4DH, etc.)"]]
                )
                writerow(
                    writer,
                    [
                        "url",
                        row["Track URL (e.g., http://ieeevis.org/year/2021/welcome)"],
                    ],
                )

                chair_names = row[
                    "Chair Names (comma-separated, e.g., Jon Snow, Arya Stark)"
                ].split(",")
                chair_emails = row[
                    "Chair Emails (comma-separated, e.g., jon@stark.net, arya@stark.net)"
                ].split(",")

                for chair in zip(chair_names, chair_emails):
                    writerow(writer, ["chair", chair[0].strip(), chair[1].strip()])

                writerow(
                    writer,
                    [
                        "chair email",
                        row[
                            "Overall Chairs email (e.g., papers@ieeevis.org, panels@ieeevis.org)"
                        ],
                    ],
                )
                writerow(
                    writer,
                    [
                        "bounce email",
                        row[
                            "Overall Chairs email (e.g., papers@ieeevis.org, panels@ieeevis.org)"
                        ],
                    ],
                )

                deadlines = [
                    ["early deadline", row["Early deadline (e.g., abstract)"]],
                    ["submission deadline", row["Submission deadline"]],
                    ["review deadline", row["Review deadline"]],
                    ["camera deadline", row["Camera-ready deadline"]],
                    ["conference date", CONF_DATE],
                ]

                for d in deadlines:
                    if d[1]:
                        d[1] = date_to_str(d[1])
                        d.append(DEADLINE_TIME)
                        writerow(writer, d)
                    else:
                        d.append(None)
                        writerow(writer, d)

                writerow(
                    writer,
                    [
                        "primary",
                        row["Primary role name (e.g., Primary Reviewer, Coordinator)"]
                        or "Primary Reviewer",
                    ],
                )
                writerow(
                    writer,
                    [
                        "secondary",
                        row[
                            "Secondary role name (e.g., Secondary Reviewer, Committee Member)"
                        ]
                        or "Secondary Reviewer",
                    ],
                )
                writerow(
                    writer,
                    [
                        "reviewer",
                        row["Reviewer role name (e.g., Reviewer, External)"]
                        or "Reviewer",
                    ],
                )

                writerow(writer, [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input CSV file from Google Form responses")
    parser.add_argument("output", help="Output CSV file in PCS format")
    args = parser.parse_args()

    print(args)
    convert(args)
