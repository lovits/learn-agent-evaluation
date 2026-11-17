# e10 源码导读：阶段缺口与错误归因

[教材](README.zh.md) · [阶段回放](code.py) · [缺口检查与噪声算式](eval.py)

## 本课实际调用链

`prepare` 校验第9课冻结记录与原始资料哈希。每个条件深拷贝资料快照，固定真实运行的第一条检索查询，再调用原生 TinyRAG。source_missing 在查询前移除文档，stale_source 修改快照内容并重算哈希；挂载文件未修改。

native_hits 是原生返回，retrieved 是控制处理后的检索输出，selected 是准备送入模型的片段。retrieval_miss 是主动过滤，不是事后宣称原生查询漏召回；assembly_drop 则只改变 selected。noise、conflict 追加明确标注的 constructed 片段，不伪造检索来源。

`first_gap` 依次检查目标文档、内容版本、检索输出与组装结果，报告最先观察到的缺口。这只是当前短文、已知参考来源的检查器，不是任意文档的语义根因定位。哈希变化需审核，不能自动断定旧版本错误。

`replay` 深拷贝最后一次真实生成输入，替换唯一知识结果，附加每组相同的来源策略。tools={} 且拒绝新工具调用，使模型不能靠再次检索消除控制条件。实际 retrieval_context 从这次 model_input 提取；原始参考仅用于评分，未传给生成模型。

七种条件的调用是受控生成回放，不是七次新完整 Agent 运行。接口错误单独记录，逐条件保存已完成结果及原始裁判返回。

## DeepEval：阶段证据与答案指标配合

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)。[RAG Evaluation 指南](https://deepeval.com/guides/guides-rag-evaluation) 将检索器与生成器分开评价；本课进一步保留来源和上下文组装阶段，避免把检索输出与模型实际输入混为一谈。

[ContextualRelevancyMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) 根据问题，对上下文拆出的陈述判相关，再求 yes 比例。它不读取资料目录、原始候选与组装日志，因此相同上下文可有相同分数，却来自不同故障阶段。第6课保留其原生执行与具体导读，本课不重复跑全套指标。

本课实际复用第8课 [FaithfulnessMetric 包装](../e08_faithfulness/eval.py) 与第9课 [G-Eval 任务标准](../e09_answer_quality/eval.py)。前者的原生 [faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py) 从本次上下文抽 truths、从回答抽 claims，再判 verdicts。默认 yes 与 borderline 都通过，不能将默认分数解释成每条声明均有明确支持；support_score 单独保留 yes 比例。

在冲突资料中，truths 提取可能丢失来源及其优先级。单纯对全部 truths 判断是否矛盾，不一定等价于按当前主规范回答。G-Eval 同时读取问题、回答、当前参考与实际上下文，按本课策略解释完整回答或合理保留；这也仍是模型裁决，不替代阶段事实或来源审核。

因此，faithfulness 高、任务质量低时应回看参考与来源版本；存在阶段缺口而任务质量高时，可能是模型正确保留了缺失信息。两类观察都不能从一个分数直接推成根因。

## Ragas：从支持矩阵到 Noise Sensitivity

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Noise Sensitivity](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/)。本课不执行 Ragas。

现代 [noise_sensitivity/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/metric.py) 的 `ascore`：

1. 分别把 reference 与 response 拆为声明。
2. 对每份 context，判断它对参考声明和回答声明的支持，构成 retrieved2ground_truth 与 retrieved2answer 两个矩阵。行对应声明，列对应资料。
3. 再用 reference 判断回答声明，得到 ground_truth2answer。其布尔取反就是代码里的 incorrect；这里指参考未支持，不是外部世界已证明错误。
4. `_compute_score` 将支持至少一条参考声明的资料列标为 relevant_retrieved，再判断回答声明是否得到这些资料列中任意一列支持。
5. relevant 模式统计 relevant_faithful 与 incorrect 的交集；irrelevant 模式统计无关资料的支持，并先用 `&= ~relevant_faithful` 排除同时被相关资料支持的声明。最后对全部回答声明取均值。

因此，相关资料的定义依赖参考声明支持，不等同第6课单纯与问题主题相关。一个混杂了正确条件和错误命令的旧规范，仍可能属于 relevant 类，错误命令也就可能进入 relevant 方向。

[util.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/util.py) 委托公共声明生成和 NLI 提示词，输出声明、理由与整数 verdict；代码用真假值转为布尔支持关系。声明拆分、参考完整性和裁判判断都会影响矩阵，不能只看最终均值。

本课 `noise_fraction` 的三组向量是假设这些矩阵已得到之后的简化聚合示例，标签由编写助手构造，不是对七次回放的自动语义判断。长度和布尔类型需对齐；空列表返回 None。原实现只先检查输入字符串与列表非空，空抽取会产生空矩阵，后续 max/mean 没有统一的完整保护，不能一概说框架对空声明返回有效零分。

## 分母与诊断限制

分母是全部回答声明数，不是错误声明数。增加正确声明可能降低这个比例，即使错误支持数量没变；零分也可能遗漏大量要求。不同拆分粒度或参考版本的数值不能直接横比。

Noise Sensitivity 不是基线分数减去加噪后分数，也不是严格因果证明。它描述参考未支持声明与不同资料的支持关系。受控回放有助于观察变化位置，单次生成差异仍可能含有随机性；正式版本比较与不确定性在第15课展开。

飞书原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对 RAG 分层评价与 NoiseSensitivity 相关段落，具体聚合以固定源码为准。
