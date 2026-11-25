# e06 源码导读：同一个“精度”，分母可能不同

[教材](README.zh.md) · [排序算式](eval.py) · [TinyRAG 与评分入口](code.py)

## 本课调用链

[code.py](code.py) 中的 `prepare` 先校验 [cases.jsonl](cases.jsonl) 里记录的文档 SHA-256，再调用第 5 课的 TinyRAG `retrieve` 取得 `limit=3` 条候选，确认命中的 `chunk_id` 集合与标注键一致后冻结该列表。基于这批固定候选，`prepare` 构造出 `original`、`useful_first`、`useful_last` 以及在末尾追加构造天气文本 `constructed/weather` 的 `trailing_noise` 四组序列。

`main` 先对四组序列的固定标签运行 `ranking`，观察同一批标签在不同位置下的数学表现。传入 `--judge` 参数后，复用第 4 课的 `JudgeModel` 与 `score` 包装函数，依次调用 DeepEval 原生的 `ContextualPrecisionMetric`（测量 `original` 与 `useful_first`）和 `ContextualRelevancyMetric`（测量 `original` 的三条检索片段），并把原始返回与裁决结果一起写入报告。

## 排序算式

设第 `i` 个候选片段的二元相关性标签为 `rᵢ`（`1` 为有用，`0` 为无用），`R` 为列表内相关片段总数，`K` 为返回列表长度：

```text
P@i       = 前 i 位相关数 / i
precision = R / K
list_ap   = Σ(rᵢ × P@i) / R
RR        = 1 / 第一个相关项的位置
DCG       = Σ(rᵢ / log₂(i+1))
NDCG      = DCG / 同一批标签理想重排后的 DCG
```

`ranking` 只接受整型 `0` 或 `1` 作为标签，在纯 Python 中直接完成计算；其中的二元折损与归一化定义，对应 [scikit-learn `ndcg_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html) 在相关性仅取 `0/1` 时的情形。需要留意的是，`RR` 针对单个查询计算，对多条查询求 `RR` 的平均值才是 MRR。

`list_ap` 的分母是当前列表内被判相关的项数 `R`，而非知识库里应该找回的全部证据数，因此不能用来替代召回率。当输入为空列表时，`ranking` 对四项指标统一返回 `None`；列表非空但全部标签为 `0` 时，四项均返回 `0.0`。

## DeepEval：Contextual Precision

本课对应 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念文档见 [Contextual Precision](https://deepeval.com/docs/metrics-contextual-precision)。

沿着 [contextual_precision.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/contextual_precision.py) 跟踪同步 `llm` 路径：

1. `_required_params` 声明所需字段为 `input`、`retrieval_context` 与 `expected_output`。`measure` 校验样本字段后进入 `_generate_verdicts`。
2. 提示词把问题、参考答案和有序检索上下文交给裁判模型，要求逐个节点判断它是否有助于得出参考答案。[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/schema.py) 为每个节点保存 `yes`/`no` 裁决与 `reason`。
3. `_calculate_score` 把 `yes` 视为 `1`，沿位置累计命中数与 `P@i`，再除以列表内的 `yes` 总数；当裁决为空或全部为 `no` 时，内部聚合函数返回 `0`。
4. 开启 `strict_mode` 会把低于阈值的分数压成 `0`；本课保持关闭，保留原始浮点比例并与 `threshold` 比较分开记录。

源码中的 `_group_retrieval_contexts` 会区分输入类型：传入纯字符串列表时，每条字符串单独作为一个判断单元；如果传入 `RetrievedContextData` 并带有相同来源标识，则会按来源合并后再判断。本课在 `judge_precision` 中显式传入字符串列表，并强制检查 `len(verdicts) == len(sample.retrieval_context)`，裁决缺条时直接记为对齐错误。若未来改用分组上下文对象，对齐校验方式也需要相应调整。

由于每次重排都会重新发起模型请求，模型在另一份排序下可能给出不同的逐项裁决。因此本课用固定教学标签单独验证算式，而在原生指标中如实保存每次请求返回的裁决。

## DeepEval：Contextual Relevancy

[contextual_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) 的必需字段只有 `input` 和 `retrieval_context`，不需要参考答案，概念说明见 [Contextual Relevancy](https://deepeval.com/docs/metrics-contextual-relevancy)。

`measure` 针对每条上下文片段分别调用 `_generate_verdicts`，提示词指示模型先从片段中提取高层陈述（`statement`），再逐条判断该陈述与问题是否相关，输出 `statement`、`yes`/`no` 和可选 `reason`。随后 `_calculate_score` 把所有片段拆出的裁决列表展平，送入 [utils/qag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 的 `score_qag_verdicts`，用 `yes` 陈述数除以全部有效裁决数（无裁决时返回 `0`）。

这也决定了 `ContextualRelevancyMetric` 的分母是“全部抽取出来的陈述数”，既不同于片段总数，也不是各片段相关比例的简单平均。一个片段被拆出的陈述越多，在最终得分里占的比重就越大。审查得分时，需要结合 `statements_by_context` 核对陈述拆分是否合理。

在 `utils/qag.py` 中，严格 schema 路径会约束裁决枚举值，宽松 JSON 解析则会在归一化后丢弃无效项。本课通过 `JudgeModel` 在返回层先执行 Pydantic schema 校验，`judge_precision` 还追加条数校验，确保任何格式错误或数量不对齐都进入 `status="error"` 并置空分数。

在直接调用这两个指标的 `measure` 方法时，不填 `actual_output`（保持为 `None`）即可通过参数校验；如果通过同时要求回答字段的端到端 `evaluate(...)` 入口运行，仍需按该入口的参数规范补齐样本字段。

[样本与评测记录](assessment.md)
