# e09 源码导读：不同分数在比较什么

[教材](README.zh.md) · [评分函数](eval.py) · [样本与真实 Agent 入口](code.py)

## 本课调用链

`prepare` 读取六条构造样本与统一参考，校验 release、logs 的哈希。上下文直接从指定文档取出，是控制条件，不声称六种条件都是 TinyRAG 实际检索结果。fact_ids 是课程编写助手给出的事实标注，`fact_scores` 按集合求 TP、FP、FN 和 F-beta。

command 将命令与工作目录作为同一个必答单元，gate 和 fix 分别标注发布门槛及失败处理。错误命令即 command 单元未覆盖，不表示其中“根目录”几个字也错误。改成更细的声明划分后，需要重新标注，计数与权重也会变化。

`--live` 复用第5课 `run_task`，真实查询可挂载知识库并回答，不新增 Agent 循环。保存全部轨迹、原始候选和实际 model_inputs；live sample 的 retrieval_context 由成功模型输入恢复。新回答不自动填事实 ID。

`--judge` 对各回答运行 DeepEval 原生 AnswerRelevancyMetric 与 G-Eval 任务标准。评分只从持久化记录取 input、actual_output、expected_output、retrieval_context 四个字段；完整工具调用留在记录中，不把工具字典错误当成答案质量问题。逐样本保存已完成评分和原始裁判返回。

## DeepEval：切题性不校验事实

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念见 [Answer Relevancy](https://deepeval.com/docs/metrics-answer-relevancy)。

沿 [answer_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py) 阅读：

1. 必需参数只有 input、actual_output。`measure` 从回答生成 statements，再把问题与这些 statements 交给裁判；没有读取 expected_output 或 retrieval_context 来核验正确性。
2. [generate_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/templates/generate_verdicts.txt) 要求每条陈述一个 yes/no/borderline。这里 yes 是相关，no 是无关，borderline 是模糊或可能有辅助作用的信息；与 Faithfulness 的判据不同。
3. `_calculate_score` 以 yes、borderline 为通过项，调用 QAG 聚合。未提取 statements 时，原生空裁决默认得 1；本课保留 sdk_score，但对外标记不适用。裁决数不齐记错误，类型对齐不证明语义判断已正确。
4. include_reason=False 跳过总分解释；陈述抽取与逐项裁决仍各需一次请求，原始 statements 与 verdicts 都保留。

因此，它看不到“用户还问了但回答没说”的全部遗漏，也不会因为命令错了就必然低分。完整性与正确性需要自己的比较对象。

## DeepEval：用 G-Eval 写清任务标准

[官方 Answer Correctness 指南](https://deepeval.com/guides/guides-answer-correctness-metric) 以 G-Eval 展示按应用选择参考、参数与标准的方法。本课复用第4课已读过的 G-Eval 路径，提供明确 evaluation_steps 和 0～2 rubric，再经 SDK 归一化。

`task_metric` 把问题、回答、参考和实际上下文一起传入。参考用于检查应答事实；实际上下文用于判断这些事实是否可由回答方获得。模型按两种情况判读：有证据时检查正确与完整；缺证据时检查是否明确保留、请求补充，且没有猜测。

这个评分有自己的任务语义，不能称为原生相关性、事实 F1 或三者平均。默认阈值也是教学选择，未经过业务校准。适配器没有 logprobs 能力时沿直接模型评分路径，原始返回与理由保留，不伪造概率加权。

## Ragas：双向事实判断与 F-beta

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Factual Correctness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)。本课没有运行 Ragas。

现代 [factual_correctness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/factual_correctness/metric.py) 的 `ascore`：

1. 把 response 拆为 claims，用 reference 做 NLI，得到回答方向的支持布尔数组；其通过数是 TP，未通过数是 FP。
2. 非 precision 模式再把 reference 拆为 claims，以 response 作证据；反向未覆盖数是 FN。precision 模式跳过反向。
3. precision 用 TP/(TP+FP+极小量)，recall 用 TP/(TP+FN+极小量)，f1 模式调用 `fbeta_score`；最后保留两位小数。

TP 来自回答方向，FN 来自参考方向。两个方向的声明粒度未必一致，不能未经核对就假设它们是同一个严格一一对应的事实集合。本课的 ID 集合是简化、已对齐的算式例子，不是假装复现了全部 NLI 流程。

atomicity 控制拆分粒度，coverage 控制提取覆盖范围，都会改变计数。`_decompose_and_verify_claims` 无声明或无判定时返回空数组，后续按当前公式聚合；这种 SDK 空值处理与本课显式 None 约定分别阅读。

[utils.py 的 fbeta_score](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/utils.py) 先求 precision、recall，再作加权调和平均。β² 加大 FN 的代价；β>1 重视召回，β<1 重视精确。参考不完整时 FP 可能只是参考未支持的真实信息，不能直接等同客观错误。

## Ragas：两种向量相似度比较不同对象

[Response Relevancy 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/) 对应现代 [answer_relevancy/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_relevancy/metric.py)。实现按 strictness 次数从回答生成问题，计算它们与原问题的向量余弦均值。无有效生成问题返回 0；所有有效生成结果都标为 noncommittal 时将分数乘为 0。

这和 DeepEval 的逐陈述相关性判断不是同一算法。合理拒答也可能在这类反向提问指标中受惩罚，所以它不直接回答“本场景是否该拒答”。原始余弦公式还需考虑模型、向量范数等数值边界，不能把名称当作概率标定。

[Semantic Similarity 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/semantic_similarity/) 对应 [_semantic_similarity.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/_semantic_similarity.py)。它分别嵌入 reference 与 response，按范数归一化后点乘；可选阈值再转二元值。当前实现对空文本用空格代替，这不等于答案已有效；相似度也不会逐事实证明关键数值或否定条件正确。

本课只分析这两个相似度流程，没有训练或调用嵌入模型，也没有把 TF-IDF 数值冒充语义相似度实测。

飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对答案相关性与事实正确性相关段落，细节以固定源码和实际返回为准。
