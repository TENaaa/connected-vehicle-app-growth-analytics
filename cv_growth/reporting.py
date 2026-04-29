from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .analysis import ExperimentStats


def pct(value: float) -> str:
    return f"{value:.1%}"


def pp(value: float) -> str:
    return f"{value * 100:.2f} pp"


def money(value: float) -> str:
    return f"{value:,.0f}"


COLUMN_LABELS = {
    "stage": "阶段",
    "users": "用户数",
    "rate_of_registered": "占注册用户比例",
    "step_conversion_rate": "环节转化率",
    "cohort_month": "注册月份",
    "activity_window": "活跃窗口",
    "cohort_users": "同期用户数",
    "active_users": "活跃用户数",
    "retention_rate": "留存率",
    "indexed_to_w1": "相对首周指数",
    "product_category": "产品类别",
    "product_name": "产品名称",
    "order_channel": "订单渠道",
    "orders": "订单数",
    "buyers": "购买用户数",
    "gross_revenue": "收入",
    "direct_cost": "直接成本",
    "gross_margin": "毛利",
    "margin_rate": "毛利率",
    "avg_order_value": "客单价",
    "channel": "触达渠道",
    "touchpoints": "触点数",
    "touched_users": "触达用户数",
    "delivered_users": "送达用户数",
    "clicked_users": "点击用户数",
    "intent_users": "意向用户数",
    "paid_buyers": "付费用户数",
    "delivery_rate": "送达率",
    "click_rate": "点击率",
    "intent_rate": "意向率",
    "paid_conversion_rate": "付费转化率",
    "touchpoint_cost": "触达成本",
    "roi": "ROI",
    "variant": "实验组",
    "assigned_users": "分配用户数",
    "reached_users": "触达用户数",
    "reach_rate": "触达率",
    "intent_14d_users": "14日意向用户数",
    "intent_14d_rate": "14日意向率",
    "paid_order_30d_users": "30日付费用户数",
    "paid_order_30d_rate": "30日付费率",
    "revenue_30d": "30日收入",
    "revenue_per_assigned_user": "人均30日收入",
    "auto_renew_users": "自动续约用户数",
    "auto_renew_rate": "自动续约率",
    "push_unsubscribed_users": "退订用户数",
    "push_unsubscribe_rate": "退订率",
    "attribution_model": "归因模型",
    "attributed_revenue": "归因收入",
    "attributed_orders": "归因订单",
    "avg_revenue_credit": "平均收入贡献",
    "domain": "运营域",
    "metric": "指标",
    "segment": "分组",
    "numerator": "分子",
    "denominator": "分母",
    "rate": "达成率",
    "value": "数值",
}


def write_report(
    report_path: Path,
    tables: dict[str, pd.DataFrame],
    experiment_stats: "ExperimentStats",
    north_star_rate: float,
    figure_paths: dict[str, Path],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lifecycle = tables["lifecycle"]
    retention = tables["retention"]
    product_revenue = tables["product_revenue"]
    channel_funnel = tables["channel_funnel"]
    experiment = tables["experiment"]
    attribution = tables["attribution"]
    operations = tables["operations"]

    paid_stage = lifecycle.loc[lifecycle["stage"] == "07_paid_order"].iloc[0]
    top_product = product_revenue.groupby("product_category", as_index=False)["gross_revenue"].sum().sort_values("gross_revenue", ascending=False).iloc[0]
    top_channel = channel_funnel.sort_values("gross_revenue", ascending=False).iloc[0]
    latest_retention = retention.groupby("activity_window")["retention_rate"].mean().to_dict()
    data_quality = operations.loc[operations["domain"] == "data_quality"].copy()
    quality_warns = int((data_quality["segment"] != "pass").sum())

    lines = [
        "# 车联网车主 App 增长分析案例报告",
        "",
        "## 核心结论",
        "",
        "这是一个完全基于合成数据的车联网车主 App 增长分析项目，模拟车主生命周期激活、多产品商业化、多触点触达、增量实验、归因分析、意向模型输入和运营质量诊断。",
        "",
        f"- 北极星指标，30 日服务活跃率：**{pct(north_star_rate)}**。",
        f"- 严格生命周期付费漏斗完成率：**{pct(float(paid_stage['rate_of_registered']))}**。",
        f"- 付费收入最高的产品类别：**{top_product['product_category']}**，合成收入 **{money(float(top_product['gross_revenue']))}**。",
        f"- 收入最高的触达渠道：**{top_channel['channel']}**，ROI **{float(top_channel['roi']):.2f}**。",
        f"- 增量实验 30 日付费转化率：control **{pct(experiment_stats.control_rate)}**，treatment **{pct(experiment_stats.treatment_rate)}**。",
        f"- 绝对提升：**{pp(experiment_stats.absolute_lift)}**；相对提升：**{pct(experiment_stats.relative_lift)}**；p-value **{experiment_stats.p_value:.4f}**。",
        f"- 数据质量检查 warning 数：**{quality_warns}**。",
        "",
        "## 指标体系",
        "",
        "| 层级 | 指标 | 业务用途 |",
        "| --- | --- | --- |",
        "| 生命周期 | D7 登录、D30 核心功能、活动触达、意向、付费订单 | 判断车主旅程在哪个环节流失。 |",
        "| 商业化 | 收入、毛利、客单价、渠道 ROI | 将增长动作和经营结果连接起来。 |",
        "| 实验 | holdout/control/treatment 转化与 guardrail | 区分真实增量和自然需求。 |",
        "| 归因 | 首触、末触、线性、位置归因 | 解释不同归因规则下渠道排序如何变化。 |",
        "| 运营 | 坐席触达、经销商 SLA、数据质量、过度触达 | 保证策略能被运营团队稳定执行。 |",
        "",
        "## 生命周期 KPI Tree",
        "",
        f"![生命周期 KPI tree]({figure_paths['lifecycle'].relative_to(report_path.parent).as_posix()})",
        "",
        _markdown_table(
            lifecycle,
            rate_cols=["rate_of_registered", "step_conversion_rate"],
        ),
        "",
        "## 功能留存",
        "",
        f"![功能留存]({figure_paths['retention'].relative_to(report_path.parent).as_posix()})",
        "",
        "各活跃窗口平均留存率：",
        "",
    ]
    for window, rate in sorted(latest_retention.items()):
        lines.append(f"- {window}: {pct(float(rate))}")

    lines.extend(
        [
            "",
            "## 多产品收入结构",
            "",
            f"![多产品收入结构]({figure_paths['product_revenue'].relative_to(report_path.parent).as_posix()})",
            "",
            _markdown_table(
                product_revenue.head(10),
                rate_cols=["margin_rate"],
                money_cols=["gross_revenue", "direct_cost", "gross_margin", "avg_order_value"],
            ),
            "",
            "## 渠道触点漏斗",
            "",
            f"![渠道触点漏斗]({figure_paths['channel_funnel'].relative_to(report_path.parent).as_posix()})",
            "",
            _markdown_table(
                channel_funnel,
                rate_cols=["delivery_rate", "click_rate", "intent_rate", "paid_conversion_rate"],
                money_cols=["touchpoint_cost", "gross_revenue"],
            ),
            "",
            "## 增量实验评估",
            "",
            f"![增量实验评估]({figure_paths['experiment'].relative_to(report_path.parent).as_posix()})",
            "",
            _markdown_table(
                experiment,
                rate_cols=["reach_rate", "intent_14d_rate", "paid_order_30d_rate", "auto_renew_rate", "push_unsubscribe_rate"],
                money_cols=["revenue_30d", "revenue_per_assigned_user"],
            ),
            "",
            f"解读：在这个合成场景中，个性化多触点策略相对普通触达策略带来 **{pp(experiment_stats.absolute_lift)}** 的 30 日付费转化绝对提升。表中保留 holdout 组，用来观察自然需求基线。",
            "",
            "## 归因口径敏感性",
            "",
            f"![归因口径敏感性]({figure_paths['attribution'].relative_to(report_path.parent).as_posix()})",
            "",
            _markdown_table(
                attribution.sort_values(["attribution_model", "attributed_revenue"], ascending=[True, False]).head(16),
                money_cols=["attributed_revenue", "avg_revenue_credit"],
            ),
            "",
            "## 运营执行与数据质量",
            "",
            f"![运营执行与数据质量]({figure_paths['operations'].relative_to(report_path.parent).as_posix()})",
            "",
            _markdown_table(
                operations.head(16),
                rate_cols=["rate"],
            ),
            "",
            "## 行动建议",
            "",
            "1. 对续约临期和服务到期人群保留个性化多触点策略，同时持续保留 holdout 组做增量测量。",
            "2. 按渠道角色拆分运营动作：App 卡片适合低成本教育，坐席适合高价值续约收口，经销商线索重点看 SLA。",
            "3. 将归因作为预算讨论的敏感性分析，而不是唯一事实；真正判断策略有效性仍要依赖 holdout 实验。",
            "4. 将意向模型输出为排序人群包，只在预期毛利覆盖触达成本时，把 top decile 用户路由到高成本渠道。",
            "5. 每周增长复盘中同时检查数据质量和过度触达，避免短期转化提升损害长期车主体验。",
            "",
            "## 隐私与脱敏说明",
            "",
            "所有数据和结论均由代码生成。项目不包含真实公司名称、部门名称、内部系统、个人姓名、客户标识、车辆唯一标识、联系方式、截图、演示文稿内容或真实业务指标。",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_table(
    df: pd.DataFrame,
    rate_cols: list[str] | None = None,
    money_cols: list[str] | None = None,
) -> str:
    rate_cols = rate_cols or []
    money_cols = money_cols or []
    display = df.copy()
    for col in rate_cols:
        if col in display.columns:
            display[col] = display[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.1%}")
    for col in money_cols:
        if col in display.columns:
            display[col] = display[col].map(lambda value: "" if pd.isna(value) else f"{float(value):,.2f}")
    display = display.rename(columns=COLUMN_LABELS)
    display = display.fillna("")
    headers = [str(col) for col in display.columns]
    rows = [[str(value) for value in row] for row in display.to_numpy()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)
