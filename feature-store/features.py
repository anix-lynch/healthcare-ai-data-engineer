"""
L1.25 Feature layer (Feast on BigQuery).

Built ON the L1 gold marts (dbt -> BigQuery, project bchan-genai-lab,
dataset healthcare_analytics). Consumed BY the L1.5 signal layer
(anomaly / cluster / classify) and any downstream ML model.

Point-in-time correctness
--------------------------
The offline source is a query against the gold fact `fact_patient_encounters`
(one row per encounter, keyed by patient_key) carrying a real *event* timestamp
(admission date). Aggregate features are PRIOR-ONLY:

  - prior_encounter_count    -> previous_admission_count   (precomputed in the
                                gold mart; counts admissions strictly before
                                this one)
  - days_since_last_admission-> gap to the previous admission
  - prior_avg_los            -> AVG(length_of_stay) over a window that excludes
                                the current row
                                (ROWS UNBOUNDED PRECEDING .. 1 PRECEDING)

Because every aggregate looks only at rows strictly before the encounter's
event_timestamp, a Feast point-in-time join (get_historical_features) will not
leak the future. has_chronic_comorbidity / los_days / is_emergency /
is_readmission are facts of the encounter row itself.
"""

from datetime import timedelta

from feast import BigQuerySource, Entity, FeatureService, FeatureView, Field
from feast.types import Float32, Int64
from feast.value_type import ValueType

# --- Entity: one patient -----------------------------------------------------
patient = Entity(
    name="patient",
    join_keys=["patient_key"],
    value_type=ValueType.STRING,
    description="A de-identified patient (gold dim_patient surrogate key).",
)

# --- Offline source: PIT query over the L1 gold fact mart --------------------
# No view-create required: Feast reads this query at materialize / historical
# retrieval time via the BigQuery offline store (runtime SA = read-only on the
# dataset is sufficient).
encounter_pit_source = BigQuerySource(
    name="encounter_pit_source",
    query="""
        SELECT
          patient_key,
          TIMESTAMP(admission_date_key)                        AS event_timestamp,
          previous_admission_count                             AS prior_encounter_count,
          COALESCE(days_since_last_admission, 0)               AS days_since_last_admission,
          length_of_stay_days                                  AS los_days,
          is_emergency,
          is_readmission,
          COALESCE(
            AVG(length_of_stay_days) OVER (
              PARTITION BY patient_key
              ORDER BY admission_date_key
              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0.0)                                            AS prior_avg_los
        FROM `bchan-genai-lab.healthcare_analytics.fact_patient_encounters`
    """,
    timestamp_field="event_timestamp",
)

# --- FeatureView: machine-ready features, PIT-correct ------------------------
patient_encounter_features = FeatureView(
    name="patient_encounter_features",
    entities=[patient],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="prior_encounter_count", dtype=Int64),
        Field(name="days_since_last_admission", dtype=Int64),
        Field(name="los_days", dtype=Int64),
        Field(name="is_emergency", dtype=Int64),
        Field(name="is_readmission", dtype=Int64),
        Field(name="prior_avg_los", dtype=Float32),
    ],
    online=True,
    source=encounter_pit_source,
    tags={
        "layer": "L1.25",
        "built_on": "fact_patient_encounters (L1 gold mart)",
        "consumed_by": "L1.5 signals (anomaly/cluster/classify)",
    },
)

# --- FeatureService: the bundle the L1.5 signal layer requests ---------------
high_utilizer_signal_features = FeatureService(
    name="high_utilizer_signal_features",
    features=[patient_encounter_features],
)
