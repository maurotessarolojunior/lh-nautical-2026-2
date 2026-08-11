-- Questão 1.1 - SQL
-- Código calculando: quantidade total de linhas, intervalo de datas (mín/máx),
-- valor mínimo, valor máximo e valor médio da tabela "orders".
--
-- Inclui também a quantidade total de colunas (pedida na Parte 1 do enunciado
-- principal, ainda que não listada no resumo desta subquestão), contada via
-- information_schema.columns e não COUNT(*) — COUNT(*) conta linhas, não colunas.
-- O filtro por table_schema evita contagem inflada caso exista mais de uma
-- tabela "orders" em schemas diferentes do mesmo banco.
--
-- Premissas obrigatórias respeitadas: só a tabela "orders", sem nenhuma limpeza
-- ou tratamento de dado — a query apenas observa e agrega o que já existe.

SELECT
    (SELECT COUNT(*) FROM orders)                                     AS total_linhas,
    (SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'orders'
          AND table_schema = current_schema())                        AS total_colunas,
    (SELECT MIN(created_at) FROM orders)                              AS data_min,
    (SELECT MAX(created_at) FROM orders)                              AS data_max,
    (SELECT MIN(total) FROM orders)                                   AS total_min,
    (SELECT MAX(total) FROM orders)                                   AS total_max,
    (SELECT AVG(total) FROM orders)                                   AS total_media;
