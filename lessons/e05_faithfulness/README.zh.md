# 第5课：Faithfulness，每句话都能在证据里找到依据吗

## 问题

检索到的项目文档只说明了上传认证方式和大小限制，并没有提到自动重试。可是回答却写道：

> 上传接口失败后会自动重试三次。

“三次”从哪里来的？

它听起来合理，甚至可能碰巧符合真实系统，但无法从本次检索证据中推出。Faithfulness 要检查的正是这件事：回答中的事实声明，是否忠于交给模型的证据。

这里要特别注意“相对证据”。Faithfulness 不等于外部正确性，也不负责判断回答是否切题、是否完整、是否完成任务。例如，旧文档写着上传上限为 1 MiB，回答也照着写了。这个回答可以忠于旧文档，却可能不符合服务器当前配置。

本课不会扩展 Agent，也不会重新运行第4课的 Agent。我们只增加一个独立评分环节：

- 五条人工构造的受控回答；
- 一条使用新版证据、但回答不变的对照；
- 一条第4课真实 Agent 的历史回答，以及它当时检索到的文档快照。

最后一条只是重新评分历史记录，不是一次新的 Agent 运行，也没有用今天重新检索的内容替换当时证据。

## 解决方案

先把回答拆成尽量独立的事实声明，再逐条对照证据。可以用自然语言推断的三个关系帮助理解：

- 支持：证据足以推出声明；
- 矛盾：证据明确否定声明；
- 信息不足：证据没有说明，既不能支持，也不能断定相反。

“文档没提自动重试”属于信息不足，不应自动当成“文档明确说不会重试”。

本课分别调用 DeepEval 4.3.4 和 Ragas 0.4.4 的原生 Faithfulness 指标。三种关系只是理解工具，两个 SDK实际使用的结构并不相同：

- DeepEval 先整理证据中的 `truths`，再从回答抽取 `claims`，最后生成 `yes`、`borderline` 或 `no`；
- Ragas 先生成原子 `statements`，再通过自然语言推断为每条声明给出 `1` 或 `0`。

两者可能把同一句话拆成不同数量的声明，因此不能只看谁的分数高，就断言谁更准确。`cases.jsonl` 中的人工 `annotation` 只用于教学说明，不会作为标准答案交给裁判。

完整七条样本及分数保留在[历史实验摘要](run_summary.md)。先看一个能直接说明口径差异的例子。

例如 `unmentioned`：DeepEval 默认把 `borderline` 计为通过，所以得到 1.0；开启惩罚后，同一组裁决重聚合为 0.0。这个差异不是重新调用模型得到的。

完整的小数、原始请求数、初次连接失败以及来源封装补测都在[实测摘要](run_summary.md)中。逐条声明、原始裁决和证据快照可在[固定示例报告](example_report.json)中核对。

## 工作原理

下面只展示现有实现中的必要片段，均省略了导入、异常记录和报告写入等上下文，不能单独作为运行入口。完整实现见[评测代码](eval.py)和[聚合与证据身份代码](code.py)。

**第1步：固定本次评分使用的证据快照**

Faithfulness 必须知道回答是相对哪一批文档产生的。代码从第4课历史报告中找到当次 `search_knowledge` 的命中结果：

```python
documents = next(
    e["result"]["hits"]
    for e in agent["events"]
    if e["type"] == "tool"
    and e["call"]["name"] == "search_knowledge"
)
```

`documents` 保存文档正文、标识和哈希。真实 Agent 样本直接复用这份快照，不重新检索。否则知识库变化后，我们就无法分清分数变化来自回答，还是来自证据。

证据身份由文档的 `id`、`sha256` 及顺序共同决定：

```python
def evidence_key(documents):
    payload = [
        {"id": d["id"], "sha256": d["sha256"]}
        for d in documents
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
```

这些哈希来自可信加载器，用于识别版本；它们不能独立证明记录未被篡改。

**第2步：准备可解释的受控回答**

五条受控回答分别覆盖支持、未提及、矛盾、混合和无事实声明。运行时为它们补上同一个问题和同一份证据：

```python
cases = [
    {
        **json.loads(line),
        "question": question,
        "documents": documents,
        "origin": "controlled_answer",
    }
    for line in (HERE / "cases.jsonl").read_text().splitlines()
]
```

例如 `mixed` 包含三句话：认证请求头有支持；自动重试三次未被提及；2097152 字节与旧证据的 1048576 字节矛盾。先用这种容易检查的输入理解指标，再看真实 Agent 记录，会比直接盯着一个总分清楚得多。

**第3步：让 DeepEval 逐声明裁决**

DeepEval 的原生输入是 `LLMTestCase`。回答放入 `actual_output`，检索证据正文放入 `retrieval_context`：

```python
sample = LLMTestCase(
    input=case["question"],
    actual_output=case["response"],
    retrieval_context=[
        d["text"] for d in case["documents"]
    ],
)
```

随后创建并同步运行原生指标：

```python
metric = FaithfulnessMetric(
    model=DeepJudge(t),
    async_mode=False,
    include_reason=False,
    threshold=0.7,
)
value = metric.measure(sample, _show_indicator=False)
```

这里复用第3课的 `DeepEvalBaseLLM` 适配，不修改 DeepEval 的算法。`strict_mode=False` 保持默认值；0.7 是本课的教学阈值。`include_reason=False` 省去最终总结调用，但每条裁决的 `reason` 仍会保存。

内部顺序是：抽取 `truths`、抽取 `claims`、生成 `verdicts`。`truths` 也是模型整理的结果，并非天然完整的真值；如果整理时漏掉原文信息，后续判定也会受到影响。同步与异步入口的差别见[源码导读](source_walkthrough.md)。

**第4步：让 Ragas 完成声明生成与自然语言推断**

Ragas 使用问题、回答和检索上下文三个原生参数：

```python
metric = Faithfulness(llm=judge)
value = asyncio.run(metric.ascore(
    user_input=case["question"],
    response=case["response"],
    retrieved_contexts=[
        d["text"] for d in case["documents"]
    ],
)).value
```

这里的 `judge` 复用第4课的 `InstructorBaseRagasLLM` 适配。`CapturingJudge` 只记录每一步真实结构，不替换提示词，也不改写裁决：

```python
result = super().generate(prompt, response_model)
self.steps.append({
    "schema": response_model.__name__,
    "result": result.model_dump(mode="json"),
})
```

报告会分别留下 `StatementGenerator` 的声明生成结果和后续自然语言推断结果。这样即使总分令人意外，也能检查问题出在如何拆句，还是如何判定。

**第5步：区分有效分数、未定义和调用错误**

假设 DeepEval 实际得到 `yes`、`borderline`、`no`，默认把前两项计为通过，因此是 2/3；打开 `penalize_ambiguous_claims` 后只计 `yes`，所以是 1/3：

```python
metric.penalize_ambiguous_claims = True
scores["DeepEval"][
    "penalized_same_verdicts"
] = metric._calculate_score()
```

这只是对已经得到的裁决重新聚合，没有新的模型调用。Ragas 若对应得到 `1、0、0`，二元支持比例为 1/3。

边界情况不能混在一起：

- DeepEval 的共享聚合函数对空 `verdicts` 返回 1，但这不表示任务答对；
- Ragas 没有声明或没有判定时返回 `NaN`；
- Ragas 的空字符串 `response` 会更早触发输入错误；
- 非空的 `Thanks!` 是否被拆成零条声明，应以模型实测为准，不能强迫它输出预设标签。

原生 `NaN` 写入 JSON 时转换为 `null`，同时记录 `status="undefined_nan"` 和 `passed=null`。调用异常记录为 `status="error"`，并使程序以非零状态退出。有效的 0 分仍是正常结果，不能和前两者合并成零。

**第6步：证据变化后拒绝旧标注**

对照实验把同一路径文档中的 1048576 改为 2097152，并重新计算正文哈希：

```python
d["text"] = d["text"].replace(
    "1048576", "2097152"
).replace("1 MiB", "2 MiB")
d["sha256"] = hashlib.sha256(
    d["text"].encode()
).hexdigest()
```

然后用同一个回答重新评分。旧证据下它构成矛盾，新证据下则获得支持。这只是受控材料改版，不代表真实服务器配置发生了变化。

在复用人工标注前，代码检查证据身份：

```python
def require_same_evidence(old_key, documents):
    if old_key != evidence_key(documents):
        raise ValueError(
            "Evidence changed; old annotations must not be reused"
        )
```

同一个文档标识配上新的哈希，会产生新的 `evidence_key`，旧标注因此被拒绝。验收时检查原生指标是否正常运行、原始裁决能否核对，以及旧证据标注是否被拒用。低分样本本来就是这组实验的一部分。

## 相对上一课的变更

| 第4课 | 本课 |
|---|---|
| Agent 检索文档并生成任务产物 | 不改 Agent，只增加独立 Faithfulness 评分 |
| 关注检索与任务执行记录 | 关注回答声明能否由当次证据支持 |
| 保存真实回答和命中文档 | 复用原始回答与原始证据快照 |
| 运行 Agent 得到新轨迹 | 复用 Agent 记录，独立调用裁判评分 |

Agent 的工具、提示词和停止条件保持原样，评分在它已经保存的运行记录上独立进行。

## 试一下

先在宿主机保持裁判入口运行。它复用本机已经登录的 Codex，凭据不会放入容器：

```sh
python3 tools/judge_bridge.py
```

另开一个终端执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e05_faithfulness.eval
```

结果写入 `runs/e05-evaluation.json`。再次运行会覆盖同名文件，需要比较时请先另存。教材中的 `example_report.json` 是固定历史记录，不受重跑影响。

阅读课程页面可运行：

```sh
docker compose up -d
```

然后访问 `http://localhost:8765/lesson5`。

请带着三个问题查看报告：

1. `mixed` 被两个 SDK分别拆成了多少条声明？哪些属于支持、矛盾或证据未提及？
2. 为什么同一组 `yes、borderline、no` 在 DeepEval 默认设置下是 2/3，开启惩罚后却是 1/3？
3. `evidence_v2` 与旧证据的文档路径相同，为什么旧标注仍会被拒绝复用？

更多手算、空声明、证据改版和历史快照再评练习见[练习](exercises.md)，完成后可对照[参考答案](solutions.md)。官方说明、固定提交和源码调用链集中在[源码导读](source_walkthrough.md)。

## 接下来

有证据支持的回答，仍可能只回答了问题的一小部分；忠于旧文档，也可能不符合当前任务合同。下一课把相关性、参考正确性、完整性和拒答分开检查，继续看这些评分器各自能回答什么。
