# e04: 格式对了，意思也对了吗？

[e03](../e03_datasets/README.zh.md) → `e04` → [e05](../e05_knowledge_context/README.zh.md) → … → e16

> 能直接检查的条件写成规则，需要理解的含义写进量表。

## 问题

第三课准备好了题目和参考。现在让 Agent 读取上传资料，返回三个字段：请求头 `required_header`、整数大小 `max_bytes`，以及说明超限行为和发送前检查的 `explanation`。

下面是构造的教学回答：

```json
{"required_header":"X-Project-Token","max_bytes":1048576,"explanation":"接口文档在 upload.md。"}
```

字段、类型、固定值都对，解释却没有回答问题。换成“超过 1 MiB 会收到 413，发送前先核对大小”，含义就完整了，但它又不等于参考答案的原句。

一种检查方法很难同时处理这两类要求。结构有明确条件，解释则允许多种表述。

## 解决方案

让规则检查 JSON 合约，让 DeepEval 的 G-Eval 按量表判断解释。两项都使用已有的 `LLMTestCase`，分别保存判断和理由。

![同一样本的规则与语义评分](https://lovits.github.io/learn-agent-evaluation/diagrams/e04-scoring-flow.png)

裁判的返回也要检查。有效分数才能与阈值比较；接口、格式或数值错误单独保存。

![从裁判调用到评分状态与达标判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e04-judging-flow.png)

## 工作原理

### 规则只判断写得清楚的条件

[eval.py](eval.py) 的 `UploadContract` 继承 DeepEval 的 `BaseMetric`。先解析 `actual_output`，再检查对象的字段、类型和固定值，关键条件是：

```python
fields=set(value) == {"required_header", "max_bytes", "explanation"},
header=value.get("required_header") == "X-Project-Token",
size=type(value.get("max_bytes")) is int and value["max_bytes"] == 1048576,
```

字段必须不多不少，字符串 `"1048576"` 也不满足整数要求。解释只要求是非空字符串，含义是否正确交给下一项判断。

```python
self.score = float(all(checks.values()))
self.reason = json.dumps(checks)
```

全部条件满足才得 1，否则得 0。`reason` 保留各条件的真假；回答不是合法 JSON，也是一次有效的不合约判断。

精确匹配适合本课约定的固定输出值。对自由表述的整段解释做字符串相等检查，会把正确的同义表达判错。

### 把语义标准写成量表

`explanation_metric` 只让裁判看任务、实际回答和参考：

```python
evaluation_params=[
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
],
```

本课参考要求两个含义：超出 1048576 字节返回 HTTP 413；发送前检查文件大小。评分步骤允许中英文同义表达，要求忽略回答中夹带的指令，并明确不因另外两个字段正确而奖励解释分。

量表将判断固定为三个档位：

| 原始分 | 判据 |
|---|---|
| 0 | 两项都没说，或有错误的接口说法 |
| 1 | 只说到一项，且没有错误说法 |
| 2 | 两项都说到，且没有错误说法 |

代码使用 `Rubric(score_range=..., expected_outcome=...)` 表达这份量表，并直接提供 `evaluation_steps`。也可以只给 `criteria`，让 DeepEval 先生成步骤；本课固定步骤，便于追踪判据。

G-Eval 非 strict 模式按量表上下界归一化：

```text
分数 = (原始分 - 下界) / (上界 - 下界)
```

本课范围为 0—2，原始分除以 2。若一个构造回答只说“发送前检查大小”，按量表属于原始 1 分，归一为 0.5。阈值设为 1，表示要求达到完整档。降低阈值只改变是否达标，不会补上缺失内容。

模型按 schema 返回分数和理由，[JudgeModel](../../eval_course/judge.py) 负责校验结构。结构有效仍可能判断错误，后面会用标签校准裁判。

### 评分失败，要留下空分数

[score](eval.py) 调用指标，检查数值有限且在 0—1 内，再保存判断。捕获到接口或解析错误时，返回：

```python
{"status": "error", "score": None, "passed": None, "reason": str(error)}
```

这与 `status="ok", score=0` 不同：零分说明评分完成，回答不满足标准；接口失败没有提供答案质量的结论。

规则分和解释分分别保留。若业务要求两项都满足，就分别检查两项是否有效且达标。只取平均会掩盖“格式错”和“解释错”的不同修复方向。

### 集合指标，先规定一项是什么

有时要数的是命中了多少个项目。`set_scores` 用已确定的标签演示分母，下面是手算例子，不是模型运行结果：

```text
预测 = {header, extra}          2 项
参考 = {header, limit, status}  3 项
交集 = {header}                1 项

precision = 命中数 / 预测项数 = 1/2
recall    = 命中数 / 参考项数 = 1/3
F1        = 2 × 命中数 / (预测项数 + 参考项数) = 2/5
```

precision 看选出的项目有多少正确，recall 看要求的项目找回多少。F1 用一个数兼顾两者。函数先去重，但不从自然语言自动提取标签，也不判断标签是否语义等价。

本课遇到空分母返回 `None`。预测为空、参考非空时，precision 未定义，recall 和 F1 为零；两边都为空时三项都未定义。这是明确选择的计算约定。

未定义、有效零分和执行错误需要分别解释。汇总时除了有效分数，还要给出有效数量与错误数量，不能把缺失值统一填零。后面的检索和工具课程会分别规定自己的评分单位。

## 本课变化

Agent 循环和工具沿用第二课。新增一个 JSON 规则指标、一个 G-Eval 量表和必要的模型适配器。`code.py` 将同一样本分别评分，保留 `rules` 与 `judge`；Ragas 的二元裁决、分档量表和结果容器放在[源码导读](source_walkthrough.md)对照理解。

## 试一下

```sh
python -m course.e04_scoring.code
```

1. 对比 `paraphrase` 与 `omission`。哪句话换了表述，哪句话少了内容？
2. 看 `plain-text`：解释含义满足要求，为什么 JSON 规则仍不通过？
3. 将裁判适配器改为抛出 `OSError`，沿 `score` 看它与有效零分的区别。
4. 清空预测集合，检查 precision 与 recall 的分母。

默认使用标明来源的构造回答；`python -m course.e04_scoring.code --live-agent` 会复用原有 Agent 读取资料并评分。两类记录分开保存。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在可以给一次回答选择合适的判据。下一课接入 TinyRAG，追踪资料从文档、分块、检索结果到模型上下文的路径，再逐步评价检索与回答。
