# e03 源码导读：题目、参考和运行各放在哪里

[教材](README.zh.md) · [数据整理](code.py) · [候选生成](generate.py) · [复用 Agent](experiment.py)

## 一道题还没有实际回答

[code.py](code.py) 的 `curate` 先核对审核记录、来源版本和证据，再按已经审核过的 `family + intent` 去重。`family` 表示共享事实的题族，`intent` 表示题意；它们由审核者确定，不从题目字面自动推断。

这能去掉词句不同但题意相同的候选。若两道不同题意误用了同一个键，也会误删。大规模数据可以先用向量找近邻，再核对题意；本课用少量可逐题检查的键说明语义去重的判断依据。

`quote` 必须出现在当前来源中，只能证明引文确实存在。参考答案是否忠于引文、题目是否值得测，仍由审核负责。资料未提供答案的题，参考可以是明确拒答，审核范围必须限定在给定资料。

## DeepEval：Golden 到 EvaluationDataset

[官方数据集说明](https://deepeval.com/docs/evaluation-datasets)把 Golden 作为运行前的样本。固定版本的 [golden.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/golden.py#L181) 中，`input` 必填，`actual_output` 和 `expected_output` 都可空；它还保存 `context`、`source_file` 与 `additional_metadata`。

本课在 `expected_output` 放审核后的参考，在 `context` 放参考所依据的资料。这里尚未执行检索，所以不能把它写成实际的 `retrieval_context`。题号、题族、来源哈希和划分保存在 metadata 中。

[dataset.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py#L237) 的 `add_golden` 负责组织样本并检查单轮、多轮类型。它没有判断本课的题族是否泄漏，也没有替我们检查参考正确性。因此，本课先整理和划分，再构造两个 `EvaluationDataset`。

[experiment.py](experiment.py) 复用第2课循环，读取实际工具反馈后记录模型回答，再生成 `LLMTestCase`。参考来自题目，实际回答来自运行，两者没有互相填补。

## DeepEval：生成器的质量分还需要审核

[官方生成指南](https://deepeval.com/guides/guides-using-synthesizer)说明从文档到上下文、候选问题、改写和参考生成的过程。

固定版本 [Synthesizer.generate_goldens_from_contexts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py#L673) 对上下文生成输入，调用 `_rewrite_inputs`，再做 evolution、构造 Golden，最后按需生成 `expected_output`。

沿 [_rewrite_inputs](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py#L1554) 看，critic 给出分数与反馈；不足阈值时重写，最多尝试指定次数。循环结束后，代码仍把该项加入返回列表。质量阈值与重写次数不能保证最终参考已经正确。

本课的 [generate.py](generate.py) 只实现一次小规模模型候选生成，然后统一标成 `pending`；正式入库要经过同一套审核。实际使用了 DeepEval 的 Golden 和 Dataset，没有运行原生 Synthesizer 的整条生成链。

## Ragas：先决定要生成哪类问题

[Ragas 的生成概念](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/)从知识图谱、场景和 query 类型组织生成。固定版本 [TestsetGenerator](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/generate.py#L114) 将文档变成节点，应用 transforms，再进入 `generate`；后者结合 persona、query distribution 分配场景，调用各 synthesizer 生成样本。

这提醒我们先决定要覆盖的行为：正常问法、错误前提、边界条件，以及资料没有答案的请求。仅把一道普通题换十种说法，并没有补上这些空白。本课借这个思路设计题型，不再写一套 Ragas 数据接入。

## 按题族固定划分

`HOLDOUT_FAMILIES` 明确保存留出题族，所有同族题都走同一分支。`check_dataset` 核对题号、题意键、题型和两侧题族是否相交。

题族是审核后的语义分组，程序只能按标签执行。划分固定后，开发集用于修改 Agent 或评分标准，留出集用于最后比较；反复看留出结果并据此调参，会消耗它的独立性。这份小数据只演示过程，不代表真实用户分布。

[练习](exercises.md) · [样本与评测记录](assessment.md)
