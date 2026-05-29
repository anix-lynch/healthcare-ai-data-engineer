"""
Healthcare API - Free REST API for synthetic patient data
Similar to FakeStore API but for healthcare/medical data

Author: Anix Lynch
Dataset: 55,500 patient encounters (2019-2024)
"""

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

try:
    from .control_room import build_control_room_payload
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from control_room import build_control_room_payload  # type: ignore

try:
    from .trust_room import build_trust_room_payload
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from trust_room import build_trust_room_payload  # type: ignore

try:
    from .warehouse_room import build_warehouse_room_payload
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from warehouse_room import build_warehouse_room_payload  # type: ignore

try:
    from .retrieval import get_retriever
except Exception:
    try:
        from retrieval import get_retriever  # type: ignore
    except Exception:
        get_retriever = None  # type: ignore

try:
    from .classifier import classify_esi
except Exception:
    try:
        from classifier import classify_esi  # type: ignore
    except Exception:
        classify_esi = None  # type: ignore

try:
    from .ask import answer as grounded_answer
except Exception:
    try:
        from ask import answer as grounded_answer  # type: ignore
    except Exception:
        grounded_answer = None  # type: ignore

# Typed response contracts live in api/app/schemas.py.
# They are reference contracts (publishable as OpenAPI components manually if
# needed) — NOT wired as `response_model=` decorators, because the existing
# endpoints return rich nested aggregates that don't fit a single flat schema
# without losing fidelity. Kept as living documentation that:
#   1. names every endpoint's contract
#   2. is the target shape if we move to strict validation later
#   3. enforces the production-DB swap doesn't drift the API surface

# Initialize FastAPI
app = FastAPI(
    title="Healthcare API",
    description="Free REST API serving 55,500 synthetic patient encounters. No authentication required. Perfect for demos, learning, and AI agents!",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

BASE_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = BASE_DIR / "web"
PORTFOLIO_DIR = BASE_DIR / "portfolio"

# Enable CORS (allow all origins for demo API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Human UI layer (single artifact app): static UI + portfolio assets.
if WEB_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
if PORTFOLIO_DIR.exists():
    app.mount("/portfolio-assets", StaticFiles(directory=str(PORTFOLIO_DIR)), name="portfolio-assets")

# Load dataset
DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/raw/healthcare_dataset.csv")
df = pd.read_csv(DATA_PATH)

# Data preprocessing
df['Date of Admission'] = pd.to_datetime(df['Date of Admission'])
df['Discharge Date'] = pd.to_datetime(df['Discharge Date'])
df['Length of Stay'] = (df['Discharge Date'] - df['Date of Admission']).dt.days

print(f"✅ Loaded {len(df):,} patient encounters")

# Helper function to convert DataFrame to dict
def df_to_dict(dataframe):
    """Convert DataFrame to list of dicts with proper date serialization"""
    return dataframe.to_dict(orient='records')


@app.get("/")
def root():
    """API root - welcome message and endpoints"""
    return {
        "message": "Healthcare API - Free synthetic patient data",
        "version": "1.0.0",
        "total_encounters": len(df),
        "date_range": {
            "start": df['Date of Admission'].min().strftime('%Y-%m-%d'),
            "end": df['Date of Admission'].max().strftime('%Y-%m-%d')
        },
        "endpoints": {
            "encounters": "/api/encounters",
            "patients": "/api/patients",
            "doctors": "/api/doctors",
            "hospitals": "/api/hospitals",
            "conditions": "/api/conditions",
            "medications": "/api/medications",
            "insurance": "/api/insurance",
            "stats": "/api/stats"
        },
        "docs": "/docs",
        "github": "https://github.com/anix-lynch/healthcare-analytics"
    }


@app.get("/app")
def app_shell():
    """Serve the human cockpit UI shell."""
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not built")
    return FileResponse(index_path)


@app.get("/api/encounters")
def get_encounters(
    limit: int = Query(default=10, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    condition: Optional[str] = Query(None, description="Filter by medical condition"),
    admission_type: Optional[str] = Query(None, description="Filter by admission type (Emergency/Urgent/Elective)"),
    min_age: Optional[int] = Query(None, ge=0, le=120, description="Minimum patient age"),
    max_age: Optional[int] = Query(None, ge=0, le=120, description="Maximum patient age"),
    gender: Optional[str] = Query(None, description="Filter by gender (Male/Female)"),
    insurance: Optional[str] = Query(None, description="Filter by insurance provider"),
    sort_by: Optional[str] = Query("Date of Admission", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get patient encounters with filtering, pagination, and sorting
    
    Example: /api/encounters?condition=Diabetes&min_age=50&limit=20
    """
    filtered_df = df.copy()
    
    # Apply filters
    if condition:
        filtered_df = filtered_df[filtered_df['Medical Condition'].str.contains(condition, case=False, na=False)]
    if admission_type:
        filtered_df = filtered_df[filtered_df['Admission Type'].str.contains(admission_type, case=False, na=False)]
    if min_age:
        filtered_df = filtered_df[filtered_df['Age'] >= min_age]
    if max_age:
        filtered_df = filtered_df[filtered_df['Age'] <= max_age]
    if gender:
        filtered_df = filtered_df[filtered_df['Gender'].str.lower() == gender.lower()]
    if insurance:
        filtered_df = filtered_df[filtered_df['Insurance Provider'].str.contains(insurance, case=False, na=False)]
    
    # Sort
    if sort_by in filtered_df.columns:
        ascending = (order.lower() == 'asc')
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    # Pagination
    total = len(filtered_df)
    paginated_df = filtered_df.iloc[offset:offset+limit]
    
    # Convert to dict
    encounters = df_to_dict(paginated_df)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(encounters),
        "data": encounters
    }


@app.get("/api/encounters/{encounter_id}")
def get_encounter_by_id(encounter_id: int):
    """Get a single encounter by index ID"""
    if encounter_id < 0 or encounter_id >= len(df):
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    encounter = df.iloc[encounter_id].to_dict()
    return {
        "id": encounter_id,
        "data": encounter
    }


@app.get("/api/patients")
def get_patients(
    limit: int = Query(default=10, ge=1, le=100),
    age_group: Optional[str] = Query(None, description="Age group (0-17, 18-30, 31-50, 51-70, 70+)")
):
    """
    Get unique patients with their demographics
    """
    # Group by patient name (in real API, would use patient ID)
    patient_df = df.groupby('Name').agg({
        'Age': 'first',
        'Gender': 'first',
        'Blood Type': 'first',
        'Medical Condition': lambda x: list(x.unique()),
        'Date of Admission': 'count'  # Count encounters
    }).reset_index()
    
    patient_df.columns = ['Name', 'Age', 'Gender', 'Blood Type', 'Conditions', 'Total Encounters']
    
    # Filter by age group if provided
    if age_group:
        age_ranges = {
            '0-17': (0, 17),
            '18-30': (18, 30),
            '31-50': (31, 50),
            '51-70': (51, 70),
            '70+': (70, 200)
        }
        if age_group in age_ranges:
            min_age, max_age = age_ranges[age_group]
            patient_df = patient_df[(patient_df['Age'] >= min_age) & (patient_df['Age'] <= max_age)]
    
    total = len(patient_df)
    patients = df_to_dict(patient_df.head(limit))
    
    return {
        "total": total,
        "limit": limit,
        "count": len(patients),
        "data": patients
    }


@app.get("/api/doctors")
def get_doctors(
    limit: int = Query(default=10, ge=1, le=100),
    specialty: Optional[str] = Query(None, description="Filter by specialty")
):
    """Get list of doctors with their statistics"""
    doctor_df = df.groupby('Doctor').agg({
        'Name': 'count',  # Total patients
        'Billing Amount': 'mean',
        'Length of Stay': 'mean',
        'Medical Condition': lambda x: x.mode()[0] if len(x.mode()) > 0 else None  # Most common condition = specialty
    }).reset_index()
    
    doctor_df.columns = ['Doctor', 'Total Patients', 'Avg Billing', 'Avg LOS', 'Specialty']
    
    if specialty:
        doctor_df = doctor_df[doctor_df['Specialty'].str.contains(specialty, case=False, na=False)]
    
    total = len(doctor_df)
    doctors = df_to_dict(doctor_df.head(limit))
    
    return {
        "total": total,
        "limit": limit,
        "count": len(doctors),
        "data": doctors
    }


@app.get("/api/hospitals")
def get_hospitals(limit: int = Query(default=10, ge=1, le=100)):
    """Get list of hospitals with their statistics"""
    hospital_df = df.groupby('Hospital').agg({
        'Name': 'count',  # Total patients
        'Billing Amount': ['sum', 'mean'],
        'Length of Stay': 'mean',
        'Room Number': 'max'  # Max room = estimated bed count
    }).reset_index()
    
    hospital_df.columns = ['Hospital', 'Total Patients', 'Total Revenue', 'Avg Billing', 'Avg LOS', 'Bed Count']
    
    total = len(hospital_df)
    hospitals = df_to_dict(hospital_df.head(limit))
    
    return {
        "total": total,
        "limit": limit,
        "count": len(hospitals),
        "data": hospitals
    }


@app.get("/api/conditions")
def get_conditions():
    """Get all medical conditions with statistics"""
    condition_df = df.groupby('Medical Condition').agg({
        'Name': 'count',
        'Billing Amount': 'mean',
        'Length of Stay': 'mean',
        'Age': 'mean'
    }).reset_index()
    
    condition_df.columns = ['Condition', 'Total Cases', 'Avg Cost', 'Avg LOS', 'Avg Patient Age']
    condition_df = condition_df.sort_values('Total Cases', ascending=False)
    
    conditions = df_to_dict(condition_df)
    
    return {
        "total": len(conditions),
        "data": conditions
    }


@app.get("/api/medications")
def get_medications():
    """Get all medications with usage statistics"""
    med_df = df.groupby('Medication').agg({
        'Name': 'count',
        'Medical Condition': lambda x: list(x.value_counts().head(3).index)  # Top 3 conditions
    }).reset_index()
    
    med_df.columns = ['Medication', 'Total Prescriptions', 'Common Conditions']
    med_df = med_df.sort_values('Total Prescriptions', ascending=False)
    
    medications = df_to_dict(med_df)
    
    return {
        "total": len(medications),
        "data": medications
    }


@app.get("/api/insurance")
def get_insurance_providers():
    """Get insurance providers with coverage statistics"""
    insurance_df = df.groupby('Insurance Provider').agg({
        'Name': 'count',
        'Billing Amount': ['mean', 'sum']
    }).reset_index()
    
    insurance_df.columns = ['Insurance Provider', 'Total Covered', 'Avg Reimbursement', 'Total Billing']
    insurance_df = insurance_df.sort_values('Total Covered', ascending=False)
    
    providers = df_to_dict(insurance_df)
    
    return {
        "total": len(providers),
        "data": providers
    }


@app.get("/api/stats")
def get_statistics():
    """Get overall dataset statistics"""
    
    # Calculate readmissions (simplified: same patient within 30 days)
    df_sorted = df.sort_values(['Name', 'Date of Admission'])
    df_sorted['Days Since Last'] = df_sorted.groupby('Name')['Date of Admission'].diff().dt.days
    readmissions = (df_sorted['Days Since Last'] <= 30).sum()
    
    return {
        "dataset": {
            "total_encounters": len(df),
            "unique_patients": df['Name'].nunique(),
            "unique_doctors": df['Doctor'].nunique(),
            "unique_hospitals": df['Hospital'].nunique(),
            "date_range": {
                "start": df['Date of Admission'].min().strftime('%Y-%m-%d'),
                "end": df['Date of Admission'].max().strftime('%Y-%m-%d'),
                "years": (df['Date of Admission'].max() - df['Date of Admission'].min()).days / 365
            }
        },
        "demographics": {
            "avg_age": round(df['Age'].mean(), 1),
            "age_range": {"min": int(df['Age'].min()), "max": int(df['Age'].max())},
            "gender_distribution": df['Gender'].value_counts().to_dict()
        },
        "clinical": {
            "conditions": df['Medical Condition'].value_counts().to_dict(),
            "admission_types": df['Admission Type'].value_counts().to_dict(),
            "test_results": df['Test Results'].value_counts().to_dict(),
            "readmission_rate": round((readmissions / len(df)) * 100, 2)
        },
        "financial": {
            "total_billing": round(df['Billing Amount'].sum(), 2),
            "avg_cost_per_encounter": round(df['Billing Amount'].mean(), 2),
            "cost_range": {
                "min": round(df['Billing Amount'].min(), 2),
                "max": round(df['Billing Amount'].max(), 2)
            }
        },
        "operational": {
            "avg_length_of_stay": round(df['Length of Stay'].mean(), 1),
            "los_range": {"min": int(df['Length of Stay'].min()), "max": int(df['Length of Stay'].max())},
            "total_patient_days": int(df['Length of Stay'].sum())
        }
    }


@app.get("/api/control-room")
def get_control_room():
    """Return the display payload used by the A1 operational dashboard mock."""
    return build_control_room_payload()


@app.get("/api/portfolio/a1")
def get_portfolio_a1():
    """Alias for the A1 control-room payload."""
    return build_control_room_payload()


@app.get("/api/trust-room")
def get_trust_room():
    """Return the display payload used by the A2 trust dashboard mock."""
    return build_trust_room_payload()


@app.get("/api/portfolio/a2")
def get_portfolio_a2():
    """Alias for the A2 trust-investigation payload."""
    return build_trust_room_payload()


@app.get("/api/warehouse-room")
def get_warehouse_room():
    """Return the display payload used by the A5 warehouse explorer."""
    return build_warehouse_room_payload()


@app.get("/api/portfolio/a5")
def get_portfolio_a5():
    """Alias for the A5 warehouse-explorer payload."""
    return build_warehouse_room_payload()


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Search across all fields
    Example: /api/search?q=diabetes
    """
    # Search in multiple columns
    mask = (
        df['Name'].str.contains(q, case=False, na=False) |
        df['Medical Condition'].str.contains(q, case=False, na=False) |
        df['Doctor'].str.contains(q, case=False, na=False) |
        df['Hospital'].str.contains(q, case=False, na=False) |
        df['Medication'].str.contains(q, case=False, na=False)
    )
    
    results_df = df[mask]
    total = len(results_df)
    results = df_to_dict(results_df.head(limit))
    
    return {
        "query": q,
        "total": total,
        "limit": limit,
        "count": len(results),
        "data": results
    }


# ─────────────────────────────────────────────────────────────────────
# L1-feeds-downstream-chefs endpoints (added 2026-05-18)
# ─────────────────────────────────────────────────────────────────────
# These two endpoints prove the L1 substrate (healthcare-api pantry) can
# feed BOTH retrieval-style consumers (genai-engineer / RAG) AND
# classification-style consumers (forward-deployed-engineer / ESI triage)
# from the same enriched corpus. Same pantry, two chefs.

@app.get("/api/retrieve")
async def retrieve(
    q: str = Query(..., description="Query text (free-form clinical)"),
    k: int = Query(5, ge=1, le=20, description="Top-K results"),
):
    """
    BM25 retrieval over the 497-row enriched holdout corpus.

    Feeds the retrieval-style consumer (genai-engineer / RAG runtime).
    Returns top-K matches with score, age, gender, medical condition,
    chief complaint, ESI ground-truth label, and HPI snippet.

    Test against data/quality/golden_retrieval_set.json (20 queries).
    """
    if get_retriever is None:
        raise HTTPException(status_code=503, detail="retriever unavailable in this environment")
    results = get_retriever().search(q, k=k)
    return {
        "query": q,
        "k": k,
        "method": "bm25_okapi",
        "corpus": "enriched_use_397.jsonl",
        "results": results,
    }


@app.post("/api/classify")
async def classify(payload: dict = Body(...)):
    """
    Rule-based ESI triage classifier with customer-signed safety floors.

    Feeds the classification-style consumer (forward-deployed-engineer
    ER triage). Applies the 10 acceptance criteria from
    data/quality/esi_eval_dataset.json (ACC-001..ACC-009, etc).

    Input:
      {
        "age": 62,
        "chief_complaint": "Chest pain, shortness of breath, diaphoresis",
        "vitals": {
          "bp_systolic": 142, "bp_diastolic": 88,
          "heart_rate": 108, "respiratory_rate": 22,
          "temperature_f": 98.8, "spo2_pct": 93
        }
      }

    Output: { esi_tier, rules_fired[], confidence, human_review_required }
    """
    if classify_esi is None:
        raise HTTPException(status_code=503, detail="classifier unavailable in this environment")
    return classify_esi(payload)


@app.get("/api/ask")
async def ask(
    q: str = Query(..., min_length=2, description="Free-form clinical question"),
    k: int = Query(5, ge=1, le=10, description="Top-K evidence rows to ground on"),
):
    """
    L2 grounded answer: BM25 retrieves top-K rows from the enriched corpus,
    then Gemini answers ONLY from that evidence with [doc N] citations.

    Grounds exclusively on the redacted enriched narratives
    (enriched_use_397.jsonl) — never the raw PII table. If Vertex is
    unavailable the retrieval sources still return (grounded=false).

    Example: /api/ask?q=which%20patients%20show%20cardiac%20red%20flags
    """
    if grounded_answer is None:
        raise HTTPException(status_code=503, detail="ask path unavailable in this environment")
    return grounded_answer(q, k=k)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
