from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import run_analysis
from .config import (
    DEFAULT_AUDIENCE_PATH,
    DEFAULT_CSV_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_FIGURE_DIR,
    DEFAULT_MODEL_CARD_PATH,
    DEFAULT_MODEL_METRICS_PATH,
    DEFAULT_REPORT_PATH,
)
from .data_generation import generate_synthetic_data
from .database import build_database
from .modeling import export_high_value_audience, train_propensity_model


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Connected vehicle owner app growth analytics CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate synthetic CSV data")
    generate.add_argument("--out", type=Path, default=DEFAULT_CSV_DIR)
    generate.add_argument("--users", type=int, default=3000)
    generate.add_argument("--seed", type=int, default=42)

    build = subparsers.add_parser("build-db", help="Build SQLite database from generated CSVs")
    build.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    build.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)

    analyze = subparsers.add_parser("analyze", help="Run SQL/Python analysis and write report")
    analyze.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    analyze.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    analyze.add_argument("--figures", type=Path, default=DEFAULT_FIGURE_DIR)

    train_model = subparsers.add_parser("train-model", help="Train propensity model and write metrics/model card")
    train_model.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    train_model.add_argument("--out", type=Path, default=DEFAULT_MODEL_METRICS_PATH)
    train_model.add_argument("--model-card", type=Path, default=DEFAULT_MODEL_CARD_PATH)

    export_audience = subparsers.add_parser("export-audience", help="Export ranked high-value audience")
    export_audience.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    export_audience.add_argument("--out", type=Path, default=DEFAULT_AUDIENCE_PATH)
    export_audience.add_argument("--top-n", type=int, default=500)

    run_all = subparsers.add_parser("run-all", help="Generate data, build SQLite DB, and write report")
    run_all.add_argument("--users", type=int, default=3000)
    run_all.add_argument("--seed", type=int, default=42)
    run_all.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    run_all.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    run_all.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    run_all.add_argument("--figures", type=Path, default=DEFAULT_FIGURE_DIR)
    run_all.add_argument("--model-metrics", type=Path, default=DEFAULT_MODEL_METRICS_PATH)
    run_all.add_argument("--model-card", type=Path, default=DEFAULT_MODEL_CARD_PATH)
    run_all.add_argument("--audience", type=Path, default=DEFAULT_AUDIENCE_PATH)

    args = parser.parse_args(argv)

    if args.command == "generate":
        result = generate_synthetic_data(args.out, n_users=args.users, seed=args.seed)
        print(f"Generated synthetic data in {result.output_dir}")
        print(result.row_counts)
    elif args.command == "build-db":
        row_counts = build_database(args.csv_dir, args.db)
        print(f"Built SQLite database at {args.db}")
        print(row_counts)
    elif args.command == "analyze":
        run_analysis(args.db, args.report, args.figures)
        print(f"Wrote report to {args.report}")
    elif args.command == "train-model":
        metrics = train_propensity_model(args.db, args.out, args.model_card)
        print(f"Wrote model metrics to {args.out}")
        print(f"Wrote model card to {args.model_card}")
        print(metrics)
    elif args.command == "export-audience":
        audience = export_high_value_audience(args.db, args.out, top_n=args.top_n)
        print(f"Wrote {len(audience)} high-value audience rows to {args.out}")
    elif args.command == "run-all":
        result = generate_synthetic_data(args.csv_dir, n_users=args.users, seed=args.seed)
        row_counts = build_database(args.csv_dir, args.db)
        run_analysis(args.db, args.report, args.figures)
        train_propensity_model(args.db, args.model_metrics, args.model_card)
        audience = export_high_value_audience(args.db, args.audience)
        print(f"Generated synthetic data in {result.output_dir}")
        print(f"Built SQLite database at {args.db}")
        print(f"Wrote report to {args.report}")
        print(f"Wrote model metrics to {args.model_metrics}")
        print(f"Wrote model card to {args.model_card}")
        print(f"Wrote {len(audience)} high-value audience rows to {args.audience}")
        print(row_counts)


if __name__ == "__main__":
    main()
