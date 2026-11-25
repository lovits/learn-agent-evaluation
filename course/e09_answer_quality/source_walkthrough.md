# e09 源码导读：切题性、事实覆盖与证据边界怎样各自打分

[教材](README.zh.md) · [评分函数](eval.py) · [样本与真实 Agent 入口](code.py)

## 本课调用链

[code.py](code.py) 中的 `prepare` 读取 [cases.jsonl](cases.jsonl) 的六组样本和统一 `spec`，逐一比对 `catalog()` 返回的 `atlas/release.md` 与 `atlas/logs.md` 的 SHA-256，确保基准文本没有改动。每条样本直接按 `case["context_paths"]` 取出对应文档作为 `retrieval_context`，以控制条件隔离单一变量。

`cases.jsonl` 里的 `fact_ids` 将“在项目根目录运行 `python -m pytest -q`”合为 `command` 一个必答单元，把“全部检查通过才能提交发布”标为 `gate`、把“失败时先修复，不跳过失败项”标为 `fix`。如果回答把命令写成 `python -m unittest`，即使提到了“根目录”，整个 `command` 单元依然视为未覆盖。如果改用更细的事实拆分粒度，对应的 `fact_ids` 和 F-beta 数值也会随之变化。

命令行传入 `--live` 时，`main` 复用第 5 课的 `run_task`（`k=3`、`context_limit=2`），在隔离工作目录中实际调用 `search_knowledge` 并保存完整运行轨迹、原始检索候选和真实 `model_inputs`。由于新生成的 `live_agent` 回答没有预先标注 `fact_ids`，`code.py` 只对其执行原生裁判评分，不会强行套用静态事实标签。

命令行传入 `--judge` 时，循环对每个条件从持久化样本里提取 `input`、`actual_output`、`expected_output` 和 `retrieval_context` 四个字段重建 `LLMTestCase`，分别传给 `judge_relevance` 与 `score(task_metric(model), sample)`。这样既把完整 `tools_called` 轨迹留在外层记录里，也避免 `AnswerRelevancyMetric` 或 `GEval` 因校验无关字段结构而中断；每次裁判返回后都会即时更新 `judge_calls` 并落盘保存进度。

## DeepEval：AnswerRelevancyMetric 的抽取与打分

以下源码分析基于 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念说明见 [Answer Relevancy](https://deepeval.com/docs/metrics-answer-relevancy)。

沿着 [answer_relevancy.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py) 的同步 `llm` 路径阅读，执行过程如下：

1. `_required_params` 只要求 `input` 和 `actual_output`。`measure` 先调用 `_generate_statements` 从 `actual_output` 抽取出陈述列表 `self.statements`，再交给 `_generate_verdicts` 对照问题逐条打标签，全程不读取 `expected_output` 或 `retrieval_context`。
2. 模板 [generate_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/templates/generate_verdicts.txt) 要求为每条陈述输出 `yes`、`no` 或 `borderline`。其中 `yes` 表示直接切题，`no` 表示跑题，`borderline` 表示可能起辅助作用的相关信息或无法直接解答的周边说明。
3. `_calculate_score` 调用 `score_qag_verdicts`，默认以 `(Verdict.YES, Verdict.BORDERLINE)` 作为通过集合，计算两者合计占比。当 `statements` 为空时，原生默认逻辑直接返回 `1.0`。
4. 设置 `include_reason=False` 会跳过最后一步 `_generate_reason`，因此每次评测发起两次模型请求（陈述抽取和逐条裁决）。

为了防止空回答或格式漂移产生误导分，[eval.py](eval.py) 中的 `judge_relevance` 在拿到原始返回后先记录 `sdk_score`、`statements` 和 `verdicts`：当 `statements` 为空时将对外 `status` 改为 `not_applicable` 并把 `score` 与 `passed` 设为 `None`；当 `len(verdicts) != len(statements)` 时标为 `error` 并置空分数。同时需要记住，由于分母是已抽取的陈述数，模型漏掉用户追问的条款不会出现在 `statements` 里，因此切题分高无法说明回答完整或命令正确。

## 集合算式：fact_scores 的分母与边界

`fact_scores(predicted, reference, beta=1.0)` 先校验证据权重参数 `beta` 为有限正数，再对 `predicted` 和 `reference` 取集合去重，计算 `tp`、`fp`、`fn`：

- 精确率分母是 `tp + fp`，衡量回答给出的事实中有多少命中了参考集合；当 `predicted` 为空时返回 `None`。
- 召回率分母是 `tp + fn`，衡量参考要求的事实有多少被回答覆盖；当 `reference` 为空时返回 `None`。
- `fbeta` 按 `(1 + beta**2) * tp / ((1 + beta**2) * tp + beta**2 * fn + fp)` 计算；当分子分母同时为零（双方均为空集）时返回 `None`，以免把“无事实可比”误作 `0` 分或满分。

在分析结果时还要留意参考本身的范围：当回答里多出一条客观真实、但不在本题 `reference_fact_ids` 里的陈述（如 `off_topic` 里的 `logs`），它会落入 `fp`；而若参考集合本身遗漏了合理答案要素，同样会把真实有用的回答算成 `fp`。因此出现 `fp` 时要先核对题目范围与参考清单。

## DeepEval：用 GEval 写清证据边界

[官方 Answer Correctness 指南](https://deepeval.com/guides/guides-answer-correctness-metric) 示范了用 `GEval` 结合特定应用目标定制正确性指标的做法。本课复用第 4 课接入的 `GEval` 路径，在 [eval.py](eval.py) 的 `task_metric` 中把 `INPUT`、`ACTUAL_OUTPUT`、`EXPECTED_OUTPUT` 和 `RETRIEVAL_CONTEXT` 四个 `SingleTurnParams` 一起交给裁判。

`evaluation_steps` 明确规定了两层核对顺序：第一层先检查 `retrieval_context` 是否足以支撑问题所需的发布规范；第二层根据证据是否充足走不同判定标准。如果上下文充足，按 `Rubric` 分别对完全覆盖给 `2` 分、仅部分正确给 `1` 分、跑题或矛盾或拒答给 `0` 分；如果上下文缺少发布规范，只要明确说明缺失并请求补充、不靠猜测作答就给 `2` 分，即便蒙对了 `expected_output` 里的字面命令也只给 `0` 分。

SDK 随后按 `(原始分 - 0) / (2 - 0)` 将分档归一化到 `0` 到 `1`，再与 `threshold=1.0` 比较得出是否通过。由于本课的 `JudgeModel` 适配器沿直接结构化输出路径评分（不支持 token 级 `logprobs` 加权），保存的 `score` 直接对应三档归一化结果，`reason` 则完整记录裁判依据。`task_metric` 体现的是本课特定的证据策略标准，属于独立维度，不等于切题性与事实 F1 的平均值。

[样本与评测记录](assessment.md)
