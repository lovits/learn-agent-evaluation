# 第8课源码导读：从生成器到可审核数据

本课只增加离线数据生成与审核，不改变前七课Agent。候选问题与参考答案由生成器产生，目标Agent没有执行；`actual_output`保持空，人工批准数为0。模型生成、自动参考审核、目标Agent和未来模拟用户是不同角色。

## 文档入口与版本

[DeepEval合成数据指南](https://deepeval.com/guides/guides-using-synthesizer)说明从文档切块、组织上下文、生成与演化的整体路线，也支持从已经准备好的上下文开始。本课选择后者，使原始证据范围可以逐文件核对。在线指南可能展示不同版本的参数形式，本课以固定源码中的配置对象为准。

[Ragas数据生成概念](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/)区分单跳、多跳和具体/抽象问题，并介绍图谱与场景生成。[自定义入口页](https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/)目前只有概述，不能替代API源码。本课原生实跑具体单跳与具体多跳，未运行默认分布中的抽象多跳。

DeepEval固定4.3.4、提交`34db63dd005ebc9a905c8ef4741ae0687c93c14c`；Ragas固定0.4.4、提交`8c63f10d500c44efbf24fdb9e2920de2104c321c`。源码阅读清单和哈希见[阅读记录](../../references/e08-reading.json)。

## DeepEval：质量配置不等于最终拒收

[原生Synthesizer](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/synthesizer.py)与[配置](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/synthesizer/config.py)是本课依据。

1. `Synthesizer.__init__`接收模型、`FiltrationConfig`、`EvolutionConfig`和`StylingConfig`。显式传入critic模型，避免使用隐式的其他模型服务。
2. `generate_goldens_from_contexts`在同步分支先调用`generate_synthetic_inputs`模板，`_generate_inputs`要求`SyntheticDataList`，其中每条有input与可选used_source_files。
3. `_rewrite_inputs`请critic返回`InputFeedback(score, feedback)`。达到阈值时结束重写；未达到则重写。这个固定版本在达到最大重试数后仍把最后输入加入列表，不自动拒收。记录的score是当次critic分数，不是之后演化、风格改写完成后的重新评分。
4. `_evolve_input`按配置选择演化提示词。默认方法还包括具体化、约束、比较、假设和广度等；本课实际分别固定Reasoning和Multi-context各一次，便于解释。
5. 如配置风格，再经`SyntheticData`改写；创建`Golden`后，根据当前问题与上下文生成expected_output。`Golden`的context及source元数据保留，但used_source_files来自较早阶段，可能为空，也不证明最终问题确实使用每个来源。

本轮两条Golden的synthetic_input_quality为0.4、0.2，但都继续完成了演化和参考答案生成。这说明该字段不能直接当成最终题目质量，也不能以“已配置过滤”宣布数据已经通过审核。

`GeneratorModel`复用前课DeepEval模型接口，并将所需JSON schema显式加入提示词；`_generate`期望`Response.response`时也能得到正确结构。原生同步入口实跑；异步入口通过并发任务生成上下文，原理按固定源码理解，没有把同步实验说成异步吞吐测试。

## Ragas：规则构图，原生场景与问答生成

[图模型](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/graph.py)、[生成编排](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/generate.py)。

`build_graph`对两份实际文档提取`POST /upload`接口词，构造原生DOCUMENT节点和entities_overlap关系。节点携带page_content、entities、source_id；关系保存overlapped_items。没有共同接口就报错，不凭空连边。这是课程自己的规则构图，不是Ragas默认的分块、LLM实体抽取、嵌入和相似度变换流水线；本课没有运行embedding模型。

`TestsetGenerator.generate`接受已经构好的knowledge_graph、明确的persona_list和query_distribution。调用这条路径时没有使用embedding_model，所以本课传None；不要把它移用到需要默认embedding transforms的文档入口。

本课persona是明确编写的Python客户端开发者，不是模型推断出的真实用户。原生流程先按分布分配数量，再生成scenario，再生成sample，最后构造Testset。场景含节点、persona、查询风格与长度；这些元数据不等于经过人工校准的难度等级。本课difficulty仅为教学标签。

[具体单跳](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/single_hop/specific.py)挑选含entities的节点，用ThemesPersonasMatchingPrompt建立persona与主题映射；[单跳基类](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/single_hop/base.py)再要求QueryAnswerGenerationPrompt返回query、answer，保存reference_contexts。

[具体多跳](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/multi_hop/specific.py)按entities_overlap找两节点关系；[多跳基类](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/testset/synthesizers/multi_hop/base.py)组织组合与风格，用两份带hop标签的上下文生成问题和参考。两个上下文并不能保证问题必须跨来源推理，因此还有独立的requires_multiple_sources审核，仍需人工复核。

## 候选结构、去重与来源

`candidate`只准备question、reference、evidence、family、query_type、difficulty、answerable、origin和空actual_output。DeepEval样本保存提供给生成器的证据；Ragas根据实际reference_contexts映射回来源。来源ID和正文哈希共同记录版本，不能仅用路径证明版本相同。

`structure_errors`检查字段、来源和哈希等合同；它不能仅凭哈希证明资料真实，也不是任意JSON输入的完整schema库。`question_key`用Unicode归一化、大小写和标点归一化识别重复，保留数值差异。它不识别所有同义改写或中英翻译；`near_duplicates`的词项Jaccard只提供复核建议，不自动删题。

相同规范化问题若跨family出现，两个都隔离，避免给相同任务套不同标签后跨集。相同family中的重复保留第一条，后续记录duplicate_of和原因。

## 自动审核、分组与独立验收

生成器使用8769入口；参考审核使用8768裁判入口。它检查reference是否受给定证据支持，以及多跳题是否真的需要多个来源。它是独立的一次模型判断，不是外部真值，也不意味着人工批准。本次生成器与审核仍共用本机登录模型来源，不能称为模型独立性实验。

FAMILY_SPLITS把上传合同放开发集，目录任务放校准集，编辑任务放留出集。同一题族不跨集，先冻结划分再比较版本。这里的编程种子来自已经公开讲过的第1、2课，故只是划分演示，不是严格盲测，也不估计泛化能力。自动参考审核通过的样本仍为pending_human；真实基准还需要独立题族、难度覆盖、人工确认和冻结版本。

`eval.py`在断网verifier中重算数据合同，检查两套原生生成、反例隔离、来源哈希、题族划分、待审状态与无伪造Agent输出。它不再次调用模型、不执行候选编程任务，也不能替代人工参考审核。程序返回通过表示本课小型数据流程合同成立，不表示Agent准确率或数据已获得人工批准。

完整记录见[实验摘要](run_summary.md)、[原生输出与请求](example_report.json)、[独立合同验收](grade_report.json)、[实际运行环境](runtime_evidence.json)。
