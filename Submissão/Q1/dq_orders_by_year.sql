-- Q1 (apoio à Q1.3) — distribuição por ano de created_at: confirma se a base cobre 2020-2026
-- como o enunciado descreve, e quanto disso é "futuro" em relação à data de hoje.

SELECT date_part('year', created_at) AS ano, COUNT(*) AS n
FROM orders
GROUP BY ano
ORDER BY ano;
