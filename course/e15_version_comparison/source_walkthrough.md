# 第15课源码导读：先对应同一题，再谈平均差值

## 本课调用链

```text
main → 验证全部参考来源哈希
     → repeat × case × version
       → run_version → 第5课 run_task → 第2课 agent_loop
         → 固定首步 search_knowledge → TinyRAG 原生 VectorStore
         → 模型续跑 / 构造回答 → 实际轨迹与上下文
       → DeepEval G-Eval / 明确的构造分 → 逐行保存
     → compare → 同题配对 → 题型与题族 → 重采样范围
```

[code.py](code.py) 每完成一行就保存同一 run_id 的记录。固定步骤、真实模型请求、构造回答分别标明；模型报错仍留下轨迹。两轮交错 AB、BA 只降低固定先后顺序的影响，不保证消除时间混杂。

[eval.py](eval.py) 的质量分与运行协议分开。语义判据重复使用同一份 evaluation_steps 和 rubric，阈值不随版本改动。参考覆盖多个文档时，不能只核对主文档哈希；本课先验证 sources 全部引用，再运行旧接口。

## DeepEval：一次评分属于哪个版本

[优化参数指南](https://deepeval.com/guides/guides-optimizing-hyperparameters) 将提示、模型、top-k 等视为可改变的应用参数，并要求生成结果能对应相应配置。本课只调上下文条数，保持检索候选数不变；本地循环承担配对统计，框架承担同一量表的语义评分。

固定源码版本：`34db63dd005ebc9a905c8ef4741ae0687c93c14c`。

- [EvaluationDataset](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py#L90) 分开保存 goldens 与执行后的 test_cases。固定任务并不代表已有该版本的实际输出。
- [TestResult 与 EvaluationResult](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/types.py#L11) 分别承载单条输入、输出、指标数据与整次 test_results。类名本身不会替你确定同题对应关系或统计显著性。
- 本课 G-Eval 沿第4、9课已读的 [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 执行。配置量表为0—2，归一化到0—1；自定义 JudgeModel 不支持 logprobs，使用结构化裁决分支。

没有调用 evaluate 的整批接口并不意味着重复实现另一框架。本课用同一个 DeepEval 指标逐条 measure，额外写的只是同题比较。

## Ragas：结果存下来了，顺序却未必相同

[Experimentation](https://docs.ragas.io/en/stable/concepts/experimentation/) 强调固定数据、明确指标、一次改变一个因素并保存元数据。飞书归档的同名章节也保留了这条原则。这里只吸收实验设计，实际不调用 Ragas 评分。

固定源码版本：`8c63f10d500c44efbf24fdb9e2920de2104c321c`。

[ExperimentWrapper.arun](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py) 为数据行调度任务，通过 asyncio.as_completed 收集完成项，非空结果加入实验；个别异常会记录后继续。完成顺序和缺失行都可能变化。

```text
版本A：题1、题2、题3
版本B：题3、题1；题2失败
```

按列表位置配对会比较错题。显式ID、完整的预期配对清单和覆盖率应由实验组织者保留。不要与另一个 [Executor](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/executor.py) 中按返回索引排序的路径混为一谈。

## 重采样的单位比调用次数更重要

[SciPy bootstrap 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) 解释 paired=True 会对多个数组使用同一组重采样索引；其默认方法为 BCa。本课先算同题差值，再以题族均值做标准库 percentile 演示，避免把同题重复当独立任务。没有声称实现完整统计推断或调用 SciPy。

只有三个构造题族、每族一题、每题两次，足以解释代码，无法可靠估计广泛任务分布；报告配对覆盖与原始失败，比给平均差值附上“稳定提升”的结论更有用。
