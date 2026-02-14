import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def _parse_decimal(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _parse_date_iso(date_str: str) -> str | None:
    date_str = (date_str or "").strip()
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def convert_tsv_to_json(input_path: Path, output_path: Path) -> int:
    with input_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("TSV file has no header row.")

        out = []
        for index, row in enumerate(reader, start=1):
            def get(key: str) -> str:
                return (row.get(key) or "").strip()

            geographe_raw = get("Le Géographe")
            naturaliste_raw = get("Le Naturaliste")
            casuarina_raw = get("Le Casuarina")
            flinders_raw = get("Flinders")

            lat_south_decimal = _parse_decimal(get("Latitude Sud décimale"))
            lon_east_greenwich_decimal = _parse_decimal(get("Longitude Est (Greenwich) décimale"))

            lat = lat_south_decimal
            if lat == 0:
                lat = 0.0

            lon = lon_east_greenwich_decimal

            interpolation_raw = get("Interpolation")

            out.append(
                {
                    "id": index * 100,
                    "dateISO": _parse_date_iso(get("Date")),
                    "story": get("Story"),
                    "histoire": get("Histoire"),
                    "geographe": geographe_raw.upper() == "X",
                    "naturaliste": naturaliste_raw.upper() == "X",
                    "casuarina": casuarina_raw.upper() == "X",
                    "flinders": flinders_raw.upper() == "X",
                    "latitudeSouthDegrees": get("Latitude Sud degrés"),
                    "longitudeEastParisDegrees": get("Longitude Est (Paris) degrés"),
                    "lat": lat,
                    "lon": lon,
                    "interpolation": interpolation_raw.upper() == "X",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(out)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    app_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Convertit 'Historique Baudin.tsv' en timeline JSON utilisable par le site.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=repo_root / "Parcours et Chronologie" / "Historique Baudin.tsv",
        help="Chemin vers le fichier TSV source.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=app_root / "data" / "timeline_baudin.json",
        help="Chemin vers le fichier JSON de sortie.",
    )
    args = parser.parse_args()

    count = convert_tsv_to_json(args.input, args.output)
    print(f"OK: {args.output} ({count} entrées)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
