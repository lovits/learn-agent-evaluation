# e16: 综合项目与持续回归：修过的问题，怎样留下来？

[e15](../e15_version_comparison/README.zh.md) → `e16`

> *“修好一个问题只算完成了一半；把任务、独立观察和硬门禁留进回归集，下一次改动才不会把旧账带回来。”*
>
> **评测层：持续回归。** 把 Agent 循环、TinyRAG 检索、独立产物检查和 DeepEval 语义指标接进同一套门禁，按分项关键条件决定接受、拒绝或阻塞。

## 问题

第 12 课的账单任务要求修复 `billing.py` 里的 `total_cents(items)` 并向用户说明修复了什么。Agent 把函数逻辑改对了，独立测试也全部通过，最后却只回复了一句“已完成。”。只靠代码契约检查，会直接放过这类文字交付缺口。

为了补上说明要求，我们把候选版本的提示词收紧，明确要求在最终回复里交代计算规则、空订单处理和输入不变性。改动上线前，至少要确认三件事：原来的说明缺口补上了没有、空订单边界有没有写坏、原本已经正确的代码会不会被顺手改错。要让每次修改都在同一批任务和同一套判据下接受复验，就需要把这些组合能力沉淀成持续回归流程。

## 解决方案

执行层继续复用前面的最小架构：通过第 5 课的 `run_task` 和第 2 课的 `agent_loop`，把具名文件工具、Bash 和基于 TinyRAG 的 `search_knowledge` 接进同一个循环，每次都在全新的隔离工作区里从头运行，完整记录 `messages`、`retrievals`、`model_inputs` 和 `responses`。

![一个 Agent 循环连接模型、具名工具、只读知识库与交付文件](https://lovits.github.io/learn-agent-evaluation/diagrams/e16-integrated-agent-flow.svg?v=6bd1187ddf0b)

循环退出后，由 [eval.py](eval.py) 脱离模型上下文独立取证：先重新加载工作区代码校验计算行为和保护文件哈希，再用 DeepEval 的 `GEval` 与 `ContextualRecallMetric` 分别评判交付说明和检索覆盖。门禁逻辑逐题逐项核对关键条件，只要发现候选版本有明确失败就拒绝，有运行或评分缺失就先阻塞，未复核的新失败统一送入待审队列。

![补充任务，比较版本，按关键条件接受、拒绝或保留未决](https://lovits.github.io/learn-agent-evaluation/diagrams/e16-regression-gate-flow.svg?v=1c47918ea1cc)

## 工作原理

### 串联 Agent 循环与知识库

打开 [code.py](code.py)，`run_case` 准备独立工作目录并在候选版本提示里追加 `REPAIR` 约束，随后直接调用第 5 课的 `run_task` 驱动原有循环：

```text
任务 → 模型 → 工具调用？
              有：执行文件 / Bash / search_knowledge → 结果回写 messages → 模型
              无：退出循环，留下最终回答与磁盘产物
```

知识库目录按只读方式挂载，底层复用 TinyRAG 原生 `VectorStore` 与本地 TF-IDF 词面检索基线，查询参数固定为 `k=3`、`context_limit=3`。`main` 在启动评测前先比对每道任务绑定的 `source.sha256` 与当前知识库文档哈希，防止参考依据过期后继续误判。

工具执行沿用第 2 课的工作区路径检查和基础命令拦截。每次模型调用的真实可见输入、模型响应以及参考答案都分开存放，评分参考绝不进入被测模型的提示词。

### 从历史失败派生回归任务

[failure_origin.json](failure_origin.json) 存档了第 12 课那条“程序契约通过但说明缺失”的反例：独立检查 `DeliveryContract` 给了 `1.0`，而 `TaskCompletionMetric` 给出 `0.95` 并判为未通过（原因就是最终回复只有“已完成。”）。其中动作轨迹和回复是当时为演示准备的受控输入，文件执行与原生裁判判断都是真实发生的。

基于这个教训，[cases.jsonl](cases.jsonl) 派生出三道属于 `Atlas_billing` 题族的公开回归任务，每道题都要求先查规范、读源码，再决定是否改写代码：

| 题号 | 初始缺陷 | 回归保护重点 |
|---|---|---|
| `quantity` | 漏乘 `quantity` | 验证核心计费公式修复与说明补充 |
| `empty` | 空订单错误返回 `100` | 防止修复一处边界时漏掉另一处边界 |
| `preserve` | 实现原本正确 | 防止模型画蛇添足改坏已有正确代码 |

运行中一旦出现未通过项（`accepted is not True`），[failure_candidates](eval.py) 会自动将其归入 `failure_candidates` 并标为 `needs_review`，连同诊断标签 `diagnosis`、原始回答和 JSON 格式的独立观察一起留下。团队先人工核对是 Agent 失误、参考过期、裁判误判还是接口异常，确认后再把稳定可复现的任务补进 `cases.jsonl`。

### 规则判产物，DeepEval 判语义与覆盖

运行结束后，[evaluate_run](eval.py) 先调用第 12 课的 `inspect_delivery` 和 `DeliveryContract` 检查客观结果：

```python
evidence = inspect_delivery(workspace, case["files"]["policy.txt"])
contract = score(DeliveryContract(), evidence_sample(run, evidence))
```

`inspect_delivery` 在隔离的 `python -I` 子进程里导入 `billing.py`，实测空订单、多商品订单、零数量以及输入列表/字典不被修改四项行为，同时核对 `policy.txt` 的 SHA-256 哈希。中途即使某条 Bash 测试报错，只要 Agent 观察到错误并修正到最终通过，独立检查依然认可最终交付。

随后，`evaluate_run` 把其余维度拆给各自独立的检查项：

| 证据来源 | 检查内容 |
|---|---|
| 运行与工具轨迹（`checks`） | 循环正常 `finished`、实际送入过知识片段、成功调用 `read_file` 读取 `billing.py`、参考来源未过期 |
| 独立行为与哈希（`DeliveryContract`） | 函数计算结果、输入保持不变以及 `policy.txt` 未被篡改 |
| 显式 `GEval`（`completion_metric`） | 对照任务、原始回答、独立观察与 `tool_events`，以 0/1 二元量表核对计算、流程与中文说明 |
| `ContextualRecallMetric`（`judge_recall`） | 核对参考规范里的各条事实是否被实际检索上下文覆盖 |

这里特意把第 12 课的 `TaskCompletionMetric` 换成了显式 `GEval` 量表 `completion_metric`。第 12 课的兼容路径会先让模型抽取一段 `outcome` 摘要再判分，摘要过程容易漏掉实际调用过的 `search_knowledge` 或 `read_file`，或者擅自扣掉任务根本没要求的仓库级测试分；把原始回答、独立观察和 `tool_events` 一起交给 `GEval` 并使用明确步骤与 0/1 `Rubric`，就能让两个版本在完全一致的证据视野下接受评判。`judge_recall` 复用第 7 课封装，额外记录 `threshold=1.0` 和 `accepted`，同时保留 SDK 原生的 `passed` 字段。

### 分项硬门禁拦截退化与缺口

拿到逐题评分后，[gate](eval.py) 先检查每道题的两个版本是否都拿到了有效结论：

```python
if any(k not in lookup or lookup[k] is None for k in expected):
    return {"decision": "blocked", ...}
```

只要任意一行因为模型报错（`model_error`）或评分接口异常导致 `accepted` 为 `None`，门禁就直接返回 `blocked`，先排查可用性与取证链路。所有题目都拿到有效结果后，门禁再按硬条件收口：

- 任意一道题的候选版本失败（例如改坏 `policy.txt` 或漏掉说明），返回 `reject`，不允许靠另外两题的满分去平均抵消。
- 候选版本全部通过且至少修好了基线原本失败的一道题，返回 `accept_in_scope`。
- 基线和候选版本原本就全部通过，返回 `no_regression_observed`，只说明当前题集没有退化。

本课三道题都属于公开的 `Atlas_billing` 题族，主要用于守住已知回归边界；要把某次改动推广到更广场景或上线发布，还需要补充独立留出题族与多轮复测。

### 最小修复只改一句提示

为了隔离变量，[code.py](code.py) 只在候选版本的首轮任务文本后追加固定指令 `REPAIR`，其余循环、工具、TinyRAG 参数与评分量表完全保持不变：

```text
最终回复须具体说明计算规则如何修复、空订单与输入保持的处理；
准确区分实际检查与未检查，不要只回复已完成。
```

默认离线运行会真正执行文件工具与 TinyRAG 检索，同时配合预设动作和构造的 `fixture_completion` 来验证整条接线与门禁分支；传入 `--live --judge` 才会驱动真实模型并调用 DeepEval 原生裁判。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `run_case` | [code.py](code.py) | 创建隔离工作区，按版本追加 `REPAIR` 指令并调用第 5 课 `run_task` |
| `completion_metric` | [eval.py](eval.py) | 定义 DeepEval `GEval` 显式 0/1 量表，联合审查回答、独立观察与工具事件 |
| `evaluate_run` | [eval.py](eval.py) | 串联运行检查、`DeliveryContract`、`completion_metric` 与 `judge_recall` 并归因 `diagnosis` |
| `gate` / `failure_candidates` | [eval.py](eval.py) | 按硬条件生成门禁结论，把未通过条目送入 `needs_review` 复核列表 |
| `main` | [code.py](code.py) | 校验知识文档哈希，执行离线门禁或 `--live --judge` 实测并落盘报告 |

## 试一下

运行离线门禁流程，观察工具执行、独立产物检查与门禁判断：

```sh
python -m course.e16_regression.code --gate
```

动手验证四个问题：

1. 把某个任务的 `billing.py` 改成固定返回错误金额，观察 `evaluate_run` 里的哪一层会率先拦截，以及 `diagnosis` 会给出什么标签。
2. 在保留 `billing.py` 正确实现的前提下改写 `policy.txt`，即使其余两题全部满分，`gate` 还能放行吗？
3. 将某条语义评分改设为 `None`（模拟裁判接口异常），对比 `gate` 返回 `blocked` 与 `reject` 的分支条件。
4. 加上 `--live --judge` 运行真实模型与原生裁判。如果两个版本在当前三道题上全部通过，结论应该怎样表述？

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

16 课到这里已经搭起一条从“定义成功”到“持续回归”的完整评测链。你可以在[完整项目导读](../../docs/integrated-project.md)里回顾全课模块如何衔接，并把这套方法搬到自己的 Agent 上：先用规则固定能直接验证的产物边界，再为语义要求建立校准过的裁判，最后把每一次复核过的线上故障留成回归用例。
