# 第16课源码导读：把证据接到判断上

## 一条完整调用链

```text
code.main → 检查样本来源 → 每题 baseline / candidate
  → run_case → 第5课 run_task → 第2课 agent_loop
    → call_model → 具名工具 → 实际文件 / TinyRAG / Bash
    → messages、retrievals、model_inputs、responses
  → evaluate_run
    → 第12课 inspect_delivery → DeliveryContract
    → 轨迹中的查询、读取与来源检查
    → completion_metric → DeepEval G-Eval 显式0/1裁决
    → 第7课 judge_recall → DeepEval ContextualRecallMetric
  → gate → 分项关键条件 → 接受 / 拒绝 / 未决
  → failure_candidates → 待人工复核，不自动入参考集
```

完整运行入口是 [code.py](code.py)。模型请求仍只提出动作，课程 Harness 才执行动作；真实输入与响应保留，参考分和独立检查不会注入被测模型。

## Learn Claude Code：组合已有机制

固定版本 `448c75bb596917ad196cc1fb7558f459c5c50fdd` 的 [s15 agent_loop](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py#L3155) 仍沿调用模型、判断工具、执行 handler、追加结果的结构。任务、上下文与其他机制进入同一循环。

本课保留这条教学思路，只组合前面已出现的文件工具、知识库、轨迹和评分。没有复制上游团队、cron、后台任务或工作树管理。工具结果是否返回消息，比工具列表有多长更能解释这里的执行过程。

## DeepEval：执行评分与决定是否接受要分开

[CI 回归指南](https://deepeval.com/guides/guides-regression-testing-in-cicd) 将固定用例和明确阈值接入持续检查。本课将可离线核对的行为检查与需要模型的语义复核分开，不把语义 fixture 的绿灯写成模型质量结论。

固定版本 `34db63dd005ebc9a905c8ef4741ae0687c93c14c`：

- [evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py#L213) 先校验输入、指标阈值，再按 AsyncConfig 选择同步或异步执行，返回 EvaluationResult。它能组织指标，不会替业务定义哪些失败可以被平均抵消。
- 同文件的 [assert_test](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py#L85) 检查结果并在明确失败时抛出断言；flaky 标记有特殊处理。不能把缺失裁决自动视为业务通过。
- 本课复用已实现的逐条 measure 包装，DeliveryContract 是 BaseMetric，两个语义指标来自同一个 DeepEval。没有新增 Ragas 评分路径，也没有为展示 evaluate 再跑一次相同任务。

[evaluate_run](eval.py) 的接受条件没有总平均分：行为、运行过程、业务完成、证据覆盖分别满足明确条件。ContextualRecall 的 SDK passed 可能基于默认阈值，本课额外保存 threshold=1 与 accepted，保留原始 passed，避免覆盖 SDK 判断。

### 为什么保留早期 TaskCompletion，再改成显式量表

第12课已说明固定版本的无 tracing 兼容路径会提取 outcome 再评分。综合任务多了检索流程，outcome 若只保留业务结果，就可能遗漏原始工具证据；另有完整回答因未运行任务没有要求的仓库级检查被扣分。

这些原始评分留在独立评测记录。当前 [completion_metric](eval.py) 复用已经讲过的 [GEval](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)：原任务作为 INPUT，原始回答、独立观察与 tool_events 一起作为 ACTUAL_OUTPUT，当前参考作为 EXPECTED_OUTPUT。量表显式列出全部要求，用0/1裁决。

```text
正确计算与输入不变性 → 看独立观察
查询与读文件过程 → 看真实事件
必要的修复说明 → 看原始最终回答
没有要求的仓库级检查 → 不增加成隐藏条件
```

量表修正同时应用到两个版本，另做受控反例核对，不偷偷改原始回答或旧分。若两侧都通过，结论是修正了评分接线、当前未观察到版本退化，不能说提示词带来新收益。小型教学对照也不能冒充独立人工校准研究。

## Ragas：样本、指标与结果索引

[CI 页面](https://docs.ragas.io/en/stable/howtos/applications/add_to_ci/) 提醒使用自己的系统输出，而非只给固定示例数据评分。页面中的 in_ci 示例与本课固定源码接口存在版本差异，不能直接复制参数。

固定版本 `8c63f10d500c44efbf24fdb9e2920de2104c321c` 的 [aevaluate](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/evaluation.py#L59)：

1. 验证样本类型与指标必需字段，为指标准备模型等依赖。
2. 按行与适用指标提交任务，用行、指标索引组织返回分数。
3. 将 scores、dataset、traces 等合为 EvaluationResult。

该固定版本已对 aevaluate 给出弃用提示，建议 experiment。第15课已读 [ExperimentWrapper.arun](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)，其完成顺序与单条异常还提醒我们显式保留任务身份和覆盖。不同入口的顺序保证不能混用。

这些源码解释了为什么要验证字段、保留逐行证据，而不是照搬框架默认值。本课没有安装第二套评分接入，也不将 Ragas 的旧 CI 参数写进可运行代码。

## 回归集的边界

三个任务同属 Atlas billing，公开且用于调试，不能当独立留出集。当前仅比较一句提示改动，每题一次真实运行；不提供广泛任务上的统计提升证据。

失败候选只进入待复核列表。确认任务、参考、文件和评分范围都有效，再补题和选择最小修复；针对接口异常改重试条件、针对证据不足改检索、针对说明不足改交付要求，不能一律改提示词。
