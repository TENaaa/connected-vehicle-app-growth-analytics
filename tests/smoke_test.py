from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cv_growth.analysis import run_analysis
from cv_growth.config import SQL_DIR
from cv_growth.data_generation import generate_synthetic_data
from cv_growth.database import build_database
from cv_growth.modeling import export_high_value_audience, train_propensity_model


REQUIRED_TABLES = {
    "users",
    "vehicles",
    "products",
    "campaigns",
    "content_items",
    "experiment_assignments",
    "user_features",
    "touchpoints",
    "events",
    "subscriptions",
    "orders",
    "call_center_contacts",
    "dealer_leads",
    "data_quality_checks",
}

FORBIDDEN_TERMS = [
    "\u5b89\u5409\u661f",
    "\u4e0a\u6c7d",
    "\u901a\u7528",
    "BD" + "CO",
    "S" + "GM",
    "On" + "Star",
    "SO" + "S",
    "V" + "IN",
]


def test_pipeline_runs_end_to_end() -> None:
    with TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        csv_dir = tmp_dir / "data"
        db_path = tmp_dir / "analytics.sqlite"
        report_path = tmp_dir / "reports" / "case.md"
        figure_dir = tmp_dir / "reports" / "figures"
        metrics_path = tmp_dir / "output" / "model_metrics.json"
        model_card_path = tmp_dir / "reports" / "propensity_model_card.md"
        audience_path = tmp_dir / "output" / "audience.csv"

        result = generate_synthetic_data(csv_dir, n_users=750, seed=7)
        assert REQUIRED_TABLES.issubset(result.row_counts)
        assert result.row_counts["users"] == 750
        assert result.row_counts["vehicles"] == 750
        assert result.row_counts["experiment_assignments"] == 750
        assert result.row_counts["touchpoints"] > 500
        assert result.row_counts["events"] > 3000
        assert result.row_counts["orders"] > 80

        _assert_data_quality(csv_dir)
        row_counts = build_database(csv_dir, db_path)
        assert row_counts["orders"] == result.row_counts["orders"]

        with sqlite3.connect(db_path) as conn:
            for sql_file in sorted(SQL_DIR.glob("*.sql")):
                df = pd.read_sql_query(sql_file.read_text(encoding="utf-8"), conn)
                assert not df.empty, sql_file.name

        outputs = run_analysis(db_path, report_path, figure_dir)
        assert report_path.exists()
        report_text = report_path.read_text(encoding="utf-8")
        assert "生命周期 KPI Tree" in report_text
        assert "归因口径敏感性" in report_text
        assert outputs["north_star_rate"] > 0
        assert len(list(figure_dir.glob("*.png"))) == 7

        metrics = train_propensity_model(db_path, metrics_path, model_card_path)
        assert metrics_path.exists()
        assert model_card_path.exists()
        assert float(metrics["auc"]) > 0.55
        assert float(metrics["top_decile_conversion_rate"]) > float(metrics["overall_test_conversion_rate"])
        assert json.loads(metrics_path.read_text(encoding="utf-8"))["model_name"]

        audience = export_high_value_audience(db_path, audience_path, top_n=50)
        assert audience_path.exists()
        assert len(audience) == 50
        assert audience["predicted_conversion_score"].is_monotonic_decreasing
        assert set(audience["recommended_channel"]).issubset({"app_card", "push", "call_center", "dealer_lead"})


def _assert_data_quality(csv_dir: Path) -> None:
    users = pd.read_csv(csv_dir / "users.csv")
    vehicles = pd.read_csv(csv_dir / "vehicles.csv")
    events = pd.read_csv(csv_dir / "events.csv")
    assignments = pd.read_csv(csv_dir / "experiment_assignments.csv")
    touchpoints = pd.read_csv(csv_dir / "touchpoints.csv")
    orders = pd.read_csv(csv_dir / "orders.csv")
    quality = pd.read_csv(csv_dir / "data_quality_checks.csv")

    assert users["user_id"].is_unique
    assert vehicles["user_id"].is_unique
    assert set(events["user_id"]).issubset(set(users["user_id"]))
    assert set(touchpoints["user_id"]).issubset(set(users["user_id"]))
    assert set(orders["user_id"]).issubset(set(users["user_id"]))
    assert set(orders["attributed_touchpoint_id"]).issubset(set(touchpoints["touchpoint_id"]))

    joined_events = events.merge(users[["user_id", "register_date"]], on="user_id", how="left")
    assert (pd.to_datetime(joined_events["event_timestamp"]) >= pd.to_datetime(joined_events["register_date"])).all()

    order_touch = orders.merge(
        touchpoints[["touchpoint_id", "touchpoint_time"]],
        left_on="attributed_touchpoint_id",
        right_on="touchpoint_id",
        how="left",
    )
    assert (pd.to_datetime(order_touch["order_timestamp"]) >= pd.to_datetime(order_touch["touchpoint_time"])).all()
    assert (orders[["gross_revenue", "unit_cost", "gross_margin"]] >= 0).all().all()

    variant_share = assignments["variant"].value_counts(normalize=True)
    assert 0.36 <= variant_share["control"] <= 0.50
    assert 0.36 <= variant_share["treatment"] <= 0.50
    assert 0.08 <= variant_share["holdout"] <= 0.20
    assert set(quality["check_status"]).issubset({"pass", "warn"})

    for csv_path in csv_dir.glob("*.csv"):
        text = csv_path.read_text(encoding="utf-8")
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"{term} leaked in {csv_path.name}"


if __name__ == "__main__":
    test_pipeline_runs_end_to_end()
    print("connected-vehicle-app-growth-analytics smoke test passed")
