from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from scipy import stats

from .config import SQL_DIR
from .database import read_sql
from .plotting import write_figures
from .reporting import write_report


SQL_FILES = {
    "lifecycle": "01_lifecycle_kpi_tree.sql",
    "retention": "02_feature_retention.sql",
    "product_revenue": "03_product_revenue.sql",
    "channel_funnel": "04_channel_touchpoint_funnel.sql",
    "experiment": "05_experiment_incrementality.sql",
    "attribution": "06_attribution_models.sql",
    "model_features": "07_model_features.sql",
    "operations": "08_operations_sla_quality.sql",
}


@dataclass(frozen=True)
class ExperimentStats:
    control_users: int
    treatment_users: int
    control_conversions: int
    treatment_conversions: int
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float
    ci_low: float
    ci_high: float
    p_value: float


def run_analysis(db_path: Path, report_path: Path, figure_dir: Path) -> dict[str, pd.DataFrame | ExperimentStats | float]:
    tables = {name: _run_sql_file(db_path, sql_file) for name, sql_file in SQL_FILES.items()}
    north_star_rate = _north_star_rate(db_path)
    experiment_stats = _experiment_stats(tables["experiment"])

    figure_paths = write_figures(
        lifecycle=tables["lifecycle"],
        retention=tables["retention"],
        product_revenue=tables["product_revenue"],
        channel_funnel=tables["channel_funnel"],
        experiment=tables["experiment"],
        attribution=tables["attribution"],
        operations=tables["operations"],
        experiment_stats=experiment_stats,
        figure_dir=figure_dir,
    )
    write_report(
        report_path=report_path,
        tables=tables,
        experiment_stats=experiment_stats,
        north_star_rate=north_star_rate,
        figure_paths=figure_paths,
    )

    tables_dir = report_path.parent / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        if name != "model_features":
            table.to_csv(tables_dir / f"{name}.csv", index=False)

    return {
        **tables,
        "experiment_stats": experiment_stats,
        "north_star_rate": north_star_rate,
    }


def _run_sql_file(db_path: Path, filename: str) -> pd.DataFrame:
    sql = (SQL_DIR / filename).read_text(encoding="utf-8")
    return read_sql(db_path, sql)


def _north_star_rate(db_path: Path) -> float:
    sql = """
    WITH service_active AS (
        SELECT DISTINCT u.user_id
        FROM users u
        JOIN events e ON e.user_id = u.user_id
        WHERE e.event_name IN ('feature_use', 'purchase_intent', 'order_create')
          AND julianday(e.event_timestamp) - julianday(u.register_date) BETWEEN 0 AND 30
    )
    SELECT 1.0 * COUNT(sa.user_id) / COUNT(u.user_id) AS rate
    FROM users u
    LEFT JOIN service_active sa ON sa.user_id = u.user_id;
    """
    result = read_sql(db_path, sql)
    return float(result.loc[0, "rate"])


def _experiment_stats(experiment: pd.DataFrame) -> ExperimentStats:
    control = experiment.loc[experiment["variant"] == "control"].iloc[0]
    treatment = experiment.loc[experiment["variant"] == "treatment"].iloc[0]

    control_users = int(control["assigned_users"])
    treatment_users = int(treatment["assigned_users"])
    control_conversions = int(control["paid_order_30d_users"])
    treatment_conversions = int(treatment["paid_order_30d_users"])
    control_rate = control_conversions / control_users
    treatment_rate = treatment_conversions / treatment_users
    absolute_lift = treatment_rate - control_rate
    relative_lift = absolute_lift / control_rate if control_rate else 0.0

    pooled = (control_conversions + treatment_conversions) / (control_users + treatment_users)
    z_denom = (pooled * (1 - pooled) * (1 / control_users + 1 / treatment_users)) ** 0.5
    z_score = absolute_lift / z_denom if z_denom else 0.0
    p_value = float(2 * (1 - stats.norm.cdf(abs(z_score))))

    se_diff = ((control_rate * (1 - control_rate) / control_users) + (treatment_rate * (1 - treatment_rate) / treatment_users)) ** 0.5
    ci_low = absolute_lift - 1.96 * se_diff
    ci_high = absolute_lift + 1.96 * se_diff

    return ExperimentStats(
        control_users=control_users,
        treatment_users=treatment_users,
        control_conversions=control_conversions,
        treatment_conversions=treatment_conversions,
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        absolute_lift=absolute_lift,
        relative_lift=relative_lift,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
    )
