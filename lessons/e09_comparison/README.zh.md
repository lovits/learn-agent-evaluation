# 第9课：版本比较，先配对再看均值

## 问题

上一课把任务与来源保存成了候选。现在我们只改一个参数：把知识检索的 `limit` 从 1 调成 2。运行后，候选版本的平均成功率更高。能否据此宣布“新版本更好”？


假设基线在任务甲上失败、任务乙上成功，候选在两个任务上都成功。比较这两个均值前，先核对：两个版本做的是不是同一批任务，读的是不是同一份文档，用的是不是同一个模型入口、提示词和判分合同。换题、换资料或换判分规则，都可能产生与 `limit`无关的差异。

模型输出还有波动。一次成功或失败可能只是偶然，所以同一任务、同一版本要重复运行。不过，重复两次并不会把一个任务变成两个独立需求。先合并任务内部的重复结果，才能比较同一任务的两个版本。

总体均值也可能遮住关键退化。例如，新版本让三道常见题通过，却让一类关键组合题失败。此时均值上升，业务上仍未必能够采用。因此，本课还要按 `single_hop` 与 `multi_hop` 分层检查。

一边看结果一边改选择规则，容易选中碰巧适合开发题的版本。本课先用公开合成的 `upload` 族做开发，保存决定后，再用 `archive` 族做留出验证。两族都是公开课程数据，这只能演示分组验证流程，不能声称是生产盲测，更不能代表真实用户总体。

实验继续使用第4课的编程循环和工具；新增代码负责比较结果。

## 解决方案

我们固定六项条件：`query`、任务合同、知识文档、模型入口、提示词和判分方法。唯一变化是检索数量：

- 基线版本：`k=1`
- 候选版本：`k=2`

`upload` 与 `archive` 是两个不同任务族。当前合同中，上传上限是 1 MiB，即 `1048576` 字节；归档上限是 `131072` 字节。它们不能混用，也不能拿第6课的 2 MiB v2 合同替换。

每族各有两类任务：单跳题只问限额；组合题还要同时找出认证字段和超限状态码。每个任务、每个版本真实运行两次，执行顺序交替为 `1→2`、`2→1`，避免某个版本永远先运行。

开发阶段使用预先声明的选择规则：候选相对基线的任务成功率差至少为 `0.1`，并且已经观察到的每个分层都不退化，才选择 `k=2`；否则保留 `k=1`。决定保存后才能运行留出族，留出结果不反过来参与选择。

完整入口见[运行代码](code.py)、[配对统计](statistics.py)和[分析与独立验收](eval.py)。API差异、长调用链和固定源码说明见[源码导读](source_walkthrough.md)。

## 工作原理

**第1步：用manifest冻结真正参与比较的条件**

如果只记录“比较了 `k=1` 和 `k=2`”，以后就无法判断代码、任务或文档是否已经变化。`manifest`因此保存实际代码哈希、知识库哈希、候选值和重复次数：

```python
return {
    "code_sha256": {p: sha(project / p) for p in sources},
    "documents": {p: document(p)["sha256"] for c in cases for p in c["knowledge_paths"]},
    "only_changed_factor": "retrieval_limit_k",
    "k_values": [1, 2],
    "repeats": REPEATS,
    "minimum_effect": 0.1,
    "model_sampling_seed": None,
}
```

片段来自 `code.py`，局部省略，不能独立运行。任务文件中的 `expected`供运行后的检查器使用；模型输入只接收任务文本，驱动器不把参考值注入提示。未设置抽样种子也被如实记录，所以重跑时仍可能得到不同结果。

**第2步：只替换检索数量，证据仍由真实搜索产生**

受控分发器只截获 `search_knowledge`。它检查Agent是否使用固定 `query`，再从当前任务的文档副本中真实检索；其他工具仍交给已经学过的 `dispatch`：

```python
if call.get("name") != "search_knowledge":
    return dispatch(call, workspace, approve)
try:
    if json.loads(call["arguments_json"]) != {"query": case["query"]}:
        raise ValueError("The query is fixed in this controlled experiment")
    hits = [{**d, "id": d["path"]} for d in search(case["query"], limit=k, root=corpus)]
    retrievals.append({"query": case["query"], "k": k, "hits": hits})
```

片段来自 `code.py`，局部省略。两个版本使用同一任务、同一文档副本，只让 `limit=k`变化。答案由Agent依据本次返回的文档写出，检索记录保留了它实际看见的证据。

**第3步：真实运行Agent，再检查真实文件**

`execute_trial`复用 `agent_loop`。Agent必须写出 `answer.json`；随后 `inspect`重新读取文件，检查键、类型、参考值以及 `sources`是否确实来自本次检索：

```python
result = agent_loop(
    case["task"],
    workspace,
    model=counted_model,
    tool_dispatch=limited_dispatch(case, k, corpus, retrievals),
)
elapsed = time.monotonic() - start
returned = {d["id"] for r in retrievals for d in r["hits"]}
artifact = inspect(workspace, case, returned)
```

片段来自 `code.py`，局部省略。最终的 `passed`同时要求产物检查通过和循环状态为 `finished`。独立验收器之后会再次读取文件，核对内容是否和Agent的完成回执相符。

每条任务由原生Ragas的 `@experiment` 与 `arun`驱动；若一行结果被遗漏，程序立即报错，避免异常行消失后悄悄缩小分母。原生DeepEval的 `LLMTestCase`只用作样本载体，`metadata`保存版本信息；本课没有调用 `deepeval.evaluate`，也没有把规则分冒充成SDK语义指标。字段适配的预运行问题与正式重跑记录见[真实运行摘要](run_summary.md)。

**第4步：先合并重复，再计算同任务差值**

配对统计先按 `(case_id, k)`收集运行，再确认两个版本拥有相同的重复编号。缺失或重复记录都拒绝分析：

```python
left, right = grouped[identifier, 1], grouped[identifier, 2]
if not left or not right or {r["repeat"] for r in left} != {r["repeat"] for r in right}:
    raise ValueError("Missing matched case/version/repeat")
if len({r["repeat"] for r in left}) != len(left) or len(
    {r["repeat"] for r in right}
) != len(right):
    raise ValueError("Duplicate case/version/repeat")
```

片段来自 `statistics.py`，局部省略。假设同一任务的基线两次结果是 `0、1`，候选是 `1、1`。基线任务成功率为 `0.5`，候选为 `1`，所以配对差为：

`1 - 0.5 = 0.5`

这四次执行共享同一个任务，只描述它在重复运行时的波动。随后程序再按 `single_hop`与 `multi_hop`分别汇总；选择规则要求总体差至少为 `0.1`且各层不退化，不能看到结果后临时修改合同。

**第5步：冻结开发决定，再打开留出任务**

开发报告写完后，决定会连同manifest和开发报告哈希一起保存。运行留出阶段时先重新计算manifest；只要代码、数据或协议发生变化，就拒绝沿用旧决定：

```python
if args.phase == "holdout":
    decision = json.loads(decision_path.read_text())
    if decision["manifest"] != frozen:
        raise ValueError(
            "Code, data or protocol changed after selection; start a new experiment"
        )
```

片段来自 `code.py`，局部省略。原生Ragas的 `arun`按完成顺序收集结果，因此不能把两个结果列表直接 `zip`起来；必须用 `case_id`、`k`和 `repeat`配对。本课每次只让原生调用处理一行，使实验顺序可核对；每完成一项还写入 `partial`。它只用于中断保护，不能冒充完整实验。

正式结果显示：开发与留出的单跳差都为 `0`，组合题差都为 `1`。单跳题在第一份命中文档中已经能找到限额；组合题的 `k=1`缺少认证文档，实际产物中的 `auth_header`为 `null`，而 `k=2`取得第二份证据后字段才完整。开发任务平均差为 `0.5`，按预定规则先选择 `k=2`；随后留出的任务平均差也为 `0.5`。逐题记录和限制见[真实运行摘要](run_summary.md)。

**第6步：按任务族重采样，并把质量与代价分开报告**

同族任务共享文档和失败原因，同族题的结果可能一起变化。`family_bootstrap`先求每个任务族的平均差，再有放回抽取任务族：

```python
rng = random.Random(seed)
draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(resamples))
return {
    "low": draws[int(0.025 * (resamples - 1))],
    "high": draws[int(0.975 * (resamples - 1))],
    # 其余元数据见完整函数。
}
```

片段来自 `statistics.py`，局部省略。这是标准库实现的percentile区间，没有调用SciPy，也不是BCa。单个split只有一个任务族，所以区间为空；合并后也仅有两个公开合成族，不能据此证明总体改进。抽样2000次能让数值模拟更稳定，样本量仍是原来的两个族。两个族的平均差恰好相同，本次区间缩成[0.5,0.5]；它反映的是现有数据的重复，无法证明未知任务没有波动。

本次固定输出还可由同一裁判重复判断两次，但那与Agent重复执行不同：前者观察判分波动，后者观察回答波动。重复裁判结果不是人工标签，也不进入版本选择。

应用事件保存了真实usage，分析器按原字段汇总输入、输出和缓存输入，具体数值见[运行摘要](run_summary.md)。缓存输入不能再次简单加到输入总数。`token_count`为空表示runner没有预先聚合，型号和单价不明确时费用保持空。质量、墙钟延迟、请求数和token分别观察；本次平均延迟的小幅差异还受模型波动与宿主机负载影响。应用、裁判和教材调用分别记账。

## 相对上一课的变更

上一课保存任务和来源，本课用冻结的任务合同运行两个版本：

| 项目 | 上一课 | 本课 |
|---|---|---|
| 目标 | 保存候选 | 比较 `k=1` 与 `k=2` |
| 任务组织 | 候选任务及来源 | 同任务、同合同、两个版本 |
| 运行方式 | 保存待审核材料 | 每任务每版本真实运行2次 |
| 统计单位 | 候选记录 | 先合并重复，再按任务配对 |
| 风险检查 | 来源是否可追溯 | 分层是否退化 |
| 验证 | 审核候选 | 开发选择后冻结，再跑留出 |
| Agent能力 | 已有循环与工具 | 不变 |

这些比较代码包在原有循环外面，读者可以沿用前面的工具和权限实现。

## 试一下

先在宿主机终端启动模型桥，并保持运行：

```bash
python3 tools/model_bridge.py
```

它监听8766端口。只有准备执行可选的重复裁判时，才在另一个终端启动8768端口：

```bash
python3 tools/judge_bridge.py
```

构建镜像，然后先运行开发阶段：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e09_comparison.code --phase development
```

开发完成并保存决定后，再运行留出阶段：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e09_comparison.code --phase holdout
```

不要修改manifest覆盖的代码、任务或文档后继续使用旧决定。若条件改变，应保存旧报告并重新开始开发实验。

可选的重复裁判命令是：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e09_comparison.eval --repeat-judge
```

断网独立验收使用：

```bash
docker compose --profile verify run --rm -T \
  --entrypoint python verifier -m lessons.e09_comparison.eval
```

报告和决定都写入 `runs/e09-*`。同名重跑会覆盖文件，比较前应另存旧结果；`partial`只是已完成项的检查点，不代表整轮成功。阅读页面可运行 `docker compose up -d`，再访问 `http://localhost:8765/lesson9`。

请在记录中回答三个观察题：

1. `k`增加后，哪个分层发生改变？真实检索证据为什么会造成这个差异？
2. 同一任务的重复运行怎样合并？为什么单个split的区间为空？
3. 原始usage与墙钟代价是否同向变化？现有数据允许下什么结论？

更多练习见[练习](exercises.md)，参考答案见[答案](solutions.md)。完整结果计数见[真实运行摘要](run_summary.md)，长调用链见[源码导读](source_walkthrough.md)，验收证据见[验证记录](../../docs/e09-validation.md)，生成与审校说明见[生成记录](../../generation/e09-README.md)。

## 接下来

这次比较把 `k`的变化关联到了真实缺失的认证字段。逐题记录还能用于下一次回归，检查同一种失败是否重新出现。

第10课接入MCP，并沿工具选择、参数和调用顺序继续评测：文件最终正确时，过程中仍可能漏调、误调或重复调用。
