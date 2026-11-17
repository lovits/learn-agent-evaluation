# e12 源码导读：目标、结果与外部证据

[教材](README.zh.md) · [交付检查与原生裁判](eval.py) · [运行入口](code.py)

## 本课调用链

`code.py` 复用第11课 run_case，底层仍为第2课 agent_loop 和原有工具。八组构造决策实际写文件，最终都回复“已完成。”；--live 另加一组真实模型修复。原始消息、响应、调用和最终文件内容分别保存，没有修改完成声明来制造对照。

`inspect_delivery` 在 Agent 返回后读取目标，调用独立 Python 子进程加载 billing.py。检查程序由评分端提供，不从工作区加载 Agent 可修改的检查文件。四组输入分别覆盖空订单、多项且数量大于1、另一组金额和零数量；每组同时检查返回类型、金额与输入是否保持不变。

policy.txt 的参考来自任务夹具，哈希不由 Agent 自报。评分前后比对策略文件的实际字节，防止“金额正确”掩盖保护条件失败。它检测最终状态与检查期间的变化，不能证明 Agent 过程中从未改动后又恢复文件；若任务禁止任何写入行为，还需更完整的事件或文件系统审计。

`evidence_sample` 保留原始 Agent 回复，另加入 independent_observation，形成面向评分的复合结果。这个 actual_output 是评测者组装的证据，不是模型直接生成的全部内容。原始运行样本可由 to_deepeval(run) 还原。

## DeepEval：把业务条件写进 BaseMetric

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，参考 [自定义指标指南](https://deepeval.com/guides/guides-building-custom-metrics)。

[BaseMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py) 声明 measure、a_measure、score、threshold、reason 与 success 等接口。它并不知道订单业务；继承接口只让业务判断能够与其他 DeepEval 指标一起记录，不会自动保证判据正确。

本课 DeliveryContract 读取独立观察，要求检查状态有效、条件不为空，再把关键条件作逻辑与：

```python
self.score = float(all(evidence["checks"].values()))
```

金额行为正确、策略文件未变等条件均为必要条件。本指标覆盖可执行的程序行为与保护条件，不评价任务中的说明义务。说明是否充分由语义裁判另看，不能把程序契约通过当成全部任务要求已满足。它不是子检查通过比例；如果保护条件失败，其他项目通过再多，也不能补偿。threshold=1 只负责把当前分数与通过条件比较，不会替业务决定哪些条件关键。

有效反例是0；观察本身缺失或损坏是评分错误，score 保持 None。候选程序语法错误被检查程序捕获，loaded=False，属于确实观察到的交付失败；子进程未产生有效观察则不能伪装成有效0分。候选执行超时表示未满足本课的有限执行条件，不代表所有检查基础设施故障都可归为候选失败。

## DeepEval：Task Completion 先抽取，再判断

[Task Completion 文档](https://deepeval.com/docs/metrics-task-completion) 对应 [task_completion.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/task_completion.py)。本课固定 eval_mode="llm"、async_mode=False，不把其他推理模式的公式混进来。

沿 measure 看两阶段：

1. `_extract_task_and_outcome` 生成 task、outcome。若 `_trace_dict` 为字典，使用 trace 模板；否则固定源码仍保留 input、actual_output、格式化 tools_called 的兼容路径。
2. `_generate_verdicts` 将目标与抽出的 outcome 交给裁判，得到 verdict、reason；默认 `_calculate_score` 直接采用 verdict，strict_mode 才会作阈值压零。

显式提供 task 会固定最终比较目标，但不会省掉抽取请求。没有提供 task 时，目标也由模型推断，可能在第一阶段就偏离用户要求。本课使用原始任务固定目标，并保存 judged_task、outcome 与最终理由。

[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/schema.py) 中 TaskAndOutcome 要求两个字符串，TaskCompletionVerdict 的 verdict 为 float；本课沿用第4课包装层，额外拒绝非有限或超出[0,1]的分数。结构解析通过与业务判断正确是两件事。

抽取模板 [extract_goal_and_outcome.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/templates/extract_goal_and_outcome.txt) 让裁判从输入、响应和工具中概括结果。它不会再次导入程序或检查磁盘；若工具只报告“已写入”，并不能独自证明业务行为符合要求。

[generate_verdict.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/templates/generate_verdict.txt) 要求0到1的目标对齐分，不是逐项业务条件通过率。语义分与 DeliveryContract 保留为两列，不取平均；裁判高分不能覆盖明确的硬条件失败。

### 本课使用的兼容路径

当前官方文档推荐通过 observe 和 evals_iterator 建立完整 tracing，指标也标记 requires_trace=True。本课为沿用已保存的最小运行记录，直接调用固定版本 measure 的无 trace 兼容路径，传入任务、按顺序保存的 ToolCall 与复合观察。它不是 SDK 原生 span 树，也不是建议在通用 evaluate 中跳过 tracing。

因此本课只能说明这个固定版本、这组明确输入的行为。迁移到追踪式线上运行时，应按官方方式收集完整 trace，再核对裁判实际可见的证据；不能给 _trace_dict 伪造一棵没有真实执行来源的树。

## Ragas：有参考与无参考改变了目标来源

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，参考 [Agent Goal Accuracy](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/#agent-goal-accuracy)。本课只读原理，不执行第二套框架评分。

现代 [agent_goal_accuracy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/metric.py) 提供两个类：

- WithReference 把消息列表格式化，先推断 workflow 的 end_state，再与给定 reference 比较。
- WithoutReference 同样先推断 user_goal、end_state，但第二阶段的目标来自刚推断的 user_goal。

两条路径各有两次语义请求，最后将比较结果转换成0或1。AgentGoalAccuracy 是 WithReference 的别名。有参考不表示结果会从业务系统自动读取；无参考也不表示没有标准，只是目标来源变成模型推断。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/util.py) 将 workflow 抽成 user_goal、end_state，CompareOutcomePrompt 再比较 desired_outcome、arrived_outcome。若对话中只是声称“已下单”，缺少真实订单状态，这条推断链仍受输入证据限制。

[collections/base.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/base.py) 提供 ascore 与同步 score 包装，结果使用 MetricResult。自定义指标仍需自行实现业务判据。它与 DeepEval BaseMetric 的返回和字段接口不同，本课不复制一个 Ragas 适配器。

## 独立检查的边界

有限输入通过只说明这些情况被检查过。用返回650的硬编码反例可以发现“只看演示输入”的问题；扩大输入族、加入性质检查和留出任务仍有必要。程序检查也不能替自然语言要求自动决定全部成功标准。

本课检查器与 Agent 的决策分离，进程使用 Python -I 并设置超时，但仍在同一个教学容器中运行。它不是对恶意代码的安全沙箱，也不具备防篡改证明。真实业务应由权限隔离的评测进程读取可信状态，必要时使用只读挂载、网络隔离与外部系统回执。

飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对 TaskCompletion 的轨迹定位、自定义指标接口与 AgentGoalAccuracy 两种目标来源。
