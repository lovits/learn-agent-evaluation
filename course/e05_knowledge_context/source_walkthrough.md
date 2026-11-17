# e05 源码导读：资料怎样进入模型输入

[教材](README.zh.md) · [本课入口](code.py) · [TinyRAG 适配](../../eval_course/tinyrag.py)

## 本课调用链

`run_task` 一次读入挂载目录中的文本，保存路径与内容哈希清单，再把它交给 `search_knowledge` 的分发函数。第二课循环只增加 `execute_tool=execute` 参数，默认仍用原有工具；第五课传入包含检索的新分发函数，循环、文件工具和路径权限继续复用。

`dispatch` 调用 `retrieve`，把完整结果保留在 `retrievals.hits`，只把前 `context_limit` 条格式化为 `emitted`，放进工具返回。其余候选没有通过这个工具送给模型。

`next_response` 用带新工具的原有模型接口请求下一步，成功返回后保存这次输入历史的深拷贝。`sent_contexts` 从最后一次成功调用的输入中取搜索片段；文件读写结果仍在 `tools_called`，不自动冒充检索资料。多次搜索的片段会随历史累积，本课没有上下文压缩。

## TinyRAG：实际调用了什么

固定来源为 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG)，提交 `a5ae08d`。副本、修改说明与许可在 [vendor/tinyrag](../../vendor/tinyrag/provenance.json)，保留上游 CC BY-NC-SA 4.0 许可。

[VectorBase.py](https://github.com/datawhalechina/tiny-universe/blob/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG/RAG/VectorBase.py) 的路径很短：`get_vector` 为各文本取向量；`query` 为查询取向量，调用 `get_similarity` 计算余弦相似度，用 `argsort` 从高到低取前 k 个文本。零向量的余弦值由本地无副作用的 `BaseEmbeddings` 适配返回 0。

本课没有把 TinyRAG 的算法换成自己的排序器。`retrieve` 调用原生 `VectorStore.get_vector`、`query` 和 `get_similarity`；外层负责分块、归属信息和正相似度过滤。上游返回文本，本地给文本加片段编号前缀，使相同正文的不同来源仍可区分。

向量来自 `CorpusEmbeddings`。它把英文词和中文连续二字片段组成词项集合，交给 `TfidfVectorizer`。词项先去重，因此重复次数不再贡献额外词频；主要依赖出现与否和语料的逆文档频率。编号前缀也参与向量化，来源词可能影响排名。这里是词面基线，不是预训练语义嵌入模型，也不理解否定句。

每次检索都用本次运行读入的文档重建小索引，适合教学规模。扩大语料后可考虑持久化索引；本课不引入另一套向量服务。

## 分块与版本

`chunks` 默认按 1200 个字符切分，相邻窗口重叠 150 个字符。`start`、`end` 为字符偏移，不是 token 或字节位置；`text` 保留原文，片段 ID 为 `path#start`。`source_sha256` 标识文档内容，`sha256` 标识这一段内容。

`run_task` 对排序后的文档路径与内容哈希清单再求哈希，得到本次知识快照版本。它标识读到的文档内容，不包含检索算法参数；k 和每次回填数量另存 `retrieval_settings`，切分、向量化实现见本版本课程代码。文档按顺序读入，不声称目录读取是一个原子事务。读入后的文本保持固定，中途修改磁盘文件不会改变本次查询使用的内存文本。

题目里的参考绑定 `source.path` 和 `source.sha256`。版本不符时，实际上下文仍照常保存，但参考字段置空，`reference_status` 标为 `source_changed_or_missing`。这延续第三课的来源审核要求，不能拿过期参考判断新资料下的回答。

## DeepEval：样本字段与评价范围

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念见 [Single-Turn Test Case](https://deepeval.com/docs/evaluation-test-cases)。

[LLMTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py) 分别定义 `context` 和 `retrieval_context`。本课 `context` 来自已审核参考资料；`retrieval_context` 来自搜索工具实际进入成功模型调用的片段。两者可能不同，不能相互补填。

本样本的评价范围是回答阶段，所以实际送入模型的片段进入 `retrieval_context`。后续评价检索器时，将从独立保留的 `hits` 构造相应范围的指标输入，不能只看裁剪后的片段就声称评价了完整候选列表。

代码先复用 `to_deepeval` 保存任务、实际回答和工具，再填写参考、实际检索上下文。本课没有调用相关性、召回或忠实度指标；构造出一个 SDK 样本，并不代表这些质量已经得分。

## Ragas：参考与实际同样需要分开

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，概念见 [Evaluation Sample](https://docs.ragas.io/en/stable/concepts/components/eval_sample/)。

[dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py) 的 `SingleTurnSample` 分开定义 `retrieved_contexts`、`reference_contexts`、实际回答 `response` 和参考答案 `reference`，还有两类 context ID。它们提供表达实际与参考的字段，不会自动证明来源正确或上下文确实被模型读取。

本课只对照这组概念，没有运行 Ragas，也不为同一过程再导出第二份框架样本。DeepEval 的 `context` 与 Ragas 的参考上下文字段可作概念对应；具体指标使用哪些字段，仍要逐个读实现。

[experiment.py](experiment.py) 固定同一查询和一次读入的文档，分别执行三种 k/回填数量组合。它只运行 TinyRAG，不调用模型，避免把 Agent 自主改写查询的影响混进参数比较。

## 本课检查的边界

`check_run` 核对搜索记录、文档/片段哈希、偏移长度和样本到模型输入的对应。即使这些都一致，检索到的也可能是无用说明。真正相关性留到第六课，覆盖与召回留到第七课，回答是否依赖这些证据继续由后续指标判断。
