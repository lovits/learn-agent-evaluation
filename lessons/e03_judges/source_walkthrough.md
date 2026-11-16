# 第3课源码导读

本课不扩展Agent。第2课的工具、权限、轨迹继续作为被测对象；新增代码全部在独立评分层。四个回答是围绕第2课输出48构造的受控变体，不冒充新一轮Agent实测。artifact_verified是实验夹具中的事实标签；正式使用时必须来自第2课独立验收器，不能采信Agent自报。

## 规则先确定比较单位

[code.py](code.py)中exact_match按原始字符串比较，JSON合同要求唯一result键、整数48（排除Python的bool），state_contract只读取独立状态。set_f1按工具名集合去重，precision=交集/实际集合，recall=交集/预期集合，F1为调和平均。双方空集合约定为1，只有一方空为0。集合评分忽略顺序、参数和重复次数，不能替代第2课轨迹合同。

## DeepEval GEval

固定提交34db63dd005ebc9a905c8ef4741ae0687c93c14c，版本4.3.4。

[官方说明](https://deepeval.com/docs/metrics-llm-evals)与[实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)可对照阅读：

1. _validate检查evaluation_params需要的输入。本课提供INPUT、ACTUAL_OUTPUT，既给问题和独立状态，也给回答。
2. _generate_evaluation_steps在已有evaluation_steps时直接复用。本课固定语义标准，避免每次先生成一份不同标准。
3. _results_prompt组装步骤和样本；_evaluate经generate_rubric_score请求结构化ReasonScore。自定义DeepEvalBaseLLM把结果恢复成schema对象。
4. measure将原始评分按score_range归一化，再以阈值0.7判定通过。本课自定义模型没有logprobs，不宣称用了原生模型的概率加权分数。实际prompt、响应、reason、score全部保存。

自定义模型的费用在SDK里可能为None，不能解释成免费。宿主机入口保留usage、耗时及实际返回的模型标识；未返回确切型号时保持null。

## DeepEval DAG

[官方说明](https://deepeval.com/docs/metrics-dag)与[DAGMetric实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py)说明了图检查、必需字段提取和根节点执行。

本课只建一个BinaryJudgementNode，True到10分叶子，False到0分叶子，最终归一化。映射由程序固定，节点的真假判断仍由模型给出。include_reason=False关闭额外总结调用，节点原始裁决和verbose_logs仍保存。同步measure与异步a_measure是两条入口；实验使用同步measure，四个样本各用独立metric实例并行运行，避免共享实例的score被覆盖。

## Ragas AspectCritic

固定提交8c63f10d500c44efbf24fdb9e2920de2104c321c，版本0.4.4。

[官方说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/)与[固定实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/_aspect_critic.py)中：definition进入提示词，AspectCriticInput承载user_input/response，AspectCriticOutput要求reason和verdict。single_turn_ascore走异步prompt生成，再由_compute_score聚合。

本课strictness=1，二元verdict为0或1，阈值1。该固定版本的_ascore只把一次生成的response传入_compute_score；即使构造器把偶数strictness调为奇数，也不能仅凭这个属性宣称已做多次独立投票。导入路径采用固定版本的legacy实现，迁移新版本时要重新核对接口。原始reason在calls响应里，不因最终结果仅返回标量而丢弃。

## 适配与错误处理

[eval.py](eval.py)里DeepJudge和RagasJudge只做模型接口转换，真正提示词和评分由原生SDK执行。宿主机judge_bridge只提供模型输出，工具被关闭；Docker内的裁判不能执行学生代码。本课评分不需要知识库、工作目录或私有凭据。

非JSON、缺字段、超时或SDK异常保存为score=null和error，进程非零退出；不把调用失败写成0分，也不把人工标签填回裁判输出。raw prompt/响应可用于核对输入污染和裁决差异。它们属于评测证据，不是人类标注真值。
