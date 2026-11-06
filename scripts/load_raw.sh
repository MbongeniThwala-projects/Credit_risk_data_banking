#Load the cloud storage extracts into the raw BQ tables

set -euo pipefail

PROJECT="credit-risk-dev-00215"
LOCATION="africa-south1"
BUCKET="gs://${PROJECT}-landing"

#small reference tables: one file each
for table in borrowers loans; do
    bq load \
        --project_id="${PROJECT}" \
        --location="${LOCATION}" \
        --source_format=PARQUET \
        --replace \
        "raw.${table}" \
        "${BUCKET}/${table}/${table}.parquet"
done

# Monthly snapshots: partitioned by month and clustered for cheaper queries
bq load \
    --project_id="${PROJECT}" \
    --location="${LOCATION}" \
    --source_format=PARQUET \
    --replace \
    --time_partitioning_type=MONTH \
    --time_partitioning_field=snapshot_date \
    --clustering_fields=status,delinquency_bucket,loan_id \
    raw.loan_monthly_snapshots \
    "${BUCKET}/loan_snapshots/*"