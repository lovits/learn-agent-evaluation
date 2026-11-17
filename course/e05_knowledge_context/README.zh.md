# e05: 找到了资料，模型看到了吗？

[e04](../e04_scoring/README.zh.md) → `e05` → [e06](../../docs/curriculum.md#06-上下文相关性与排序) → … → e16

> 把候选片段、工具回填和模型输入分别保存。

## 问题

Agent 要为 Atlas 项目写一份发布检查命令。资料在知识库里，原来的 `read_file` 只能在工作目录中按路径读文件；现在需要先找到相关资料。

加一个搜索工具就能取得候选。但如果搜索返回三条，长度预算只允许回填一条，模型究竟依据了哪些内容？只保存最终回答，或只保存检索结果，都无法分清。

## 解决方案

复用已有循环和文件工具，加入只读的 `search_knowledge`。用 TinyRAG 检索挂载目录，将候选和选中的片段分别记录，再保存下一次模型调用的输入。

![文档经 TinyRAG 检索后回填给模型](https://lovits.github.io/learn-agent-evaluation/diagrams/e05-retrieval-flow.png)

已审核参考资料走独立路径。后续评分既要知道模型收到什么，也要知道参考依据什么。

![候选、回填与实际上下文的评测范围](https://lovits.github.io/learn-agent-evaluation/diagrams/e05-context-evaluation.png)

## 工作原理

### 先固定这次读到的资料

[run_task](code.py) 开始时读入知识库文档，再保存来源清单：

```python
documents = catalog(root)
manifest = [{key: d[key] for key in ["path", "sha256"]} for d in documents]
version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
```

路径指出来源，文档哈希标识内容，清单哈希标识本次读入的知识版本。后续查询使用这批内存文本；磁盘文档中途变化，不会悄悄改变本次运行的资料。

知识库只读挂载。Agent 仍可用 `write_file` 在工作目录写入 `check.txt`，读资料和改练习文件是两条路径。

### 从文档到候选片段

[分块代码](../../eval_course/tinyrag.py) 按字符窗口切分，默认每段 1200 字符、重叠 150 字符。每段保留：

| 字段 | 作用 |
|---|---|
| path、source_sha256 | 文档来自哪里，内容是哪一版 |
| start、end | 这段文字在文档中的字符位置 |
| text、sha256 | 实际片段及其内容哈希 |
| chunk_id | 用 `path#start` 区分片段 |

位置使用 Python 字符串下标。可以沿 `文档[start:end]` 找回原文，不把字符、字节和 token 混在一起。

本地 `CorpusEmbeddings` 把词项集合转成 TF-IDF 向量。TinyRAG 原生 `VectorStore` 随后完成建库和查询：

```python
store = VectorStore(list(entries))
store.get_vector(embedding)
ranked = store.query(query, embedding, k=min(limit, len(entries)))
```

查询也被向量化，再按余弦相似度排序。相似度是两向量点积除以各自长度的乘积；本地适配在此后去掉不大于零的结果，所以返回数量可以少于 k。

这是一条词面基线：英文词和中文二字片段共享越多，越容易匹配。它没有预训练语义模型的理解能力，含“发布检查”的否定说明也可能排得很高。相似度不等于资料能回答问题。

### 搜索结果，先留全；回填内容，再选择

`search_knowledge` 的核心是：

```python
hits = retrieve(arguments["query"], limit=k, documents=documents)
selected = hits[:context_limit]
emitted = [f"[{part['chunk_id']}]\n{part['text']}" for part in selected]
```

`hits` 保留全部返回候选，`selected` 保留这次选择，`emitted` 才进入工具消息。没有选中的片段只在运行记录里，不随工具结果发送。

例如，假设候选是 A、B、C，k=3、`context_limit=1`，这一条工具消息只含 A。把 k 改大，会增加候选上限；要让更多候选进入输入，还要看回填数量。

限制作用于每次搜索。当前循环保留历史，多次搜索的片段会累积，也不会自动去重。

### 回填之后，还要发生下一次模型调用

第二课循环把工具结果追加到消息中。下一次模型成功返回后，本课保存输入的深拷贝，实际代码还保留了注入模型的练习入口：

```python
response = model(messages) if model else call_model(messages, tools=TOOLS)
model_inputs.append(copy.deepcopy(messages))
```

若最后一次搜索后正好达到步数上限，就没有下一次模型调用。工具结果虽然已经准备好，仍不能算作模型实际收到的新增上下文。

`sent_contexts` 从最后一次成功调用的输入历史中，只取带知识上下文标记的工具片段。普通文件读写结果继续留在工具记录中。这说明哪些资料成为了输入，不证明模型使用了每一条事实。

### 实际上下文与参考分别进入样本

继续使用 DeepEval 的 `LLMTestCase`：

```python
sample = to_deepeval(run)
sample.retrieval_context = sent_contexts(model_inputs)
```

本课把样本范围定为回答阶段，`retrieval_context` 保存送入该阶段的搜索片段。全部候选另存在 `retrievals.hits`，后面评价检索器时再使用。

参考来自题目事先绑定的文档。路径存在且哈希一致，才填写：

```python
sample.context = [reference["text"]] if current else None
sample.expected_output = case["reference"] if current else None
```

替换文档后，旧参考需要重新审核。代码保留新资料下的实际输入，同时把过期参考置空；不能拿 Agent 自己的回答补成参考答案。

Ragas 的 `retrieved_contexts`、`reference_contexts` 也区分实际与参考，具体字段和源码见[导读](source_walkthrough.md)。本课只构造 DeepEval 样本，相关性、召回和忠实度还没有得分。

## 本课变化

循环只多了一个可替换的工具分发入口，默认继续使用第二课工具。第五课传入带搜索的分发函数，新增的内容集中在检索、上下文选择和输入记录。

现在可以沿一条任务追踪：搜索发布规范，把命令写入工作目录，读回文件，再说明依据。[数据对应检查](eval.py)核对来源与样本字段；它不判断资料是否相关、回答是否正确。

## 试一下

```sh
python -m course.e05_knowledge_context.code
```

用 `python -m course.e05_knowledge_context.experiment` 可以固定查询和文档，比较三种参数。完整 Agent 可能自己改写查询，比较参数时要把这个变化分开。

1. 固定查询和知识版本，比较 k=1 与 k=3 的候选。
2. 用 `--k 3 --context-limit 2`，观察每次回填和最终输入怎样变化。
3. 连续搜索两次，追踪历史中保留了哪些片段。
4. 更换挂载目录中的发布规范，再看新知识版本与旧参考状态。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在能追到资料从哪里来、哪些片段成为了输入。下一课固定问题和候选列表，判断相关资料占多少，以及有用证据是否排在前面。
