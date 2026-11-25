# e09 样本与评测记录

[教材](README.zh.md) · [样本](cases.jsonl) · [完整记录](assessment.json)

## 资料与样本

本课固定一条 Atlas 补丁发布问题，参考标准分为 `command`、`gate`、`fix` 三个必答单元。其中 `command` 将运行目录与命令合并为一个单元，命令写错即使目录正确也记为未覆盖；更改事实拆分粒度需要同步调整标注。

[cases.jsonl](cases.jsonl) 中的六组对照答案由课程构造，并附有教学用的事实 ID 标注。前四组携带 `atlas/release.md` 和 `atlas/logs.md` 两份上下文，后两组只携带 `atlas/logs.md`，用来分别观察无依据猜答与合理拒答。文档内容均在加载时校验 SHA-256。

## Docker 中的事实计算

离线集合计算运行编号为 `7c7b58577c2a4feaae88ef3cc6a7424d`，在 Docker 中执行，无裁判模型请求：

| 条件 | TP | FP | FN | 精确率 | 召回率 | F1 |
|---|---:|---:|---:|---:|---:|---:|
| `off_topic` | 0 | 1 | 3 | 0 | 0 | 0 |
| `on_topic_wrong` | 0 | 2 | 3 | 0 | 0 | 0 |
| `incomplete` | 1 | 0 | 2 | 1 | 1/3 | 1/2 |
| `complete` | 3 | 0 | 0 | 1 | 1 | 1 |
| `unsupported_answer` | 3 | 0 | 0 | 1 | 1 | 1 |
| `reasonable_refusal` | 0 | 0 | 3 | 未定义 | 0 | 0 |

`off_topic` 给出的审计日志天数符合知识库原文，但不在本题参考集合内，因此计为 1 个 `fp`。`reasonable_refusal` 没有说出发布事实，在集合指标上精确率未定义、F1 为 `0`，但它在证据策略维度上属于正确行为。

## DeepEval 原生评分

有效原生评测运行编号为 `ec1898e29726435b8d15a120d507507f`，共发出 21 次实际裁判请求：7 个条件各有 2 次 `AnswerRelevancyMetric` 请求（抽陈述、判裁决）和 1 次 `GEval` 请求。`task_metric` 依据 0 到 2 三档 `Rubric` 打分并由 SDK 归一化到 `0` 到 `1`。

| 条件 | `AnswerRelevancyMetric` | `GEval` 任务质量 | 理由中的关键依据 |
|---|---:|---:|---|
| `off_topic` | 0 | 0 | 只谈日志期限，未答发布要求 |
| `on_topic_wrong` | 1 | 0 | 切题，但命令和失败后发布规则违背资料 |
| `incomplete` | 1 | 0.5 | 命令正确，遗漏发布门槛与失败处理 |
| `complete` | 1 | 1 | 三项要求正确且有资料依据 |
| `unsupported_answer` | 1 | 0 | 只收到日志资料，却自信给出全部发布事实 |
| `reasonable_refusal` | 1 | 1 | 明确资料不足并请求发布规范，没有猜测 |
| `live_agent` | 1 | 1 | 真实检索后完整回答，遵守不执行要求 |

`reasonable_refusal` 在 `AnswerRelevancyMetric` 中抽出三条陈述且全部判为 `borderline`，SDK 默认将 `borderline` 计入通过项，因而得分为 `1`。阅读这一结果时要对照原始 `statements`、`verdicts` 和 `GEval` 理由，区分“合理澄清获得相关性默认通过”与“直接给出发布规范”。

## 真实 Agent 运行

`live_agent` 复用第 5 课 `run_task`（`k=3`、`context_limit=2`），实际完成 2 轮模型输入与 1 次 `search_knowledge` 调用，最终选中 `atlas/release.md` 和 `atlas/logs.md` 两个片段，参考版本为 `current`，运行状态为 `finished`，且没有执行 Bash、测试或发布命令。

模型最终回答原文如下：

> 在 Atlas 项目根目录运行 `python -m pytest -q`。只有全部检查通过后才能提交发布；如果检查失败，应先修复失败项并重新检查，不得跳过。按要求，此处未执行测试或发布。

新生成的回答没有预设事实 ID，只由原生 `AnswerRelevancyMetric`（6 条陈述全部判为 `yes`）与 `task_metric`（得 `1`）评分，完整对话历史、检索记录与实际 `retrieval_context` 保存在记录中。

## 首次失败记录与软件检查

首次运行因 `LLMTestCase.model_validate` 拒绝 `live_agent` 样本中已序列化的 `tools_called` 字典而报错中断，完整报错日志保留在 `assessment.json` 的 `failed_attempt` 字段中。修复后，[code.py](code.py) 在构造送评样本时只提取 `input`、`actual_output`、`expected_output` 和 `retrieval_context` 四个字段，完整 `tools_called` 轨迹继续留在 `conditions["live_agent"]["sample"]` 内，并在每次模型调用后增量存盘。

配套单元测试核对了以下行为：`fact_scores` 在 TP/FP/FN 计算、精确率与召回率分母区分、`beta` 权重调节、集合去重、空集返回 `None` 以及非正 `beta` 抛错上的表现；`judge_relevance` 在切题但命令错误时仍得 `1` 且空陈述返回 `not_applicable`；`task_metric` 正确配置四个输入字段与 `threshold=1.0`；以及 `--live --judge` 路径在保留 `tools_called` 的前提下完成四字段送评。

本课评估基于六个教学构造条件与一次真实 Agent 运行，具体业务接入时仍需结合行业文档重新校准参考事实拆分粒度与阈值。
