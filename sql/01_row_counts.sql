SELECT 'borrowers' AS table_name, COUNT(*) AS row_count
FROM `credit-risk-dev-00215.raw.borrowers`
UNION ALL
SELECT 'loans', COUNT(*)
FROM `credit-risk-dev-00215.raw.loans`
UNION ALL
SELECT 'loan_monthly_snapshots', COUNT(*)
FROM `credit-risk-dev-00215.raw.loan_monthly_snapshots`
WHERE snapshot_date >= TIMESTAMP('2000-01-01')
ORDER BY table_name