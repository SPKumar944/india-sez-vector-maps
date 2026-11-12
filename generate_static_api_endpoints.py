#!/usr/bin/env python3
"""
Generate Static REST API JSON Endpoints for GitHub Pages Hosting.
Enables instant, zero-latency CORS-enabled API access for external clients,
browser Chrome consoles, mobile apps, and Python/cURL scripts directly from GitHub.

Output structure:
cloud-kitchen/api/v1/
  pincodes.json
  summary.json
  openapi.json
  {pincode}/
    datasets.json
    geojson.json
    dim_localities.json
    dim_housing_density_proxies.json
    fact_demand_generators.json
    fact_competitors.json
    fact_popular_times.json
    log_mobility.json
"""

import os
import json
import sqlite3
import pandas as pd
from api.database import PINCODE_REGISTRY, TABLE_METADATA, get_available_pincodes, get_pincode_datasets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BASE_DIR, "cloud-kitchen", "api", "v1")
os.makedirs(API_DIR, exist_ok=True)

GITHUB_PAGES_BASE = "https://spkumar944.github.io/india-sez-vector-maps/cloud-kitchen/api/v1"

def generate_static_api():
    print(f"Generating Static REST API JSON endpoints in: {API_DIR}")

    # 1. pincodes.json
    pincodes_meta = get_available_pincodes()
    for item in pincodes_meta:
        pin = item["pincode"]
        item["api_urls"] = {
            "datasets_discovery": f"{GITHUB_PAGES_BASE}/{pin}/datasets.json",
            "geojson": f"{GITHUB_PAGES_BASE}/{pin}/geojson.json",
            "competitors": f"{GITHUB_PAGES_BASE}/{pin}/fact_competitors.json",
            "demand_generators": f"{GITHUB_PAGES_BASE}/{pin}/fact_demand_generators.json",
            "housing_proxies": f"{GITHUB_PAGES_BASE}/{pin}/dim_housing_density_proxies.json",
            "localities": f"{GITHUB_PAGES_BASE}/{pin}/dim_localities.json",
            "popular_times": f"{GITHUB_PAGES_BASE}/{pin}/fact_popular_times.json",
            "mobility": f"{GITHUB_PAGES_BASE}/{pin}/log_mobility.json",
            "excel_workbook": f"https://github.com/SPKumar944/india-sez-vector-maps/raw/main/data/{PINCODE_REGISTRY[pin]['folder']}/{PINCODE_REGISTRY[pin]['name'].replace(' ', '_')}_{pin}_Cloud_Kitchen_Master_Dataset.xlsx"
        }

    with open(os.path.join(API_DIR, "pincodes.json"), "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "api_version": "2.0.0",
            "provider": "Cloud Kitchen Market Geospatial Intelligence API",
            "base_url": GITHUB_PAGES_BASE,
            "total_pincodes": len(pincodes_meta),
            "pincodes": pincodes_meta
        }, f, indent=2)
    print(" -> Generated api/v1/pincodes.json")

    # 2. summary.json
    master_db_path = os.path.join(BASE_DIR, "data", "master_cloud_kitchen.sqlite")
    conn = sqlite3.connect(master_db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_pincode_summary")
    cols = [d[0] for d in cur.description]
    summary_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    with open(os.path.join(API_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "api_version": "2.0.0",
            "total_markets_analyzed": len(summary_rows),
            "markets": summary_rows
        }, f, indent=2)
    print(" -> Generated api/v1/summary.json")

    # 3. For each pincode, generate dataset files and geojson
    for pin, reg in PINCODE_REGISTRY.items():
        pin_dir = os.path.join(API_DIR, pin)
        os.makedirs(pin_dir, exist_ok=True)
        data_pdir = os.path.join(BASE_DIR, "data", reg["folder"])

        # datasets.json (discovery)
        datasets = get_pincode_datasets(pin)
        for d in datasets:
            dname = d["dataset_name"]
            d["static_api_url"] = f"{GITHUB_PAGES_BASE}/{pin}/{dname}.json"
            d["raw_csv_url"] = f"https://github.com/SPKumar944/india-sez-vector-maps/raw/main/data/{reg['folder']}/{dname}.csv"

        with open(os.path.join(pin_dir, "datasets.json"), "w", encoding="utf-8") as f:
            json.dump({
                "status": "success",
                "pincode": pin,
                "name": reg["name"],
                "total_datasets": len(datasets),
                "datasets": datasets
            }, f, indent=2)

        # geojson.json
        # find matching geojson in data folder
        geo_name = f"{reg['name'].lower().replace(' ', '_')}_{pin}_spatial_layers.geojson"
        geo_path = os.path.join(data_pdir, geo_name)
        if not os.path.exists(geo_path):
            # check alternative name
            for alt in os.listdir(data_pdir):
                if alt.endswith("spatial_layers.geojson"):
                    geo_path = os.path.join(data_pdir, alt)
                    break
        
        if os.path.exists(geo_path):
            with open(geo_path, "r", encoding="utf-8") as gf:
                geo_data = json.load(gf)
            with open(os.path.join(pin_dir, "geojson.json"), "w", encoding="utf-8") as out_gf:
                json.dump(geo_data, out_gf)
            print(f" -> Generated api/v1/{pin}/geojson.json ({len(geo_data.get('features', []))} features)")

        # individual datasets
        for tbl, meta in TABLE_METADATA.items():
            csv_path = os.path.join(data_pdir, f"{tbl}.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                # sanitize any NaN to None/null
                records = df.replace({float('nan'): None}).to_dict(orient="records")
                
                out_json = os.path.join(pin_dir, f"{tbl}.json")
                with open(out_json, "w", encoding="utf-8") as out_f:
                    json.dump({
                        "status": "success",
                        "pincode": pin,
                        "pincode_name": reg["name"],
                        "dataset_name": tbl,
                        "title": meta["title"],
                        "description": meta["description"],
                        "primary_key": meta["primary_key"],
                        "spatial_coordinates": {"lat": meta["lat_col"], "lon": meta["lon_col"]},
                        "total_records": len(records),
                        "columns": list(df.columns),
                        "records": records
                    }, out_f)
                print(f" -> Generated api/v1/{pin}/{tbl}.json ({len(records)} records)")

    # 4. OpenAPI / Swagger 3.0 specification
    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Cloud Kitchen Market Geospatial Intelligence REST API",
            "version": "2.0.0",
            "description": "High-density geospatial, F&B competitor, housing proxy, and OSRM mobility intelligence across Bangalore prime commercial pincodes (560034, 560041, 560038, 560102). Hosted publicly via GitHub Pages with CORS enabled.",
            "contact": {
                "name": "Cloud Kitchen Geospatial Engineering Team",
                "url": "https://github.com/SPKumar944/india-sez-vector-maps"
            }
        },
        "servers": [
            {
                "url": "https://spkumar944.github.io/india-sez-vector-maps/cloud-kitchen/api/v1",
                "description": "Public Static REST API (GitHub Pages - CORS Enabled)"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Local Dynamic FastAPI Server (with SQL Filtering & CRUD Write)"
            }
        ],
        "paths": {
            "/pincodes.json": {
                "get": {
                    "summary": "List All Analyzed Pincodes",
                    "description": "Returns all 4 analyzed market corridors with centroids, bounding boxes, entity counts, feasibility scores, and recommended kitchen hub coordinates.",
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/summary.json": {
                "get": {
                    "summary": "Cross-Market Overview & GMV Analytics",
                    "description": "Aggregated market saturation, order counts, and estimated GMV across all analyzed pincodes.",
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/datasets.json": {
                "get": {
                    "summary": "Discover Datasets for a Specific Pincode",
                    "description": "Returns metadata, schema definitions, column data types, row counts, and endpoint URLs for all 6 tables.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/fact_competitors.json": {
                "get": {
                    "summary": "F&B Competitor Landscape",
                    "description": "Detailed directory of restaurants, cafes, cloud kitchens, and QSRs with ratings, pricing, order estimates, and flags.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/fact_demand_generators.json": {
                "get": {
                    "summary": "Demand Generators (POIs)",
                    "description": "Corporate tech parks, universities, coaching centers, hospitals, and transit hubs driving delivery order surges.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/dim_housing_density_proxies.json": {
                "get": {
                    "summary": "Residential & Housing Density Proxies",
                    "description": "Gated communities, apartments, PGs, and settlements with unit counts, resident estimates, and gate drop friction.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/dim_localities.json": {
                "get": {
                    "summary": "Localities & Electoral Micro-Zones",
                    "description": "Macro sub-localities and official electoral polling sections with voter age cohorts and affluence index.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/fact_popular_times.json": {
                "get": {
                    "summary": "Popular Times & 24h Busyness Curves",
                    "description": "Hourly weekday vs weekend footfall curves and midnight delivery surge opportunities.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/log_mobility.json": {
                "get": {
                    "summary": "OSRM Mobility & Origin-Destination Matrix",
                    "description": "Real road distance, peak lunch/dinner travel times, congestion multipliers, and delivery SLA compliance.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            },
            "/{pincode}/geojson.json": {
                "get": {
                    "summary": "Master GeoJSON Spatial Layers",
                    "description": "Complete FeatureCollection of all POIs, housing complexes, competitors, and dispatch route linestrings.",
                    "parameters": [{"name": "pincode", "in": "path", "required": True, "schema": {"type": "string", "example": "560034"}}],
                    "responses": {"200": {"description": "Successful response"}}
                }
            }
        }
    }

    with open(os.path.join(API_DIR, "openapi.json"), "w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, indent=2)
    print(" -> Generated api/v1/openapi.json")

    print(f"\nSUCCESS: All static REST API endpoints generated under {API_DIR}")

if __name__ == "__main__":
    generate_static_api()
