from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DataGenerationResult:
    output_dir: Path
    row_counts: dict[str, int]


PRODUCTS = [
    ("P001", "service_package", "connected_service_plus", 699.0, 210.0, 12, True, "renewal"),
    ("P002", "data_entertainment", "in_car_data_pack", 399.0, 160.0, 12, False, "trial_expiry"),
    ("P003", "protection", "extended_protection_plan", 1880.0, 1040.0, 36, False, "ownership"),
    ("P004", "roadside_care", "roadside_care_bundle", 199.0, 75.0, 12, True, "safety"),
    ("P005", "maintenance", "maintenance_coupon_pack", 299.0, 180.0, 12, False, "service_due"),
    ("P006", "charging", "energy_and_charging_pack", 459.0, 250.0, 12, True, "ev_owner"),
    ("P007", "smart_drive", "smart_drive_report_plus", 299.0, 90.0, 12, False, "feature_growth"),
    ("P008", "benefit_bundle", "owner_life_benefit_bundle", 259.0, 130.0, 12, True, "cross_sell"),
]

CAMPAIGNS = [
    ("CA01", "first_90d_onboarding", "new_owner", "P001", "2025-01-01", "2025-06-30", "app_card", 120000.0, "vehicle_age<=90d", True),
    ("CA02", "renewal_due_winback", "renewal_due", "P001", "2025-02-01", "2025-07-31", "call_center", 180000.0, "renewal_due<=60d", True),
    ("CA03", "in_car_data_trial_expiry", "trial_expiry", "P002", "2025-03-01", "2025-07-31", "push", 90000.0, "data_trial_expiring", True),
    ("CA04", "maintenance_service_due", "service_due", "P005", "2025-01-15", "2025-07-31", "dealer_lead", 110000.0, "service_due<=45d", True),
    ("CA05", "ev_energy_pack_growth", "ev_owner", "P006", "2025-02-15", "2025-07-31", "sms", 85000.0, "energy_type in EV/PHEV", True),
    ("CA06", "dormant_owner_reactivation", "dormant", "P008", "2025-04-01", "2025-07-31", "push", 70000.0, "app_sessions_30d<=1", True),
    ("CA07", "smart_drive_feature_education", "feature_growth", "P007", "2025-02-01", "2025-07-31", "app_card", 60000.0, "advanced_driver_assist", True),
    ("CA08", "roadside_care_safety_moment", "safety", "P004", "2025-01-01", "2025-07-31", "sms", 65000.0, "high_mileage_or_low_tire_pressure", True),
]

CONTENT_ITEMS = [
    ("C001", "homepage_card", "service_renewal", "P001", "CA02", True),
    ("C002", "push", "trial_expiry", "P002", "CA03", True),
    ("C003", "homepage_card", "maintenance_due", "P005", "CA04", True),
    ("C004", "sms", "energy_pack", "P006", "CA05", True),
    ("C005", "homepage_card", "smart_drive_report", "P007", "CA07", True),
    ("C006", "push", "owner_life_bundle", "P008", "CA06", True),
    ("C007", "call_script", "renewal_offer", "P001", "CA02", False),
    ("C008", "dealer_message", "service_lead", "P005", "CA04", False),
    ("C009", "sms", "roadside_care", "P004", "CA08", True),
    ("C010", "homepage_card", "first_90d_guide", "P001", "CA01", True),
]

CHANNEL_COST = {
    "app_card": 0.03,
    "push": 0.05,
    "sms": 0.18,
    "call_center": 6.50,
    "dealer_lead": 2.80,
    "organic": 0.00,
}


def generate_synthetic_data(output_dir: Path, n_users: int = 3000, seed: int = 42) -> DataGenerationResult:
    rng = np.random.default_rng(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_csv in output_dir.glob("*.csv"):
        stale_csv.unlink()

    user_ids = np.array([f"U{i:06d}" for i in range(1, n_users + 1)])
    register_dates = _random_dates(rng, "2025-01-01", n_users, 181)
    acquisition_channel = _choice(
        rng,
        ["dealer_qr", "app_store", "owner_message", "service_center", "referral", "brand_app"],
        n_users,
        [0.28, 0.18, 0.21, 0.13, 0.08, 0.12],
    )
    city_tier = _choice(rng, ["T1", "T2", "T3", "T4"], n_users, [0.17, 0.33, 0.32, 0.18])
    lifecycle_stage = _choice(
        rng,
        ["new_owner", "active_owner", "renewal_due", "dormant", "service_due"],
        n_users,
        [0.24, 0.30, 0.20, 0.12, 0.14],
    )
    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "register_date": register_dates.dt.strftime("%Y-%m-%d"),
            "city_tier": city_tier,
            "acquisition_channel": acquisition_channel,
            "lifecycle_stage": lifecycle_stage,
            "marketing_consent": _choice(rng, ["opt_in", "limited", "opt_out"], n_users, [0.77, 0.18, 0.05]),
        }
    )

    vehicle_segments = _choice(
        rng,
        ["compact_suv", "family_sedan", "ev_crossover", "premium_mpv", "pickup", "city_ev"],
        n_users,
        [0.25, 0.24, 0.18, 0.11, 0.08, 0.14],
    )
    energy_type = np.where(
        np.isin(vehicle_segments, ["ev_crossover", "city_ev"]),
        _choice(rng, ["EV", "PHEV"], n_users, [0.76, 0.24]),
        _choice(rng, ["ICE", "HEV", "PHEV"], n_users, [0.60, 0.27, 0.13]),
    )
    purchase_offsets = _purchase_offsets_for_stage(rng, lifecycle_stage)
    purchase_dates = pd.to_datetime(users["register_date"]) - pd.to_timedelta(purchase_offsets, unit="D")
    warranty_remaining = np.maximum(0, 36 - (purchase_offsets // 30))
    vehicles = pd.DataFrame(
        {
            "vehicle_id": [f"V{i:06d}" for i in range(1, n_users + 1)],
            "user_id": user_ids,
            "model_segment": vehicle_segments,
            "energy_type": energy_type,
            "purchase_date": purchase_dates.dt.strftime("%Y-%m-%d"),
            "vehicle_age_days": purchase_offsets,
            "vehicle_age_bucket": [_vehicle_age_bucket(int(days)) for days in purchase_offsets],
            "has_advanced_driver_assist": (rng.random(n_users) < np.where(np.isin(vehicle_segments, ["premium_mpv", "ev_crossover", "city_ev"]), 0.48, 0.18)).astype(int),
            "warranty_remaining_months": warranty_remaining.astype(int),
        }
    )

    trips_30d = rng.poisson(np.where(lifecycle_stage == "dormant", 10, np.where(lifecycle_stage == "new_owner", 24, 32))).clip(0, 110)
    app_sessions_30d = rng.poisson(
        np.select(
            [
                lifecycle_stage == "dormant",
                lifecycle_stage == "new_owner",
                lifecycle_stage == "renewal_due",
                lifecycle_stage == "service_due",
            ],
            [0.7, 2.8, 2.4, 3.2],
            default=4.4,
        )
    ).clip(0, 45)
    remote_commands_30d = rng.poisson(np.where(np.isin(energy_type, ["EV", "PHEV"]), 1.9, 0.8)).clip(0, 40)
    service_due_days = rng.integers(-20, 150, size=n_users)
    renewal_due_days = rng.integers(-30, 220, size=n_users)
    renewal_due_days = np.where(lifecycle_stage == "renewal_due", rng.integers(-15, 61, size=n_users), renewal_due_days)
    product_affinity = np.clip(
        0.35
        + 0.05 * (city_tier == "T1")
        + 0.07 * np.isin(energy_type, ["EV", "PHEV"])
        + 0.04 * (acquisition_channel == "referral")
        + 0.02 * app_sessions_30d
        + rng.normal(0, 0.10, size=n_users),
        0.02,
        0.98,
    )
    user_features = pd.DataFrame(
        {
            "user_id": user_ids,
            "trips_30d": trips_30d.astype(int),
            "app_sessions_30d": app_sessions_30d.astype(int),
            "remote_commands_30d": remote_commands_30d.astype(int),
            "driving_score": np.clip(rng.normal(76, 10, size=n_users), 35, 99).round(1),
            "energy_efficiency_score": np.clip(rng.normal(np.where(np.isin(energy_type, ["EV", "PHEV"]), 78, 70), 11), 30, 99).round(1),
            "service_due_days": service_due_days.astype(int),
            "warranty_remaining_months": warranty_remaining.astype(int),
            "renewal_due_days": renewal_due_days.astype(int),
            "product_affinity_score": product_affinity.round(4),
            "churn_risk_score": np.clip(0.62 - product_affinity + 0.18 * (lifecycle_stage == "dormant") + rng.normal(0, 0.08, size=n_users), 0.02, 0.98).round(4),
        }
    )

    variants = rng.choice(["control", "treatment", "holdout"], size=n_users, p=[0.43, 0.43, 0.14])
    assigned_at = pd.to_datetime(users["register_date"]) + pd.to_timedelta(rng.integers(0, 5, size=n_users), unit="D")
    assignments = pd.DataFrame(
        {
            "experiment_id": "personalized_multi_touch_v2",
            "user_id": user_ids,
            "variant": variants,
            "assigned_at": assigned_at.dt.strftime("%Y-%m-%d"),
        }
    )

    products = pd.DataFrame(
        PRODUCTS,
        columns=[
            "product_id",
            "product_category",
            "product_name",
            "list_price",
            "unit_cost",
            "subscription_months",
            "is_bundle",
            "lifecycle_stage",
        ],
    )
    campaigns = pd.DataFrame(
        CAMPAIGNS,
        columns=[
            "campaign_id",
            "campaign_name",
            "target_stage",
            "primary_product_id",
            "start_date",
            "end_date",
            "primary_channel",
            "budget",
            "targeting_rule",
            "has_holdout",
        ],
    )
    content_items = pd.DataFrame(
        CONTENT_ITEMS,
        columns=["content_id", "content_type", "content_intent", "product_id", "campaign_id", "personalization_eligible"],
    )

    user_frame = (
        users.merge(vehicles, on="user_id")
        .merge(user_features, on="user_id")
        .merge(assignments, on="user_id")
    )
    product_lookup = products.set_index("product_id").to_dict("index")

    events: list[dict[str, object]] = []
    touchpoints: list[dict[str, object]] = []
    orders: list[dict[str, object]] = []
    subscriptions: list[dict[str, object]] = []
    call_center_contacts: list[dict[str, object]] = []
    dealer_leads: list[dict[str, object]] = []

    for row in user_frame.itertuples(index=False):
        register_date = pd.Timestamp(row.register_date)
        assigned_date = pd.Timestamp(row.assigned_at)
        user_score = _base_propensity(row)

        _add_base_activity(events, row, register_date, rng)
        _add_existing_subscription(subscriptions, row, register_date, rng)

        campaign_id, product_id = _select_campaign_and_product(row, rng)
        planned_channels = _planned_channels(row.variant, campaign_id, rng)
        primary_content = _content_for_campaign(campaign_id)
        converted = False
        order_id_for_lead: str | None = None

        for touch_rank, channel in enumerate(planned_channels, start=1):
            touch_time = assigned_date + pd.to_timedelta(int(rng.integers(0, 15)), unit="D")
            touchpoint_id = f"T{len(touchpoints) + 1:08d}"
            delivered_prob = 0.96 if channel in {"app_card", "push", "organic"} else 0.90 if channel == "sms" else 0.82
            delivered = rng.random() < delivered_prob and row.marketing_consent != "opt_out"
            touchpoints.append(
                {
                    "touchpoint_id": touchpoint_id,
                    "user_id": row.user_id,
                    "campaign_id": campaign_id,
                    "product_id": product_id,
                    "channel": channel,
                    "touchpoint_time": touch_time.strftime("%Y-%m-%d"),
                    "touchpoint_rank": touch_rank,
                    "touchpoint_status": "delivered" if delivered else "failed",
                    "touchpoint_cost": round(CHANNEL_COST[channel] * rng.uniform(0.85, 1.25), 2),
                    "is_high_pressure_contact": int(channel in {"call_center", "sms"} and touch_rank >= 3),
                }
            )
            if not delivered:
                continue

            events.append(_event(row, touch_time, "content_exposure", primary_content, campaign_id, product_id, channel, touchpoint_id))
            click_prob = np.clip(user_score + _channel_click_bonus(channel) + (0.06 if row.variant == "treatment" else 0.0), 0.03, 0.82)
            clicked = rng.random() < click_prob
            if clicked:
                click_time = touch_time + pd.to_timedelta(int(rng.integers(0, 3)), unit="D")
                events.append(_event(row, click_time, "content_click", primary_content, campaign_id, product_id, channel, touchpoint_id))
            intent_prob = np.clip(user_score + (0.12 if clicked else -0.03) + (0.07 if row.variant == "treatment" else 0.0), 0.02, 0.76)
            has_intent = rng.random() < intent_prob
            if has_intent:
                intent_time = touch_time + pd.to_timedelta(int(rng.integers(0, 8)), unit="D")
                events.append(_event(row, intent_time, "purchase_intent", primary_content, campaign_id, product_id, channel, touchpoint_id))
            order_prob = np.clip(user_score * 0.48 + (0.16 if has_intent else 0.0) + (0.05 if channel == "call_center" else 0.0), 0.01, 0.58)
            if not converted and rng.random() < order_prob:
                product = product_lookup[product_id]
                discount = _discount_for_variant(row.variant, rng)
                revenue = round(float(product["list_price"]) * (1 - discount), 2)
                cost = round(float(product["unit_cost"]), 2)
                order_time = touch_time + pd.to_timedelta(int(rng.integers(1, 18)), unit="D")
                order_id = f"O{len(orders) + 1:08d}"
                converted = True
                order_id_for_lead = order_id
                orders.append(
                    {
                        "order_id": order_id,
                        "user_id": row.user_id,
                        "vehicle_id": row.vehicle_id,
                        "product_id": product_id,
                        "campaign_id": campaign_id,
                        "attributed_touchpoint_id": touchpoint_id,
                        "order_timestamp": order_time.strftime("%Y-%m-%d"),
                        "order_channel": channel,
                        "order_status": rng.choice(["paid", "paid", "paid", "refunded"], p=[0.55, 0.30, 0.11, 0.04]),
                        "gross_revenue": revenue,
                        "unit_cost": cost,
                        "gross_margin": round(revenue - cost, 2),
                    }
                )
                events.append(_event(row, order_time, "order_create", primary_content, campaign_id, product_id, channel, touchpoint_id))
                if product["subscription_months"] > 0:
                    subscriptions.append(
                        {
                            "subscription_id": f"S{len(subscriptions) + 1:08d}",
                            "user_id": row.user_id,
                            "product_id": product_id,
                            "start_date": order_time.strftime("%Y-%m-%d"),
                            "expiry_date": (order_time + pd.DateOffset(months=int(product["subscription_months"]))).strftime("%Y-%m-%d"),
                            "renewal_window": "new_purchase" if row.lifecycle_stage != "renewal_due" else "renewal_due",
                            "subscription_status": "active",
                            "auto_renew_flag": int(rng.random() < (0.24 + 0.18 * (row.variant == "treatment"))),
                        }
                    )
            if channel == "call_center":
                call_center_contacts.append(_call_contact(row, touchpoint_id, campaign_id, product_id, touch_time, clicked, has_intent, converted, rng))
            if channel == "dealer_lead":
                dealer_leads.append(_dealer_lead(row, touchpoint_id, campaign_id, product_id, touch_time, order_id_for_lead, converted, rng))

        if rng.random() < 0.02 + 0.05 * (row.variant == "control") + 0.03 * (row.lifecycle_stage == "dormant"):
            events.append(
                _event(
                    row,
                    assigned_date + pd.to_timedelta(int(rng.integers(3, 30)), unit="D"),
                    "push_unsubscribe",
                    primary_content,
                    campaign_id,
                    product_id,
                    "push",
                    None,
                )
            )

    events_df = pd.DataFrame(events).sort_values(["user_id", "event_timestamp", "event_name"]).reset_index(drop=True)
    events_df.insert(0, "event_id", [f"E{i:08d}" for i in range(1, len(events_df) + 1)])
    touchpoints_df = pd.DataFrame(touchpoints)
    orders_df = pd.DataFrame(orders)
    subscriptions_df = pd.DataFrame(subscriptions)
    call_center_df = pd.DataFrame(call_center_contacts)
    dealer_leads_df = pd.DataFrame(dealer_leads)

    tables = {
        "users": users,
        "vehicles": vehicles,
        "products": products,
        "campaigns": campaigns,
        "content_items": content_items,
        "experiment_assignments": assignments,
        "user_features": user_features,
        "touchpoints": touchpoints_df,
        "events": events_df,
        "subscriptions": subscriptions_df,
        "orders": orders_df,
        "call_center_contacts": call_center_df,
        "dealer_leads": dealer_leads_df,
    }
    tables["data_quality_checks"] = _build_data_quality_checks(tables)

    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)

    return DataGenerationResult(output_dir=output_dir, row_counts={name: len(table) for name, table in tables.items()})


def _random_dates(rng: np.random.Generator, start: str, periods: int, max_days: int) -> pd.Series:
    base = pd.Timestamp(start)
    offsets = rng.integers(0, max_days, size=periods)
    return pd.Series(base + pd.to_timedelta(offsets, unit="D"))


def _choice(rng: np.random.Generator, values: list[str], size: int, probs: list[float]) -> np.ndarray:
    return rng.choice(values, size=size, p=np.array(probs) / np.sum(probs))


def _purchase_offsets_for_stage(rng: np.random.Generator, lifecycle_stage: np.ndarray) -> np.ndarray:
    offsets = rng.integers(0, 720, size=len(lifecycle_stage))
    offsets = np.where(lifecycle_stage == "new_owner", rng.integers(0, 91, size=len(lifecycle_stage)), offsets)
    offsets = np.where(lifecycle_stage == "renewal_due", rng.integers(300, 720, size=len(lifecycle_stage)), offsets)
    offsets = np.where(lifecycle_stage == "service_due", rng.integers(120, 540, size=len(lifecycle_stage)), offsets)
    return offsets.astype(int)


def _vehicle_age_bucket(days_since_purchase: int) -> str:
    if days_since_purchase <= 30:
        return "0-30d"
    if days_since_purchase <= 90:
        return "31-90d"
    if days_since_purchase <= 180:
        return "91-180d"
    if days_since_purchase <= 365:
        return "181-365d"
    return "366d+"


def _base_propensity(row: object) -> float:
    city_bonus = {"T1": 0.035, "T2": 0.024, "T3": 0.008, "T4": -0.006}[row.city_tier]
    channel_bonus = {
        "dealer_qr": 0.018,
        "owner_message": 0.014,
        "app_store": 0.002,
        "service_center": 0.020,
        "referral": 0.036,
        "brand_app": 0.016,
    }[row.acquisition_channel]
    stage_bonus = {
        "new_owner": 0.040,
        "active_owner": 0.034,
        "renewal_due": 0.026,
        "dormant": -0.025,
        "service_due": 0.028,
    }[row.lifecycle_stage]
    energy_bonus = 0.018 if row.energy_type in {"EV", "PHEV"} else 0.0
    app_bonus = min(float(row.app_sessions_30d) * 0.006, 0.070)
    risk_penalty = float(row.churn_risk_score) * 0.045
    return float(np.clip(0.13 + city_bonus + channel_bonus + stage_bonus + energy_bonus + app_bonus - risk_penalty, 0.03, 0.62))


def _add_base_activity(events: list[dict[str, object]], row: object, register_date: pd.Timestamp, rng: np.random.Generator) -> None:
    login_count = int(min(row.app_sessions_30d, 12))
    for _ in range(login_count):
        ts = register_date + pd.to_timedelta(int(rng.integers(0, 31)), unit="D")
        events.append(_event(row, ts, "app_login", None, None, None, "organic", None))
    feature_count = int(min(row.remote_commands_30d, 8))
    for _ in range(feature_count):
        ts = register_date + pd.to_timedelta(int(rng.integers(0, 31)), unit="D")
        events.append(_event(row, ts, "feature_use", None, None, None, "organic", None))


def _add_existing_subscription(subscriptions: list[dict[str, object]], row: object, register_date: pd.Timestamp, rng: np.random.Generator) -> None:
    start = register_date - pd.to_timedelta(int(rng.integers(20, 340)), unit="D")
    expiry = register_date + pd.to_timedelta(max(15, int(row.renewal_due_days)), unit="D")
    subscriptions.append(
        {
            "subscription_id": f"S{len(subscriptions) + 1:08d}",
            "user_id": row.user_id,
            "product_id": "P001",
            "start_date": start.strftime("%Y-%m-%d"),
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "renewal_window": "due_soon" if row.renewal_due_days <= 60 else "not_due",
            "subscription_status": "active" if row.lifecycle_stage != "dormant" else rng.choice(["active", "expired"], p=[0.55, 0.45]),
            "auto_renew_flag": int(rng.random() < 0.18),
        }
    )


def _select_campaign_and_product(row: object, rng: np.random.Generator) -> tuple[str, str]:
    if row.lifecycle_stage == "new_owner":
        return "CA01", "P001"
    if row.lifecycle_stage == "renewal_due":
        return "CA02", "P001"
    if row.lifecycle_stage == "service_due" or row.service_due_days <= 45:
        return "CA04", "P005"
    if row.energy_type in {"EV", "PHEV"} and rng.random() < 0.56:
        return "CA05", "P006"
    if row.has_advanced_driver_assist and rng.random() < 0.42:
        return "CA07", "P007"
    if row.lifecycle_stage == "dormant":
        return "CA06", "P008"
    return str(rng.choice(["CA03", "CA08", "CA06"], p=[0.42, 0.24, 0.34])), str(rng.choice(["P002", "P004", "P008"], p=[0.42, 0.24, 0.34]))


def _planned_channels(variant: str, campaign_id: str, rng: np.random.Generator) -> list[str]:
    if variant == "holdout":
        return ["organic"] if rng.random() < 0.20 else []
    primary = {
        "CA01": "app_card",
        "CA02": "call_center",
        "CA03": "push",
        "CA04": "dealer_lead",
        "CA05": "sms",
        "CA06": "push",
        "CA07": "app_card",
        "CA08": "sms",
    }[campaign_id]
    if variant == "control":
        return [primary]
    sequence = [primary]
    if primary != "app_card" and rng.random() < 0.55:
        sequence.append("app_card")
    if primary != "push" and rng.random() < 0.42:
        sequence.append("push")
    if campaign_id in {"CA02", "CA04"} and primary != "call_center" and rng.random() < 0.20:
        sequence.append("call_center")
    return sequence[:3]


def _content_for_campaign(campaign_id: str) -> str:
    for content_id, _, _, _, item_campaign_id, _ in CONTENT_ITEMS:
        if item_campaign_id == campaign_id:
            return content_id
    return "C001"


def _channel_click_bonus(channel: str) -> float:
    return {
        "app_card": 0.13,
        "push": 0.07,
        "sms": 0.04,
        "call_center": 0.11,
        "dealer_lead": 0.08,
        "organic": 0.02,
    }[channel]


def _discount_for_variant(variant: str, rng: np.random.Generator) -> float:
    base = 0.08 if variant == "treatment" else 0.03 if variant == "control" else 0.0
    return float(np.clip(base + rng.normal(0.02, 0.025), 0.0, 0.18))


def _event(
    row: object,
    event_timestamp: pd.Timestamp,
    event_name: str,
    content_id: str | None,
    campaign_id: str | None,
    product_id: str | None,
    channel: str | None,
    touchpoint_id: str | None,
) -> dict[str, object]:
    return {
        "user_id": row.user_id,
        "vehicle_id": row.vehicle_id,
        "event_timestamp": event_timestamp.strftime("%Y-%m-%d"),
        "event_name": event_name,
        "content_id": content_id,
        "campaign_id": campaign_id,
        "product_id": product_id,
        "channel": channel,
        "touchpoint_id": touchpoint_id,
    }


def _call_contact(
    row: object,
    touchpoint_id: str,
    campaign_id: str,
    product_id: str,
    touch_time: pd.Timestamp,
    clicked: bool,
    has_intent: bool,
    converted: bool,
    rng: np.random.Generator,
) -> dict[str, object]:
    reached = rng.random() < (0.58 + 0.14 * clicked)
    return {
        "contact_id": f"CC{touchpoint_id[1:]}",
        "touchpoint_id": touchpoint_id,
        "user_id": row.user_id,
        "campaign_id": campaign_id,
        "product_id": product_id,
        "contact_timestamp": touch_time.strftime("%Y-%m-%d"),
        "contact_status": "reached" if reached else rng.choice(["no_answer", "invalid_window"], p=[0.82, 0.18]),
        "talk_seconds": int(rng.integers(45, 520) if reached else 0),
        "contact_outcome": "converted" if converted else "interested" if has_intent else "refused" if reached else "unreached",
        "agent_tier": rng.choice(["A", "B", "C"], p=[0.25, 0.50, 0.25]),
    }


def _dealer_lead(
    row: object,
    touchpoint_id: str,
    campaign_id: str,
    product_id: str,
    touch_time: pd.Timestamp,
    converted_order_id: str | None,
    converted: bool,
    rng: np.random.Generator,
) -> dict[str, object]:
    sla_hours = float(np.round(rng.gamma(shape=2.2, scale=9.0), 1))
    first_contact = touch_time + pd.to_timedelta(max(1, int(round(sla_hours))), unit="h")
    return {
        "lead_id": f"DL{touchpoint_id[1:]}",
        "touchpoint_id": touchpoint_id,
        "user_id": row.user_id,
        "vehicle_id": row.vehicle_id,
        "campaign_id": campaign_id,
        "product_id": product_id,
        "lead_type": rng.choice(["maintenance_due", "diagnostic_followup", "benefit_redemption"], p=[0.63, 0.22, 0.15]),
        "created_at": touch_time.strftime("%Y-%m-%d"),
        "first_contact_at": first_contact.strftime("%Y-%m-%d"),
        "sla_hours": sla_hours,
        "lead_status": "converted" if converted else rng.choice(["contacted", "open", "closed_lost"], p=[0.46, 0.24, 0.30]),
        "converted_order_id": converted_order_id,
    }


def _build_data_quality_checks(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    users = tables["users"]
    vehicles = tables["vehicles"]
    events = tables["events"]
    touchpoints = tables["touchpoints"]
    orders = tables["orders"]
    assignments = tables["experiment_assignments"]

    rows: list[dict[str, object]] = []
    missing_vehicle_users = users.loc[~users["user_id"].isin(vehicles["user_id"])]
    rows.append(_quality_row("users_have_vehicle", len(users), len(missing_vehicle_users)))

    joined_events = events.merge(users[["user_id", "register_date"]], on="user_id", how="left")
    bad_events = joined_events.loc[pd.to_datetime(joined_events["event_timestamp"]) < pd.to_datetime(joined_events["register_date"])]
    rows.append(_quality_row("event_time_after_registration", len(joined_events), len(bad_events)))

    if orders.empty:
        rows.append(_quality_row("orders_have_valid_touchpoint", 0, 0))
        rows.append(_quality_row("order_time_after_touchpoint", 0, 0))
        rows.append(_quality_row("revenue_non_negative", 0, 0))
    else:
        order_touch = orders.merge(
            touchpoints[["touchpoint_id", "touchpoint_time"]],
            left_on="attributed_touchpoint_id",
            right_on="touchpoint_id",
            how="left",
        )
        rows.append(_quality_row("orders_have_valid_touchpoint", len(orders), int(order_touch["touchpoint_time"].isna().sum())))
        bad_order_time = order_touch.loc[pd.to_datetime(order_touch["order_timestamp"]) < pd.to_datetime(order_touch["touchpoint_time"])]
        rows.append(_quality_row("order_time_after_touchpoint", len(order_touch), len(bad_order_time)))
        bad_revenue = orders.loc[(orders["gross_revenue"] < 0) | (orders["unit_cost"] < 0)]
        rows.append(_quality_row("revenue_non_negative", len(orders), len(bad_revenue)))

    variant_share = assignments["variant"].value_counts(normalize=True)
    balance_failed = int(variant_share.get("control", 0) < 0.36 or variant_share.get("treatment", 0) < 0.36 or variant_share.get("holdout", 0) < 0.08)
    rows.append(_quality_row("experiment_variant_balance", len(assignments), balance_failed))

    contact_pressure = touchpoints.groupby("user_id")["is_high_pressure_contact"].sum().reset_index()
    over_contacted = int((contact_pressure["is_high_pressure_contact"] >= 3).sum()) if not contact_pressure.empty else 0
    rows.append(_quality_row("high_pressure_contact_guardrail", len(contact_pressure), over_contacted, warn_threshold=0.08))

    return pd.DataFrame(rows)


def _quality_row(check_name: str, checked_rows: int, failed_rows: int, warn_threshold: float = 0.001) -> dict[str, object]:
    fail_rate = 0.0 if checked_rows == 0 else failed_rows / checked_rows
    return {
        "check_name": check_name,
        "check_status": "pass" if fail_rate <= warn_threshold else "warn",
        "checked_rows": int(checked_rows),
        "failed_rows": int(failed_rows),
        "fail_rate": round(float(fail_rate), 6),
    }
