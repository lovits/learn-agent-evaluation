# e04 源码导读：TinyRAG 的排序怎样进入评测

[教材](README.zh.md) · [挂载读取](../../eval_course/knowledge.py) · [检索适配](../../eval_course/tinyrag.py) · [评分](eval.py)

## 先沿 TinyRAG 走一遍

[上游 TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG) 将流程拆成读取、分块、嵌入、向量库与生成。本课保留实际 `VectorStore` 算法，生成继续交给已有 Agent 与模型入口。

```text
catalog → chunks → CorpusEmbeddings
                         ↓
               VectorStore.get_vector
                         ↓
       VectorStore.query → 来源映射 → search_knowledge
```

## query 只做三件事

[VectorBase.py](../../vendor/tinyrag/VectorBase.py) 的原生主干是：

```python
query_vector = EmbeddingModel.get_embedding(query)
result = np.array([self.get_similarity(query_vector, vector)
                   for vector in self.vectors])
return np.array(self.document)[result.argsort()[-k:][::-1]].tolist()
```

余弦比较方向，分数高的先返回。相同内容可能来自不同文档，适配层给索引条目附来源前缀，返回后映射回片段及来源哈希。

`BaseEmbeddings.cosine_similarity` 使用点积除以范数乘积，零向量返回0。课程裁掉供应商导入及修改环境变量的副作用，保留计算；来源与许可见 [TinyRAG 说明](../../vendor/tinyrag/LICENSE.md)。

## 嵌入与分块有哪些适配

`CorpusEmbeddings` 在当前语料上拟合 TF-IDF，再提供 `get_embedding`。词项沿用英文单词与中文相邻双字。这是无密钥词法向量，不把它解释成预训练语义模型。

`chunks` 按字符窗口保留空白和原文偏移。上游 `ReadFiles.get_chunk` 同时使用 token 长度与字符切片，并会去空格；本课改用明确的字符单位，避免把代码空白或长行丢掉。[上游工具副本](../../vendor/tinyrag/upstream/utils.py.txt)用于对照，不作为本课读取入口。

`sha256` 标识当前片段，`source_sha256` 标识原文件。`matches` 仅保留词项交集计数供旧调用者读取，排序由 `similarity` 决定。换文档后重建当前小型索引，不复用旧向量。

## 文档与片段是两种标注

`ranking` 先按传入 ID 去重。文档级用来源路径，片段级用 `chunk_id`；标注集合必须采用相同单位。

precision 分母为返回 ID 数，recall 分母为标注相关总数；AP 累计相关位置的 `P@i`，再按 retrieved 或 reference 口径归一化。MRR 是首相关排名倒数；二元 NDCG 用 `1/log2(rank+1)` 折扣。

已知标注非空而返回为空时规则记0；标注本身为空则无法定义召回。

## DeepEval 的判定对象

[Contextual Precision 文档](https://deepeval.com/docs/metrics-contextual-precision) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/contextual_precision.py)

`prepare_measure` 检查问题、expected_output 与 retrieval_context；`_generate_verdicts` 逐片段给有用性判断；`_calculate_score` 对相关位置累计精度，再除以本次相关数。

[Contextual Recall 文档](https://deepeval.com/docs/metrics-contextual-recall) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/contextual_recall.py)按参考声明是否能归因到片段计算 yes 比例。它的分母是声明数。

[Contextual Relevancy](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py) 不需要参考，按上下文声明是否与问题相关聚合。嵌套 `verdicts_list` 展平后计数，长片段可能贡献更多声明。

## Ragas 的参考口径

[Context Precision 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_precision/metric.py)

WithReference 逐片段判断问题、reference 与 context 的支持关系，再计算平均精度。WithoutReference 用回答替换 reference，回答自己的遗漏也可能掩盖检索缺口。

[Context Recall 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_recall/metric.py)合并上下文，按参考声明的 attributed 比例评分；无 classifications 可返回 NaN，必要输入为空则更早报错。

现代 collections 使用 `InstructorBaseRagasLLM`，与旧接口分开适配。模型分数、未定义和请求错误分别记录；相似度只影响召回，不能代替这些质量判断。
