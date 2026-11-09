'''
Measure how much data different queries read from the. snapshot table
'''

from google.cloud import bigquery

PROJECT = "credit-risk-dev-00215"
LOCATION = "africa-south1"
TABLE = f"`{PROJECT}.raw.loan_monthly_snapshots`"
ONE_MONTH = "snapshot_date >= TIMESTAMP('2026-09-01') AND snapshot_date < TIMESTAMP('2026-10-01')"
GUARD_BYTES = 5 * 1024**3   #restrict query billing to 5GiB

QUERIES = {
    "A  all months, 3 columnns": f"""
        SELECT delinquency_bucket, COUNT(*) AS loan_months, SUM(closing_balance) AS exposure
        FROM {TABLE}
        GROUP BY delinquency_bucket""",
    "B  one month, 3 columns": f"""
        SELECT delinquency_bucket, COUNT(*) AS loan_months, SUM(closing_balance) AS exposure
        FROM {TABLE}
        WHERE {ONE_MONTH}
        GROUP BY delinquency_bucket""",
    "C  one month + status filter": f"""
        SELECT delinquency_bucket, COUNT(*) AS loan_months, SUM(closing_balance) AS exposure
        FROM {TABLE}
        WHERE {ONE_MONTH} AND status = 'default'
        GROUP BY delinquency_bucket""",
    "D  one month, SELECT *": f"""
        SELECT *
        FROM {TABLE}
        WHERE {ONE_MONTH}""",
}

def run_all(client):
    results = []
    for name, sql in QUERIES.items():
        config = bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=GUARD_BYTES)
        job = client.query(sql, job_config=config)
        job.result()
        seconds = (job.ended - job.started).total_seconds()
        results.append((name, job.total_bytes_processed, job.total_bytes_billed, seconds))
    return results

def print_table(results):
    mib = 1024**2
    baseline = results[0][1]
    print(f"{'query':32}{'processed MiB':>15}{'billed MiB':>12}{'% of A':>9}{'seconds':>9}")
    for name, processed, billed, seconds in results:
        print(
            f"{name:32}{processed / mib:>15.1f}{billed / mib:>12.1f}"
            f"{processed / baseline:>9.1%}{seconds:>9.1f}"
        )

def main():
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    print_table(run_all(client))

if __name__ == "__main__":
    main()