# e07 源码导读：召回的分母从哪里来

[教材](README.zh.md) · [覆盖计算与原生评分](eval.py) · [条件构造](code.py)

## 本课调用链

`prepare` 校验样本中 release、logs 的内容哈希，调用一次 TinyRAG 取得候选，再筛出必要来源。两份来源未出现在候选中就停止，避免把检索变化混入预设对照。原始候选仍完整保存。

complete 保留两份资料；missing_logs 移除 logs、参考不变；incomplete_reference 继续使用同一个缺日志上下文，同时从参考中移除 log_days。后两组是主动构造的条件，不声称检索器真实返回过这两种列表。

`summarize` 按事先审核的来源映射计算文档和事实覆盖，`coverage` 去重后求交集比例。当前两篇短文各占一个完整片段，才可以用路径映射事实。切换到长文档、分块内容或来源版本变化后，必须重审证据范围；本课函数不具备任意文本的蕴含判断能力。

`--judge` 为每个条件调用一次 DeepEval ContextualRecallMetric。样本不生成 actual_output；固定实现的直接 measure 路径只用 reference 与上下文做归因。这不表示所有评测入口都允许缺少回答。

## DeepEval：逐参考句归因

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念见 [Contextual Recall](https://deepeval.com/docs/metrics-contextual-recall)。

沿 [contextual_recall.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/contextual_recall.py) 阅读：

1. `_required_params` 声明 input、retrieval_context、expected_output。同步 measure 先校验，再将 expected_output 与 retrieval_context 传给 `_generate_verdicts`。虽然样本要求 input，这条 llm 归因提示词没有把问题传进去。
2. [generate_verdicts.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/templates/generate_verdicts.txt) 要求每个参考句产生一条 yes/no 和 reason，理由尽量指出支持它的上下文节点。拆句与归因由这次模型请求一起完成，不是先执行一个独立事实提取器。
3. [schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/schema.py) 的 verdict 限定 yes/no。`VerdictWithExpectedOutput` 给每条结果附加的是**整段** expected_output，没有保存单独的 statement。不能把这一字段误读成当前句文本，也不能只凭列表下标确认与自定义事实 ID 对齐。
4. `_calculate_score` 调用 `score_qag_verdicts`，以 yes 为通过项，空裁决约定 0。strict 模式另将低于阈值的分数压为 0，本课关闭 strict，保留比例。
5. `_generate_reason` 在 include_reason=False 时返回 None；这不删除逐项 reason，只减少总分解释请求。

本课适配层在 SDK 之外拒绝空白参考，并把空裁决改记为 error/None。SDK 的空聚合约定和课程的数据质量约定分别说明，不能说成 SDK 原本就抛出了这个错误。

当前原生 schema 没有逐句文本字段，也未强制裁决数量等于真实句数。非空裁决通过类型校验，仍需人工核对理由中的覆盖范围；本课不声称已经自动验证了每条参考的完整对齐。更严格的裁判对齐与校准在第14课展开。

## Ragas：参考声明作为评分单位

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)。

现代 collections 的 [context_recall/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_recall/metric.py) 中，`ContextRecall.ascore` 拒绝空 question、reference 和 contexts。它把上下文用换行连接，构造 question、context、answer，其中 answer 实际装的是 reference。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_recall/util.py) 的 prompt 要求分析参考中的每个 statement，返回 statement、reason、attributed。模型一次完成拆解与归因，程序取 `sum(attributions) / len(attributions)`；空 classifications 返回 NaN。

提示词要求 attributed 为 0/1，但类型是普通 int，本字段本身没有把取值限制为二元。这与 DeepEval 的 yes/no schema 不同。理解分数时应连同验证、提示词和原始裁决阅读，不能只看最后的除法。

Ragas 文档也介绍 ID Based Context Recall，按检索 ID 和参考 ID 的交集求召回。本课 `coverage` 展示这类集合算式，事实映射则由教学标注提供；没有运行 Ragas，也没有把它当成语义裁判的替代品。

## 参考事实的边界

文档召回、作者标注的事实覆盖、模型拆句后的语义归因使用不同单位。原子事实合并成一句会改变权重，重复参考也可能重复加权；本课集合算式只按 ID 去重，不自动合并同义事实。

高召回只说明当前参考得到支持，不能证明参考已经完整代表用户需求，也不能证明实际回答使用了全部证据。第8课转向实际回答的忠实度，第9课再看回答质量。

相关飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对召回相关段落；实现细节以固定源码为准。
