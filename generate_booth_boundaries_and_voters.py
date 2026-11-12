#!/usr/bin/env python3
"""
generate_booth_boundaries_and_voters.py
Extracts booth boundaries (catchment area polygons) clipped strictly to official BBMP Wards
and generates per-booth voter records and search indices for AC-160 Shantinagar.
"""

import os
import json
import re
import pandas as pd
import numpy as np
import shapely.geometry as sg
import shapely.ops as so

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=== Generating Polling Booth Boundaries & Corresponding Voters ===")
    
    # 1. Load Wards GeoJSON
    wards_path = os.path.join(BASE_DIR, "data", "shantinagar_wards.geojson")
    with open(wards_path, 'r', encoding='utf-8') as f:
        wards_fc = json.load(f)
    print(f"Loaded {len(wards_fc['features'])} BBMP Wards.")

    # 2. Load Electoral Summary Data
    electoral_path = os.path.join(BASE_DIR, "data", "shantinagar_electoral_geo.json")
    with open(electoral_path, 'r', encoding='utf-8') as f:
        electoral_data = json.load(f)
    booths = electoral_data['booths']
    print(f"Loaded {len(booths)} polling booths.")

    # 3. Load Master Electoral Roll Excel for Voters Extraction
    excel_path = os.path.join(BASE_DIR, "Shantinagar_Master_Electoral_Roll.xlsx")
    print(f"Reading {excel_path} for detailed voter records...")
    df_voters = pd.read_excel(excel_path)
    df_voters['Part No'] = pd.to_numeric(df_voters['Part No'], errors='coerce').fillna(0).astype(int)
    df_voters['Serial No'] = pd.to_numeric(df_voters['Serial No'], errors='coerce').fillna(0).astype(int)
    df_voters['Age'] = pd.to_numeric(df_voters['Age'], errors='coerce').fillna(0).astype(int)
    df_voters['Gender'] = df_voters['Gender'].astype(str).str.strip().str.title()
    print(f"Loaded {len(df_voters):,} voters across {df_voters['Part No'].nunique()} parts.")

    # 4. Create directory for per-part voter JSON files
    voters_dir = os.path.join(BASE_DIR, "data", "booth_voters")
    os.makedirs(voters_dir, exist_ok=True)

    # 5. Extract per-part voters
    print("Exporting per-booth voter records...")
    voter_columns = ['Serial No', 'Voter Name', 'Relation Type', 'Relation Name', 'House No', 'Section / Street Name', 'Voter ID (EPIC)', 'Age', 'Gender']
    
    for part_no, group in df_voters.groupby('Part No'):
        if part_no == 0:
            continue
        sorted_group = group.sort_values(by='Serial No')
        records = []
        for _, row in sorted_group.iterrows():
            records.append({
                "s": int(row['Serial No']),
                "n": str(row['Voter Name']),
                "rt": str(row['Relation Type']),
                "rn": str(row['Relation Name']),
                "h": str(row['House No']) if str(row['House No']) != 'nan' else '',
                "sec": str(row['Section / Street Name']) if str(row['Section / Street Name']) != 'nan' else '',
                "id": str(row['Voter ID (EPIC)']) if str(row['Voter ID (EPIC)']) != 'nan' else '',
                "a": int(row['Age']),
                "g": str(row['Gender'])
            })
        part_file = os.path.join(voters_dir, f"part_{part_no}.json")
        with open(part_file, 'w', encoding='utf-8') as pf:
            json.dump(records, pf)
            
    print(f"Exported voter JSON files for all parts in {voters_dir}.")

    # 6. Generate Booth Boundary Polygons clipped to Ward Geometry
    print("Computing Booth Catchment Polygons per Ward...")
    booth_features = []

    # Map booths by ward
    booths_by_ward = {}
    for b in booths:
        wn = b['ward_no']
        if wn not in booths_by_ward:
            booths_by_ward[wn] = []
        booths_by_ward[wn].append(b)

    for ward_feat in wards_fc['features']:
        ward_props = ward_feat['properties']
        ward_no = int(ward_props['WARD_NO'])
        ward_geom = sg.shape(ward_feat['geometry'])
        
        # Ensure valid geometry
        if not ward_geom.is_valid:
            ward_geom = ward_geom.buffer(0)

        ward_booths = booths_by_ward.get(ward_no, [])
        if not ward_booths:
            continue

        print(f"Processing Ward {ward_no} ({ward_props['WARD_NAME']}) with {len(ward_booths)} booths...")

        if len(ward_booths) == 1:
            # Entire ward is single booth catchment
            b = ward_booths[0]
            geom_json = sg.mapping(ward_geom)
            centroid = [round(ward_geom.centroid.x, 5), round(ward_geom.centroid.y, 5)]
            minx, miny, maxx, maxy = ward_geom.bounds
            feat = {
                "type": "Feature",
                "geometry": geom_json,
                "properties": {
                    **b,
                    "centroid": centroid,
                    "bbox": [[round(minx, 5), round(miny, 5)], [round(maxx, 5), round(maxy, 5)]]
                }
            }
            booth_features.append(feat)
            continue

        # Create booth points with micro-offset if identical coordinates
        points = []
        booth_map = []
        seen_coords = set()

        for idx, b in enumerate(ward_booths):
            lng, lat = b['lng'], b['lat']
            coord_key = (round(lng, 4), round(lat, 4))
            if coord_key in seen_coords:
                # Add micro-offset (approx 35-50 meters) so Voronoi splits cleanly
                offset_x = ((b['part_no'] * 17) % 7 - 3) * 0.0003
                offset_y = ((b['part_no'] * 23) % 7 - 3) * 0.0003
                lng += offset_x
                lat += offset_y
            seen_coords.add(coord_key)
            
            pt = sg.Point(lng, lat)
            points.append(pt)
            booth_map.append(b)

        # Generate Voronoi diagram for the ward
        multi_pt = sg.MultiPoint(points)
        envelope = ward_geom.buffer(0.005)
        voronoi_diagram = so.voronoi_diagram(multi_pt, envelope=envelope)

        # Match each Voronoi cell with its closest booth point and clip with ward_geom
        matched_cells = {b['part_no']: [] for b in ward_booths}
        for poly in voronoi_diagram.geoms:
            clipped_poly = poly.intersection(ward_geom)
            if clipped_poly.is_empty:
                continue
            
            # Find closest booth point
            closest_part = min(booth_map, key=lambda b: sg.Point(b['lng'], b['lat']).distance(poly))['part_no']
            matched_cells[closest_part].append(clipped_poly)

        # Merge polygons for each booth
        for b in ward_booths:
            p_no = b['part_no']
            polys = matched_cells.get(p_no, [])
            pt = sg.Point(b['lng'], b['lat'])
            
            if polys:
                union_poly = so.unary_union(polys)
                if not union_poly.is_valid:
                    union_poly = union_poly.buffer(0)
            else:
                union_poly = pt.buffer(0.0015).intersection(ward_geom)

            if union_poly.is_empty:
                union_poly = pt.buffer(0.0015)

            geom_json = sg.mapping(union_poly)
            try:
                c_pt = union_poly.centroid
                centroid = [round(c_pt.x, 5), round(c_pt.y, 5)]
            except Exception:
                centroid = [round(b['lng'], 5), round(b['lat'], 5)]
                
            minx, miny, maxx, maxy = union_poly.bounds

            feat = {
                "type": "Feature",
                "geometry": geom_json,
                "properties": {
                    **b,
                    "centroid": centroid,
                    "bbox": [[round(minx, 5), round(miny, 5)], [round(maxx, 5), round(maxy, 5)]]
                }
            }
            booth_features.append(feat)

    # 7. Save Booth Boundaries GeoJSON & JS
    booth_fc = {
        "type": "FeatureCollection",
        "features": booth_features
    }

    geojson_path = os.path.join(BASE_DIR, "data", "shantinagar_booth_boundaries.geojson")
    with open(geojson_path, 'w', encoding='utf-8') as f:
        json.dump(booth_fc, f, indent=2)
    print(f"Saved {geojson_path} with {len(booth_features)} booth catchment polygons ({os.path.getsize(geojson_path)/1024:.1f} KB).")

    js_path = os.path.join(BASE_DIR, "data", "shantinagar_booth_boundaries.js")
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("window.SHANTINAGAR_BOOTHS_GEOJSON = " + json.dumps(booth_fc) + ";\n")
    print(f"Saved {js_path} ({os.path.getsize(js_path)/1024:.1f} KB).")

    print("\n=== All Polling Booth Boundaries & Corresponding Voter Datasets Complete! ===")

if __name__ == '__main__':
    main()
