# e10: RAG 诊断：答案错了，先改哪一层？

[e09](../e09_answer_quality/README.zh.md) → `e10` → [e11](../e11_tool_quality/README.zh.md) → … → e16

> *“只看最终回答往往分不清是资料缺了、没搜到，还是没送进模型；沿阶段留痕逐层对照，才能把问题归到正确位置。”*
>
> **评测层：RAG 链路诊断。** 冻结第 9 课的真实检索查询与生成输入，逐段记录知识快照、检索输出和组装上下文，用 `first_gap` 定位最早证据缺口，再用 DeepEval 的 `FaithfulnessMetric`、`task_metric`（`GEval`）与 `noise_fraction` 分层诊断生成表现与噪声归因。

## 问题

Agent 没能答出正确的发布命令 `python -m pytest -q`。导致这个问题的原因可能落在完全不同的环节：知识库里压根缺少 `atlas/release.md`、知识库文档还是旧版本、检索器没能把规范排进候选列表、检索器明明返回了规范却在组装上下文时被截断，或者正确规范与干扰备忘一起送进模型后干扰了生成。

如果仅凭最终回答“只看到了日志资料”，或者只看最后送进模型的 `retrieval_context`，前面几种情况看起来几乎一模一样。若问题出在上下文组装被截断，去调优生成提示词或微调模型都改错了地方。

## 解决方案

冻结第 9 课真实运行保存下来的检索查询与最后一次生成输入，构造七组受控条件（基线、资料缺失、检索漏召回、组装丢弃、过期资料、无关噪声、冲突备忘）。每次只在内存快照或下游筛选环节改动一处，保留各阶段输出后，禁用工具重放同一回合的生成过程。

![从知识库到生成回答，保留各阶段快照](https://lovits.github.io/learn-agent-evaluation/diagrams/e10-pipeline-flow.svg?v=aa9bdc972a7b)

评分阶段先调用 `first_gap` 逐层排查证据最早在哪里缺失或版本失配，再用 DeepEval 的 `FaithfulnessMetric`（第 8 课）和 `task_metric`（第 9 课的 `GEval`）检查模型在收到这批上下文后是如何生成与取舍的，并用 `noise_fraction` 量化错误陈述与不同资料类别的关联比例。

![沿来源、检索与组装逐层检查证据缺口](https://lovits.github.io/learn-agent-evaluation/diagrams/e10-diagnosis-flow.svg?v=bf1b36dcb766)

## 工作原理

### 一条链路，七种单点改动

[prepare](code.py) 先校验第 9 课记录文件与基准文档的 SHA-256，确认输入基线保持冻结，再固定取出真实运行中的首条检索查询，基于 TinyRAG 重建七组控制条件。挂载在磁盘上的原始知识库文件保持不变，所有缺失与改写都在内存拷贝的 `documents`、检索输出或组装结果中完成：

| 条件 | 改动位置 | 留痕核对对象 |
|---|---|---|
| `baseline` | 无改动，保留完整发布与日志资料 | 基线各阶段快照与哈希 |
| `source_missing` | 检索前从内存 `documents` 移除 `atlas/release.md` | 知识库清单与候选列表 |
| `retrieval_miss` | TinyRAG 返回 `native_hits` 后过滤掉 `atlas/release.md` | 原始候选 `native_hits` 与 `retrieved` |
| `assembly_drop` | `retrieved` 保留规范，组装 `selected` 时将其剔除 | `retrieved` 与最终 `contexts` |
| `stale_source` | 内存快照将命令改成 `python -m unittest` 并重算哈希 | 文档 SHA-256 与当前参考哈希 |
| `noise` | 组装结束后追加一条无关天气备忘 | 原上下文与 `constructed/noise.md#0` |
| `conflict` | 组装结束后追加两条规则相反的旧备忘 | 冲突来源与主规范优先级 |

把 `retrieval_miss` 和 `assembly_drop` 拆成两步实现，目的是把原生检索命中与下游处理分开留痕：

```python
native_hits = retrieve(trace["retrievals"][0]["query"], limit=3, documents=documents)
retrieved = (
    [p for p in native_hits if p["path"] != spec["source"]["path"]]
    if fault == "retrieval_miss"
    else native_hits
)
selected = retrieved[:2]
if fault == "assembly_drop":
    selected = [p for p in selected if p["path"] != spec["source"]["path"]]
```

在 `retrieval_miss` 中，TinyRAG 本身的 `native_hits` 其实命中了发布规范，过滤发生在模拟的检索输出层；在 `assembly_drop` 中，规范已经进入 `retrieved`，只是在组装送入模型的 `selected` 时被丢弃。把这三份中间列表分别落盘，就能分清故障究竟属于检索召回还是上下文组装。

### 沿阶段顺序定位第一个证据缺口

拿到各阶段快照后，[eval.py](eval.py) 中的 `first_gap` 按证据流动顺序依次核对目标文档：

```python
def first_gap(documents, retrieved, selected, source):
    document = next((d for d in documents if d["path"] == source["path"]), None)
    if document is None:
        return "source_missing"
    if document["sha256"] != source["sha256"]:
        return "source_version"
    if not any(p["path"] == source["path"] for p in retrieved):
        return "retrieval_output"
    if not any(p["path"] == source["path"] for p in selected):
        return "context_assembly"
    return None
```

函数返回最先发现缺口的阶段名，方便定位下一步优先排查的位置：

- `source_missing` 或 `source_version`：说明数据源本身缺文档或版本哈希对不上。需要注意，哈希变化只代表内容与参考绑定版本不同，可能是语料过期（如本课故意构造的 `stale_source`），也可能是文档已正当更新而参考标准尚未同步，需要人工审核确认。
- `retrieval_output` 或 `context_assembly`：说明知识库里有正确版本，但证据在检索输出或上下文组装时脱落。
- `None`：说明目标来源文档按预期进入了 `selected`。这代表来源传递环节无缺口，但仍需结合生成结果核对模型是否正确利用了它；在较长文档切成多段时，按路径命中后还需继续核对具体段落是否落入上下文。

另外，上游出现证据缺口时，回答质量也未必一定低。在 `source_missing`、`retrieval_miss` 和 `assembly_drop` 条件下，如果模型如实说明发布规范缺失并拒绝猜测，按照第 9 课的证据边界标准依然可以得到满分。

### 冻结前缀，只重放生成环节

为了单独观测生成层对这七组上下文的反应，[replay](code.py) 深拷贝第 9 课真实轨迹中最后一次发给模型的消息列表，附加同一段资料策略（只按当前所给资料回答，缺证据不猜测；若资料冲突，以 `atlas/release.md` 为准），再替换其中唯一一条知识检索工具的返回内容：

```python
results[0]["output"] = {
    "knowledge_version": row["knowledge_version"],
    "contexts": row["contexts"],
}
response = call_model(messages, tools={})
```

调用 `call_model` 时传入空的 `tools={}`，禁止模型在生成回合再调用搜索工具。一旦允许模型重新搜索，就无法孤立比较当前这组控制上下文对生成的影响。重放完成后，`replay` 直接用 `sent_contexts([messages])` 构造 `LLMTestCase`，再把 `expected_output` 设为当前参考答案交给评分器。

### 忠实度与任务分如何拆开“忠于旧文档”和“干扰信息”

加 `--judge` 运行时，[code.py](code.py) 对七组重放结果分别运行 DeepEval 的 `judge_faithfulness`（`FaithfulnessMetric`）与 `task_metric`（`GEval`）：

- 在 `stale_source` 中，内存里的 `atlas/release.md` 把命令改成了 `python -m unittest`。模型照实复述旧命令后，`FaithfulnessMetric` 给出 `1.0`（完全忠于当时收到的上下文），而对照当前参考的 `GEval` 降至 `0.5`。如果只看忠实度，就会误以为链路健康；如果只去改生成提示词，也无法修正过期的知识库版本。
- 在 `noise` 中，上下文末尾多出了一条天气备忘，模型忽略干扰后依然正确作答；在 `conflict` 中，上下文同时包含新版规范和允许失败发布的旧归档备忘，模型按照优先级规则选择了 `atlas/release.md` 的规定。

需要注意一个常见分析陷阱：在 `conflict` 条件下，如果 `FaithfulnessMetric` 抽取的 `truths` 同时混入了主规范和旧备忘的内容，而未能保留来源优先级，模型按主规范做出的回答在 NLI 裁决时就可能与旧备忘陈述产生表面冲突。阅读这类分数时，务必结合抽取出来的 `truths`、逐条 `verdicts` 和 `GEval` 理由一起判断，而不能只看单个标量分。

### 噪声干扰比例：错话从哪类资料来

当上下文同时混入相关资料与无关资料、回答又出现错误或不准确陈述时，诊断常需要回答另一个问题：错误陈述究竟是被无关噪声带偏的，还是源自相关文档里混杂的错误信息？[eval.py](eval.py) 中的 `noise_fraction` 用三组逐声明布尔标记展示了这一算式：

```python
return {
    "relevant": sum(not c and r for c, r in zip(correct, relevant_support)) / len(correct),
    "irrelevant": sum(
        not c and i and not r for c, r, i in zip(correct, relevant_support, irrelevant_support)
    )
    / len(correct),
}
```

这里的两个比率衡量“未被参考支持的错误陈述（`not c`）分别能从哪类上下文里找到依据”，分母是全部回答陈述数 `len(correct)`，用来追踪错话来自哪一类文档，与“加噪前后任务分数的差值”回答的是不同问题。在无关方向上，代码用 `i and not r` 排除了同时得到相关资料支持的陈述，避免同一句错话被重复归入两侧。

以 `cases.jsonl` 里的教学向量 `correct=[True, False, False]`、`relevant_support=[True, True, False]`、`irrelevant_support=[False, True, True]` 为例：共三条陈述，第 1 条正确；第 2 条有误且两类资料都支持，归入 `relevant`（`1/3`）；第 3 条有误且仅得无关资料支持，归入 `irrelevant`（`1/3`）。

使用这个指标时要留意它的边界：增加一条无关紧要但正确的陈述，分母 `len(correct)` 会从 `3` 变成 `4`，即使错话一条没少，两个比例也会双双降成 `1/4`；而只要参考集本身漏写了合理事实，原本正确的陈述也会被标为 `not c`。此外，单次噪声回放没有降分，只能说明这次特定采样下干扰未触发错误，稳定的版本抗噪差异需要多次重复比较（第 15 课展开）。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `prepare` | [code.py](code.py) | 校验冻结轨迹与文档哈希，构造七种阶段快照与受控上下文 |
| `replay` | [code.py](code.py) | 冻结历史消息并禁用工具，仅替换知识结果重放单轮生成 |
| `first_gap` | [eval.py](eval.py) | 按源文档、版本、检索输出、上下文组装顺序返回首个证据缺口 |
| `noise_fraction` | [eval.py](eval.py) | 以全部回答陈述作分母，拆分相关资料支持与纯无关资料支持的错误陈述比例 |
| `judge_faithfulness` / `task_metric` | [e08](../e08_faithfulness/eval.py) / [e09](../e09_answer_quality/eval.py) | 复用 DeepEval 忠实度与证据边界 `GEval`，核对生成层如何处理各阶段上下文 |

## 试一下

运行本课脚本，检查七组控制条件下的 `first_evidence_gap` 与 `noise_fraction` 结果：

```sh
python -m course.e10_rag_diagnosis.code
```

动手验证四个问题：

1. 对照 `source_missing`、`retrieval_miss`、`assembly_drop`，说出证据最早分别在哪一层发生变化。
2. 查看 `stale_source` 的文档哈希、重放回答与 `expected_output`，说明为什么提高忠实度解决不了版本过期问题。
3. 加上 `--live --judge` 运行七组生成回放与 DeepEval 评分，先核对每组的实际 `retrieval_context`，再对照 `FaithfulnessMetric` 的 `truths` 与 `GEval` 理由。
4. 在 `noise_fraction` 的手算例子里追加一条正确陈述，观察为什么错误支持条数没变而两个比例同时下降。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

知识检索与上下文组装之外，编程 Agent 还会频繁调用文件与命令工具。下一课 `e11` 切换到工具调用质量，使用 DeepEval 的 `ToolCorrectnessMetric` 与 `ArgumentCorrectnessMetric` 拆开检查工具名称、参数、顺序与执行结果。
