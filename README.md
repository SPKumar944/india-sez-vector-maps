# 🗺️ India Special Economic Zones (SEZ) & Industrial Areas GIS Vector Maps

Interactive GIS vector master plans, boundaries, and individual plot layouts extracted directly from the [India Industrial Land Bank (IILB)](https://indiaindustriallandbank.gov.in/) maintained by DPIIT, Ministry of Commerce and Industry, Government of India.

## 🚀 Live Interactive Dashboard
**Explore the Live Dashboard:** [https://spkumar944.github.io/india-sez-vector-maps/](https://spkumar944.github.io/india-sez-vector-maps/)

---

## 📦 Extracted Vector Datasets (GeoJSON WGS84)

| Dataset | Type | Features / Plots | Area | Managing Agency |
| :--- | :--- | :--- | :--- | :--- |
| **[`seepz_mumbai_master_vector.geojson`](seepz_mumbai_master_vector.geojson)** | Full Plots + Boundary | **208 Plots + 3 Boundaries** | ~111 Acres | MIDC / Development Commissioner SEEPZ |
| **[`seepz_mumbai_plots.geojson`](seepz_mumbai_plots.geojson)** | Individual Plots | 208 Plots (Allotted/Vacant/Reserved) | 111 Acres | SEEPZ SEZ, Mumbai |
| **[`sri_city_sez_boundary.geojson`](sri_city_sez_boundary.geojson)** | SEZ Outer Master Boundaries | MultiPolygons (296 vertices) | 7,156 + 7,500 Acres | APIIC (Andhra Pradesh) |
| **[`auric_shendra_boundary.geojson`](auric_shendra_boundary.geojson)** | DMIC Smart City Node | 5-Star Industrial Area + SEZ | 2,139 Acres | AURIC / MIDC (Maharashtra) |
| **[`sanand_gidc_boundary.geojson`](sanand_gidc_boundary.geojson)** | Automotive Cluster | Industrial Park Outer Polygon | 237 Acres | GIDC (Gujarat) |

---

## 🛠️ CLI Vector Extractor (`extract_iilb_vector.py`)

A standalone Python script is provided to extract vector geometries directly from the IILB GeoServer backend for any bounding box or park in India:

```bash
# Extract outer boundary polygons for any region
python3 extract_iilb_vector.py --bbox 79.95,13.50,80.10,13.60 --layer park --output sricity.geojson

# Extract individual plot vectors
python3 extract_iilb_vector.py --bbox 72.862,19.115,72.885,19.135 --layer plot --output plots.geojson

# Extract infrastructure (NH highways, rail, power lines, ports)
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
