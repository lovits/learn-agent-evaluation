# e08: 忠实度：回答里的话，资料支持吗？

[e07](../e07_context_recall/README.zh.md) → `e08` → [e09](../e09_answer_quality/README.zh.md) → … → e16

> *“检索找对了资料，生成依然可能编造细节；把回答拆成独立声明，才能逐条核对证据。”*
>
> **评测层：生成忠实度。** 用 DeepEval 的 `FaithfulnessMetric` 抽取资料事实与回答声明，逐条判定支持关系，并区分默认通过率与明确支持比例。

## 问题

知识库原文写着“Atlas 审计日志保留 14 天”，模型的回答却写成“保留 30 天”。即便检索环节已经拿到了正确段落，生成阶段仍然可能改写数字或塞进资料里没有的信息。

另一种常见情况是模型回答“Atlas 仓库使用 GitLab 托管”，而检索资料里压根没提托管平台。这两类出错的性质不同：前者与给定证据直接矛盾，后者缺乏任何证据支撑。只凭肉眼扫一遍整段回答，很容易漏掉混在正确句子里的个别失真细节。

要衡量回答对资料的忠实程度，必须先把复合句拆成可独立验证的声明，再逐条对照送入模型的上下文。

## 解决方案

复用第 5 课保存下来的真实回答与当时送入模型的 `retrieval_context`，再加上三组对照样本（无依据声明、期限矛盾、替换证据）。调用 DeepEval 的 `FaithfulnessMetric`，先从资料抽取 `truths`，再从回答抽取 `claims`，最后逐条给出裁决 `verdicts`，并把这些中间产物随分数一起落盘。

![从实际上下文与回答分别抽取事实和声明，再逐条判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e08-claim-flow.svg?v=a4893fd286ab)

拿到逐条裁决后，先检查声明数与裁决数是否一致，再按两种聚合口径分别计算默认分数与明确支持比例。整个二次聚合直接复用同一批 `verdicts`，无需再发起额外的裁判请求。

![检查声明与裁决数量，再按两种口径聚合](https://lovits.github.io/learn-agent-evaluation/diagrams/e08-scoring-flow.svg?v=1d116c6691d1)

## 工作原理

### 组装样本：锁定当时的回答与证据

打开 [code.py](code.py)，`prepare` 先校验第 5 课记录文件的 SHA-256，确认冻结基线没有被改动，再取出三个字段组装 `LLMTestCase`：

```python
LLMTestCase(
    input=baseline["task"],
    actual_output=baseline["final_answer"],
    retrieval_context=baseline["sample"]["retrieval_context"],
)
```

`retrieval_context` 严格沿用那次运行实际喂给模型的检索片段。忠实度只衡量 `actual_output` 与 `retrieval_context` 之间的一致性，不需要标准答案 `expected_output`。上一课的上下文召回从参考事实出发，检验检索资料够不够全；这一课从回答出发，检验每一句话在资料里有没有落脚点。

### 三步拆解：从上下文抽 truths，从回答抽 claims

“发布前运行 pytest，日志保留 30 天”一句话包含两个独立事实。测试命令有资料支持，不能顺带掩盖日志天数的错误。拆出的每条声明都应保留主体、条件与数值；把“全部检查通过后才能发布”简化成“可以发布”，会直接丢失关键约束，后面的分数聚合也无法补回这种信息损失。

[eval.py](eval.py) 中的 `judge_faithfulness` 直接调用 DeepEval 原生指标，并复用第 4 课的裁判适配器与错误处理：

```python
metric = FaithfulnessMetric(
    model=model, eval_mode="llm", async_mode=False, include_reason=False
)
result = score(metric, sample)
```

同步 `llm` 路径会依次发起三次模型请求：先从 `retrieval_context` 抽取 `truths`，再从 `actual_output` 抽取 `claims`，最后对照 `truths` 逐条裁决 `claims`。设置 `include_reason=False` 只会省去第四次“生成总分解释”的请求，不影响前面三步。

需要注意，`truths` 是模型从上下文提取出来的中间陈述。如果提取阶段漏掉了限定条件或文档来源编号，后续裁决就会失去对应依据，因此中间结果必须和最终分数一起保存下来供复核。

### 裁决标签：支持、矛盾与未支持

自然语言推断（NLI）在这里回答一个具体问题：给定这些 `truths`，能否推出当前这条 `claim`？DeepEval 的判定提示词将结果分成三类：

| 语义关系 | 资料与回答示例 | DeepEval 裁决标签 |
|---|---|---|
| 支持 | 资料与回答均说明日志保留 14 天 | `yes` |
| 矛盾 | 资料写 14 天，回答说 30 天 | `no` |
| 未支持 | 回答说用 GitLab，资料未提托管平台 | `borderline` |

在 DeepEval 的文本判据中，只有与证据直接冲突的声明才判为 `no`；缺乏证据但不直接矛盾、或者表述模糊推测的声明，都会归入 `borderline`。裁判只能依据给定的 `truths` 做出判断，不能用自身常识替回答补全证据。

### 聚合口径：为什么默认满分仍可能包含未支持声明

DeepEval 的 `FaithfulnessMetric` 默认 `penalize_ambiguous_claims=False`，聚合时会把 `yes` 和 `borderline` 一并计入分子：

```text
默认分数     = (yes 数 + borderline 数) / 有效裁决数
明确支持比例 = yes 数 / 有效裁决数
```

以裁决列表 `[yes, yes, borderline]` 为例：默认分数是 `1.0`，而明确支持比例是 `2/3`。看到默认的满分结果，不能直接理解为“每条声明都有资料明文支撑”。

[eval.py](eval.py) 里的 `aggregate` 把这两种口径直接写成显式代码：

```python
passing = {"yes"} if penalize_ambiguous else {"yes", "borderline"}
return sum(label in passing for label in labels) / len(labels)
```

`judge_faithfulness` 返回的 `score` 来自 DeepEval 原生计算；`support_score` 则对同一批 `verdicts` 调用 `aggregate(..., penalize_ambiguous=True)`，只把 `yes` 计入分子，等价于开启 `penalize_ambiguous_claims=True` 后的聚合结果。

这两个参数容易与 `strict_mode` 混淆：`penalize_ambiguous_claims` 决定 `borderline` 算不算通过；`strict_mode` 则是在算出比例之后，把低于阈值的分数直接压成 `0`。本课关闭 `strict_mode`，保留原始比例以便观察细节。

### 证据边界：换了上下文，以及知识库之外的执行声明

[cases.jsonl](cases.jsonl) 中包含两组对照：`contradicted` 让回答说“日志保留 30 天”，对照原始的 14 天资料；`changed_evidence` 保持回答完全不变，只把教学上下文里的“14 天”替换成“30 天”。后者的期限声明会被判为支持，但这只说明它忠于当前喂进去的文本，无法证明它符合现实中的 Atlas 规范。

真实 Agent 的回答里还有另一类语句，例如“已写入并读回 `check.txt`”。知识库里的发布规范只能说明应该运行什么命令，不会记录 Agent 刚才有没有写过文件。由于本课传给 `FaithfulnessMetric` 的 `retrieval_context` 只有知识库片段，这类执行类声明往往会被判为 `borderline`。核验工具执行情况要回到工具轨迹与磁盘产物（第 11、12 课展开），不能仅凭知识库忠实度就断定 Agent 在撒谎。

### 空声明与裁决数量异常

当模型回复“我无法根据现有资料确定”时，回答里可能抽不出任何事实声明。DeepEval 原生在空裁决列表时会默认返回 `1.0`。本课把原生值保留在 `sdk_score` 字段中，同时在对外结果里把 `status` 标为 `not_applicable`，将 `score` 和 `passed` 设为 `None`，避免把无声明回答误读成满分。

同样，如果抽出了三条 `claims` 却只收到两条 `verdicts`，`judge_faithfulness` 会把状态标记为 `error` 并将分数置空。数量一致是最基本的结构对齐，排查问题时仍要顺着 `claims` 与 `verdicts` 核对语义是否对应。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `prepare` | [code.py](code.py) | 校验第 5 课基线哈希，组装冻结回答与三组对照的 `LLMTestCase` |
| `aggregate` | [eval.py](eval.py) | 按默认口径或严格支持口径计算 `yes`/`no`/`borderline` 的通过比例 |
| `judge_faithfulness` | [eval.py](eval.py) | 调用 DeepEval `FaithfulnessMetric`，保存 `truths`、`claims`、`verdicts` 与 `support_score` |
| `cases.jsonl` | [cases.jsonl](cases.jsonl) | 定义冻结基线引用与 `unmentioned`、`contradicted`、`changed_evidence` 三组对照 |

## 试一下

运行本课脚本，先看固定标签在两种聚合口径下的计算结果：

```sh
python -m course.e08_faithfulness.code
```

动手验证四个问题：

1. 对照 `unmentioned` 与 `contradicted`，说说“没有证据支持”和“与证据直接矛盾”在裁决标签上有什么区别。
2. 对比 `contradicted` 和 `changed_evidence`，回答文本一字未改，为什么忠实度结果反过来了？
3. 加上 `--judge` 参数运行真实裁判，顺着输出文件里的 `truths`、`claims` 和 `verdicts` 核对最终分数的由来。
4. 读一遍 `frozen_agent` 的拆解结果，把其中的知识类声明和工具执行类声明分开，指出后者应该去哪里查证。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

即使回答里的每一句话都忠于检索资料，它依然可能答非所问，或者漏掉用户关心的关键要求。下一课 `e09` 把切题性、事实覆盖与证据不足时的拒答策略拆开来评。
