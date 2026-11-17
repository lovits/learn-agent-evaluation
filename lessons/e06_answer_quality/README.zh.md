# e06: 答案质量 — 切题、答对、答全

[课程](../../README.md) · [上一课](../e05_faithfulness/README.zh.md) · [下一课](../e07_failure_diagnosis/README.zh.md) · [源码导读](source_walkthrough.md)

> 评价答案以前，先区分问题、证据和参考答案。

## 只回答认证头够吗

用户问上传接口的认证头、文件上限和超限状态码。回答只有：

> 使用 `X-Project-Token` 认证头。

它切题，内容也可能正确，但漏了两项。上一课的 Faithfulness 可以接受这句话，因为它没有编造事实，却不会因此发现所有遗漏。

本课保持 Agent 不变，给评分输入增加版本化 `reference`、可回答性与业务政策。

## 三种比较，各用自己的依据

| 要判断什么 | 比较什么 |
|---|---|
| 是否切题 | 问题与回答 |
| 是否忠于证据 | 当次检索结果与回答 |
| 事实是否正确、覆盖多少 | 指定版本 reference 与回答 |
| 是否满足业务要求 | 问题、reference、可回答性与政策 |

本课合成 v2 的上传上限是2097152字节。旧记录若属于 v1，就仍按 v1 的1048576字节评价；只有当前任务要求 v2 却使用旧资料时，才属于版本错误。

## 相关性为什么不核验数字

DeepEval 的调用只给问题与回答：

```python
sample = LLMTestCase(
    input=case["question"],
    actual_output=case["response"],
)
metric = AnswerRelevancyMetric(
    model=DeepJudge(transport), eval_mode="llm",
    async_mode=False, include_reason=False,
)
```

它拆出回答声明，再判断是否与问题相关。一个错误限额也可以很切题，因为这里没有参考数字供它核实。

Ragas 的 Answer Relevancy 使用另一条路：从回答反推问题，再比较反推问题与原问题的嵌入相似度。两者名字接近，测量过程不同。

## 事实精度与事实召回

Ragas `FactualCorrectness` 使用回答和 reference：

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

它先拆回答声明，判断 reference 是否支持；再反向拆参考声明，检查回答是否覆盖。

固定实现按正向支持数记 TP，正向不支持数记 FP，反向不支持数记 FN：

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
```

手算设 TP=1、FP=0、FN=2：precision 为1，recall 为1/3，F1 为0.5。回答说出的都对，仍可能漏掉大部分需求。F-beta 可按业务要求增加召回或精度的权重。

两次拆句粒度未必相同，实际计数要沿阶段结果核对，不能直接按句号数套公式。

## AnswerCorrectness 还混入了什么

Ragas `AnswerCorrectness` 分别生成回答与参考声明，再让分类器直接产出 TP/FP/FN。默认配置还混合嵌入相似度：

```text
正确性 = 0.75 × 事实分 + 0.25 × 相似度
```

本课调用显式使用 `weights=[1.0, 0.0]`，只讨论事实部分。相似度高表示语义空间接近，无法保证数字或否定关系正确。

这个固定版本在任一侧没有声明时，事实部分可直接得到1。拒答是否合理，需要另看业务政策。

## 证据不足时，怎样回答

文档没有写重试次数，不能推成“重试0次”。合格回答可以说明无法确定，并请求重试配置。

如果资料已经给全，却无理由拒答，也不满足任务。我们把这两种情况明确交给 G-Eval：

```python
policy = (
    f"Reference version: {case['reference_version']}\n"
    f"Answerable within supplied evidence: {case['answerable']}\n"
    f"Reference: {case['reference']}\nPolicy: {case['policy']}"
)
```

`expected_output` 携带这些标准。裁判同时检查所问事项的覆盖和合理拒答；外部代码是否修好，仍由任务检查器负责。

参考措辞也要准确。“使用这个头”若没有写明用于认证，逐声明 NLI 可能认为“认证头”没有依据。先补清参考本身，再讨论模型是否答错。

## 试一下

给同一问题准备三份回答：只答认证头、把限额答错、明确说明重试次数未知。逐一写出相关性、事实支持和需求覆盖应检查什么。

再把 reference 从 v1 换成 v2，指出哪些旧结论需要重新判断。

[计算示例](code.py) · [评分入口](eval.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

答案分数已经能说明不同问题。下一课把它们接回资料、检索和生成过程，追查错误最先出现在哪里。
