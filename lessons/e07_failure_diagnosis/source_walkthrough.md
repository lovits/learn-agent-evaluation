# e07 源码导读：沿支持关系定位失败

[教材](README.zh.md) · [干预与产物读取](code.py) · [评分](eval.py)

## 先读本课的数据流

```text
资料副本 available
  → search_knowledge
  → before / 干预 / after
  → agent_loop
  → upload_notes.json
  → inspect_artifact → diagnose
```

`fault_dispatch` 只截获知识检索，查询固定为 `QUERY`。其他工具与前课保持同一路径；生成故障只改变模型入口提示，不修改检索结果。

`diagnose` 检查实际文件、可用文档和实际返回，不读取 `case.id` 来决定失败原因。一次干预只能支持当前观察，模型抽样和更多潜在因素仍需进一步控制。

## DeepEval：话题相关性的分母

[Contextual Relevancy 文档](https://deepeval.com/docs/metrics-contextual-relevancy) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) · [RAG 指南](https://deepeval.com/guides/guides-rag-evaluation)

固定实现 `_required_params` 只要求问题和检索上下文。同步 `measure` 为每个片段生成带 statement、verdict 和 reason 的列表；异步入口可以并发处理片段。

`_calculate_score` 展平列表，数相关声明比例，空裁决默认0。它不读取 reference 来检查漏掉的必要资料，长文档拆出的更多声明还会改变权重。

## Ragas：三张支持矩阵

[Noise Sensitivity 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/metric.py) · [prompt/schema](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/util.py)

`ascore` 需要问题、回答、reference 和上下文。先拆 reference 与回答，再分别判断：

| 矩阵 | 行与列 |
|---|---|
| `retrieved2ground_truth` | 参考声明 × 上下文 |
| `retrieved2answer` | 回答声明 × 上下文 |
| `ground_truth2answer` | reference 对回答声明的支持 |

最后一项取反，得到错误回答声明。第一张表把文档分成相关和无关组，第二张表说明每组支持哪些回答声明。

## _compute_score 怎样用这些表

relevant 模式取“错误”与“被相关组任一文档支持”的交集，再对全部回答声明取均值。

irrelevant 模式同样计算，但排除也被相关组支持的声明。若三条回答中有一条只被无关组支持且为错误，无关模式就是1/3。

同一错误在两组都有支持时，只计入相关模式。错误不被任何上下文支持时，两组都可能为0；这个指标没有覆盖全部幻觉来源。

`AuditedNoise` 记录原生矩阵并调用父类聚合，允许对同组裁决切换模式。空拆解或异常矩阵可能产生 NaN 或错误，外层要分开记录。

## 先检查投影，再解释指标

`response_text` 只投影实际文件的业务字段，来源数组和最后的完成回执保留在原记录中。`null` 明确表示当前证据未知；reference 应写清任务端点与版本。

同一套字段投影用于各干预，才方便对照。阶段诊断、答案质量与噪声来源分别回答不同问题。
