SELECT partition_id, total_rows
FROM `credit-risk-dev-00215.raw.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'loan_monthly_snapshots'
ORDER BY partition_id