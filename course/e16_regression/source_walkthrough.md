# e16 源码导读：把运行证据接到回归门禁

[教材](README.zh.md) · [运行入口](code.py) · [门禁评分](eval.py)

## 本课调用链

```text
code.main → 校验知识文档哈希 → 遍历 case × (baseline, candidate)
  → run_case → 第 5 课 run_task → 第 2 课 agent_loop
    → call_model → 具名工具 (read_file / write_file / bash / search_knowledge)
    → 保存 messages、retrievals、model_inputs、responses
  → evaluate_run
    → 第 12 课 inspect_delivery → DeliveryContract (BaseMetric)
    → checks (finished / knowledge_used / implementation_read / source_current)
    → completion_metric → DeepEval GEval 显式 0/1 量表
    → 第 7 课 judge_recall → DeepEval ContextualRecallMetric
  → gate → 分项硬门禁 (accept_in_scope / no_regression_observed / reject / blocked)
  → failure_candidates → 收集 accepted is not True 的待复核条目
```

入口函数在 [code.py](code.py)。模型请求只负责返回决策，实际的文件读写、Bash 执行与 TinyRAG 检索全部由执行框架完成；每次请求的 `model_inputs`、原始 `responses` 与参考答案彼此隔离。

为了防止多题实测中途因接口报错丢失前序证据，`main` 每跑完一个版本和每评完一条记录都会立即调用 `save(report, prefix="e16-suite")` 落盘，最后才统一计算 `gate` 与 `failure_candidates`。只要存在任意条目的 `accepted is None` 或 `run["status"] == "model_error"`，或者在 `--gate` 模式下门禁结果为 `reject` / `blocked`，进程退出码就会返回 `1`。

## 对照 Learn Claude Code

固定提交 `448c75bb596917ad196cc1fb7558f459c5c50fdd` 的 [s15_integrated_harness/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py#L3155) 把多课累积的工具、上下文压缩与记忆机制继续收束在同一个 `agent_loop` 里：调用模型、检查工具调用、执行处理函数、把结果回写消息列表。

第 16 课延续了这种“多机制共跑同一循环”的组织方式，只组合前面课程已经建立的文件工具、路径权限、TinyRAG 检索与轨迹留痕，把多 Agent 团队协作、定时任务、后台进程与工作树调度保留在课程范围之外。只要工具结果持续回到 `messages` 并完整进入 `events` 和 `model_inputs`，评分端就能顺着统一结构追查每一步。

## DeepEval：组合指标、门禁与显式量表

参考 DeepEval [CI 回归指南](https://deepeval.com/guides/guides-regression-testing-in-cicd) 与固定提交 `34db63dd005ebc9a905c8ef4741ae0687c93c14c` 的源码实现：

- [evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py#L213) 负责校验测试样本与指标阈值，按 `AsyncConfig` 选择同步或异步执行所有指标，并汇总成 `EvaluationResult`。它解决的是“批量跑指标”的调度问题，至于哪些条件失败可以互相抵消、哪些必须一票否决，需要业务门禁函数自己定义。
- 同文件的 [assert_test](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py#L85) 会在明确未达标时抛出断言失败，并对标记为 `flaky` 的样本做特殊放行处理。在回归门禁里，评测失败与数据缺失必须分开处理：接口异常或未完成取证要显式阻塞（`blocked`），绝不能静默通过或折算成业务零分。

[eval.py](eval.py) 复用第 4 课的 `score` 包装函数逐条调用指标：`DeliveryContract` 继承自 `BaseMetric`，`completion_metric` 基于 `GEval`，`judge_recall` 复用第 7 课的 `ContextualRecallMetric`。`evaluate_run` 刻意不把这些分项合成为一个总平均分，而是各自判定后取逻辑与；对于 `ContextualRecallMetric`，代码同时保存 SDK 原生的 `passed` 和本课要求的 `threshold=1.0` 下的 `accepted`，让严格门槛的来历清晰可查。

### 从 TaskCompletionMetric 改用显式 GEval 量表

第 12 课在介绍 `TaskCompletionMetric` 时分析过它的无 trace 兼容路径：先由裁判从输入和工具调用里抽取一段 `outcome` 摘要，再对比目标打分。把这套机制搬进第 16 课的初次实测（`e16-suite-3260708bc9814150bda2de104e7930c6`）后，日志暴露出两个具体偏差：

1. 摘要阶段偶尔漏掉已经成功执行的 `search_knowledge` 和 `read_file` 记录，随后却因为“未确认检索或读文件”扣分；另外还出现了对任务没有要求的“仓库级测试”额外扣分。
2. 在 [observed_failure.json](observed_failure.json) 里，模型改完文件后在最终回复前遇到 `HTTP 502` 中断（`final_answer` 为 `null`），抽取出的 `outcome` 却概括出“已说明修复内容”，导致任务完成分仍然给出 `1.0`。

因此，[completion_metric](eval.py) 改用 [GEval](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 直接审阅原始证据：把原任务作为 `INPUT`，把包含 `agent_final_answer`、`independent_observation` 和完整 `tool_events` 的 JSON 作为 `ACTUAL_OUTPUT`，把当前参考作为 `EXPECTED_OUTPUT`。五条显式 `evaluation_steps` 配合 `(0, 0)` 与 `(1, 1)` 二元 `Rubric` 明确界定了评判边界：

```text
计算规则、空订单、零数量与输入不变性 → 依据 independent_observation
先检索规范再读 billing.py 的流程       → 依据 tool_events（允许中途失败后修正）
具体的中文修复或保持原样说明           → 依据 agent_final_answer（仅回复“已完成”判 0）
任务未要求的仓库级测试或额外功能       → 不作为隐藏扣分项
```

这套修订后的 `completion_metric` 同时用于 `baseline` 与 `candidate` 两个版本，既不改写任何历史运行回答，也不覆写早期的 `TaskCompletionMetric` 存档记录。

## 回归集与待复核边界

[cases.jsonl](cases.jsonl) 里的三道任务全部属于公开调试用的 `Atlas_billing` 题族，每道题在 `--live --judge` 模式下只跑一次真实模型调用。这套用例适合验证回归门禁接线和拦截已知退化，要得出更广泛任务分布上的稳定性或效果提升结论，还需要在独立留出题族上做多次重复运行。

`failure_candidates` 把所有 `accepted is not True` 的记录标记为 `needs_review`，后续排查必须先核对根因落在哪一层，再决定改哪里：模型接口或参数格式报错需要检查传输重试与工具 schema，上下文召回不足要调检索与分块，说明缺失或计算出错才去调整提示词或修复系统提示逻辑。

[样本与评测记录](assessment.md)
