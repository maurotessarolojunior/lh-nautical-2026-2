-- Questão 1.1 - SQL
-- Linhas, colunas, intervalo de datas e valores de "total" da tabela orders.
-- Colunas contadas via information_schema (COUNT(*) conta linha, não coluna),
-- filtrando pelo schema atual para não inflar se existir "orders" em outro schema.

SELECT
    COUNT(*) AS total_linhas,
    (SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'orders' AND table_schema = current_schema()) AS total_colunas,
    MIN(created_at) AS data_minima,
    MAX(created_at) AS data_maxima,
    MIN(total) AS total_minimo,
    MAX(total) AS total_maximo,
    AVG(total) AS total_medio
FROM orders;
