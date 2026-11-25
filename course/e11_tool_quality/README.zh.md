# e11: 工具调用质量：工具名选对了，事情做对了吗？

[e10](../e10_rag_diagnosis/README.zh.md) → `e11` → [e12](../e12_task_completion/README.zh.md) → … → e16

> *“工具名完全匹配，参数也可能写错；参数全部匹配，工具执行也可能报错。”*
>
> **评测层：工具调用质量。** 拆开核对工具名称、输入参数、调用顺序与执行结果，再按需引入参数语义裁判。

## 问题

假设任务是把 `source.txt` 复制到 `delivery.txt`，再读回确认。参考路线只有三步：读源文件、写目标文件、读回目标文件。

如果 Agent 把后两步的路径都写成 `other.txt`，调用的工具名依然是 `read_file`、`write_file`、`read_file`，磁盘上却根本没有 `delivery.txt`。反过来，工具名和参数全都填对，如果 `delivery.txt` 所在位置恰好是个目录，写入依然会报错。

要评价 Agent 工具用得好不好，必须先分清你在比较哪一层：选对了工具名、填对了参数、按顺序调用，还是拿到了预期的执行结果。

## 解决方案

本课沿用第 2 课的 Agent 循环与三个具名工具，完整记录每次调用的 `name`、`arguments` 和 `result`，在隔离工作区里真实执行调用轨迹，再对照参考路线逐层评分。

![具名调用经过校验与分发，状态和输出进入事件记录](https://lovits.github.io/learn-agent-evaluation/diagrams/e11-tool-flow.svg?v=8022eba4fe33)

同一条执行轨迹会送进 DeepEval 的 `ToolCorrectnessMetric` 五种原生规则配置，分别检查名称、参数、顺序与输出；对于允许替代路线的场景，再叠加 `ArgumentCorrectnessMetric` 做参数语义判断，两类结果各自保留。

![参考匹配与参数语义裁判分别保留结果](https://lovits.github.io/learn-agent-evaluation/diagrams/e11-scoring-flow.svg?v=199c5383280d)

## 工作原理

### 真实执行与参考构造

[code.py](code.py) 中的 `run_case` 为每条测试样本准备独立工作目录。默认模式按预设调用列表驱动第 2 课的 `agent_loop`，文件读写、目录冲突和权限拒绝都由工具真实执行产生。加上 `--live` 参数后，复制与权限恢复两个任务交由真实模型自主决策，`run["origin"]` 会区分真实模型决策与脚本决策，并完整保存每轮输入、原始响应和工具事件。

工具分发逻辑保持原样：

```python
output = HANDLERS[name](workspace=workspace, **arguments)
```

文件工具会先校验路径是否落在工作区内，而 `bash` 工具仅沿用基础命令拦截规则，权限任务会在提示词中明确禁止用 `bash` 绕过文件权限拒绝。

运行结束后，[eval.py](eval.py) 中的 `sample_for` 把实际工具事件转成 `tools_called`，把参考步骤构造成 `expected_tools`：

```python
ToolCall(
    name=c["name"],
    input_parameters=c["arguments"],
    output=c["result"],
)
```

### 常规匹配衡量的是参考覆盖

`ToolCorrectnessMetric` 默认只比较工具名称和类型。本课不传入 `available_tools`，因此不会触发额外的最优工具选择模型调用，五种模式全部由原生确定性代码计算。

在非精确模式下，指标会为每个参考调用寻找一个尚未匹配的实测调用，累加匹配权重后除以参考调用总数：

```text
常规匹配 = 累计匹配权重 / 参考调用数
```

因为分母是参考调用数，如果参考需要 3 次调用，实际做完这 3 次后又多读了一次文件，常规分数依然是 `1`。它反映的是参考步骤的覆盖程度，无法直接约束多余调用。

### 参数匹配与部分权重

要把输入参数纳入比对，需要显式指定 `evaluation_params`：

```python
evaluation_params=[ToolCallParams.INPUT_PARAMETERS]
```

非精确模式比较参数字典时，会按两个字典键的并集计算匹配比例。例如 `write_file` 有 `path` 和 `content` 两个参数，如果 `path` 写错而 `content` 一致，这次写入仍会得到 `1/2` 的结构匹配权重。这个权重只代表字典键值的重合度，判断文件是否落盘仍要看执行输出与工作区产物。

### 有序子序列与完全匹配

开启 `should_consider_ordering=True` 后，`ToolCorrectnessMetric` 改用加权最长公共子序列（Weighted LCS），在保持先后顺序的前提下取最大累计权重，再除以参考长度。参考顺序是“读源、写目标、读目标”，如果实际先写再读，仍会匹配其中两个有序位置并拿到部分分；如果完整参考顺序都出现了，中间夹杂额外调用，有序分数依然可以是 `1`。

当任务要求调用次数、先后位置和指定字段完全一致时，需要开启 `should_exact_match=True`。本课对照的五种原生配置如下：

| 模式 | 比较范围 |
|---|---|
| `names` | 默认无序参考覆盖，只比对工具名称与类型 |
| `arguments` | 加入输入参数比对，允许键级部分权重 |
| `ordered_arguments` | 参数加权的有序最长公共子序列 |
| `exact_arguments` | 调用长度、每个位置的工具名与输入参数完全一致 |
| `exact_outputs` | 在精确参数基础上，要求工具执行输出也与参考一致 |

是否采用唯一序列取决于任务本身。对于允许多种合法解法的任务，强行用单一路径做精确匹配会把正确做法判为低分。

### 参数语义裁判与覆盖边界

`ArgumentCorrectnessMetric` 根据原始任务和实际发生的 `tools_called` 逐条判断参数是否合理，不依赖 `expected_tools`。它能接受语义合理的 `bash` 复制命令，但因为只审视已发生的调用，缺少必要步骤（例如漏掉读回确认）时，已执行调用的参数仍可能全获 `yes`。

本课包装层会保留逐调用的 `yes`/`no` 裁决与理由，并核对裁决总数是否等于实际调用数。当实际调用为空时，原生指标会直接返回 `1`，包装层在保留 `sdk_score` 的同时把状态标为 `not_applicable`，把漏调工具的检查交给参考覆盖与产物核验。

另外，这里将整段短任务的调用汇总评估，属于事后回顾；若要评估模型在单步决策当下的参数质量，应按对应步骤的上下文单独构造样本。

### 调用匹配与执行结果分开看

`tool_failed` 场景会先把 `delivery.txt` 建为目录。此时写入工具的名称和参数与参考完全一致，但实际返回 `error`。只有比对 `output` 或直接检查磁盘文件，才能发现交付失败。

`permission_recovery` 展示了另一种情况：任务要求先尝试读取越界路径，收到 `denied` 后写入工作区内的 `status.txt` 并读回。这里的 `denied` 是符合预期的安全拦截，不能把所有非 `ok` 状态一律当作 Agent 出错。

而 `bash_alternative` 用合法的 Bash 命令完成了复制并生成正确文件，但在以文件工具为参考的规则匹配中得分为 `0`。工具路线相似度与任务最终结果必须拆开评估。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `run_case` | [code.py](code.py) | 准备隔离工作区，复用 `agent_loop` 真实执行预设或模型决策并记录产物 |
| `sample_for` | [eval.py](eval.py) | 将运行记录与参考步骤转换为带 `expected_tools` 的 `LLMTestCase` |
| `tool_scores` | [eval.py](eval.py) | 用五种 `ToolCorrectnessMetric` 原生配置分别计算名称、参数、顺序与输出分 |
| `judge_arguments` | [eval.py](eval.py) | 运行 `ArgumentCorrectnessMetric`，保留逐条裁决并处理空调用与数量校验 |

## 试一下

运行预设场景的五种规则匹配对照：

```sh
python -m course.e11_tool_quality.code
```

动手验证四个问题：

1. 对比 `wrong_path` 的 `names` 与 `arguments` 分数，手算写入调用的部分权重。
2. 对比 `reordered`、`extra_read`、`duplicate_write`，看清有序子序列与完全匹配的差别。
3. 查看 `tool_failed` 的执行状态，说明为什么精确参数满分下目标文件依然缺失。
4. 加上 `--live --judge` 运行真实模型复制与权限恢复任务，核对工具事件、参数裁决与磁盘产物。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

工具轨迹只能说明 Agent 做了哪些操作，还不能直接代表用户目标已经达成。下一课 `e12` 从用户最终收到的结果出发，检查磁盘代码的行为契约、副作用和保护条件，再对照 DeepEval 的 `TaskCompletionMetric`。
