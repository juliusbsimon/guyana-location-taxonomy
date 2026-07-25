"""Spatially join Gazetteer points to audited GuyNode boundary polygons.

This implementation uses only the Python standard library. It reads polygon
shapefiles directly, converts Gazetteer WGS 84 coordinates to Web Mercator,
and performs point-in-polygon tests without requiring GDAL or GeoPandas.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from collections import Counter
from pathlib import Path


WEB_MERCATOR_RADIUS = 6378137.0


def read_dbf(path: Path) -> list[dict]:
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 4)[0]
    header_length, record_length = struct.unpack_from("<HH", raw, 8)
    fields = []
    offset = 32
    while raw[offset] != 0x0D:
        descriptor = raw[offset : offset + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode("ascii")
        fields.append((name, chr(descriptor[11]), descriptor[16], descriptor[17]))
        offset += 32

    rows = []
    offset = header_length
    for _ in range(count):
        record = raw[offset : offset + record_length]
        offset += record_length
        if record[:1] == b"*":
            continue
        cursor = 1
        row = {}
        for name, kind, length, decimals in fields:
            value = record[cursor : cursor + length].decode("latin-1").strip()
            cursor += length
            if kind in "NF" and value:
                try:
                    value = float(value) if decimals else int(value)
                except ValueError:
                    pass
            row[name] = value or None
        rows.append(row)
    return rows


def read_polygon_shapefile(path: Path) -> list[dict]:
    raw = path.read_bytes()
    shape_type = struct.unpack_from("<I", raw, 32)[0]
    if shape_type not in (5, 15, 25):
        raise ValueError(f"{path} is not a polygon shapefile (type {shape_type})")

    shapes = []
    offset = 100
    while offset + 8 <= len(raw):
        _, content_words = struct.unpack_from(">II", raw, offset)
        offset += 8
        content_length = content_words * 2
        content = raw[offset : offset + content_length]
        offset += content_length
        if len(content) < 4:
            continue
        record_type = struct.unpack_from("<I", content, 0)[0]
        if record_type == 0:
            shapes.append({"bbox": None, "rings": []})
            continue
        if record_type not in (5, 15, 25):
            raise ValueError(f"Unexpected record shape type {record_type} in {path}")
        bbox = struct.unpack_from("<4d", content, 4)
        part_count, point_count = struct.unpack_from("<2I", content, 36)
        parts = list(struct.unpack_from(f"<{part_count}I", content, 44))
        point_offset = 44 + part_count * 4
        points = [
            struct.unpack_from("<2d", content, point_offset + index * 16)
            for index in range(point_count)
        ]
        rings = []
        for index, start in enumerate(parts):
            end = parts[index + 1] if index + 1 < len(parts) else point_count
            rings.append(points[start:end])
        shapes.append({"bbox": bbox, "rings": rings})
    return shapes


def load_layer(shp_path: Path) -> list[dict]:
    shapes = read_polygon_shapefile(shp_path)
    projection = shp_path.with_suffix(".prj").read_text(
        "utf-8", errors="ignore"
    )
    if projection.lstrip().upper().startswith("GEOGCS["):
        for shape in shapes:
            transformed_rings = [
                [to_web_mercator(longitude, latitude) for longitude, latitude in ring]
                for ring in shape["rings"]
            ]
            shape["rings"] = transformed_rings
            transformed_points = [
                point for ring in transformed_rings for point in ring
            ]
            shape["bbox"] = (
                min(point[0] for point in transformed_points),
                min(point[1] for point in transformed_points),
                max(point[0] for point in transformed_points),
                max(point[1] for point in transformed_points),
            )
    elif "MERCATOR" not in projection.upper():
        raise ValueError(f"Unsupported projection in {shp_path.with_suffix('.prj')}")
    attributes = read_dbf(shp_path.with_suffix(".dbf"))
    if len(shapes) != len(attributes):
        raise ValueError(
            f"Geometry/attribute count mismatch for {shp_path}: "
            f"{len(shapes)} versus {len(attributes)}"
        )
    return [
        {"geometry": geometry, "attributes": attribute}
        for geometry, attribute in zip(shapes, attributes)
    ]


def to_web_mercator(longitude: float, latitude: float) -> tuple[float, float]:
    latitude = max(min(latitude, 85.05112878), -85.05112878)
    x = WEB_MERCATOR_RADIUS * math.radians(longitude)
    y = WEB_MERCATOR_RADIUS * math.log(
        math.tan(math.pi / 4 + math.radians(latitude) / 2)
    )
    return x, y


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    previous_x, previous_y = ring[-1]
    for current_x, current_y in ring:
        crosses = (current_y > y) != (previous_y > y)
        if crosses:
            crossing_x = (
                (previous_x - current_x)
                * (y - current_y)
                / (previous_y - current_y)
                + current_x
            )
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def point_in_shape(x: float, y: float, shape: dict) -> bool:
    bbox = shape["bbox"]
    if bbox is None or not (bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]):
        return False
    # The even-odd rule works for multipart polygons and nested hole rings.
    return sum(point_in_ring(x, y, ring) for ring in shape["rings"]) % 2 == 1


def shape_union_contains(x: float, y: float, shapes: list[dict]) -> bool:
    return any(point_in_shape(x, y, shape) for shape in shapes)


def region_number_from_name(name: str) -> int | None:
    names = {
        "Barima-Waini": 1,
        "Pomeroon-Supenaam": 2,
        "Essequibo Islands-West Demerara": 3,
        "Demerara-Mahaica": 4,
        "Mahaica-Berbice": 5,
        "East Berbice-Corentyne": 6,
        "Cuyuni-Mazaruni": 7,
        "Potaro-Siparuni": 8,
        "Upper Takutu-Upper Essequibo": 9,
        "Upper Demerara-Berbice": 10,
    }
    return names.get(name)


def build_candidates(
    combined_layer: list[dict],
    crosswalk: dict,
    supplemental_paths: dict[str, Path],
) -> list[dict]:
    combined_by_id = {
        str(feature["attributes"]["ID"]): feature for feature in combined_layer
    }
    candidates = []
    for area in crosswalk["local_authorities"]:
        status = area["coverage_status"]
        if status.startswith("combined_"):
            feature = combined_by_id[str(area["boundary_id"])]
            shapes = [feature["geometry"]]
        elif status.startswith("supplemental_"):
            path = supplemental_paths.get(area["geo_order"])
            if path is None:
                continue
            shapes = [feature["geometry"] for feature in load_layer(path)]
        else:
            continue
        candidates.append(
            {
                "geo_order": area["geo_order"],
                "name": area["gecom_name"],
                "authority_type": area["authority_type"],
                "boundary_name": area["boundary_name"],
                "coverage_status": status,
                "confidence": area["confidence"],
                "source_url": area["boundary_source_url"],
                "region_number": int(area["geo_order"].split(".")[0]),
                "shapes": shapes,
            }
        )
    return candidates


def merge(args: argparse.Namespace) -> dict:
    repo = args.repo_root.resolve()
    gazetteer = json.loads(
        (repo / "data/gazetteer-locations.json").read_text("utf-8")
    )
    crosswalk = json.loads(
        (repo / "data/local-authority-boundary-crosswalk.json").read_text("utf-8")
    )
    combined = load_layer(args.combined_shp)
    candidates = build_candidates(
        combined,
        crosswalk,
        {
            "2.07": args.annandale_shp,
            "8.01": args.mahdia_shp,
            "9.01": args.lethem_shp,
        },
    )

    output_rows = []
    region_status_counts = Counter()
    local_status_counts = Counter()
    confidence_counts = Counter()

    for location in gazetteer["locations"]:
        x, y = to_web_mercator(location["longitude"], location["latitude"])

        region_hits = sorted(
            {
                feature["attributes"]["REGION"]
                for feature in combined
                if feature["attributes"].get("REGION")
                and point_in_shape(x, y, feature["geometry"])
            }
        )
        if len(region_hits) == 1:
            region_status = "matched"
            region_name = region_hits[0]
            region_number = region_number_from_name(region_name)
        elif not region_hits:
            region_status = "outside"
            region_name = None
            region_number = None
        else:
            region_status = "overlap"
            region_name = None
            region_number = None

        local_hits = [
            candidate
            for candidate in candidates
            if shape_union_contains(x, y, candidate["shapes"])
        ]
        if len(local_hits) == 1:
            local_status = "matched"
            local = local_hits[0]
            confidence_counts[local["confidence"]] += 1
        elif not local_hits:
            local_status = "unassigned"
            local = None
        else:
            local_status = "overlap"
            local = None

        row = dict(location)
        row.update(
            {
                "region_match_status": region_status,
                "region_number": region_number,
                "region_name": region_name,
                "region_candidates": region_hits if len(region_hits) > 1 else [],
                "local_authority_match_status": local_status,
                "gecom_geo_order": local["geo_order"] if local else None,
                "local_authority_name": local["name"] if local else None,
                "local_authority_type": local["authority_type"] if local else None,
                "boundary_name": local["boundary_name"] if local else None,
                "boundary_coverage_status": (
                    local["coverage_status"] if local else None
                ),
                "boundary_confidence": local["confidence"] if local else None,
                "boundary_source_url": local["source_url"] if local else None,
                "local_authority_candidates": (
                    [
                        {
                            "geo_order": item["geo_order"],
                            "name": item["name"],
                        }
                        for item in local_hits
                    ]
                    if len(local_hits) > 1
                    else []
                ),
            }
        )
        output_rows.append(row)
        region_status_counts[region_status] += 1
        local_status_counts[local_status] += 1

    output_json = repo / "data/gazetteer-with-local-authorities.json"
    output_csv = repo / "data/gazetteer-with-local-authorities.csv"
    qa_json = repo / "data/gazetteer-boundary-merge-quality.json"

    payload = {
        "title": "Guyana National Gazetteer with audited spatial assignments",
        "spatial_reference": "EPSG:4326",
        "record_count": len(output_rows),
        "warning": (
            "Local-authority assignments use audited GuyNode research geometry. "
            "They are not legal or cadastral boundary determinations."
        ),
        "locations": output_rows,
    }
    output_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )

    csv_fields = [
        key
        for key in output_rows[0]
        if key not in {
            "region_candidates",
            "local_authority_candidates",
        }
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(
            {key: row.get(key) for key in csv_fields} for row in output_rows
        )

    quality = {
        "record_count": len(output_rows),
        "local_authority_polygon_candidates": len(candidates),
        "region_match_status": dict(region_status_counts),
        "local_authority_match_status": dict(local_status_counts),
        "matched_confidence": dict(confidence_counts),
        "matched_local_authorities_represented": sorted(
            {
                row["gecom_geo_order"]
                for row in output_rows
                if row["gecom_geo_order"] is not None
            }
        ),
        "unresolved_boundary_geo_orders": [
            area["geo_order"]
            for area in crosswalk["local_authorities"]
            if area["coverage_status"] == "unresolved"
        ],
    }
    qa_json.write_text(
        json.dumps(quality, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    return quality


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--combined-shp", type=Path, required=True)
    parser.add_argument("--annandale-shp", type=Path, required=True)
    parser.add_argument("--mahdia-shp", type=Path, required=True)
    parser.add_argument("--lethem-shp", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(merge(parse_args()), indent=2))
