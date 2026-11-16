# 第6课：答案切题、答对、答全，是三件事

## 问题

用户问：

> 对课程合成系统 v2，上传接口使用什么认证头？最大文件是多少字节？超过限制返回什么状态码？

回答是：

> 使用 `X-Project-Token` 认证头。

这句话切题，也可能是事实，但仍不合格：用户问了三项，它只答了一项。

这正是本课要分清的三个问题：

1. **切题吗？**回答是否在处理用户的问题。
2. **答对吗？**回答中的事实是否得到当前标准支持。
3. **答全吗？**用户要求的事项是否都已覆盖。

此外还有第四个问题：资料不足时，应该给数字、说“无法判断”，还是请求补充配置？这不能只靠相关性或通用事实指标决定，而要结合信息是否可得以及业务拒答政策。

本课不扩展 Agent，不增加工具，也不重新执行 Agent。我们只加入版本化 `reference`、不可回答问题和评测入口。教材中的八条回答是明确标注的受控构造样例；第九条来自第4课保存的真实 Agent 原始 `notes`。本轮改写保留已有历史结果，没有增加 Agent 执行或裁判测量。

先看各字段各管什么：

| 字段 | 用途 | 主要比较对象 |
|---|---|---|
| `question` | 用户究竟问了什么 | 与 `response` 比较切题程度 |
| `response` | 被评测的回答 | 所有指标的被测对象 |
| `retrieved_contexts` | 当次检索实际拿到的证据 | 与回答比较忠实性 |
| `reference` | 指定版本下的参考事实 | 与回答比较事实正确性 |
| 需求清单 | 用户要求覆盖的事项 | 检查业务完整性 |
| `answerable` | 给定证据范围内能否回答 | 决定回答还是限定性拒答 |
| `policy` | 业务接受与拒绝规则 | 评价遗漏、拒答和越界推断 |

这些对象不能混用。切题不等于正确；事实精确率高不等于答全；忠于旧检索证据不等于符合当前合同；`reference` 不支持某句话，也不自动证明它在外部世界中为假。

## 解决方案

本课把评分拆成几条独立观察线：

- DeepEval `AnswerRelevancyMetric` 比较 `question` 与 `response`，检查回答声明是否切题，不核验数字。
- Ragas `FactualCorrectness` 比较 `response` 与版本化 `reference`，用双向声明拆解和自然语言推断形成事实上的 TP、FP、FN。
- Ragas `AnswerCorrectness` 分别从回答与参考答案抽取声明，再直接分类 TP、FP、FN。它与前一个指标不是同一种算法。
- DeepEval `GEval` 接收问题、回答以及包含 `reference`、`answerable`、`policy` 的 `expected_output`，评价业务完整性和拒答是否合理。
- `retrieved_contexts` 只在需要检查“是否忠于当次检索证据”时使用，不能代替当前合同。

本课的 [`reference.json`](reference.json) 是独立编写的课程合成系统合同。v2 中的 `2097152` 字节，也就是 2 MiB，只是受控教学设定，不代表任何生产环境配置。受控回答可以为了暴露边界而构造，但必须清楚标注；SDK 的历史实测分数以 [`run_summary.md`](run_summary.md) 为准。

真实旧 Agent 记录来自第4课原始 `notes`，并按它自己的 v1 `reference` 评价，不能偷偷换成 v2 后重新标错。另一个受控样例 `stale_v1` 才专门模拟“当前任务要求 v2，却检索到旧文档”的情况。

## 工作原理

**第1步：固定问题、证据和合同版本**

同一句回答可能忠于 v1，却不符合 v2。因此先把版本写进评测输入。下面片段来自 [`eval.py`](eval.py)，省略了异常处理和其他指标：

```python
policy = (
    f"Reference version: {case['reference_version']}\n"
    f"Answerable within supplied evidence: {case['answerable']}\n"
    f"Reference: {case['reference']}\nPolicy: {case['policy']}"
)
```

`reference_version` 防止新旧标准混在一起；`answerable` 表示在指定证据范围内能否作答；`policy` 说明怎样才算业务上合格。需求清单则来自 `question` 和政策，例如这里明确要求认证头、字节限额、超限状态码三项。

旧 Agent 的 v1 记录按 v1 判断。`stale_v1` 则用 v2 问题和 v2 参考答案评价，同时另用 `retrieved_contexts` 检查它对旧证据是否忠实。于是“忠于证据”和“符合当前合同”可以同时得到不同结论。

**第2步：先检查回答是否切题**

DeepEval 的相关性指标只需要问题与回答：

```python
sample = LLMTestCase(
    input=case["question"],
    actual_output=case["response"],
)
metric = AnswerRelevancyMetric(
    model=DeepJudge(transport), eval_mode="llm",
    async_mode=False, include_reason=False,
)
value = metric.measure(sample, _show_indicator=False)
```

固定版本的 LLM 模式先从回答抽取 `statements`，再把每条判为 `yes`、`no` 或 `borderline`。`yes` 和 `borderline` 都计为通过；声明列表为空时默认得 1。实际拆出的声明与裁决会原样保存在报告里，不能用人工预期替换。

因为输入中没有 `reference`，它不会核验 `4194304` 是否正确。一个回答可以非常切题，却把限额答错。它也不同于 Ragas 的 Answer Relevancy：后者会从回答反推多个问题，再与原问题计算平均嵌入余弦；固定版本只有全部反推结果都标为不作实质回答时才乘以 0。本课仅做这条源码原理分析，没有实际运行其嵌入模型。

**第3步：用双向声明判断事实支持**

Ragas `FactualCorrectness` 的真实 SDK 调用如下，片段同样省略了记录步骤：

```python
metric = FactualCorrectness(
    llm=judge, mode="f1",
    atomicity="high", coverage="high",
)
value = asyncio.run(metric.ascore(
    response=case["response"],
    reference=case["reference"],
)).value
```

它先拆回答声明，并用自然语言推断判断每条能否由 `reference` 推出；随后交换两个文本，再检查参考答案有哪些内容未被回答支持。

- TP：回答中被 `reference` 支持的声明数。
- FP：回答中不被 `reference` 支持的声明数。
- FN：反向检查中未被回答支持的参考声明数。

精确率 = TP / (TP + FP)  
召回率 = TP / (TP + FN)  
F-beta = (1 + beta²) × 精确率 × 召回率 / (beta² × 精确率 + 召回率)

例如人工设定 TP=1、FP=0、FN=2：

- 精确率为 1；
- 召回率为 1/3；
- F1 为 0.5；
- F2 为 5/13。

这说明“说出来的都对”仍可能漏答。业务完整性只要求覆盖本题所问事项，不是要求回答所有百科事实。

这是**人工计数演示**，不是模型实测。固定源码计算时会在分母加入很小的 `epsilon`，最终保留两位小数。本课原生只运行 `f1`；报告中的精确率和召回率是对同一组实际裁决重新聚合，不是另外运行两遍指标。三种原生模式由固定裁决的断网测试验证。双向拆解粒度及完整公式见 [`source_walkthrough.md`](source_walkthrough.md)。

**第4步：不要把两个“正确性”算法当成同一个**

`AnswerCorrectness` 会分别抽取回答和参考答案的声明，再由分类器直接生成 TP、FP、FN：

```python
metric = AnswerCorrectness(
    llm=judge,
    weights=[1.0, 0.0],
)
value = asyncio.run(metric.ascore(
    user_input=case["question"],
    response=case["response"],
    reference=case["reference"],
)).value
```

本课历史原生实测使用 `[1.0, 0.0]`，只保留事实部分，没有调用嵌入服务。默认配置则以 `[0.75, 0.25]` 混合事实 F-beta 与回答、参考答案的嵌入余弦，但那不是本课的原生实测设置。

固定版本还有一个需要谨慎解释的边界：任一侧没有抽出声明时，事实部分直接为 1。这个行为已由原生离线边界测试检查，却绝不能据此推断拒答合格。

Ragas `SemanticSimilarity` 更简单：直接计算回答和 `reference` 的嵌入相似度。它没有专门的数值正确性或逻辑蕴含检查；改一个数字或否定词后，嵌入仍可能很相近。Response Relevancy 和 Semantic Similarity 在本课都只有**固定源码解释**，没有真实运行嵌入模型。

**第5步：把完整性和拒答政策明确交给业务裁判**

本课把这些业务标准交给第3课已经使用过的 `GEval`：

```python
metric = GEval(
    name="Task answer quality including refusal",
    model=DeepJudge(transport),
    evaluation_steps=STEPS,
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ],
    async_mode=False,
)
```

`expected_output` 中放的是版本化参考答案、可回答性和政策。它要求可回答问题覆盖所有所问事项，也要求不可回答问题进行合理限定。

“文档没有写重试次数”不等于“重试 0 次”。合格回答可以说：现有资料无法确定，请提供重试政策或客户端配置。相反，如果资料已经给出认证头、限额和状态码，却无理由拒答，就应扣分。通用事实知识和相关性分数都不能代替这条业务政策。

`GEval` 仍是模型依照标准作出的判断，不是独立外部真值，也不能证明工具调用、文件修改或整个 Agent 任务已经完成。

**第6步：检查 `partial` 中参考措辞造成的真实分歧**

`partial` 的回答是：

> 使用 `X-Project-Token` 认证头。

人工设计意图是“认证事实正确，但漏掉限额和状态码”。然而历史原生 `FactualCorrectness` 实测为 0。回到这次裁决的输入，可以看到参考首句写的是：

> Use the X-Project-Token header.

参考句没有明写“用于认证”。这次 NLI 把回答中的“用于认证”判为不受支持。

另一个 `AnswerCorrectness` 分类器在生成参考声明时还能看到问题，获得了认证语境，最后得到 TP=1、FN=2、事实分 0.5。两者输入和声明生成方式不同，不能把人工预期的精确率 1 写成前一个指标的原生实测结果。

补测脚本只澄清参考首句，回答保持不变：

```python
clarified = case["reference"].replace(
    "Use the X-Project-Token header.",
    "For authentication, use the X-Project-Token header."
)
assert clarified != case["reference"]
```

这段来自[补测脚本](../../tools/e06_reference_repair.py)，省略后续原生调用与保存。已保存的补测将原生事实F1从0变为0.5；原始报告另存未覆盖。它展示参考措辞的影响，单次对照不能证明普遍稳定性。详细阶段结果见[实验摘要](run_summary.md)。

类似地，真实旧回答中的来源路径被 `FactualCorrectness` 拆成独立声明，而参考答案没有该路径；`AnswerCorrectness` 却把路径和内容并入复合声明并接受。不能只凭两个分数选择“赢家”，应先查看它们究竟比较了什么。

## 相对上一课的变更

| 上一课已有内容 | 本课只增加的内容 |
|---|---|
| Agent、检索结果和历史运行记录 | 版本化 `reference` |
| 回答与检索证据的忠实性 | 切题、事实正确性和需求覆盖 |
| 已有裁判适配器 | 原生指标评测入口 |
| 可回答的任务样例 | `answerable=false` 与拒答政策 |
| 第4课保存的旧 Agent 产物 | 按其原始 v1 合同重新评价 |

Agent 沿用已有实现，九条材料中，八条来自 [`cases.jsonl`](cases.jsonl) 的受控回答：全对、相关但错误、缺项、真实却答偏、忠于旧文档、适当拒答、信息不足却编造、不必要拒答；第九条是旧 Agent 的真实产物。

其中 `off_topic` 所说的健康接口事实存在于合成 `v2_config`，但不在上传问题的 `reference` 内。指标把它判为不受参考支持，只能说明它超出了当前评分标准，不能推出该事实在外部为假。完整九条历史结果和具体分歧见 [`run_summary.md`](run_summary.md)。

## 试一下

先在宿主机保持裁判桥运行。已有 Codex 登录凭据留在宿主机，不进入容器：

```bash
python3 tools/judge_bridge.py
```

另开终端构建并执行评测：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e06_answer_quality.eval
```

结果写入 `runs/e06-evaluation.json`。重跑会覆盖该文件，如需比较，请先另存旧结果。固定的 [`example_report.json`](example_report.json) 不会被覆盖。这里的精确事实以报告和 [`run_summary.md`](run_summary.md) 为准，这些分数用于解释各个案例，不能据此排名或推断通用能力；构造的失败案例也不需要越过通过阈值。

启动教材服务：

```bash
docker compose up -d
```

浏览器访问 `http://localhost:8765/lesson6`。

请在报告中回答三个观察题：

1. `relevant_wrong` 为什么相关性为 1，却不能视为正确答案？
2. `partial` 在两个事实指标中使用了哪些不同输入，为什么得到不同结果？
3. `appropriate_refusal` 与 `invented_retry` 都在回答重试问题，业务政策为什么给出相反评价？

更多练习见 [`exercises.md`](exercises.md)，参考答案见 [`solutions.md`](solutions.md)。完整的双向 NLI 粒度示例、空声明边界、默认嵌入混合的人工计算、固定版本源码链接和调用链见 [`source_walkthrough.md`](source_walkthrough.md)；完整九条结果及参考措辞补测见 [`run_summary.md`](run_summary.md)。

## 接下来

相关性比较问题与回答，事实正确性比较回答与指定版本参考，完整性看所问事项的覆盖，拒答还要结合信息范围和政策。遇到分歧，先看各指标的输入、声明和裁决。第7课把这些观察接回完整执行过程，通过可控故障定位资料、检索和生成阶段的问题。
