import os
import sqlite3
import math
import json
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "master_cloud_kitchen.sqlite"))
)
DATA_BASE_DIR = os.environ.get(
    "DATA_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
)

TABLE_PRIMARY_KEYS = {
    "dim_localities": "locality_id",
    "dim_housing_density_proxies": "housing_id",
    "fact_demand_generators": "poi_id",
    "fact_competitors": "competitor_id",
    "fact_popular_times": "popular_time_id",
    "log_mobility": "route_id"
}

TABLE_METADATA = {
    "dim_localities": {
        "title": "Localities & Electoral Micro-Zones",
        "description": "Geospatial boundary centroids, zoning (Commercial, Industrial, Residential), population estimates, and electoral voter age cohorts (Gen Z, Millennial).",
        "primary_key": "locality_id",
        "lat_col": "center_lat",
        "lon_col": "center_lon"
    },
    "dim_housing_density_proxies": {
        "title": "Housing & Residential Density Proxies",
        "description": "Gated communities, high-rise apartments, student PGs, and low-income settlements with dwelling unit counts, resident estimates, and gate drop friction.",
        "primary_key": "housing_id",
        "lat_col": "latitude",
        "lon_col": "longitude"
    },
    "fact_demand_generators": {
        "title": "Demand Generators (POIs)",
        "description": "Tech parks, corporate offices, universities, coaching hubs, hospitals, transit hubs, and retail malls driving delivery demand.",
        "primary_key": "poi_id",
        "lat_col": "latitude",
        "lon_col": "longitude"
    },
    "fact_competitors": {
        "title": "F&B Competitor Landscape",
        "description": "Commercial restaurants, cafes, cloud kitchens, and QSR chains with cuisine mix, price band, Google ratings, reviews, order estimates, and dining flags.",
        "primary_key": "competitor_id",
        "lat_col": "latitude",
        "lon_col": "longitude"
    },
    "fact_popular_times": {
        "title": "Footfall & Popular Times Curves",
        "description": "Hourly 24-hour busyness distributions (00:00 - 23:00) comparing weekday vs weekend footfall and midnight cloud kitchen delivery surges.",
        "primary_key": "popular_time_id",
        "lat_col": "latitude",
        "lon_col": "longitude"
    },
    "log_mobility": {
        "title": "OSRM Mobility & Origin-Destination Matrix",
        "description": "Actual road distances, free-flow vs. 1 PM lunch & 8 PM dinner peak travel times, congestion multipliers, and total order-to-door delivery SLAs.",
        "primary_key": "route_id",
        "lat_col": "dest_lat",
        "lon_col": "dest_lon"
    }
}

PINCODE_REGISTRY = {
    "560034": {
        "name": "Koramangala",
        "folder": "560034_koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "centroid": {"latitude": 12.9345, "longitude": 77.6245},
        "bounding_box": {"min_latitude": 12.9120, "min_longitude": 77.6080, "max_latitude": 12.9520, "max_longitude": 77.6520},
        "cloud_kitchen_feasibility_score": 9.2,
        "recommended_hubs": [
            {"hub_id": "HUB_560034_01", "name": "5th Block Industrial Layout", "lat": 12.9362, "lon": 77.6205},
            {"hub_id": "HUB_560034_02", "name": "Ejipura / Sony World Dark Kitchen Strip", "lat": 12.9385, "lon": 77.6270},
            {"hub_id": "HUB_560034_03", "name": "Jakkasandra Link Hub", "lat": 12.9225, "lon": 77.6395},
            {"hub_id": "HUB_560034_04", "name": "8th Block / Adugodi Perimeter Hub", "lat": 12.9398, "lon": 77.6168}
        ]
    },
    "560041": {
        "name": "Jayanagar",
        "folder": "560041_jayanagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "centroid": {"latitude": 12.9234, "longitude": 77.5924},
        "bounding_box": {"min_latitude": 12.9100, "min_longitude": 77.5700, "max_latitude": 12.9450, "max_longitude": 77.6080},
        "cloud_kitchen_feasibility_score": 9.1,
        "recommended_hubs": [
            {"hub_id": "HUB_560041_01", "name": "4th Block / 9th Block Commercial Border", "lat": 12.9265, "lon": 77.5930},
            {"hub_id": "HUB_560041_02", "name": "South End Circle / RV Road Metro Hub", "lat": 12.9360, "lon": 77.5795},
            {"hub_id": "HUB_560041_03", "name": "East End Main Road / 9th Block Extension", "lat": 12.9180, "lon": 77.5985},
            {"hub_id": "HUB_560041_04", "name": "Tilaknagar / Bannerghatta Link Hub", "lat": 12.9285, "lon": 77.5995}
        ]
    },
    "560038": {
        "name": "Indiranagar",
        "folder": "560038_indiranagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "centroid": {"latitude": 12.9797, "longitude": 77.6417},
        "bounding_box": {"min_latitude": 12.9620, "min_longitude": 77.6250, "max_latitude": 12.9920, "max_longitude": 77.6580},
        "cloud_kitchen_feasibility_score": 9.5,
        "recommended_hubs": [
            {"hub_id": "HUB_560038_01", "name": "Doopanahalli / 100ft Road Backstreet Pod", "lat": 12.9715, "lon": 77.6410},
            {"hub_id": "HUB_560038_02", "name": "CMH Road / Metro Station Perimeter Hub", "lat": 12.9785, "lon": 77.6445},
            {"hub_id": "HUB_560038_03", "name": "HAL 2nd Stage / 12th Main Cloud Cluster", "lat": 12.9740, "lon": 77.6465},
            {"hub_id": "HUB_560038_04", "name": "Binnamangala / Old Madras Road North Hub", "lat": 12.9860, "lon": 77.6380}
        ]
    },
    "560102": {
        "name": "HSR Layout",
        "folder": "560102_hsr_layout",
        "city": "Bengaluru",
        "state": "Karnataka",
        "centroid": {"latitude": 12.9151, "longitude": 77.6505},
        "bounding_box": {"min_latitude": 12.8980, "min_longitude": 77.6300, "max_latitude": 12.9280, "max_longitude": 77.6680},
        "cloud_kitchen_feasibility_score": 9.4,
        "recommended_hubs": [
            {"hub_id": "HUB_560102_01", "name": "27th Main / Sector 1 Commercial Strip", "lat": 12.9165, "lon": 77.6515},
            {"hub_id": "HUB_560102_02", "name": "Sector 7 / Hosur Road - Silk Board Gateway Hub", "lat": 12.9090, "lon": 77.6375},
            {"hub_id": "HUB_560102_03", "name": "Sector 3 / 19th Main Central Hub", "lat": 12.9125, "lon": 77.6450},
            {"hub_id": "HUB_560102_04", "name": "Sector 2 / Haralur - Sarjapur Link Hub", "lat": 12.9065, "lon": 77.6580}
        ]
    }
}

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_available_pincodes() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    pincode_list = []

    for pin, reg in PINCODE_REGISTRY.items():
        stats = {}
        for tbl in TABLE_METADATA.keys():
            try:
                pin_col = "origin_pincode" if tbl == "log_mobility" else "pincode"
                cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE ({pin_col} = ? OR target_pincode_zone = ?)", (pin, pin))
                stats[tbl] = cursor.fetchone()[0]
            except Exception:
                stats[tbl] = 0

        pincode_list.append({
            "pincode": pin,
            "name": reg["name"],
            "city": reg["city"],
            "state": reg["state"],
            "country": "India",
            "centroid": reg["centroid"],
            "bounding_box": reg["bounding_box"],
            "total_entities_extracted": sum(stats.values()),
            "datasets_count": len(TABLE_METADATA),
            "summary_breakdown": {
                "competitors": stats.get("fact_competitors", 0),
                "demand_generators": stats.get("fact_demand_generators", 0),
                "housing_proxies": stats.get("dim_housing_density_proxies", 0),
                "localities_micro_zones": stats.get("dim_localities", 0),
                "mobility_routes": stats.get("log_mobility", 0),
                "popular_times_profiles": stats.get("fact_popular_times", 0)
            },
            "cloud_kitchen_feasibility_score": reg["cloud_kitchen_feasibility_score"],
            "recommended_hub_coordinates": reg["recommended_hubs"]
        })
    conn.close()
    return pincode_list

def get_pincode_datasets(pincode: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    datasets = []
    
    for tbl, meta in TABLE_METADATA.items():
        cursor.execute(f"PRAGMA table_info({tbl})")
        columns = [{"name": row["name"], "type": row["type"]} for row in cursor.fetchall()]
        
        pin_col = "origin_pincode" if tbl == "log_mobility" else "pincode"
        cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE ({pin_col} = ? OR target_pincode_zone = ?)", (pincode, pincode))
        row_count = cursor.fetchone()[0]
        
        datasets.append({
            "dataset_name": tbl,
            "title": meta["title"],
            "description": meta["description"],
            "primary_key": meta["primary_key"],
            "row_count": row_count,
            "column_count": len(columns),
            "spatial_columns": {"lat": meta["lat_col"], "lon": meta["lon_col"]},
            "columns": columns,
            "supported_operations": ["GET (List)", "GET (Detail by ID)", "POST (Create)", "PATCH (Update)", "DELETE (Delete)"],
            "endpoints": {
                "list_and_filter": f"/api/v1/pincodes/{pincode}/datasets/{tbl}",
                "detail_or_edit": f"/api/v1/pincodes/{pincode}/datasets/{tbl}/{{id}}"
            }
        })
    conn.close()
    return datasets

def query_dataset(
    pincode: str,
    dataset_name: str,
    q: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    is_cloud_kitchen: Optional[bool] = None,
    min_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    if dataset_name not in TABLE_METADATA:
        raise ValueError(f"Unknown dataset '{dataset_name}'. Available: {list(TABLE_METADATA.keys())}")
    
    meta = TABLE_METADATA[dataset_name]
    lat_col = meta["lat_col"]
    lon_col = meta["lon_col"]

    conn = get_connection()
    cursor = conn.cursor()

    pin_col = "origin_pincode" if dataset_name == "log_mobility" else "pincode"
    conditions = [f"({pin_col} = ? OR target_pincode_zone = ?)"]
    params: List[Any] = [pincode, pincode]

    if q:
        cursor.execute(f"PRAGMA table_info({dataset_name})")
        tbl_cols = [r["name"] for r in cursor.fetchall()]
        search_clauses = []
        for candidate_col in ["outlet_name", "poi_name", "complex_name", "sub_locality_block", "destination_name", "brand_name"]:
            if candidate_col in tbl_cols:
                search_clauses.append(f"{candidate_col} LIKE ?")
                params.append(f"%{q}%")
        if search_clauses:
            conditions.append(f"({' OR '.join(search_clauses)})")

    if category:
        cursor.execute(f"PRAGMA table_info({dataset_name})")
        tbl_cols = [r["name"] for r in cursor.fetchall()]
        if "primary_category" in tbl_cols:
            conditions.append("primary_category LIKE ?")
            params.append(f"%{category}%")
        elif "category" in tbl_cols:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        elif "housing_category" in tbl_cols:
            conditions.append("housing_category LIKE ?")
            params.append(f"%{category}%")

    if min_rating is not None and dataset_name == "fact_competitors":
        conditions.append("rating >= ?")
        params.append(min_rating)

    if is_cloud_kitchen is not None and dataset_name == "fact_competitors":
        conditions.append("is_cloud_kitchen = ?")
        params.append(1 if is_cloud_kitchen else 0)

    if all(v is not None for v in [min_lat, min_lon, max_lat, max_lon]):
        conditions.append(f"{lat_col} >= ? AND {lat_col} <= ? AND {lon_col} >= ? AND {lon_col} <= ?")
        params.extend([min_lat, max_lat, min_lon, max_lon])

    where_clause = " WHERE " + " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM {dataset_name}{where_clause}"
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()[0]

    select_sql = f"SELECT * FROM {dataset_name}{where_clause} LIMIT ? OFFSET ?"
    select_params = list(params) + [limit, offset]
    cursor.execute(select_sql, select_params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if near_lat is not None and near_lon is not None and radius_km is not None:
        filtered = []
        for r in rows:
            r_lat = r.get(lat_col)
            r_lon = r.get(lon_col)
            if r_lat is not None and r_lon is not None:
                dist = haversine_km(near_lat, near_lon, float(r_lat), float(r_lon))
                if dist <= radius_km:
                    r["distance_from_query_km"] = round(dist, 3)
                    filtered.append(r)
        filtered.sort(key=lambda x: x.get("distance_from_query_km", 0))
        return filtered, len(filtered)

    return rows, total_count

def get_entity_by_id(pincode: str, dataset_name: str, entity_id: str) -> Optional[Dict[str, Any]]:
    if dataset_name not in TABLE_METADATA:
        raise ValueError(f"Unknown dataset '{dataset_name}'")
    pk = TABLE_PRIMARY_KEYS[dataset_name]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {dataset_name} WHERE {pk} = ? AND pincode = ?", (entity_id, pincode))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def insert_entity(pincode: str, dataset_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if dataset_name not in TABLE_METADATA:
        raise ValueError(f"Unknown dataset '{dataset_name}'")
    pk = TABLE_PRIMARY_KEYS[dataset_name]
    conn = get_connection()
    cursor = conn.cursor()

    if pk not in payload or not payload[pk]:
        cursor.execute(f"SELECT COUNT(*) FROM {dataset_name} WHERE pincode = ?", (pincode,))
        next_idx = cursor.fetchone()[0] + 1
        prefix = {
            "dim_localities": "LOC_CUSTOM",
            "dim_housing_density_proxies": "HSG_CUSTOM",
            "fact_demand_generators": "POI_CUSTOM",
            "fact_competitors": "FNB_CUSTOM",
            "fact_popular_times": "POP_CUSTOM",
            "log_mobility": "MOB_CUSTOM"
        }.get(dataset_name, "ENT")
        payload[pk] = f"{prefix}_{pincode}_{next_idx:04d}"

    payload["pincode"] = pincode
    cursor.execute(f"PRAGMA table_info({dataset_name})")
    valid_cols = {r["name"] for r in cursor.fetchall()}
    data_to_insert = {k: v for k, v in payload.items() if k in valid_cols}

    cols = list(data_to_insert.keys())
    placeholders = [":" + c for c in cols]
    sql = f"INSERT INTO {dataset_name} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    cursor.execute(sql, data_to_insert)
    conn.commit()
    conn.close()
    return get_entity_by_id(pincode, dataset_name, payload[pk])

def update_entity(pincode: str, dataset_name: str, entity_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if dataset_name not in TABLE_METADATA:
        raise ValueError(f"Unknown dataset '{dataset_name}'")
    pk = TABLE_PRIMARY_KEYS[dataset_name]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {dataset_name} WHERE {pk} = ? AND pincode = ?", (entity_id, pincode))
    if not cursor.fetchone():
        conn.close()
        return None

    cursor.execute(f"PRAGMA table_info({dataset_name})")
    valid_cols = {r["name"] for r in cursor.fetchall()}
    updates = {k: v for k, v in payload.items() if k in valid_cols and k not in [pk, "pincode"]}

    if not updates:
        conn.close()
        return get_entity_by_id(pincode, dataset_name, entity_id)

    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
    sql = f"UPDATE {dataset_name} SET {set_clause} WHERE {pk} = :entity_pk AND pincode = :entity_pin"
    params = dict(updates)
    params["entity_pk"] = entity_id
    params["entity_pin"] = pincode
    cursor.execute(sql, params)
    conn.commit()
    conn.close()
    return get_entity_by_id(pincode, dataset_name, entity_id)

def delete_entity(pincode: str, dataset_name: str, entity_id: str) -> bool:
    if dataset_name not in TABLE_METADATA:
        raise ValueError(f"Unknown dataset '{dataset_name}'")
    pk = TABLE_PRIMARY_KEYS[dataset_name]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {dataset_name} WHERE {pk} = ? AND pincode = ?", (entity_id, pincode))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_pincode_geojson(pincode: str) -> Dict[str, Any]:
    reg = PINCODE_REGISTRY.get(pincode)
    if not reg:
        return {"type": "FeatureCollection", "features": []}
    folder = reg["folder"]
    name_clean = reg["name"].lower().replace(" ", "_")
    geo_path = os.path.join(DATA_BASE_DIR, folder, f"{name_clean}_{pincode}_spatial_layers.geojson")
    if not os.path.exists(geo_path):
        geo_path = os.path.join(DATA_BASE_DIR, folder, f"koramangala_{pincode}_spatial_layers.geojson")
    if os.path.exists(geo_path):
        with open(geo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"type": "FeatureCollection", "features": []}
