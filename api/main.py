import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Path, Body, Depends, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from api.database import (
    get_available_pincodes,
    get_pincode_datasets,
    query_dataset,
    get_entity_by_id,
    insert_entity,
    update_entity,
    delete_entity,
    get_pincode_geojson,
    TABLE_METADATA
)
from api.models import (
    PincodeSummary,
    DatasetMeta,
    PaginatedResponse,
    CompetitorCreate,
    CompetitorUpdate,
    DemandGeneratorCreate,
    HousingProxyCreate
)

API_TITLE = "Cloud Kitchen Geospatial Intelligence API"
API_DESCRIPTION = """
## Cloud Kitchen Location Intelligence & Market Feasibility API

This RESTful API allows client applications to discover, query, and **edit** rich geospatial datasets for cloud kitchen site selection, demand mapping, and competitor saturation.

### Key Capabilities:
- **Dataset Discovery:** Inspect all available datasets and schemas for any target Pincode (e.g. `560034` Koramangala).
- **Geospatial & Semantic Queries:** Perform radius searches (`near_lat`, `near_lon`, `radius_km`), bounding-box queries, and full-text searches across 1,185 POIs.
- **Client Editing & CRUD:** Add, update (PATCH), or remove competitor profiles, proposed dark kitchen hubs, and demand entities.
- **GeoJSON Streaming:** Stream layer-compliant GeoJSON for Mapbox, Leaflet, Google Maps, or Kepler.gl.

### Available Datasets:
1. `fact_competitors`: 473 F&B outlets (Curefoods, EatFit, Rebel Foods, Domino's, cloud kitchens, ratings, AOVs).
2. `fact_demand_generators`: 510 tech parks, colleges, hospitals, and transit hubs.
3. `dim_housing_density_proxies`: 133 gated communities, high-rises, and PGs with drop-off friction scores.
4. `dim_localities`: 69 micro-localities with electoral roll Gen Z / Millennial age cohorts and commercial kitchen rents.
5. `fact_popular_times`: 140 24-hour weekday vs. weekend footfall & order surge curves.
6. `log_mobility`: 160 OSRM-routed Origin-Destination delivery SLAs and congestion metrics.
"""

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for direct web / mobile frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API Key Security Header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEYS = {
    "demo-read-key": {"role": "read", "client": "Demo Read-Only Client"},
    "demo-editor-key": {"role": "editor", "client": "Partner Client (Read/Write)"},
    "admin-master-key": {"role": "admin", "client": "Platform Admin"}
}

def verify_api_access(required_role: str = "read"):
    def dependency(api_key: Optional[str] = Security(API_KEY_HEADER)):
        # If running in development without configured keys, default to full access
        if not api_key:
            return {"role": "editor", "client": "Default Client (Dev Mode)"}
        
        auth = API_KEYS.get(api_key)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key. Use 'demo-editor-key' or 'demo-read-key' for testing."
            )
        
        if required_role == "editor" and auth["role"] not in ["editor", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Client does not have edit permissions on this pincode dataset."
            )
        return auth
    return dependency


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Returns API health status, available datasets, and database connectivity."""
    pincodes = get_available_pincodes()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "sqlite_connected",
        "available_pincodes": [p["pincode"] for p in pincodes],
        "total_entities_available": sum(p["total_entities_extracted"] for p in pincodes)
    }


@app.get(
    "/api/v1/pincodes",
    response_model=List[PincodeSummary],
    tags=["Pincode Discovery"]
)
def list_available_pincodes(auth: dict = Depends(verify_api_access("read"))):
    """List all geographical pincode regions available in the database with summary stats and feasibility scores."""
    return get_available_pincodes()


@app.get(
    "/api/v1/pincodes/{pincode}",
    response_model=PincodeSummary,
    tags=["Pincode Discovery"]
)
def get_pincode_overview(
    pincode: str = Path(..., openapi_examples="560034", description="6-digit Indian Postal Pincode"),
    auth: dict = Depends(verify_api_access("read"))
):
    """Retrieve detailed geographical bounding box, centroid, and entity statistics for a target pincode."""
    pincodes = get_available_pincodes()
    match = next((p for p in pincodes if p["pincode"] == pincode), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Pincode '{pincode}' not found in registry.")
    return match


@app.get(
    "/api/v1/pincodes/{pincode}/datasets",
    response_model=List[DatasetMeta],
    tags=["Dataset Discovery"]
)
def list_datasets_for_pincode(
    pincode: str = Path(..., openapi_examples="560034"),
    auth: dict = Depends(verify_api_access("read"))
):
    """
    **Dataset Discovery Endpoint**:
    Returns the complete list of datasets available for this pincode, including record counts,
    column schemas, primary keys, and supported query/edit operations.
    """
    try:
        return get_pincode_datasets(pincode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/pincodes/{pincode}/datasets/{dataset_name}",
    response_model=PaginatedResponse,
    tags=["Data Querying"]
)
def query_pincode_dataset(
    pincode: str = Path(..., openapi_examples="560034"),
    dataset_name: str = Path(..., openapi_examples="fact_competitors", description="Name of dataset (e.g. fact_competitors, fact_demand_generators, dim_housing_density_proxies)"),
    q: Optional[str] = Query(None, description="Full-text search query (matches name, brand, or locality)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. 'Cloud Kitchen', 'IT Park', 'Gated Community')"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="Minimum Google rating (for competitors)"),
    is_cloud_kitchen: Optional[bool] = Query(None, description="Filter solely for cloud/dark kitchens"),
    near_lat: Optional[float] = Query(None, description="Spatial search: center latitude"),
    near_lon: Optional[float] = Query(None, description="Spatial search: center longitude"),
    radius_km: Optional[float] = Query(None, ge=0.1, le=25.0, description="Spatial search: radius in kilometers"),
    min_lat: Optional[float] = Query(None, description="Bounding box filter: minimum latitude"),
    min_lon: Optional[float] = Query(None, description="Bounding box filter: minimum longitude"),
    max_lat: Optional[float] = Query(None, description="Bounding box filter: maximum latitude"),
    max_lon: Optional[float] = Query(None, description="Bounding box filter: maximum longitude"),
    limit: int = Query(50, ge=1, le=500, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    auth: dict = Depends(verify_api_access("read"))
):
    """
    **Query Dataset Rows**:
    Retrieve records with multi-dimensional filtering, including geospatial radius and bounding-box queries.
    """
    try:
        rows, total = query_dataset(
            pincode=pincode,
            dataset_name=dataset_name,
            q=q,
            category=category,
            min_rating=min_rating,
            is_cloud_kitchen=is_cloud_kitchen,
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            near_lat=near_lat,
            near_lon=near_lon,
            radius_km=radius_km,
            limit=limit,
            offset=offset
        )
        return PaginatedResponse(
            pincode=pincode,
            dataset_name=dataset_name,
            total_records=total,
            limit=limit,
            offset=offset,
            count=len(rows),
            records=rows
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get(
    "/api/v1/pincodes/{pincode}/datasets/{dataset_name}/{entity_id}",
    tags=["Data Querying"]
)
def get_single_entity(
    pincode: str = Path(..., openapi_examples="560034"),
    dataset_name: str = Path(..., openapi_examples="fact_competitors"),
    entity_id: str = Path(..., openapi_examples="FNB_560034_001", description="Primary key ID of entity"),
    auth: dict = Depends(verify_api_access("read"))
):
    """Fetch the full record for a single entity by its primary key."""
    try:
        entity = get_entity_by_id(pincode, dataset_name, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in {dataset_name}.")
        return entity
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post(
    "/api/v1/pincodes/{pincode}/datasets/{dataset_name}",
    status_code=status.HTTP_201_CREATED,
    tags=["Client Dataset Editing (CRUD)"]
)
def create_dataset_entity(
    pincode: str = Path(..., openapi_examples="560034"),
    dataset_name: str = Path(..., openapi_examples="fact_competitors"),
    payload: Dict[str, Any] = Body(
        ...,
        openapi_examples={
            "outlet_name": "Proposed Dark Kitchen Pod - Sony World Corner",
            "brand_name": "New Venture Kitchen",
            "primary_category": "Cloud Kitchen",
            "cuisine_type": "Biryani, Rolls, North Indian",
            "sub_locality": "Koramangala 4th Block",
            "latitude": 12.9365,
            "longitude": 77.6255,
            "rating": 4.5,
            "total_reviews": 120,
            "price_level": "$$",
            "avg_order_value_inr": 380,
            "is_cloud_kitchen": 1,
            "estimated_monthly_orders": 3500,
            "dine_in_takeaway_delivery_flags": "Delivery"
        }
    ),
    auth: dict = Depends(verify_api_access("editor"))
):
    """
    **Create / Add Entity to Pincode Dataset**:
    Allows the client to add a newly surveyed restaurant, a proposed dark kitchen hub, or a demand POI.
    Requires `editor` role permissions.
    """
    try:
        payload["pincode"] = pincode
        new_record = insert_entity(pincode, dataset_name, payload)
        return {
            "status": "success",
            "message": f"Created new record in {dataset_name}",
            "editor": auth["client"],
            "record": new_record
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create record: {str(e)}")


@app.patch(
    "/api/v1/pincodes/{pincode}/datasets/{dataset_name}/{entity_id}",
    tags=["Client Dataset Editing (CRUD)"]
)
def edit_dataset_entity(
    pincode: str = Path(..., openapi_examples="560034"),
    dataset_name: str = Path(..., openapi_examples="fact_competitors"),
    entity_id: str = Path(..., openapi_examples="FNB_560034_001"),
    payload: Dict[str, Any] = Body(
        ...,
        openapi_examples={
            "rating": 4.6,
            "total_reviews": 520,
            "avg_order_value_inr": 420,
            "estimated_monthly_orders": 4500
        }
    ),
    auth: dict = Depends(verify_api_access("editor"))
):
    """
    **Edit / Update Entity in Pincode Dataset**:
    Allows the client to update any fields of an existing entity (e.g. order volume, rating, price band, coordinates, or category).
    Requires `editor` role permissions.
    """
    try:
        updated = update_entity(pincode, dataset_name, entity_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in {dataset_name}.")
        return {
            "status": "success",
            "message": f"Updated {entity_id} in {dataset_name}",
            "editor": auth["client"],
            "updated_record": updated
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update record: {str(e)}")


@app.delete(
    "/api/v1/pincodes/{pincode}/datasets/{dataset_name}/{entity_id}",
    tags=["Client Dataset Editing (CRUD)"]
)
def delete_dataset_entity(
    pincode: str = Path(..., openapi_examples="560034"),
    dataset_name: str = Path(..., openapi_examples="fact_competitors"),
    entity_id: str = Path(..., openapi_examples="FNB_CUSTOM_560034_0001"),
    auth: dict = Depends(verify_api_access("editor"))
):
    """
    **Delete Entity from Pincode Dataset**:
    Remove an entity from the active dataset. Requires `editor` role permissions.
    """
    try:
        success = delete_entity(pincode, dataset_name, entity_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in {dataset_name}.")
        return {
            "status": "success",
            "message": f"Entity '{entity_id}' deleted from {dataset_name}.",
            "editor": auth["client"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete record: {str(e)}")


@app.get(
    "/api/v1/pincodes/{pincode}/geojson",
    tags=["Geospatial Export"]
)
def get_geojson_layers(
    pincode: str = Path(..., openapi_examples="560034"),
    auth: dict = Depends(verify_api_access("read"))
):
    """
    **Master GeoJSON Stream**:
    Returns the complete GeoJSON FeatureCollection (including boundaries, candidate hubs,
    competitors, POIs, and delivery routes) for instant map rendering.
    """
    return get_pincode_geojson(pincode)
