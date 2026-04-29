WITH cohort_users AS (
    SELECT
        user_id,
        substr(register_date, 1, 7) AS cohort_month,
        register_date
    FROM users
),
activity AS (
    SELECT DISTINCT
        cu.user_id,
        cu.cohort_month,
        CASE
            WHEN julianday(e.event_timestamp) - julianday(cu.register_date) BETWEEN 0 AND 6 THEN 'W1_D0_6'
            WHEN julianday(e.event_timestamp) - julianday(cu.register_date) BETWEEN 7 AND 13 THEN 'W2_D7_13'
            WHEN julianday(e.event_timestamp) - julianday(cu.register_date) BETWEEN 14 AND 20 THEN 'W3_D14_20'
            WHEN julianday(e.event_timestamp) - julianday(cu.register_date) BETWEEN 21 AND 30 THEN 'W4_D21_30'
        END AS activity_window
    FROM cohort_users cu
    JOIN events e ON e.user_id = cu.user_id
    WHERE e.event_name IN ('app_login', 'feature_use', 'content_click', 'purchase_intent', 'order_create')
      AND julianday(e.event_timestamp) - julianday(cu.register_date) BETWEEN 0 AND 30
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_users
    FROM cohort_users
    GROUP BY cohort_month
),
window_counts AS (
    SELECT
        cohort_month,
        activity_window,
        COUNT(DISTINCT user_id) AS active_users
    FROM activity
    WHERE activity_window IS NOT NULL
    GROUP BY cohort_month, activity_window
)
SELECT
    wc.cohort_month,
    wc.activity_window,
    cs.cohort_users,
    wc.active_users,
    ROUND(1.0 * wc.active_users / cs.cohort_users, 4) AS retention_rate,
    ROUND(
        1.0 * wc.active_users
        / FIRST_VALUE(wc.active_users) OVER (
            PARTITION BY wc.cohort_month
            ORDER BY wc.activity_window
        ),
        4
    ) AS indexed_to_w1
FROM window_counts wc
JOIN cohort_size cs ON cs.cohort_month = wc.cohort_month
ORDER BY wc.cohort_month, wc.activity_window;
