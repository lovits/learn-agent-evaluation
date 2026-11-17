# e16 源码导读：证据怎样走到门禁

[教材](README.zh.md) · [综合运行时](../../integrated_agent/runtime.py) · [采样](code.py) · [评分](eval.py)

## 从公开入口追到模型与工具

```text
Runtime.submit → _goal_loop → 原生 agent_loop
                                  ├─ RecordedMessages.create
                                  └─ PreToolUse → handler → PostToolUse
                                                           ↓
                                                     tool_result
```

固定 [s15 集成](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py)、[s09 记忆](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py)、[s16 工作流](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s16_workflow_runtime/code.py)与 [s17 目标](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/code.py)在适配层接线，上游副本保留来源与许可。

`returned` 只表示入口返回。Goal 读取对话证据，独立检查器再读业务文件与持久状态。

## 原生观测与样本投影

`traces.py` 在固定版本 trace 结束边界保存原生对象。观测对象限定在实际调用边界，避免把整套运行时的公开对象图作为普通输入序列化。

`trace_samples` 用原生响应 ID 连接唯一 trace，保留工具名、参数、输出、时间与 UUID。函数正常返回的 `SUCCESS` 可能包含错误字符串，要继续读结果内容。

规范证据与工具观测分别构造 Faithfulness 样本；工具样本是指定读取的局部投影。原始记录不因投影而被替换。

## DeepEval 与 Ragas 怎样复用

[DeepEval Faithfulness](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)继续走 truths、claims、verdict 与 [QAG 聚合](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py)。默认接受 yes/borderline，惩罚含糊项只接受 yes。空裁决默认1，需要同时保留声明数。

[Ragas Faithfulness](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)走 statements、NLI、支持比例；无声明可返回 NaN，外层记录未定义。详情见[第5课源码导读](../e05_faithfulness/source_walkthrough.md)。

[DeepEval ToolCorrectness](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py)按配置评价覆盖、参数、顺序或完整匹配；[Ragas Accuracy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py)先对齐调用序列，[F1](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py)另算集合覆盖。两个预期调用只完成一个时，可以分别得到覆盖1/2、完整匹配0与集合F1为2/3。

这些是不同判分合同，不能平均同名分数来代替解释。

## 工作流为什么能恢复

`workflows.py` 安装可信脚本。`ExecutionState.agent` 先检查请求与预算，再按步骤、prompt 与 schema 查日志；命中结果仍经过 schema 校验。

`parallel` 等已经启动的分支结束后再抛错误，使成功分支可以写完 journal。恢复复用这些步骤；日志损坏时保留错误，不假装重新成功。

工作流完成与评审意见正确分别检查。`gates.py` 在已知测试文件不在输入范围时，拒绝接受项目级覆盖结论。

## 独立状态检查与回归入口

`verify.py` 运行有限业务合同，`state.py` 读取实际 Task、记忆索引、cron、worktree 与 workflow 日志。模型总结和团队摘要只作为可追查声明。

`critical_gate` 对每个关键值使用 `is True`，把假、未知和未评分都保留为拒绝项。通过比例可用于诊断，关键条件仍逐项处理。

[DeepEval evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py) 与 [Ragas evaluation](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/evaluation.py)提供批量入口；本课直接调用 metric 以保留中间阶段，不混用旧批量 API 与 collections 签名。

回归思路见 [DeepEval CI 指南](https://deepeval.com/guides/guides-regression-testing-in-cicd)与 [Ragas CI 指南](https://docs.ragas.io/en/stable/howtos/applications/add_to_ci/)。固定规则检查与真实模型评价分别运行，后者还需数据、裁判与配置版本。
