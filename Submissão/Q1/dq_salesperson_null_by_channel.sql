-- Q1 (apoio à Q1.3) — salesperson_id nulo é estrutural (canal ecommerce) ou falta de dado real?

SELECT channel, COUNT(*) AS pedidos, COUNT(*) FILTER (WHERE salesperson_id IS NULL) AS sem_vendedor
FROM orders
GROUP BY channel;
