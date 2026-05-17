"""Pydantic reference contracts for the Healthcare API.

These models document the response shape of every endpoint in main.py.
They are NOT wired as `response_model=` decorators today because the
existing endpoints return rich nested aggregates (per-condition counts,
demographic / clinical / financial / operational nested blocks) that
benefit from staying as raw dicts during the demo phase.

Why publish them as a separate file then?
    1. Living contract for consumers — they can `pip install` this package
       and use the models for validation client-side.
    2. Target shape when we promote endpoints to strict validation.
    3. Guarantees the production-DB swap (pandas → DuckDB / warehouse)
       doesn't drift the API surface — the contract stays the same.

Production swap path (also documented in README):
    api/app/main.py loads the CSV into pandas at cold start. For >100K rows:
        - DuckDB local:  `con.execute("SELECT ... FROM read_csv_auto(...)")`
        - Cloud warehouse: BigQuery / Snowflake / Fabric query layer
    Either backend returns the SAME shapes documented here.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")  # forward-compat: ignore new fields


# ── GET / ──────────────────────────────────────────────────────────────
class RootResponse(_Base):
    message: str
    version: str
    total_encounters: int
    date_range: dict[str, str]
    endpoints: dict[str, str]
    docs: str
    github: str | None = None


# ── GET /api/encounters ────────────────────────────────────────────────
class EncounterListResponse(_Base):
    total: int = Field(..., description="rows matching filter, pre-pagination")
    limit: int
    offset: int
    count: int = Field(..., description="rows in this response")
    data: list[dict] = Field(default_factory=list)


# ── GET /api/encounters/{encounter_id} ─────────────────────────────────
class EncounterDetailResponse(_Base):
    id: int
    data: dict


# ── GET /api/patients · /api/doctors · /api/hospitals ──────────────────
class GroupedListResponse(_Base):
    """Used by /patients, /doctors, /hospitals. They all return the same
    shape — group-by aggregates with total + limit + count + data."""
    total: int
    limit: int
    count: int
    data: list[dict]


# ── GET /api/conditions · /api/medications · /api/insurance ────────────
class CatalogListResponse(_Base):
    """Used by /conditions, /medications, /insurance.
    No pagination — returns full catalog with per-item aggregates."""
    total: int
    data: list[dict]


# ── GET /api/stats ─────────────────────────────────────────────────────
class StatsDatasetBlock(_Base):
    total_encounters: int
    unique_patients: int
    unique_doctors: int
    unique_hospitals: int
    date_range: dict[str, Any]


class StatsDemographicsBlock(_Base):
    avg_age: float
    age_range: dict[str, int]
    gender_distribution: dict[str, int]


class StatsClinicalBlock(_Base):
    conditions: dict[str, int]
    admission_types: dict[str, int]
    test_results: dict[str, int]
    readmission_rate: float = Field(..., description="% within 30 days")


class StatsFinancialBlock(_Base):
    total_billing: float
    avg_cost_per_encounter: float
    cost_range: dict[str, float]


class StatsOperationalBlock(_Base):
    avg_length_of_stay: float
    los_range: dict[str, int]
    total_patient_days: int


class StatsResponse(_Base):
    dataset: StatsDatasetBlock
    demographics: StatsDemographicsBlock
    clinical: StatsClinicalBlock
    financial: StatsFinancialBlock
    operational: StatsOperationalBlock


# ── GET /api/search ────────────────────────────────────────────────────
class SearchResponse(_Base):
    query: str
    total: int
    limit: int
    count: int
    data: list[dict]
