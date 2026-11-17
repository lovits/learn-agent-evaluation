# e07: 资料都相关，为什么还答不全？

[e06](../e06_context_precision/README.zh.md) → `e07` → [e08](../../docs/curriculum.md#08-回答对上下文的忠实度) → … → e16

> 先列出必要事实，再检查哪些证据还没找到。

## 问题

Atlas 的问题多了一项：发布前运行什么检查、满足什么条件才能发布，审计日志又保留多久？

发布规范能回答前两项。只返回这份资料，内容完全相关，却找不到日志期限。上一课的精度和排序都看着返回列表；召回还需要一份清单，说明列表之外有没有漏掉必要内容。

## 解决方案

把参考拆成明确的事实，为每条事实注明证据来源。复用 TinyRAG 的候选，分别保留完整资料、移除日志资料，再检查覆盖情况。

![从参考事实对照实际上下文，指出覆盖与遗漏](https://lovits.github.io/learn-agent-evaluation/diagrams/e07-coverage-flow.png)

已知来源映射适合手算和定位。需要判断语义支持时，再把参考与上下文交给 DeepEval 的 Contextual Recall。

![DeepEval 逐参考句判断归因并汇总召回](https://lovits.github.io/learn-agent-evaluation/diagrams/e07-scoring-flow.png)

## 工作原理

### 先写出应该找到什么

[样本](cases.jsonl) 给出三条参考事实。这是课程构造、由编写助手核对的教学标注，不是独立人工金标准。

| 事实 | 必要内容 | 来源 |
|---|---|---|
| check_command | 发布前在根目录运行 `python -m pytest -q` | release.md |
| release_gate | 全部检查通过才能发布，失败先修复 | release.md |
| log_days | 审计日志保留 14 天 | logs.md |

每条参考都要能回答问题的一部分，并能追到资料。如果参考遗漏日志期限，后面的召回检查也不会主动补上这项要求。

[prepare](code.py) 核对来源哈希，再冻结一次真实检索取得的候选。从中选出两份必要资料是教学控制条件，不声称 TinyRAG 自动过滤掉了其他内容。移除日志时只改上下文，参考保持三条。

### 数文档，还是数事实

设 required 是必要项目，found 是实际找到的项目：

```python
def coverage(required, found):
    required, found = set(required), set(found)
    return len(required & found) / len(required) if required else None
```

交集给出已覆盖的必要项目，分母始终来自 required。重复找到同一项目不多算一次，无关项目不增加覆盖。

单位可以是文档 ID，也可以是参考事实 ID：

```text
文档召回 = 找到的必要文档数 / 全部必要文档数
事实召回 = 覆盖的参考事实数 / 全部参考事实数
```

手算一个例子：只留下发布规范。两份必要文档找到了 1 份，所以文档召回是 1/2；三条事实覆盖了命令和发布条件，所以事实召回是 2/3。同一份文档承载了两条事实，两种口径自然有不同权重。

这时文档精度仍为 1：返回的唯一文档确实有用。精度没有检查未返回的日志资料，因此高精度不能保证高召回。

### 路径命中为什么能代表事实覆盖

本课的两份固定资料都短于一个分块，且经过逐条核对，才可以用来源路径查表：

```python
paths = {p["path"] for p in parts}
covered = [f["id"] for f in facts if f["source"] in paths]
```

[summarize](code.py) 同时保存 covered 和 missing，后者直接写出缺少的事实。

这个查表方法只适用于当前教学映射。长文档被切成多个片段时，命中某个路径不代表找到了那条事实。需要把标注细化到证据片段，或根据实际片段做语义归因。

### DeepEval 判断的是参考能否归因

构造样本时，把参考事实组成独立句子：

```python
sample = LLMTestCase(
    input=case["query"],
    expected_output="\n".join(f["text"] for f in facts),
    retrieval_context=[p["text"] for p in parts],
)
```

本课评价已固定的检索上下文，不重新运行 Agent 生成回答。固定版本的 `ContextualRecallMetric.measure` 不读取 actual_output，所以该字段留空。

[judge_recall](eval.py) 调用原生指标，复用第四课的裁判适配器和错误处理：

```python
metric = ContextualRecallMetric(
    model=model, eval_mode="llm", async_mode=False, include_reason=False
)
result = score(metric, sample)
```

提示词要求对每个参考句给 yes/no：能从上下文归因则 yes，否则 no。SDK 再计算：

```text
Contextual Recall = yes 数 / 全部有效裁决数
```

裁判负责判断支持关系，除法由代码完成。`include_reason=False` 省去额外的总分解释调用，逐项理由仍保留。

参考句与原子事实也不完全相同。一句若合并了命令、条件和期限，模型如何处理部分支持就会影响分数。写参考时尽量拆清事实，再读实际裁决，不能把裁决数量自动当成事实数量。

Ragas 的 Context Recall 也从 reference 出发，输出拆出的 statement、归因标记和理由，再求归因比例。本课只读它的原理与源码，不重复调用另一套框架。[源码导读](source_walkthrough.md)展开两者的单位和空值约定。

### 参考变短，分母也变了

仍只留下发布规范，却从参考中删掉日志事实。现在清单只要求命令和发布条件，2/2 就是满覆盖。

检索没有改善，评分标准变了。比较两个版本时，应固定参考事实；审核数据时，也要对照用户问题检查参考是否完整。参考中额外写入无依据的事实，同样会把低分归错原因。

### 空参考不能算满分

没有任何必要项目时，`coverage` 返回 None；存在必要项目但一个没找到时，才返回 0。

语义评分先拒绝空白参考。裁判没有返回任何裁决时，本课也记为评分错误，分数为空；有裁决而全部为 no，才是有效零分。不能把分母缺失或接口错误解释为检索能力差。

## 本课变化

复用已有 Agent 和 TinyRAG，不增加工具。新增参考事实与来源映射、文档和事实两种覆盖计算，以及 DeepEval 原生归因。原始候选、受控上下文、参考与裁决分开保存。

## 试一下

```sh
python -m course.e07_context_recall.code
```

1. 找到 missing_logs 的 missing，指出具体漏了哪条证据。
2. 比较文档召回与事实召回，解释两个分母。
3. 比较 missing_logs 和 incomplete_reference：上下文相同，评价标准变了哪里？
4. 加 `--judge` 查看实际归因理由，核对裁判拆出了几条判断。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

必要资料到齐以后，还要检查回答有没有忠实使用它们。下一课从实际回答出发，判断每条声明能否得到上下文支持。
