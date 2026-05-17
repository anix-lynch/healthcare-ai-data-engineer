#!/usr/bin/env python3
"""
Quick test script for Healthcare API
Run this after starting the API server
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, description):
    """Test an API endpoint"""
    print(f"\n🧪 Testing: {description}")
    print(f"   GET {endpoint}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Returned {len(str(data))} bytes")
            if isinstance(data, dict) and 'data' in data:
                print(f"   📊 Records: {data.get('count', 0)} / {data.get('total', 0)}")
            return True
        else:
            print(f"   ❌ Error: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - Is the API running?")
        print(f"   💡 Start it with: ./scripts/start_api.sh")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🏥 Healthcare API Test Suite")
    print("=" * 60)
    
    # Test endpoints
    tests = [
        ("/", "Root endpoint"),
        ("/api/encounters?limit=5", "Get encounters (limit 5)"),
        ("/api/encounters?condition=Diabetes&limit=3", "Filter by condition"),
        ("/api/encounters/0", "Get single encounter"),
        ("/api/patients?limit=5", "Get patients"),
        ("/api/doctors?limit=5", "Get doctors"),
        ("/api/hospitals?limit=5", "Get hospitals"),
        ("/api/conditions", "Get medical conditions"),
        ("/api/medications", "Get medications"),
        ("/api/insurance", "Get insurance providers"),
        ("/api/stats", "Get statistics"),
        ("/api/search?q=diabetes&limit=3", "Search functionality"),
    ]
    
    results = []
    for endpoint, description in tests:
        results.append(test_endpoint(endpoint, description))
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the API server.")
    print("=" * 60)

if __name__ == "__main__":
    main()

