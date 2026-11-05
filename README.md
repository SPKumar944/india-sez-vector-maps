# 🗺️ India Special Economic Zones (SEZ) & Industrial Areas GIS Vector Maps

Interactive GIS vector master plans, boundaries, and individual plot demarcation layouts extracted directly from the [India Industrial Land Bank (IILB)](https://indiaindustriallandbank.gov.in/) maintained by DPIIT, Ministry of Commerce and Industry, Government of India.

## 🚀 Live Interactive Dashboard
**Explore the Live Dashboard:** [https://spkumar944.github.io/india-sez-vector-maps/](https://spkumar944.github.io/india-sez-vector-maps/)

---

## 🏛️ Maharashtra District-Wise Delving

The dashboard provides a dedicated district selector for **Maharashtra**, enabling exploration and comparison across major industrial clusters:

1. **District: Mumbai Suburban**
   * **Industrial Area:** SEEPZ Special Economic Zone & Marol Industrial Area
   * **Plots Demarcated:** **208 Plots**
   * **Key Focus:** Gems & Jewellery, Electronics, IT/ITeS (UTI Asset Management, Micro World Softwares, Tata Hydro Electric, etc.)

2. **District: Pune**
   * **Industrial Area:** Rajiv Gandhi Infotech Park & SEZ (Hinjewadi Phases I & II)
   * **Plots Demarcated:** **303 Plots**
   * **Key Focus:** Software, IT/ITeS, Biotech, Hardware (Wipro, Birlasoft, Techbiz, STPI, Sunbeam, etc.)

---

## 📦 Demarcated Vector Datasets (GeoJSON WGS84)

| Dataset | District / State | Demarcated Features | Area | Managing Agency |
| :--- | :--- | :--- | :--- | :--- |
| **[`pune_hinjewadi_master_vector.geojson`](pune_hinjewadi_master_vector.geojson)** | **Pune, Maharashtra** | **303 Plots + 3 Boundaries** | 849 Acres | MIDC |
| **[`seepz_mumbai_master_vector.geojson`](seepz_mumbai_master_vector.geojson)** | **Mumbai Suburban, Maharashtra** | **208 Plots + 3 Boundaries** | ~111 Acres | MIDC / Development Commissioner SEEPZ |
| **[`pune_hinjewadi_plots.geojson`](pune_hinjewadi_plots.geojson)** | Pune, Maharashtra | 303 Plots (Allotted/Vacant/Reserved) | 849 Acres | MIDC |
| **[`seepz_mumbai_plots.geojson`](seepz_mumbai_plots.geojson)** | Mumbai Suburban, Maharashtra | 208 Plots (Allotted/Vacant/Reserved) | ~111 Acres | SEEPZ SEZ, Mumbai |
| **[`sri_city_sez_boundary.geojson`](sri_city_sez_boundary.geojson)** | Tirupati, Andhra Pradesh | MultiPolygons (296 vertices) | 7,156 + 7,500 Acres | APIIC |
| **[`auric_shendra_boundary.geojson`](auric_shendra_boundary.geojson)** | Chhatrapati Sambhajinagar, MH | 5-Star Industrial Area + SEZ | 2,139 Acres | AURIC / MIDC |
| **[`sanand_gidc_boundary.geojson`](sanand_gidc_boundary.geojson)** | Ahmedabad, Gujarat | Industrial Park Outer Polygon | 237 Acres | GIDC |

---

## 🛠️ CLI Vector Extractor (`extract_iilb_vector.py`)

A standalone Python script is provided to query and extract vector geometries directly from the IILB GeoServer backend for any bounding box or park in India:

```bash
# Demarcate outer boundary polygons for any region
python3 extract_iilb_vector.py --bbox 73.68,18.56,73.76,18.62 --layer park --output pune_hinjewadi.geojson

# Demarcate individual plot vectors
python3 extract_iilb_vector.py --bbox 73.69,18.57,73.75,18.62 --layer plot --output hinjewadi_plots.geojson

# Demarcate infrastructure (NH highways, rail, power lines, ports)
python3 extract_iilb_vector.py --bbox 72.86,19.11,72.89,19.14 --layer power --output power_grid.geojson
```

Supported `--layer` options: `park`, `plot`, `nh`, `rail`, `ports`, `power`, `substation`, `gas`, `water`.

---

## 💻 Compatibility
All `.geojson` files in this repository adhere to the **RFC 7946 OGC GeoJSON standard** and can be directly loaded into:
* **QGIS / ArcGIS**
* **AutoCAD / Civil 3D** (via Map 3D or shapefile import)
* **Google Earth Pro**
* **Mapbox, Leaflet, or OpenLayers**
