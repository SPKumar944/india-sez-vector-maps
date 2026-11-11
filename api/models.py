from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PincodeCentroid(BaseModel):
    latitude: float
    longitude: float

class PincodeBoundingBox(BaseModel):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float

class RecommendedHub(BaseModel):
    hub_id: str
    name: str
    lat: float
    lon: float

class PincodeSummary(BaseModel):
    pincode: str
    name: str
    city: str
    state: str
    country: str
    centroid: PincodeCentroid
    bounding_box: PincodeBoundingBox
    total_entities_extracted: int
    datasets_count: int
    summary_breakdown: Dict[str, int]
    cloud_kitchen_feasibility_score: float
    recommended_hub_coordinates: List[RecommendedHub]

class ColumnMeta(BaseModel):
    name: str
    type: str

class DatasetMeta(BaseModel):
    dataset_name: str
    title: str
    description: str
    primary_key: str
    row_count: int
    column_count: int
    spatial_columns: Dict[str, str]
    columns: List[ColumnMeta]
    supported_operations: List[str]
    endpoints: Dict[str, str]

class PaginatedResponse(BaseModel):
    pincode: str
    dataset_name: str
    total_records: int
    limit: int
    offset: int
    count: int
    records: List[Dict[str, Any]]

class CompetitorCreate(BaseModel):
    outlet_name: str = Field(..., description="Name of the restaurant, cafe or cloud kitchen outlet")
    brand_name: Optional[str] = Field(None, description="Parent brand or chain name (e.g. Curefoods, EatFit, Domino's)")
    primary_category: str = Field(..., description="Category: Cloud Kitchen, Fast Food, Cafe, Casual Dining, Dessert")
    cuisine_type: str = Field(..., description="Comma-separated cuisines (e.g. North Indian, Biryani, Healthy Bowls)")
    sub_locality: str = Field(..., description="Sub-locality block (e.g. Koramangala 5th Block, 1st Block, Ejipura)")
    pincode: str = Field("560034", description="6-digit Pincode")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    rating: Optional[float] = Field(4.0, ge=1.0, le=5.0, description="Google Maps rating 1.0 - 5.0")
    total_reviews: Optional[int] = Field(50, ge=0, description="Total review count")
    price_level: Optional[str] = Field("$$", description="Google price band: $, $$, $$$, $$$$")
    avg_order_value_inr: Optional[float] = Field(350.0, description="Estimated Average Order Value (AOV) in INR")
    is_cloud_kitchen: Optional[int] = Field(0, description="1 if cloud kitchen / dark kitchen, 0 otherwise")
    estimated_monthly_orders: Optional[int] = Field(2000, description="Projected monthly delivery orders")
    dine_in_takeaway_delivery_flags: Optional[str] = Field("Delivery, Takeaway", description="Fulfillment flags")

class CompetitorUpdate(BaseModel):
    outlet_name: Optional[str] = None
    brand_name: Optional[str] = None
    primary_category: Optional[str] = None
    cuisine_type: Optional[str] = None
    sub_locality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    total_reviews: Optional[int] = None
    price_level: Optional[str] = None
    avg_order_value_inr: Optional[float] = None
    is_cloud_kitchen: Optional[int] = None
    estimated_monthly_orders: Optional[int] = None
    dine_in_takeaway_delivery_flags: Optional[str] = None

class DemandGeneratorCreate(BaseModel):
    poi_name: str
    category: str
    sub_category: Optional[str] = None
    sub_locality: str
    pincode: str = "560034"
    latitude: float
    longitude: float
    estimated_daily_footfall: Optional[int] = 500
    delivery_demand_weight_1_10: Optional[float] = 7.0
    peak_demand_window: Optional[str] = "Lunch (12:30 PM - 2:30 PM)"

class HousingProxyCreate(BaseModel):
    complex_name: str
    housing_category: str
    sub_locality: str
    pincode: str = "560034"
    latitude: float
    longitude: float
    estimated_dwelling_units: Optional[int] = 120
    estimated_residents: Optional[int] = 380
    income_segment: Optional[str] = "Upper Middle Class"
    security_gate_drop_friction: Optional[str] = "Moderate (Intercom / MyGate App)"
