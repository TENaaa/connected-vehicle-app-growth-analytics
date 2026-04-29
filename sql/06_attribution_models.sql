WITH qualified_touchpoints AS (
    SELECT
        o.order_id,
        o.user_id,
        o.gross_revenue,
        tp.channel,
        tp.touchpoint_time,
        ROW_NUMBER() OVER (PARTITION BY o.order_id ORDER BY tp.touchpoint_time) AS rn_first,
        ROW_NUMBER() OVER (PARTITION BY o.order_id ORDER BY tp.touchpoint_time DESC) AS rn_last,
        COUNT(*) OVER (PARTITION BY o.order_id) AS touch_count
    FROM orders o
    JOIN touchpoints tp
      ON tp.user_id = o.user_id
     AND julianday(tp.touchpoint_time) <= julianday(o.order_timestamp)
    WHERE o.order_status = 'paid'
      AND tp.touchpoint_status = 'delivered'
),
credits AS (
    SELECT
        'first_touch' AS attribution_model,
        channel,
        order_id,
        CASE WHEN rn_first = 1 THEN gross_revenue ELSE 0 END AS revenue_credit,
        CASE WHEN rn_first = 1 THEN 1.0 ELSE 0 END AS order_credit
    FROM qualified_touchpoints
    UNION ALL
    SELECT
        'last_touch',
        channel,
        order_id,
        CASE WHEN rn_last = 1 THEN gross_revenue ELSE 0 END,
        CASE WHEN rn_last = 1 THEN 1.0 ELSE 0 END
    FROM qualified_touchpoints
    UNION ALL
    SELECT
        'linear',
        channel,
        order_id,
        gross_revenue / touch_count,
        1.0 / touch_count
    FROM qualified_touchpoints
    UNION ALL
    SELECT
        'position_based',
        channel,
        order_id,
        CASE
            WHEN touch_count = 1 THEN gross_revenue
            WHEN touch_count = 2 THEN gross_revenue * 0.5
            WHEN rn_first = 1 OR rn_last = 1 THEN gross_revenue * 0.4
            ELSE gross_revenue * 0.2 / (touch_count - 2)
        END,
        CASE
            WHEN touch_count = 1 THEN 1.0
            WHEN touch_count = 2 THEN 0.5
            WHEN rn_first = 1 OR rn_last = 1 THEN 0.4
            ELSE 0.2 / (touch_count - 2)
        END
    FROM qualified_touchpoints
)
SELECT
    attribution_model,
    channel,
    ROUND(SUM(revenue_credit), 2) AS attributed_revenue,
    ROUND(SUM(order_credit), 2) AS attributed_orders,
    ROUND(AVG(revenue_credit), 2) AS avg_revenue_credit
FROM credits
GROUP BY attribution_model, channel
HAVING attributed_revenue > 0
ORDER BY attribution_model, attributed_revenue DESC;
