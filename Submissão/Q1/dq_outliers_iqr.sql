-- Q1 (apoio à Q1.3) — outliers em `total` via IQR (1.5x), sem excluir nada, só quantificar.

WITH q AS (
    SELECT quantile_cont(total, 0.25) AS q1, quantile_cont(total, 0.75) AS q3
    FROM orders
)
SELECT
    q1,
    q3,
    (SELECT COUNT(*) FROM orders, q WHERE total > q3 + 1.5 * (q3 - q1)) AS outliers_acima,
    (SELECT COUNT(*) FROM orders, q WHERE total < q1 - 1.5 * (q3 - q1)) AS outliers_abaixo
FROM q;
