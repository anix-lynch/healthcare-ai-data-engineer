"""Pydantic response models for the Healthcare API.

Used as `response_model=` on every endpoint in api/app/main.py so:
    1. OpenAPI docs auto-generate with proper field types
    2. unexpected/hallucinated fields get filtered at serialization time
    3. response shape is a contract — change here = visible diff in docs

Honest scope: these schemas describe what the in-memory pandas-backed API
returns today. The PRODUCTION path swaps pandas-read-CSV for a warehouse
query (DuckDB local · BigQuery / Snowflake / Fabric cloud). Schemas stay
identical across both backends.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")  # drop unexpected fields, never error


class EndpointInfo(_Base):
    method: str
    path: str
    description: str


class RootResponse(_Base):
    name: str = "Healthcare API"
    description: str
    version: str
    total_encounters: int
    endpoints: list[EndpointInfo]


class Encounter(_Base):
    """One row from healthcare_dataset.csv (denormalized view)."""
    Name: str | None = None
    Age: int | float | None = None
    Gender: str | None = None
    Medical_Condition: str | None = Field(None, alias="Medical Condition")
    Date_of_Admission: str | None = Field(None, alias="Date of Admission")
    Doctor: str | None = None
    Hospital: str | None = None
    Insurance_Provider: str | None = Field(None, alias="Insurance Provider")
    Billing_Amount: float | None = Field(None, alias="Billing Amount")
    Room_Number: int | float | None = Field(None, alias="Room Number")
    Admission_Type: str | None = Field(None, alias="Admission Type")
    Discharge_Date: str | None = Field(None, alias="Discharge Date")
    Medication: str | None = None
    Test_Results: str | None = Field(None, alias="Test Results")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class EncounterListResponse(_Base):
    total: int = Field(..., description="rows matching the filter, before pagination")
    returned: int = Field(..., description="rows in this response (≤ limit)")
    limit: int
    offset: int
    data: list[dict] = Field(default_factory=list, description=(
        "encounter rows. dict instead of Encounter typed list to preserve "
        "the original alias-laden field names for backward compatibility."
    ))


class PatientSummary(_Base):
    patient_name: str | None = None
    age: int | float | None = None
    gender: str | None = None
    encounter_count: int = 0


class PatientListResponse(_Base):
    total: int
    returned: int
    limit: int
    offset: int
    data: list[dict]


class DoctorSummary(_Base):
    doctor: str
    encounter_count: int


class DoctorListResponse(_Base):
    total: int
    returned: int
    data: list[dict]


class HospitalSummary(_Base):
    hospital: str
    encounter_count: int


class HospitalListResponse(_Base):
    total: int
    returned: int
    data: list[dict]


class StringListResponse(_Base):
    """For /api/conditions · /api/medications · /api/insurance."""
    total: int
    data: list[str]


class StatsResponse(_Base):
    """Aggregate over the whole corpus. Shape is flexible — values are dict
    of counts per dimension. Pydantic preserves the shape but doesn't enforce
    inner dict schemas (pandas value-counts output varies)."""
    total_encounters: int
    by_condition: dict[str, int] | None = None
    by_admission_type: dict[str, int] | None = None
    by_gender: dict[str, int] | None = None
    avg_billing_amount: float | None = None
    avg_age: float | None = None
    date_range: dict[str, Any] | None = None


class SearchResponse(_Base):
    query: str
    total_matches: int
    returned: int
    data: list[dict]
