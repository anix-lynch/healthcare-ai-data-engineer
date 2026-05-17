"""
Healthcare API - Free REST API for synthetic patient data
Similar to FakeStore API but for healthcare/medical data

Author: Anix Lynch
Dataset: 55,500 patient encounters (2019-2024)
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import pandas as pd
from datetime import datetime
import os

# Initialize FastAPI
app = FastAPI(
    title="Healthcare API",
    description="Free REST API serving 55,500 synthetic patient encounters. No authentication required. Perfect for demos, learning, and AI agents!",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS (allow all origins for demo API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

