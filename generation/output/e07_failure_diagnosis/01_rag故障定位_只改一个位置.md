# Chapter 1: RAG故障定位：只改一个位置

这一课解决一个具体问题：同样漏掉“最大上传字节数”，怎样判断是资料没有、检索漏掉，还是模型拿到资料后写错了。

## 问题

假设 Agent 的任务是阅读上传接口资料，并生成 `upload_notes.json`。正确结果应包含认证头、最大上传字节数和超限状态码。某次运行中，文件里的 `max_bytes` 却是 `null`。

只看最终文件，原因至少有三种：

- 资料源里根本没有限额说明。
- 限额说明存在，但检索结果没有返回它。
- 限额说明已经交给模型，模型却没有正确使用。

一个答案分数也区分不了这三种情况。低分只告诉我们“末端有问题”，没有告诉我们问题从哪里开始。若没有阶段证据，很容易一看到错误就修改提示词；但真正缺的是文档时，改提示词并不能补回事实。

本课固定使用第4课挂载资料中的合成上传合同 v1：

- 认证头：`X-Project-Token`
- 最大上传大小：`1048576` 字节，也就是 1 MiB
- 超限状态码：`413`

第6课使用的 v2 合同是另一个受控版本，其中限额为 2 MiB。这里不能拿 v2 判断 v1 文档是否正确。我们保留的是“参考答案必须带版本”的方法，并不是说两课使用了完全相同的参考文本。

## 解决方案

做故障定位时，先固定任务、查询词和参考版本，然后每次只改变一个位置：

| 实验组 | 唯一干预位置 | 改动 |
|---|---|---|
| `baseline` | 无 | 保留正常流程 |
| `drop_doc` | 文档 | 从临时资料副本移除限额文档 |
| `drop_hit` | 检索 | 文档仍在，但从返回命中移除 |
| `add_old` | 检索 | 追加明确过期的旧规范 |
| `add_noise` | 检索 | 追加无关的办公室说明 |
| `bad_prompt` | 生成 | 只给生成模型加入错误的旧限额指令 |

这像检查一条供水管道：先看水源有没有水，再看管道是否送到，最后看出水口是否正确使用。每轮只动一个接点，阶段之间的差异才有解释价值。

`cases.jsonl` 中的 `expected_observation` 是作者事先写下的人工预期，不是实测结论。实际发生了什么，只能查看保存的运行记录和 [实测记录](run_summary.md)。本轮是教材重写，没有重新运行 Agent 或裁判；已有数值都是保留下来的历史记录，不能称为本轮新测量。

完整实现见 [code.py](code.py)，评分实现见 [eval.py](eval.py)。下面只摘取与数据流有关的短片段，并省略日志、异常处理和外围组装代码；这些片段不是可独立运行的入口。

## 工作原理

**第1步：固定任务、查询和业务合同**

要比较不同故障位置，首先不能让任务本身变化。本课固定三个正确字段和一条查询词：

```python
QUERY = "POST upload API token size limit"
EXPECTED = {
    "auth_header": "X-Project-Token",
    "max_bytes": 1048576,
    "over_limit_status": 413,
}
REQUIRED = {"e04/auth.md", "e04/limits.md"}
```

输入是 synthetic v1 的两份资料，输出目标是 `upload_notes.json`。任务要求模型先用完全相同的 `QUERY` 检索，只写四个键：三个业务字段和 `sources`。证据缺失时必须写 JSON 的 `null`，不能猜。

这里没有增加新工具。读者已经学过文件工具和 `search_knowledge`，本课只在已有流程中记录故障发生的位置。固定查询也很重要：如果一组实验偷偷换了查询词，我们就无法判断差异来自检索干预，还是来自查询改写。

**第2步：在临时资料副本中制造文档缺口**

`drop_doc` 模拟“资料里就没有”。代码先根据实验组生成可用资料列表：

```python
available = [
    d for d in documents
    if case["id"] != "drop_doc"
    or d["id"] != "e04/limits.md"
]
retrievals = []
```

输入是原始的 `documents`，输出是该组实际可见的 `available`。随后程序把这些文档写进独立临时目录，检索器只读取这个副本。

原始知识挂载不会被修改。全部实验结束后，程序重新计算挂载文档的哈希；报告中的 `source_mount_unchanged` 用来确认原文仍然一致。这样，`drop_doc` 表示“Agent 拿不到这份资料”，而不是永久删掉课程资料。

这也把两个常被混淆的情况分开了：`drop_doc` 是资料集合中没有，即“拿不到”；`drop_hit` 是资料集合中有，但检索结果没交出来，即“取不到”。

**第3步：同时保存检索前后结果**

`fault_dispatch` 只截获 `search_knowledge`。它先正常检索并保存 `before`，再实施过滤或追加，最后把 `after` 作为真正的工具结果交给模型：

```python
hits = search_knowledge(QUERY, root=corpus)
before = json.loads(json.dumps(hits))
if case_id == "drop_hit":
    hits = [d for d in hits if d["id"] != "e04/limits.md"]
if case_id in ("add_old", "add_noise"):
    hits = [*hits, extra_document(case_id)]
retrievals.append({"query": QUERY, "before": before, "after": hits})
```

输入是固定查询和临时资料目录。输出有两份：`before` 表示检索器原本找到了什么，`after` 表示模型实际收到了什么。工具返回中的 `hits` 和 `output` 也都使用 `after`，所以日志不是旁观记录，而是与模型输入一致的真实证据。

其他工具仍交给原来的 `dispatch`。如果模型使用了不同查询，分发器会拒绝执行，并把错误留在 `events` 中。这能防止第二个变量悄悄混入实验。

**第4步：把故障开关接回原有 Agent 循环**

本课复用第4课的 `agent_loop`。循环只增加一个参数，并把工具执行处改为调用这个参数：

```python
def agent_loop(
    task,
    workspace,
    model=call_model,
    max_steps=8,
    approve=lambda n, a: False,
    tool_dispatch=dispatch,
):
```

真正接入循环的变化只有工具执行这一行：

```python
policy, result = tool_dispatch(
    call, workspace, approve
)
```

默认值仍是原来的 `dispatch`，所以普通调用保持原行为。模型调用、权限判断、工具结果回填、事件记录和停止条件都没有另写一套。

`bad_prompt` 也不能通过手工修改答案来伪造。它只把 `faulty_generation=True` 传给宿主机模型入口；入口源码会给生成阶段加入错误的兼容限额 `524288`。检索资料仍然包含正确的 `1048576`。因此我们可以观察“证据完整，但生成结果不一致”的情况，同时保留模型真实写出的文件。

**第5步：独立读取文件，再按证据定位**

Agent 说“已经完成”不代表文件正确。`inspect_artifact` 从工作区重新读取实际文件，校验 JSON 结构和字段类型，然后比较三个业务字段：

```python
value = json.loads(raw) if raw is not None else None
if not isinstance(value, dict):
    raise ValueError("Expected an object")
return {
    "status": "valid",
    "raw": raw,
    "value": value,
    "field_matches": {
        k: value[k] == v for k, v in EXPECTED.items()
    },
}
```

这里的输入是磁盘上的 `upload_notes.json`，输出包括原文、解析值和逐字段匹配结果。`null` 是合法的“当前证据缺失”，不是程序异常，也不是“系统确定没有限制”。

定位函数不读取 `case.id`，而是按照实际留下的证据逐层判断：

```python
if artifact["status"] != "valid":
    return "artifact_error"
if not REQUIRED <= set(available_ids):
    return "knowledge_gap"
if not REQUIRED <= set(returned_ids):
    return "retrieval_gap"
if all(artifact["field_matches"].values()):
    return "no_observed_task_failure"
return "generation_mismatch_requires_review"
```

`available_ids` 来自临时资料副本，`returned_ids` 来自最后一次检索的 `after`。资料缺了就是 `knowledge_gap`；资料在而返回缺了就是 `retrieval_gap`；两处都完整但字段不匹配，才进入 `generation_mismatch_requires_review`。

最后一个名称特意保留“需要复核”。它缩小了排查范围，却没有自动证明提示词就是唯一原因。模型抽样没有固定，单次结果只能支持当前观察和下一步假设，不能证明普遍因果。

**第6步：最后再用评分器补充观察**

阶段证据看清后，才需要辅助评分。评分程序不评价 `sources`，也不评价 Agent 最后的完成回执，只把实际文件的三个业务字段投影成文字：

```python
response = response_text(row["artifact"]["value"])
contexts = [
    d["text"]
    for d in row["retrievals"][-1]["after"]
]
```

DeepEval 的上下文相关性越高越好，但高分只说明返回内容大多切题，不保证资料找全，也不保证模型采用了正确值。

Ragas 的 NoiseSensitivity 越低越好。它按照“上下文是否支持 reference 中的事实”划分 `relevant` 与 `irrelevant`，不是按话题是否相似划分。一份过期上传说明可能很切题，却不支持当前合同；一份混合文档只要支持至少一条参考事实，就会进入相关组。若错误值没有被任何上下文支持，两个模式都可能是 0，因此 0 分也不能代替文件正确性检查。

测试夹具有一个构造演示：三条回答声明中，第一条正确；第二条错误且同时被两组上下文支持；第三条错误且只被无关组支持。两个模式都得到 `1/3`，分母是全部三条回答声明，而且第二条不会在无关模式重复计算。这只是手算夹具，不是 Agent 成绩。详细提示词、数据结构、支持矩阵和聚合过程见 [源码导读](source_walkthrough.md)。

评分输入本身也可能出错。初版 reference 漏写 `POST /upload`，并把 `null` 直接投影成 `None`，曾造成不合预期的裁判结果。修订版补全端点，并把 `null` 明确写成“在本次检索证据中未知”。当时只重新评分，没有修改或重跑 Agent。两轮数值和保留证据见 [实测记录](run_summary.md)。

## 相对上一课的变更

| 部分 | 第6课 | 本课 |
|---|---|---|
| reference 方法 | 使用版本化参考答案 | 保留方法，但固定回到 synthetic v1 |
| 工具、权限、循环 | 使用既有 Agent 流程 | 全部保留 |
| 实验对象 | 构造回答或已有产物 | 在三个真实阶段实施干预并重新运行六组 Agent |
| 新增机制 | 回答质量评测 | 故障开关、`before/after` 快照和噪声指标 |
| 判断依据 | 结果与评分 | 资料、检索、产物三层证据共同判断 |

历史制作时，六组 Agent 确实重新执行过，不是回放旧回答；当前文档重写则没有再执行它们。`add_old` 或 `add_noise` 在某一次运行中没有造成字段错误，只能写“本次未观察到任务失败”，不能说模型永远不受噪声影响。反过来，一次失败也不能证明同类干预必然失败。

## 试一下

先在宿主机保持两个桥接服务运行。已有登录凭据留在宿主机，不放入容器：

```bash
python3 tools/model_bridge.py
python3 tools/judge_bridge.py
```

模型桥接监听 `8766`，裁判桥接监听 `8768`。另开终端构建并运行六组 Agent：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e07_failure_diagnosis.code
```

它会写入 `runs/e07-agents.json`。然后对这份记录评分：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e07_failure_diagnosis.eval
```

评分结果写入 `runs/e07-evaluation.json`。两个文件重跑时都会覆盖；若要比较两轮实验，请先把旧文件另存。评测命令读取已保存的 Agent 记录，不会再次运行 Agent。

启动课程页面：

```bash
docker compose up -d
```

浏览器打开 `http://localhost:8765/lesson7`。阅读报告时，试着回答三个问题：

1. 对比 `drop_doc` 和 `drop_hit`：哪一组的 `available_documents` 已经缺少 `e04/limits.md`？哪一组只在 `retrievals.before` 到 `after` 之间丢失它？
2. 查看 `add_old` 与 `add_noise`：`after` 是否真的加入了合成文档？再检查 `artifact`，本次业务字段有没有随之变错？不要用干预意图代替实际结果。
3. 查看 `bad_prompt`：正确限额是否仍存在于 `after`？`artifact.raw` 写了什么？再从 `events` 核对模型调用和工具结果，说明为什么这里只能定位为“生成不匹配，仍需复核”。

完整六组历史实验、两轮裁判记录和边界说明分别保存在 [实测记录](run_summary.md) 与 [源码导读](source_walkthrough.md)，练习可继续查看 [课后题](exercises.md)。

## 接下来

这一课把一个低质量答案拆成了三层证据：资料是否可用、检索是否交付、产物是否正确。核心动作不是多加几个分数，而是固定任务和查询，每次只改变一个位置，并保存变化前后的事实。

排查得到的坏案例不能只留下一个低分。下一课会把这些有证据的案例整理成评测数据集：明确任务、参考版本、输入、预期标准和失败证据。这样，偶然发现的问题才能变成可以重复运行、持续检查的测试。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)