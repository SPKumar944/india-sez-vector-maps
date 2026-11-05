# 🏢 India Special Economic Zones (SEZ) Plot Demarcation Master Plan GIS

Interactive GIS vector master plans, boundaries, and individual plot demarcation layouts extracted directly from the [India Industrial Land Bank (IILB)](https://indiaindustriallandbank.gov.in/) maintained by DPIIT, Ministry of Commerce and Industry, Government of India.

## 🚀 Live Interactive Dashboard
**Explore the Live Dashboard:** [https://spkumar944.github.io/india-sez-vector-maps/](https://spkumar944.github.io/india-sez-vector-maps/)

---

## 🏛️ Maharashtra District & SEZ Plot-Level Breakdown

The live dashboard provides plot-by-plot demarcation, an interactive searchable plot directory, and detailed datasheets for every demarcated parcel across Maharashtra’s premier SEZs:

### 1. Mumbai Suburban: SEEPZ Special Economic Zone & Marol
* **Plots Demarcated:** **464 individual plot polygons**
* **Status Breakdown:** 379 Allotted | 26 Vacant | 59 Reserved / Utilities
* **Key Allottee Companies Identified:** *UTI Asset Management*, *Micro World Softwares*, *Tata Hydro Electric*, *Dyna Hitech Power*, *Avcon Controls*, *Navnit Motors*, *Powerweave Software*, *Hotel Tunga Regale*, etc.
* **Vector File:** [`seepz_mumbai_plots.geojson`](seepz_mumbai_plots.geojson)

### 2. Pune: Rajiv Gandhi Infotech Park & SEZ (Hinjewadi Phase 1 & 2)
* **Plots Demarcated:** **504 individual plot polygons**
* **Status Breakdown:** 303 Allotted | 140 Vacant | 61 Reserved / Green Buffer / Utilities
* **Key Allottee Companies Identified:** *Wipro Limited*, *Birlasoft Ltd*, *Software Technology Parks of India (STPI)*, *Techbiz Info Services*, *Sunbeam Infotech*, *MJ Biopharma*, *Lemon Tree Hotels*, etc.
* **Vector File:** [`pune_hinjewadi_plots.geojson`](pune_hinjewadi_plots.geojson)

---

## 🎯 Plot-Level Attribute Details Available on Every Demarcated Unit

Each demarcated polygon in the dataset includes:
* **Plot Number:** Official survey/allotment plot identifier (e.g., `A-57`, `30`, `P-17`, `X-23`).
* **Allottee / Occupant Company:** Registered enterprise name or vacant indicator.
* **Plot Area:** Measured in square meters and converted to acres.
* **Allotment Status:** Color-coded (🟠 Allotted, 🟢 Vacant, 🟣 Reserved).
* **Zoning Category:** Industrial, Commercial, IT/ITeS, or Utility.
* **Tariff Valuation:** Rate per sq. meter where recorded in state industrial development corporation records.
* **Coordinates:** Centroid latitude/longitude and full boundary vector vertices (WGS84).

---

## 🛠️ CLI Vector Extractor (`extract_iilb_vector.py`)

A standalone Python script is provided to query and extract vector geometries directly from the IILB GeoServer backend for any bounding box or park in India:

```bash
# Demarcate individual plot vectors for any SEZ
python3 extract_iilb_vector.py --bbox 72.862,19.115,72.885,19.135 --layer plot --output seepz_plots.geojson

# Demarcate outer boundary polygons
python3 extract_iilb_vector.py --bbox 73.68,18.56,73.76,18.62 --layer park --output pune_boundary.geojson
```

---

## 💻 Compatibility
All `.geojson` files adhere to the **RFC 7946 OGC GeoJSON standard** and can be directly loaded into **QGIS**, **ArcGIS**, **AutoCAD / Civil 3D**, and web mapping frameworks.
