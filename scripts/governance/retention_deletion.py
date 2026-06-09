#!/usr/bin/env python3
"""
Bullet 4 proof: automated retention and deletion policies, on a BOUNDED fixture.

Builds a disposable fixture table seeded with rows spanning old->recent dates, then:
  1. RETENTION: sets partition expiration (time-based auto-expiry) — the declarative
     retention policy BigQuery enforces without a cron.
  2. DELETION: runs an explicit right-to-be-forgotten style deletion (rows older than the
     retention window, plus a targeted subject delete), verifying before/after counts.
Everything runs on a throwaway `_fixture_retention` table and the table is dropped at the
end (cost-clean), so no production data and no lingering cost.
"""
import json, datetime
from pathlib import Path
from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[2]
PROJECT, DS = "PROJECT", "healthcare_analytics"
FIX = "_fixture_retention"
RETENTION_DAYS = 365


def main():
    c = bigquery.Client(project=PROJECT)
    fid = f"{PROJECT}.{DS}.{FIX}"
    c.delete_table(fid, not_found_ok=True)

    # seed fixture: 5 old (>365d), 5 recent, distinct subject to delete
    seed_sql = f"""
    CREATE TABLE `{fid}`
    PARTITION BY DATE(event_ts) AS
    SELECT
      GENERATE_UUID() AS row_id,
      CASE WHEN n <= 5 THEN 'subject_old' ELSE 'subject_recent' END AS subject,
      CASE WHEN n <= 5
           THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL (400 + n) DAY)
           ELSE TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL n DAY) END AS event_ts
    FROM UNNEST(GENERATE_ARRAY(1,10)) AS n
    """
    c.query(seed_sql).result()
    total0 = list(c.query(f"SELECT COUNT(*) n FROM `{fid}`").result())[0]["n"]

    # baseline: how many rows are past the retention window BEFORE any policy
    older = list(c.query(
        f"SELECT COUNT(*) n FROM `{fid}` "
        f"WHERE event_ts < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {RETENTION_DAYS} DAY)"
    ).result())[0]["n"]

    # 1. RETENTION: declarative partition expiration. BigQuery auto-expires partitions
    #    older than the window — no cron. Setting it removes the expired partitions.
    t = c.get_table(fid)
    t.time_partitioning = bigquery.TimePartitioning(
        field="event_ts", expiration_ms=RETENTION_DAYS * 24 * 3600 * 1000)
    c.update_table(t, ["time_partitioning"])
    part_exp_days = c.get_table(fid).time_partitioning.expiration_ms / (24 * 3600 * 1000)

    # verify the retention policy actually disposed the past-window rows
    after_retention = list(c.query(f"SELECT COUNT(*) n FROM `{fid}`").result())[0]["n"]

    # 2b. DELETION: targeted subject erasure (right-to-be-forgotten pattern)
    c.query(f"DELETE FROM `{fid}` WHERE subject = 'subject_recent' AND "
            f"event_ts < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)").result()
    final = list(c.query(f"SELECT COUNT(*) n FROM `{fid}`").result())[0]["n"]

    # clean up the fixture (no lingering cost / data)
    c.delete_table(fid, not_found_ok=True)

    retention_ok = older == 5 and after_retention == total0 - older  # past-window rows disposed
    deletion_ok = final < after_retention
    policy_set = abs(part_exp_days - RETENTION_DAYS) < 1
    green = retention_ok and deletion_ok and policy_set

    receipt = {
        "proof": "bullet4_retention_deletion",
        "claim_phrase": "automated retention and deletion policies",
        "fixture": {"table": fid, "seeded_rows": total0, "bounded": True, "dropped_after": True},
        "retention_policy": {"partition_expiration_days": part_exp_days,
                             "declarative_auto_expiry": True, "target_days": RETENTION_DAYS},
        "deletion_run": {"rows_past_retention": older, "after_retention_delete": after_retention,
                         "after_targeted_erasure": final},
        "checks": {"retention_deletes_expected_rows": retention_ok,
                   "targeted_deletion_works": deletion_ok,
                   "partition_expiration_set": policy_set},
        "verdict": "GREEN — partition expiration set + retention/targeted deletion verified on fixture"
                   if green else "YELLOW — a retention/deletion check did not pass",
    }
    out = REPO / "data" / "quality" / "bullet4_retention_proof.json"
    json.dump(receipt, open(out, "w"), indent=2, default=str)
    print("WROTE", out)
    print(f"  seeded={total0} past_retention={older} after_retention={after_retention} final={final}")
    print(f"  partition_expiration_days={part_exp_days}")
    print("VERDICT:", receipt["verdict"])
    raise SystemExit(0 if green else 1)


if __name__ == "__main__":
    main()
