# e15 源码导读：从标签到对齐与偏差检查

[教材](README.zh.md) · [样本与统计](code.py) · [裁判](eval.py)

## 先看输入有没有泄漏

`make_cases` 产生明确的合同记录，`validate_cases` 检查标签、重复 ID 与跨集家族。`judge_input` 只发送评价需要的证据，省略 label、split 与辅助构造字段。

构造标签不是人工投票。样本标签来源和人工审核状态应保留，正式项目不能把自动一致称成人类一致。

## DeepEval G-Eval 的标准选择

[文档](https://deepeval.com/docs/metrics-llm-evals) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)

`score → measure → _validate → _generate_evaluation_steps → _evaluate → generate_rubric_score → 归一化`。

显式步骤省去生成标准的请求。无 raw/logprobs 支持时回退到 schema 评分。阈值将连续等级映射成通过，不代表正确概率。

`select_version` 先排除未完整评分的候选，再优先减少误放行、比较一致率；同分政策预先声明。`atomic_save` 保存选择以后才评分留出集。

## Ragas 少样本对齐

[对齐指南](https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/) · [discrete.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/discrete.py) · [base.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/base.py)

`DiscreteMetric` 建立离散结果 schema，`SimpleLLMMetric.score/ascore` 格式化提示，再由结构化模型返回 `MetricResult`。

`align` 从训练 Dataset 读取输入变量、标签及理由，交给 `DynamicFewShotPrompt`。`embedding_model=None` 使用最近示例；有 embedding 的相似选择是另一条路径。固定版本的旧 wrapper 与示例库可能接口不匹配，要按实际模型类型核对。

`validate_alignment` 计算 agreement 与 κ。固定实现分别过滤 None 时存在配对错位风险，本课 `alignment` 始终按同一 ID 保留成对记录，把未评分计入覆盖率。κ分母退化时保留空值。

## 中文适配经过哪些步骤

[语言适配说明](https://docs.ragas.io/en/stable/howtos/customizations/metrics/metrics_language_adaptation/) · [BasePrompt](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/prompt/metrics/base_prompt.py)

`adapt → 收集示例字符串 → 翻译 → 检查数量 → 更新深拷贝 → 可选翻译指令`。空示例在固定实现会提前返回，仅更新 language，因此字段变化不证明指令已翻译。

本课用数字标签避免翻译固定枚举，仍需核对否定、范围和“诚实失败报告可准确”的语义。

## 偏差比较按内容回映

`equivalent_pairs` 检查等义改写，A/B 交换后映射回内容 ID。位置稳定性与是否选对分别统计。作者身份提示只是一条线索，无法在未知真实模型身份时证明自偏好。

误放行、误拒绝、覆盖与分歧一起看，才能判断下一步改标准、改输入还是换裁判。位置与篇幅偏差的研究背景见 [MT-Bench](https://arxiv.org/abs/2306.05685)。
