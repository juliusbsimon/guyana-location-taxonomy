"""Download and normalize the Guyana National Gazetteer ArcGIS layer."""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path


SERVICE_URL = (
    "https://services3.arcgis.com/9QdN8AGqFexQGuDv/arcgis/rest/services/"
    "Guyana_National_Gazetteer/FeatureServer/0"
)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PAGE_SIZE = 1000

FIELDS = [
    "name",
    "feature",
    "location",
    "regional_c",
    "map_reference",
    "dms_latitude",
    "dms_longitude",
    "utm_northing",
    "utm_easting",
    "object_id",
    "latitude",
    "longitude",
]


def request_json(path: str, params: dict[str, object]) -> dict:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{SERVICE_URL}/{path}?{query}", timeout=60) as response:
        return json.load(response)


def fetch_features() -> list[dict]:
    count_response = request_json(
        "query", {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    )
    expected_count = int(count_response["count"])
    features: list[dict] = []

    for offset in range(0, expected_count, PAGE_SIZE):
        page = request_json(
            "query",
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "orderByFields": "ObjectId",
                "f": "json",
            },
        )
        if "error" in page:
            raise RuntimeError(page["error"])
        features.extend(page.get("features", []))

    if len(features) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} features but downloaded {len(features)}"
        )
    return features


def normalize(feature: dict) -> dict:
    attributes = feature.get("attributes") or {}
    geometry = feature.get("geometry") or {}
    return {
        "name": attributes.get("NAME"),
        "feature": attributes.get("FEATURE"),
        "location": attributes.get("LOCATION"),
        "regional_c": attributes.get("REGIONAL_C"),
        "map_reference": attributes.get("MAP_REFERE"),
        "dms_latitude": attributes.get("DMS_Lat"),
        "dms_longitude": attributes.get("DMS_Long"),
        "utm_northing": attributes.get("UTM_N"),
        "utm_easting": attributes.get("UTM_E"),
        "object_id": attributes.get("ObjectId"),
        "latitude": geometry.get("y"),
        "longitude": geometry.get("x"),
    }


def main() -> None:
    records = [normalize(feature) for feature in fetch_features()]
    records.sort(key=lambda item: (item["object_id"] is None, item["object_id"] or 0))

    missing_coordinates = sum(
        row["latitude"] is None or row["longitude"] is None for row in records
    )
    invalid_coordinates = sum(
        row["latitude"] is not None
        and row["longitude"] is not None
        and not (-90 <= row["latitude"] <= 90 and -180 <= row["longitude"] <= 180)
        for row in records
    )
    if invalid_coordinates:
        raise RuntimeError(f"Found {invalid_coordinates} invalid coordinate pairs")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "gazetteer-locations.json"
    csv_path = DATA_DIR / "gazetteer-locations.csv"

    payload = {
        "source": SERVICE_URL,
        "spatial_reference": "EPSG:4326",
        "record_count": len(records),
        "missing_coordinate_count": missing_coordinates,
        "locations": records,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(
        json.dumps(
            {
                "records": len(records),
                "missing_coordinates": missing_coordinates,
                "json": str(json_path),
                "csv": str(csv_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
