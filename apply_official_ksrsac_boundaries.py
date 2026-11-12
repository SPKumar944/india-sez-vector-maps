import os
import json
from shapely.geometry import shape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ksrsac_path = os.path.join(BASE_DIR, 'Shanthinagar_KSRSAC_163.geojson')
geo_path = os.path.join(BASE_DIR, 'data', 'shantinagar_electoral_geo.json')
out_geojson = os.path.join(BASE_DIR, 'data', 'shantinagar_booth_boundaries.geojson')
out_js = os.path.join(BASE_DIR, 'data', 'shantinagar_booth_boundaries.js')
out_electoral_js = os.path.join(BASE_DIR, 'data', 'electoral_data.js')

with open(ksrsac_path, 'r', encoding='utf-8') as f:
    ksrsac = json.load(f)

with open(geo_path, 'r', encoding='utf-8') as f:
    electoral = json.load(f)

booths_map = {b['part_no']: b for b in electoral['booths']}

enriched_features = []
processed_parts = set()

# Map features
for feat in ksrsac['features']:
    props = feat['properties']
    ps_no_raw = props.get('PS_NO')
    try:
        part_no = int(ps_no_raw)
    except (ValueError, TypeError):
        continue

    if part_no not in booths_map:
        continue

    b_meta = booths_map[part_no]
    geom = shape(feat['geometry'])
    minx, miny, maxx, maxy = geom.bounds
    centroid = geom.centroid

    # Enrich booth metadata with official centroid and bbox
    b_meta['lng'] = round(centroid.x, 6)
    b_meta['lat'] = round(centroid.y, 6)
    b_meta['bbox'] = [[round(minx, 6), round(miny, 6)], [round(maxx, 6), round(maxy, 6)]]
    b_meta['official_ps_name'] = props.get('PS_Name', '')
    b_meta['ps_code'] = props.get('PSCode', '')

    new_props = {
        'part_no': part_no,
        'booth_code': props.get('BoothCode', f"29163{part_no:03d}"),
        'ps_code': props.get('PSCode', f"163-{part_no:03d}"),
        'booth_name': props.get('PS_Name') or b_meta['booth_name'],
        'building': b_meta['building'],
        'ward_no': b_meta['ward_no'],
        'ward_name': b_meta['ward_name'],
        'total_electors': b_meta['total_electors'],
        'male': b_meta['male'],
        'female': b_meta['female'],
        'third_gender': b_meta['third_gender'],
        'gender_ratio': b_meta['gender_ratio'],
        'avg_age': b_meta['avg_age'],
        'sections_count': len(b_meta.get('sections', [])),
        'centroid': [round(centroid.x, 6), round(centroid.y, 6)],
        'bbox': [[round(minx, 6), round(miny, 6)], [round(maxx, 6), round(maxy, 6)]],
        'source': 'Official Election Commission / KSRSAC Polling Station Boundary'
    }

    enriched_features.append({
        'type': 'Feature',
        'geometry': feat['geometry'],
        'properties': new_props
    })
    processed_parts.add(part_no)

print(f"Enriched {len(enriched_features)} features covering {len(processed_parts)} polling parts.")

# Save enriched GeoJSON
geojson_obj = {
    'type': 'FeatureCollection',
    'crs': {
        'type': 'name',
        'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}
    },
    'features': enriched_features
}

with open(out_geojson, 'w', encoding='utf-8') as f:
    json.dump(geojson_obj, f, indent=2)

with open(out_js, 'w', encoding='utf-8') as f:
    f.write('window.BOOTH_BOUNDARIES_GEOJSON = ' + json.dumps(geojson_obj, indent=2) + ';\n')

# Save updated electoral data
with open(geo_path, 'w', encoding='utf-8') as f:
    json.dump(electoral, f, indent=2)

with open(out_electoral_js, 'w', encoding='utf-8') as f:
    f.write('window.ELECTORAL_DATA = ' + json.dumps(electoral, indent=2) + ';\n')

print("Successfully written official KSRSAC booth boundaries to GeoJSON and JS bundle!")
