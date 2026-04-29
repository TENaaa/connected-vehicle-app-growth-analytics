WITH user_flags AS (
    SELECT
        u.user_id,
        MAX(CASE WHEN e.event_name = 'app_login'
                  AND julianday(e.event_timestamp) - julianday(u.register_date) BETWEEN 0 AND 7
                 THEN 1 ELSE 0 END) AS d7_login,
        MAX(CASE WHEN e.event_name = 'feature_use'
                  AND julianday(e.event_timestamp) - julianday(u.register_date) BETWEEN 0 AND 30
                 THEN 1 ELSE 0 END) AS d30_core_feature,
        MAX(CASE WHEN tp.touchpoint_status = 'delivered' THEN 1 ELSE 0 END) AS reached_by_campaign,
        MAX(CASE WHEN e.event_name = 'purchase_intent' THEN 1 ELSE 0 END) AS purchase_intent,
        MAX(CASE WHEN o.order_status IN ('paid', 'refunded') THEN 1 ELSE 0 END) AS placed_order,
        MAX(CASE WHEN o.order_status = 'paid' THEN 1 ELSE 0 END) AS paid_order,
        MAX(CASE WHEN s.renewal_window IN ('due_soon', 'renewal_due') AND s.subscription_status = 'active' THEN 1 ELSE 0 END) AS renewal_base
    FROM users u
    LEFT JOIN events e ON e.user_id = u.user_id
    LEFT JOIN touchpoints tp ON tp.user_id = u.user_id
    LEFT JOIN orders o ON o.user_id = u.user_id
    LEFT JOIN subscriptions s ON s.user_id = u.user_id
    GROUP BY u.user_id
),
stages AS (
    SELECT '01_registered_users' AS stage, COUNT(*) AS users FROM user_flags
    UNION ALL SELECT '02_d7_login', SUM(d7_login) FROM user_flags
    UNION ALL SELECT '03_d30_core_feature', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 THEN 1 ELSE 0 END) FROM user_flags
    UNION ALL SELECT '04_campaign_reached', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 AND reached_by_campaign = 1 THEN 1 ELSE 0 END) FROM user_flags
    UNION ALL SELECT '05_purchase_intent', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 AND reached_by_campaign = 1 AND purchase_intent = 1 THEN 1 ELSE 0 END) FROM user_flags
    UNION ALL SELECT '06_order_created', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 AND reached_by_campaign = 1 AND purchase_intent = 1 AND placed_order = 1 THEN 1 ELSE 0 END) FROM user_flags
    UNION ALL SELECT '07_paid_order', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 AND reached_by_campaign = 1 AND purchase_intent = 1 AND placed_order = 1 AND paid_order = 1 THEN 1 ELSE 0 END) FROM user_flags
    UNION ALL SELECT '08_paid_with_active_subscription', SUM(CASE WHEN d7_login = 1 AND d30_core_feature = 1 AND reached_by_campaign = 1 AND purchase_intent = 1 AND placed_order = 1 AND paid_order = 1 AND renewal_base = 1 THEN 1 ELSE 0 END) FROM user_flags
),
base AS (
    SELECT users AS registered_users FROM stages WHERE stage = '01_registered_users'
)
SELECT
    stage,
    users,
    ROUND(1.0 * users / registered_users, 4) AS rate_of_registered,
    ROUND(
        1.0 * users
        / LAG(users) OVER (ORDER BY stage),
        4
    ) AS step_conversion_rate
FROM stages
CROSS JOIN base
ORDER BY stage;
