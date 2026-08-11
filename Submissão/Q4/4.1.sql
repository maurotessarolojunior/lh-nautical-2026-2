-- Questao 4 - Analise de clientes
--
-- Duas consultas independentes, cada uma executavel sozinha (sem depender
-- de tabela/view temporaria uma da outra). Ha uma pequena repeticao das
-- CTEs de metricas/diversidade/top_10 entre as duas consultas - aceitavel
-- aqui porque deixa o raciocinio visivel em cada arquivo, sem precisar de
-- DDL adicional so para compartilhar uma CTE.
--
-- Principio central (raciocinio completo em ../../Anotações/comentarios.md):
-- orders tem uma linha por pedido, order_items tem uma linha por item do
-- pedido. Se total/frequencia fossem calculados depois do JOIN com
-- order_items, um pedido com 3 itens contaria 3 vezes - faturamento e
-- frequencia inflados. Por isso as metricas financeiras vem de uma CTE que
-- so olha "orders" (granularidade de pedido), e a diversidade de
-- categorias vem de uma CTE separada que so olha a cadeia de itens
-- (granularidade de item) - as duas so se juntam depois, por customer_id.


-- =====================================================================
-- Consulta 1 — metricas por cliente e Top 10
-- =====================================================================

WITH metricas_pedidos AS (
    -- Faturamento, frequencia e ticket medio: somente "orders", nunca
    -- depois de um JOIN com order_items (isso multiplicaria o pedido por
    -- item e infla os tres numeros).
    SELECT
        customer_id,
        SUM(total)          AS faturamento_total,
        COUNT(id)            AS frequencia,
        SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),

diversidade_clientes AS (
    -- Diversidade de categorias: cadeia de item ate produto, granularidade
    -- diferente da CTE acima de proposito. COUNT(DISTINCT category_id) e
    -- obrigatorio - comprar varios produtos da mesma categoria conta como
    -- uma unica categoria.
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi     ON oi.order_id = o.id
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
WHERE dc.diversidade_categorias >= 13          -- filtro de elite, antes do ranking
ORDER BY mp.ticket_medio DESC, mp.customer_id ASC  -- ticket sem arredondar; desempate exigido pelo enunciado
LIMIT 10;


-- =====================================================================
-- Consulta 2 — categoria com maior quantidade de itens comprados
--              pelo Top 10 (mesmo Top 10 da consulta 1)
-- =====================================================================

WITH metricas_pedidos AS (
    SELECT
        customer_id,
        SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),

diversidade_clientes AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi     ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),

top_10 AS (
    -- Os mesmos 10 clientes da consulta 1, isolados aqui ANTES de voltar
    -- para orders/order_items - garante que nenhum pedido de cliente fora
    -- do Top 10 entra na soma de quantidade abaixo.
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
    SUM(oi.quantity) AS quantidade_total   -- SUM(quantity), nunca COUNT(*): uma linha pode ter quantidade > 1
FROM top_10 t
JOIN orders o             ON o.customer_id = t.customer_id
JOIN order_items oi        ON oi.order_id = o.id
JOIN product_variants pv   ON pv.id = oi.product_variant_id
JOIN products p            ON p.id = pv.product_id
JOIN categories c          ON c.id = p.category_id
GROUP BY c.id, c.name
ORDER BY quantidade_total DESC, category_id ASC;
-- Resultado completo (14 categorias) deixado sem LIMIT de proposito: a
-- resposta e a primeira linha (category_id = 8, "Helices", 492), mas ver
-- a segunda colocada (393) no mesmo resultado comprova que nao ha empate
-- no primeiro lugar, sem precisar rodar a query de novo.
