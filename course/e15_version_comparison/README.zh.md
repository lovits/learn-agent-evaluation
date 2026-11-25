# e15: 版本对比：改了参数，真的更好吗？

[e14](../e14_judge_calibration/README.zh.md) → `e15` → [e16](../e16_regression/README.zh.md)

> *“平均分变高，只说明这一批样本均值更高；改动是否可靠，要看同题配对差值、题族分布和资源消耗。”*
>
> **评测层：版本对比。** 固定题集与检索变量，按任务和重复编号配对计算差值，再结合题型退化、题族重采样与调用成本一起判断。

## 问题

假设我们把检索后送入模型的上下文上限 `context_limit` 从 `1` 提高到 `3`。对于需要跨文档拼接的题目（例如同时询问发布命令和 API 认证头），多看两条资料能让回答变完整；但在要求识别当前生效版本（`Shipping v3`）的题目上，多放进两条片段也可能把旧版本规则混进上下文。

如果只比较改动前后的总体平均分，很容易漏掉几个核心问题：两次测试用的是同一批题目和同一套裁判量表吗？哪些题型在变好，哪些题型反而退步了？新增上下文带来了多少额外的 token 与耗时开销？

## 解决方案

本课复用第 5 课的 Agent 与 TinyRAG 检索器，保持检索候选数 `k=3` 不变，只把 `context_limit` 作为唯一变量：`baseline` 取 `1` 条，`candidate` 取 `3` 条。每道题运行两次，并在第二次交换两个版本的执行顺序，完整保存每行轨迹、裁决与耗时。

![固定同题，只改变上下文条数，保留每次运行和裁决](https://lovits.github.io/learn-agent-evaluation/diagrams/e15-paired-run-flow.svg?v=91ed3bbe050e)

统计阶段严格按 `(case_id, repeat, version)` 配对后计算差值，先按任务、题型和题族分层查看退化，再以题族为单位做重采样区间估计，同时把模型请求数、token 用量与延迟单列记录。

![有效同题配对后看差值、覆盖率、题族波动和成本](https://lovits.github.io/learn-agent-evaluation/diagrams/e15-comparison-flow.svg?v=e175ff093ef8)

## 工作原理

### 一次只改变一个变量

[run_version](code.py) 直接调用第 5 课的 `run_task`，只切换 `context_limit`：

```python
run = run_task(
    case,
    prepare_workspace({"files": {}}, uuid.uuid4().hex),
    k=3,
    context_limit=1 if version == "baseline" else 3,
    root=root,
    model=next_response,
)
```

运行前，`main` 会校验每道题 `sources` 里全部参考文档的 SHA-256 哈希是否与当前知识库 `catalog()` 一致（有变化则抛出异常中止），同时把 `cases_sha256` 和 `changed_factor` 写入报告元数据。

为了把对比变量锁定在上下文条数上，第一步 `search_knowledge` 的查询词由实验固定（`decision_origins` 记为 `controlled_first_retrieval`），并交由 TinyRAG 实际执行检索；从第二步开始，默认模式返回预设的 `fixture_answers`，传入 `--live --judge` 时交由真实模型续跑并回答（记为 `live_model`）。同时，任务契约 `contract` 要求运行正常结束且只调用一次成功的 `search_knowledge`，即便模型多调了工具也会完整保留在 `events` 里，不会从记录中删掉。

### 按任务与重复编号配对

[compare](eval.py) 用三元组建立唯一索引，发现重复观测直接报错：

```python
key = (row["case_id"], row["repeat"], row["version"])
```

只有当同一道题、同一次重复的 `baseline` 与 `candidate` 都存在且 `quality` 不为 `None` 时，才计算配对差值：

```text
delta = candidate 的质量分 - baseline 的质量分
```

如果并发执行导致返回顺序颠倒，或者某一行评分报错，按列表位置 `zip` 就会把两道不同的题错位配对。通过键索引配对，缺失任意一侧的组合都会归入 `missing_pairs`，并与 `expected_pairs`、`valid_pairs` 和 `pair_coverage` 一起汇报。默认模式使用 `cases.jsonl` 自带的 `fixture_scores` 演示聚合算法；真实模型回答则必须加上 `--judge` 交由原生裁判统一打分。

### 统一量表与协议门禁

[quality_metric](eval.py) 使用同一个 DeepEval `GEval` 实例评估两个版本，将 `INPUT`、`ACTUAL_OUTPUT`、`EXPECTED_OUTPUT` 与 `RETRIEVAL_CONTEXT` 传入同一套 `Rubric`（`threshold=1.0`）：

| 原始分 | 判据 |
|---|---|
| `0` | 与当前规范矛盾、包含无依据断言、空回答或离题 |
| `1` | 有依据地覆盖部分要求，或明确说明上下文缺少证据 |
| `2` | 正确且有依据地回答全部要求 |

DeepEval 会把 `0` 至 `2` 的原始分归一化为 `0`、`0.5` 与 `1.0`。这一量表聚焦“任务事实覆盖度”，因此证据不足时的合理说明拿 `0.5` 归一化分，与第 9 课专门鼓励合理拒答的量表各自服务不同目标。

在 [code.py](code.py) 汇总有效质量分 `quality` 时，协议检查与评分异常分开处理：

```python
quality = (result["score"] if row["contract"] else 0) if result["status"] == "ok" else None
```

裁判正常返回时，若违反单次检索协议则将 `quality` 置为 `0`；若裁判接口调用报错（`status != "ok"`），`quality` 保留为 `None`，进入 `missing_pairs`，避免把接口异常折算成 `0` 分。

### 分层查看退化与题族重采样

同一道题重复跑两次，可以观察模型输出和顺序交错（第一轮 `baseline` 在前，第二轮 `candidate` 在前）带来的波动，同时不会增加独立题目的数量。如果把同一题重复 20 次并直接当成 20 道独立样本做置信区间，就会人为夸大统计确定性。

[compare](eval.py) 先对每道题的多次重复取均值（`case_deltas`），再分别按题族汇总 `family_deltas`（本课三个题族 `Atlas`、`Upload`、`Shipping` 等权）和按题型汇总 `stratum_deltas`（`cross_document` 与 `current_version`），同时列出所有 `delta < 0` 的 `regressions`。这样就能看清“跨文档题变好、当前版本题变差”这类被总平均分掩盖的矛盾表现。

随后，`compare` 以题族均值为单位执行 2000 次带放回重采样（固定种子 `random.Random(7)`）：

```python
draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(2000))
```

取第 50 个和第 1950 个有序统计量（`[draws[49], draws[1949]]`）作为近似 95% 百分位区间。当重采样区间跨过或触及 `0` 时，说明现有题族数量还不足以排除“没有改善”的可能；需要继续验证时，应当扩充独立题族，并留意缺失配对是否集中出现在特定难题上。

### 资源消耗与运行边界

[usage_summary](eval.py) 单独统计真实模型消耗：固定的第一步检索不计入 `model_calls`，裁判耗时与 `judge_calls` 也与 Agent 耗时 `agent_elapsed_seconds` 分开保存。只有当每次真实模型调用都返回完整 `usage` 时，才累加 `input_tokens` 与 `output_tokens`，缺失时保持 `None`。

记录 token 与费用时需要注意两点：提供方返回的 `cached_input_tokens` 通常已经包含在 `input_tokens` 总数内，不能二次相加；在没有确认输入、缓存与输出单价表之前，`usd` 和 `pricing_assumption` 保持 `None`，不能把未知单价当作零成本。此外，同一桥接接口未锁定底层模型快照，交叉执行顺序也只能缓解固定顺序偏差，对比结论始终要结合实际运行条件和成本一起审视。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `run_version` | [code.py](code.py) | 固定首步检索并切换 `context_limit`（1 与 3），记录回复来源、轨迹与耗时 |
| `quality_metric` | [eval.py](eval.py) | 定义基于 0 至 2 `Rubric` 的 `GEval` 语义质量指标，绑定参考与检索上下文 |
| `compare` | [eval.py](eval.py) | 按 `(case_id, repeat, version)` 配对计算差值、缺失覆盖率、题型分层与题族重采样区间 |
| `usage_summary` | [eval.py](eval.py) | 排除受控检索步骤，汇总真实模型请求次数与 token 用量，缺失时返回 `None` |
| `main` | [code.py](code.py) | 启动前校验全部参考文档哈希，交错执行两轮对照并落盘完整对比报告 |

## 试一下

运行默认模式，查看三题两次重复在 `fixture_scores` 下的配对差值、分层统计与重采样区间：

```sh
python -m course.e15_version_comparison.code
```

动手验证四个问题：

1. 按 `case_id` 和 `repeat` 手算每组 `delta`，找出默认样本里被总均值 `0.0` 掩盖的退化任务。
2. 把其中一条 `candidate` 的评分改成异常状态（`quality=None`），观察 `valid_pairs`、`missing_pairs` 与 `pair_coverage` 如何变化。
3. 加上 `--live --judge` 运行真实续跑与原生 `GEval` 裁判，区分 `controlled_first_retrieval` 与 `live_model` 的耗时和 `usage`。
4. 检查 `stratum_deltas`、`regressions` 与 token 开销，思考总均值提升时还需要满足哪些条件才能接受新版配置。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

掌握了同题配对比较和分层看退化的方法，最后一课 `e16` 把整套课程的能力串进闭环：从单条真实失败案例派生回归测试集，用多维门禁检验修复是否生效，并防止改好一个问题又把原本正常的用例改坏。
