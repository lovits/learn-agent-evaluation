# e16 样本与评测记录

[教材](README.zh.md) · [回归任务](cases.jsonl) · [历史来源](failure_origin.json) · [中断样本](observed_failure.json) · [完整记录](assessment.json)

## 样本与来源设计

[cases.jsonl](cases.jsonl) 包含三道属于 `Atlas_billing` 题族的公开回归任务：`quantity`（漏乘数量）、`empty`（空订单错误返回 `100`）和 `preserve`（已有正确实现需保持不变）。三道题绑定同一份知识库文档 `e16/billing.md`（SHA-256 `b8fdbde40d18e5ec8aece46df984a747c75c09f155e62c4a0bb5b11064cf48b4`），各自在全新的隔离工作区里从相同的初始文件启动，候选版本仅在任务尾部追加一段 `REPAIR` 说明要求。

[failure_origin.json](failure_origin.json) 存档了第 12 课记录 `6e25dfe26d9a487b9d715c34c89cc80e` 里的 `native_supplement.conditions.correct`：该条由受控决策驱动并实际修改了文件，独立契约 `DeliveryContract` 得 `1.0`，而 `TaskCompletionMetric` 因最终回答只有“已完成。”给出 `0.95`（`passed: false`）。本课三道回归任务正是围绕这一说明缺口与知识库查询要求派生的。

[observed_failure.json](observed_failure.json) 来自本课初次真实模型运行（`3260708bc9814150bda2de104e7930c6`）中的 `empty` 候选条目：模型查过规范并把 `billing.py` 的空订单分支改回 `0`，在返回最终答复前遇到 `HTTP Error 502: Bad Gateway`，导致 `status` 为 `model_error`、`final_answer` 为 `null`。但旧版 `TaskCompletionMetric` 抽取的 `outcome` 摘要仍写出了“已说明修复内容”并给了 `1.0` 分。依靠 `checks["finished"]` 与可用性门禁，`evaluate_run` 将其 `accepted` 保持为 `None`（`diagnosis: "observation_or_scoring_unavailable"`），使当轮 `gate` 正确返回 `blocked`。

## 评分口径演进

初次组合实验使用 `TaskCompletionMetric`（运行 `3260708bc9814150bda2de104e7930c6`，共 18 次裁判请求）。逐条复核理由时发现三项问题：部分条目在摘要阶段丢失了实际执行过的工具事件，另有完整实现因为没有跑任务未要求的仓库级测试而被扣分，同时出现了上述 `HTTP 502` 中断。这些原始分数与轨迹全部完整保留。

随后的评测改用 [eval.py](eval.py) 里的显式 `GEval` 量表 `completion_metric`，直接把 `agent_final_answer`、`independent_observation` 和 `tool_events` 一起送入裁判，并统一应用到基线与候选两个版本。所有历史运行回答与早期实验记录都保持原样。

## Docker 实验结果汇总

| 实验轮次 | 运行编号 | 模式 | 主要结果 | 门禁结论 |
|---|---|---|---|---|
| 默认离线门禁 | `07537c6f1c304d9ab1c17d6663805665` | 真实工具执行与构造语义分 | 6 条独立契约全为 `1.0`；基线说明分 `0.5` 未通过，候选 `1.0` 全通过 | `accept_in_scope`（仅验证接线与构造口径） |
| 受控动作与原生裁判 | `a91a38b54aa4402f89be732e17ad2f39` | 受控决策与 12 次原生 DeepEval 请求 | 3 条仅回复“已完成。”的基线 `completion` 均为 `0.0`，3 条完整候选均为 `1.0`；`context_recall` 全为 `1.0` | `accept_in_scope` |
| 真实模型与显式量表 | `d37560ca7f9d43278532d18f39271d6f` | `--live --judge`（12 次裁判请求） | 基线 `3/3` 完成并通过；候选 `preserve` 通过，`quantity` 与 `empty` 各调 2 轮后触发 `model_error` | `blocked` |
| 失败行独立恢复 | `8e06545de6374f6c8de763a6e0624c7d` | 新工作区仅重跑 2 条中断候选（新增 4 次裁判请求） | 两条候选再次因工具参数格式无效触发 `model_error`，`accepted` 仍保持 `None` | `blocked` |

在真实模型主轮 `d37560ca7f9d43278532d18f39271d6f` 中，基线完成 13 次桥接调用并全部成功返回（`quantity` 4 次、`empty` 6 次、`preserve` 3 次）；候选发起 10 次调用并收到 8 次有效响应（共 23 次尝试、21 次有效响应）。由于桥接层未返回固定模型快照与计费单价，`usd` 字段保持为 `null`。另外，`empty` 基线在执行中途遇到过两次 Bash 测试报错，模型观察错误后修正了代码，最终独立行为与语义判据均判为通过。

由于候选版本在真实模型与恢复运行中仍存在未解决的接口与参数格式故障，本次对 `REPAIR` 提示词的改动没有通过门禁，记录如实停留在 `blocked` 状态。

## 软件与图件核验

仓库单元测试中与本课相关及全库检查共通过 52 项（`software_checks: 52`；开发过程中曾修复一处测试索引层级错误后重跑，未改动任何实验结果）；本地阅读器内两张 SVG 流程图均通过尺寸（`706x571`、`701x701`）及便携文本规范核验。完整原始记录与逐条裁决存储在 [assessment.json](assessment.json) 中。
