from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cv_growth_matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/cv_growth_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

if TYPE_CHECKING:
    from .analysis import ExperimentStats


def write_figures(
    lifecycle: pd.DataFrame,
    retention: pd.DataFrame,
    product_revenue: pd.DataFrame,
    channel_funnel: pd.DataFrame,
    experiment: pd.DataFrame,
    attribution: pd.DataFrame,
    operations: pd.DataFrame,
    experiment_stats: "ExperimentStats",
    figure_dir: Path,
) -> dict[str, Path]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "lifecycle": figure_dir / "lifecycle_kpi_tree.png",
        "retention": figure_dir / "feature_retention.png",
        "product_revenue": figure_dir / "product_revenue_mix.png",
        "channel_funnel": figure_dir / "channel_touchpoint_funnel.png",
        "experiment": figure_dir / "experiment_incrementality.png",
        "attribution": figure_dir / "attribution_models.png",
        "operations": figure_dir / "operations_quality.png",
    }
    _plot_lifecycle(lifecycle, paths["lifecycle"])
    _plot_retention(retention, paths["retention"])
    _plot_product_revenue(product_revenue, paths["product_revenue"])
    _plot_channel_funnel(channel_funnel, paths["channel_funnel"])
    _plot_experiment(experiment, experiment_stats, paths["experiment"])
    _plot_attribution(attribution, paths["attribution"])
    _plot_operations(operations, paths["operations"])
    return paths


def _plot_lifecycle(lifecycle: pd.DataFrame, path: Path) -> None:
    plot_df = lifecycle.copy()
    plot_df["stage_label"] = plot_df["stage"].str.replace(r"^\d+_", "", regex=True).str.replace("_", " ")
    ax = plot_df.plot(kind="bar", x="stage_label", y="rate_of_registered", legend=False, figsize=(11, 5), color="#2D9C7F")
    ax.set_title("Lifecycle KPI Tree")
    ax.set_ylabel("Rate of registered users")
    ax.set_xlabel("")
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_retention(retention: pd.DataFrame, path: Path) -> None:
    pivot = retention.pivot_table(index="cohort_month", columns="activity_window", values="retention_rate")
    ax = pivot.plot(marker="o", figsize=(10, 5), color=["#4E79A7", "#F28E2B", "#59A14F", "#E15759"])
    ax.set_title("Feature Retention by Registration Cohort")
    ax.set_ylabel("Retention rate")
    ax.set_xlabel("Registration cohort")
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_product_revenue(product_revenue: pd.DataFrame, path: Path) -> None:
    top = product_revenue.groupby("product_category", as_index=False)["gross_revenue"].sum().sort_values("gross_revenue", ascending=False)
    ax = top.plot(kind="bar", x="product_category", y="gross_revenue", legend=False, figsize=(10, 5), color="#4E79A7")
    ax.set_title("Paid Revenue by Product Category")
    ax.set_ylabel("Gross revenue")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_channel_funnel(channel_funnel: pd.DataFrame, path: Path) -> None:
    metrics = ["delivery_rate", "click_rate", "intent_rate", "paid_conversion_rate"]
    plot_df = channel_funnel.set_index("channel")[metrics].sort_values("paid_conversion_rate", ascending=False)
    ax = plot_df.plot(kind="bar", figsize=(11, 5), color=["#4E79A7", "#F28E2B", "#59A14F", "#E15759"])
    ax.set_title("Channel Touchpoint Funnel")
    ax.set_ylabel("Rate")
    ax.set_xlabel("")
    ax.set_ylim(0, max(0.85, float(plot_df.max().max()) + 0.08))
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_experiment(experiment: pd.DataFrame, stats: "ExperimentStats", path: Path) -> None:
    plot_df = experiment.set_index("variant")[["paid_order_30d_rate", "intent_14d_rate", "push_unsubscribe_rate"]]
    ax = plot_df.plot(kind="bar", figsize=(9, 5), color=["#2D9C7F", "#4E79A7", "#E15759"])
    ax.set_title("Incrementality Test by Variant")
    ax.set_ylabel("User rate")
    ax.set_xlabel("")
    ax.set_ylim(0, max(0.45, float(plot_df.max().max()) + 0.08))
    ax.grid(axis="y", alpha=0.25)
    lift_text = f"Paid conversion lift: {stats.absolute_lift:.1%}\np={stats.p_value:.4f}"
    ax.text(1.35, max(float(plot_df["paid_order_30d_rate"].max()) + 0.03, 0.06), lift_text, fontsize=10)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_attribution(attribution: pd.DataFrame, path: Path) -> None:
    pivot = attribution.pivot_table(index="channel", columns="attribution_model", values="attributed_revenue", aggfunc="sum").fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    ax = pivot.plot(kind="bar", figsize=(11, 5))
    ax.set_title("Revenue Credit by Attribution Model")
    ax.set_ylabel("Attributed revenue")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_operations(operations: pd.DataFrame, path: Path) -> None:
    selected = operations.loc[operations["domain"].isin(["call_center", "dealer_lead", "data_quality"])].copy()
    selected["label"] = selected["domain"] + ": " + selected["metric"] + " / " + selected["segment"].astype(str)
    selected = selected.sort_values("rate", ascending=True).head(12)
    ax = selected.plot(kind="barh", x="label", y="rate", legend=False, figsize=(10, 6), color="#F28E2B")
    ax.set_title("Operational SLA and Data Quality Checks")
    ax.set_xlabel("Pass / success rate")
    ax.set_ylabel("")
    ax.set_xlim(0, 1.05)
    ax.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
