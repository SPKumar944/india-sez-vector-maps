#!/usr/bin/env python3
"""
build_electoral_dashboard.py
Extracts electoral roll data from Master Excel sheets, geocodes polling stations and wards,
and generates the public interactive Electoral Map & Voter Intelligence Dashboard for GitHub Pages.
"""

import os
import re
import json
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------------------
# High-precision Geocoding Dictionaries & Landmark Heuristics
# -------------------------------------------------------------
# Shantinagar Known Landmarks (lat, lng, ward_no, ward_name)
SHANTINAGAR_LANDMARKS = {
    "st joseph's indian": (12.9723, 77.5962, 111, "Shantala Nagar"),
    "bishop cotton girls": (12.9708, 77.6014, 111, "Shantala Nagar"),
    "bishop cotton boys": (12.9682, 77.6010, 111, "Shantala Nagar"),
    "st joseph commerce college": (12.9716, 77.6072, 111, "Shantala Nagar"),
    "baldwin boys": (12.9644, 77.6055, 111, "Shantala Nagar"),
    "baldwin girls": (12.9659, 77.6037, 111, "Shantala Nagar"),
    "cathedral high school": (12.9678, 77.6094, 111, "Shantala Nagar"),
    "moulana azad": (12.9685, 77.6108, 111, "Shantala Nagar"),
    "m g road": (12.9742, 77.6080, 111, "Shantala Nagar"),
    "brigade road": (12.9715, 77.6070, 111, "Shantala Nagar"),
    "church street": (12.9748, 77.6045, 111, "Shantala Nagar"),
    "lavelle road": (12.9710, 77.5975, 111, "Shantala Nagar"),
    "richmond": (12.9655, 77.6060, 111, "Shantala Nagar"),
    "langford": (12.9590, 77.6005, 117, "Shanthi Nagar"),
    "shanti nagar": (12.9565, 77.5970, 117, "Shanthi Nagar"),
    "k h road": (12.9575, 77.5955, 117, "Shanthi Nagar"),
    "wilson garden": (12.9530, 77.5940, 117, "Shanthi Nagar"),
    "engineering ward office": (12.9570, 77.5985, 117, "Shanthi Nagar"),
    "old ward no 75": (12.9568, 77.5992, 117, "Shanthi Nagar"),
    
    # Neelasandra / Anjanappa Garden (Ward 116)
    "bright high school": (12.9556, 77.6146, 116, "Nilasandra"),
    "elite english high school": (12.9562, 77.6136, 116, "Nilasandra"),
    "karnataka vidya shala": (12.9545, 77.6150, 116, "Nilasandra"),
    "urdu primary boys": (12.9551, 77.6142, 116, "Nilasandra"),
    "b.b.m.p primary health centre": (12.9616, 77.6190, 114, "Agaram"),
    "bbmp primary health centre": (12.9616, 77.6190, 114, "Agaram"),
    "crystal english school": (12.9518, 77.6112, 116, "Nilasandra"),
    "anepalya": (12.9515, 77.6110, 116, "Nilasandra"),
    "neelasandra": (12.9550, 77.6145, 116, "Nilasandra"),
    "l r nagar": (12.9538, 77.6172, 116, "Nilasandra"),
    "rose garden": (12.9578, 77.6185, 115, "Vannarpet"),
    
    # Austin Town / Victoria Layout / Agaram (Ward 114)
    "corporation girls high school": (12.9622, 77.6182, 114, "Agaram"),
    "corporation girls junior college": (12.9625, 77.6180, 114, "Agaram"),
    "corporation highschool": (12.9620, 77.6175, 114, "Agaram"),
    "austin town": (12.9620, 77.6180, 114, "Agaram"),
    "victoria layout": (12.9660, 77.6140, 114, "Agaram"),
    "sri dhanraj poolchand": (12.9638, 77.6174, 114, "Agaram"),
    "yalagunda palya": (12.9632, 77.6168, 114, "Agaram"),
    
    # Vannarpet / Viveknagar (Ward 115)
    "corporation higher elementary": (12.9582, 77.6225, 115, "Vannarpet"),
    "st philomena": (12.9586, 77.6218, 115, "Vannarpet"),
    "vannarpet": (12.9588, 77.6220, 115, "Vannarpet"),
    "vivek nagar": (12.9572, 77.6240, 115, "Vannarpet"),
    "maya bazar": (12.9568, 77.6245, 115, "Vannarpet"),
    "ceva govt": (12.9572, 77.6162, 116, "Nilasandra"),
    
    # Domlur (Ward 112)
    "domlur": (12.9625, 77.6380, 112, "Domlur"),
    "corporation high school domlur": (12.9626, 77.6382, 112, "Domlur"),
    "corporation nursery school jogupalya": (12.9735, 77.6255, 112, "Domlur"),
    "jogupalya": (12.9732, 77.6250, 112, "Domlur"),
    "kairali nikethan": (12.9680, 77.6320, 112, "Domlur"),
    "s s b english school": (12.9710, 77.6350, 112, "Domlur"),
    "appa reddy palya": (12.9705, 77.6345, 112, "Domlur"),
    "amarjyoti": (12.9605, 77.6410, 112, "Domlur"),
    
    # Konena Agrahara / Murugeshpalya (Ward 113)
    "konena agrahara": (12.9555, 77.6520, 113, "Konena Agrahara"),
    "murugeshpalya": (12.9540, 77.6540, 113, "Konena Agrahara"),
    "wind tunnel road": (12.9510, 77.6560, 113, "Konena Agrahara")
}

def geocode_shantinagar_booth(part_no, ps_name, sections):
    ps_lower = ps_name.lower()
    secs_lower = " ".join([str(s).lower() for s in sections])
    combined = ps_lower + " " + secs_lower

    # Try matching specific landmark keys
    for key, (lat, lng, w_no, w_name) in SHANTINAGAR_LANDMARKS.items():
        if key in ps_lower:
            # Add a micro-jitter based on part_no so overlapping booths inside same building are distinct
            jitter_lat = ((part_no * 17) % 20 - 10) * 0.00008
            jitter_lng = ((part_no * 23) % 20 - 10) * 0.00008
            return round(lat + jitter_lat, 5), round(lng + jitter_lng, 5), w_no, w_name

    # Check sections text if building wasn't matched
    for key, (lat, lng, w_no, w_name) in SHANTINAGAR_LANDMARKS.items():
        if key in secs_lower:
            jitter_lat = ((part_no * 17) % 20 - 10) * 0.0001
            jitter_lng = ((part_no * 23) % 20 - 10) * 0.0001
            return round(lat + jitter_lat, 5), round(lng + jitter_lng, 5), w_no, w_name

    # Part number zone fallback based on Shantinagar electoral order
    if part_no <= 35:
        base_lat, base_lng, w_no, w_name = 12.9680, 77.6040, 111, "Shantala Nagar"
    elif part_no <= 60:
        base_lat, base_lng, w_no, w_name = 12.9570, 77.5975, 117, "Shanthi Nagar"
    elif part_no <= 95:
        base_lat, base_lng, w_no, w_name = 12.9545, 77.6145, 116, "Nilasandra"
    elif part_no <= 125:
        base_lat, base_lng, w_no, w_name = 12.9585, 77.6210, 115, "Vannarpet"
    elif part_no <= 155:
        base_lat, base_lng, w_no, w_name = 12.9620, 77.6180, 114, "Agaram"
    elif part_no <= 180:
        base_lat, base_lng, w_no, w_name = 12.9630, 77.6380, 112, "Domlur"
    else:
        base_lat, base_lng, w_no, w_name = 12.9550, 77.6530, 113, "Konena Agrahara"

    jitter_lat = ((part_no * 31) % 40 - 20) * 0.00015
    jitter_lng = ((part_no * 47) % 40 - 20) * 0.00015
    return round(base_lat + jitter_lat, 5), round(base_lng + jitter_lng, 5), w_no, w_name


# -------------------------------------------------------------
# Process Constituency Data
# -------------------------------------------------------------
def process_constituency_excel(excel_file, constituency_name, ac_no, gdrive_link):
    excel_path = os.path.join(BASE_DIR, excel_file)
    if not os.path.exists(excel_path):
        print(f"File {excel_file} not found locally, skipping...")
        return None

    print(f"Reading {excel_file} for {constituency_name}...")
    df = pd.read_excel(excel_path)
    print(f" Loaded {len(df):,} voters in {constituency_name}")

    # Clean types
    df['Part No'] = pd.to_numeric(df['Part No'], errors='coerce').fillna(0).astype(int)
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['Gender'] = df['Gender'].astype(str).str.strip().str.title()

    booths = []
    grouped = df.groupby('Part No')

    for part_no, group in grouped:
        if part_no == 0:
            continue
            
        ps_name = str(group['Polling Station'].dropna().iloc[0] if not group['Polling Station'].dropna().empty else f"Booth {part_no}")
        # Clean building name
        clean_building = re.sub(r'^\d+\s*-\s*', '', ps_name)
        clean_building = re.sub(r',?\s*Room\s*(?:No\.?|Number)?\s*\d+.*', '', clean_building, flags=re.I).strip()
        
        # Sections
        raw_secs = [str(s).strip() for s in group['Section / Street Name'].dropna().unique() if str(s).strip() != 'nan' and len(str(s).strip()) > 1]
        
        # Demographic aggregation
        tot_voters = len(group)
        male_cnt = int((group['Gender'] == 'Male').sum())
        female_cnt = int((group['Gender'] == 'Female').sum())
        third_cnt = int(tot_voters - male_cnt - female_cnt)
        
        gender_ratio = round((female_cnt / male_cnt * 1000), 1) if male_cnt > 0 else 1000.0
        
        # Age brackets
        valid_ages = group['Age'].dropna()
        avg_age = round(float(valid_ages.mean()), 1) if not valid_ages.empty else 42.0
        
        age_u25 = int((valid_ages < 25).sum())
        age_25_35 = int(((valid_ages >= 25) & (valid_ages < 35)).sum())
        age_35_50 = int(((valid_ages >= 35) & (valid_ages < 50)).sum())
        age_50_65 = int(((valid_ages >= 50) & (valid_ages < 65)).sum())
        age_o65 = int((valid_ages >= 65).sum())

        # Geocode
        lat, lng, w_no, w_name = geocode_shantinagar_booth(part_no, ps_name, raw_secs)

        booths.append({
            "part_no": int(part_no),
            "booth_name": ps_name,
            "building": clean_building,
            "lat": lat,
            "lng": lng,
            "ward_no": w_no,
            "ward_name": w_name,
            "total_electors": tot_voters,
            "male": male_cnt,
            "female": female_cnt,
            "third_gender": third_cnt,
            "gender_ratio": gender_ratio,
            "avg_age": avg_age,
            "age_groups": {
                "u25": age_u25,
                "25_35": age_25_35,
                "35_50": age_35_50,
                "50_65": age_50_65,
                "o65": age_o65
            },
            "sections": raw_secs[:8]
        })

    # Sort booths by part number
    booths.sort(key=lambda x: x['part_no'])

    tot_constituency_voters = sum(b['total_electors'] for b in booths)
    tot_male = sum(b['male'] for b in booths)
    tot_female = sum(b['female'] for b in booths)
    constituency_gr = round((tot_female / tot_male * 1000), 1) if tot_male > 0 else 1000.0
    overall_avg_age = round(float(np.mean([b['avg_age'] for b in booths])), 1)

    # Ward summary
    wards_summary = {}
    for b in booths:
        w_id = f"Ward {b['ward_no']} - {b['ward_name']}"
        if w_id not in wards_summary:
            wards_summary[w_id] = {
                "ward_no": b['ward_no'],
                "ward_name": b['ward_name'],
                "booths_count": 0,
                "total_electors": 0,
                "male": 0,
                "female": 0
            }
        wards_summary[w_id]["booths_count"] += 1
        wards_summary[w_id]["total_electors"] += b['total_electors']
        wards_summary[w_id]["male"] += b['male']
        wards_summary[w_id]["female"] += b['female']

    return {
        "constituency": constituency_name,
        "ac_no": ac_no,
        "total_electors": tot_constituency_voters,
        "total_booths": len(booths),
        "male": tot_male,
        "female": tot_female,
        "gender_ratio": constituency_gr,
        "avg_age": overall_avg_age,
        "gdrive_link": gdrive_link,
        "wards": list(wards_summary.values()),
        "booths": booths
    }

def main():
    print("Building Electoral Intelligence Datasets & Maps...")
    
    # 1. Shantinagar (The primary sheet requested)
    shantinagar_data = process_constituency_excel(
        "Shantinagar_Master_Electoral_Roll.xlsx",
        "Shantinagar",
        160,
        "https://docs.google.com/spreadsheets/d/11IFVlZ0-npAND4NBa_ptw68ZSvRjmouY/edit"
    )

    if not shantinagar_data:
        print("Error: Could not build Shantinagar dataset.")
        return

    # Save to data/electoral_data.js for instant static web embedding
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    
    js_content = f"window.ELECTORAL_DATA = {json.dumps(shantinagar_data, indent=2)};\n"
    js_path = os.path.join(BASE_DIR, "data", "electoral_data.js")
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f" Created {js_path} ({os.path.getsize(js_path)/1024:.1f} KB)")

    # Also save as JSON for API consumption
    json_path = os.path.join(BASE_DIR, "data", "shantinagar_electoral_geo.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(shantinagar_data, f, indent=2)
    print(f" Created {json_path} ({os.path.getsize(json_path)/1024:.1f} KB)")

    print(f"\nSuccessfully compiled {shantinagar_data['total_electors']:,} voters across {shantinagar_data['total_booths']} polling booths in Shantinagar!")

if __name__ == '__main__':
    main()
