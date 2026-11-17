# e08: 回答里的话，资料支持吗？

[e07](../e07_context_recall/README.zh.md) → `e08` → [e09](../../docs/curriculum.md#09-答案质量) → … → e16

> 从回答拆出声明，再逐条寻找证据。

## 问题

资料写着“Atlas 审计日志保留 14 天”，回答却说“保留 30 天”。检索已经找到了正确资料，生成仍然可能出错。

另一种回答说“Atlas 仓库使用 GitLab 托管”。资料没有提及托管平台。这与前面的期限矛盾不同：一项有相反证据，另一项根本没有证据。

需要把回答里的事实分别拿出来，检查它们与本次上下文的关系。

## 解决方案

复用第 5 课的真实回答和当时交给模型的资料。DeepEval 先从资料抽取 truths、从回答抽取 claims，再逐声明判定。中间结果随分数一起保存。

![从实际上下文与回答分别抽取事实和声明，再逐条判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e08-claim-flow.png)

判定之后还要核对聚合口径。同一批裁决可以分别计算默认比例和明确支持比例，整个过程不需要再次调用裁判。

![检查声明与裁决数量，再按两种口径聚合](https://lovits.github.io/learn-agent-evaluation/diagrams/e08-scoring-flow.png)

## 工作原理

### 评分对象是回答与当时的证据

[prepare](code.py) 读取已有的原始记录，先校验文件哈希，再取三个字段：

```python
LLMTestCase(
    input=baseline["task"],
    actual_output=baseline["final_answer"],
    retrieval_context=baseline["sample"]["retrieval_context"],
)
```

这里读取第 5 课的 baseline；没有重新生成一次 Agent 回答。`retrieval_context` 使用实际送入模型的检索资料，不把后来找到的参考补进去。

忠实度检查回答是否符合给定证据，不需要标准答案。上一课的召回则从参考事实出发，检查资料够不够。两者的检查方向不同。

### 先把复合句拆开

“发布前运行 pytest，日志保留 30 天”包含两个事实。测试命令得到支持，不应顺带让日志期限通过。

声明应能独立判断，并保留主体、条件、数值。把“全部检查通过后才能发布”缩成“可以发布”，已经丢掉了关键条件。声明拆解改变了被评测内容，后面的除法无法补回这些遗漏。

本课用原生指标执行拆解：

```python
metric = FaithfulnessMetric(
    model=model, eval_mode="llm", async_mode=False, include_reason=False
)
result = score(metric, sample)
```

[judge_faithfulness](eval.py) 继续复用第四课的裁判适配器与评分错误处理。固定实现的这条路径包含三次模型请求：从上下文抽取 truths，从回答抽取 claims，再根据 truths 判断 claims。关闭总分解释不影响这三个步骤。

truths 是模型抽取的资料内容，不是经过外部核验的真实事实。若这一步漏掉条件或来源编号，后面的裁判也可能失去判断依据，所以记录不能只留最终分数。

### 支持、矛盾、未支持

NLI，即自然语言推断，在这里问：给定这份证据，能推出这条声明吗？先分清三种关系：

| 关系 | 资料与回答 | 本课固定 DeepEval 提示词 |
|---|---|---|
| 支持 | 都说明日志保留 14 天 | yes |
| 矛盾 | 资料写 14 天，回答说 30 天 | no |
| 未支持 | 回答说用 GitLab，资料没有托管平台信息 | borderline |

固定模板要求只有直接矛盾才判 no；没有依据但不矛盾，或模糊、推测性的表述，使用 borderline。裁判应按给定资料判断，不能用自己的常识替回答补证据。

这三个标签是 DeepEval 当前模板的约定，不能把 borderline 当成所有 NLI 系统通用的“中立”标签。

### 默认分数允许 borderline 通过

固定 DeepEval 默认 `penalize_ambiguous_claims=False`，聚合时 yes 和 borderline 都进入分子：

```text
默认分数     = (yes 数 + borderline 数) / 有效裁决数
明确支持比例 = yes 数 / 有效裁决数
```

手算标签 `[yes, yes, borderline]`：默认分数为 1，明确支持比例为 2/3。默认满分不能解释成“三条都有资料支持”。

[aggregate](eval.py) 直接展开这段聚合：

```python
passing = {"yes"} if penalize_ambiguous else {"yes", "borderline"}
return sum(label in passing for label in labels) / len(labels)
```

真实评分中的 score 来自原生 DeepEval；support_score 复用同一次的原始 verdicts，只统计 yes。它对应开启 penalize_ambiguous_claims 后的聚合口径，不是另一轮模型判断，也没有调用 Ragas。

不要把这个选项与 strict_mode 混淆。前者决定哪些标签算通过；后者会将低于阈值的比例压成 0。本课关闭 strict_mode，保留比例。

Ragas 的 Faithfulness 则将回答拆成声明，判断每条能否从原上下文推得，以 0/1 聚合支持比例。它没有 DeepEval 这一步 truths 抽取，也没有相同的默认 borderline 通过规则。相近名称不能保证相同含义，详细调用链见[源码导读](source_walkthrough.md)。

### 改了证据，忠实度也会变

[样本](cases.jsonl) 除了真实记录，还提供明确标注的构造回答。先让回答说“日志保留 30 天”，对照原始的 14 天资料；再保持回答不变，只把教学上下文改成 30 天。

后一组的期限声明能得到当前证据支持，却仍不符合原始 Atlas 规范。这说明忠实度依赖给定上下文，不能单独证明现实正确性。替换资料只是教学反例，不是检索器实际返回的新版本。

### 知识库证据不能证明工具做过什么

真实 Agent 回答还包含“已写入并读回 check.txt”。发布规范能说明应该运行什么命令，不能证明文件确实写过。

本课忠实度只传知识库上下文。执行类声明可能因此被判 borderline，需要回到工具轨迹核对，不能直接宣布 Agent 撒谎。第 11、12 课再评价工具使用与任务完成。评分边界取决于交给裁判的证据范围。

### 空声明与错误分别处理

回答“我无法根据资料确定”可能没有可抽取的事实声明。原生 DeepEval 空裁决聚合返回 1；本课保留该值在 sdk_score，同时将对外结果标为 not_applicable，score 与 passed 留空。

这不代表回答完成了任务，合理拒答和答案完整性还要另评。如果提取出三条声明却只返回两条裁决，则记评分错误，同样不给有效分数。数量一致也只解决基本对齐，仍应核对声明有没有丢失原意。

## 本课变化

Agent 与检索器保持已有实现。只增加声明评测和中间记录，保留 truths、claims、verdicts，以及两种明确注明口径的比例。构造标签用于手算，真实裁判结果独立保存，不要求两者自动一致。

## 试一下

```sh
python -m course.e08_faithfulness.code
```

1. 对照 unmentioned 与 contradicted，指出“没依据”与“有反证”的区别。
2. 比较 contradicted 和 changed_evidence，确认回答没变，证据变了什么。
3. 加 `--judge`，沿 truths、claims、verdicts 找到分数的来源。
4. 在 frozen_agent 中区分知识声明与执行声明，分别说明应当查哪些证据。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

忠于资料的回答仍可能答非所问，或漏掉用户要求。下一课把切题、正确和完整分开评价。
