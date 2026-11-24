"""Deduplicate locally saved ICSD result tables by record and composition."""

import argparse
from collections import defaultdict
import csv
from pathlib import Path
import re
import sys

from pymatgen.core import Composition, Element

COLUMNS = (
    "Coll. Code", "HMS", "Struct. Form.", "Struct. Type", "Title", "Reference",
    "Cell Parameter", "Temperature", "Pressure", "Wyckoff Sequence",
)
REQUIRED = {"Coll. Code", "Struct. Form."}
FORMULA = re.compile(r"(?:[A-Z][a-z]?|\(|\)|[0-9]+(?:\.[0-9]+)?)+")
PRECISION = 12
EXPORT_HEADERS = {
    "CollectionCode": "Coll. Code",
    "StructuredFormula": "Struct. Form.",
    "StructureType": "Struct. Type",
    "CellParameter": "Cell Parameter",
    "WyckoffSequence": "Wyckoff Sequence",
}


def read_tables(path):
    if path.suffix.lower() in {".html", ".htm"}:
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise ValueError("To read saved HTML, install beautifulsoup4 or use CSV/TSV.") from exc
        document = BeautifulSoup(path.read_bytes(), "html.parser")
        for table in document.find_all("table"):
            header = table.find("thead")
            if header is None:
                continue
            names = [cell.get_text(" ", strip=True) for cell in header.find_all("th")]
            if REQUIRED <= set(names):
                rows = [names]
                for body in table.find_all("tbody", recursive=False):
                    rows.extend(
                        [cell.get_text(" ", strip=True) for cell in row.find_all("td", recursive=False)]
                        for row in body.find_all("tr", recursive=False)
                        if row.find("td", recursive=False)
                    )
                return rows
        raise ValueError(f"{path}: no ICSD results table found")
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream, delimiter=delimiter))


def read_records(paths):
    records = {}
    for path in paths:
        rows = read_tables(path)
        if not rows:
            raise ValueError(f"{path}: missing table header")
        names = [EXPORT_HEADERS.get(name.strip(), name.strip()) for name in rows[0]]
        if not REQUIRED <= set(names):
            raise ValueError(f"{path}: expected headers Coll. Code and Struct. Form.")
        for line, fields in enumerate(rows[1:], 2):
            if not any(field.strip() for field in fields):
                continue
            if len(fields) != len(names):
                raise ValueError(f"{path}, row {line}: table row does not match its header")
            raw = dict(zip(names, fields))
            row = {name: " ".join(raw.get(name, "").split()) for name in COLUMNS}
            code = row["Coll. Code"]
            if not code.isascii() or not code.isdecimal():
                raise ValueError(f"{path}, row {line}: invalid collection code {code!r}")
            code = row["Coll. Code"] = str(int(code))
            existing = records.setdefault(code, row)
            for name, value in row.items():
                if existing[name] and value and existing[name] != value:
                    raise ValueError(f"{path}, row {line}: conflicting {name} for ICSD-{code}")
                if value:
                    existing[name] = value
    return [records[code] for code in sorted(records, key=int)]


def composition_key(raw, elements):
    formula = "".join(raw.split())
    if not FORMULA.fullmatch(formula):
        raise ValueError("formula contains unsupported notation")
    composition = Composition(formula, strict=True)
    symbols = set(composition.get_el_amt_dict())
    if not symbols or not symbols <= set(elements):
        raise ValueError("formula contains elements outside the requested system")
    if len(symbols) == 1:
        return None  # The elemental vertices are outside the four-system comparison.
    return tuple(round(composition.get_atomic_fraction(e), PRECISION) for e in elements)


def write_table(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elements", nargs=3, metavar="ELEMENT")
    parser.add_argument("inputs", nargs="+", type=Path, help="Saved ICSD HTML, CSV or TSV tables")
    parser.add_argument("--output-prefix", required=True, type=Path)
    args = parser.parse_args()
    try:
        elements = [Element(symbol).symbol for symbol in args.elements]
        if len(set(elements)) != 3:
            raise ValueError("Provide three distinct elements")
        records = read_records(args.inputs)
        groups = defaultdict(list)
        unresolved = 0
        for row in records:
            try:
                key = composition_key(row["Struct. Form."], elements)
            except ValueError as exc:
                unresolved += 1
                print(f"ICSD-{row['Coll. Code']}: {exc}", file=sys.stderr)
                continue
            if key is not None:
                groups[key].append(row["Coll. Code"])
        records_path = args.output_prefix.with_name(args.output_prefix.name + "-records.csv")
        compositions_path = args.output_prefix.with_name(args.output_prefix.name + "-compositions.csv")
        if {records_path.resolve(), compositions_path.resolve()} & {p.resolve() for p in args.inputs}:
            raise ValueError("Output would overwrite an input table")
        write_table(records_path, COLUMNS, ([row[name] for name in COLUMNS] for row in records))
        write_table(
            compositions_path, [*(f"{e} atomic fraction" for e in elements), "Coll. Codes"],
            ([*key, " ".join(codes)] for key, codes in sorted(groups.items())),
        )
        print(f"{len(records)} ICSD records, {len(groups)} distinct binary/ternary compositions"
              f" ({unresolved} records require formula review)")
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
