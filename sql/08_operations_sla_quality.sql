WITH call_metrics AS (
    SELECT
        'call_center' AS domain,
        'reach_rate' AS metric,
        campaign_id AS segment,
        SUM(CASE WHEN contact_status = 'reached' THEN 1 ELSE 0 END) AS numerator,
        COUNT(*) AS denominator,
        ROUND(1.0 * SUM(CASE WHEN contact_status = 'reached' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS rate,
        ROUND(AVG(talk_seconds), 2) AS value
    FROM call_center_contacts
    GROUP BY campaign_id
),
lead_metrics AS (
    SELECT
        'dealer_lead' AS domain,
        'within_24h_sla_rate' AS metric,
        lead_type AS segment,
        SUM(CASE WHEN sla_hours <= 24 THEN 1 ELSE 0 END) AS numerator,
        COUNT(*) AS denominator,
        ROUND(1.0 * SUM(CASE WHEN sla_hours <= 24 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS rate,
        ROUND(AVG(sla_hours), 2) AS value
    FROM dealer_leads
    GROUP BY lead_type
),
quality_metrics AS (
    SELECT
        'data_quality' AS domain,
        check_name AS metric,
        check_status AS segment,
        checked_rows - failed_rows AS numerator,
        checked_rows AS denominator,
        ROUND(1.0 - fail_rate, 4) AS rate,
        failed_rows AS value
    FROM data_quality_checks
),
pressure_metrics AS (
    SELECT
        'contact_policy' AS domain,
        'high_pressure_contact_share' AS metric,
        'all_users' AS segment,
        SUM(CASE WHEN high_pressure_contacts >= 2 THEN 1 ELSE 0 END) AS numerator,
        COUNT(*) AS denominator,
        ROUND(1.0 * SUM(CASE WHEN high_pressure_contacts >= 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS rate,
        ROUND(AVG(high_pressure_contacts), 2) AS value
    FROM (
        SELECT
            user_id,
            SUM(is_high_pressure_contact) AS high_pressure_contacts
        FROM touchpoints
        GROUP BY user_id
    )
)
SELECT * FROM call_metrics
UNION ALL
SELECT * FROM lead_metrics
UNION ALL
SELECT * FROM quality_metrics
UNION ALL
SELECT * FROM pressure_metrics
ORDER BY domain, metric, segment;
