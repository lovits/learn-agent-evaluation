# e04: 检索质量 — 用 TinyRAG 找资料，再看找得怎样

[课程](../../README.md) · [上一课](../e03_judges/README.zh.md) · [下一课](../e05_faithfulness/README.zh.md) · [源码导读](source_walkthrough.md)

> 向量相似度负责排序，评测负责判断资料是否有用。

## 答案分散在两份文档里

Agent 要为 `POST /upload` 编写接入说明。`auth.md` 写认证头，`limits.md` 写最大1048576字节及超限状态413。

只拿到认证文档，返回内容完全切题，却仍答不出后两项。本课接入 Datawhale TinyRAG，让已有 Agent 通过 `search_knowledge` 读取挂载知识库，再分别评价相关、覆盖与排序。

## TinyRAG 只有几块

```text
只读文档 → 切成片段 → 文本向量 → VectorStore
                                      ↑
问题 → 查询向量 → 余弦相似度 → top-k 片段 → Agent
```

TinyRAG 的核心在于把文档与查询放到相同向量空间。`VectorStore` 保存向量，用余弦相似度排序，再返回最接近的片段。

本课嵌入接口使用本地 TF-IDF：按语料中的词项及稀有程度形成向量，无需模型密钥。它是词法向量基线，不具备神经嵌入的同义理解；更换嵌入实现时，向量库的查询接口仍可复用。

## 从挂载文件到片段

[`catalog`](../../eval_course/knowledge.py) 读取只读挂载里的 Markdown 和文本。适配层按字符窗口分块，保留原文、起止位置和来源：

```python
text = doc["text"][start : start + size]
```

每个片段有 `chunk_id`、片段哈希和 `source_sha256`。同一文档可以产生多个片段，评价片段覆盖和评价文档覆盖时，要使用不同的 ID 单位。

课程窗口为1200字符、重叠150字符。短规范只有一个片段；长文档相邻窗口保留重叠。这里明确按字符计量，源码导读会对照上游分块方法。

## 建向量，再按问题查询

[`retrieve`](../../eval_course/tinyrag.py) 把片段交给实际 TinyRAG `VectorStore`：

```python
embedding = CorpusEmbeddings(list(entries))
store = VectorStore(list(entries))
store.get_vector(embedding)
ranked = store.query(query, embedding, k=min(limit, len(entries)))
```

`get_vector` 对片段编码；`query` 对问题编码，再与已存向量比较。返回值映射回来源字段，并过滤没有向量重合的零相似度结果。

为了让课程数据保持透明，这个小语料在查询时重建内存索引，更换挂载即可读取新内容。TinyRAG 也提供持久化接口，使用它时还要检查索引与文档、分块和嵌入版本是否一致。

## Agent 循环只接一个新工具

[`dispatch`](code.py) 截获 `search_knowledge`，其他动作继续交给前课。检索结果作为普通工具结果回填，Agent 再据此写接入说明。

相似度是召回排序依据。它并不直接知道本题必须包含认证头、字节上限和状态码，不能当成业务正确率。

## 相关与找全分别计算

标注相关文档为 `{auth, limits}`，手算几种返回：

| 返回 | 文档精度 | 文档召回 |
|---|---:|---:|
| `[auth]` | 1 | 1/2 |
| `[auth, limits]` | 1 | 1 |
| `[auth, limits, noise]` | 2/3 | 1 |

精度的分母是返回数，召回的分母是应找回的相关总数。`ranking` 在文档级先按来源 ID 去重；若要评价长文片段，应改用 `chunk_id` 并准备相应标注。

## 排序还改变什么

`[auth, limits, noise]` 与 `[noise, auth, limits]` 的精度和召回相同，相关位置的平均精度却分别为1与 `(1/2 + 2/3)/2 = 7/12`。

`ap_retrieved` 除以本次相关命中数，`ap_reference` 除以全部标注相关数。MRR 只看首个相关位置，NDCG 给靠后位置打折。

DeepEval 与 Ragas 的 Context Precision 让模型判断片段是否支持回答，再按顺序聚合；Context Recall 检查参考声明被支持的比例。DeepEval Contextual Relevancy 则检查上下文声明是否切题。

认证、限额和413若拆成三条声明，只找到认证时，声明召回可能为1/3，而文档召回是1/2。先辨认单位，再解释分数。

## 试一下

让 TinyRAG 检索同一个问题，再分别删掉限额命中、把噪声移到前面。哪些分数改变，哪些保持不变？

再把一份长文切成多个片段。文档已经命中，但关键片段没返回时，文档召回能发现什么，片段召回又能发现什么？

[TinyRAG 适配](../../eval_course/tinyrag.py) · [原生向量库](../../vendor/tinyrag/VectorBase.py) · [评分](eval.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

TinyRAG 找到资料以后，Agent 仍可能补出文档没有的重试次数。下一课逐条检查回答是否得到这些证据支持。
