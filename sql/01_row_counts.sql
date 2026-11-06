SELECT 'borrowers' AS table_name, COUNT(*) AS row_count
FROM `credit-risk-dev-00215.raw.borrowers`
UNION ALL
SELECT 'loans', COUNT(*)
FROM `credit-risk-dev-00215.loans`
UNION ALL
SELECT 'loan_monthly_snapshots', COUNT(*)
FROM `credit-risk-dev-00215.raw.loan_monthly_snapshots`
ORDER BY table_name