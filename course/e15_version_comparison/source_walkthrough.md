# e15 源码导读：先配对同题，再聚合差值

[教材](README.zh.md) · [对比入口](code.py) · [配对与重采样](eval.py)

## 本课调用链

```text
main → 校验全部参考文档 SHA-256
     → repeat(2) × case(3) × version(baseline, candidate)
       → run_version → 第 5 课 run_task → 第 2 课 agent_loop
         → 固定首步 search_knowledge → TinyRAG 原生检索
         → 模型续跑或构造回答 → 保存轨迹、上下文与 Agent 耗时
       → DeepEval GEval 或构造分 → 计算 quality 与裁判耗时 → 逐行保存
     → compare → 同题配对 → 题型与题族均值 → 2000 次题族重采样
```

运行开始前，[code.py](code.py) 中的 `main` 先对照知识库 `catalog()` 检查每道题 `sources` 列表里全部文档的 SHA-256 哈希，确保多文档参考依赖均未漂移。随后按 `repeat`（0 与 1）循环，在第一轮按 `["baseline", "candidate"]` 执行，第二轮反过来按 `["candidate", "baseline"]` 执行，以降低固定先后顺序带来的系统偏差，每完成一行即刷新同一 `run_id` 的报告文件。

在 `run_version` 中，第一步查询由实验固定（`decision_origins` 记为 `controlled_first_retrieval`）并真正调用 TinyRAG 检索，第二步起由构造回答或真实模型续跑（`live_model`）。若模型在拿到资料后又发起了多余工具调用，轨迹仍按原样写入 `events`，`contract` 会记为 `False` 并将该行 `quality` 压为 `0`。

## 配对键、异常隔离与异步乱序

[eval.py](eval.py) 中的 `compare` 使用 `(row["case_id"], row["repeat"], row["version"])` 作为索引键：

1. 一旦发现同一键出现两次，立刻抛出 `ValueError("Duplicate paired observation")`。
2. 遍历预期题集与重复次数，只有当 `baseline` 与 `candidate` 两行同时存在且 `quality` 都不为 `None` 时才计算 `delta`。
3. 在并发或异步批量评分时，不同任务可能按完成先后返回，个别样本也可能因超时或解析失败而缺行。如果直接对两个结果列表按位置 `zip`，就会把第 1 题的 `baseline` 配给第 3 题的 `candidate`。显式按任务和重复编号索引，并输出 `missing_pairs`、`valid_pairs` 与 `pair_coverage`，才能保证配对不错位、异常不失真。

## DeepEval：把版本配置与同一量表对齐

参考 DeepEval 官方 [优化参数指南](https://deepeval.com/guides/guides-optimizing-hyperparameters)：调整提示、模型或检索 `top-k` 时，需要把每次生成的实际配置与输出准确关联起来。本课固定检索候选 `k=3`，把变更收敛在 `context_limit` 上，外层负责同题循环与配对，DeepEval 负责在统一量表上打分。

以下源码对照基于 DeepEval 固定提交 `34db63dd005ebc9a905c8ef4741ae0687c93c14c`：

- [EvaluationDataset](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py#L90)：把待测题目 `goldens` 与执行后的 `test_cases` 分开保存。固定同一批题目只是对比的前提，每个版本仍需独立收集当次运行的 `LLMTestCase`。
- [TestResult 与 EvaluationResult](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/types.py#L11)：分别承载单条测试的指标结果与整批 `test_results`。数据结构本身不负责计算版本差值、配对覆盖率或统计区间，这些聚合逻辑由实验层 `compare` 显式承担。
- `GEval` 评分路径（[g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)）：本课 `quality_metric` 配置 `0` 至 `2` 的三档 `Rubric`，DeepEval 在非 strict 模式下归一化为 `0` 至 `1`；由于自定义 `JudgeModel` 不输出 `logprobs`，评分走结构化裁决分支。本课通过第 4 课的 `score` 包装函数逐条调用 `measure`，保证裁判异常能留下 `status="error"` 与原始 `reason` 而不中断整组配对。

## 题族重采样与统计学边界

参考 [SciPy bootstrap 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)：当两组数据按配对观测时，`paired=True` 会对两个数组使用同一组重采样索引，其默认区间估计方法为 BCa。

在 [eval.py](eval.py) 中，`compare` 先按 `case_id` 求多次重复的均值，再汇总出三个题族的均值，最后用标准库 `random.Random(7)` 做 2000 次百分位重采样（取排序后的 `draws[49]` 与 `draws[1949]`），保持了零外部科学计算依赖。因为先合并了同题重复再对题族重采样，同一题的多次运行不会虚增独立样本数。

这里只有三个构造题族，每族一题、每题两次，这个区间用来演示“按题族重采样”的代码结构；如果要得出可推广的统计学结论，仍需要扩充足够多独立题族，并在需要更精确区间时采用 BCa 等标准统计方法。

[样本与评测记录](assessment.md)
