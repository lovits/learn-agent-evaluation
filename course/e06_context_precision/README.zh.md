# e06: 上下文相关性与排序：有用的资料，排在了哪里？

[e05](../e05_knowledge_context/README.zh.md) → `e06` → [e07](../e07_context_recall/README.zh.md) → … → e16

> *“检索返回了相关内容，还要看有用片段占比有多高、排在前面还是后面；先定清楚相关性判据，再分开看数量与顺序。”*
>
> **评测层：上下文精度与排序。** 固定 TinyRAG 返回的候选片段，用普通精度、列表 AP、RR 与 NDCG 度量排序影响，并用 DeepEval 的 `ContextualPrecisionMetric` 与 `ContextualRelevancyMetric` 对比片段级与陈述级相关性。

## 问题

上一课已经能追踪模型收到的检索上下文。现在向知识库提出一个具体问题：“Atlas 补丁发布前的检查要求 测试命令 发布条件”。

TinyRAG 返回的三条候选里包含发布规范，但也排进了审计日志期限和 API 认证说明。一旦发布规范被挤在列表后面，而上下文长度预算（`context_limit`）又只够放进前两条，模型就会在看到关键依据前截断列表。因此，评价检索列表不能只问“有没有命中”，还得同时弄清两件事：返回的片段里有多少真正有用，以及有用的片段排得有多靠前。

## 解决方案

先冻结 TinyRAG 实际返回的候选列表，依据“能否回答测试命令与发布条件”给每个片段标出 `0` 或 `1` 的二元标签；随后保持内容和标签不变，只移动片段位置或向末尾追加一条干扰文本，用普通精度和排名指标分别计算得分。

![固定标签后分别计算普通精度与列表 AP](https://lovits.github.io/learn-agent-evaluation/diagrams/e06-ranking-flow.svg?v=27768952155e)

再接入 DeepEval 原生的 `ContextualPrecisionMetric` 与 `ContextualRelevancyMetric`，观察模型裁判分别在片段级和陈述级如何打分，并将每条裁决与对应的计数单位一并留档。

![两类 DeepEval 原生指标的评分过程](https://lovits.github.io/learn-agent-evaluation/diagrams/e06-scoring-flow.svg?v=fab93946eccc)

## 工作原理

### 先规定什么叫有用

[cases.jsonl](cases.jsonl) 把直接提供测试命令与发布条件的 `atlas/release.md#0` 标为 `1`，把只写日志期限或认证请求头的 `atlas/logs.md#0` 与 `atlas/auth.md#0` 标为 `0`。相关性判据紧扣“能否支持参考答案”，只要提到了 Atlas 但给不出发布要求，依然算作无用片段。

[prepare](code.py) 先校验知识库文档的 SHA-256 哈希与候选 `chunk_id` 集合，确认语料和命中条目与预先审核的版本一致，再构建四组排序对照：`original`（原序）、`useful_first`（有用项前移）、`useful_last`（有用项后移）以及 `trailing_noise`（前移后在末尾追加构造天气文本）。固定同一批候选与标签后，位置变动对公式的影响就能单独看清。

### 普通精度只数数量，列表 AP 还看位置

设相关标签为 `1`，无关为 `0`。普通精度计算整个列表里相关项的比例，位置精度 `P@i` 则计算前 `i` 位里的相关比例：

```text
precision = 相关片段数 / 返回片段数
P@i       = 前 i 位相关数 / i
```

看一组只有一条相关项的排列对比：

| 标签顺序 | 普通精度 | 相关位置的 `P@i` |
|---|---:|---:|
| `[1,0,0]` | `1/3` | `P@1 = 1` |
| `[0,1,0]` | `1/3` | `P@2 = 1/2` |
| `[0,0,1]` | `1/3` | `P@3 = 1/3` |

三种排法的普通精度都是 `1/3`，完全看不出位置差别。列表平均精度（`list_ap`）只在标签为 `1` 的位置累加 `P@i`，最后除以列表内的相关项总数：

```text
list_ap = Σ(当前位置标签 × P@i) / 本列表相关数
```

[eval.py](eval.py) 中的 `ranking` 直接实现这个递推过程：

```python
for position, label in enumerate(labels, 1):
    cumulative += label
    weighted += label * cumulative / position
```

遇到 `label=0` 时 `weighted` 不增加；遇到 `label=1` 时把截至当前位置的相关比例 `cumulative / position` 加进去，循环结束后再除以 `relevant`。上面三种排法各有一条相关项，因此 `list_ap` 依次为 `1`、`1/2` 和 `1/3`。如果列表里有两条相关项，例如 `[1,0,1]`，第 1 位贡献 `1`，第 3 位贡献 `2/3`，平均后 `list_ap` 为 `(1 + 2/3) / 2 = 5/6`。

### 高 AP 依然可能带着尾部噪声

把 `[1,0,0]` 扩充为 `[1,0,0,0]`，普通精度会从 `1/3` 降到 `1/4`，但 `list_ap` 仍然等于 `1`。因为有用片段前面的排序没有变化，加在末尾的噪声根本不会进入 `list_ap` 的求和项。

还要注意分母范围：`list_ap` 的分母是**当前列表中被判相关的条目数**，代表“已有有用片段排得多靠前”，而知识库里还有没有漏掉未返回的必要证据，它看不出来。哪怕检索器只返回了一条有用片段，列表 AP 也可以拿到满分 `1.0`。

当输入为空列表时，`ranking` 返回 `None`；非空列表但全为 `0` 时，四项排序指标统一记为 `0.0`。这套空值约定与 DeepEval 内部聚合函数的默认行为有所不同，具体差异对照见[源码导读](source_walkthrough.md)。

### 用 ContextualPrecisionMetric 让裁判判定片段有用性

手写标签适合用来隔离排名公式，实际评测则需要模型按问题和参考答案自动判断每个候选片段是否有用。`code.py` 构造样本时填入三项字段：

```python
sample = LLMTestCase(
    input=case["query"],
    expected_output=case["reference"],
    retrieval_context=[p["text"] for p in orders[name]],
)
```

这里只评测检索候选，不触发 Agent 生成回答。当前 DeepEval 版本的 `ContextualPrecisionMetric.measure` 只读取 `input`、`expected_output` 与 `retrieval_context`，因此 `actual_output` 保持为空。

`judge_precision` 调用 `ContextualPrecisionMetric` 让裁判为每个字符串片段给出 `yes` 或 `no` 裁决及理由，再由 SDK 按列表 AP 公式聚合。函数同时校验裁决长度必须等于传入片段数：如果传入 3 段文本只返回 2 条裁决，就会把状态记为 `error` 并置空分数，避免把漏判默认补成 `no`。需要注意，把同一批片段换个顺序再送给 LLM 裁判，模型自身也可能改变个别片段的判断，因此实际评测时应如实保留每次运行的原生裁决。

### 片段相关与陈述相关：两个 DeepEval 指标的单位差

和需要参考答案的 `ContextualPrecisionMetric` 不同，`ContextualRelevancyMetric` 只读问题 `input` 和 `retrieval_context`，不依赖 `expected_output`。它会先把每段检索文本拆成若干陈述，再逐条判断与问题是否相关，最后计算：

```text
相关陈述数 / 全部有效陈述数
```

假设某段检索文本里有 `1` 条有用陈述和 `3` 条无关废话。按片段级判据，因为这段文本包含了答案依据，片段级精度可以给 `1`；但按陈述级比例计算，其余 `3` 条无关陈述全部进入分母，得分立刻变成 `1/4`。而且哪一段拆出的陈述越多，它对最终比例的权重就越大，各文档之间并非等权平均。

两个名字相近的 DeepEval 指标各自关注的颗粒度如下：

| 指标 | 输入依赖与判断单位 | 聚合方式 |
|---|---|---|
| `ContextualPrecisionMetric` | 问题、参考答案与有序上下文；逐片段是否有用 | 相关位置的 `P@i` 均值（列表 AP） |
| `ContextualRelevancyMetric` | 问题与上下文（无需参考答案）；逐条抽取陈述是否相关 | 相关陈述数 / 全部有效陈述数 |

由于判断依据和分母单位都不同，两者数值高低不能直接横向比较，解读分数时必须写明是片段级列表排序还是陈述级含噪比例。

### 另外两个排序视角：RR 与 NDCG

`ranking` 函数一并计算了倒数排名 `rr` 和二元 `ndcg`，方便从不同侧重观察同一份列表：

- `rr` 取第一个相关项出现位置的倒数（多个查询求平均才是 MRR）。`[1,0,1]` 的 `rr` 为 `1.0`，后续位置的变化不会再影响它，而 `list_ap` 会继续计入第 3 位。
- 二元 `ndcg` 先将每个相关位除以位置折损 `log₂(i+1)` 得到 DCG，再除以同一批相关标签全部排在最前面时的理想 DCG。即使不依赖参考答案之外的多级相关性打分，它也能直观反映高相关性内容是否靠前。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `prepare` | [code.py](code.py) | 校验文档哈希与 TinyRAG 候选，构造原序、前移、后移与尾部噪声四组序列 |
| `ranking` | [eval.py](eval.py) | 基于 `0/1` 标签计算 `precision`、`list_ap`、`rr` 与二元 `ndcg` |
| `judge_precision` | [eval.py](eval.py) | 调用 DeepEval `ContextualPrecisionMetric`，核对裁决数量并保存逐片段理由 |
| `judge_relevancy` | [eval.py](eval.py) | 调用 DeepEval `ContextualRelevancyMetric`，保留按片段分组的陈述裁决 |
| `cases.jsonl` | [cases.jsonl](cases.jsonl) | 固定查询、参考答案、来源哈希、片段标签以及尾部干扰文本 |

## 试一下

运行本课脚本，计算四组受控序列的普通精度与排序分数：

```sh
python -m course.e06_context_precision.code
```

加上 `--judge` 参数可调用 DeepEval 的两个原生指标，查看模型裁判给出的逐片段裁决和逐陈述拆解：

```sh
python -m course.e06_context_precision.code --judge
```

动手验证四个问题：

1. 对 `[0,1,0]` 手算每个相关位置的 `P@i` 和 `list_ap`，再分别把 `1` 移到首位和末位对比变化。
2. 对比 `useful_first` 与 `trailing_noise`，解释为什么末尾加入干扰后普通精度下降而 `list_ap` 保持不变。
3. 运行 `--judge` 后查看输出 JSON，分别找出 `ContextualPrecisionMetric` 与 `ContextualRelevancyMetric` 的分母各是什么。
4. 比较 `[1,0,1]` 的 `rr` 与 `list_ap`，说说两项指标各自对列表里哪一部分位置敏感。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在我们已经能度量返回列表的有用比例、陈述纯度以及前后顺序。但哪怕排序和精度都拿到满分，只要检索从一开始就漏掉了某份关键文档，最终回答还是会缺胳膊少腿。

下一课 `e07` 从参考事实清单出发，检验检索上下文到底覆盖了多少必要证据，排查“高精确率却答不全”的召回缺口。
