# Faithfulness 学习卡

Faithfulness 检查回答中的事实声明是否被给定检索上下文支持。
它不等于事实在现实世界中是否正确，也不测检索是否完整或回答是否有用。

本课固定版本中，DeepEval 的 llm 模式默认不惩罚 borderline；
penalize_ambiguous_claims=True 才仅把 yes 算作通过。
Ragas collections 的 Faithfulness 只接受能从上下文直接推断的声明。

参考：
- https://deepeval.com/docs/metrics-faithfulness
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/

精确实现和 commit 见 references/versions.json。
