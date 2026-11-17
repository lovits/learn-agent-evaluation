# e08 源码导读：声明怎样进入分子

[教材](README.zh.md) · [原生评分与聚合](eval.py) · [冻结样本入口](code.py)

## 本课调用链

`prepare` 校验第 5 课 assessment.json 的 SHA-256，从 baseline 读取任务、真实回答和当时实际送入模型的 retrieval_context。复用的是冻结记录，不重新运行 Agent，不把参考 context 当成本次检索资料。

其余三组使用标注为构造的回答，分别添加没有依据的 GitLab 声明、改错日志天数、替换日志证据。最后一组将 14 天改为 30 天，并把片段编号改为 constructed/logs-30-days，避免冒充原始文档版本。原始知识库未修改。

`--judge` 才调用 DeepEval。`judge_faithfulness` 保留原生 score 与 sdk_score、中间 truths、claims、verdicts，再对同一裁决计算 yes 比例作为 support_score。受控教学标签与模型结果不强制对齐；作者示意拆分不是独立人工金标准。

## DeepEval：三次模型请求

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，官方概念见 [Faithfulness](https://deepeval.com/docs/metrics-faithfulness)。

沿 [faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py) 的同步 llm 路径阅读：

1. 必需字段为 input、actual_output、retrieval_context。`measure` 校验后依次抽取 truths、claims，再判定 verdicts，最后聚合。该路径的三个主要提示词不使用问题 input；input 是样本必需字段，不应误写成三个阶段都拿它作判断。
2. `_generate_truths` 以双换行连接上下文，要求抽取其中事实。truths_extraction_limit 默认 None，不主动限制数量；提取器仍可能漏掉条件或证据。变量名 truths 不代表这些内容已经外部查真。
3. `_generate_claims` 从实际回答提取事实性声明，模板要求保留原语境，即使声明事实上有误也应提取。若提取器悄悄纠正了 30 天，后续就不再评测原回答。
4. `_generate_verdicts` 把 truths 重新连接，与 claims 交给裁判。最终判定依赖抽取后的资料事实，不能声称它在这一步直接阅读了完整原文。
5. `_calculate_score` 根据 penalize_ambiguous_claims 决定通过集合；默认包括 yes 与 borderline，开启该选项才只包括 yes。strict_mode 是另外的阈值压零步骤，本课关闭。

主要模板：[generate_truths](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_truths.txt)、[generate_claims](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_claims.txt)、[generate_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_verdicts.txt)。文本判据还须继续读其引用的 [guidelines fragment](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/templates/metrics/fragments/faithfulness_verdicts_guidelines_text_only.txt)：no 仅用于直接矛盾，未获上下文支持但非矛盾的声明使用 borderline。

## schema、聚合与空值

[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/schema.py) 分别保存 truths 字符串列表、claims 字符串列表、verdicts 列表。每条 verdict 只有 yes/no/borderline 与可选 reason，没有声明 ID；本课检查数量，仍需按 claims 与理由核对语义顺序。

include_reason=False 只跳过额外的总分理由请求；no 或 borderline 的逐项 reason 仍由判定模板要求。同步路径通常三次请求；异步路径会并行抽 truths 与 claims，本课为便于观察选择同步。

[score_qag_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 默认 empty_score=1。claims 为空时 `_generate_verdicts` 直接返回空列表，因此原生聚合可得 1。

本课额外约定：空 claims 标记 not_applicable，对外分数与 passed 为空；原生返回仍在 sdk_score 留存。有 claims 但裁决数不等于 claims 数时，标记 error。接口或 schema 错误也保留 error 与空分数，不能填成有效零分。数量一致不能自动证明抽取或语义对齐正确。

`aggregate` 的空列表返回 None，拒绝未知标签，便于手算同一组裁决在两种口径下的差别。support_score 对应 penalize_ambiguous_claims=True 的聚合，不重新请求模型，不运行第二套框架。

## Ragas：从声明到原上下文的 NLI

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)。本课没有实际执行 Ragas。

现代 collections 的 [faithfulness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py) 中，`ascore` 验证 question、response、retrieved_contexts 非空，然后：

1. `_create_statements` 用问题与回答生成 statements，要求拆解句子并消除代词，使每条能独立理解。
2. 直接将原始 retrieved_contexts 用换行连接，交给 `_create_verdicts`；没有独立的上下文 truths 提取步骤。
3. `_compute_score` 对返回的 statement verdict 求支持比例。无抽取声明、或无判定声明时返回 NaN，不采用 DeepEval 空聚合的 1。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/util.py) 的 NLI 提示词要求：能直接从上下文推得为 1，否则为 0。输出还保存 statement 与 reason。当前 schema 的 verdict 是普通 int，聚合用真假值统计；提示词的 0/1 要求不等于字段类型已强制二元边界。

两个实现的抽取粒度、证据中间层、裁决规则、空值约定均不同。即使把 DeepEval 的 borderline 排除，也不能据此声称已经得到了某次 Ragas 分数。

## 证据范围决定解释范围

忠实度是回答与指定证据之间的关系。知识库文档不包含写文件的执行记录，不能单独证明“已写入 check.txt”；应该检查实际工具输出和工作区产物。反过来，只忠于错误或过期文档也不能证明现实正确。

飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对忠实度相关段落，具体行为以固定源码与本次原始裁决为准。
