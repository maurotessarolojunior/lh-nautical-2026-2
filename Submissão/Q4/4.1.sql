-- Questao 4 - Analise de clientes
--
-- orders tem uma linha por pedido; order_items, uma por item. Por isso
-- faturamento/frequencia vem de uma consulta que so olha "orders" (nunca
-- depois de JOIN com order_items, que multiplicaria o pedido por item), e a
-- diversidade de categorias vem de uma consulta separada, na cadeia de
-- itens - as duas se juntam depois, por customer_id.
--
-- Duas consultas independentes (pequena repeticao das CTEs entre elas,
-- aceitavel pra manter cada uma executavel sozinha).


-- Consulta 1 - metricas por cliente e Top 10

WITH metricas_pedidos AS (
    SELECT
        customer_id,
        SUM(total) AS faturamento_total,
        COUNT(id) AS frequencia,
        SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),

diversidade_clientes AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias  -- DISTINCT: mesma categoria em varios produtos conta uma vez
    FROM orders o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
)

SELECT
    mp.customer_id,
    ROUND(mp.faturamento_total, 2) AS faturamento_total,
    mp.frequencia,
    ROUND(mp.ticket_medio, 2)      AS ticket_medio,
    dc.diversidade_categorias
FROM metricas_pedidos mp
JOIN diversidade_clientes dc ON dc.customer_id = mp.customer_id
WHERE dc.diversidade_categorias >= 13
ORDER BY mp.ticket_medio DESC, mp.customer_id ASC  -- ticket sem arredondar; desempate exigido pelo enunciado
LIMIT 10;


-- Consulta 2 - categoria com maior quantidade de itens comprados pelo Top 10

WITH metricas_pedidos AS (
    SELECT customer_id, SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),

diversidade_clientes AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),

top_10 AS (
    SELECT mp.customer_id
    FROM metricas_pedidos mp
    JOIN diversidade_clientes dc ON dc.customer_id = mp.customer_id
    WHERE dc.diversidade_categorias >= 13
    ORDER BY mp.ticket_medio DESC, mp.customer_id ASC
    LIMIT 10
)

SELECT
    c.id   AS category_id,
    c.name AS categoria,
    SUM(oi.quantity) AS quantidade_total  -- SUM(quantity), nao COUNT(*): item pode ter quantidade > 1
FROM top_10 t
JOIN orders o             ON o.customer_id = t.customer_id
JOIN order_items oi        ON oi.order_id = o.id
JOIN product_variants pv   ON pv.id = oi.product_variant_id
JOIN products p            ON p.id = pv.product_id
JOIN categories c          ON c.id = p.category_id
GROUP BY c.id, c.name
ORDER BY quantidade_total DESC, category_id ASC;
-- sem LIMIT: mostra as 14 categorias, confirmando que a 2a colocada (393) nao empata com a 1a (492)
