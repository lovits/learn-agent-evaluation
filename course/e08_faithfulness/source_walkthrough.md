# e08 源码导读：声明怎样进入分子

[教材](README.zh.md) · [原生评分与聚合](eval.py) · [冻结样本入口](code.py)

## 本课调用链

`prepare` 先校验第 5 课 `assessment.json` 的 SHA-256，从 `baseline` 中读取任务、真实回答以及当时实际送入模型的 `retrieval_context`。其余三组对照样本在内存中组装，分别加入无依据的 GitLab 托管声明、将日志保留期限改为 30 天，以及在最后一组把教学上下文里的 14 天替换为 30 天并将片段编号改为 `constructed/logs-30-days`，原始知识库文件保持不变。

命令行传入 `--judge` 时才会调用 DeepEval。`judge_faithfulness` 记录原生返回的 `score`、`sdk_score` 以及中间的 `truths`、`claims`、`verdicts`，随后对同一批裁决只统计 `yes` 的比例作为 `support_score`。

## DeepEval：三次模型请求

本课对应 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，官方概念说明见 [Faithfulness](https://deepeval.com/docs/metrics-faithfulness)。

沿着 [faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py) 的同步 `llm` 路径阅读，执行流程分五步：

1. 参数校验要求样本包含 `input`、`actual_output` 和 `retrieval_context`。`measure` 校验通过后依次抽取 `truths`、`claims`，再判定 `verdicts` 并聚合。需要注意，这条路径的三个核心提示词实际都不使用 `input`，`input` 仅作为 `LLMTestCase` 的必需字段存在。
2. `_generate_truths` 用双换行拼接上下文片段，让模型抽取其中的客观陈述。`truths_extraction_limit` 默认为 `None`，不做数量截断，但提取阶段仍有可能漏掉限定条件或文档编号。
3. `_generate_claims` 从 `actual_output` 提取事实性声明，提示词要求保留原句语境，即使声明内容明显有误也应原样提取。如果提取器擅自把“30 天”改成了“14 天”，后续裁决评测的就不再是原始回答。
4. `_generate_verdicts` 把抽取后的 `truths` 重新拼接，与 `claims` 一并交给裁判模型。最终判定依据的是 `truths` 列表，而非重新阅读完整原始文档。
5. `_calculate_score` 依据 `penalize_ambiguous_claims` 决定通过集合：默认包含 `yes` 和 `borderline`，设为 `True` 时才只计入 `yes`。`strict_mode` 是聚合之后的阈值压零步骤，本课保持关闭。

三个步骤对应的提示词模板分别是 [generate_truths](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_truths.txt)、[generate_claims](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_claims.txt) 和 [generate_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/templates/generate_verdicts.txt)。裁决规则还需要结合它引用的 [guidelines fragment](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/templates/metrics/fragments/faithfulness_verdicts_guidelines_text_only.txt) 一起读：只有与 `truths` 直接矛盾的声明判 `no`，缺乏支持但不矛盾的表述归入 `borderline`。

## schema、聚合与空值处理

[schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/schema.py) 分别定义了 `truths` 字符串列表、`claims` 字符串列表和 `verdicts` 列表。每条 `verdict` 只包含 `yes`/`no`/`borderline` 和可选的 `reason`，没有绑定声明 ID。本课在代码里校验 `len(verdicts) == len(claims)`，排查具体案例时仍要对照 `claims` 与 `reason` 核对逐项顺序。

`include_reason=False` 会跳过第四次生成总分理由的请求，但判定模板仍会要求对 `no` 和 `borderline` 给出逐项 `reason`。异步模式下 DeepEval 会并行抽取 `truths` 与 `claims`，本课关闭异步以保持执行顺序清晰。

聚合函数 [score_qag_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 默认设置 `empty_score=1`。当 `claims` 为空时，`_generate_verdicts` 直接返回空列表，原生得分会落到 `1.0`。

为了避免误读，本课在 [eval.py](eval.py) 里做了三项保护：

- 当 `claims` 为空时，将 `status` 标为 `not_applicable`，`score` 和 `passed` 置为 `None`，原生结果保留在 `sdk_score`。
- 当存在 `claims` 但 `len(verdicts) != len(claims)` 时，将 `status` 标为 `error`，分数置为 `None`。
- `aggregate` 收到空列表返回 `None`，遇到非法标签直接抛出 `ValueError`，确保手算与程序聚合口径一致。

## 证据范围决定解释范围

忠实度衡量的是回答与给定 `retrieval_context` 之间的关系。知识库文档里没有写入文件的执行日志，因此无法单独证明“已写入 `check.txt`”，这类声明需要回到工具调用记录与工作区文件核对。反过来，回答即使完全忠于一份过时或错误的上下文，也只能说明它遵循了给定材料，不能证明结论在现实中成立。

[样本与评测记录](assessment.md)
