SELECT
    p.product_category,
    p.product_name,
    o.order_channel,
    COUNT(*) AS orders,
    COUNT(DISTINCT o.user_id) AS buyers,
    ROUND(SUM(o.gross_revenue), 2) AS gross_revenue,
    ROUND(SUM(o.unit_cost), 2) AS direct_cost,
    ROUND(SUM(o.gross_margin), 2) AS gross_margin,
    ROUND(1.0 * SUM(o.gross_margin) / NULLIF(SUM(o.gross_revenue), 0), 4) AS margin_rate,
    ROUND(AVG(o.gross_revenue), 2) AS avg_order_value
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status = 'paid'
GROUP BY p.product_category, p.product_name, o.order_channel
ORDER BY gross_revenue DESC;
