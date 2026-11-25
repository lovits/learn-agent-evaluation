# e05: 知识与上下文：找到了资料，模型看到了吗？

[e04](../e04_scoring/README.zh.md) → `e05` → [e06](../e06_context_precision/README.zh.md) → … → e16

> *“检索返回了片段，不代表模型看到了它；候选列表、工具回填和实际输入要分开留痕。”*
>
> **评测层：上下文归属。** 接入只读知识库与 TinyRAG 检索，把完整候选、工具回填和模型实际收到的上下文分别记录进 DeepEval 样本。

## 问题

现在要让 Agent 为 Atlas 项目写一份发布检查命令。相关规范存放在外部知识库里，原来的 `read_file` 只能在工作目录中按路径读文件，Agent 必须先通过搜索找到资料。

给 Agent 加上一个检索工具就能拿到候选片段。但如果一次搜索返回了三条候选，受上下文长度预算限制，工具只回填了第一条，模型到底看到了哪些资料？如果最后一次搜索完刚好触达步数上限、没有触发下一轮模型调用，刚查出来的片段又算不算模型收到的上下文？只留最终回答，或者只留检索结果，都分不清这些边界。

## 解决方案

继续复用已有的循环和文件工具，为 Agent 新增一个只读的 `search_knowledge` 工具。检索底层调用 TinyRAG，把每次搜索的完整候选（`hits`）、按预算选出的片段（`selected`）和工具回填内容（`emitted`）分别落盘，并在每次模型成功返回后保存当时的完整输入历史。

![文档经 TinyRAG 检索后回填给模型](https://lovits.github.io/learn-agent-evaluation/diagrams/e05-retrieval-flow.svg?v=ef19778acb31)

已审核的参考资料单独绑定文档路径与内容哈希，走独立路径进入样本。这样后续评测既能追查模型实际看到了什么，也能核对参考依据是否已经过期。

![候选、回填与实际上下文的评测范围](https://lovits.github.io/learn-agent-evaluation/diagrams/e05-context-evaluation.svg?v=84f6dfe6dcfb)

## 工作原理

### 固定本次读入的知识快照

[run_task](code.py) 启动时先一次性读入知识库文档，计算每篇文档的哈希，再把排序后的清单聚合成一个知识版本号：

```python
documents = catalog(root)
manifest = [{key: d[key] for key in ["path", "sha256"]} for d in documents]
version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
```

`path` 标明来源，`sha256` 锁定文档内容，清单哈希标识整批知识快照。后续查询都针对这份内存里的文档集合进行，运行中途磁盘文件发生变化也不会影响本次检索。

知识库目录以只读方式挂载，Agent 依然用 `write_file` 在工作目录里写入 `check.txt`，读知识资料和写任务产物完全隔离。

### 从文档切分到 TinyRAG 检索

[分块代码](../../eval_course/tinyrag.py) 按字符窗口切分文档，默认每段 1200 字符、相邻重叠 150 字符，每段记录以下元数据：

| 字段 | 作用 |
|---|---|
| `path`、`source_sha256` | 文档路径及其内容哈希 |
| `start`、`end` | 片段在原文中的字符起止下标 |
| `text`、`sha256` | 片段正文及其内容哈希 |
| `chunk_id` | 以 `path#start` 唯一标识片段 |

`start` 和 `end` 统一采用 Python 字符串下标，随时可以通过 `文档[start:end]` 精确还原原文，避免把字符、字节和 token 混为一谈。

本地适配器 `CorpusEmbeddings` 将文本拆成英文词与中文连续二字片段，通过 TF-IDF 生成向量，再交给 TinyRAG 原生 `VectorStore` 建库并查询：

```python
store = VectorStore(list(entries))
store.get_vector(embedding)
ranked = store.query(query, embedding, k=min(limit, len(entries)))
```

查询文本经过同样的向量化后按余弦相似度排序，适配层会过滤掉相似度不大于 0 的条目，因此实际返回条数可能少于 `k`。

这是一条纯词面基线：共享的英文词和中文二字片段越多，排名越靠前。它不具备语义理解能力，即便某篇文档里出现的是否定说明，只要包含“发布检查”等高频词，依然可能排在前面。

### 完整留存候选，按预算回填片段

`search_knowledge` 的核心逻辑把“搜到了什么”和“发给了模型什么”明确拆开：

```python
hits = retrieve(arguments["query"], limit=k, documents=documents)
selected = hits[:context_limit]
emitted = [f"[{part['chunk_id']}]\n{part['text']}" for part in selected]
```

`hits` 保存本次检索返回的全部候选，`selected` 记录截断后的条目，`emitted` 才是真正放进工具返回消息里的文本。未被选中的候选保留在运行日志中，供后续评测检索器使用，不会发给模型。

假设检索返回 A、B、C 三条候选，`k=3`、`context_limit=1`，那么这条工具消息只包含 A。调大 `k` 只会放宽候选上限，想让更多片段进入模型上下文，还需要同步调整 `context_limit`。每次搜索都会独立应用这个上限，由于循环保留完整对话历史，多次搜索回填的片段会累加在历史消息中，不会自动去重。

### 确认片段进入下一次模型调用

工具结果追加到 `messages` 之后，只有真正触发了下一次模型调用，这些片段才算送进了模型输入。[code.py](code.py) 在模型每次成功返回后，对当时的 `messages` 做一次深拷贝：

```python
response = model(messages) if model else call_model(messages, tools=TOOLS)
model_inputs.append(copy.deepcopy(messages))
```

如果最后一次搜索结束时刚好达到步数上限，循环直接终止，没有后续模型调用。此时工具返回虽然已经拼好，但并未进入任何一次模型输入。

`sent_contexts` 从最后一次成功调用的输入历史里，只提取带有 `knowledge_context` 标记的工具片段，普通文件读写结果仍归属于工具轨迹。这样就能准确回答“模型在生成回答前收到了哪些知识片段”。

### 实际上下文与参考分别写入 DeepEval 样本

样本构造继续沿用 DeepEval 的 `LLMTestCase`：

```python
sample = to_deepeval(run)
sample.retrieval_context = sent_contexts(model_inputs)
```

本课将样本范围定在回答阶段，`retrieval_context` 填入真正送入模型调用的检索片段；完整的检索候选另存于 `retrievals.hits`，留给后续课程单独评价检索器。

参考资料来自题目事先绑定的来源文档，只有当路径存在且文档哈希完全匹配时才写入样本：

```python
sample.context = [reference["text"]] if current else None
sample.expected_output = case["reference"] if current else None
```

一旦知识库文档被替换，旧参考随即失效。代码会保留新资料下采集到的 `retrieval_context`，同时把过期参考置空并标记状态，等待重新审核，绝不用 Agent 自己的回答去回填参考答案。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `retrieve` / `chunks` | [tinyrag.py](../../eval_course/tinyrag.py) | 按字符窗口切分文档，调用 TinyRAG `VectorStore` 计算词面相似度并返回候选 |
| `run_task` / `dispatch` | [code.py](code.py) | 固定知识快照、分发 `search_knowledge`、分离 `hits` 与 `emitted`，并记录 `model_inputs` |
| `sent_contexts` | [code.py](code.py) | 从最后一次成功模型调用的历史消息中提取实际送入的知识片段 |
| `check_run` | [eval.py](eval.py) | 核对搜索记录、来源与片段哈希、字符偏移长度以及样本与模型输入的一致性 |

## 试一下

运行本课的完整任务：

```sh
python -m course.e05_knowledge_context.code
```

如果要固定查询和文档来对比参数组合，可以运行不调用模型的独立实验脚本 `python -m course.e05_knowledge_context.experiment`，避免 Agent 自主改写查询干扰参数观察。

动手验证四个问题：

1. 固定查询与知识版本，比较 `k=1` 和 `k=3` 的候选列表，观察 `context_limit=1` 时模型实际输入有没有变化。
2. 使用 `--k 3 --context-limit 2`，对比 `hits`、`emitted` 和最终 `model_inputs` 的差异。
3. 让 Agent 连续搜索两次，追踪对话历史中累积保留了哪些片段。
4. 替换挂载目录里的发布规范，观察新运行的知识版本号与旧参考字段会变成什么状态。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在我们已经能沿着运行记录追查每段资料的来源版本，分清候选列表、工具回填和模型实际输入。

下一课 `e06` 固定查询和候选列表，进入检索质量评测的第一步：衡量返回的片段里有多少真正有用，以及有用证据排得够不够靠前。
