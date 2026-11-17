# e11 源码导读：从完成目标到自定义指标

[教材](README.zh.md) · [目标状态](code.py) · [外部规则](verify.py) · [指标](metrics.py)

## 停止候选在哪里被复查

参考 [s17 目标循环](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/code.py)。上游在返回边界调用目标判断，处理允许、阻止、延后、异常和预算上限。

本课 `run_case` 包住已有循环：`finished` 后调用公开 `probe`，失败反馈追加到 history，继续使用同一工具池。明确要求“保留测试”又“删除所有测试”的声明式冲突，先标为 impossible；这不承担一般自然语言的可满足性判断。

内部 span 编号可能在续轮间重复，定位还要带上审查轮号。

## 外部执行器读实际代码

[runner.py](runner.py) 检查 AST、签名和允许的纯 Python 子集，再在受限子进程运行函数。类型采用精确比较，异常比较类名；缺文件、删除测试属于已观察的失败。

不支持的代码、语法错误或执行器异常按接口保留为未评分。资源限制用于有限教学代码，不提供通用恶意代码隔离保证。

## DeepEval TaskCompletion 的两次模型判断

[文档](https://deepeval.com/docs/metrics-task-completion) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/task_completion.py)

```text
prepare_measure
  → _extract_task_and_outcome → TaskAndOutcome
  → _generate_verdicts → TaskCompletionVerdict
  → _calculate_score
```

官方推荐完整 trace。固定版本也保留无 `_trace_dict` 时读取 `input/actual_output/tools_called` 的兼容分支，本课在这里使用序列化对话及明确外部事实；原生采集在计划课接入。

即使显式传 task，抽取阶段仍执行。`threshold=1` 不等于 strict mode，未启用 strict 时中间分仍保留。schema 声明 float，外层还需校验有限值与范围。

## Ragas 的目标从哪里来

[Agent 指标文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/) · [AgentGoalAccuracy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/metric.py)

WithReference 先把消息转成 workflow，抽取 `WorkflowOutput(user_goal,end_state)`，再用给定 reference 比较终态。WithoutReference 改为比较推断出的 user_goal，仍然需要模型与证据。

第二阶段 `CompareOutcomeOutput` 返回字符串0/1及理由。固定实现的 `MetricResult` 可能只保存 value，理由要从捕获的结构化结果读取。两个指标都没有代替应用执行代码。

## 两套自定义接口怎样接

[DeepEval 自定义指标指南](https://deepeval.com/guides/guides-building-custom-metrics) · [BaseMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py)

`ExternalCompletionMetric.measure` 读取 metadata，严格解析外部 Evidence，再取所有必需 checks 的逻辑与。每条样本重置 score/error/reason，`a_measure` 复用无网络规则。

Ragas 的 [collections BaseMetric](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/base.py)需要覆盖 `ascore`，返回 value/reason。已经在异步环境中时直接 await，不嵌套运行事件循环。

`composite` 是本课明确的业务政策：有效分取 min；错误或缺失维持未评分。逐项检查仍保留，方便定位失败，不能只输出一个总分。
