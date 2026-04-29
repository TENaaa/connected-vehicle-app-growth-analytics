WITH assigned AS (
    SELECT
        ea.user_id,
        ea.variant,
        ea.assigned_at
    FROM experiment_assignments ea
),
touch_flags AS (
    SELECT
        a.user_id,
        MAX(CASE WHEN tp.touchpoint_status = 'delivered' THEN 1 ELSE 0 END) AS reached
    FROM assigned a
    LEFT JOIN touchpoints tp ON tp.user_id = a.user_id
    GROUP BY a.user_id
),
event_flags AS (
    SELECT
        a.user_id,
        MAX(CASE WHEN e.event_name = 'purchase_intent'
                  AND julianday(e.event_timestamp) - julianday(a.assigned_at) BETWEEN 0 AND 14
                 THEN 1 ELSE 0 END) AS intent_14d,
        MAX(CASE WHEN e.event_name = 'push_unsubscribe' THEN 1 ELSE 0 END) AS push_unsubscribed
    FROM assigned a
    LEFT JOIN events e ON e.user_id = a.user_id
    GROUP BY a.user_id
),
order_metrics AS (
    SELECT
        a.user_id,
        MAX(CASE WHEN o.order_status = 'paid'
                  AND julianday(o.order_timestamp) - julianday(a.assigned_at) BETWEEN 0 AND 30
                 THEN 1 ELSE 0 END) AS paid_order_30d,
        SUM(CASE WHEN o.order_status = 'paid'
                  AND julianday(o.order_timestamp) - julianday(a.assigned_at) BETWEEN 0 AND 30
                 THEN o.gross_revenue ELSE 0 END) AS revenue_30d
    FROM assigned a
    LEFT JOIN orders o ON o.user_id = a.user_id
    GROUP BY a.user_id
),
subscription_flags AS (
    SELECT
        a.user_id,
        MAX(CASE WHEN s.renewal_window IN ('renewal_due', 'new_purchase') AND s.auto_renew_flag = 1 THEN 1 ELSE 0 END) AS auto_renew_enabled
    FROM assigned a
    LEFT JOIN subscriptions s ON s.user_id = a.user_id
    GROUP BY a.user_id
),
user_metrics AS (
    SELECT
        a.user_id,
        a.variant,
        COALESCE(tf.reached, 0) AS reached,
        COALESCE(ef.intent_14d, 0) AS intent_14d,
        COALESCE(om.paid_order_30d, 0) AS paid_order_30d,
        COALESCE(om.revenue_30d, 0) AS revenue_30d,
        COALESCE(sf.auto_renew_enabled, 0) AS auto_renew_enabled,
        COALESCE(ef.push_unsubscribed, 0) AS push_unsubscribed
    FROM assigned a
    LEFT JOIN touch_flags tf ON tf.user_id = a.user_id
    LEFT JOIN event_flags ef ON ef.user_id = a.user_id
    LEFT JOIN order_metrics om ON om.user_id = a.user_id
    LEFT JOIN subscription_flags sf ON sf.user_id = a.user_id
)
SELECT
    variant,
    COUNT(*) AS assigned_users,
    SUM(reached) AS reached_users,
    ROUND(1.0 * SUM(reached) / COUNT(*), 4) AS reach_rate,
    SUM(intent_14d) AS intent_14d_users,
    ROUND(1.0 * SUM(intent_14d) / COUNT(*), 4) AS intent_14d_rate,
    SUM(paid_order_30d) AS paid_order_30d_users,
    ROUND(1.0 * SUM(paid_order_30d) / COUNT(*), 4) AS paid_order_30d_rate,
    ROUND(SUM(revenue_30d), 2) AS revenue_30d,
    ROUND(SUM(revenue_30d) / COUNT(*), 2) AS revenue_per_assigned_user,
    SUM(auto_renew_enabled) AS auto_renew_users,
    ROUND(1.0 * SUM(auto_renew_enabled) / COUNT(*), 4) AS auto_renew_rate,
    SUM(push_unsubscribed) AS push_unsubscribed_users,
    ROUND(1.0 * SUM(push_unsubscribed) / COUNT(*), 4) AS push_unsubscribe_rate
FROM user_metrics
GROUP BY variant
ORDER BY
    CASE variant
        WHEN 'holdout' THEN 1
        WHEN 'control' THEN 2
        WHEN 'treatment' THEN 3
        ELSE 4
    END;
