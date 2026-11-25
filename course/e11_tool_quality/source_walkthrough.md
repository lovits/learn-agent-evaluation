# e11 源码导读：名称、参数、顺序与输出如何分别打分

[教材](README.zh.md) · [五种原生配置](eval.py) · [真实工具执行](code.py)

## 本课调用链

[code.py](code.py) 中的 `run_case` 复用第 2 课的 `agent_loop`、`TOOLS` 与工具执行器。十组预设决策在隔离工作区里真实调用工具，文件读写、目录冲突与权限拒绝都由工具返回；传入 `--live` 时，复制与权限恢复两个任务交由真实模型自主决策，输入、原始响应和工具事件全部落盘。预设样本中的 `reordered` 提前在脚本里写明源文件内容，用来单独观察顺序变化对分数的影响。

[eval.py](eval.py) 中的 `sample_for` 调用第 2 课的 `to_deepeval` 把实际工具事件转为 `ToolCall`，再显式构造 `expected_tools`。`tool_scores` 用五种原生配置分别评分，各自保留结果；目标文件是否存在以及内容是否一致则由 `run_case` 独立记录。

在复制任务中，工作区内的 `bash` 复制属于允许的替代路线，而参考步骤只写了文件工具路线，用来呈现单一参考路径的局限；权限恢复任务则明确禁止改用 `bash` 绕过文件工具的路径校验。

## DeepEval：`ToolCorrectnessMetric` 的三条计算路径

以下源码分析基于 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念文档见 [Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)。

沿 [tool_correctness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py) 的执行路径可以看到：

1. `_required_params` 要求 `input`、`tools_called` 和 `expected_tools`。规则匹配直接比较工具调用列表，不读取 `actual_output` 里的完成声明。
2. `evaluation_params` 默认为空，只比对工具 `name` 与 `type`。显式传入 `ToolCallParams.INPUT_PARAMETERS` 或 `ToolCallParams.OUTPUT` 后，才会把对应字段纳入比较。
3. `_calculate_non_exact_match_score` 为每个参考调用在未使用的实际调用中挑选最高权重，累加后除以参考长度。额外调用不会进入分母，因此它是贪心参考覆盖。
4. `_compare_dicts` 在非精确模式下按两个字典键的并集计权：值相等的键各贡献 1 份权重，嵌套字典递归计算。例如 `path` 与 `content` 两个键只匹配了 `content`，权重就是 `1/2`。精确模式下则要求字典完全相等。
5. 开启 `should_consider_ordering=True` 时走 `_compute_weighted_lcs`，用动态规划求最大加权公共子序列并除以参考长度。它允许跳过多余调用和不匹配项，只要求匹配到的子序列保持相对顺序。
6. 开启 `should_exact_match=True` 时优先走 `_calculate_exact_match_score`，逐位置核对总长度、名称、类型以及指定字段，任何一处不符直接得 `0`。`strict_mode` 另负责按阈值压零，本课保持关闭。

需要注意两处实现细节：

- 非精确模式用 `ToolCall` 值集合追踪已匹配项，而不按事件 ID 消耗次数。如果任务需要核对相同调用的执行次数，应直接检查未去重的事件列表，或采用精确序列匹配。
- `measure` 传入 `available_tools` 时会额外触发一次 LLM 工具选择评估，并取“调用匹配分”与“选择分”的较小值。本课不传 `available_tools`，选择部分固定为 `1`，五种规则模式全程零模型请求。
- 当 `tools_called` 和 `expected_tools` 都为空时，原生指标返回 `1`；无参考但有实际调用时返回 `0`。设计空参考用例时要先明确它代表“不应调用任何工具”。

## DeepEval：`ArgumentCorrectnessMetric` 的语义参数判定

概念见 [Argument Correctness 文档](https://deepeval.com/docs/metrics-argument-correctness)，实现见 [argument_correctness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/argument_correctness.py)。它的必需字段是 `input` 与 `tools_called`，不读取 `expected_tools`。

`_generate_verdicts` 把原始问题和每次工具调用交由裁判模型，判断输入参数是否准确且与任务相关。[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/schema.py) 定义了逐条 `yes`/`no` 与可选理由，最终得分是 `yes` 的占比。设置 `include_reason=False` 省去了一次总分总结请求，同时保留了每条否定裁决的理由。

当 `tools_called` 为空时，原生 `measure` 不发模型请求并直接返回 `1`。本课 `judge_arguments` 保留 `sdk_score`，并将状态改为 `not_applicable`、`score` 设为 `None`，避免把空调用误读为满分；若返回的裁决数与实际调用数不一致，则记为 `error`。

此外，`ToolCall` 的完整序列化可能携带工具输出，将多步调用合并送评属于事后回顾。若需严格评估某一步决策当下的参数选择，应按该步对应的 LLM span 截取当时上下文，排除后续工具返回的影响。

[样本与评测记录](assessment.md)
