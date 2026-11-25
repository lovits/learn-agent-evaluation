# e04 源码导读：从判据到分数

[教材](README.zh.md) · [评分代码](eval.py) · [运行入口](code.py)

## 本课调用链

`code.py` 中的 `main` 从 [cases.jsonl](cases.jsonl) 读入五条对照样本，或者在传入 `--live-agent` 时复用第 2 课的 `agent_loop` 读取 `upload.md` 生成真实回答，再组装成 `LLMTestCase`。

每条样本都会分别交给 [eval.py](eval.py) 中的两套指标独立执行：`UploadContract.measure` 校验 JSON 结构、字段集合、字段类型和固定常量；`explanation_metric` 构建的 `GEval` 则读取任务、实际输出与参考答案，给出解释字段的语义得分。`score` 包装函数分别记录两者的 `status`、`score`、`passed` 与 `reason`，保留各自诊断信息而不做简单平均。

模型裁判请求通过 [judge.py](../../eval_course/judge.py) 中的 `JudgeModel` 发出。`JudgeModel` 继承 `DeepEvalBaseLLM`，经宿主机桥接地址请求模型，再用指标传入的 Pydantic schema 对返回文本执行 `schema.model_validate_json` 校验，同时将原始返回、耗时和 token `usage` 追加到 `self.calls`。

## DeepEval：G-Eval 怎样得到分数

本课对应 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，官方概念说明见 [G-Eval](https://deepeval.com/docs/metrics-llm-evals) 与[自定义指标](https://deepeval.com/docs/metrics-custom)。

沿着 [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 跟踪同步 `measure` 路径，执行分为四步：

1. `__init__` 保存评估字段（`evaluation_params`）、评分步骤或判据、`rubric` 和 `threshold`。若传入 `criteria`，DeepEval 会额外让模型生成步骤；本课直接提供固定的 `evaluation_steps`，保证每次评估使用相同的审题规则。
2. `_validate` 核对样本是否包含所需字段，随后 `_results_prompt` 把选定字段、编号步骤、量表和分值区间拼接成裁判提示词。本课只传入 `INPUT`、`ACTUAL_OUTPUT` 与 `EXPECTED_OUTPUT`，工具轨迹不参与语义评分。
3. `_generate_evaluation_steps` 检测到已有 `evaluation_steps` 后直接返回，跳过步骤生成请求；接着 `_evaluate` 调用 `generate_rubric_score` 获取原始分和理由。
4. 在非 `strict_mode` 下，`measure` 按 `(原始分 - 下界) / (上界 - 下界)` 将原始分归一化。本课量表为 `0` 至 `2`，因此除以 `2`；`threshold=1.0` 表示回答必须达到 `2` 分这一完整档位，代表含义完整覆盖，而非正确概率。

[decision.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/decision.py) 中的 `generate_rubric_score` 会检查模型是否支持 logprobs：支持时会对分值 token 做概率加权；本课 `JudgeModel.supports_log_probs()` 返回 `False`，因此稳定走结构化分数分支，返回离散整数档位。

[generation.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/generation.py) 的 `generate_with_schema_and_extract` 负责解析模型返回并应用 schema。在 `JudgeModel` 验证 JSON 结构通过后，`score` 会继续检查返回值是否为 `0` 至 `1` 之间的有限浮点数。需要注意，JSON 结构合规仍可能包含误判，裁判自身的准确性会在第 14 课通过对照标签来校准。

## BaseMetric 与 DAGMetric

[base_metric.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py) 定义了指标的通用属性与接口契约（`score`、`reason`、`success`、`threshold` 以及 `measure` / `a_measure`）。本课的 `UploadContract` 直接继承 `BaseMetric`，因此可以无缝接入 `score` 包装函数和 DeepEval 的 `LLMTestCase` 样本结构。

对于需要多阶段条件分支的复杂判定，DeepEval 还提供了 [DAGMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py)，允许把确定性规则节点与模型裁判节点编排成有向无环图。本课的 JSON 合约只需平铺核对几个字段条件，因此用单步 `BaseMetric` 子类即可清晰表达。

## 集合指标的评分单位

`set_scores` 接收的是已经确定好边界的项目 ID 列表，例如本课用来演示分母的 `header`、`limit` 和 `status`，它本身不承担从自然语言抽取标签的职责。

函数先通过 `set` 去重，再以交集大小作为 `TP`、预测集合大小作为 `TP + FP`、参考集合大小作为 `TP + FN`，计算 `precision`、`recall` 与 `F1 = 2 * TP / (预测项数 + 参考项数)`。当某侧分母为空时返回 `None`，避免把无从算起的比例硬写成零分。后续检索课与工具课会在这个统一算式下，分别把条目单位替换成文档、事实或工具调用。

## 评分状态与错误处理

[eval.py](eval.py) 中的 `score` 函数把每次测量结果分为三类清晰状态：

- 正常完成且数值落在 `0` 至 `1` 之间：记录 `status="ok"`，若条件不满足则产生有效的 `0.0` 分。
- 网络连接失败、返回内容无法通过 Pydantic schema 校验或分值越界：记录 `status="error"`，将 `score` 与 `passed` 设为 `None`，并在 `reason` 中保留异常详情。
- 集合算式遇到空分母：返回 `None` 代表指标当前未定义。

将这三种情况连同 `ok` 计数与 `error` 计数一并报告，才能避免把基础设施故障或空分母误算进模型能力均值。

[样本与评测记录](assessment.md)
