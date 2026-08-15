-- Questão 1.1 - SQL
-- Linhas, colunas, intervalo de datas e valores de "total" da tabela orders.
-- Colunas contadas via information_schema (count(*) conta linha, não coluna),
-- filtrando pelo schema atual para não inflar se existir "orders" em outro schema.

select
    count(*) as total_linhas,
    (
        select count(*)
        from information_schema.columns
        where table_name = 'orders'
            and table_schema = current_schema()
    ) as total_colunas,
    min(created_at) as data_minima,
    max(created_at) as data_maxima,
    min(total) as total_minimo,
    max(total) as total_maximo,
    avg(total) as total_medio
from orders;
