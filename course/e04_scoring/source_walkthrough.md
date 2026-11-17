# e04 源码导读：从判据到分数

[教材](README.zh.md) · [评分代码](eval.py) · [运行入口](code.py)

## 本课调用链

`code.main` 读取构造回答，或复用第二课的 `agent_loop` 产生真实回答，再构造 `LLMTestCase`。`UploadContract.measure` 检查 JSON 合约；`GEval.measure` 判断 explanation 的含义。`score` 分别保留状态、分数、阈值判断和理由，不把两项平均成一个总分。

规则检查对象、字段集合、类型和固定数值。解释只检查非空字符串。即使这段话写错了，结构也可能达标。

`eval_course/judge.py` 是 DeepEval 的模型适配器：继承 `DeepEvalBaseLLM`，经已有宿主机接口请求模型，再用指标传入的 Pydantic schema 校验 JSON。它不读取 Agent 工作目录。`calls` 保留模型原始文本、耗时和 usage；没有价格依据时不推算费用。

## DeepEval：G-Eval 怎样得到分数

固定提交：[34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)。概念参考 [G-Eval](https://deepeval.com/docs/metrics-llm-evals) 和[自定义指标](https://deepeval.com/docs/metrics-custom)。

沿 [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 看四处：

1. `__init__` 保存所选字段、判据或步骤、rubric 和阈值。`criteria` 交给模型生成步骤；本课直接给 `evaluation_steps`，固定实际评分步骤，不同时传两种参数。
2. `_validate` 核对需要的样本字段。`_results_prompt` 把所选字段、编号步骤、rubric 和分数区间组装为提示词。本课只传任务、回答和参考，工具轨迹不参与这一语义分。
3. `_generate_evaluation_steps` 遇到已有步骤直接返回。`_evaluate` 调用 `generate_rubric_score` 得到原始分和理由。
4. 非 strict 模式下，`measure` 使用 `(原始分 - 下界) / (上界 - 下界)`。本课量表为 0—2，因此除以 2。阈值 1 表示要求达到完整档；它不是“正确概率为 100%”。

[decision.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/decision.py) 的 `generate_rubric_score` 还区分模型是否支持 logprobs。支持时可对评分 token 做加权；本课适配器明确不支持，走结构化分数分支，不宣称运行了概率加权。

[generation.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/generation.py) 的 `generate_with_schema_and_extract` 接收 schema 实例或解析 JSON。本课适配器进一步执行 `schema.model_validate_json`；`score` 检查最终数值有限且位于 0—1。合法 JSON 仍可能判断错误，第 14 课再用标签校准裁判。

[BaseMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py) 提供分数、理由、错误与阈值字段。本课 `UploadContract` 继承它，实现同步与异步测量，直接使用 DeepEval 样本，不另建评测框架。

[DAGMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py) 把任务和判断节点组织成有向无环图，适合多阶段判据；其中判断仍可调用模型。一个 JSON 合约用几条明确规则已经足够，本课只读其分支组织思路，不运行 DAG。

## Ragas：二元判定与分档量表

固定提交：[8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)。只作原理对照，本课没有 Ragas 调用或第二套评分。

[AspectCritic](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/_aspect_critic.py) 是该提交保留的旧接口：`definition` 进入提示词，输出 `reason` 与二元 `verdict`，然后由 `_compute_score` 取裁决。代码虽然保留 strictness 的多数票逻辑，这一版本 `_ascore` 实际给 `_compute_score` 的是单个 response；不能据参数名就说已经多次独立投票。概念见 [Aspect Critique](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/)。

现代 collections 的 [DomainSpecificRubrics](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/domain_specific_rubrics/metric.py) 在初始化时把量表写入 prompt，`ascore` 组装任务、回答及可选参考/上下文，再返回 `MetricResult(value=float(result.score), reason=result.feedback)`。默认分档为 1—5，没有在此处自动变成 DeepEval 的 0—1；比较分数之前必须先看量表。

[MetricResult](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/result.py) 保存 value、reason 和可选 traces，允许多种结果类型。结果容器本身不定义“多少分算完成”，也不能替你选分母。

## Precision / recall 的单位

`set_scores` 的输入是已经确定的项目 ID 集合，不是从回答自动抽出的事实。本课的 `header`、`limit`、`status` 只是解释分母的构造标签。

交集数为 TP，预测集合大小为 TP+FP，参考集合大小为 TP+FN。重复 ID 先去重。precision 分母是预测项数，recall 分母是参考项数；F1 为 `2TP/(预测项数+参考项数)`。空分母保留 `None`，这是本课显式选定的约定。后面的检索课、工具课会各自规定评分单位，不能把同一公式中的单位随意替换。

## 评分状态

`score` 只把已取得的有效数值记为 `ok`；网络、解析或数值校验错误记为 `error`，分数与是否达标均为空。规则判定不满足是有效零分；空集合分母的 `None` 表示未定义。三者需要连同状态解释，不能全填成 0 后求平均。
