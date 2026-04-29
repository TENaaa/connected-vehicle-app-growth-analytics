from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


TABLES = [
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
]


def build_database(csv_dir: Path, db_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    row_counts: dict[str, int] = {}
    with sqlite3.connect(db_path) as conn:
        for table in TABLES:
            csv_path = csv_dir / f"{table}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing required CSV: {csv_path}")
            df = pd.read_csv(csv_path)
            df.to_sql(table, conn, index=False, if_exists="replace")
            row_counts[table] = len(df)

        conn.executescript(
            """
            CREATE INDEX idx_events_user_time ON events(user_id, event_timestamp);
            CREATE INDEX idx_events_name ON events(event_name);
            CREATE INDEX idx_events_touchpoint ON events(touchpoint_id);
            CREATE INDEX idx_assignments_user ON experiment_assignments(user_id);
            CREATE INDEX idx_touchpoints_user_time ON touchpoints(user_id, touchpoint_time);
            CREATE INDEX idx_touchpoints_campaign ON touchpoints(campaign_id);
            CREATE INDEX idx_orders_user ON orders(user_id);
            CREATE INDEX idx_orders_touchpoint ON orders(attributed_touchpoint_id);
            CREATE INDEX idx_call_center_touchpoint ON call_center_contacts(touchpoint_id);
            CREATE INDEX idx_dealer_leads_touchpoint ON dealer_leads(touchpoint_id);
            """
        )

    return row_counts


def read_sql(db_path: Path, sql: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(sql, conn)
