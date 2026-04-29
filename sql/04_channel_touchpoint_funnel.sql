WITH channel_users AS (
    SELECT
        tp.channel,
        COUNT(*) AS touchpoints,
        COUNT(DISTINCT tp.user_id) AS touched_users,
        COUNT(DISTINCT CASE WHEN tp.touchpoint_status = 'delivered' THEN tp.user_id END) AS delivered_users,
        COUNT(DISTINCT CASE WHEN e_click.event_name = 'content_click' THEN tp.user_id END) AS clicked_users,
        COUNT(DISTINCT CASE WHEN e_intent.event_name = 'purchase_intent' THEN tp.user_id END) AS intent_users,
        COUNT(DISTINCT CASE WHEN o.order_status = 'paid' THEN tp.user_id END) AS paid_buyers,
        SUM(tp.touchpoint_cost) AS touchpoint_cost,
        SUM(CASE WHEN o.order_status = 'paid' THEN o.gross_revenue ELSE 0 END) AS gross_revenue
    FROM touchpoints tp
    LEFT JOIN events e_click
        ON e_click.touchpoint_id = tp.touchpoint_id
       AND e_click.event_name = 'content_click'
    LEFT JOIN events e_intent
        ON e_intent.touchpoint_id = tp.touchpoint_id
       AND e_intent.event_name = 'purchase_intent'
    LEFT JOIN orders o
        ON o.attributed_touchpoint_id = tp.touchpoint_id
    GROUP BY tp.channel
)
SELECT
    channel,
    touchpoints,
    touched_users,
    delivered_users,
    clicked_users,
    intent_users,
    paid_buyers,
    ROUND(1.0 * delivered_users / NULLIF(touched_users, 0), 4) AS delivery_rate,
    ROUND(1.0 * clicked_users / NULLIF(delivered_users, 0), 4) AS click_rate,
    ROUND(1.0 * intent_users / NULLIF(delivered_users, 0), 4) AS intent_rate,
    ROUND(1.0 * paid_buyers / NULLIF(delivered_users, 0), 4) AS paid_conversion_rate,
    ROUND(touchpoint_cost, 2) AS touchpoint_cost,
    ROUND(gross_revenue, 2) AS gross_revenue,
    ROUND((gross_revenue - touchpoint_cost) / NULLIF(touchpoint_cost, 0), 2) AS roi
FROM channel_users
ORDER BY gross_revenue DESC;
