from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .config import SQL_DIR
from .database import read_sql


def train_propensity_model(db_path: Path, metrics_path: Path, model_card_path: Path) -> dict[str, float | int | str]:
    features = _load_model_features(db_path)
    prepared = _prepare_features(features)
    X_train, X_test, y_train, y_test = train_test_split(
        prepared["X"],
        prepared["y"],
        test_size=0.30,
        random_state=42,
        stratify=prepared["y"],
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X_train_scaled, y_train)
    test_scores = model.predict_proba(X_test_scaled)[:, 1]

    auc = float(roc_auc_score(y_test, test_scores))
    decile_metrics = _decile_metrics(y_test, test_scores)
    metrics: dict[str, float | int | str] = {
        "model_name": "owner_purchase_propensity_logistic_regression",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": int(len(features)),
        "feature_count": int(prepared["X"].shape[1]),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "target_rate": float(prepared["y"].mean()),
        "auc": auc,
        **decile_metrics,
    }

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_model_card(model_card_path, metrics)
    return metrics


def export_high_value_audience(db_path: Path, out_path: Path, top_n: int = 500) -> pd.DataFrame:
    features = _load_model_features(db_path)
    prepared = _prepare_features(features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(prepared["X"])
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X_scaled, prepared["y"])
    scores = model.predict_proba(X_scaled)[:, 1]

    scored = features.copy()
    scored["predicted_conversion_score"] = scores
    scored["recommended_product_id"] = scored.apply(_recommended_product, axis=1)
    scored["recommended_channel"] = scored.apply(_recommended_channel, axis=1)
    scored["reason_code"] = scored.apply(_reason_code, axis=1)
    export_cols = [
        "user_id",
        "predicted_conversion_score",
        "recommended_product_id",
        "recommended_channel",
        "reason_code",
        "lifecycle_stage",
        "vehicle_age_bucket",
        "energy_type",
        "renewal_due_days",
        "service_due_days",
        "product_affinity_score",
    ]
    audience = (
        scored.sort_values("predicted_conversion_score", ascending=False)
        .head(top_n)[export_cols]
        .reset_index(drop=True)
    )
    audience["predicted_conversion_score"] = audience["predicted_conversion_score"].round(4)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audience.to_csv(out_path, index=False)
    return audience


def _load_model_features(db_path: Path) -> pd.DataFrame:
    sql = (SQL_DIR / "07_model_features.sql").read_text(encoding="utf-8")
    return read_sql(db_path, sql)


def _prepare_features(features: pd.DataFrame) -> dict[str, pd.DataFrame | pd.Series]:
    frame = features.copy()
    y = frame.pop("converted_next_30d").astype(int)
    frame = frame.drop(columns=["user_id"])
    numeric_cols = frame.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [col for col in frame.columns if col not in numeric_cols]
    for col in numeric_cols:
        frame[col] = frame[col].fillna(frame[col].median())
    for col in categorical_cols:
        frame[col] = frame[col].fillna("unknown")
    X = pd.get_dummies(frame, columns=categorical_cols, drop_first=False)
    return {"X": X, "y": y}


def _decile_metrics(y_test: pd.Series, scores: np.ndarray) -> dict[str, float]:
    scored = pd.DataFrame({"target": y_test.to_numpy(), "score": scores}).sort_values("score", ascending=False)
    top_n = max(1, int(np.ceil(len(scored) * 0.10)))
    top_decile_rate = float(scored.head(top_n)["target"].mean())
    overall_rate = float(scored["target"].mean())
    bottom_decile_rate = float(scored.tail(top_n)["target"].mean())
    return {
        "overall_test_conversion_rate": overall_rate,
        "top_decile_conversion_rate": top_decile_rate,
        "bottom_decile_conversion_rate": bottom_decile_rate,
        "top_decile_lift": top_decile_rate / overall_rate if overall_rate else 0.0,
    }


def _write_model_card(model_card_path: Path, metrics: dict[str, float | int | str]) -> None:
    model_card_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 购买/续约意向模型卡",
        "",
        "## 模型用途",
        "",
        "该合成模型用于预测车主 App 用户未来 30 日付费转化倾向，并将用户按触达优先级排序。它适合用于增长运营分层，不用于自动资格判定或敏感决策。",
        "",
        "## 模型设计",
        "",
        "- 算法：带类别权重的逻辑回归。",
        "- 预测目标：用户在实验分组后 30 日内是否产生付费订单。",
        "- 输入特征：生命周期阶段、获客来源、车辆属性、功能使用、续约/服务到期时间、产品亲和度、触点次数和触达压力等。",
        "",
        "## 离线效果",
        "",
        f"- 样本行数：{metrics['rows']}",
        f"- one-hot 后特征数：{metrics['feature_count']}",
        f"- 目标转化率：{float(metrics['target_rate']):.1%}",
        f"- ROC AUC: {float(metrics['auc']):.3f}",
        f"- 测试集整体转化率：{float(metrics['overall_test_conversion_rate']):.1%}",
        f"- Top decile 转化率：{float(metrics['top_decile_conversion_rate']):.1%}",
        f"- Top decile lift：{float(metrics['top_decile_lift']):.2f}x",
        "",
        "## 业务使用方式",
        "",
        "先用模型分数给用户排序，再做渠道路由。低成本 App 卡片和 Push 可以覆盖较宽人群；坐席联系、经销商跟进等高成本触达，应优先给预期毛利能够覆盖触达成本的高分用户。",
        "",
        "## 限制与 Guardrail",
        "",
        "- 数据为合成数据，因此该模型是作品集演示，不是生产模型。",
        "- 意向分数不等于因果增量，仍需要结合 holdout 实验评估真实 lift。",
        "- 用户退订、触达频控和过度触达规则应优先于模型分数。",
        "- 项目不使用个人标识、真实公司数据、车辆唯一标识、联系方式或真实客户记录。",
        "",
    ]
    model_card_path.write_text("\n".join(lines), encoding="utf-8")


def _recommended_product(row: pd.Series) -> str:
    if row["renewal_due_days"] <= 60:
        return "P001"
    if row["service_due_days"] <= 45:
        return "P005"
    if row["energy_type"] in {"EV", "PHEV"}:
        return "P006"
    if int(row["has_advanced_driver_assist"]) == 1:
        return "P007"
    return "P008"


def _recommended_channel(row: pd.Series) -> str:
    score = float(row["predicted_conversion_score"])
    product_id = row["recommended_product_id"]
    if product_id == "P005":
        return "dealer_lead" if score >= 0.45 else "app_card"
    if product_id == "P001" and score >= 0.55:
        return "call_center"
    if score >= 0.40:
        return "push"
    return "app_card"


def _reason_code(row: pd.Series) -> str:
    if row["renewal_due_days"] <= 60:
        return "renewal_due_high_intent"
    if row["service_due_days"] <= 45:
        return "service_due_window"
    if row["energy_type"] in {"EV", "PHEV"}:
        return "energy_owner_cross_sell"
    if row["lifecycle_stage"] == "dormant":
        return "dormant_reactivation"
    return "high_affinity_general"
