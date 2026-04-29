# Connected Vehicle Growth Analytics

一个面向数据分析岗位面试展示的精品项目：用 100% 合成数据模拟 connected vehicle owner app 的生命周期增长、多产品商业化、多触点触达、增量实验、归因分析、续约/购买意向预测和运营质量诊断。

项目刻意使用泛化车联网语境，不包含任何真实公司、部门、内部系统、客户、车辆唯一标识、个人联系方式、截图、演示文稿内容或真实业务指标。

## 业务问题

- 首年车主从注册、激活、核心功能使用到付费/续约的漏斗是否健康？
- App、Push、短信、坐席联系、经销商线索等触点分别承担什么增长角色？
- 个性化多触点策略相比普通触达是否带来真实增量？
- 不同归因口径会如何改变渠道价值判断？
- 哪些用户值得进入高成本触达队列，哪些更适合低成本 App/Push 触达？
- 坐席触达、经销商 SLA、数据质量和过度触达是否会限制策略落地？

## 展示能力

- SQL：KPI tree、cohort 留存、收入结构、渠道漏斗、增量实验、归因、模型特征抽取、SLA/数据质量诊断
- Python：合成数据生成、SQLite 分析流水线、统计检验、Matplotlib 报告图表
- 实验分析：holdout/control/treatment 设计、付费转化 lift、置信区间、p-value、guardrail 指标
- 增长建模：scikit-learn 逻辑回归、ROC AUC、decile lift、高潜人群导出
- 业务表达：从指标体系到运营动作建议

## 如何运行

```bash
python3 -m pip install -r requirements.txt
python3 -m cv_growth run-all
```

运行检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/cv_growth_pycache python3 -m compileall .
python3 tests/smoke_test.py
```

常用命令：

```bash
python3 -m cv_growth generate --out data/synthetic
python3 -m cv_growth build-db --csv-dir data/synthetic --db output/analytics.sqlite
python3 -m cv_growth analyze --db output/analytics.sqlite --report reports/connected_vehicle_growth_case.md
python3 -m cv_growth train-model --db output/analytics.sqlite --out output/model_metrics.json
python3 -m cv_growth export-audience --db output/analytics.sqlite --out output/high_value_audience.csv
```

默认生成 3,000 个合成用户，便于快速复现。如果想做更大的本地演示，可以使用 `--users 10000`。

## 项目结构

```text
connected-vehicle-app-growth-analytics/
├── cv_growth/                 # Python package and CLI
├── sql/                       # 8 reusable SQL analysis queries
├── docs/                      # Metric framework and data dictionary
├── reports/                   # Generated report, model card, figures, tables
├── tests/                     # Smoke and data-quality checks
├── INTERVIEW_TALK_TRACK.md    # 3-minute and 8-minute interview narration
└── README.md
```

## 合成数据模型

- `users`, `vehicles`, `user_features`：车主画像、车辆属性、App/车辆行为特征
- `products`, `campaigns`, `content_items`：产品目录和增长活动配置
- `experiment_assignments`：holdout、普通 control、个性化 treatment 分组
- `touchpoints`, `events`：触达记录和行为日志
- `subscriptions`, `orders`：续约、购买、收入、毛利结果
- `call_center_contacts`, `dealer_leads`：线下执行和 SLA 数据
- `data_quality_checks`：报告中使用的合成数据治理检查

## 关键产物

- `reports/connected_vehicle_growth_case.md`：中文主报告
- `reports/propensity_model_card.md`：中文模型卡和业务 guardrail
- `reports/figures/`：生命周期、留存、收入、漏斗、实验、归因、运营图表
- `output/model_metrics.json`：模型指标
- `output/high_value_audience.csv`：高潜人群排序导出
- `docs/metric_framework.md`：指标定义和解释
- `docs/data_dictionary.md`：表结构和字段说明

## 隐私说明

- 所有数据都由固定随机种子的代码生成。
- 不包含真实公司名称、部门名称、内部系统名称、个人姓名、客户标识、车辆唯一标识、联系方式、截图、演示文稿内容或真实业务指标。
- `data/synthetic/` 和 `output/` 可重新生成，默认不作为核心源码提交。

## License

MIT License
