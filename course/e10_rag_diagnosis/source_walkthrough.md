# e10 源码导读：阶段缺口与噪声归因如何排查

[教材](README.zh.md) · [阶段回放](code.py) · [缺口检查与噪声算式](eval.py)

## 本课调用链

[code.py](code.py) 中的 `prepare` 首先读取第 9 课 `assessment.json` 与挂载知识库，校验两者的 SHA-256 哈希，确保冻结轨迹和基准语料没有漂移。随后从真实运行记录里提取 `trace["retrievals"][0]["query"]`，在内存里为七组条件深拷贝文档清单并调用原生 TinyRAG 的 `retrieve(..., limit=3)`。

各条件在内存快照和下游环节逐一隔离变量：

- `source_missing` 在检索前从内存 `documents` 列表剔除 `atlas/release.md`，磁盘文件保持原样。
- `stale_source` 修改内存里 `atlas/release.md` 的命令为 `python -m unittest` 并重算该条哈希，因此 `documents` 清单与 `knowledge_version` 均随之更新。
- `retrieval_miss` 保留原生返回的 `native_hits`，只在 `retrieved` 阶段过滤掉目标规范路径。
- `assembly_drop` 保留完整的 `retrieved`，仅在截取前两条形成 `selected` 后剔除目标规范路径。
- `noise` 与 `conflict` 不修改 `documents` 清单（因此 `knowledge_version` 与 `baseline` 一致），只在 `selected` 末尾追加明确标为 `constructed context injection` 的片段。

`replay` 深拷贝最后一次成功模型的输入消息 `trace["model_inputs"][-1]`，往首条消息追加统一的资料使用与冲突优先级规则，并把唯一一条 `kind == "knowledge_context"` 的工具输出替换成当前条件的 `knowledge_version` 和 `contexts`。随后以 `tools={}` 调用 `call_model` 生成回答（若模型返回新工具调用则抛错中止），并通过 `sent_contexts([messages])` 从本次实际送入模型的消息重建 `LLMTestCase.retrieval_context`。命令行传入 `--judge` 时必须同时传入 `--live`，逐条件执行评测并在每轮 `finally` 块即时保存结果和 `judge_calls`。

## DeepEval：阶段证据与生成指标分工

以下源码分析基于 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，架构参考 [RAG Evaluation 指南](https://deepeval.com/guides/guides-rag-evaluation)。

DeepEval 将检索质量与生成质量拆开评价：在检索侧，第 6 课使用过的 [ContextualRelevancyMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) 只读取 `input` 与最终 `retrieval_context`，无法分辨这份上下文缺失究竟是源于知识库缺文档、检索器漏召回还是上下文组装阶段被截断。本课保留 `documents`、`native_hits`、`retrieved`、`selected` 四份中间产物，正是为了补齐检索与生成之间的组装观测空白。

在生成侧，本课直接复用第 8 课的 `judge_faithfulness`（封装 [faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)）与第 9 课的 `task_metric`（`GEval`）：

1. `FaithfulnessMetric` 从当次 `retrieval_context` 抽取 `truths`，再从重放生成的 `actual_output` 抽取 `claims`，最后逐条判定 `yes`/`no`/`borderline`。由于原生默认将 `borderline` 算作通过，`judge_faithfulness` 另存只统计 `yes` 的 `support_score` 供复核。
2. 当上下文混入冲突信息时，`_generate_truths` 从原始片段抽取事实可能丢失“哪条来自 `atlas/release.md`、哪条来自旧备忘”的来源优先级，导致遵循主规范的正确回答在 NLI 阶段被误判为与旧备忘矛盾；因此必须把 `truths` 与 `verdicts` 原样保存下来查验。
3. `task_metric` 把问题、回答、当前标准 `expected_output` 和当次 `retrieval_context` 一起交给 `GEval`，从而既能发现 `stale_source` 下“忠于旧文档却偏离当前规范”的问题，也能肯定 `source_missing`、`retrieval_miss`、`assembly_drop` 下“证据不足时主动拒答”的合规行为。

## 诊断函数：first_gap 与 noise_fraction 的代码细节

[eval.py](eval.py) 里的两个轻量诊断函数把阶段检查与噪声归因算式独立出来：

- `first_gap(documents, retrieved, selected, source)` 按固定顺序检查文档存在性、内容 SHA-256 一致性、`retrieved` 路径命中以及 `selected` 路径命中，返回最早出现的缺口标识或 `None`。它面向单篇短规范、已知目标路径的链路排查；若文档包含多个切片或路径名相同而关键段落未入选，还需继续核对具体的 `chunk_id` 与正文内容。
- `noise_fraction(correct, relevant_support, irrelevant_support)` 严格校验三个布尔数组长度一致且元素类型为 `bool`（空列表时返回 `{"relevant": None, "irrelevant": None}`）。它以 `len(correct)` 为分母，计算两项占比：`relevant` 统计 `not c and r`（未被参考支持但有相关资料支撑的陈述），`irrelevant` 统计 `not c and i and not r`（未被参考支持且仅由无关资料支撑的陈述）。

这里需要留意两处指标解读边界：其一，当某篇文档同时包含部分正确规则和一条过时命令时，因为触及了部分参考信息，它在归因分类上仍可能属于相关资料，从而把错命令算进 `relevant` 侧；其二，由于分母是全部回答陈述数，回答里多说几句无关紧要但正确的废话会稀释错误占比，却没有真正减少错话数量。单次重放还带有模型采样随机性，涉及版本对比与置信区间评估时将在第 15 课继续展开。

[样本与评测记录](assessment.md)
