# e05 源码导读：资料怎样进入模型输入

[教材](README.zh.md) · [本课入口](code.py) · [TinyRAG 适配](../../eval_course/tinyrag.py)

## 本课调用链

`run_task` 启动后先调用 `catalog(root)` 一次性读入挂载目录中的全部文档，生成包含路径与 `sha256` 的清单并计算总版本号，随后把这批内存文档交给 `search_knowledge` 的分发函数 `dispatch`。第 2 课的 `agent_loop` 只增加了一个默认值为 `execute` 的 `execute_tool` 参数，本课传入新的 `dispatch`，从而完整复用原有的循环逻辑、文件工具和路径权限校验。

`dispatch` 收到 `search_knowledge` 调用后执行 `retrieve`，将完整候选写入 `retrievals.hits`，再截取前 `context_limit` 条拼装为 `emitted` 放入工具返回值。其余候选只保存在运行日志里，不会通过工具消息传给模型。

`next_response` 调用原有模型接口发送带新工具定义的消息，并在成功返回后把当时的 `messages` 深拷贝进 `model_inputs`。`sent_contexts` 读取最后一次成功调用的输入历史，仅筛选 `kind == "knowledge_context"` 的工具片段，普通文件读写仍留在 `tools_called` 中。多次搜索回填的片段会随着对话历史累积，当前循环不做上下文压缩或去重。

## TinyRAG 的实际调用路径

本课集成固定版本的 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG)（提交 `a5ae08d`），源码副本、改动记录与 CC BY-NC-SA 4.0 许可均保存在 [vendor/tinyrag](../../vendor/tinyrag/provenance.json)。

上游 [VectorBase.py](https://github.com/datawhalechina/tiny-universe/blob/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG/RAG/VectorBase.py) 的检索链路非常直接：`get_vector` 为每段文本计算向量；`query` 对查询文本向量化后调用 `get_similarity` 计算余弦相似度，再用 `argsort` 从高到低取前 `k` 条。遇到零向量时，本地无副作用的 `BaseEmbeddings` 适配层直接返回 `0`。

`retrieve` 原样调用 `VectorStore.get_vector`、`query` 和 `get_similarity`，外层负责文档切分、归属信息绑定以及过滤掉相似度不大于 0 的条目。由于上游 `query` 只返回文本字符串，本地在建库前为每段文本加上片段编号前缀，确保正文相同的不同来源文档依然可以区分。

向量化由本地 `CorpusEmbeddings` 完成：它提取英文单词和中文连续二字片段，去重后交给 `TfidfVectorizer`。因为词项经过了去重，同一词在片段内重复出现不会增加词频权重，排序主要取决于词项是否出现以及语料级的逆文档频率。片段编号前缀同样参与向量化，路径中的关键词也会影响得分。这套方案是轻量的词面基线，每次检索都基于本次读入的文档重建内存索引，适合教学规模的语料；语料扩大后再按需引入持久化索引。

## 分块与知识版本

`chunks` 默认按 1200 个字符切分文档，相邻窗口重叠 150 个字符。`start` 和 `end` 记录 Python 字符串偏移，`text` 保留原始切片，`chunk_id` 记为 `path#start`。`source_sha256` 标识整篇源文档，`sha256` 标识当前切片。

`run_task` 对按路径排序后的文档清单再求一次哈希，得到本次运行的知识快照版本。这个版本号只标识读入的文档内容，检索参数 `k` 与 `context_limit` 另存于 `retrieval_settings`。文档按顺序读入内存后即保持固定，运行中途修改磁盘文件不会改变内存中的检索语料。

题目参考绑定了 `source.path` 和 `source.sha256`。当实际读入的文档哈希与题目不一致时，运行仍正常记录 `retrieval_context`，但样本中的参考字段会被置空，并将 `reference_status` 标为 `source_changed_or_missing`，防止用过期参考去评判新资料下的回答。

## DeepEval 的样本字段与评价范围

本课对照 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，样本概念见 [Single-Turn Test Case](https://deepeval.com/docs/evaluation-test-cases)。

[LLMTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/llm_test_case.py) 将参考上下文和检索上下文拆成两个独立字段：

- `context`：存放已审核的参考资料，来源为题目绑定的基准文档。
- `retrieval_context`：存放搜索工具实际送入成功模型调用的知识片段。

两者含义不同，不能互相补填。本课构造的样本面向回答阶段，因此 `retrieval_context` 只收录真正送进模型输入的片段；后续课程评价检索器本身时，则会从完整保存的 `hits` 出发构造对应范围的输入。

代码先复用 `to_deepeval` 填入任务、最终回答和工具调用记录，再补充 `retrieval_context`、`context` 与 `expected_output`。本课聚焦于把数据管线与样本字段接通，相关性、召回和忠实度指标将在后续课程依次接入。

[experiment.py](experiment.py) 固定查询与单次读入的文档，直接运行 TinyRAG 对比三组 `k` 与 `context_limit` 组合，剥离了 Agent 自主改写查询带来的变量。

## 本课检查的边界

[eval.py](eval.py) 中的 `check_run` 核对五项基础链路：是否观察到检索调用、候选的来源哈希是否与知识清单一致、片段内容哈希是否吻合、字符偏移长度是否等于正文长度，以及样本里的 `retrieval_context` 是否严格等于最后一次成功模型调用收到的知识片段。这些检查保证数据归属准确无误；至于检索到的片段是否相关、有没有漏掉关键事实，将在第 6 课和第 7 课展开评测。

[样本与评测记录](assessment.md)
