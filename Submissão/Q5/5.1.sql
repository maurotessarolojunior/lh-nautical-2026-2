-- Questao 5 - Dimensao de calendario
--
-- Calendario garante que todo dia do periodo entra no calculo, mesmo sem
-- venda registrada (ausencia de linha != valor zero) - e o erro que o
-- estagiario cometeu ao agrupar direto em "orders".
--
-- Periodo usa min/max(placed_at::date) observados no arquivo, nao
-- current_date: os limites vem do proprio arquivo (como o enunciado pede)
-- e a consulta fica reproduzivel em qualquer dia que for executada.

with limites as (
    select
        min(placed_at::date) as data_inicial,
        max(placed_at::date) as data_final
    from orders
),

datas as (
    -- Uma linha por dia do periodo, sem lacunas.
    select generate_series(data_inicial, data_final, interval '1 day')::date as data
    from limites
),

calendario as (
    -- isodow (Segunda=1...Domingo=7); case em vez de to_char pra nao
    -- depender do locale do servidor.
    select
        data,
        extract(isodow from data)::int as numero_dia_semana,
        case extract(isodow from data)::int
            when 1 then 'Segunda-feira'
            when 2 then 'Terça-feira'
            when 3 then 'Quarta-feira'
            when 4 then 'Quinta-feira'
            when 5 then 'Sexta-feira'
            when 6 then 'Sábado'
            when 7 then 'Domingo'
        end as dia_semana
    from datas
),

vendas_diarias as (
    -- Soma por dia antes do join (uma linha por data). Filtro de canal aqui
    -- dentro, nunca num where depois do left join - eliminaria os dias sem
    -- venda que o calendario deveria preservar.
    select
        placed_at::date as data,
        sum(total) as venda_diaria
    from orders
    where channel = 'pos'
    group by placed_at::date
),

calendario_com_vendas as (
    -- left join a partir do calendario preserva toda data; coalesce
    -- transforma o null da ausencia em 0 antes da media (avg ignora null,
    -- nao ignora zero).
    select
        calendario.data,
        calendario.numero_dia_semana,
        calendario.dia_semana,
        coalesce(vendas_diarias.venda_diaria, 0) as venda_diaria
    from calendario
    left join vendas_diarias on
        vendas_diarias.data = calendario.data
)

select
    numero_dia_semana,
    dia_semana,
    count(*) as dias_no_calendario,
    count(*) filter (where venda_diaria = 0) as dias_sem_venda,
    round(avg(venda_diaria), 2) as media_vendas_diarias
from calendario_com_vendas
group by numero_dia_semana, dia_semana
order by media_vendas_diarias asc, numero_dia_semana asc;
-- Sem limit: mostra os 7 dias, confirma que nao ha empate perto do topo.
