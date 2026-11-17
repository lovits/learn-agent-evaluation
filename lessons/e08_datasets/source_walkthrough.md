# e08 源码导读：生成器为什么不能代替数据审核

[教材](README.zh.md) · [生成器接入](code.py) · [数据合同](dataset.py)

## DeepEval 的生成链

[Synthesizer 指南](https://deepeval.com/guides/guides-using-synthesizer) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py) · [配置](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/config.py)

```text
指定 contexts
  → _generate_inputs
  → _rewrite_inputs / InputFeedback
  → _evolve_input
  → 风格加工
  → Golden + expected_output
```

`FiltrationConfig` 规定 critic 与重试；`EvolutionConfig` 规定演化分布；`StylingConfig` 规定风格。

`_rewrite_inputs` 达阈值时停止重写，耗尽重试时仍可追加最后输入。`synthetic_input_quality` 属于当时反馈，不保证之后演化与风格加工后的质量。`used_source_files` 同样不能证明最终问题必须使用每个来源。

本课从已准备的上下文开始，分别固定 Reasoning 与 Multi-context，便于沿原文检查参考。异步批处理可以并发处理上下文，审核职责不因此改变。

## Ragas 从图到样本

[数据生成概念](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/) · [graph.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/graph.py) · [生成编排](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/generate.py)

`build_graph` 为真实文档建立原生 DOCUMENT 节点，通过共同端点建立 `entities_overlap` 关系。这是课程自己的规则构图。

`TestsetGenerator.generate` 接收预构建图、persona 与 query distribution，先分配 scenario，再生成 sample。本课这条路径不需要 embeddings；不能把这个参数设置直接套到需要默认 transforms 的文档入口。

[具体单跳](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/single_hop/specific.py) 从实体节点组织场景，再由[单跳基类](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/single_hop/base.py)生成 query/answer。

[具体多跳](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/multi_hop/specific.py) 沿实体重合关系取节点组合，[多跳基类](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/multi_hop/base.py)用带 hop 标记的上下文生成问答。节点数量与问题的真实多跳需求仍要分别审核。

## 统一结构接在生成器外面

`candidate` 映射问题、reference、证据、题族和来源，把实际输出留空。自动参考审核返回支持关系、多来源需求和理由，不能据此写成人工通过。

`structure_errors` 检查必要字段与来源版本；`question_key` 使用 NFKC、casefold 和去标点识别词面重复；Jaccard 只给近似提示。数值差异保留，不把1 MiB与2 MiB当成同一个事实。

跨题族重复要隔离，避免相同任务换标签后进入不同集合。同族重复保留首条，其余保存 `duplicate_of`。

## 最后审核哪几件事

检查来源是否仍是同一版本，reference 是否完整，answerable 是否正确，问题是否真需要多来源，以及题族是否跨集。`difficulty` 和 persona 都是生成条件或标签，需要单独校准。

`eval.py` 可以重算这些结构合同，语义参考仍需人工审核。数据通过结构检查与 Agent 在数据上表现良好，是两件独立的事。
