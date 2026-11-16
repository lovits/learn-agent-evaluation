# Chapter 1: Faithfulness：回答真的被证据支持吗

假设知识库里只有三条信息：

> 未拆封商品可在签收后 30 天内申请退货。  
> 退款按照原支付渠道退回。  
> 本规则没有说明退货运费由谁承担。

用户问：“退货规则是什么？”

助手回答：

> 未拆封商品可以在 30 天内退货，退款原路返回，而且退货完全免费。

前两项有明确依据，最后一项却没有。知识库只是“没说运费”，并不等于“承诺免费退货”。

这就是 Faithfulness（忠实度）要检查的问题：

> 回答中的每一项事实性声明，是否得到当前检索证据的支持？

本章围绕这个退货案例，学习如何分类声明、手算分数、跟踪两个真实框架的源码，并用可重复的 Docker 实验验证评测管线。

---

## 1. Faithfulness 究竟测量什么

Faithfulness 的测量对象不是“回答与世界真相的关系”，而是：

> 回答中的声明，相对于给定检索上下文的证据支持程度。

最小输入通常包括：

- `question`：用户问题；
- `answer` 或 `response`：待评估回答；
- `retrieved_contexts`：检索到的证据。

参考答案不是必需字段。即使没有标准答案，只要有待测回答和检索上下文，也可以检查回答是否忠于证据。

可以把它想成一次“开卷考试”：

- 回答是考生写下的内容；
- 检索上下文是允许使用的教材；
- Faithfulness 裁判只检查答案能不能从教材中推出；
- 裁判不负责判断教材本身是否正确。

因此，高 Faithfulness 分数不代表：

- 回答符合现实事实；
- 检索结果完整；
- 回答切题；
- 回答有用；
- 回答覆盖了用户需要的全部信息。

如果文档错误地写着“退货期限为 300 天”，回答也说“300 天”，它可能得到很高的忠实度分数。它忠于文档，却未必忠于现实。

---

## 2. 最小评测管线

一次 Faithfulness 评测可以拆成四步：

1. 收集问题、回答和检索上下文；
2. 把回答拆成可独立判断的声明；
3. 根据上下文判断每条声明；
4. 聚合分数，并保存逐声明解释。

退货回答可以拆成三条声明：

1. 未拆封商品可在签收后 30 天内退货；
2. 所有退货运费都由商家承担；
3. 未拆封商品可在签收后 60 天内退货。

拆分很重要。若把整段回答只判成一个“对”或“错”，就无法知道错误来自期限、退款渠道还是运费。

本课程中的数据流是：

```text
问题、回答、检索上下文
        ↓
拆分声明
        ↓
逐条检查证据
        ↓
聚合分数并保存判定记录
```

这条管线看起来简单，但“如何拆声明”和“什么算支持”都会影响最终分数。

---

## 3. 三类声明

本课程使用三类人类标注：

| 类别 | 含义 | 退货案例 |
|---|---|---|
| `supported`（有支持） | 可以从上下文直接推出 | “30 天内可退货” |
| `unsupported`（未支持） | 上下文没有支持，但也没有直接反驳 | “商家承担全部运费” |
| `contradicted`（相矛盾） | 上下文与声明直接冲突 | “60 天内可退货” |

### 3.1 有支持不等于“听起来合理”

知识库明确写着：

> 未拆封商品可在签收后 30 天内申请退货。

所以“未拆封商品可在签收后 30 天内退货”是 `supported`。

判断依据是文档，而不是常识或商业经验。

### 3.2 信息缺失不等于矛盾

知识库说“没有说明退货运费由谁承担”。

因此，“所有退货运费都由商家承担”是 `unsupported`，不是 `contradicted`：

- 文档没有承诺商家承担；
- 文档也没有明确说商家不承担。

这像证人回答“我不知道谁付了运费”。我们不能据此证明“商家付款”，也不能据此证明“商家没有付款”。

### 3.3 直接冲突才是矛盾

文档规定 30 天，回答却说 60 天。两个期限不能同时作为同一规则成立，因此属于 `contradicted`。

初学时可以使用下面的判断顺序：

1. 上下文能直接推出声明吗？能则为 `supported`。
2. 上下文直接否定声明吗？是则为 `contradicted`。
3. 两者都不是，则为 `unsupported`。

---

## 4. 两个框架并不采用完全相同的口径

本课程固定到两个源码版本。下面的说明只适用于指定提交和模式，不能推广成“两个框架永远如此”。

- DeepEval：提交 [`34db63dd005ebc9a905c8ef4741ae0687c93c14c`](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，使用 `llm` 模式；
- Ragas：提交 [`8c63f10d500c44efbf24fdb9e2920de2104c321c`](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，使用 `metrics.collections.Faithfulness`。

### 4.1 DeepEval 的三档裁决

在固定版本的 DeepEval 中，裁判可返回：

- `yes`：证据支持；
- `borderline`：证据未支持，但没有直接矛盾；
- `no`：证据直接矛盾。

异步执行时，DeepEval 会并行做两件事：

- 从检索上下文抽取 `truths`；
- 从回答抽取 `claims`。

随后，它再根据 `truths` 为每个 `claim` 生成裁决。

默认聚合规则是：

\[
\text{分数}=
\frac{\text{yes 数量}+\text{borderline 数量}}{\text{裁决总数}}
\]

也就是说，默认情况下，证据缺失的 `borderline` 仍然通过。

设置 `penalize_ambiguous_claims=True` 后，规则变为：

\[
\text{分数}=
\frac{\text{yes 数量}}{\text{裁决总数}}
\]

这与 `strict_mode` 不是同一个开关：

- `penalize_ambiguous_claims` 改变哪些裁决算通过；
- `strict_mode` 会把阈值设为 1，并在分数低于阈值时将结果钳制为 0。

此外，`idk` 是历史裁决值的兼容别名，会被归一化为 `borderline`。它不是助手面向用户说出的“我不知道”。

若没有任何有效裁决，`score_qag_verdicts` 的默认 `empty_score` 为 1。

### 4.2 Ragas 的二元裁决

固定版本的 Ragas 会：

1. 从 `response` 拆出 `statements`；
2. 合并所有 `retrieved_contexts`；
3. 使用自然语言推断检查每条声明；
4. 直接支持记为 1，否则记为 0。

因此：

\[
\text{分数}=
\frac{\text{裁决为 1 的声明数}}{\text{声明总数}}
\]

这里不会单独保留“未支持”和“相矛盾”两个分数档位。两者都会得到 0，但裁判给出的原因仍可用于解释区别。

如果生成的 `statements` 为空，或者最终裁决列表为空，结果是 `NaN`。课程在写入严格 JSON 时会将它转换成 `null`，不会偷偷改成 0。

另一个容易混淆的边界是输入校验：

- 空 `response` 会先失败；
- 空 `user_input` 会先失败；
- 空 `retrieved_contexts` 会先失败；
- 非空回答若被拆成零条声明，才会进入 `NaN` 分支。

---

## 5. 手算同一组固定裁决

假设人类已经固定了三条裁决：

```text
[yes, borderline, no]
```

DeepEval 默认模式中，`yes` 和 `borderline` 都通过：

\[
\frac{2}{3}
\]

开启歧义惩罚后，只有 `yes` 通过：

\[
\frac{1}{3}
\]

对应到 Ragas 的二元裁决：

```text
[1, 0, 0]
```

结果为：

\[
\frac{1}{3}
\]

这只能说明三个聚合口径在这组固定输入下得到不同结果，不能据此断言哪个模型或框架“更聪明”。

真实模型运行时，两个框架可能：

- 拆出不同数量的声明；
- 使用不同措辞重写声明；
- 对证据做出不同判断。

所以不能拿这组人工对齐的三条声明，直接推导实际模型效果优劣。

---

## 6. 本课程实验到底验证了什么

默认实验使用的是：

> 真实 SDK，加上人工固定的结构化模型输出。

这种方式称为回放。它不是自己仿写一个简化版公式，而是：

- 真实调用 DeepEval 和 Ragas 的指标类；
- 让真实 SDK 生成提示并执行自己的管线；
- 在模型调用位置返回人工编写的固定结构化结果；
- 观察真实 SDK 如何聚合和保存结果。

因此，回放适合验证：

- SDK 调用了哪些结构化输出；
- 数据是否按预期流动；
- 不同聚合策略得到什么分数；
- 空声明如何处理；
- 严格 JSON 如何保存特殊数值。

回放不验证：

- 某个裁判模型的真实准确率；
- 模型费用；
- 模型延迟；
- 不同模型的效果排名。

只有 `live` 模式才会调用真实裁判模型。若本轮没有配置 API Key，就不能声称已经完成真实裁判实测。

### 6.1 为什么回放必须绑定知识库 SHA

每个回放样本都保存了所用知识库文件的 SHA-256。

例如，退货规则的固定摘要是：

```text
64ce8519335ae6213d423c8a4450787cb48d43bc78985af3b7e32bf328d77849
```

人工裁决是针对这个确切版本编写的。如果知识库后来把期限改成 60 天，旧的 `contradicted` 标签可能已经失效。

因此文件内容变化时，系统必须拒绝旧回放，不能继续照搬旧分数。这与“试卷答案必须对应同一版题目”是一个道理。

---

## 7. 五组固定样本

课程包含五组实际样本：

| 样本 | 声明情况 | DeepEval 默认 | DeepEval 惩罚歧义 | Ragas |
|---|---|---:|---:|---:|
| `supported` | 两条有支持 | 1 | 1 | 1 |
| `unsupported` | 一条未支持 | 1 | 0 | 0 |
| `contradicted` | 一条相矛盾 | 0 | 0 | 0 |
| `mixed` | 支持、未支持、矛盾各一条 | 2/3 | 1/3 | 1/3 |
| `no_claims` | 没有事实性声明 | 1 | 1 | `null` |

这些是人工固定回放下可确定的结果，不是模型实测分数。

其中最值得注意的是 `no_claims`：

- DeepEval 没有裁决时，原始分数为 1；
- Ragas 没有声明或裁决时，原始值为 `NaN`；
- 保存报告时，Ragas 的值写成 JSON `null`，状态记为未评分。

这说明“1 分”不一定代表回答质量优秀。回答只有一句“你好！”，完全没有回答退货问题，却可能因为没有可扣分的声明而得到 DeepEval 原始 1 分。

---

## 8. 运行 Docker 实验

在项目根目录启动课程环境：

```bash
docker compose up --build -d
```

然后在浏览器打开：

```text
http://localhost:8765
```

运行本课默认回放：

```bash
docker compose exec course python s07_faithfulness/code.py
```

只回放混合样本：

```bash
docker compose run --rm course replay --sample mixed
```

搜索知识库中的“退款”：

```bash
docker compose run --rm course search "退款"
```

课程结果挂载到：

```text
./runs:/data/runs
```

默认知识库以只读方式挂载：

```text
./knowledge_base:/data/knowledge:ro
```

如果要使用自定义知识库，在 `.env` 中设置 `KNOWLEDGE_DIR`。对应的宿主机目录必须先存在，否则容器挂载行为可能与预期不同。

回放完成后，应在 `runs` 目录找到一份逐样本 JSON 记录。重点查看：

- `mode`：应为 `replay`；
- `interpretation`：说明它不是模型效果实验；
- `source_versions`：记录固定源码版本；
- `context_files`：记录知识库路径和 SHA；
- `human_claims`：记录人工声明；
- `metrics`：记录分数、裁决和调用信息。

---

## 9. 最小入口代码

课程入口是 [`code.py`](code.py)。它调用真实运行器，而不是自己实现评分公式。

```python
report = run(args.mode, args.sample)
for row in report["rows"]:
    scores = {
        name: value["score"]
        for name, value in row["metrics"].items()
    }
```

这里的 `run` 负责执行回放或真实裁判模式。循环只提取各指标的最终分数。

```python
print(row["id"], scores)
print(report["interpretation"])
print("已保存：", save(report))
```

输出会显示样本编号、分数和实验性质，随后将完整报告保存到运行记录目录。控制台摘要不是完整证据，逐声明记录应以保存的 JSON 为准。

---

## 10. 真实 SDK 如何被调用

运行器位于 [`../eval_course/runner.py`](../eval_course/runner.py)。

### 10.1 构造 DeepEval 测试样本

```python
test = LLMTestCase(
    input=case["question"],
    actual_output=case["answer"],
    retrieval_context=[d["text"] for d in docs],
)
```

这三个字段分别对应问题、回答和检索上下文。这里没有传入参考答案，因为 Faithfulness 不要求它。

### 10.2 切换两种 DeepEval 聚合策略

```python
metric = FaithfulnessMetric(
    model=DeepEvalJudge(backend),
    eval_mode="llm",
    penalize_ambiguous_claims=penalize,
    include_reason=False,
)
```

运行器对同一个样本执行两次：一次不惩罚 `borderline`，另一次惩罚它。

```python
score = await metric.a_measure(
    test,
    _show_indicator=False,
)
```

这里调用的是 DeepEval 自己的异步指标实现，回放适配器只替代模型输出。

### 10.3 调用 Ragas

```python
metric = Faithfulness(
    llm=RagasJudge(backend)
)
result = await metric.ascore(
    user_input=case["question"],
    response=case["answer"],
    retrieved_contexts=[d["text"] for d in docs],
)
```

同样，声明拆分、证据判断和分数计算仍由 Ragas 的真实指标管线组织。

### 10.4 把 `NaN` 转成严格 JSON

```python
finite = math.isfinite(float(result.value))
results["ragas"] = {
    "score": result.value if finite else None,
    "status": "scored" if finite else "not_scored",
}
```

Python 的 `None` 会被序列化为 JSON 的 `null`。这保留了“未评分”的含义，不会误导性地写成 0。

---

## 11. 回放裁判如何工作

适配器位于 [`../eval_course/judges.py`](../eval_course/judges.py)。

标签映射明确写在代码中：

```python
DE_LABELS = {
    "supported": "yes",
    "unsupported": "borderline",
    "contradicted": "no",
}
```

因此，人类三分类会被转换为 DeepEval 固定版本使用的三档裁决。

Ragas 的二元值则由下面的表达式产生：

```python
"verdict": int(
    c["label"] == "supported"
)
```

只有 `supported` 得到 1，`unsupported` 和 `contradicted` 都得到 0。

回放不是通过提示重新猜测答案，而是按结构化输出类型返回固定内容：

```python
if schema.__name__ not in payloads:
    raise ValueError(
        f"回放未定义该 schema：{schema.__name__}"
    )
```

如果真实 SDK 请求了课程没有定义的结构，回放会直接失败。这避免了在接口变化时静默伪造结果。

---

## 12. DeepEval 源码跟踪

固定源码文件：

- [`faithfulness.py`](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)
- [`qag.py`](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py)
- [`schema.py`](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/schema.py)

在 `a_measure` 中，`truths` 和 `claims` 被并行抽取：

```python
self.truths, self.claims = await asyncio.gather(
    self._a_generate_truths(
        retrieval_context, multimodal
    ),
    self._a_generate_claims(
        actual_output, multimodal
    ),
)
```

随后生成裁决并计算分数：

```python
self.verdicts = await self._a_generate_verdicts(
    multimodal
)
self.score = self._calculate_score()
```

`_calculate_score` 先决定哪些裁决算通过：

```python
passing = (
    (Verdict.YES,)
    if self.penalize_ambiguous_claims
    else (Verdict.YES, Verdict.BORDERLINE)
)
```

最后进入共享函数：

```python
return score_qag_verdicts(
    self,
    self.verdicts,
    passing=passing,
)
```

所以关键调用链是：

```text
a_measure
  → 并行抽取 truths 与 claims
  → 生成 verdicts
  → _calculate_score
  → score_qag_verdicts
```

`score_qag_verdicts` 计算通过数量占有效裁决总数的比例；没有裁决时默认返回 1。若启用 `strict_mode` 且分数低于阈值，则结果被钳制为 0。

---

## 13. Ragas 源码跟踪

固定源码文件：

- [`metric.py`](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)
- [`util.py`](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/util.py)

`ascore` 首先拆分声明：

```python
statements = await self._create_statements(
    user_input,
    response,
)
```

若没有声明，它直接返回 `NaN`：

```python
if not statements:
    return MetricResult(
        value=float("nan")
    )
```

随后合并上下文并生成裁决：

```python
context_str = "\n".join(
    retrieved_contexts
)
verdicts = await self._create_verdicts(
    statements,
    context_str,
)
```

最后计算支持比例：

```python
score = self._compute_score(verdicts)
return MetricResult(
    value=float(score)
)
```

关键调用链是：

```text
ascore
  → _create_statements
  → _create_verdicts
  → _compute_score
```

`_compute_score` 把裁决为 1 的声明数除以声明总数。裁决列表为空时同样返回 `NaN`。

两个框架都使用“先拆声明，再逐条判断，再聚合”的思想，但具体提示、标签空间、空值语义和聚合策略并不相同。

---

## 14. 四个练习

参考题目见 [`exercises.md`](exercises.md)，参考答案见 [`solutions.md`](solutions.md)。

### 练习一：手算混合样本

固定裁决为：

```text
[yes, borderline, no]
```

请计算：

1. DeepEval 默认分数；
2. DeepEval 惩罚歧义后的分数；
3. Ragas 对应 `[1, 0, 0]` 的分数。

可检查结果：

- DeepEval 默认：`2/3`；
- DeepEval 惩罚歧义：`1/3`；
- Ragas：`1/3`。

不应推导的结论：

> 不能据此断言 Ragas 比 DeepEval 更严格或效果更好，因为真实运行时二者可能拆出不同声明并给出不同裁决。

### 练习二：改变歧义策略

对 `unsupported` 样本分别使用：

```python
penalize_ambiguous_claims=False
```

和：

```python
penalize_ambiguous_claims=True
```

可检查结果：

- 默认模式下 `borderline` 通过，分数为 1；
- 惩罚歧义时 `borderline` 不通过，分数为 0。

不应推导的结论：

> 分数为 1 不代表“免费退货”得到证据支持，它只是该版本默认聚合策略允许 `borderline` 通过。

### 练习三：修改证据

把知识库补充为：

> 退货运费均由商家承担。

然后重新考虑“所有退货运费都由商家承担”的标签。

可检查结果：

- 新证据下，它应从 `unsupported` 变成 `supported`；
- 原回放绑定旧 SHA，必须拒绝继续使用；
- 应重新编写或确认回放标注，并更新对应摘要。

不应推导的结论：

> 不能只修改知识库后继续引用旧分数，因为旧裁决针对的是旧证据。

### 练习四：解释空声明

检查 `no_claims` 样本，其回答只有“你好！”。

可检查结果：

- DeepEval 原始结果为 1；
- Ragas 原始结果为 `NaN`；
- 报告中的 Ragas 分数为 JSON `null`，而不是 0；
- 该回答没有完成用户任务。

不应推导的结论：

> DeepEval 的 1 分不代表回答正确、相关或有用，只表示没有产生可扣分的有效裁决。

---

## 15. 验收清单

完成本章后，你应当能够：

- 区分 `supported`、`unsupported` 和 `contradicted`；
- 说明 Faithfulness 测量的是声明相对于检索上下文的证据支持；
- 解释为什么参考答案不是必需字段；
- 手算 DeepEval 两种歧义策略和 Ragas 二元口径；
- 说明固定提交、运行模式和聚合策略为何必须一起记录；
- 运行五组回放，并在 `runs` 中找到逐样本记录；
- 区分真实 SDK 回放与真实模型裁判实验；
- 解释知识库 SHA 为什么必须与人工标注绑定；
- 解释为什么 `null` 不能随意改成 0；
- 解释为什么 Faithfulness 得到 1 分也不保证回答质量高。

---

## 小结

Faithfulness 回答的不是“这句话在现实中是真的吗”，而是：

> 这句话能否由当前提供的证据支持？

可靠的评测需要先拆声明，再区分有支持、未支持和相矛盾，最后按明确且版本固定的规则聚合。分数必须与逐声明裁决、源码版本、运行模式和知识库 SHA 一起解释。

Faithfulness 只是回答质量的一块拼图。一个回答可以完全忠于文档，却仍然答非所问、遗漏重点，甚至忠于错误文档。接下来应继续评估答案正确性与相关性，而不能把忠实度分数当成完整质量结论。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)