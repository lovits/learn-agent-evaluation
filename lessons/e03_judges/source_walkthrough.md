# e03 源码导读：规则怎样变成裁决

[教材](README.zh.md) · [规则](code.py) · [模型裁判](eval.py)

## 从规则函数读起

`rules` 分别返回 `exact_match`、`json_contract`、`state_contract` 和工具集合分。它们对应不同条件，不能互相代替。

`set_f1` 明确选择空集合约定：双方都为空时为1，仅一方为空时为0。先确定任务是否需要工具，再决定这个分数有没有业务意义。

## DeepEval G-Eval

[官方说明](https://deepeval.com/docs/metrics-llm-evals) · [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)

```text
measure
  → _validate：检查 evaluation_params 对应字段
  → _generate_evaluation_steps：复用显式步骤或生成步骤
  → _evaluate：组织样本与评分要求
  → generate_rubric_score：请求评分和理由
  → 按 score_range 归一化
```

提供 `evaluation_steps` 可以固定本次标准，减少一步标准生成。自定义 `DeepJudge` 接收 prompt 与 schema，再把模型文本恢复为结构化对象。

原生评分工具会尝试支持概率的路径，不支持时进入 schema 路径。本课适配不提供 logprobs，不能把这个等级分解释成概率加权结果。阈值0.7是示例政策，需要在具体任务上校准。

## DeepEval DAG

[官方说明](https://deepeval.com/docs/metrics-dag) · [dag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py)

图先检查节点关系和必需字段，再执行根节点。本课用一个 `BinaryJudgementNode`：真分支指向10分叶子，假分支指向0分叶子，最后归一化。

确定的是路径到分值的映射；模型节点的判断仍可能变化。`include_reason=False` 省略额外总结，节点裁决仍可保留用于解释。

## Ragas AspectCritic

[官方说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/) · [_aspect_critic.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/_aspect_critic.py)

```text
single_turn_ascore
  → AspectCriticInput(user_input, response)
  → prompt.generate
  → AspectCriticOutput(reason, verdict)
  → _compute_score
```

`definition` 进入提示，结果是0或1。固定版本此路径把一次生成结果交给聚合函数，不能仅凭 `strictness` 属性推断执行了多次独立投票。

## 适配器只连接接口

`DeepJudge` 与 `RagasJudge` 负责模型传输及对象转换，评分 prompt 和聚合由原生 SDK 负责。后续 collections 指标要求另一套现代 Ragas 接口，要按所用类的签名接入。

保存原始理由有助于排查“标准不清”和“裁判误解”。错误、有效零分和未定义结果分别记录；已看过的样本用于修订标准后，还需要留出样本验证。
