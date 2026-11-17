# e10 源码导读：每个匹配开关改变了什么

[教材](README.zh.md) · [工具池](mcp_tools.py) · [指标](metrics.py)

## MCP 的绑定与授权

上游 [s14](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s14_mcp_plugin/code.py) 使用进程内服务。本课 `connect_mcp` 保存客户端，`assemble` 转换 schema 并建立名字绑定，每轮更新可见工具快照。

绑定从内部表读取，参数不能覆盖实际客户端或原始工具名。规范化后检查名字冲突与长度。`HOST_POLICY` 独立判断授权，再进入处理器的参数校验。

## DeepEval ToolCorrectness

[文档](https://deepeval.com/docs/metrics-tool-correctness) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py)

- 默认匹配工具名与类型，非精确分母为预期调用数。
- `INPUT_PARAMETERS` 启用递归参数比较，按双方键的并集计权，多余键可能扣分。
- `should_consider_ordering` 使用加权最长公共子序列，仍按预期数归一化。
- `should_exact_match` 要求长度、位置、名称、类型及选中的参数或输出全部匹配，优先于 ordering。
- `available_tools` 触发模型选择评分，最后取它与匹配分的较小值。

因此 strict mode、exact match、ordering 不是同一个开关。额外调用未必降低覆盖分，效率需另评。

## Ragas ToolCallAccuracy

[Agent 指标说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py) · [参数比较](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/util.py)

从 `AIMessage` 取调用后，严格模式比较完整工具名序列；flexible 排序后比较，仍受长度与多重集影响。

参数比较遍历参考键，再以字符串比较值。额外预测键可能不扣分，整数与同形字符串也可能匹配。实际 handler 的 schema 仍可能拒绝该调用。名字对齐后还可能有参数部分分。

## Ragas ToolCallF1

[实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py) · [可哈希转换](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/util.py)

名字与完整参数转成可哈希集合，TP 为交集，FP 为多余种类，FN 为遗漏种类。顺序和相同调用的重复次数被丢掉。

固定实现双方空调用时 F1 为0，Accuracy 为1；第3课自写集合函数选择了另一种空集约定。先判断任务是否应调用工具，再解释这些默认值。

## ArgumentCorrectness 的输入来自哪轮

[文档](https://deepeval.com/docs/metrics-argument-correctness) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/argument_correctness.py) · [trace 适配](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/utils.py)

它根据 `input/tools_called` 生成 yes/no 裁决，再按有效 yes 比例聚合。空调用在固定版本直接返回1，不请求裁判；缺少判定不应被误作全部通过。

原生 trace 适配先定位选择参数的 LLM span。本课用 `parent_id` 重建每轮的已知消息，保留工具定义、连接与检索证据，并核对 verdict 数量。

控制轨迹与真实轨迹分开保存。教学投影只用于相应指标，最终任务仍读实际文件、执行证据和权限状态，接受多种满足合同的合法路径。
