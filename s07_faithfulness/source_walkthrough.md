# s07 源码分析：沿一次评分走到分母

本页分析固定源码，不以官网最新示例代替版本事实。原始文件的只读副本在
`references/upstream/`，每个文件的 URL 和 SHA-256 在
`references/sources.json`。依赖锁中的 SDK 也使用相同 commit。

可直接离线阅读 [DeepEval 源码副本](../references/upstream/deepeval/deepeval/metrics/faithfulness/faithfulness.py)
和 [Ragas 源码副本](../references/upstream/ragas/src/ragas/metrics/collections/faithfulness/metric.py)。

## 先确定测量对象

问题、实际回答、检索上下文是输入。我们关心回答中的声明是否被这次检索上下文支持，
没有使用标准答案来替代证据。两套框架还会独立拆分声明，裁判和 prompt 也不同；
真实模型运行时不能把同名指标的分数看成同一把尺。

## DeepEval：抽取、判定、聚合

固定 commit：`34db63dd005ebc9a905c8ef4741ae0687c93c14c`，本课显式 `eval_mode="llm"`。

1. `FaithfulnessMetric.a_measure` 读取实际回答和检索上下文。
2. `asyncio.gather` 并行抽取 truths 和 claims，随后生成 verdicts。
3. `_calculate_score` 根据 `penalize_ambiguous_claims` 选择通过类别。
4. `score_qag_verdicts` 以有效 verdict 数为分母，空列表默认得到 1。
5. `strict_mode` 另做阈值钳制，和“惩罚歧义”不是一个开关。

关键原始代码：

```python
passing = (
    (Verdict.YES,)
    if self.penalize_ambiguous_claims
    else (Verdict.YES, Verdict.BORDERLINE)
)
return score_qag_verdicts(self, self.verdicts, passing=passing)
```

本版提示词把“直接矛盾”判 no，把“不被支持但未直接矛盾”判 borderline；
历史 idk 也被归一化到 borderline。默认不惩罚它，所以高分不保证证据充分。
这是该版本的语义，不能无条件推广到全部版本或 hybrid/system_one 模式。

源码：
- [FaithfulnessMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py#L161)
- [聚合与空列表](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py#L113)
- [文本 verdict 指令](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/templates/metrics/fragments/faithfulness_verdicts_guidelines_text_only.txt)

## Ragas：声明、NLI、支持比例

固定 commit：`8c63f10d500c44efbf24fdb9e2920de2104c321c`，使用
`ragas.metrics.collections.Faithfulness`。

1. `ascore` 校验 response、user_input、retrieved_contexts 非空。
2. `_create_statements` 让裁判将回答拆为可独立理解的声明。
3. `_create_verdicts` 把上下文合并，逐声明判断是否可以直接推断。
4. `_compute_score` 计算支持声明数 / verdict 数；无声明时是 NaN。

关键原始代码：

```python
if not verdicts.statements:
    return float("nan")
faithful_statements = sum(
    1 if statement.verdict else 0 for statement in verdicts.statements
)
num_statements = len(verdicts.statements)
```

NLI 提示词只有 0/1：不被支持和直接矛盾都不得分。它仍然是模型判断，
不是对任意文本都可靠的逻辑证明器。

源码：
- [ascore 与聚合](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py#L88)
- [NLI 指令与未提及的反例](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/util.py#L86)

## 本项目怎样让评分可观察

`eval_course/judges.py` 的 Replay 返回课程预设的结构化输出，真实 SDK 负责发起
阶段调用和聚合。它不从任意句子推理语义，也没有替换 SDK 的计算函数。

`eval_course/runner.py` 记录模型收到的 schema、prompt 哈希、结构化响应、声明、
verdict 和最终分数。NaN 保存为 JSON null，并保留未评分原因。DeepEval 空声明的原始
1 分会照实呈现；不要据此声称空洞回答是好回答，也不要把 null 当成 0 求平均。

回放的知识库文本有 SHA-256 校验。修改证据后旧标注失效，回放必须拒绝；
新的真实裁判实验读取当前挂载文件，结果可能因抽取或判定不同而变化。
