#!/usr/bin/env python3
"""
India Industrial Land Bank (IILB) Vector Extractor
Queries the underlying GeoServer WMS/GetFeatureInfo service on indiaindustriallandbank.gov.in
and exports vector geometries (MultiPolygon/Polygon) and full attribute tables in standard GeoJSON format.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import argparse

IILB_WMS_URL = "https://indiaindustriallandbank.gov.in/gislyrwms"

LAYERS = {
    "park": "cite:park_boundary_iis1",
    "plot": "cite:plot_boundary_iis",
    "cpse": "cite:cpse_land_bank",
    "bulk": "cite:bulk_land_iis",
    "airport": "cite:airport_ai",
    "nh": "cite:nh_ai",
    "ports": "cite:major_ports",
    "rail": "cite:railway_track",
    "station": "cite:railway_station",
    "power": "cite:transmission_lines",
    "substation": "cite:substation",
    "gas": "cite:gas_pipeline",
    "water": "cite:water_pipeline"
}

def extract_vector(minx, miny, maxx, maxy, layer="park", feature_count=50, buffer=10):
    layer_name = LAYERS.get(layer, layer)
    
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer_name,
        "QUERY_LAYERS": layer_name,
        "BBOX": f"{minx},{miny},{maxx},{maxy}",
        "WIDTH": "101",
        "HEIGHT": "101",
        "X": "50",
        "Y": "50",
        "SRS": "EPSG:4326",
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": str(feature_count),
        "BUFFER": str(buffer)
    }

    req_url = IILB_WMS_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(req_url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://indiaindustriallandbank.gov.in/exploreParks"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"Error querying IILB service: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Extract vector boundary data from IILB")
    parser.add_argument("--bbox", required=True, help="Bounding box as minx,miny,maxx,maxy (lon,lat in WGS84)")
    parser.add_argument("--layer", default="park", choices=list(LAYERS.keys()), help="Layer type to extract")
    parser.add_argument("--output", default="iilb_extracted.geojson", help="Output GeoJSON filepath")
    parser.add_argument("--count", type=int, default=50, help="Max feature count")

    args = parser.parse_args()
    minx, miny, maxx, maxy = map(float, args.bbox.split(","))

    print(f"Extracting layer '{args.layer}' for BBOX: [{minx}, {miny}, {maxx}, {maxy}]...")
    geojson = extract_vector(minx, miny, maxx, maxy, layer=args.layer, feature_count=args.count)

    if geojson and "features" in geojson:
        count = len(geojson["features"])
        print(f"Found {count} vector features.")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)
        print(f"Saved vector map to: {args.output}")
    else:
        print("No features returned or extraction failed.")

if __name__ == "__main__":
    main()
