# e06 源码导读：同一个“精度”，分母可能不同

[教材](README.zh.md) · [排序算式](eval.py) · [TinyRAG 与评分入口](code.py)

## 本课调用链

`prepare` 复用上一课的 TinyRAG，取得本次候选。题目把发布规范标为有用，认证、日志标为不能提供所需命令或发布条件。这是课程编写助手核对的教学标签，不是独立人工金标准；文档哈希或候选集合变化，先重新审核，程序不默默给新候选贴标签。

`main` 冻结这批候选，生成原序、有用项前移、有用项后移和末尾加噪声四组条件。后三组是受控改动，不声称 TinyRAG 真正检索出了这些顺序。天气噪声也明确标为人工构造。

`ranking` 用同一组固定标签解释聚合。加 `--judge` 才实际运行 DeepEval 的两个原生指标，继续复用第四课 `JudgeModel` 和评分状态包装。全程不再运行 Agent 或生成回答，也不接入 Ragas 评分。

## 排序算式

令第 i 个候选的标签为 rᵢ，相关为 1，否则为 0。R 是本列表的相关数，K 是返回数：

```text
P@i       = 前 i 位相关数 / i
precision = R / K
list_ap   = Σ(rᵢ × P@i) / R
RR        = 1 / 第一个相关项的位置
DCG       = Σ(rᵢ / log₂(i+1))
NDCG      = DCG / 同一批标签理想重排后的 DCG
```

本课只接受二元标签，因此 NDCG 的增益取 rᵢ；不引入多级相关度。RR 是一个查询的值，多个查询的 RR 均值才叫 MRR。`ranking` 没有调用另一个评测框架，只展开当前算式；NDCG 的折扣与归一化可对照 [scikit-learn 官方说明](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)。

`list_ap` 的分母是当前列表中已判相关的项数，不是整个知识库里应当找回的相关总数。它不能代替召回率。只保留一条有用资料，或者把噪声放在所有有用项之后，都可能取得很高的列表 AP。

空列表在本课算式中返回 `None`；非空而全不相关时，四项均为 0。这是显式约定。下面 SDK 聚合函数的空值约定另行说明，不能把二者不加区分地合并。

## DeepEval：Contextual Precision

固定提交：[34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)。概念参考 [Contextual Precision](https://deepeval.com/docs/metrics-contextual-precision)。

沿 [contextual_precision.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/contextual_precision.py) 阅读：

1. `_required_params` 为 input、retrieval_context、expected_output。`measure` 核对输入，再按 llm 模式调用 `_generate_verdicts`。本课不走其他裁判模式。
2. prompt 输入为问题、参考答案和有序候选，要求判断各候选是否有助于得到参考答案。[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/schema.py) 保存 yes/no 与 reason。模型负责这一步语义判断。
3. `_calculate_score` 按 yes 转为 1，累积相关数量，在每个相关位置加 P@i，最后除以列表内相关数。没有裁决或没有相关裁决时，该聚合函数返回 0；实际调用还要先经过样本校验。
4. strict 模式会将低于阈值的分数压为 0；本课关闭它，保留原始聚合结果。阈值判断仍与分数本身分开。

注意 `_group_retrieval_contexts`：字符串各自作为一个单位；若传入 `RetrievedContextData`，同一 source 会合并再判断。本课明确只传字符串片段，并检查裁决数量等于片段数量。换成分组输入后，需要重新规定对齐方式，不能继续按原片段数解释。

本课原序和前移序各实际调用一次裁判；模型可能因为顺序改变而改变判定。所以受控聚合使用固定教学标签，原生评分则保存每次自己的裁决，不能假定两次标签必定相同。

## DeepEval：Contextual Relevancy

[contextual_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) 的必需字段是 input、retrieval_context，不依赖参考答案。概念见 [Contextual Relevancy](https://deepeval.com/docs/metrics-contextual-relevancy)。

`measure` 对每个片段调用 `_generate_verdicts`。提示词要求先提取高层陈述，再判断每条陈述与问题的相关性。结果保留 statement、yes/no 和可选 reason。`_calculate_score` 将各片段的裁决展平，交给 `score_qag_verdicts`，按 yes 数除以全部有效裁决数，空裁决约定为 0。

因此，它不是“相关片段数 / 片段数”，也不是“先算每片段相关比例再等权平均”。一个片段若被拆出更多陈述，会对总分产生更多贡献。当前陈述怎样拆分、哪些算相关，都带有裁判判断，必须查看原始裁决。

[utils/qag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 对严格 schema 和宽松 JSON 路径分别处理：前者限制词表，后者归一化词表并可能丢弃无效项。本课模型适配器先做 schema 校验，Precision 还检查数量；接口、格式或对齐失败保持 error 与空分数，不冒充有效零分。

官网用法通常连同 actual_output 展示样本。本课直接调用这两个指标的 measure；固定实现不读取该字段，已用原生 SDK 检查 `actual_output=None` 的路径。这不表示任意评测入口都允许缺少回答；本课只评价检索器，没有编造回答凑字段。

## Ragas：Context Precision 的判断与分母

固定提交：[8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)。

现代 collections 的 [context_precision/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_precision/metric.py) 中，`ContextPrecisionWithReference.ascore` 对每条 context 单独调用模型，以问题、context 和 reference 组成输入；收集 verdict 后调用 `_calculate_average_precision`。

聚合用累计相关数除以当前位置，在相关位置累加，再除以相关数加极小量。当前列表没有相关项时得到 0。概念上接近本课列表 AP，但不能把框架分数直接当成同一次裁决：模型提示词、逐条或整组判断、类型处理和数值细节仍不同。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_precision/util.py) 的输出是 reason 与整数 verdict，提示词要求 0/1；整数类型本身不等于运行时已经限制为二元值。读源码时需要同时核对 schema、裁决和聚合。

`ContextPrecisionWithoutReference`（也由 `ContextUtilization` 包装）把比较对象换成实际 response，仍计算同类 AP。它衡量的是对该回答的用处，不能据此单独证明回答本身正确。本课只读这些原理，没有 Ragas 调用或第二套实际评分。
