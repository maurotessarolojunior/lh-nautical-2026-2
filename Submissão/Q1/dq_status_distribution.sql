-- Q1 (apoio à Q1.3) — distribuição de status: quantos pedidos não deveriam entrar em métricas
-- de faturamento realizado (cancelled, draft) nas questões de análise mais à frente.

SELECT status, COUNT(*) AS n
FROM orders
GROUP BY status
ORDER BY n DESC;
