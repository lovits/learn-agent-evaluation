# 第16课源码导读：从执行证据追到分数

本课继续使用 [固定版本](../../references/versions.json)，没有因官网示例更新而自动升级依赖。DeepEval 为 `34db63dd005ebc9a905c8ef4741ae0687c93c14c`，Ragas 为 `8c63f10d500c44efbf24fdb9e2920de2104c321c`。以下指出本课真正调用的入口；批量评价入口另外解释，避免把源码阅读写成执行记录。

## 1. 先找到实际对象

`Runtime.submit → _goal_loop → 原生 agent_loop → RecordedMessages.create` 形成一次主轮。模型响应由本机桥转换成原生 Message；具名工具由 `PreToolUse → call_tool_handler → PostToolUse` 执行，工具结果与对应调用 ID 一起回到消息。Goal 裁判读同一会话的证据，但最终文件与状态由另一个容器验收。

原生 trace 通过 [traces.py](../../integrated_agent/traces.py) 保存。固定版本结束 trace 后会在非评价模式下清除已完成对象；课程在结束边界记录 `create_trace_api(...).model_dump`，再恢复原方法。它是依赖固定版本内部接口的适配，升级时必须重测。

trace 的 `SUCCESS` 表示被观测函数正常返回。例如文件工具返回 `Error: ...` 字符串，函数本身没有抛异常，也可能得到 `SUCCESS`。文件是否存在、任务是否完成，应读返回内容并执行相应验收。

本轮还有一条观测失败记录：把整个 Runtime 当成被装饰函数的普通参数，框架序列化其公开对象图，进程在首个模型请求前以137结束。已移除讲师编排函数上的装饰，仅观测原生执行边界。原容器自动移除，未取得 OOMKilled 元数据，因此不能把137单独写成“已证明内存溢出”。原始协议、源码快照和终止记录都保留。

## 2. trace 转成样本时保留什么

[trace_samples](code.py)先找首个真正完成的工作响应，以 `response.id` 连接原生 LLM span，再定位唯一 trace。工具 span 按原生时间排序；采样保留工具名、实际参数、返回值、源 UUID 和内容哈希。它没有按模型的完成总结倒推一条理想轨迹。

首次投影只留下工具输出，测试 `OK` 仍在，产生它的命令却不在。裁判因此无法核实“运行的是哪条命令”。修订版把实际参数一起加入证据；原 Agent、业务文件和运行记录保持原样，投影与新评分另外冻结。这是查看首轮结果后的开发诊断，不能称作独立留出集上的提升。

两份 Faithfulness 样本共用同一个真实回答：第一份只给实际 docs 检索输出；第二份给修复轮的工具观测。后者含测试和编辑记录，证据范围更宽，不能把分数差异归成检索器质量变化。规范中的“必须保持原测试”也不等于“本次已经保持”。

工具样本只投影两个实现文件的 `read_file` 调用。参考为先读 shipping、后读 checkout 的声明序列；实际参数不做悄悄归一化。删除 checkout 读取的版本是讲师构造的退化投影，新增 Agent 请求为0。全任务可以有其他合理工具路径，这个分数只诊断指定投影。

## 3. DeepEval Faithfulness 的完整链

固定源码：[faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)、[QAG 聚合与 schema 适配](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py)、[输入校验](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/test_case.py)。

本课复用第5课 `evaluate`：构造 `LLMTestCase(input, actual_output, retrieval_context)`，调用原生 `FaithfulnessMetric.measure`，明确使用课程自定义裁判。`prepare_measure` 校验该指标所需字段，并重置状态与成本；对象能构造成功，不代表它具备某个指标的全部输入。

同步 llm 路径先从证据生成 truths，再从回答生成 claims，最后按 truths 判断每条 claim。每一步用模板形成 prompt，交给 `DeepJudge.generate(prompt, schema)`；桥的原始文字通过 `schema.model_validate_json` 变成结构化对象。verdict 仍是裁判的判断，schema 只保证结果形状。异步 `a_measure` 并行提取 truths 与 claims，再生成 verdict 并聚合；共享可变 metric 实例不应同时测不同样本。

默认通过集合为 `YES` 与 `BORDERLINE`，开启 `penalize_ambiguous_claims` 后只通过 `YES`。对同一组 verdict 重算：

```text
默认分数 = (YES 数 + BORDERLINE 数) / 有效 verdict 数
惩罚含糊项 = YES 数 / 有效 verdict 数
```

没有有效 verdict 时，固定 QAG 默认返回1；严格模式另按阈值钳制低分。因此需要保存声明数、verdict 和异常，不能把空声明高分解释为高质量答案。本课 `include_reason=False` 省去整体验因请求，仍保存逐声明理由与 verdict。

官方 [Faithfulness 文档](https://deepeval.com/docs/metrics-faithfulness)说明用途；判分细节与空输入边界以固定源码及本课记录为准。

## 4. Ragas Faithfulness 的完整链

固定源码：[collections/faithfulness/metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)、[prompt 与输出模型](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/util.py)。

本课使用 `metrics.collections.Faithfulness.ascore(user_input, response, retrieved_contexts)`。入口拒绝缺失的回答、问题和上下文。`_create_statements` 将问题、回答送入 `StatementGeneratorPrompt`，按 `StatementGeneratorOutput` 取得原子声明；`_create_verdicts` 将上下文与声明送入 NLI prompt，按 `NLIStatementOutput` 取得每项0/1。最后返回 `MetricResult.value`：

```text
score = 明确获支持的 statement 数 / statement 总数
```

无声明或空 verdict 集合可返回 NaN。本课将其记录为 `undefined_nan`、`score=None`；网络和解析错误另记 `error`。`CapturingJudge` 保存 schema 名及实际结构化结果，能查到每条分数从哪里来。

与 DeepEval 的默认值不同，Ragas 没有把“含糊但未被反驳”统一计为支持。首次实测还把一句报告拆成了不同数量的声明。即使使用同一个后端，prompt、拆句和聚合不同，也不会天然得到相同分数。官方定义见 [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)。

## 5. 工具指标为什么给出不同分数

本课复用第10课 [score_rules](../e10_tool_evaluation/metrics.py)，实际调用两个框架的原生实现，裁判请求为0。

DeepEval 的 `LLMTestCase.tools_called/expected_tools` 持有 `ToolCall`。只给预期工具时，`ToolCorrectnessMetric` 可做确定性比较；课程分别检查工具名、参数、顺序和 exact match。按两个预期调用计算，少一个可得到0.5，exact match则为0。若改为 `available_tools` 语义判断模式，算法与是否请求裁判都会变化，不能沿用这组规则结论。

Ragas collections `ToolCallAccuracy` 从 `AIMessage.tool_calls` 取预测，与独立提供的 `reference_tool_calls` 比较。先判断工具名序列是否对齐，再比较配对参数；额外或缺失调用可让序列因子为0。flexible 允许换序，仍要求名字多重集对齐。`ToolCallF1` 另按集合匹配计算 precision/recall，因此少一个时可得到约0.6667；重复去重也是它的边界。

固定源码：[DeepEval ToolCorrectness](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py)、[Ragas ToolCallAccuracy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py)。

## 6. 批量评价入口与 CI 的职责

DeepEval [evaluate.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)先校验测试与指标配置，再按 async/cache/error/display 配置执行，整理逐测试 `EvaluationResult`。本课为保存每一阶段的原始响应，直接调用 metric；没有把阅读批量入口当成它已被本课运行。

Ragas 固定版本 [evaluation.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/evaluation.py)的旧批量 `evaluate` 包装 `aevaluate`，与本课 collections `ascore` 接口分开。官方 [CI 指南](https://docs.ragas.io/en/stable/howtos/applications/add_to_ci/)给回归思路，旧示例参数不能直接拼接到当前签名。DeepEval 的 [CI 指南](https://deepeval.com/guides/guides-regression-testing-in-cicd)同样需要按本课固定环境执行。

CI 运行断网的可重复合同测试，检查已保存 bad case 与门禁；真实 Agent 和裁判实验通过独立命令运行并留证。没有设定自动夜间任务，避免把课程里的发布策略解释成已部署的调度服务。

## 7. 外部验收与恢复

[state.py](../../integrated_agent/state.py)读取实际 Task、记忆索引、cron 文件、workflow 快照与 journal，核对已释放 worktree 和保留分支；[verify.py](../../integrated_agent/verify.py)另在受限副本里验证业务。模型调用数、测试数或 workflow completed 均不替代这两层。

workflow 中，`ExecutionState.agent` 先检查请求额度和预算，再用语义键查缓存；缓存结果也要通过 schema 校验。新响应不符合 schema 时只重试一次，两次实际用量合计。`parallel` 等所有已启动分支结束才抛错误，让已成功分支写完 journal。已有的真实跨进程恢复复用了两个成功检查，仅新增一次验证；日志损坏时保留原文件并报错。

门禁用 `critical_gate` 对每个关键条件做 `is True` 判断。一个权限失败或未评分项会阻止接受，不能与其他高分平均。完整17项机制与各自真实/夹具证据边界见 [能力说明](../../integrated_agent/capabilities.md)。
