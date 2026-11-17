# e09: 资料没说错，问题答好了吗？

[e08](../e08_faithfulness/README.zh.md) → `e09` → [e10](../e10_rag_diagnosis/README.zh.md) → … → e16

> 切题、正确、完整，要分别检查。

## 问题

用户问 Atlas 发布前运行什么命令、什么条件下可以发布、检查失败怎么办。回答却说“审计日志保留 14 天”。这句话符合资料，但没有解决问题。

另一份回答只给出了正确命令。说出来的内容没有错，发布条件和失败处理却漏了。忠实度已经不足以区分这些情况。

## 解决方案

固定问题与参考，构造离题、错误、漏项和完整回答。再固定回答、减少可见资料，比较无依据猜答与合理拒答。各维度分别保留，不直接平均成一个总分。

![分别用问题、参考和可见资料检查答案质量](https://lovits.github.io/learn-agent-evaluation/diagrams/e09-quality-flow.png)

切题性使用 DeepEval 原生指标；事实 ID 标签展开正确与遗漏的算式；G-Eval 则依据本课明确的任务标准，综合判断是否恰当地回答或拒答。

![G-Eval 根据证据充分程度判断回答或拒答](https://lovits.github.io/learn-agent-evaluation/diagrams/e09-scoring-flow.png)

## 工作原理

### 同一回答，面对三种比较对象

[prepare](code.py) 先核对来源哈希，再构造样本：

```python
LLMTestCase(
    input=spec["query"],
    actual_output=case["answer"],
    expected_output=spec["reference"],
    retrieval_context=[documents[path]["text"] for path in case["context_paths"]],
)
```

input 说明用户问什么，expected_output 说明参考要求什么，retrieval_context 说明回答方有哪些证据。参考由评测方持有，不等于 Agent 当时读过它。

[六组样本](cases.jsonl) 是明确标注的教学构造。加 `--live` 时复用第 5 课 Agent，实际搜索挂载知识库并回答；真实轨迹与构造样本分开保存，不预先给新回答填事实标签。

### 切题性：回答在解决这个问题吗

[judge_relevance](eval.py) 调用 `AnswerRelevancyMetric`。它先从实际回答提取 statements，再根据问题判断每条是否相关：

```python
metric = AnswerRelevancyMetric(
    model=model, eval_mode="llm", async_mode=False, include_reason=False
)
```

固定实现以 yes 和 borderline 为通过项，除以有效裁决数。这里 borderline 表示可能起辅助作用的模糊相关信息，不能套用上一课忠实度的标签含义。

它不读取参考答案来校验命令。错误命令仍可能切题；只回答命令而漏掉其他要求，也可能所有已说出的句子都相关。因此，相关比例既不证明正确，也不证明完整。

本课保留 statements 与 verdicts，并检查数量。空 statements 标记不适用，数量不齐标记评分错误，不用异常结果冒充有效分数。

### 正确与遗漏：先展开事实标签

参考包含三个事实：command 是根目录下的测试命令，gate 是全部检查通过的发布条件，fix 是失败先修复、不跳过。

在已经审核的事实 ID 上，集合关系很直接：

```python
tp = len(predicted & reference)
fp = len(predicted - reference)
fn = len(reference - predicted)
```

TP 是回答覆盖的参考事实，FP 是回答增加而参考未支持的事实，FN 是参考要求却遗漏的事实。FP 不自动等于现实中错误：日志保留 14 天可能真实，却不在本题发布参考中。

这些 ID 来自课程编写助手的教学标注，不是模型自动提取或独立人工金标准。[fact_scores](eval.py) 只负责算集合，不能读一段自然语言就证明它对不对。

### 精确率与召回率的分母不同

只回答 command 时，手算得到 TP=1、FP=0、FN=2：

```text
事实精确率 = TP / (TP + FP) = 1
事实召回率 = TP / (TP + FN) = 1/3
```

前者看说出的事实中有多少与参考对齐；后者看参考要求覆盖了多少。这和上下文召回使用了相似算式，但这里的对象已经换成回答事实。

F-beta 合并这两个方向：

```text
Fβ = (1 + β²)TP / [(1 + β²)TP + β²FN + FP]
```

β=1 时等权，刚才的例子 F1=1/2；β>1 更重视遗漏，β<1 更重视额外未支持事实。选择权重需要依据任务代价，不能认为某个 β 普遍更好。

空回答事实、非空参考时，精确率未定义，召回为 0，F-beta 为 0；两边都空则 F-beta 也未定义。课程用 None 表示未定义，避免与有效零分混淆。

### Ragas 怎样从自然语言得到这些量

Ragas 的 FactualCorrectness 使用模型拆分声明，再做双向支持判断：回答声明是否被参考支持，参考声明是否被回答覆盖，最后形成 TP、FP、FN 并聚合。

声明粒度和参考完整性都会影响结果。把一条复合事实拆成几条，可能改变计数；参考漏掉正确事实，也可能产生看似多余的 FP。因此事实级分数仍需要追到声明与依据。[源码导读](source_walkthrough.md)保留具体实现，本课没有另接一套 Ragas 评分。

### 猜中参考，仍可能违反证据要求

本课规定知识库助理只按给定资料回答；资料不足时，应说明缺失并请求发布规范。complete 与 unsupported_answer 的回答完全相同，后者却只收到日志资料。

只与参考比较，两者都覆盖三个事实；加上可见资料，后者是在没有发布证据时自信作答。相反，合理拒答几乎不覆盖参考事实，却符合这个场景的行为要求。

不能让事实 F1 替代这项策略判断。[task_metric](eval.py) 复用 G-Eval，并明确传入四个字段：

```python
evaluation_params=[
    SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT, SingleTurnParams.RETRIEVAL_CONTEXT,
]
```

评分标准是 0、1、2 级：离题、矛盾、无据断言为 0；证据充分但只正确答出部分为 1；有据且完整，或缺证据时明确保留、不猜测并请求资料，为 2。SDK 将等级归一化到 0～1。

这是本课任务标准的综合判断，不是把相关性、事实 F1 和拒答简单相加。拒答是否恰当取决于资料；证据充分仍拒答也不能通过。裁判仍可能误判，所以要保留理由，后续再校准。

### 相似度为什么只能作辅助

Ragas Response Relevancy 从回答反向生成问题，再比较这些问题与原问题的向量相似度；SemanticSimilarity 则比较回答与参考的向量。

两者比较的对象不同。后者适合观察改写是否语义接近，却不能单独保证关键事实正确。“全部检查通过才能发布”和“全部检查失败才能发布”只有少数词变化，规则已经相反。即使向量接近，也要另查事实。

合理拒答与完整参考可能并不相似，仍可能是缺证据时的正确行为。相似度也不能代替证据策略。

## 本课变化

Agent 与 TinyRAG 保持原实现。新增答案对照样本、参考事实标签与 F-beta、原生切题性和 G-Eval 任务标准。真实运行保存完整轨迹，评分只读取所需字段；每个样本完成后保存已有结果。

## 试一下

```sh
python -m course.e09_answer_quality.code
```

1. 比较 off_topic 与 on_topic_wrong，说明真实、切题分别缺少什么判断。
2. 对 incomplete 手算 TP、FP、FN，再改变 β，观察遗漏的权重。
3. 比较 complete 与 unsupported_answer：回答没变，为什么任务标准不同？
4. 用 `--live --judge` 查看真实 Agent 的上下文、回答和原生理由。新回答的事实 ID 没有预先标注，不应直接套用构造标签。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

现在能指出答案偏题、说错、漏项或越过证据边界。下一课把这些观察放回检索与生成链路，找出错误从哪个阶段开始。
