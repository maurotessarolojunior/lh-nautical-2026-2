-- Questao 5 - Dimensao de calendario
--
-- Calendario garante que todo dia do periodo entra no calculo, mesmo sem
-- venda registrada (ausencia de linha != valor zero) - e o erro que o
-- estagiario cometeu ao agrupar direto em "orders".
--
-- Periodo usa MIN/MAX(placed_at::date) observados no arquivo, nao
-- CURRENT_DATE: os limites vem do proprio arquivo (como o enunciado pede)
-- e a consulta fica reproduzivel em qualquer dia que for executada.

WITH limites AS (
    SELECT
        MIN(placed_at::date) AS data_inicial,
        MAX(placed_at::date) AS data_final
    FROM orders
),

datas AS (
    -- Uma linha por dia do periodo, sem lacunas.
    SELECT generate_series(data_inicial, data_final, INTERVAL '1 day')::date AS data
    FROM limites
),

calendario AS (
    -- ISODOW (Segunda=1...Domingo=7); CASE em vez de TO_CHAR pra nao
    -- depender do locale do servidor.
    SELECT
        data,
        EXTRACT(ISODOW FROM data)::int AS numero_dia_semana,
        CASE EXTRACT(ISODOW FROM data)::int
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
            WHEN 7 THEN 'Domingo'
        END AS dia_semana
    FROM datas
),

vendas_diarias AS (
    -- Soma por dia antes do join (uma linha por data). Filtro de canal aqui
    -- dentro, nunca num WHERE depois do LEFT JOIN - eliminaria os dias sem
    -- venda que o calendario deveria preservar.
    SELECT
        placed_at::date AS data,
        SUM(total) AS venda_diaria
    FROM orders
    WHERE channel = 'pos'
    GROUP BY placed_at::date
),

calendario_com_vendas AS (
    -- LEFT JOIN a partir do calendario preserva toda data; COALESCE
    -- transforma o NULL da ausencia em 0 antes da media (AVG ignora NULL,
    -- nao ignora zero).
    SELECT
        c.data,
        c.numero_dia_semana,
        c.dia_semana,
        COALESCE(v.venda_diaria, 0) AS venda_diaria
    FROM calendario c
    LEFT JOIN vendas_diarias v ON v.data = c.data
)

SELECT
    numero_dia_semana,
    dia_semana,
    COUNT(*) AS dias_no_calendario,
    COUNT(*) FILTER (WHERE venda_diaria = 0) AS dias_sem_venda,
    ROUND(AVG(venda_diaria), 2) AS media_vendas_diarias
FROM calendario_com_vendas
GROUP BY numero_dia_semana, dia_semana
ORDER BY media_vendas_diarias ASC, numero_dia_semana ASC;
-- Sem LIMIT: mostra os 7 dias, confirma que nao ha empate perto do topo.
