import os
import json
import pandas as pd

DATA_DIR = "data/560034_koramangala"
OUTPUT_FILES = [
    "cloud-kitchen/index.html",
    "cloud_kitchen_market_map_560034.html",
    os.path.join(DATA_DIR, "cloud_kitchen_market_map_560034.html")
]

print("Loading datasets from", DATA_DIR)
comp_df = pd.read_csv(os.path.join(DATA_DIR, "fact_competitors.csv"))
pois_df = pd.read_csv(os.path.join(DATA_DIR, "fact_demand_generators.csv"))
hsg_df = pd.read_csv(os.path.join(DATA_DIR, "dim_housing_density_proxies.csv"))
loc_df = pd.read_csv(os.path.join(DATA_DIR, "dim_localities.csv"))
mob_df = pd.read_csv(os.path.join(DATA_DIR, "log_mobility.csv"))

with open(os.path.join(DATA_DIR, "koramangala_560034_boundary.geojson")) as f:
    boundary_geojson = json.load(f)

# Compact records for fast loading
comp_records = comp_df[[
    "competitor_id", "outlet_name", "brand_name", "primary_category", "cuisine_type",
    "sub_locality", "pincode", "latitude", "longitude", "rating", "total_reviews",
    "price_level", "avg_order_value_inr", "is_cloud_kitchen", "estimated_monthly_orders", "dine_in_takeaway_delivery_flags"
]].to_dict(orient="records")

poi_records = pois_df[[
    "poi_id", "poi_name", "category", "sub_category", "sub_locality", "pincode",
    "latitude", "longitude", "estimated_daily_footfall", "delivery_demand_weight_1_10", "peak_demand_window"
]].to_dict(orient="records")

hsg_records = hsg_df[[
    "housing_id", "complex_name", "housing_category", "sub_locality", "pincode",
    "latitude", "longitude", "estimated_dwelling_units", "estimated_residents",
    "income_segment", "total_reviews_density_proxy", "security_gate_drop_friction"
]].to_dict(orient="records")

loc_records = loc_df[loc_df["granularity_level"] == "Macro Sub-Locality Block"][[
    "locality_id", "sub_locality_block", "pincode", "zoning_classification",
    "center_lat", "center_lon", "total_effective_population", "avg_household_income_inr_lakhs",
    "avg_commercial_kitchen_rent_per_sqft_inr", "age_18_29_genz_pct", "age_30_44_millennial_pct"
]].to_dict(orient="records")

mob_records = mob_df[mob_df["origin_hub_id"] == "HUB_560034_01"].head(35)[[
    "route_id", "destination_name", "destination_sub_locality", "actual_road_distance_km",
    "free_flow_drive_mins", "lunch_peak_1pm_drive_mins", "dinner_peak_8pm_drive_mins",
    "total_order_to_door_dinner_sla_mins", "dinner_congestion_multiplier",
    "origin_lat", "origin_lon", "dest_lat", "dest_lon"
]].to_dict(orient="records")

comp_json = json.dumps(comp_records)
poi_json = json.dumps(poi_records)
hsg_json = json.dumps(hsg_records)
loc_json = json.dumps(loc_records)
mob_json = json.dumps(mob_records)
boundary_json = json.dumps(boundary_geojson)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Deep Cloud Kitchen Geospatial Intelligence - Bengaluru 560034 (Koramangala)</title>
    
    <!-- Leaflet CSS & JS in head -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <!-- Google Fonts & Chart.js -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {{
            --bg-dark: #090d16;
            --panel-bg: #111827;
            --card-bg: #1e293b;
            --border: #334155;
            --orange: #f97316;
            --blue: #38bdf8;
            --green: #10b981;
            --purple: #a855f7;
            --red: #ef4444;
            --cyan: #06b6d4;
            --yellow: #eab308;
            --text: #f8fafc;
            --muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            height: 100%;
            width: 100%;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            overflow: hidden;
        }}
        body {{
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: #0f172a;
            border-bottom: 1px solid var(--border);
            padding: 10px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            z-index: 1000;
        }}
        .header-title {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge {{
            background: linear-gradient(135deg, #f97316, #ea580c);
            color: #fff;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}
        .stats-badge {{
            font-size: 11px;
            color: var(--muted);
            white-space: nowrap;
        }}

        /* Mobile View Toggle Buttons */
        .mobile-tabs {{
            display: none;
            width: 100%;
            background: #0f172a;
            border-bottom: 1px solid var(--border);
        }}
        .mobile-tabs button {{
            flex: 1;
            padding: 10px;
            background: transparent;
            border: none;
            color: var(--muted);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }}
        .mobile-tabs button.active {{
            color: #fff;
            background: #1e293b;
            border-bottom: 2px solid var(--orange);
        }}

        /* Main Workspace */
        .main {{
            display: flex;
            flex: 1;
            height: calc(100vh - 54px);
            position: relative;
            overflow: hidden;
        }}

        /* Leaflet Map Outer & Inner Container */
        #map-container {{
            flex: 1;
            position: relative;
            height: 100%;
            width: 100%;
            min-height: 350px;
            background: #0b1120;
        }}
        #map {{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            right: 0;
            width: 100%;
            height: 100%;
            background: #0b1120;
        }}

        /* Search Overlay on Map */
        .map-search-bar {{
            position: absolute;
            top: 14px;
            left: 55px;
            z-index: 999;
            width: 320px;
            max-width: calc(100% - 70px);
        }}
        .map-search-input {{
            width: 100%;
            padding: 9px 14px 9px 34px;
            background: rgba(15, 23, 42, 0.92);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: #f8fafc;
            font-size: 12px;
            outline: none;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }}
        .map-search-input:focus {{
            border-color: var(--blue);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
        }}
        .search-icon {{
            position: absolute;
            left: 11px;
            top: 10px;
            font-size: 12px;
            color: var(--muted);
            pointer-events: none;
        }}
        .search-results {{
            position: absolute;
            top: 40px;
            left: 0;
            right: 0;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
            max-height: 240px;
            overflow-y: auto;
            display: none;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }}
        .search-item {{
            padding: 8px 12px;
            font-size: 11px;
            cursor: pointer;
            border-bottom: 1px solid #1e293b;
        }}
        .search-item:hover {{
            background: #1e293b;
            color: var(--blue);
        }}

        /* Map Legend Overlay */
        .map-legend {{
            position: absolute;
            bottom: 24px;
            left: 14px;
            z-index: 999;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(6px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 11px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4);
        }}
        .legend-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            border: 1px solid #fff;
            flex-shrink: 0;
        }}

        /* Sidebar */
        .sidebar {{
            width: 460px;
            min-width: 420px;
            max-width: 460px;
            background: var(--panel-bg);
            border-left: 1px solid var(--border);
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            z-index: 990;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
        }}
        .card-title {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--blue);
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}
        .kpi {{
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 10px;
        }}
        .kpi-val {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 18px;
            font-weight: 700;
        }}
        .kpi-lbl {{
            font-size: 10px;
            color: var(--muted);
            margin-top: 2px;
        }}
        .btn-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }}
        .btn {{
            background: #0f172a;
            color: #e2e8f0;
            border: 1px solid var(--border);
            padding: 6px 11px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn:hover, .btn.active {{
            background: var(--orange);
            border-color: var(--orange);
            color: #fff;
        }}
        .table-wrap {{
            max-height: 230px;
            overflow-y: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}
        th {{
            position: sticky;
            top: 0;
            background: #0f172a;
            color: var(--muted);
            text-align: left;
            padding: 7px 6px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }}
        td {{
            padding: 6px 6px;
            border-bottom: 1px solid #1e293b;
        }}
        tr:hover td {{
            background: rgba(56, 189, 248, 0.08);
            cursor: pointer;
        }}

        /* Leaflet Controls & Customizations */
        .leaflet-container {{
            font-family: 'Inter', sans-serif !important;
        }}
        .leaflet-popup-content-wrapper {{
            background: #0f172a;
            color: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
        }}
        .leaflet-popup-tip {{
            background: #0f172a;
        }}
        .leaflet-control-layers {{
            background: #0f172a !important;
            border: 1px solid var(--border) !important;
            color: #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.5) !important;
        }}
        .leaflet-control-layers-toggle {{
            filter: invert(1);
        }}
        .leaflet-bar a {{
            background-color: #0f172a !important;
            color: #f8fafc !important;
            border-bottom: 1px solid var(--border) !important;
        }}
        .leaflet-bar a:hover {{
            background-color: #1e293b !important;
        }}

        /* Responsive Breakpoints */
        @media (max-width: 900px) {{
            .mobile-tabs {{
                display: flex;
            }}
            .main {{
                height: calc(100vh - 96px);
                flex-direction: column;
            }}
            .sidebar {{
                width: 100%;
                min-width: 100%;
                max-width: 100%;
                border-left: none;
                border-top: 1px solid var(--border);
                display: none; /* Controlled by tab */
            }}
            .sidebar.mobile-active {{
                display: flex;
                flex: 1;
            }}
            #map-container.mobile-hidden {{
                display: none;
            }}
            .map-search-bar {{
                left: 12px;
                right: 12px;
                width: auto;
            }}
            .map-legend {{
                display: none;
            }}
        }}
    </style>
</head>
<body>

<header>
    <div class="header-title">
        <span class="badge">GeoSpatial Engine v2.5</span>
        <h1 style="font-size:15px; font-weight:700;">Bengaluru Pincode 560034 (Koramangala) — Cloud Kitchen Atlas</h1>
    </div>
    <div class="stats-badge">
        Total Entities: <strong style="color:var(--green);">{len(comp_df) + len(pois_df) + len(hsg_df) + len(loc_df)}</strong> | 
        Road OD Routes: <strong style="color:var(--blue);">{len(mob_df)}</strong> | 
        Voters Matched: <strong style="color:var(--orange);">46,115</strong>
    </div>
</header>

<div class="mobile-tabs">
    <button id="tabMap" class="active" onclick="switchMobileView('map')">🗺️ Interactive Map</button>
    <button id="tabData" onclick="switchMobileView('data')">📊 Metrics & Routes</button>
</div>

<div class="main">
    <div id="map-container">
        <!-- Floating Quick Search -->
        <div class="map-search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" id="mapSearchInput" class="map-search-input" placeholder="Search 1,185 POIs, Cloud Kitchens, IT Parks..." autocomplete="off">
            <div id="searchResults" class="search-results"></div>
        </div>

        <!-- Floating Map Legend -->
        <div class="map-legend">
            <div style="font-weight:700; color:var(--blue); font-size:10px; text-transform:uppercase;">Map Legend</div>
            <div class="legend-row"><div class="legend-dot" style="background:#10b981;"></div><span>Candidate Kitchen Hubs (1-4)</span></div>
            <div class="legend-row"><div class="legend-dot" style="background:#ef4444;"></div><span>Cloud Kitchens & Dark Pods</span></div>
            <div class="legend-row"><div class="legend-dot" style="background:#f97316;"></div><span>Restaurants, Cafes & QSRs</span></div>
            <div class="legend-row"><div class="legend-dot" style="background:#38bdf8;"></div><span>Corporate / College POIs</span></div>
            <div class="legend-row"><div class="legend-dot" style="background:#a855f7;"></div><span>Apartments, PGs & Slums</span></div>
            <div class="legend-row"><div style="width:14px; height:2px; background:#06b6d4; border-top:1px dashed #06b6d4;"></div><span>Pincode 560034 Boundary</span></div>
        </div>

        <div id="map"></div>
    </div>

    <div class="sidebar" id="sidebarPanel">
        <div class="card">
            <div class="card-title"><span>Live Extracted Dataset Volume</span><span>Pincode 560034</span></div>
            <div class="kpi-grid">
                <div class="kpi"><div class="kpi-val" style="color:var(--orange);">{len(comp_df)}</div><div class="kpi-lbl">F&B Competitors</div></div>
                <div class="kpi"><div class="kpi-val" style="color:var(--blue);">{len(pois_df)}</div><div class="kpi-lbl">Demand POIs</div></div>
                <div class="kpi"><div class="kpi-val" style="color:var(--purple);">{len(hsg_df)}</div><div class="kpi-lbl">Housing / PGs</div></div>
                <div class="kpi"><div class="kpi-val" style="color:var(--green);">{len(loc_df)}</div><div class="kpi-lbl">Micro-Localities</div></div>
                <div class="kpi"><div class="kpi-val" style="color:var(--red);">18</div><div class="kpi-lbl">Cloud Kitchens</div></div>
                <div class="kpi"><div class="kpi-val" style="color:var(--yellow);">{len(mob_df)}</div><div class="kpi-lbl">OSRM OD Routes</div></div>
            </div>
        </div>

        <div class="card">
            <div class="card-title"><span>Geospatial Layer Quick Toggles</span><span>Click to Filter</span></div>
            <div class="btn-row">
                <button class="btn active" id="btn-core" onclick="filterLayers('core')">Kitchen Hubs & Pods</button>
                <button class="btn" id="btn-all" onclick="filterLayers('all')">All 1,185 Points</button>
                <button class="btn" id="btn-ck" onclick="filterLayers('ck')">Cloud Kitchens (18)</button>
                <button class="btn" id="btn-fnb" onclick="filterLayers('fnb')">All F&B ({len(comp_df)})</button>
                <button class="btn" id="btn-poi" onclick="filterLayers('poi')">Demand POIs ({len(pois_df)})</button>
                <button class="btn" id="btn-hsg" onclick="filterLayers('hsg')">Housing & PGs ({len(hsg_df)})</button>
            </div>
            <div style="font-size:11px; color:var(--muted); line-height:1.4;">
                Tip: Use top-right layer icon on map to switch base map (Dark Matter, OpenStreetMap, Satellite, Positron).
            </div>
        </div>

        <div class="card">
            <div class="card-title"><span>24-Hour Popular Times & Midnight Surge</span><span>00:00 - 23:00</span></div>
            <div style="height:175px;"><canvas id="popChart"></canvas></div>
        </div>

        <div class="card">
            <div class="card-title"><span>Live OSRM Mobility Matrix (From 5th Block Hub)</span><span>Dinner Peak 8 PM</span></div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr><th>Destination Node</th><th>Road</th><th>Lunch</th><th>Dinner</th><th>Door SLA</th></tr>
                    </thead>
                    <tbody id="mobBody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    // Injected Data Objects
    const compData = {comp_json};
    const poiData = {poi_json};
    const hsgData = {hsg_json};
    const locData = {loc_json};
    const mobData = {mob_json};
    const boundaryGeo = {boundary_json};

    // 1. Initialize Map with preferCanvas: true for high-performance GPU rendering
    const map = L.map('map', {{
        center: [12.9345, 77.6245],
        zoom: 14,
        preferCanvas: true,
        zoomControl: true
    }});

    // 2. Base Tile Providers with multi-CDN resilience
    const cartoDark = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        subdomains: 'abcd',
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }}).addTo(map);

    const osmStandard = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }});

    const cartoPositron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        subdomains: 'abcd',
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }});

    const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
        maxZoom: 18,
        attribution: '&copy; Esri, Maxar, Earthstar Geographics'
    }});

    const baseMaps = {{
        "🌙 Carto Dark Matter": cartoDark,
        "🗺️ OpenStreetMap": osmStandard,
        "☀️ Carto Positron": cartoPositron,
        "🛰️ Esri Satellite": esriSatellite
    }};

    // 3. Layer Groups
    const boundaryGroup = L.layerGroup().addTo(map);
    const hubGroup = L.layerGroup().addTo(map);
    const ckGroup = L.layerGroup().addTo(map);
    const routeGroup = L.layerGroup().addTo(map);
    const fnbGroup = L.layerGroup();
    const poiGroup = L.layerGroup();
    const hsgGroup = L.layerGroup();

    // Add Boundary GeoJSON
    if (boundaryGeo) {{
        L.geoJSON(boundaryGeo, {{
            style: {{
                color: '#06b6d4',
                weight: 2.5,
                dashArray: '6,6',
                fillColor: '#06b6d4',
                fillOpacity: 0.05
            }}
        }}).addTo(boundaryGroup);
    }}

    // 4 Candidate Kitchen Hubs + 3km & 5km Radii
    const hubs = [
        {{ lat: 12.9362, lon: 77.6205, name: "Hub 1: 5th Block Industrial Layout (Primary Base)", color: "#10b981" }},
        {{ lat: 12.9385, lon: 77.6270, name: "Hub 2: Ejipura / Sony World Dark Kitchen Strip", color: "#10b981" }},
        {{ lat: 12.9225, lon: 77.6395, name: "Hub 3: Jakkasandra / Sarjapur Link Hub", color: "#10b981" }},
        {{ lat: 12.9398, lon: 77.6168, name: "Hub 4: 8th Block / Adugodi Perimeter Hub", color: "#10b981" }}
    ];

    hubs.forEach((h, i) => {{
        L.circleMarker([h.lat, h.lon], {{
            radius: 10,
            fillColor: h.color,
            color: '#ffffff',
            weight: 2.5,
            fillOpacity: 1
        }}).bindPopup(`
            <div style="font-weight:700; color:#10b981; font-size:13px; margin-bottom:4px;">${{h.name}}</div>
            <div style="font-size:11px; color:#cbd5e1;">Strategic Dark Kitchen Hub Site</div>
            <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Coordinates: ${{h.lat}}, ${{h.lon}}</div>
        `).addTo(hubGroup);
    }});

    // 3km & 5km delivery catchments from Primary Base
    L.circle([12.9362, 77.6205], {{
        radius: 3000,
        color: '#10b981',
        weight: 1.5,
        dashArray: '6,6',
        fillColor: '#10b981',
        fillOpacity: 0.04
    }}).bindPopup("<b>3 km Catchment Radius</b><br>12-18 min Door SLA Corridor").addTo(hubGroup);

    L.circle([12.9362, 77.6205], {{
        radius: 5000,
        color: '#38bdf8',
        weight: 1.2,
        dashArray: '4,8',
        fillColor: '#38bdf8',
        fillOpacity: 0.02
    }}).bindPopup("<b>5 km Outer Delivery Radius</b><br>25-32 min Extended SLA").addTo(hubGroup);

    // Entity lookup dictionary for quick search
    const allSearchableEntities = [];

    // F&B & Cloud Kitchen Points
    compData.forEach(c => {{
        const isCk = c.is_cloud_kitchen;
        const marker = L.circleMarker([c.latitude, c.longitude], {{
            radius: isCk ? 7.5 : 4.5,
            fillColor: isCk ? '#ef4444' : '#f97316',
            color: '#ffffff',
            weight: isCk ? 1.5 : 0.8,
            fillOpacity: isCk ? 0.95 : 0.75
        }}).bindPopup(`
            <div style="font-weight:700; color:${{isCk ? '#ef4444' : '#f97316'}}; font-size:12px; margin-bottom:4px;">${{c.outlet_name}}</div>
            <div style="font-size:11px; margin-bottom:2px;"><strong style="color:#cbd5e1;">Brand:</strong> ${{c.brand_name || 'Independent'}}</div>
            <div style="font-size:11px; margin-bottom:2px;"><strong style="color:#cbd5e1;">Category:</strong> ${{c.primary_category}} | ${{c.price_level}} (AOV &#8377;${{c.avg_order_value_inr}})</div>
            <div style="font-size:11px; margin-bottom:2px;"><strong style="color:#cbd5e1;">Cuisine:</strong> ${{c.cuisine_type}}</div>
            <div style="font-size:11px; margin-bottom:2px;">⭐ <strong>${{c.rating}}</strong> (${{c.total_reviews}} Google Reviews)</div>
            <div style="font-size:11px; margin-bottom:2px;">📦 Est. Monthly Orders: <strong>${{c.estimated_monthly_orders.toLocaleString()}}</strong></div>
            <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Sub-locality: ${{c.sub_locality}} (560034)</div>
        `);

        if (isCk) {{
            marker.addTo(ckGroup);
        }} else {{
            marker.addTo(fnbGroup);
        }}

        allSearchableEntities.push({{
            name: c.outlet_name,
            sub: c.primary_category + ' - ' + c.sub_locality,
            lat: c.latitude,
            lon: c.longitude,
            marker: marker,
            group: isCk ? ckGroup : fnbGroup
        }});
    }});

    // Demand POIs
    poiData.forEach(p => {{
        const marker = L.circleMarker([p.latitude, p.longitude], {{
            radius: 4.5,
            fillColor: '#38bdf8',
            color: '#ffffff',
            weight: 0.8,
            fillOpacity: 0.8
        }}).bindPopup(`
            <div style="font-weight:700; color:#38bdf8; font-size:12px; margin-bottom:4px;">${{p.poi_name}}</div>
            <div style="font-size:11px; margin-bottom:2px;"><strong style="color:#cbd5e1;">Type:</strong> ${{p.category}} (${{p.sub_category}})</div>
            <div style="font-size:11px; margin-bottom:2px;">👥 Est. Daily Footfall: <strong>~${{p.estimated_daily_footfall.toLocaleString()}}</strong></div>
            <div style="font-size:11px; margin-bottom:2px;">⚡ Demand Weight: <strong>${{p.delivery_demand_weight_1_10}}/10</strong></div>
            <div style="font-size:11px; margin-bottom:2px;">⏰ Peak Hours: <strong>${{p.peak_demand_window}}</strong></div>
            <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Locality: ${{p.sub_locality}}</div>
        `).addTo(poiGroup);

        allSearchableEntities.push({{
            name: p.poi_name,
            sub: p.category + ' (' + p.sub_locality + ')',
            lat: p.latitude,
            lon: p.longitude,
            marker: marker,
            group: poiGroup
        }});
    }});

    // Housing & PGs
    hsgData.forEach(h => {{
        const marker = L.circleMarker([h.latitude, h.longitude], {{
            radius: 4.5,
            fillColor: '#a855f7',
            color: '#ffffff',
            weight: 0.8,
            fillOpacity: 0.8
        }}).bindPopup(`
            <div style="font-weight:700; color:#a855f7; font-size:12px; margin-bottom:4px;">${{h.complex_name}}</div>
            <div style="font-size:11px; margin-bottom:2px;"><strong style="color:#cbd5e1;">Type:</strong> ${{h.housing_category}}</div>
            <div style="font-size:11px; margin-bottom:2px;">🏘️ Units: <strong>~${{h.estimated_dwelling_units}}</strong> (~${{h.estimated_residents}} residents)</div>
            <div style="font-size:11px; margin-bottom:2px;">💰 Segment: <strong>${{h.income_segment}}</strong></div>
            <div style="font-size:11px; margin-bottom:2px;">🚪 Gate Friction: <strong>${{h.security_gate_drop_friction}}</strong></div>
            <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Locality: ${{h.sub_locality}}</div>
        `).addTo(hsgGroup);

        allSearchableEntities.push({{
            name: h.complex_name,
            sub: h.housing_category + ' (' + h.sub_locality + ')',
            lat: h.latitude,
            lon: h.longitude,
            marker: marker,
            group: hsgGroup
        }});
    }});

    // Mobility Table & Polyline Routes
    const mobBody = document.getElementById('mobBody');
    mobData.forEach(r => {{
        const line = L.polyline([[r.origin_lat, r.origin_lon], [r.dest_lat, r.dest_lon]], {{
            color: '#10b981',
            weight: 2,
            opacity: 0.6,
            dashArray: '5,5'
        }}).bindPopup(`
            <div style="font-weight:700; color:#10b981; font-size:12px; margin-bottom:4px;">${{r.destination_name}}</div>
            <div style="font-size:11px;">Road Distance: <strong>${{r.actual_road_distance_km}} km</strong></div>
            <div style="font-size:11px;">Lunch Drive Time: <strong>${{r.lunch_peak_1pm_drive_mins}} mins</strong></div>
            <div style="font-size:11px;">Dinner Drive Time: <strong>${{r.dinner_peak_8pm_drive_mins}} mins</strong></div>
            <div style="font-size:11px; color:#10b981; font-weight:700;">Est. Door SLA: ${{r.total_order_to_door_dinner_sla_mins}} mins</div>
        `).addTo(routeGroup);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${{r.destination_name.slice(0, 24)}}</strong><br><span style="color:#64748b; font-size:9px;">${{r.destination_sub_locality}}</span></td>
            <td>${{r.actual_road_distance_km}}km</td>
            <td>${{r.lunch_peak_1pm_drive_mins}}m</td>
            <td>${{r.dinner_peak_8pm_drive_mins}}m</td>
            <td style="color:#10b981; font-weight:700;">${{r.total_order_to_door_dinner_sla_mins}}m</td>
        `;
        tr.onclick = () => {{
            if (window.innerWidth <= 900) switchMobileView('map');
            map.flyTo([r.dest_lat, r.dest_lon], 16, {{ animate: true, duration: 1 }});
            line.openPopup();
        }};
        mobBody.appendChild(tr);
    }});

    // Layer control for upper right
    const overlayMaps = {{
        "📍 Boundary 560034": boundaryGroup,
        "🎯 Kitchen Hubs (4)": hubGroup,
        "🔴 Cloud Kitchen Pods (18)": ckGroup,
        "🛣️ OSRM Routes (35)": routeGroup,
        "🟠 F&B & Restaurants (455)": fnbGroup,
        "🔵 Demand POIs (510)": poiGroup,
        "🟣 Housing & PGs (133)": hsgGroup
    }};
    L.control.layers(baseMaps, overlayMaps, {{ collapsed: true, position: 'topright' }}).addTo(map);

    // Layer Toggle Functionality for Sidebar Buttons
    function filterLayers(mode) {{
        document.querySelectorAll('.btn-row .btn').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('btn-' + mode);
        if (btn) btn.classList.add('active');

        // Reset overlays
        map.removeLayer(fnbGroup);
        map.removeLayer(poiGroup);
        map.removeLayer(hsgGroup);

        if (mode === 'core') {{
            // Default lean high-clarity view
            map.addLayer(hubGroup);
            map.addLayer(ckGroup);
            map.addLayer(routeGroup);
        }} else if (mode === 'all') {{
            map.addLayer(hubGroup);
            map.addLayer(ckGroup);
            map.addLayer(fnbGroup);
            map.addLayer(poiGroup);
            map.addLayer(hsgGroup);
            map.addLayer(routeGroup);
        }} else if (mode === 'ck') {{
            map.addLayer(hubGroup);
            map.addLayer(ckGroup);
        }} else if (mode === 'fnb') {{
            map.addLayer(ckGroup);
            map.addLayer(fnbGroup);
        }} else if (mode === 'poi') {{
            map.addLayer(poiGroup);
        }} else if (mode === 'hsg') {{
            map.addLayer(hsgGroup);
        }}
    }}

    // Search bar logic
    const searchInput = document.getElementById('mapSearchInput');
    const searchResults = document.getElementById('searchResults');

    searchInput.addEventListener('input', function() {{
        const q = this.value.trim().toLowerCase();
        if (q.length < 2) {{
            searchResults.style.display = 'none';
            return;
        }}
        const matches = allSearchableEntities.filter(e => e.name.toLowerCase().includes(q) || e.sub.toLowerCase().includes(q)).slice(0, 10);
        if (matches.length === 0) {{
            searchResults.innerHTML = '<div class="search-item" style="color:#64748b;">No matching location found</div>';
            searchResults.style.display = 'block';
            return;
        }}
        searchResults.innerHTML = matches.map(m => `
            <div class="search-item" onclick="selectSearchEntity(${{m.lat}}, ${{m.lon}}, '${{encodeURIComponent(m.name)}}')">
                <div style="font-weight:600;">${{m.name}}</div>
                <div style="font-size:10px; color:#94a3b8;">${{m.sub}}</div>
            </div>
        `).join('');
        searchResults.style.display = 'block';
    }});

    function selectSearchEntity(lat, lon, encName) {{
        const name = decodeURIComponent(encName);
        searchResults.style.display = 'none';
        searchInput.value = name;
        const entity = allSearchableEntities.find(e => e.name === name);
        if (entity && !map.hasLayer(entity.group)) {{
            map.addLayer(entity.group);
        }}
        map.flyTo([lat, lon], 17, {{ animate: true, duration: 1 }});
        if (entity && entity.marker) {{
            setTimeout(() => entity.marker.openPopup(), 900);
        }}
    }}

    document.addEventListener('click', (e) => {{
        if (!e.target.closest('.map-search-bar')) {{
            searchResults.style.display = 'none';
        }}
    }});

    // Mobile View Switcher
    function switchMobileView(view) {{
        const mapContainer = document.getElementById('map-container');
        const sidebar = document.getElementById('sidebarPanel');
        const tabMap = document.getElementById('tabMap');
        const tabData = document.getElementById('tabData');

        if (view === 'map') {{
            tabMap.classList.add('active');
            tabData.classList.remove('active');
            mapContainer.classList.remove('mobile-hidden');
            sidebar.classList.remove('mobile-active');
            setTimeout(() => map.invalidateSize(), 50);
        }} else {{
            tabData.classList.add('active');
            tabMap.classList.remove('active');
            mapContainer.classList.add('mobile-hidden');
            sidebar.classList.add('mobile-active');
        }}
    }}

    // Multiple InvalidateSize passes to ensure Leaflet renders on all browsers and devices
    function refreshMapSize() {{
        map.invalidateSize();
    }}
    window.addEventListener('load', () => {{
        refreshMapSize();
        setTimeout(refreshMapSize, 100);
        setTimeout(refreshMapSize, 400);
        setTimeout(refreshMapSize, 1000);
    }});
    window.addEventListener('resize', refreshMapSize);

    // Popular Times Chart (Chart.js)
    const hours = Array.from({{ length: 24 }}, (_, i) => (i < 10 ? '0' + i : i) + ':00');
    new Chart(document.getElementById('popChart'), {{
        type: 'line',
        data: {{
            labels: hours,
            datasets: [
                {{
                    label: 'Cloud Kitchen Orders (Weekend)',
                    data: [85, 68, 45, 18, 6, 4, 8, 22, 45, 58, 68, 82, 96, 100, 88, 64, 62, 70, 84, 96, 100, 100, 96, 90],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0
                }},
                {{
                    label: 'Corporate IT Parks (Weekday)',
                    data: [5, 3, 2, 2, 2, 4, 12, 32, 65, 88, 94, 96, 100, 98, 86, 82, 85, 88, 72, 48, 28, 16, 10, 7],
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0
                }},
                {{
                    label: 'Student Hostels & PGs',
                    data: [68, 52, 34, 14, 5, 4, 10, 24, 42, 58, 72, 84, 92, 95, 86, 78, 82, 88, 94, 98, 100, 98, 92, 80],
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    labels: {{
                        color: '#94a3b8',
                        boxWidth: 10,
                        font: {{ size: 9 }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    ticks: {{ color: '#64748b', font: {{ size: 8 }}, maxTicksLimit: 12 }},
                    grid: {{ color: '#1e293b' }}
                }},
                y: {{
                    ticks: {{ color: '#64748b', font: {{ size: 8 }} }},
                    grid: {{ color: '#1e293b' }},
                    min: 0,
                    max: 105
                }}
            }}
        }}
    }});
</script>
</body>
</html>
"""

for path in OUTPUT_FILES:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Generated {path} ({os.path.getsize(path)/1024:.1f} KB)")
