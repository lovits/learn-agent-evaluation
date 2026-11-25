# e07 源码导读：召回的分母从哪里来

[教材](README.zh.md) · [覆盖计算与原生评分](eval.py) · [条件构造](code.py)

## 本课调用链

[code.py](code.py) 中的 `prepare` 先校验 [cases.jsonl](cases.jsonl) 记录的 `atlas/release.md` 与 `atlas/logs.md` 哈希，再调用 TinyRAG `retrieve` 取出 `limit=3` 条候选，筛选出这两份必要来源文档；只有两者都出现在候选中时才继续构建三组对照，保证对比基于同一批检索结果，原始 `raw_hits` 也会完整保留在报告中。

三组对照分别构造为：`complete` 保留两份文档和三条参考事实；`missing_logs` 移除 `atlas/logs.md` 并保留三条参考事实；`incomplete_reference` 沿用缺日志上下文，同时从参考清单移除 `log_days`。后两组作为受控对照，用来分别隔离上下文缺漏与参考清单缺漏的影响。

`summarize` 按预设的来源映射调用 `coverage` 计算文档与事实覆盖率。当前两篇短文档各自只占一个完整切分片段，因此可以使用来源路径查表；若拓展到切分为多段的长文档或更新了文档内容，则需要把映射粒度细化到具体片段，或者依靠语义归因逐条核对证据。

传入 `--judge` 时，`main` 构造不含 `actual_output` 的样本并调用 `judge_recall`，复用第 4 课的 `JudgeModel` 和 `score` 包装函数运行 DeepEval 的 `ContextualRecallMetric`。

## DeepEval：逐参考句归因

本课对应 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，官方概念见 [Contextual Recall](https://deepeval.com/docs/metrics-contextual-recall)。

沿着 [contextual_recall.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/contextual_recall.py) 查看同步 `llm` 路径的执行流程：

1. `_required_params` 声明样本需要 `input`、`retrieval_context` 与 `expected_output`。`measure` 校验通过后，将 `expected_output` 与 `retrieval_context` 传给 `_generate_verdicts`。虽然 `LLMTestCase` 校验需要 `input`，但该路径下的归因提示词本身并未读取问题文本。
2. 提示词模板 [generate_verdicts.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/templates/generate_verdicts.txt) 要求裁判把参考答案中的每句话拆解出来，分别给出 `yes`/`no` 裁决及 `reason`，并在理由中尽量标明是第几个上下文节点提供了支持。拆句和归因在同一次模型调用里完成，而非先跑独立拆句器再分别判分。
3. [schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/schema.py) 将 `verdict` 限制为 `yes` 或 `no`。需要注意，`VerdictWithExpectedOutput` 在每条结果里挂载的 `expected_output` 字段是**整段**参考文本，并没有单独保存当前这一句的 `statement`。因此不能把 `verdict.expected_output` 当作单句原文，也不能仅靠列表下标直接绑定自定义事实 ID。
4. `_calculate_score` 调用 `score_qag_verdicts`，统计 `yes` 的比例作为最终得分，遇到空裁决列表时内部聚合默认返回 `0`。开启 `strict_mode` 会把低于阈值的比例压成 `0`，本课保持关闭以保留原始比例。
5. `_generate_reason` 在 `include_reason=False` 时返回 `None`，仅省去一次额外生成总分说明的模型调用，逐条裁决里的 `reason` 依然照常保存。

为了把“参考无效或裁判失灵”与“上下文没有覆盖参考”明确分开，本课 [eval.py](eval.py) 在外层适配中做了两项保护：先拒绝空白 `expected_output`，并在 `verdicts` 为空时把状态改记为 `error`、分数置为 `None`。

由于当前 schema 没有保存逐句文本，也不强制裁决数必须等于预想句数，通过类型校验后仍需要结合每条裁决里的 `reason` 复核是否漏拆或错判；系统的裁判对齐与校准方法将在第 14 课展开。

## 参考事实的边界

文档召回、作者标注的事实覆盖与模型拆句后的语义归因各自采用不同的分母单位。将两条独立事实合并成一句话可能改变裁决总数和权重，参考中存在重复表述也会重复计入；本课 `coverage` 只对显式 ID 集合去重，不自动合并自然语言同义句。

高召回只证明检索上下文支撑了当前写的 `expected_output`，既不能代替审核参考本身的完整性，也不能保证后面的回答阶段真的把这些证据用全了。第 8 课继续检验回答对上下文的忠实度，第 9 课接着考察回答质量与信息覆盖。

相关参考资料见 [DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)，源码细节以本课对应固定版本为准。

[样本与评测记录](assessment.md)
