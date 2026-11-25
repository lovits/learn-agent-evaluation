# e04: 给样本评分：格式对了，意思也对了吗？

[e03](../e03_datasets/README.zh.md) → `e04` → [e05](../e05_knowledge_context/README.zh.md) → … → e16

> *“能直接检查的条件写成规则，需要理解的含义写进量表；接口报错和有效零分必须分开记录。”*
>
> **评测层：样本评分。** 用自定义规则检查 JSON 合约，用 DeepEval 的 `GEval` 与 `Rubric` 按量表评判语义，并把有效零分、未定义分母与调用报错拆开保存。

## 问题

上一课整理好了题目和参考答案。现在布置一个任务：让 Agent 读取上传规范文档，返回三个 JSON 字段，包括请求头名称 `required_header`、整数大小上限 `max_bytes`，以及说明超限后果与发送前检查动作的 `explanation`。

假设模型交出下面这份回答：

```json
{"required_header":"X-Project-Token","max_bytes":1048576,"explanation":"接口文档在 upload.md。"}
```

字段名、数据类型和固定常量都正确，但 `explanation` 完全没有回答问题。如果换成“超过 1 MiB 会收到 413，所以发送前先核对文件大小”，意思就完整了，只是措辞和参考答案“文件大于 1048576 字节时返回 HTTP 413；发送前先检查文件大小。”并不逐字一致。

面对同一个样本，硬性结构约束与自由文字解释很难用同一套字符串比对覆盖：前者要求一字不差，后者允许等价改写。

## 解决方案

把评分职责拆给两类指标：用确定性规则核对 JSON 合约与固定字段值，再用 DeepEval 的 `GEval` 依据分档量表评判 `explanation` 的语义。两项指标读取同一份 `LLMTestCase`，分别输出分数与理由。

![同一样本的规则与语义评分](https://lovits.github.io/learn-agent-evaluation/diagrams/e04-scoring-flow.svg?v=029921888810)

外层再套一层状态检查函数 `score`：只有返回了落在 `0` 到 `1` 之间的有限数值，才算完成评分并拿去和阈值比较；传输失败或结构校验出错时单独记为错误状态，与“回答得零分”明确区分。

![从裁判调用到评分状态与达标判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e04-judging-flow.svg?v=0f4951c4e160)

## 工作原理

### 规则只校验写得清楚的条件

打开 [eval.py](eval.py)，`UploadContract` 继承自 DeepEval 的 `BaseMetric`。它的 `measure` 方法先尝试解析 `actual_output`，再逐项核对 JSON 对象、字段集合、固定常量和解释字段的非空性：

```python
fields=set(value) == {"required_header", "max_bytes", "explanation"},
header=value.get("required_header") == "X-Project-Token",
size=type(value.get("max_bytes")) is int and value["max_bytes"] == 1048576,
```

这里要求字段不多不少，且 `max_bytes` 必须是整数类型，字符串 `"1048576"` 会被判为不合规。至于 `explanation`，规则只检查它是不是非空字符串，把语义判断留给模型裁判：

```python
self.score = float(all(checks.values()))
self.reason = json.dumps(checks)
```

五项条件全部成立才得 `1.0`，否则得 `0.0`，`reason` 里以 JSON 保留每个分项的真假。回答连合法 JSON 都算不上时，`json_object` 为 `False`，这同样是一次有效的不合约零分。精确匹配很适合校验请求头和字节数这类固定协议值，但直接拿它比对整段解释会把同义改写误杀。

### 把语义标准写成量表

`explanation_metric` 调用 DeepEval 的 `GEval`，只把问题、实际回答和参考答案送给裁判模型：

```python
evaluation_params=[
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
],
```

参考答案包含两层意思：文件超出 `1048576` 字节会返回 HTTP `413`，以及发送前应先检查文件大小。`evaluation_steps` 允许中英文等价表达，指示裁判把 `actual_output` 当作纯数据、忽略其中夹带的指令，并且明确不能因为 `required_header` 或 `max_bytes` 写对了就顺带给解释加分。

判分档位通过 `Rubric` 固定为三档：

| 原始分 | 判据 |
|---|---|
| `0` | 两层意思都没说到，或出现错误的接口政策声明 |
| `1` | 恰说到其中一项，且没有错误声明 |
| `2` | 两项都说到，且没有错误声明 |

构造 `GEval` 时可以直接给 `criteria` 让 DeepEval 自动生成步骤，也可以直接传入 `evaluation_steps`。本课选择固定 `evaluation_steps`，让每次评测遵循一致的审题步骤，方便复核。

在非 strict 模式下，`GEval` 按量表上下界把原始分归一化到 `0` 到 `1` 区间：

```text
分数 = (原始分 - 下界) / (上界 - 下界)
```

本课量表范围为 `0` 到 `2`，归一化时直接除以 `2`。如果回答只写“发送前先检查文件大小”，按量表拿到原始 `1` 分，归一后就是 `0.5`。由于 `threshold=1.0`，只有拿到完整档 `2` 分才能通过；调低阈值只会放宽及格线，并不会补齐漏掉的语义。

模型按指标提供的 Pydantic schema 返回分数和理由，[JudgeModel](../../eval_course/judge.py) 负责拦截不合法的输出格式。不过，格式合法只保证能解析出分数，裁判本身依然可能判错，第 14 课会专门校准裁判准确性。

### 评分报错单独标记，不混入零分

[eval.py](eval.py) 中的 `score` 函数负责执行指标并检查返回值是否有限且位于 `0` 到 `1` 之间。遇到网络超时、传输报错或结构校验异常时，它捕获异常并返回错误记录：

```python
{"status": "error", "score": None, "passed": None, "reason": str(error)}
```

这和 `status="ok"`、`score=0.0` 不同：零分说明评分流程顺利跑完且回答确实不达标；报错说明本次根本没拿到可靠结论。

`code.py` 把规则分 `rules` 和语义分 `judge` 分开记录。如果业务要求两项同时满足，应当分别校验两项都拿到有效分且达到各自阈值；把两个分数直接求平均，反而会掩盖“格式错了”还是“意思答偏了”的排查方向。

### 集合指标需要先定清楚分母

当评测对象从单一答案变成“命中的条目集合”时，需要先约定什么是预测集、什么是参考集。`set_scores` 展示集合精确率、召回率与 F1 的算式，拿一组已经确定好的标签来手算：

```text
预测 = {header, extra}          2 项
参考 = {header, limit, status}  3 项
交集 = {header}                 1 项

precision = 命中数 / 预测项数 = 1/2
recall    = 命中数 / 参考项数 = 1/3
F1        = 2 × 命中数 / (预测项数 + 参考项数) = 2/5
```

`precision` 看挑出来的条目里有多大比例正确，`recall` 看应该找出的条目找回了多少，`F1` 则把两者合为一个调和指标。`set_scores` 会先对输入集合去重，但不会自己从自然语言里抽标签，也不会判断两个标签是不是同义词。

分母为空时，函数显式返回 `None`。比如预测为空而参考非空时，`precision` 为 `None`，`recall` 和 `F1` 为 `0.0`；两边都为空时三项均为 `None`。汇总批量评测结果时，需要把有效评分数量、报错数量与未定义数量一起统计，避免把缺失值统一填成零。后续的检索与工具调用课程会在这套算式上各自规定评分单位。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `UploadContract` | [eval.py](eval.py) | 继承 `BaseMetric`，按明确条件校验 JSON 结构、字段类型与固定值 |
| `explanation_metric` | [eval.py](eval.py) | 基于 `GEval` 与三档 `Rubric` 评判 `explanation` 的语义完整性 |
| `score` / `set_scores` | [eval.py](eval.py) | 包装指标状态以区分报错与零分，并计算去重后的集合指标 |
| `JudgeModel` | [judge.py](../../eval_course/judge.py) | 继承 `DeepEvalBaseLLM`，通过宿主桥接请求裁判并做 schema 校验 |
| `main` | [code.py](code.py) | 分别记录对照样本或实时 Agent 运行的 `rules` 与 `judge` 结果 |

## 试一下

运行本课评分脚本，对 `cases.jsonl` 中的五条教学对照样本执行规则检查与裁判评分：

```sh
python -m course.e04_scoring.code
```

加上 `--live-agent` 参数则会启动第 2 课的 Agent 读取 `upload.md` 并给出真实回答，两类运行记录会各自保存到独立的 JSON 文件中：

```sh
python -m course.e04_scoring.code --live-agent
```

动手验证四个问题：

1. 对比 `paraphrase` 与 `omission`，看看哪一条换了表述却仍然得满分，哪一条漏掉关键信息后降为 `0.5`。
2. 查看 `plain-text` 的输出，解释为什么它的 `judge` 拿到 `1.0`，而 `rules` 却判为 `0.0`。
3. 设想裁判适配器在请求时抛出 `OSError`，沿着 `score` 函数看返回的字段与有效零分有什么不同。
4. 把 `set_scores` 的预测集合设为空集，观察 `precision` 与 `recall` 的分母各自如何处理。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在我们已经能为单轮回答选定规则判据或语义量表，并把有效零分与接口错误分开。下一步要把视野往前推一环：当 Agent 需要自己去知识库查资料时，怎样追踪检索到了什么、回填了什么，以及模型最后真正看到了什么？

下一课 `e05` 接入只读知识库与 TinyRAG 检索工具，打通从文档分块到 DeepEval `retrieval_context` 的数据链路。
