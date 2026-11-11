import os
import sys

# Ensure current workspace is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("RUNNING API TEST SUITE: Cloud Kitchen Geospatial Intelligence API")
    print("=" * 70)

    # 1. Health Check
    r = client.get("/api/v1/health")
    print("\n1. Health Check:")
    print("   Status:", r.status_code)
    print("   Response:", r.json())
    assert r.status_code == 200

    # 2. Pincode Discovery
    r = client.get("/api/v1/pincodes")
    print("\n2. Available Pincodes:")
    print("   Status:", r.status_code)
    pincodes = r.json()
    print(f"   Found {len(pincodes)} pincode(s): {pincodes[0]['pincode']} ({pincodes[0]['name']})")
    assert r.status_code == 200
    assert len(pincodes) >= 1

    # 3. Dataset Discovery for 560034
    r = client.get("/api/v1/pincodes/560034/datasets")
    print("\n3. Dataset Discovery (Pincode 560034):")
    print("   Status:", r.status_code)
    datasets = r.json()
    print(f"   Discovered {len(datasets)} active datasets:")
    for d in datasets:
        print(f"    - {d['dataset_name']} ({d['title']}): {d['row_count']} rows, {d['column_count']} cols")
    assert r.status_code == 200
    assert len(datasets) == 6

    # 4. Search Query: Fact Competitors for 'EatFit'
    r = client.get("/api/v1/pincodes/560034/datasets/fact_competitors?q=EatFit")
    print("\n4. Query Fact Competitors (Search 'EatFit'):")
    print("   Status:", r.status_code)
    res = r.json()
    print(f"   Found {res['count']} matching records out of {res['total_records']} total.")
    for rec in res["records"][:3]:
        print(f"    * {rec['outlet_name']} | Rating: ⭐ {rec['rating']} | Category: {rec['primary_category']}")
    assert r.status_code == 200
    assert res["count"] >= 1

    # 5. Spatial Radius Search: Within 1.0 km of Hub 1 (12.9362, 77.6205)
    r = client.get("/api/v1/pincodes/560034/datasets/fact_demand_generators?near_lat=12.9362&near_lon=77.6205&radius_km=1.0&limit=10")
    print("\n5. Spatial Radius Query (Demand POIs within 1 km of Hub 1):")
    print("   Status:", r.status_code)
    res = r.json()
    print(f"   Found {res['count']} POIs within 1 km:")
    for rec in res["records"][:4]:
        dist = rec.get("distance_from_query_km", "N/A")
        print(f"    * {rec['poi_name']} ({rec['category']}) — {dist} km away")
    assert r.status_code == 200

    # 6. Client EDIT: Create / Insert New Proposed Kitchen Pod
    new_pod = {
        "outlet_name": "API Test Dark Kitchen Pod - 5th Block Corner",
        "brand_name": "Antigravity Cloud Kitchens",
        "primary_category": "Cloud Kitchen",
        "cuisine_type": "Biryani, Gourmet Burgers, Asian Bowls",
        "sub_locality": "Koramangala 5th Block",
        "latitude": 12.9368,
        "longitude": 77.6210,
        "rating": 4.8,
        "total_reviews": 85,
        "price_level": "$$",
        "avg_order_value_inr": 420.0,
        "is_cloud_kitchen": 1,
        "estimated_monthly_orders": 4500,
        "dine_in_takeaway_delivery_flags": "Delivery"
    }
    r = client.post(
        "/api/v1/pincodes/560034/datasets/fact_competitors",
        json=new_pod,
        headers={"X-API-Key": "demo-editor-key"}
    )
    print("\n6. Client Edit: Create New Kitchen Pod (POST):")
    print("   Status:", r.status_code)
    created = r.json()
    created_id = created["record"]["competitor_id"]
    print(f"   Created Record ID: {created_id}")
    print(f"   Outlet: {created['record']['outlet_name']}")
    assert r.status_code == 201

    # 7. Client EDIT: Update Entity Fields (PATCH)
    patch_payload = {
        "rating": 4.9,
        "total_reviews": 150,
        "estimated_monthly_orders": 6000
    }
    r = client.patch(
        f"/api/v1/pincodes/560034/datasets/fact_competitors/{created_id}",
        json=patch_payload,
        headers={"X-API-Key": "demo-editor-key"}
    )
    print(f"\n7. Client Edit: Update Record {created_id} (PATCH):")
    print("   Status:", r.status_code)
    updated = r.json()["updated_record"]
    print(f"   Updated Rating: {updated['rating']}")
    print(f"   Updated Reviews: {updated['total_reviews']}")
    print(f"   Updated Monthly Orders: {updated['estimated_monthly_orders']}")
    assert r.status_code == 200
    assert updated["rating"] == 4.9
    assert updated["total_reviews"] == 150

    # 8. Client EDIT: Delete Created Entity (DELETE)
    r = client.delete(
        f"/api/v1/pincodes/560034/datasets/fact_competitors/{created_id}",
        headers={"X-API-Key": "demo-editor-key"}
    )
    print(f"\n8. Client Edit: Delete Record {created_id} (DELETE):")
    print("   Status:", r.status_code)
    print("   Response:", r.json())
    assert r.status_code == 200

    # Verify deletion
    r = client.get(f"/api/v1/pincodes/560034/datasets/fact_competitors/{created_id}")
    assert r.status_code == 404
    print("   Verified: Entity successfully removed from SQLite database.")

    # 9. GeoJSON Stream
    r = client.get("/api/v1/pincodes/560034/geojson")
    print("\n9. Master GeoJSON Stream:")
    print("   Status:", r.status_code)
    geo = r.json()
    print(f"   Type: {geo.get('type')}, Total Features: {len(geo.get('features', []))}")
    assert r.status_code == 200
    assert len(geo.get("features", [])) > 1000

    print("\n" + "=" * 70)
    print("ALL API TESTS PASSED SUCCESSFULLY! (100% Endpoints Verified)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
