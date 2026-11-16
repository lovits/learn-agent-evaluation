# 第6课：答案相关性、正确性、完整性与拒答

用户问：

> 对课程合成系统 v2，客户端应使用什么认证头？最大上传字节数是多少？超限返回什么状态码？

回答是：

> 使用 `X-Project-Token` 认证头。

用户要了三项信息，回答只给出认证头。它确实说到了问题中的一部分，另外两项还没有交代。

沿用前五课的 Agent、检索和裁判适配器，本课增加以下评测材料与入口：

1. 带版本的 `reference`；
2. 明确的不可回答问题与拒答政策；
3. 一个独立的答案质量评测入口。

这一课沿用已有回答，不再执行 Agent。先看指标需要什么材料，再用少量分数检查自己的理解。

## 先分清评测中的七种材料

拿到一条回答，先把问题、证据和评分标准分开。它们会进入不同的指标。

- `question`：用户究竟问了什么。它决定回答是否切题，以及需要覆盖哪些事项。
- `response`：被评测的回答。
- `retrieved_contexts`：回答当时实际拿到的检索证据。它适合判断回答是否忠于证据。
- `reference`：经过审核、带版本的参考事实，用来判断回答是否符合目标合同。
- 需求清单：问题中必须逐项回答的内容，例如“认证头、最大字节数、超限状态码”。
- `answerable`：根据限定的信息范围，这个问题是否能够回答。
- `policy`：业务如何处理遗漏、拒答、未知信息和无关内容。

可以把它们想成考试中的不同材料：题目是 `question`，考生答案是 `response`，考生当时查到的书是 `retrieved_contexts`，标准答案是 `reference`，评分点是需求清单，题目是否缺条件由 `answerable` 表示，阅卷规则则是 `policy`。

| 评测目标 | 主要输入 | 实际比较的两个对象 | 不能单独证明什么 |
|---|---|---|---|
| 答案相关性 | `question`、`response` | 回答内容与所问内容 | 事实是否正确 |
| 证据忠实性 | `response`、`retrieved_contexts` | 回答声明与当次检索证据 | 是否符合当前版本合同 |
| 参考事实正确性 | `response`、`reference` | 回答声明与版本化参考事实 | 是否覆盖全部需求 |
| 业务完整性 | `question`、需求清单、`response` | 所问事项与实际覆盖事项 | 百科知识是否面面俱到 |
| 拒答质量 | `answerable`、`policy`、证据、`response` | 回答行为与信息可得性及业务政策 | 仅靠通用事实无法决定 |
| 语义相似性 | `response`、`reference` | 两段文本的嵌入表示 | 数字、否定词和合同是否正确 |

这几种判断需要分别做：

- 切题不等于正确；
- 事实 `precision` 高不等于完整；
- 忠于过时证据不等于符合当前合同；
- 拒答是否合理，要结合信息可得性和业务政策判断。

## 版本化参考答案为什么必要

本课的 [`reference.json`](reference.json) 保存了单独编写的课程合成系统合同。v2 规定：

- 认证头为 `X-Project-Token`；
- 最大上传大小为 `2097152` 字节；
- 超限返回 HTTP `413`。

这里的 2 MiB 只是受控课程设定，不代表任何生产系统的真实配置。受控答案可以人为构造，但必须明确标注为构造教学样例。

参考材料还包含 v1：它沿用第4课冻结的 1 MiB 合同。同一句“最大为 1048576 字节”，在 v1 任务中可能正确，在当前 v2 任务中却已经过时。

本课共有九条评测记录：

- 八条明确标注的受控回答；
- 一条来自第4课原始 `notes` 的真实旧 Agent 产物。

`answerable` 由课程信息合同独立标注，不能根据被测回答是否说“不知道”反推。本课是构造回答与旧记录的内容再评，reference 仅提供给评分器；真实任务是否可答，还应核对 Agent 当时拿到的资料。

真实旧产物必须使用它自己的 v1 `reference`。不能因为今天有了 v2，就偷偷按 v2 重标过去的任务。另一个受控样例 `stale_v1` 才专门模拟“当前执行 v2 任务，却检索到了旧文档”的故障。

本次 `stale_v1` 对旧证据的 Faithfulness 实测为1，对当前 v2 reference 的事实 F1 为0.67。两个指标使用了不同的比较材料。

这两个场景表面上都出现了 1 MiB，时间语境却完全不同：

- `recorded_v1`：过去回答过去的问题，应按 v1 评价；
- `stale_v1`：现在回答 v2 问题，却用了 v1 资料，应按当前 v2 合同评价。

## 九条回答覆盖了哪些问题

八条受控回答包含四类核心错误：

- `relevant_wrong`：回答相关，但限额错误；
- `stale_v1`：忠于旧文档，却不符合当前合同；
- `off_topic`：陈述了真实但答偏的健康接口事实；
- `invented_retry`：信息不足时编造重试次数。

另外还有四个对照：

- `complete_v2`：三项都答对；
- `partial`：只回答认证头，漏掉两项；
- `appropriate_refusal`：证据不足时合理限定并请求配置；
- `unnecessary_refusal`：明明可以回答，却无理由拒答。

看 `off_topic` 时，先检查它用了哪份标准。`GET /health` 返回 HTTP `200` 的事实存在于合成 `v2_config` 中，但没有写入上传问题的 `reference`。因此“reference 不支持”只表示当前评分标准没有覆盖这条声明，不能自动升级为“它在外部世界是假的”。评测参考本身也需要接受范围审查。

## DeepEval：相关性只问“有没有回答这个问题”

本课使用固定版本 DeepEval 4.3.4 的 `AnswerRelevancyMetric`，并显式选择 `llm` 模式。它需要的是：

```python
sample = LLMTestCase(
    input=case["question"],
    actual_output=case["response"],
)
```

这个调用没有传入 `reference`。指标能看回答有没有围绕问题展开，却没有当前限额的标准答案可供核对。

内部过程分两步：

1. 从回答中拆出若干 `statements`；
2. 对每条声明裁决 `yes`、`no` 或 `borderline`。

`yes` 和 `borderline` 都计为通过，最终分数近似为“切题声明所占比例”。如果声明列表为空，固定实现默认得到 1。这个边界行为来自实现，不能解释成空回答在业务上合格。

例如：

> 最大上传大小为 4194304 字节，超限返回 HTTP 413。

它完全围绕上传设置作答，因此相关性可能是 1；但其中的限额仍然错误。相关性指标比较的是 `question` 与 `response`，不是 `response` 与 v2 合同。

实际拆出的声明和逐条裁决保存在报告中。模型如何拆分，就按实际结果呈现，不能为了符合人工预期而重写它的中间输出。固定源码及详细调用顺序见 [`source_walkthrough.md`](source_walkthrough.md)，版本固定信息见 [`versions.json`](../../references/versions.json)。

## 用 GEval 表达业务正确性、完整性与拒答

DeepEval 的正确性指南建议使用 GEval 描述应用自己的评分标准。本课继续使用第3课的 GEval 和模型适配器，把评分标准写进已有入口。

GEval 的 `expected_output` 同时携带参考答案、版本与业务政策：

```text
Reference version: e06-contract-v2
Answerable within supplied evidence: True
Reference: ...
Policy: ...
```

评分步骤明确要求检查：

- 内容事实是否符合版本化 `reference`；
- 是否覆盖问题要求的每一项；
- 是否切题；
- 拒答是否符合 `answerable` 与 `policy`。

业务完整性指的是“用户所问的需求有没有覆盖”，不是“是否列出了所有相关百科事实”。用户问三项，正确回答三项就完整；没有必要顺便介绍健康接口、部署拓扑或所有 HTTP 状态码。

GEval 会依据这些标准作判断。检查分数时，还要看 `reason` 是否确实引用了遗漏或错误。本课评价答案内容；工具是否执行、文件是否写好，需要前几课的独立产物验收。

## Ragas FactualCorrectness：两个方向的声明与 NLI

固定版本 Ragas 0.4.4 的 `FactualCorrectness` 接收 `response` 和 `reference`。它先拆解声明，再通过自然语言推断判断一段文本能否支持另一段文本中的声明。

它会做两个方向：

1. 正向：拆 `response`，由 `reference` 判断每条回答声明是否受到支持；
2. 反向：拆 `reference`，由 `response` 判断参考声明是否被回答覆盖。

计数方式是：

- TP：正向中受到 reference 支持的回答声明数；
- FP：正向中不受支持的回答声明数；
- FN：反向中未被回答支持的参考声明数。

对这组计数，公式为：

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)

Fbeta = (1 + beta²) × precision × recall
        / (beta² × precision + recall)
```

注意，固定源码计算 `recall` 时仍使用正向 TP。假设正向裁决是 `[1, 1, 1]`，反向裁决是 `[1, 0]`：

```text
TP = 3
FP = 0
FN = 1
recall = 3 / (3 + 1) = 3/4
```

它不是简单的反向覆盖率 `1/2`。原因是两个方向可能拆出不同数量、不同粒度的声明。自然语言中的一句复合事实，在另一个方向可能被拆成三句，分母因此不能随意互换。

固定源码在分母中加入很小的 `epsilon`，最后保留两位小数。本课原生只运行 `f1`；报告中的 `precision` 和 `recall` 是对同一组实际裁决重新聚合，不是冒充原生又独立运行了两遍。原生 `precision`、`recall`、`f1` 三种模式由固定裁决的断网测试校验。

手算函数可在 [`code.py`](code.py) 查看。最小调用如下：

```python
from lessons.e06_answer_quality.code import fbeta

f1 = fbeta(1, 0, 2)
f2 = fbeta(1, 0, 2, beta=2)
```

给定 TP=1、FP=0、FN=2：

```text
precision = 1
recall = 1/3
F1 = 0.5
F2 = 5/13
```

`precision=1` 只说明回答说出的那一项没有计入错误，不能证明另外两项已经回答。`beta=2` 更重视召回，因此漏答会受到更明显的惩罚。

这些计数是构造的手算演示，不是模型成绩。

## partial：人工预期为什么与原生实测不同

`partial` 的回答是：

> Use the X-Project-Token authentication header.

人工设计意图是“认证头正确，但遗漏限额和状态码”。如果按这个预期计数，可以得到 TP=1、FP=0、FN=2。

FactualCorrectness 的原生实测 F1 却为0。回到 NLI 输入，可以看到 reference 首句只有：

> Use the X-Project-Token header.

它没有明确写出 `authentication`。正向 NLI 因而把“用于认证”判成不受支持。不能把人工预期中的 `precision=1` 写成原生实测结果。

本课还做了一次独立补测：保留相同回答，只把 reference 首句澄清为：

> For authentication, use the X-Project-Token header.

主报告没有被改写。补测中原生 FactualCorrectness F1 从 0 变为 0.5。这个对照说明 reference 措辞会影响声明蕴含判断，但一次补测不能证明指标在所有任务上都稳定。准确结果以 [`run_summary.md`](run_summary.md) 为准，原始报告和补测报告见文末。

## Ragas AnswerCorrectness：声明分类与加权

`AnswerCorrectness` 同样涉及 TP、FP、FN，但内部流程不同。它分别从 `response` 和 `reference` 抽取声明，然后让分类器直接输出三类列表：

- TP：正确且匹配的声明；
- FP：回答中未获 reference 支持的声明，可能是事实错误，也可能是参考未覆盖；
- FN：reference 中有、回答未覆盖的声明。

这里要读的是分类器给出的三份列表，与前面的双向 NLI 记录分别核对。

默认情况下，它按权重 `[0.75, 0.25]` 混合：

- 事实 F-beta 分数；
- 回答与 reference 的嵌入余弦相似度。

本课没有 embedding 服务，因此原生实测明确使用 `[1.0, 0.0]`，只运行事实部分，embedding 调用数为 0。

默认混合可以先用人工数字手算。取两个人工向量：

```text
a = [1, 0]
b = [0.8, 0.6]
```

两者余弦相似度为 0.8。若预设事实分为 0.5，则默认混合为：

```text
0.75 × 0.5 + 0.25 × 0.8 = 0.575
```

0.8 和 0.575 都是人工计算，不是 embedding 模型实测。完整计算函数见 [`code.py`](code.py)。

固定版本还约定：任意一侧没有抽出 statements 时，事实部分直接设为 1。该行为由原生离线边界测试检查，但绝不能据此推断拒答合格。空声明默认值只是实现约定，拒答仍须按信息可得性和业务政策判断。

在 `partial` 中，AnswerCorrectness 的声明生成过程还拿到了问题，因此为 reference 声明补出了认证语境，最终得到 TP=1、FN=2、事实 F1=0.5。它与 FactualCorrectness 的 0 来自不同输入和不同拆分方式，不能把二者看成互相推翻。

## Response Relevancy 与 SemanticSimilarity

Ragas 文档中的 Response Relevancy 概念，在本课固定的 `metrics.collections` 接口中对应 `AnswerRelevancy`。

它通过回答反推问题，流程是：

1. 根据回答反推出多个可能的问题；
2. 将这些生成问题与原问题分别嵌入；
3. 计算余弦相似度并取平均。

这个固定版本只有在生成结果全部是 `noncommittal`，也就是全部不作实质回答时，才把结果乘以 0。它与 DeepEval 的“切题声明比例”不是同一种算法。

`SemanticSimilarity` 更直接：只比较 `response` 与 `reference` 的嵌入。两句话即使只差一个限额数字或一个否定词，语义空间仍可能很接近。因此相似不能保证合同正确，也不能验证数字、否定关系或业务限制。

本课只做了这两项的源码原理分析，没有实际运行 embedding 模型。源码位置、固定提交和边界行为见 [`source_walkthrough.md`](source_walkthrough.md)。

## 拒答要看资料是否足够

用户问：

> 仅根据提供的上传文档，客户端失败后会自动重试几次？

提供的证据没有写重试次数。这不等于重试 0 次。

比较这三种回答：

- “自动重试 0 次”：没有证据支持；
- “自动重试 3 次”：同样是编造；
- “现有资料未说明自动重试次数，请提供重试政策或客户端配置”：合理限定了信息范围，并请求必要材料。

第三种可以按本课政策判为适当拒答。这里的 `answerable=false` 表示“在给定证据范围内无法确定”，不表示世界上永远没有答案。

反过来，如果 v2 reference 已经明确给出了认证头、限额和状态码，却回答“无法确定任何上传设置”，就是不必要拒答，应当扣分。

通用事实不能替代拒答政策，相关性也不能替代它。实测中 `appropriate_refusal` 和 `invented_retry` 的 DeepEval 相关性都是 1，因为它们都在讨论重试次数；但 GEval 业务政策分数分别为 1 和 0。回答切题，不代表处理未知信息的方式正确。

## 实测结果：数字之后要回到中间声明

实际 SDK 分数以 [`run_summary.md`](run_summary.md) 为准：

| 样本 | DeepEval 相关性 | Ragas 事实 F1 | Ragas 正确性 `[1,0]` | GEval 业务政策 |
|---|---:|---:|---:|---:|
| `complete_v2` | 1 | 1 | 1 | 1 |
| `relevant_wrong` | 1 | 0.57 | 0.6667 | 0.7 |
| `partial` | 1 | 0 | 0.5 | 0.4 |
| `off_topic` | 0 | 0 | 0 | 0 |
| `stale_v1` | 1 | 0.67 | 0.3333 | 0.7 |
| `appropriate_refusal` | 1 | 1 | 1 | 1 |
| `invented_retry` | 1 | 0 | 0 | 0 |
| `unnecessary_refusal` | 0 | 0 | 0 | 0 |
| `recorded_v1` | 1 | 0.73 | 1 | 1 |

本课没有设置统一的业务通过阈值。分数出现差异时，回到声明、参考材料和裁判理由，检查差异从哪里来。

第一，`relevant_wrong` 的相关性为 1，却把限额写成 4194304。它说明切题不等于正确。FactualCorrectness 得 0.57，AnswerCorrectness 事实版得 2/3，是因为两者拆解和计数不同。

第二，`partial` 的人工预期与实测冲突。前一个指标只看未明确写出认证语境的 reference，判“用于认证”不受支持；后一个指标生成 reference 声明时拿到了问题，接受了认证语境。保留原始实测与人工预期，才有材料检查这处输入差异。

第三，`recorded_v1` 中真实旧回答包含来源路径。FactualCorrectness 把路径拆成独立声明，而 reference 没列路径，因此得到 0.73；AnswerCorrectness 把来源与内容并入复合声明并接受，得到 1。不能因为某个分数更高，就宣布该算法一定更准确。先检查声明粒度和分母是否相同。

## 如何运行与保存报告

宿主机保持裁判桥接服务运行：

```bash
python3 tools/judge_bridge.py
```

已有 Codex 登录凭据留在宿主机，不进入容器。另开终端构建并执行评测：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e06_answer_quality.eval
```

评测写入：

```text
runs/e06-evaluation.json
```

重跑会覆盖该文件，需要保留旧结果时应先另存。固定的 [`example_report.json`](example_report.json) 不会被运行覆盖。

reference 澄清补测在主实验后独立运行，保留主报告：

```bash
docker compose run --rm -T --entrypoint python course tools/e06_reference_repair.py
```

补测写入 `runs/e06-reference-repair.json`，也会覆盖同名旧文件。

启动教材服务：

```bash
docker compose up -d
```

然后访问 `http://localhost:8765/lesson6`。

评测入口的完整实现见 [`eval.py`](eval.py)。它没有新增 Agent 执行，也没有调用 embedding 模型。

## 动手练习

1. 用户要求认证头、限额和状态码，回答只给出正确认证头。分别判断它的相关性、事实 `precision` 和需求覆盖情况，并写出每项判断所需的输入字段。
2. 用 TP=1、FP=0、FN=2 手算 `precision`、`recall`、F1 和 F2，解释为什么更大的 `beta` 更重视漏答。
3. 对正向 `[1,1,1]`、反向 `[1,0]`，分别计算固定 Ragas 实现的 `recall` 和直接反向覆盖率。
4. 比较 v1 旧证据与 v2 当前合同：什么时候应使用 Faithfulness，什么时候应使用版本化 reference？
5. 对“0次”“3次”“资料未说明，请补充配置”三种重试回答制定拒答政策；再考虑证据已经包含答案时应如何评分。
6. 用人工事实分 0.5、人工相似度 0.8 和默认权重算出混合分，并说明它为什么不是 embedding 实测。
7. 从真实报告中选一处分歧，依次检查 reference、声明拆解、版本、输入字段和业务政策。若实测与预期不同，保留两者。

练习全文见 [`exercises.md`](exercises.md)，参考答案见 [`solutions.md`](solutions.md)。

## 适用边界

本课的方法适合评价有明确问题、参考事实、证据范围和业务政策的回答。它不能自动解决以下问题：

- reference 本身错误或覆盖不全；
- 版本标注缺失；
- 模型把复合声明拆成了意外粒度；
- 外部事实并未进入评分标准；
- 分数被误当成工具执行成功证明；
- 单次裁判结果被当成普遍结论。

复核时可以沿报告中的 statements、TP/FP/FN、NLI 裁决和 GEval reason 往回找，逐项确认输入和判断依据。

完整材料：

- [`source_walkthrough.md`](source_walkthrough.md)：固定版本源码导读；
- [DeepEval 相关性文档](https://deepeval.com/docs/metrics-answer-relevancy)、[正确性指南](https://deepeval.com/guides/guides-answer-correctness-metric)；
- [Ragas 事实正确性文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)、[AnswerCorrectness 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_correctness/)；
- [`exercises.md`](exercises.md)：练习；
- [`solutions.md`](solutions.md)：参考答案；
- [`example_report.json`](example_report.json)：固定主报告；
- [`reference_repair_report.json`](reference_repair_report.json)：`partial` 的 reference 澄清补测；
- [`run_summary.md`](run_summary.md)：精确实测摘要。

下一课会主动删改检索证据、加入噪声，再沿中间阶段定位故障。可以先把本课的一处分歧整理成案例：问题、回答、reference、声明与裁决理由都放在一起。
