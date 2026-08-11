-- Questao 5 - Dimensao de calendario
--
-- Pergunta do Sr. Almir: qual dia da semana tem a pior media de vendas nas
-- lojas fisicas? O erro do estagiario foi agrupar direto em "orders": dias
-- sem pedido nao existem nessa tabela, entao somem do calculo e a media
-- fica inflada (denominador menor do que deveria). A dimensao de calendario
-- existe pra garantir que todo dia do periodo entre no calculo, mesmo os
-- dias sem nenhuma venda registrada.
--
-- Interpretacao do periodo ("entre a menor e a data atual da venda no
-- arquivo"): usei MIN/MAX(placed_at::date) observados nos proprios dados,
-- nao CURRENT_DATE. Os dois limites vem do arquivo (como o enunciado pede
-- literalmente), e a consulta fica reproduzivel em qualquer dia que for
-- executada - com CURRENT_DATE o resultado mudaria com o tempo e ignoraria
-- pedidos com data futura ja presentes no arquivo (ate 2026-12-31).

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
    -- ISODOW (Segunda=1 ... Domingo=7), nao DOW (Domingo=0): ordena o
    -- calendario no padrao da semana brasileira. Nome do dia escrito
    -- explicito em CASE, nao TO_CHAR(data, 'Day') - esse depende do locale
    -- do servidor e pode devolver o nome em ingles.
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
    -- Soma por dia ANTES do join com o calendario, garantindo que cada
    -- data chegue no calendario com uma unica linha. O JOIN em si nao
    -- corromperia a soma (daria pra juntar primeiro e agrupar por data
    -- depois) - o problema seria calcular a media direto na granularidade
    -- de pedido/linha do JOIN, sem antes reduzir pra uma linha por data,
    -- que e a granularidade que a media por dia da semana exige. Filtro
    -- de canal aqui dentro, nunca num WHERE depois do LEFT JOIN (isso
    -- eliminaria justamente os dias sem venda que o calendario deveria
    -- preservar).
    SELECT
        placed_at::date AS data,
        SUM(total) AS venda_diaria
    FROM orders
    WHERE channel = 'pos'
    GROUP BY placed_at::date
),

calendario_com_vendas AS (
    -- LEFT JOIN partindo do calendario: toda data sobrevive, mesmo sem
    -- pedido correspondente. COALESCE transforma o NULL da ausencia em 0 -
    -- sem isso, AVG() ignoraria essas linhas e o problema do estagiario
    -- se repetiria.
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
    ROUND(AVG(venda_diaria), 2) AS media_vendas_diarias   -- media sobre TODOS os dias do calendario, nao só os com venda
FROM calendario_com_vendas
GROUP BY numero_dia_semana, dia_semana
ORDER BY media_vendas_diarias ASC, numero_dia_semana ASC;
-- Os 7 dias da semana ficam no resultado (sem LIMIT 1) para o ranking
-- completo ficar visivel: a primeira linha responde a pergunta do Sr.
-- Almir (pior média), mas ver as outras 6 mostra que não há empate perto
-- do topo e que Domingo - o dia que o estagiário achou ótimo - na verdade
-- fica em segundo lugar entre os piores.
