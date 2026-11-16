# Chapter 1: Faithfulness：回答是否忠于证据

文档只说了上传认证方式、大小限制和状态查询，没有说“失败后自动重试三次”。可是回答却写道：

> 上传接口会在失败后自动重试三次。

这句话听起来很像正规的接口说明，甚至可能恰好符合某个真实系统，但它并不忠于本次检索到的证据。第5课要解决的就是这个问题：把回答拆成可以核对的声明，再检查每条声明是否得到当前证据支持。

本课只新增一层独立评分，不扩展第4课的 Agent，也不让 Agent 重新执行。五条受控回答用于观察不同情况；一条回答换用新版证据；最后一条则取出第4课已经保存的原始回答和当时 `search_knowledge` 返回的文档快照，重新交给裁判评分。这里发生的是“旧记录再评”，不是一次新的 Agent 运行。

## 1. Faithfulness究竟在评什么

可以把证据想成一张允许回答使用的“小抄”。Faithfulness只问：

> 回答中的事实性声明，能否从这张小抄中得到支持？

它不等于以下任何一项：

- 外部正确性：证据本身可能已经过时。
- 完整性：回答可能只说了证据中的一小部分。
- 相关性：一句话可能有证据支持，却没有回答用户的问题。
- 任务成功：Agent可能写对了说明，但没有正确完成文件操作。
- 拒答质量：没有事实声明，也不代表回答合格。

例如，旧文档写着上传上限为 `1048576` 字节。回答也写 `1048576`，那么它对旧文档是忠实的；如果服务器实际已经改为 `2097152` 字节，它在外部仍然可能是错的。Faithfulness不能替代对真实配置的检查。

## 2. 先把回答拆成原子声明

下面这条混合回答包含三件事：

> 上传令牌应放在 X-Project-Token 中。上传失败会自动重试三次。最大文件大小为 2097152 字节。

适合核对的拆法是：

1. 上传令牌位于 `X-Project-Token`。
2. 上传失败会自动重试三次。
3. 最大文件大小是 `2097152` 字节。

每条声明只保留一个可以单独判断的事实。若把整段话视为一个整体，就很难表达“第一句有支持，第二句没提到，第三句与证据冲突”。

理解这一过程时，可以借用自然语言推断，也就是 NLI 的三个关系：

- 支持：证据能够推出声明。
- 矛盾：证据与声明不能同时成立。
- 信息不足：证据既没有支持，也没有否定声明。

“文档没说自动重试”属于信息不足，不应自动标成矛盾。只有文档明确说“不会自动重试”，它才与“会自动重试三次”构成矛盾。

这三个关系是理解工具。两个原生 SDK 实际使用的裁决结构并不完全相同，不能强行把它们改造成统一的三标签分类器。

## 3. 本课的七条输入

五条受控回答保存在 `cases.jsonl` 中：

| 样本 | 回答意图 |
|---|---|
| `supported` | 只陈述证据支持的认证头 |
| `unmentioned` | 声称自动重试三次，但证据未提及 |
| `contradiction` | 声称上限为 `2097152`，与旧证据冲突 |
| `mixed` | 同时包含支持、未提及和矛盾声明 |
| `no_claim` | 非事实性回复 `Thanks!` |

另外两条是：

- `evidence_v2`：仍回答上限为 `2097152`，但证据中的同一路径已经从 `1048576` 改为 `2097152`，并同步更新 `sha256`。
- `recorded_agent`：使用第4课真实记录中的原始回答，以及当次检索保存下来的文档快照。

`cases.jsonl` 中的 `annotation` 是供读者理解实验设计的人工标注，不会传给模型裁判充当标准答案。否则评测就变成了让裁判照抄提示。

## 4. 一次评分内部发生了什么

调用指标后，可以按下面的顺序理解：

1. 接收问题、回答和检索证据。
2. 从回答中抽取可核对的声明。
3. 整理证据中的事实，或直接将证据交给推断步骤。
4. 逐条判断声明是否获得支持。
5. 聚合逐声明裁决，得到一个分数。
6. 保存声明、裁决理由、原始阶段结果和证据身份，供人工复核。

关键不是只得到一个小数，而是能够回到“哪条声明为什么被判成这样”。不同模型可能采用不同的断句方式，所以声明数量也可能不同。

本课复用前几课的模型适配层：

```python
metric = FaithfulnessMetric(
    model=DeepJudge(transport),
    async_mode=False,
    include_reason=False,
    threshold=0.7,
)
```

这里使用教学约定阈值 `0.7`，并保持 `strict_mode=False`。`include_reason=False` 省去最终总结理由的调用，但逐声明裁决中的 `reason` 仍然保留。同步与异步入口的差异可在源码导读中继续查看。

另一个指标使用第4课的适配器：

```python
judge = CapturingJudge(transport)
metric = Faithfulness(llm=judge)
result = asyncio.run(metric.ascore(
    user_input=question,
    response=response,
    retrieved_contexts=contexts,
))
```

适配器只让现有裁判模型符合 SDK 接口，并记录真实结构化结果；它不替换 SDK 的提示词，也不修改算法。

## 5. DeepEval 4.3.4如何评分

本课固定使用 DeepEval 4.3.4。它的核心流程分三段：

1. 从检索材料抽取 `truths`。
2. 从回答抽取 `claims`。
3. 根据 `truths` 判断每个 `claim`，产生 `yes`、`no` 或 `borderline`。

需要特别小心：`truths` 也是模型整理出来的结果，不是不可出错的外部真值。如果原文中的信息在抽取时遗漏，后面的判定也会受影响。因此报告同时保存原始证据和 `truths`，不能只看最终分数。

默认聚合时，`yes` 与 `borderline` 都计为通过；启用 `penalize_ambiguous_claims` 后，只有 `yes` 计为通过。教材没有为了比较这个开关再次请求模型，而是对已经得到的同一组实际裁决重新聚合：

```python
passing = {"yes"} if penalize else {"yes", "borderline"}
return sum(v in passing for v in verdicts) / len(verdicts)
```

假设三条裁决正好是：

```text
yes, borderline, no
```

默认分数为 `2/3`，惩罚模糊声明后为 `1/3`。这是对固定裁决的手算说明，不代表模型面对任何混合回答都一定生成这三个标签。

DeepEval共享的 `score_qag_verdicts` 对空裁决列表返回 `1`。这个 `1` 只是空集合的实现约定，不表示回答正确、完整或完成了任务。

## 6. Ragas 0.4.4如何评分

Ragas的 `collections` 接口分成两步：

1. `StatementGenerator`根据问题和回答生成原子 `statements`。
2. NLI步骤结合检索上下文，为每条声明输出理由和二元裁决 `0/1`。

本课把两步的原始结构都保存下来。其聚合方式是支持声明数除以有效判定数：

```python
def ragas_aggregate(verdicts):
    if not verdicts:
        return None
    return sum(verdicts) / len(verdicts)
```

若三条裁决为 `1、0、0`，分数就是 `1/3`。Ragas没有沿用 DeepEval“默认接受 `borderline`”的规则。

当没有生成声明或没有判定时，原生结果为 `NaN`。标准 JSON不能保存 `NaN`，所以报告转换为：

```json
{
  "score": null,
  "status": "undefined_nan",
  "passed": null
}
```

这与运行错误不同。错误使用 `status=error`，并使评测程序以非零状态退出；有效的 `0` 分则是正常评分，必须如实保存为 `0`，不能伪装成异常。

还有一个容易混淆的边界：非空的 `Thanks!` 是否被拆出事实声明，应以模型实测结果为准，不能强迫它符合预设标签；真正的空字符串 `response` 会更早触发 Ragas输入校验错误。二者不是同一种情况。

## 7. 七条结果怎样阅读

固定实测报告记录了七条样本、两个原生 SDK，共 `34` 次真实裁判请求，运行错误为 `0`。生成教材所用的调用另算。

| 样本 | DeepEval默认 | 惩罚同组模糊裁决 | Ragas | 状态 |
|---|---:|---:|---:|---|
| `supported` | 1.0 | 1.0 | 1.0 | 已评分 |
| `unmentioned` | 1.0 | 0.0 | 0.0 | 已评分 |
| `contradiction` | 0.0 | 0.0 | 0.0 | 已评分 |
| `mixed` | 0.6666666666666666 | 0.3333333333333333 | 0.3333333333333333 | 已评分 |
| `no_claim` | 1 | 1 | 0.0 | 已评分 |
| `evidence_v2` | 1.0 | 1.0 | 1.0 | 已评分 |
| `recorded_agent` | 1.0 | 0.0 | 0.5714285714285714 | 已评分 |

`unmentioned`尤其值得检查：DeepEval默认把实际产生的模糊裁决计入通过，开启惩罚后变为 `0`；Ragas的二元判定也是 `0`。这不是简单地说某个框架“更宽松”或“更准确”，而是提醒我们检查实际声明和裁决口径。

`recorded_agent`在两个 SDK 中的结果也不同。原因之一是它们可能拆出不同数量、不同粒度的声明。只比较最终高分，不能推导出哪个 SDK 更优秀。

阅读报告时应区分三种结果：

- 有效低分：指标成功运行，结果可能为 `0`。
- 未定义：原生得到 `NaN`，保存为 `null` 与 `undefined_nan`。
- 调用错误：保存为 `error`，不是一个可参与平均的零分。

初次实验时，宿主机裁判入口尚未启动，出现了 `14` 项连接错误，真实模型调用为 `0`。失败报告被保留下来。启动入口后才完成上述 `34` 次真实请求。请求数是这次固定记录的事实，不应被宣传成每次运行都必须相同。

## 8. 证据改版为什么必须换身份

旧证据写的是 `1048576` 字节。同一个回答“最大上传大小为 `2097152` 字节”，在旧证据下发生冲突，在受控的新证据下则得到支持。

本课根据有序的文档 `id` 与可信加载器提供的 `sha256` 计算证据键：

```python
payload = [
    {"id": d["id"], "sha256": d["sha256"]}
    for d in documents
]
return hashlib.sha256(
    json.dumps(payload, sort_keys=True).encode()
).hexdigest()
```

证据顺序也属于身份的一部分。即使文件路径不变，只要内容和哈希改变，旧标注就不能直接复用：

```python
def require_same_evidence(old_key, documents):
    if old_key != evidence_key(documents):
        raise ValueError(
            "Evidence changed; old annotations must not be reused"
        )
```

这项检查信任加载器给出的哈希元数据，不是防篡改证明。实际项目仍应保存文档快照。新版证据也是专门构造的教学材料，不能据此声称真实服务器配置已经改变。

## 9. 重新评价第4课记录，而不是重跑Agent

真实 Agent 样本从第4课报告中读取两样东西：

- 当时生成的原始回答。
- 当次 `search_knowledge` 返回的文档快照。

随后只重新调用两个指标。报告保留源 `run_id` 和源报告哈希，且明确记录：

```text
agent_new_execution = false
```

不能重新检索今天的知识库并替换旧快照，因为那会悄悄改变被评价的证据。也不能把这次裁判调用写成一次新的 Agent 运行。Faithfulness分数还应与第4课的文件验收结果分开呈现：一个检查回答对证据是否忠实，另一个检查任务产物是否符合要求。

## 10. 运行与核对

先在宿主机保持裁判入口运行。它复用本机已经登录的 Codex，凭据不进入容器：

```sh
python3 tools/judge_bridge.py
```

另开一个终端构建并执行评测：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e05_faithfulness.eval
```

结果写入 `runs/e05-evaluation.json`，再次运行会覆盖同名文件；需要比较时应先另存。教材中的固定真实记录 `example_report.json` 不受重跑影响。

阅读课程页面可运行：

```sh
docker compose up -d
```

然后访问 `http://localhost:8765/lesson5`。

最终验收目标不是让所有样本都获得高分，也不是强求每次调用数完全相同，而是确认：

- 两个原生指标运行时没有错误。
- 原始声明、事实整理和逐条裁决可以核对。
- 证据发生变化后，旧标注确实被拒绝复用。

## 11. 动手练习

1. 把 `mixed` 拆成原子声明，分别标注支持、信息不足和矛盾，再对照两个 SDK 的实际拆解。
2. 对 `yes、borderline、no` 手算 DeepEval默认分数和惩罚分数；再计算 Ragas的 `1、0、0`。
3. 解释为什么 `Thanks!` 得到高分或未定义，都不能证明任务答对；再说明它与空字符串的区别。
4. 用同一路径的两个证据版本评价同一回答，确认 `evidence_key` 改变，并验证旧标注被拒用。
5. 构造一个“忠于过时文档，却不符合当前真实配置”的例子，分别列出 Faithfulness和外部正确性需要的材料。
6. 从第4课记录中取出原始回答和当次检索快照，说明还需要哪些指标才能判断任务总体成功。

## 完整材料

- [完整评测代码](eval.py)
- [确定性聚合与证据身份代码](code.py)
- [五条受控回答](cases.jsonl)
- [固定真实评测报告](example_report.json)
- [初始连接失败记录](initial_connection_failure.json)
- [实测摘要](run_summary.md)
- [源码导读与官方固定源码链接](source_walkthrough.md)
- [练习](exercises.md)
- [参考答案](solutions.md)

本课建立的是一套小型开发教学实验：保存证据快照，把回答拆成声明，保留原始裁决，并区分有效低分、未定义和调用错误。它不是严格盲测，也不能证明指标具有通用可靠性。下一课将继续处理相关性、外部正确性、完整性与拒答，避免让一个 Faithfulness分数承担它无法回答的问题。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)