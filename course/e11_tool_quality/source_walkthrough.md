# e11 源码导读：匹配的是字段、集合还是序列

[教材](README.zh.md) · [五种原生配置](eval.py) · [真实工具执行](code.py)

## 本课调用链

`run_case` 复用第2课 agent_loop、TOOLS 和执行器。十组构造动作真实执行，决策来自脚本；--live 增加两个真实模型任务，调用决定和原始回复单独记录。工作区隔离，构造样本的固定写入内容只用于隔离顺序因素，不表示模型在读取之前就知道源文件内容。

`sample_for` 把实际事件转换成 ToolCall，再显式构造 expected_tools。没有把序列化工具字典直接当成 SDK 对象。五种规则共用同一对调用列表，不平均成总分；目标文件的存在与内容独立记录。

本课允许 Bash 作为工作区内的合法复制路线，参考仍给出文件工具路线。这用于说明单一参考的覆盖边界，不是故意把所有有效解法定义成错误。权限任务另行明确禁止绕过拒绝；Bash 本身没有等价的文件路径沙箱约束。

## DeepEval：参考匹配的三条路径

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念见 [Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)。

沿 [tool_correctness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py) 阅读：

1. `_required_params` 为 input、tools_called、expected_tools。本课照常提供 actual_output，但规则匹配不拿最后一句“已完成”判断文件成功。
2. 默认字段列表为空，只匹配 name 和 type。指定 ToolCallParams.INPUT_PARAMETERS、OUTPUT 才比较相应字段。
3. `_calculate_non_exact_match_score` 对每个参考调用选择未使用实际调用中的最高权重，累计后除以参考长度。额外实际调用不必扣分；这是贪心参考覆盖，不是工具集合 F1。
4. `_compare_dicts` 非精确模式按两个字典键的并集计权；相等值贡献一个键的权重，嵌套字典递归比较。path、content 两键中只匹配 content，就得到 1/2。精确模式则要求字典完全相等。
5. should_consider_ordering 使用 `_compute_weighted_lcs`，以动态规划寻找最大加权公共子序列，最后仍除以参考长度。它允许跳过额外调用和不匹配项；不能当成序列全等。
6. should_exact_match 优先走 `_calculate_exact_match_score`，检查长度、每个位置的名称与类型，再检查指定字段。长度或一处不符即为 0。strict_mode 另负责阈值压零，本课关闭。

非精确模式的已匹配集合按 ToolCall 值去重，不是按事件 ID 消耗次数。若参考要求完全相同的重复动作，应单独核对数量与事件，或使用确实符合任务的精确序列标准。不能把默认模式当作严格多重集合匹配。

`measure` 还支持 available_tools 下的工具选择裁判，并取调用匹配与选择评分的较小值。本课不传 available_tools，因此选择部分固定为 1，规则过程没有模型请求；虽提供 JudgeModel 以初始化 SDK，也不代表它已经被调用。

两边都无调用时，原生匹配为 1；无参考却有实际调用时为 0。空参考的任务语义仍需先明确，不能把“无需工具”和“没有提供参考”混为一谈。

## DeepEval：语义参数判定

[Argument Correctness 文档](https://deepeval.com/docs/metrics-argument-correctness) 对应 [argument_correctness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/argument_correctness.py)。必需字段是 input、tools_called，不读取 expected_tools 作标准。缺少显式调用时，辅助路径还可以从 trace 恢复调用；本课直接提供实际 ToolCall。

`_generate_verdicts` 将原问题和完整调用表示交给提示词，要求判断每次输入参数是否正确、相关；[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/schema.py) 使用 yes/no 与可选 reason，聚合为 yes 比例。include_reason=False 只省去额外总分理由，逐调用否定理由仍保留。

没有调用时，原生 measure 直接给 1 且不请求模型。本课标记 not_applicable，保存 sdk_score；它不能证明没有漏掉必要工具。有调用却裁决数量不齐时记 error/None，不补成 yes 或 no。

完整 ToolCall 表示可能包含执行结果。本课也将多步调用汇总到短任务样本，属于回顾性观察，不是严格的单次决策前评价。若要判断某一步在当时是否选对参数，应按对应 LLM span 构造当时上下文，排除后来才获得的信息；也不能仅凭参数裁判证明复制内容正确或最终任务已完成。

## Ragas：ToolCallAccuracy 的名称门槛

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Agentic or Tool use](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)。本课没有运行 Ragas。

现代 [tool_call_accuracy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py) 从 AIMessage 提取调用。strict_order=True 要求完整名称列表相等；False 则先排序，再检查名称列表相等。

名称门槛通过后，按配对参数相似度求和、除以参考长度。[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/util.py) 的 exact_match_args 实际按参考键计数，并用 str(value) 比较，允许参数部分得分；额外预测键不会直接进入分母。因此不能仅凭函数名把它叫作全字典精确相等。

代码虽有长度覆盖惩罚，但当前名称列表长度不同就不能相等，最终乘名称对齐因子仍为 0。这个顺序门槛与 DeepEval 有序 LCS 的部分匹配不同。

## Ragas：ToolCallF1 使用集合

[tool_call_f1/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py) 将名称和参数递归转换为可哈希项，构造 actual、expected 两个集合，再求交集、差集及 F1，保留四位小数。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/util.py) 忽略字典键顺序，保留列表内部顺序；不比较工具输出，也不保留外层调用先后或相同调用的重复次数。

因此，本课 extra_read 再次读取相同 source.txt，在集合中不会增加新项；不能用“实际四次、参考三次”直接推算该 F1 会下降。若新增一个不同参数调用，才可能形成额外集合项。

空调用边界也不同：Accuracy 两边都空返回 1，而 F1 的空集合公式返回 0。它们是实现约定，不应据此断言不调用工具一定正确或错误。真正成功条件在下一课回到产物与任务要求判断。

飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对工具匹配、参数判断与工具调用集合相关段落，具体规则以固定源码为准。
