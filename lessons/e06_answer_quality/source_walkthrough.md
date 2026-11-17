# e06 源码导读：同一个回答，几个比较方向

[教材](README.zh.md) · [手算函数](code.py) · [指标入口](eval.py)

## DeepEval 先判断是否切题

[Answer Relevancy 文档](https://deepeval.com/docs/metrics-answer-relevancy) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py)

LLM 路径为 `prepare_measure → _generate_statements → _generate_verdicts → _calculate_score`。必要字段是问题和回答，yes 与 borderline 计通过，空裁决默认1。没有 reference，它不会独立核验限额。

[正确性指南](https://deepeval.com/guides/guides-answer-correctness-metric)使用 G-Eval 定义业务标准。本课把 reference 版本、answerable 和 policy 放进 `EXPECTED_OUTPUT`，与 `INPUT/ACTUAL_OUTPUT` 一起评分。指令覆盖和拒答标准来自业务定义。

## Ragas FactualCorrectness 的两个方向

[文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/factual_correctness/metric.py)

```text
response → 声明拆解 → 用 reference 做 NLI → TP、FP
reference → 声明拆解 → 用 response 做 NLI → FN
                                ↓
                     precision / recall / F-beta
```

`mode="precision"` 不做反向检查。其余模式交换文本继续。`atomicity/coverage` 控制拆解提示，实际粒度仍由模型决定。

固定计数沿用正向 TP：若正向有3项支持，反向有1项不支持，recall 是3/4，未必等于反向支持比例。分母加极小量，结果保留两位小数；空输入在入口报错，全空拆解可得到0。

## AnswerCorrectness 采用声明分类

[文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_correctness/) · [metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_correctness/metric.py) · [分类 schema](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_correctness/util.py)

先分别调用 `StatementGeneratorPrompt`，再由 `CorrectnessClassifierPrompt` 输出带理由的 TP/FP/FN 列表。它没有直接复用上一个指标的双向 NLI 计数。

默认 `weights=[0.75,0.25]`，经加权平均混合事实 F-beta 和嵌入余弦。需要相似度却没有 embeddings 时会报错。本课设 `[1,0]` 跳过嵌入。

任一侧无声明时，固定实现直接令事实部分为1；零向量相似度有显式保护。这些算法分支不能替代拒答政策。

## 相关性与相似度的差别

[AnswerRelevancy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_relevancy/metric.py) 从回答反推多个问题，与原问题计算平均余弦；固定版本只有全部有效问题都标为 noncommittal 时才乘0，没有有效问题则返回0。[概念说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)可与源码对照。

[SemanticSimilarity](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/_semantic_similarity.py) 直接比较回答与 reference 的嵌入。这个实现没有同样的零向量保护，余弦也不能一概假定为0至1。`code.py` 的二维向量只用于手算，不承担语义编码。

## 输入怎样影响结论

`reference.json` 绑定版本和政策。`teaching_expectation` 不送给裁判；旧 Agent 产物按原版本评价。参考没有写出的信息只能叫“不受当前参考支持”，不自动等于外部事实为假。

阶段记录要保留声明、NLI 方向与原始理由。它们能区分参考写得不完整、拆解粒度改变和真正的事实错误。
