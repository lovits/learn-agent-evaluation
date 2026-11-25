# e10 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. `source_missing`、`retrieval_miss`、`assembly_drop` 三组条件最终都没有把发布规范送进模型上下文。分别需要对比哪几份阶段记录，才能把它们区分开？
2. 知识库文档的 SHA-256 哈希发生变化，能否直接证明文档已经过期或写错了？如果文档只是修正了错别字，参考标准和证据校验应怎样处理？
3. 在 `stale_source` 条件下，旧规范写着错误命令，模型也照着旧规范作答。此时哪一项 DeepEval 指标依然会给出满分？应当先修改哪一层？
4. 在 `conflict` 条件下，模型正确采纳了主规范 `atlas/release.md`，若发现 `FaithfulnessMetric` 的 `support_score` 偏低，应当按什么顺序排查 `truths`、来源规则与裁决，而不是急着改写模型回答？
5. 在 `noise_fraction` 的手算示例（3 条陈述：`correct=[True, False, False]`、`relevant_support=[True, True, False]`、`irrelevant_support=[False, True, True]`）基础上，再追加 1 条正确且未被无关资料支持的陈述。`relevant` 与 `irrelevant` 两个比例会如何变化？
6. 一次加噪回放没有看到回答质量下降，能否证明该 Agent 在所有噪声场景下都稳健？`first_evidence_gap` 返回 `None` 又能说明什么？

[参考解释](solutions.md)
