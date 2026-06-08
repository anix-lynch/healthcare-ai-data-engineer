#!/usr/bin/env python3
"""
Bullet 3 proof: representative Power-BI-style queries over the openFDA semantic marts
run repeatedly, proving sub-5-second latency. Writes a machine-readable receipt with
per-query p50/p95 and a global verdict. Uses the BigQuery client (SA auth), measures
real wall-clock round-trip (the latency Power BI's DirectQuery actually feels).
"""
import json, time, statistics, os
from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
ITERS = int(os.environ.get("BENCH_ITERS", "8"))
SLA_S = 5.0

QUERIES = {
    "drug_leaderboard_by_serious_rate":
        f"SELECT primary_drug, total_reports, serious_rate, distinct_reactions "
        f"FROM `{PROJECT}.{DATASET}.mart_drug_safety_kpis` "
        f"WHERE total_reports >= 3 ORDER BY serious_rate DESC, total_reports DESC LIMIT 20",
    "top_reactions_panel":
        f"SELECT reaction_name, reports_with_reaction, distinct_drugs, serious_share "
        f"FROM `{PROJECT}.{DATASET}.mart_reaction_signals` "
        f"ORDER BY reports_with_reaction DESC LIMIT 20",
    "drug_reaction_drilldown":
        f"SELECT f.primary_drug, d.reaction_name, COUNT(*) n "
        f"FROM `{PROJECT}.{DATASET}.fact_adverse_events` f "
        f"JOIN `{PROJECT}.{DATASET}.bridge_report_reaction` b USING (safetyreportid) "
        f"JOIN `{PROJECT}.{DATASET}.dim_reaction` d USING (reaction_id) "
        f"WHERE f.primary_drug IS NOT NULL GROUP BY 1,2 ORDER BY n DESC LIMIT 50",
    "serious_kpi_card":
        f"SELECT COUNT(*) drugs, ROUND(AVG(serious_rate),3) avg_serious_rate, "
        f"SUM(serious_reports) serious_total "
        f"FROM `{PROJECT}.{DATASET}.mart_drug_safety_kpis`",
}


def run():
    client = bigquery.Client(project=PROJECT)
    results = {}
    overall_ok = True
    for name, sql in QUERIES.items():
        lat, bytes_billed = [], None
        for _ in range(ITERS):
            t0 = time.perf_counter()
            job = client.query(sql)
            rows = list(job.result())   # force full round-trip + fetch
            lat.append(time.perf_counter() - t0)
            bytes_billed = job.total_bytes_billed
        lat.sort()
        p50 = round(statistics.median(lat), 3)
        p95 = round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 3)
        mx = round(max(lat), 3)
        ok = mx < SLA_S
        overall_ok = overall_ok and ok
        results[name] = {"iters": ITERS, "rows": len(rows), "p50_s": p50,
                         "p95_s": p95, "max_s": mx, "mbytes_billed": round((bytes_billed or 0)/1e6, 2),
                         "under_5s": ok}
    receipt = {
        "proof": "bullet3_sub5s_query_benchmark",
        "claim_phrase": "sub-5-second Power BI queries",
        "sla_seconds": SLA_S,
        "engine": "BigQuery (service-account, interactive priority)",
        "queries": results,
        "verdict": "GREEN — every representative query max latency < 5s"
                   if overall_ok else "RED — at least one query exceeded the 5s SLA",
    }
    out = "data/quality/bullet3_query_latency_proof.json"
    json.dump(receipt, open(out, "w"), indent=2)
    print("WROTE", out)
    for n, r in results.items():
        flag = "OK " if r["under_5s"] else "SLA!"
        print(f"  [{flag}] {n:38s} p50={r['p50_s']}s p95={r['p95_s']}s max={r['max_s']}s rows={r['rows']}")
    print("VERDICT:", receipt["verdict"])
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
