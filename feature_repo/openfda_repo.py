"""
Feast feature definitions over REAL openFDA adverse-event data (Bullet 3).

Entity = adverse-event report. The headline feature `prior_reports_for_drug` is
point-in-time-correct (counts only earlier reports for the same drug), so a model
trained through Feast cannot leak the future. Source parquet is generated from the
governed BigQuery fact (scripts upstream), so Feast is pointed at real openFDA, not a
synthetic dump. `feast apply` registers these for discovery; historical/online
retrieval proves the feature path actually runs.
"""
from datetime import timedelta
from pathlib import Path

from feast import Entity, FeatureView, Field, FileSource, FeatureService
from feast.types import Int64, String

_PARQUET = str(Path(__file__).resolve().parents[1] / "data" / "feast" / "openfda_drug_features.parquet")

report = Entity(name="report", join_keys=["safetyreportid"], description="One openFDA adverse-event report")

openfda_source = FileSource(
    name="openfda_drug_features_src",
    path=_PARQUET,
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

openfda_drug_fv = FeatureView(
    name="openfda_drug_features",
    entities=[report],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="primary_drug", dtype=String),
        Field(name="prior_reports_for_drug", dtype=Int64),
        Field(name="is_serious", dtype=Int64),
        Field(name="n_reactions", dtype=Int64),
    ],
    online=True,
    source=openfda_source,
    tags={"domain": "openfda", "pit_correct": "prior_reports_for_drug"},
)

openfda_serving = FeatureService(name="openfda_serving_v1", features=[openfda_drug_fv])
