"""
Example usage of Healthcare API
Demonstrates how to use the API in different contexts
"""

import requests
import pandas as pd
import json

BASE_URL = "http://localhost:8000"

# Example 1: Get all diabetic patients for analysis
def example_1_get_diabetic_patients():
    """Fetch diabetic patients for data analysis"""
    print("Example 1: Get Diabetic Patients")
    print("-" * 50)
    
    response = requests.get(f"{BASE_URL}/api/encounters", params={
        "condition": "Diabetes",
        "limit": 100
    })
    
    data = response.json()
    df = pd.DataFrame(data['data'])
    
    print(f"Found {data['total']} diabetic encounters")
    print(f"Average age: {df['Age'].mean():.1f}")
    print(f"Average billing: ${df['Billing Amount'].mean():,.2f}")
    print(f"Most common medication: {df['Medication'].mode()[0]}")
    print()


# Example 2: Use in dbt (conceptual - would use external table)
def example_2_dbt_usage():
    """How dbt would consume the API"""
    print("Example 2: dbt Integration (Conceptual)")
    print("-" * 50)
    print("""
    -- models/staging/stg_healthcare_api.sql
    WITH api_data AS (
        SELECT * FROM EXTERNAL_TABLE(
            'http://localhost:8000/api/encounters?limit=55500'
        )
    )
    SELECT 
        {{ dbt_utils.generate_surrogate_key(['Name', 'Date of Admission']) }} AS encounter_id,
        Name AS patient_name,
        Age,
        "Medical Condition" AS condition,
        "Billing Amount" AS billing_amount
    FROM api_data
    """)
    print()


# Example 3: Train ML model from API
def example_3_ml_training():
    """Fetch data for ML model training"""
    print("Example 3: ML Model Training")
    print("-" * 50)
    
    # Get all encounters
    all_data = []
    offset = 0
    limit = 1000
    
    while True:
        response = requests.get(f"{BASE_URL}/api/encounters", params={
            "limit": limit,
            "offset": offset
        })
        data = response.json()
        all_data.extend(data['data'])
        
        if len(all_data) >= data['total'] or len(data['data']) < limit:
            break
        offset += limit
    
    df = pd.DataFrame(all_data)
    print(f"Loaded {len(df):,} encounters for ML training")
    print(f"Features: {list(df.columns)}")
    print(f"Target variable: is_readmission (derived from dates)")
    print()


# Example 4: Power BI / Tableau connection
def example_4_bi_connection():
    """How BI tools connect to API"""
    print("Example 4: Power BI / Tableau Connection")
    print("-" * 50)
    print("""
    Power BI:
    1. Get Data → Web
    2. URL: http://localhost:8000/api/encounters?limit=55500
    3. Format: JSON
    4. Transform data as needed
    
    Tableau:
    1. Connect → Web Data Connector
    2. URL: http://localhost:8000/api/encounters?limit=55500
    3. Parse JSON response
    """)
    print()


# Example 5: AI Agent / LangChain integration
def example_5_ai_agent():
    """How AI agents can use the API"""
    print("Example 5: AI Agent Integration")
    print("-" * 50)
    print("""
    from langchain.tools import Tool
    
    healthcare_api = Tool(
        name="HealthcareAPI",
        description="Get patient encounter data",
        func=lambda query: requests.get(
            f'http://localhost:8000/api/search?q={query}'
        ).json()
    )
    
    # Agent can now query:
    # "Find all diabetic patients over 50"
    # "What's the average cost for cancer treatment?"
    # "Which hospitals have the most emergency admissions?"
    """)
    print()


# Example 6: Real-time dashboard
def example_6_dashboard():
    """Get statistics for dashboard"""
    print("Example 6: Dashboard Statistics")
    print("-" * 50)
    
    response = requests.get(f"{BASE_URL}/api/stats")
    stats = response.json()
    
    print("Key Metrics:")
    print(f"  Total Encounters: {stats['dataset']['total_encounters']:,}")
    print(f"  Unique Patients: {stats['dataset']['unique_patients']:,}")
    print(f"  Readmission Rate: {stats['clinical']['readmission_rate']}%")
    print(f"  Avg Cost: ${stats['financial']['avg_cost_per_encounter']:,.2f}")
    print(f"  Avg LOS: {stats['operational']['avg_length_of_stay']} days")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("🏥 Healthcare API - Usage Examples")
    print("=" * 60)
    print()
    
    try:
        # Test connection
        response = requests.get(f"{BASE_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ API is running!\n")
            
            example_1_get_diabetic_patients()
            example_2_dbt_usage()
            example_3_ml_training()
            example_4_bi_connection()
            example_5_ai_agent()
            example_6_dashboard()
            
        else:
            print("❌ API returned error")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API")
        print("💡 Start the API first: ./scripts/start_api.sh")
    except Exception as e:
        print(f"❌ Error: {e}")

