# e07: 上下文覆盖与召回：资料都相关，为什么还答不全？

[e06](../e06_context_precision/README.zh.md) → `e07` → [e08](../e08_faithfulness/README.zh.md) → … → e16

> *“返回的资料哪怕条条相关，只要漏掉一条必要依据，模型依然答不全；先把该找到的事实列成清单，再逐条检查上下文覆盖。”*
>
> **评测层：上下文召回。** 把参考答案拆成带来源映射的必要事实，分别计算文档级与事实级覆盖率，并接入 DeepEval 的 `ContextualRecallMetric` 对参考句逐条做上下文归因。

## 问题

把上一课的 Atlas 问题再往前推一步，同时问三件事：发布前运行什么检查、满足什么条件才能发布，以及审计日志保留多久？

发布规范 `atlas/release.md` 能回答前两项。如果检索器只返回这一份资料，列表里的每一句话都高度相关，精度拿到满分，却找不到审计日志的保留天数。上一课的精度和排序只盯住“返回列表里有什么”；要检查列表之外还漏掉了什么，就必须先列出一份“应该找到的事实清单”。

## 解决方案

把参考答案拆成带来源路径的独立事实，写进 [cases.jsonl](cases.jsonl)。接着从 TinyRAG 检索出的候选中取出两份必要文档，构造三组对照条件：`complete` 保留完整两份文档；`missing_logs` 去掉 `atlas/logs.md` 而参考清单不变；`incomplete_reference` 保持同样的缺日志上下文，但从参考清单里删掉日志天数。

![从参考事实对照实际上下文，指出覆盖与遗漏](https://lovits.github.io/learn-agent-evaluation/diagrams/e07-coverage-flow.svg?v=e7cf7a7b6a74)

已知来源映射适合快速手算并精准指出缺哪条证据；需要在任意文本之间判断语义归因时，再把 `expected_output` 与 `retrieval_context` 交给 DeepEval 的 `ContextualRecallMetric`。

![DeepEval 逐参考句判断归因并汇总召回](https://lovits.github.io/learn-agent-evaluation/diagrams/e07-scoring-flow.svg?v=18fa6eb2bcff)

## 工作原理

### 先列出应该找到的必要事实

[cases.jsonl](cases.jsonl) 把本课问题对应的参考拆成三条有出处的必要事实：

| 事实编号 | 必要内容 | 来源文档 |
|---|---|---|
| `check_command` | Atlas 补丁发布前在项目根目录运行 `python -m pytest -q`。 | `atlas/release.md` |
| `release_gate` | 全部检查通过才可提交发布，失败时先修复，不跳过失败项。 | `atlas/release.md` |
| `log_days` | Atlas 审计日志保留 14 天。 | `atlas/logs.md` |

每条事实对应问题的一个具体子要求，并绑定到明确的文档出处。只有清单本身完整，后续召回率才能反映真实的检索缺口。

[prepare](code.py) 先校验 `atlas/release.md` 与 `atlas/logs.md` 的内容哈希，运行 TinyRAG 取得候选后筛出这两份必要文档组成 `complete`；随后在内存中移出 `atlas/logs.md` 构造 `missing_logs`，再将参考中的 `log_days` 一并移除得到 `incomplete_reference`。

### 数文档，还是数事实

设 `required` 是必须覆盖的项目集合，`found` 是实际找到的项目集合，[eval.py](eval.py) 中的 `coverage` 用交集计算覆盖比例：

```python
def coverage(required, found):
    required, found = set(required), set(found)
    return len(required & found) / len(required) if required else None
```

分母始终来自 `required`。输入经过 `set` 去重后，重复命中同一项目不会多算分，无关文档也不会拉高覆盖率。

根据统计单位取文档路径还是参考事实编号，同一份上下文会算出两种召回率：

```text
文档召回 = 找到的必要文档数 / 全部必要文档数
事实召回 = 覆盖的参考事实数 / 全部参考事实数
```

以 `missing_logs` 为例，上下文只留下 `atlas/release.md`：两份必要文档找到了 `1` 份，文档召回是 `1/2`；三条必要事实覆盖了测试命令和发布条件两条，事实召回则是 `2/3`。因为同一份文档承载了多条事实，不同粒度的计数权重自然不同。

此时返回列表的文档精度仍然是 `1.0`，因为仅有的那份文档确实有用。这也说明高精确率只证明返回列表干净，并不能排除关键证据遗漏。

### 路径查表只适用于当前短文档映射

本课的两份文档都短于单个切分窗口，每篇文档正好占一个完整片段，因此 [summarize](code.py) 可以直接按文档路径查表统计覆盖：

```python
paths = {p["path"] for p in parts}
covered = [f["id"] for f in facts if f["source"] in paths]
```

同时保存的 `missing` 列表会直接列出尚未覆盖的事实文本，方便定位缺口。

一旦面对切分成多个片段的长文档，命中文档路径只说明找到了该文档的某一部分，并不能保证所需事实就在当前片段里。长文档场景需要把映射粒度细化到具体片段，或者直接对片段正文做语义归因。

### 用 ContextualRecallMetric 对参考句逐条归因

调用 DeepEval 原生指标时，`code.py` 把参考事实按换行拼成待核对的文本放入 `expected_output`：

```python
sample = LLMTestCase(
    input=case["query"],
    expected_output="\n".join(f["text"] for f in facts),
    retrieval_context=[p["text"] for p in parts],
)
```

本课评测已经固定的检索上下文，不重新生成回答。当前 DeepEval 版本的 `ContextualRecallMetric.measure` 只读取 `expected_output` 与 `retrieval_context`，因此 `actual_output` 留空。

[judge_recall](eval.py) 复用第 4 课的裁判适配器与状态包装函数调用原生指标：

```python
metric = ContextualRecallMetric(
    model=model, eval_mode="llm", async_mode=False, include_reason=False
)
result = score(metric, sample)
```

提示词让裁判逐句分析 `expected_output`，能从 `retrieval_context` 归因出处的标为 `yes`，找不到支持的标为 `no`，最后由 SDK 计算：

```text
Contextual Recall = yes 数 / 全部有效裁决数
```

`include_reason=False` 只省去了最后生成总分解释的那一次模型调用，每条裁决里的定位理由依然完整保留。编写参考时尽量把多条事实拆成清晰独立的句子；如果把测试命令、发布条件和日志期限揉进同一长句，裁判模型对“部分支持”的切分方式就会直接牵动得分，审查结果时要结合 `verdicts` 一同核对。

### 参考变短，分母也会跟着缩水

对比 `missing_logs` 与 `incomplete_reference`：两者喂给模型的上下文一模一样（都缺少 `atlas/logs.md`），只是后者把参考里的 `log_days` 删掉了。

只要求检查命令和发布条件时，仅凭 `atlas/release.md` 就覆盖了全部 `2` 条要求，召回率立刻从 `2/3` 变成 `1.0`。检索器并没有任何改进，分数上升完全来自评测标准缩水。因此，对比不同版本的检索能力时必须锁定同一份参考清单；维护数据集时，也要先对照用户问题核查参考是否遗漏关键要求。

### 空参考和空裁决不能算满分

当 `required` 为空时，`coverage` 返回 `None` 表示未定义；只有存在必要项目且一条未命中时，才返回有效的 `0.0`。

在语义评测入口中，`judge_recall` 先拦截空白 `expected_output`，直接返回 `status="error"` 与空分数。同时，如果模型裁判返回的 `verdicts` 列表为空，适配层同样标记为 `status="error"` 并置空 `score` 与 `passed`，只有非空裁决全部为 `no` 时才算有效的 `0.0` 分。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `prepare` | [code.py](code.py) | 校验文档哈希、运行 TinyRAG 并构造 `complete`、`missing_logs`、`incomplete_reference` |
| `summarize` | [code.py](code.py) | 基于来源路径计算文档召回、事实召回、文档精度与 `missing` 清单 |
| `coverage` | [eval.py](eval.py) | 对去重后的必要集与命中集求交集覆盖率，空必要集返回 `None` |
| `judge_recall` | [eval.py](eval.py) | 调用 `ContextualRecallMetric`，拦截空白参考与空裁决列表 |
| `cases.jsonl` | [cases.jsonl](cases.jsonl) | 定义用户问题、三条带来源路径的参考事实以及来源文档哈希 |

## 试一下

运行本课脚本，对比三组条件下的文档召回、事实召回与遗漏清单：

```sh
python -m course.e07_context_recall.code
```

加上 `--judge` 参数可调用 DeepEval 原生 `ContextualRecallMetric`，查看每条参考句的逐项归因裁决与理由：

```sh
python -m course.e07_context_recall.code --judge
```

动手验证四个问题：

1. 查看 `missing_logs` 的 `missing` 字段，确认它精准列出了哪一条遗漏事实。
2. 对比 `missing_logs` 下的 `document_recall` 与 `fact_recall`，说明两个分母为什么给出不同分数。
3. 比较 `missing_logs` 与 `incomplete_reference`：上下文完全相同，分数为什么从 `2/3` 升到 `1.0`？
4. 使用 `--judge` 运行真实裁判，核对每组条件分别拆出了几条裁决，以及理由指向了哪一个上下文节点。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

经过前两课的检验，我们已经能判断检索回来的片段够不够干净、排得够不够靠前，以及必要证据有没有找齐。可即便把完整资料送进了模型输入，模型在生成回答时依然可能篡改数字，或者说出资料里压根没提过的细节。

下一课 `e08` 进入生成阶段评测，用 `FaithfulnessMetric` 把回答拆成独立声明，逐条核对上下文是否提供依据。
