# e05 源码导读：拆句、裁决、聚合

[教材](README.zh.md) · [证据身份](code.py) · [评测入口](eval.py)

## 输入先绑定当次证据

`eval.py` 从已有运行中的 `search_knowledge` 事件取得命中文档，连同回答一起组成样本。教学构造回答和实际产物使用明确来源标记；人工 annotation 不传给裁判。

`evidence_key` 按文档 ID 与 SHA-256 列表生成身份，列表顺序也参与计算。它用于版本比较，不独立提供防篡改证明。

## DeepEval 的主链

[Faithfulness 文档](https://deepeval.com/docs/metrics-faithfulness) · [faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)

```text
prepare_measure
  → _generate_truths(retrieval_context)
  → _generate_claims(actual_output)
  → _generate_verdicts(claims, truths)
  → _calculate_score
```

输入要求 `INPUT/ACTUAL_OUTPUT/RETRIEVAL_CONTEXT`，不需要 `expected_output`。模型分别整理证据和抽取回答，再生成带理由的 yes/no/borderline。

同步入口依次处理前两个抽取；`a_measure` 可以并发抽取 truths 与 claims，随后再等待裁决。两个抽取都完成以前，无法进行最后判断。

[score_qag_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 决定有效裁决与通过集合。默认接受 yes 和 borderline，含糊项惩罚只接受 yes；空列表默认1。无效标签可能被归一化或丢弃，因此要核对有效裁决数。

`strict_mode` 还会按阈值压低不通过的分数，它与含糊项惩罚是不同配置。`include_reason=False` 只省去整体总结，逐项理由仍可读取。

## Ragas 的主链

[Faithfulness 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/) · [metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py) · [prompt/schema](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/util.py)

```text
ascore
  → _create_statements：问题与回答 → statements
  → _create_verdicts：上下文与 statements → NLI 结果
  → _compute_score：支持比例
  → MetricResult
```

入口检查非空问题、回答和上下文；无 statements 或无 verdict 时返回 NaN。每项 NLI 输出包含 statement、reason 和0/1判定。

本课 `CapturingJudge` 在现代适配器上记录 schema 原始结果，不改变原生提示与算法。`deep_aggregate/ragas_aggregate` 只是帮助手算固定裁决的函数，不承担自然语言判断。

## 低分时先检查哪一步

先看原始证据是否确实包含所需事实，再看 truths/statements 有没有遗漏或合并，最后检查支持关系及聚合政策。

同名指标的差异可能来自抽取、判定和空集约定。Faithfulness 也无法单独识别参考过期、答非所问或漏答，这些留给答案质量指标。
