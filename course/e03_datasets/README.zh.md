# e03: 评测集与参考：题目从哪里来，参考凭什么可信？

[e02](../e02_samples/README.zh.md) → `e03` → [e04](../e04_scoring/README.zh.md) → … → e16

> *“先把题目和参考核对清楚，再让 Agent 作答；参考错了，后面的评分再精细也会判反。”*
>
> **评测层：评测集与参考。** 用来源哈希、原文引文、审核记录与题族划分整理题目，构建 DeepEval 的 `Golden` 与 `EvaluationDataset`。

## 问题

第二课已经能把一次运行保存为标准样本。接下来要批量跑题，马上会遇到两个现实问题：题该怎么挑，参考凭什么可信？

假设资料说明上传接口的 token 要放在 `X-Project-Token` 请求头里。围绕这一条写一道题，再换五种问法改写，表面上凑出了六道题，其实都在测同一个事实；遇到超大文件怎么办、用户问到资料里没写的账单货币时 Agent 会不会瞎编，这些关键场景依然是空白。

参考答案本身也会出问题。模型合成的一条参考写着“最大文件为 10 MiB”，读起来很完整，但原文写的是 `1048576 bytes`。如果参考在入库前没有经过原文核对，后续无论换什么评分器，都会把正确答案判成错误。

## 解决方案

先围绕核心行为写少量种子题，再让模型补充候选。每条候选都绑定资料版本哈希、原文引文和审核状态；审核通过后按题意去重、按题族切分开发集与留出集，再装进 DeepEval 的 `Golden` 和 `EvaluationDataset`。

![从资料到审核后的评测集](https://lovits.github.io/learn-agent-evaluation/diagrams/e03-dataset-flow.svg?v=d8998939c132)

题目与参考先以 `Golden` 形态独立存在；复用第二课的 Agent 跑出实际回答后，才与参考合并成可供评分的 `LLMTestCase`：

![参考与实际输出进入同一评测样本](https://lovits.github.io/learn-agent-evaluation/diagrams/e03-sample-flow.svg?v=d97fcdf3f89c)

## 工作原理

### 分清题目、参考和实际输出

[code.py](code.py) 中的 `dataset` 函数把整理好的记录转换为 DeepEval 的 `Golden`（下方省略题号等 metadata 字段）：

```python
Golden(
    input=row["task"],
    expected_output=row["reference"],
    context=[row["context"]],
    source_file=row["source"]["path"],
)
```

`input` 是任务，`expected_output` 是核对过的参考答案，`context` 是参考所依据的原文资料。由于本课还没有接入检索环节，这里不填写 `retrieval_context`。

此时 `actual_output` 保持为空，留待 Agent 真实运行之后再填入，避免参考答案和实际输出混为一谈。

### 按待测行为设计题型

本课资料包含上传认证和文件大小限制两部分规则。围绕想观察的 Agent 行为，可以把题目拆成四类：

| 题型 | 示例问题 | 观察重点 |
|---|---|---|
| 正常 | token 放在哪个请求头 | 能否准确提取明确事实 |
| 错误前提 | 只用 `Authorization` 头是否符合要求 | 能否识别并纠正错误前提 |
| 边界 | 文件为 `1048577` 字节时会怎样 | 能否正确应用大小上限 |
| 缺证据 | 账单使用哪种货币 | 资料未提及时能否明确拒答 |

从行为维度出题，能避免把题库堆满同义改写。实际业务里再按线上问题分布调整四类题型的比例即可。

### 候选生成后先进入待审核状态

[generate.py](generate.py) 根据资料调用模型生成候选题目，同时自动补上来源版本与待审核标记：

```python
review={"decision": "pending", "reviewer": None, "reason": "Await source review"}
```

生成题目的模型同样可能写出偏差参考。候选入库前必须对照原文核对题意与答案，写下接受或拒绝的理由，模型自评分数不能替代审核步骤。

### 用来源哈希和原文引文拦截过期参考

`curate` 只接纳带有审核人签名的已批准候选，并校验来源文档版本：

```python
if doc["sha256"] != source["sha256"]:
    reason = "source_changed"
```

哈希值锁定的是审核当时读到的资料版本。原文一旦更新，旧哈希失效，相关题目的引文与参考都需要重新核对。

对于可回答的题目，`curate` 还会校验引文是否真实存在于当前原文中：

```python
elif candidate["answerable"] and (
    not candidate["quote"] or candidate["quote"] not in doc["text"]
):
    reason = "missing_evidence"
```

引文存在保证了文字确有出处，而引文能否推出参考答案仍由审核环节把关。缺证据题允许没有引文，但题干必须明确限定回答范围为“根据所给资料”。

### 按题意去重，按题族划分

“token 放哪个头”和“上传用哪个 token header”字面不同，测的是同一个知识点。审核时为它们标上相同的去重键：

```python
key = (candidate["family"], candidate["intent"])
```

`family` 代表共享同一组规则的题族，`intent` 代表具体题意。只要 `seen` 里已经出现过相同的键，后续重复候选就会被记为 `duplicate_intent` 并剔除。

划分数据集时，把同一题族的所有题目固定放在同一侧：

```python
"holdout" if candidate["family"] in HOLDOUT_FAMILIES else "development"
```

大小上限和超限状态码都属于 `upload-size` 题族。如果一道放进开发集、另一道放进留出集，调优开发集时就会间接接触留出题依赖的规则。按题族整体切分并检查两侧题族不相交，才能守住留出集的独立性：开发集用于迭代 Agent 和评分标准，留出集留到最终对比时再看。

## 本课变化

| 部分 | 这一课做什么 |
|---|---|
| Agent | 继续复用第二课的循环与文件工具 |
| 评测数据 | 增加来源哈希、原文引文、审核状态、题意去重与题族划分 |
| DeepEval 样本 | 先构造 `Golden` 与 `EvaluationDataset`，运行后再填入 `actual_output` |

[experiment.py](experiment.py) 把资料复制到干净的工作目录后调用原有循环，把参考答案和真实运行结果分别保存在样本的不同字段里。本课把数据整理与结构校验做扎实，答案质量的打分方法在下一课展开。

## 试一下

运行本课的数据整理与校验脚本：

```sh
python -m course.e03_datasets.code
```

动手验证四个问题：

1. 对比 `auth-header` 和 `auth-paraphrase`，看看两道文字不同的题为什么会被判为重复。
2. 试着把 `size-limit` 单独移到开发集，观察 `check_dataset` 为什么报错。
3. 改动资料里的一个数字后重新运行整理脚本，看看旧哈希为什么会触发 `source_changed`。
4. 依据这份资料自己补一道新题，判断它测的是新行为还是已有题目的同义改写。

执行 `python -m course.e03_datasets.generate` 可以用模型生成待审核候选；执行 `python -m course.e03_datasets.experiment --case auth-header` 可以跑通一条已审核题目，查看参考答案和真实输出分别落在样本的哪个位置。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

题目、参考和实际运行输出已经各就各位。下一步要解决的是如何给回答打分：哪些条件可以直接用代码校验，哪些语义判断需要交给 LLM 裁判，以及怎样把多个裁决聚合成稳定的分数。

下一课 `e04` 引入确定性规则、LLM-as-a-Judge 与 DeepEval `GEval`，建立完整的评分链路。
