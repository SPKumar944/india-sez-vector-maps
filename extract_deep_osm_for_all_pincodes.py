#!/usr/bin/env python3
"""
Deep Multi-Pincode OSM & Nominatim Geospatial Extractor
Extracts 800 - 1,200+ raw geocoded POIs, competitors, and housing complexes
for:
- 560041 (Jayanagar)
- 560038 (Indiranagar)
- 560102 (HSR Layout)
"""

import os
import sys
import json
import time
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PINCODES = {
    "560041": {
        "name": "jayanagar",
        "viewbox": "77.568,12.945,77.615,12.905", # min_lon, max_lat, max_lon, min_lat
        "output_dir": os.path.join(BASE_DIR, "data", "560041_jayanagar")
    },
    "560038": {
        "name": "indiranagar",
        "viewbox": "77.620,12.995,77.665,12.960",
        "output_dir": os.path.join(BASE_DIR, "data", "560038_indiranagar")
    },
    "560102": {
        "name": "hsr_layout",
        "viewbox": "77.625,12.932,77.672,12.898",
        "output_dir": os.path.join(BASE_DIR, "data", "560102_hsr_layout")
    }
}

HEADERS = {
    "User-Agent": "CloudKitchenMarketResearch/4.0 (bangalore-prime-pincodes-deep-extraction)"
}

SEARCH_SPECS = [
    # Phase 1: Housing & Residential Proxies
    ('Phase1_Housing', 'Apartments', 'apartment'),
    ('Phase1_Housing', 'Residential Apartments', 'apartments'),
    ('Phase1_Housing', 'Residency', 'Residency'),
    ('Phase1_Housing', 'Residential Towers & Heights', 'Towers'),
    ('Phase1_Housing', 'Enclave / Layout', 'Enclave'),
    ('Phase1_Housing', 'Prestige / Sobha / Brigade / Mantri / Salarpuria', 'Apartment'),
    ('Phase1_Housing', 'Gated Community Complexes', 'Layout'),
    ('Phase1_Housing', 'Colony & Slum Clusters', 'Colony'),
    ('Phase1_Housing', 'Student Hostels', 'hostel'),
    ('Phase1_Housing', 'PG / Co-living', 'PG'),
    ('Phase1_Housing', 'Zolo / Stanza Co-living', 'Zolo'),
    
    # Phase 2: Corporate & Industrial
    ('Phase2_Corporate', 'IT Park / Tech Park', 'Tech'),
    ('Phase2_Corporate', 'Offices', 'office'),
    ('Phase2_Corporate', 'Coworking Spaces', 'coworking'),
    ('Phase2_Corporate', 'Software / Corporate', 'Technologies'),
    ('Phase2_Corporate', 'Commercial Complexes', 'Complex'),
    
    # Phase 2: Educational
    ('Phase2_Educational', 'Colleges', 'college'),
    ('Phase2_Educational', 'Universities / Institutes', 'Institute'),
    ('Phase2_Educational', 'Schools & Coaching', 'school'),
    ('Phase2_Educational', 'Academy & Coaching Institutes', 'Academy'),
    
    # Phase 2: Transit & Medical
    ('Phase2_Transit_Medical', 'Hospitals', 'hospital'),
    ('Phase2_Transit_Medical', 'Clinics & Diagnostics', 'clinic'),
    ('Phase2_Transit_Medical', 'Bus Stands & Stops', 'bus_stop'),
    ('Phase2_Transit_Medical', 'Metro Stations & Rail', 'metro'),
    
    # Phase 2: Recreation & Retail
    ('Phase2_Recreation_Retail', 'Malls & Shopping Centers', 'mall'),
    ('Phase2_Recreation_Retail', 'Supermarkets', 'supermarket'),
    ('Phase2_Recreation_Retail', 'Cinemas & Theaters', 'cinema'),
    ('Phase2_Recreation_Retail', 'Pubs & Bars', 'pub'),
    ('Phase2_Recreation_Retail', 'Nightlife & Lounges', 'bar'),
    ('Phase2_Recreation_Retail', 'Fitness & Gyms', 'gym'),
    ('Phase2_Recreation_Retail', 'High Street Boutiques & Shops', 'shop'),
    
    # Phase 3: F&B Competitors (Multi-page for extreme density)
    ('Phase3_FnB', 'Restaurants (Page 1)', 'restaurant'),
    ('Phase3_FnB', 'Cafes & Coffee Shops', 'cafe'),
    ('Phase3_FnB', 'Fast Food / QSR', 'fast_food'),
    ('Phase3_FnB', 'Bakeries & Patisseries', 'bakery'),
    ('Phase3_FnB', 'Ice Cream & Desserts', 'ice_cream'),
    ('Phase3_FnB', 'Biryani Outlets', 'Biryani'),
    ('Phase3_FnB', 'Pizza Outlets', 'Pizza'),
    ('Phase3_FnB', 'Burger / QSR Chains', 'Burger'),
    ('Phase3_FnB', 'Cloud Kitchens & Takeaway', 'kitchen'),
    ('Phase3_FnB', 'Sweets & Snacks', 'sweets'),
    ('Phase3_FnB', 'Juice & Beverages', 'juice'),
    ('Phase3_FnB', 'Vegetarian Heritage Dining', 'Bhavan')
]

def extract_for_pincode(pin, cfg):
    out_dir = cfg["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "raw_osm_extracted_pois.json")
    
    print(f"\n=======================================================")
    print(f"DEEP NOMINATIM EXTRACTION FOR PINCODE: {pin} ({cfg['name'].upper()})")
    print(f"Target Viewbox: {cfg['viewbox']}")
    print(f"=======================================================")

    all_items = {}
    total_calls = 0

    for phase, label, q in SEARCH_SPECS:
        exclude = []
        pages = 3 if q in ('restaurant', 'cafe', 'fast_food', 'office', 'bus_stop', 'apartment', 'apartments') else 2 if q in ('shop', 'bakery', 'hotel', 'hospital', 'school', 'Complex', 'supermarket') else 1
        
        for p in range(pages):
            excl_param = f"&exclude_place_ids={','.join(map(str, exclude[:100]))}" if exclude else ""
            url = f"https://nominatim.openstreetmap.org/search?q={q}&viewbox={cfg['viewbox']}&bounded=1&format=jsonv2&limit=50&addressdetails=1&extratags=1{excl_param}"
            try:
                r = requests.get(url, headers=HEADERS, timeout=10)
                total_calls += 1
                if r.status_code == 200:
                    arr = r.json()
                    if not arr:
                        break
                    for item in arr:
                        pid = item["place_id"]
                        exclude.append(pid)
                        if pid not in all_items:
                            item["_phase"] = phase
                            item["_query_label"] = label
                            all_items[pid] = item
                time.sleep(0.35)
            except Exception as e:
                print(f"[{pin}] Warn {q} page {p}: {e}")
                time.sleep(0.5)

        print(f"[{pin}] {phase:22s} | {label:32s} -> {len(all_items)} cumulative items")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(list(all_items.values()), f, indent=2)

    print(f"[{pin}] SUCCESS! Saved {len(all_items)} raw geocoded OSM objects to {out_file}")
    return len(all_items)

def main():
    results = {}
    for pin, cfg in PINCODES.items():
        count = extract_for_pincode(pin, cfg)
        results[pin] = count
    
    print("\n" + "=" * 70)
    print("ALL 3 PINCODES RAW OSM EXTRACTIONS COMPLETE!")
    print("=" * 70)
    for p, c in results.items():
        print(f" - Pincode {p} ({PINCODES[p]['name']}): {c} raw geocoded OSM entities extracted.")

if __name__ == "__main__":
    main()
