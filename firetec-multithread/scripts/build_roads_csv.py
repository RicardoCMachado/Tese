"""
Build data/roads_portugal.csv from the Geofabrik Portugal GeoPackage.

Input:
    data/portugal.gpkg

Output:
    data/roads_portugal.csv

The runtime app reads only the generated CSV and does not call external APIs.
"""
import argparse
import csv
import math
import sqlite3
import struct
from pathlib import Path


DEFAULT_HIGHWAYS = "motorway,trunk,primary,secondary,tertiary"
GPKG_ROADS_TABLE = "gis_osm_roads_free"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build local roads CSV from Geofabrik portugal.gpkg."
    )
    parser.add_argument(
        "--input",
        default="data/portugal.gpkg",
        help="Path to Geofabrik Portugal GeoPackage"
    )
    parser.add_argument(
        "--output",
        default="data/roads_portugal.csv",
        help="Output CSV used by FireTec"
    )
    parser.add_argument(
        "--highways",
        default=DEFAULT_HIGHWAYS,
        help="Comma-separated fclass values to include"
    )
    parser.add_argument(
        "--max-segment-meters",
        type=float,
        default=250,
        help="Interpolate points along long road segments"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Debug only: process at most N road rows"
    )
    return parser.parse_args()


def iter_road_rows(input_path: Path, highways: set, limit: int = None):
    placeholders = ",".join("?" for _ in highways)
    sql = f"""
        SELECT osm_id, fclass, name, ref, geom
        FROM {GPKG_ROADS_TABLE}
        WHERE fclass IN ({placeholders})
          AND (
            (ref IS NOT NULL AND ref <> '')
            OR (name IS NOT NULL AND name <> '')
          )
    """
    params = list(highways)
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    connection = sqlite3.connect(input_path)
    try:
        cursor = connection.cursor()
        for row in cursor.execute(sql, params):
            yield row
    finally:
        connection.close()


def decode_gpkg_linestring(blob: bytes):
    """
    Decode a GeoPackage LINESTRING geometry into [(lat, lon), ...].

    Geofabrik stores roads as GeoPackage binary geometries with WKB payloads.
    This decoder handles the LINESTRING payload used by gis_osm_roads_free.
    """
    if not blob or blob[:2] != b"GP":
        return []

    flags = blob[3]
    header_byte_order = "<" if flags & 1 else ">"
    envelope_indicator = (flags >> 1) & 0b111
    envelope_size = {
        0: 0,
        1: 32,
        2: 48,
        3: 48,
        4: 64,
    }.get(envelope_indicator, 0)

    offset = 8 + envelope_size
    if len(blob) <= offset + 9:
        return []

    wkb_byte_order = "<" if blob[offset] == 1 else ">"
    offset += 1

    geom_type = struct.unpack_from(wkb_byte_order + "I", blob, offset)[0]
    offset += 4

    # Strip possible Z/M flag ranges if present; Geofabrik roads are 2D.
    base_geom_type = geom_type % 1000
    if base_geom_type != 2:
        return []

    point_count = struct.unpack_from(wkb_byte_order + "I", blob, offset)[0]
    offset += 4

    points = []
    for _ in range(point_count):
        if len(blob) < offset + 16:
            break
        lon, lat = struct.unpack_from(wkb_byte_order + "dd", blob, offset)
        offset += 16
        points.append((lat, lon))

    # Keep this variable referenced so linters do not flag it as accidental.
    _ = header_byte_order
    return points


def densify_points(points, max_segment_meters: float):
    if len(points) < 2:
        return points

    dense = [points[0]]
    for start, end in zip(points, points[1:]):
        distance = haversine_meters(start[0], start[1], end[0], end[1])
        segment_count = max(1, math.ceil(distance / max_segment_meters))
        for index in range(1, segment_count):
            fraction = index / segment_count
            dense.append((
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            ))
        dense.append(end)

    return dense


def haversine_meters(lat1, lon1, lat2, lon2):
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) *
        math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_roads_csv(args):
    input_path = Path(args.input)
    output_path = Path(args.output)
    highways = {item.strip() for item in args.highways.split(",") if item.strip()}

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    road_count = 0
    point_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["road_id", "ref", "name", "highway", "latitude", "longitude"]
        )
        writer.writeheader()

        for osm_id, highway, name, ref, geom in iter_road_rows(
            input_path,
            highways,
            args.limit
        ):
            points = decode_gpkg_linestring(geom)
            if not points:
                continue

            points = densify_points(points, args.max_segment_meters)
            for lat, lon in points:
                writer.writerow({
                    "road_id": osm_id,
                    "ref": ref or "",
                    "name": name or "",
                    "highway": highway,
                    "latitude": f"{lat:.7f}",
                    "longitude": f"{lon:.7f}",
                })
                point_count += 1

            road_count += 1
            if road_count % 10000 == 0:
                print(f"Processed {road_count} roads, {point_count} points...")

    print(f"Done. Roads: {road_count}. Points: {point_count}.")
    print(f"Wrote: {output_path}")


def main():
    build_roads_csv(parse_args())


if __name__ == "__main__":
    main()
