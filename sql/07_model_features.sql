WITH touch_features AS (
    SELECT
        user_id,
        COUNT(*) AS touchpoints_14d,
        SUM(CASE WHEN channel = 'call_center' AND touchpoint_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_calls,
        SUM(CASE WHEN channel = 'dealer_lead' AND touchpoint_status = 'delivered' THEN 1 ELSE 0 END) AS dealer_lead_touches,
        SUM(CASE WHEN is_high_pressure_contact = 1 THEN 1 ELSE 0 END) AS high_pressure_contacts
    FROM touchpoints
    GROUP BY user_id
),
target AS (
    SELECT
        ea.user_id,
        MAX(CASE WHEN o.order_status = 'paid'
                  AND julianday(o.order_timestamp) - julianday(ea.assigned_at) BETWEEN 0 AND 30
                 THEN 1 ELSE 0 END) AS converted_next_30d
    FROM experiment_assignments ea
    LEFT JOIN orders o ON o.user_id = ea.user_id
    GROUP BY ea.user_id
)
SELECT
    u.user_id,
    t.converted_next_30d,
    u.city_tier,
    u.acquisition_channel,
    u.lifecycle_stage,
    u.marketing_consent,
    v.model_segment,
    v.energy_type,
    v.vehicle_age_bucket,
    v.has_advanced_driver_assist,
    uf.trips_30d,
    uf.app_sessions_30d,
    uf.remote_commands_30d,
    uf.driving_score,
    uf.energy_efficiency_score,
    uf.service_due_days,
    uf.warranty_remaining_months,
    uf.renewal_due_days,
    uf.product_affinity_score,
    uf.churn_risk_score,
    COALESCE(tf.touchpoints_14d, 0) AS touchpoints_14d,
    COALESCE(tf.delivered_calls, 0) AS delivered_calls,
    COALESCE(tf.dealer_lead_touches, 0) AS dealer_lead_touches,
    COALESCE(tf.high_pressure_contacts, 0) AS high_pressure_contacts
FROM users u
JOIN vehicles v ON v.user_id = u.user_id
JOIN user_features uf ON uf.user_id = u.user_id
JOIN target t ON t.user_id = u.user_id
LEFT JOIN touch_features tf ON tf.user_id = u.user_id;
