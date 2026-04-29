from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
DEFAULT_CSV_DIR = PROJECT_ROOT / "data" / "synthetic"
DEFAULT_DB_PATH = PROJECT_ROOT / "output" / "analytics.sqlite"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "connected_vehicle_growth_case.md"
DEFAULT_FIGURE_DIR = PROJECT_ROOT / "reports" / "figures"
DEFAULT_MODEL_METRICS_PATH = PROJECT_ROOT / "output" / "model_metrics.json"
DEFAULT_MODEL_CARD_PATH = PROJECT_ROOT / "reports" / "propensity_model_card.md"
DEFAULT_AUDIENCE_PATH = PROJECT_ROOT / "output" / "high_value_audience.csv"
