# e03 源码导读：题目、参考和运行各放在哪里

[教材](README.zh.md) · [数据整理](code.py) · [候选生成](generate.py) · [复用 Agent](experiment.py)

## 整理链路：先审核，再去重与切分

[code.py](code.py) 中的 `curate` 按固定顺序过滤候选题目：先核对审核状态与审核人，再校验来源文件是否存在、SHA-256 哈希是否与审核版本一致、可回答题目的引文是否出现在原文中，最后按 `(family, intent)` 键去重。

- `family` 表示共享同一组业务事实的题族，`intent` 表示具体题意，两者由审核阶段人工确认。
- 按 `(family, intent)` 去重能拦住词句不同但考点相同的改写题；在大规模题库里，通常先用向量近邻检索筛出相似候选，再由审核人确认题意归属。
- `quote in doc["text"]` 保证引文真实存在，而引文是否支撑参考答案、缺证据题是否明确限定回答范围，仍由审核记录负责。

## 对应 DeepEval 的 Golden 与 EvaluationDataset

[DeepEval 官方数据集文档](https://deepeval.com/docs/evaluation-datasets)把 `Golden` 定义为运行前的题目样本。对照固定版本的 [golden.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/golden.py#L181)：`input` 为必填字段，`actual_output` 和 `expected_output` 均可为空，同时提供 `context`、`source_file` 和 `additional_metadata`。

本课把审核通过的参考写入 `expected_output`，把参考依据的原文写入 `context`（由于尚未接入检索流程，这里不写 `retrieval_context`），把题号、题族、来源哈希和划分标签放进 `additional_metadata`。

[dataset.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py#L237) 中的 `add_golden` 负责组织样本集合并校验单轮或多轮类型，但不会自动检查题族泄漏或参考准确性。因此本课在构造开发集与留出集两个 `EvaluationDataset` 之前，先由 `curate` 和 [eval.py](eval.py) 的 `check_dataset` 完成质量把关。

运行阶段由 [experiment.py](experiment.py) 复用第 2 课的 Agent 循环，在隔离目录中读取资料并生成回答，再把实际输出和工具记录组装成 `LLMTestCase`，确保参考答案与实际输出始终来自独立来源。

## DeepEval Synthesizer 的生成与复核机制

[DeepEval 合成器指南](https://deepeval.com/guides/guides-using-synthesizer)介绍了从文档上下文生成问题、改写演化与补全参考答案的流程。

对照固定版本的 [Synthesizer.generate_goldens_from_contexts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py#L673)，内部会先基于上下文生成输入，调用 `_rewrite_inputs` 迭代改写，再构造 `Golden` 并按需生成 `expected_output`。追踪 [_rewrite_inputs](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py#L1554) 可以看到：内置 critic 会给出评分与修改意见，低于阈值时触发重写，但达到最大重试次数后，该候选依然会被加入返回列表。

这意味着自动质量分只能作为筛选辅助，不能替代人工对照原文核对。本课的 [generate.py](generate.py) 实现轻量候选生成，并把所有模型产出统一标记为 `pending`，强制走完同一套审核与整理链路后再进入 `EvaluationDataset`。

## 按题族固定划分

`HOLDOUT_FAMILIES` 显式列出留出题族，保证同族题目全部落在同一侧。`check_dataset` 会逐项检查题号唯一性、`(family, intent)` 唯一性、四类题型覆盖情况，以及开发集与留出集的题族集合是否完全不相交。

固定划分后，日常迭代修改 Agent 或提示词只在开发集上进行，留出集留到阶段性验收或版本对比时使用，避免调参过程把留出集的信息间接带入系统。

[练习](exercises.md) · [样本与评测记录](assessment.md)
