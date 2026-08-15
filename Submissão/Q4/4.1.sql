-- Questao 4 - Analise de clientes
--
-- orders tem uma linha por pedido; order_items, uma por item. Por isso
-- faturamento/frequencia vem de uma consulta que so olha "orders" (nunca
-- depois de join com order_items, que multiplicaria o pedido por item), e a
-- diversidade de categorias vem de uma consulta separada, na cadeia de
-- itens - as duas se juntam depois, por customer_id.
--
-- Duas consultas independentes (pequena repeticao das CTEs entre elas,
-- aceitavel pra manter cada uma executavel sozinha).


-- Consulta 1 - metricas por cliente e Top 10

with metricas_pedidos as (
    select
        customer_id,
        sum(total) as faturamento_total,
        count(id) as frequencia,
        sum(total) / count(id) as ticket_medio
    from orders
    group by customer_id
),

diversidade_clientes as (
    select
        orders.customer_id,
        -- distinct: mesma categoria em varios produtos conta uma vez
        count(distinct products.category_id) as diversidade_categorias
    from orders
    join order_items on
        order_items.order_id = orders.id
    join product_variants on
        product_variants.id = order_items.product_variant_id
    join products on
        products.id = product_variants.product_id
    group by orders.customer_id
)

select
    metricas_pedidos.customer_id,
    round(metricas_pedidos.faturamento_total, 2) as faturamento_total,
    metricas_pedidos.frequencia,
    round(metricas_pedidos.ticket_medio, 2) as ticket_medio,
    diversidade_clientes.diversidade_categorias
from metricas_pedidos
join diversidade_clientes on
    diversidade_clientes.customer_id = metricas_pedidos.customer_id
where diversidade_clientes.diversidade_categorias >= 13
-- ticket sem arredondar; desempate exigido pelo enunciado
order by metricas_pedidos.ticket_medio desc, metricas_pedidos.customer_id asc
limit 10;


-- Consulta 2 - categoria com maior quantidade de itens comprados pelo Top 10

with metricas_pedidos as (
    select
        customer_id,
        sum(total) / count(id) as ticket_medio
    from orders
    group by customer_id
),

diversidade_clientes as (
    select
        orders.customer_id,
        count(distinct products.category_id) as diversidade_categorias
    from orders
    join order_items on
        order_items.order_id = orders.id
    join product_variants on
        product_variants.id = order_items.product_variant_id
    join products on
        products.id = product_variants.product_id
    group by orders.customer_id
),

top_10 as (
    select metricas_pedidos.customer_id
    from metricas_pedidos
    join diversidade_clientes on
        diversidade_clientes.customer_id = metricas_pedidos.customer_id
    where diversidade_clientes.diversidade_categorias >= 13
    order by metricas_pedidos.ticket_medio desc, metricas_pedidos.customer_id asc
    limit 10
)

select
    categories.id as category_id,
    categories.name as categoria,
    -- sum(quantity), nao count(*): item pode ter quantidade > 1
    sum(order_items.quantity) as quantidade_total
from top_10
join orders on
    orders.customer_id = top_10.customer_id
join order_items on
    order_items.order_id = orders.id
join product_variants on
    product_variants.id = order_items.product_variant_id
join products on
    products.id = product_variants.product_id
join categories on
    categories.id = products.category_id
group by categories.id, categories.name
order by quantidade_total desc, category_id asc;
-- sem limit: mostra as 14 categorias, confirmando que a 2a colocada (393) nao empata com a 1a (492)
