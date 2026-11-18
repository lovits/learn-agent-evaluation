# e03: 题目从哪里来，参考凭什么可信？

[e02](../e02_samples/README.zh.md) → `e03` → [e04](../e04_scoring/README.zh.md) → … → e16

> 先把题目和参考核对好，再让 Agent 作答。

## 问题

第二课已经能保存一次运行。接下来可以多跑几道题，但题目该怎么选？

资料里说，上传接口的 token 要放在 `X-Project-Token`。我们写一道“token 放哪个头”的题，再换五种说法，得到六道题。它们仍在问同一个事实。遇到超大文件，或者用户问资料没有说明的账单货币，Agent 会怎样，题目还没有覆盖。

参考答案也可能出错。模型生成的“最大文件为 10 MiB”看着像一条完整规则，原文却写着 `1048576 bytes`。用错参考，后面评分写得再认真也会判错。

## 解决方案

先从少量事实写种子题，再让模型补充候选。每道题保留资料版本、原文证据和审核记录；审核后去重，按题族固定划分。

![从资料到审核后的评测集](https://lovits.github.io/learn-agent-evaluation/diagrams/e03-dataset-flow.svg?v=d8998939c132)

题目与参考先进入 DeepEval 的 `Golden`。复用第二课 Agent 作答后，才得到实际输出，组成后续评分需要的样本。

![参考与实际输出进入同一评测样本](https://lovits.github.io/learn-agent-evaluation/diagrams/e03-sample-flow.svg?v=d97fcdf3f89c)

## 工作原理

### 先分清题目、参考和实际输出

[code.py](code.py) 的 `dataset` 把审核后的数据放入 Golden，下面省略题号等 metadata：

```python
Golden(
    input=row["task"],
    expected_output=row["reference"],
    context=[row["context"]],
    source_file=row["source"]["path"],
)
```

`input` 是任务，`expected_output` 是事先核对的参考。`context` 是参考所依据的资料。本课还没有检索，所以这里没有实际的 `retrieval_context`。

此时 `actual_output` 为空。它要等 Agent 真正运行后填写，不能拿参考答案补进去。

### 用题型补上盲区

本课资料只说明上传认证和大小限制。围绕这些事实，题目可以这样安排：

| 题型 | 问什么 | 观察什么 |
|---|---|---|
| 正常 | token 放在哪个请求头 | 能否找到明确事实 |
| 错误前提 | 只用 Authorization 头是否符合要求 | 能否纠正错误前提 |
| 边界 | 文件为 1048577 字节时会怎样 | 能否应用大小限制 |
| 缺证据 | 账单使用哪种货币 | 能否说明资料没有提供答案 |

题型从要观察的行为出发。实际项目还要根据用户任务调整比例，这个小例子只用来说明怎样补题。

### 生成后，先保持待审核

[generate.py](generate.py) 根据资料生成候选，再补上来源版本和审核状态：

```python
review={"decision": "pending", "reviewer": None, "reason": "Await source review"}
```

生成问题的模型也可能同时生成错误参考。审核者需要重新读原文，核对题意和答案，再明确写下接受或拒绝的原因。模型给自己的质量分不能替代这一步。

### 资料更新，旧审核需要重看

`curate` 只接受有审核者的已批准候选，再核对来源：

```python
if doc["sha256"] != source["sha256"]:
    reason = "source_changed"
```

哈希标记的是审核时读过的版本。资料变化以后，原来的引文和参考要重新核对。

可回答的题还要提供资料中确实存在的引文：

```python
elif candidate["answerable"] and (
    not candidate["quote"] or candidate["quote"] not in doc["text"]
):
    reason = "missing_evidence"
```

引文存在，只说明文字能在原文找到。它是否支持参考答案，仍要审核。缺证据题可以没有引文，但题目必须把范围限定为“根据所给资料回答”。

### 题意决定去重，题族决定划分

“token 放哪个头”和“上传用哪个 token header”字面不同，题意相同。本课审核时为它们标记同一组键：

```python
key = (candidate["family"], candidate["intent"])
```

`family` 是共享事实的题族，`intent` 是具体题意。`seen` 中已经有这个键，就保留重复原因，不再加入。语义判断来自审核后的标签；标签填错，程序也会误删或漏删。源码导读会说明大规模近邻检索与这份小例子的区别。

划分时，把同一题族全部放在同一侧：

```python
"holdout" if candidate["family"] in HOLDOUT_FAMILIES else "development"
```

大小上限与超限状态都属于 `upload-size`。若前一道放开发集、后一道放留出集，调试时就可能间接碰到留出题所依赖的规则。本课把整个题族留出，并检查两侧题族是否相交。

开发集用于修改 Agent 和评分标准。留出集用于最后比较；看过结果又据此调参，就消耗了它的独立性。

## 本课变化

| 部分 | 这一课做什么 |
|---|---|
| Agent | 继续复用第二课循环和工具 |
| 数据 | 增加来源、审核、题意去重与题族划分 |
| DeepEval 样本 | 先建 Golden，运行后再填写实际回答 |

[experiment.py](experiment.py) 把资料复制到新的工作目录后调用原有循环。参考与实际回答在样本中分别保存。本课检查数据是否整理妥当，答案怎样判分留到下一课。

## 试一下

```sh
python -m course.e03_datasets.code
```

1. 比较 `auth-header` 和 `auth-paraphrase`。为什么文字不同仍算重复？
2. 把 `size-limit` 单独移入开发集，看看题族检查为什么不再通过。
3. 修改资料后重新整理。旧哈希能否继续代表这份资料？
4. 根据资料再补一道题。它测的是新行为，还是已有题的改写？

候选生成用 `python -m course.e03_datasets.generate`；它不会自动批准候选。用 `python -m course.e03_datasets.experiment --case auth-header` 可以跟随一条已审核题，查看参考和真实回答各从哪里来。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

题目、参考和真实回答已经分开保存。下一课开始选择判据：哪些条件能直接检查，哪些需要 LLM 理解含义，再把裁决汇总成分数。
