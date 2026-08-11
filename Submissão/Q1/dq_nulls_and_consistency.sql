-- Q1 (apoio à Q1.3) — nulos por coluna relevante, consistência aritmética
-- (subtotal - discount_amount = total) e duplicidade de chaves.

SELECT
    COUNT(*) FILTER (WHERE total IS NULL)              AS null_total,
    COUNT(*) FILTER (WHERE customer_id IS NULL)         AS null_customer_id,
    COUNT(*) FILTER (WHERE salesperson_id IS NULL)      AS null_salesperson_id,
    COUNT(*) FILTER (WHERE location_id IS NULL)         AS null_location_id,
    COUNT(*) FILTER (WHERE channel IS NULL)             AS null_channel,
    COUNT(*) FILTER (WHERE status IS NULL)              AS null_status,
    COUNT(*) FILTER (WHERE total <= 0)                  AS total_nao_positivo,
    COUNT(*) FILTER (WHERE ABS(total - (subtotal - discount_amount)) > 0.01)
                                                         AS total_inconsistente_com_subtotal,
    (SELECT COUNT(*) FROM (SELECT id FROM orders GROUP BY id HAVING COUNT(*) > 1))
                                                         AS ids_duplicados,
    (SELECT COUNT(*) FROM (SELECT order_number FROM orders GROUP BY order_number HAVING COUNT(*) > 1))
                                                         AS order_number_duplicados
FROM orders;
