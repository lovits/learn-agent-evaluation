# 第7课：RAG故障定位，只改一个位置

同样漏掉上传限额，问题可能出在资料、检索或生成。我们给这三个位置加上开关，分别跑一遍。

## 问题

假设 Agent 最终生成了 `upload_notes.json`，其中 `max_bytes` 是 `null`。只看这个文件，三种情况几乎一模一样：

- 挂载资料里根本没有限额说明。
- 资料存在，但检索结果漏掉了它。
- 资料已经交给模型，模型却没有正确使用。

只看答案分数，还不知道该从哪里改。要找到问题，得把资料、检索结果和实际文件一起留下来。

本课固定回到第4课挂载资料使用的合成 v1 上传合同：认证头是 `X-Project-Token`，最大上传量是 `1048576` 字节，也就是 1 MiB，超限返回 `413`。第6课的 v2 合同是另一个受控版本，限额为 2 MiB，不能拿来判定本课的 v1 文档。参考答案仍然要带版本，这一次明确使用 v1。

## 解决方案

先跑一组正常流程，再一次打开一个故障开关。每次都保存改动前后的内容。

本课固定相同任务与相同查询，真实重跑六组 Agent：

| 组 | 唯一干预 |
|---|---|
| `baseline` | 不干预 |
| `drop_doc` | 从临时资料副本移除限额文档 |
| `drop_hit` | 保留文档，但从检索命中中移除 |
| `add_old` | 在命中中追加过期旧规范 |
| `add_noise` | 在命中中追加无关办公文档 |
| `bad_prompt` | 只改变宿主机上的生成指令 |

`cases.jsonl` 中的 `expected_observation` 是实验前写下的人工预期，不是实测结论。真实发生了什么，只能查看运行记录中的资料快照、检索前后结果、实际文件和事件轨迹。

## 工作原理

### 1. 先把任务、查询和标准固定下来

我们要看故障开关的影响，就先把任务和查询固定下来。三项字段仍然是认证头、限额和超限状态码：

```python
QUERY = "POST upload API token size limit"
EXPECTED = {
    "auth_header": "X-Project-Token",
    "max_bytes": 1048576,
    "over_limit_status": 413,
}
REQUIRED = {"e04/auth.md", "e04/limits.md"}
```

后续各组实验都使用这里的 `EXPECTED` 和 `QUERY`。任务还明确要求写出 `upload_notes.json`，证据缺失时填 `null`，不能猜测，并在结束前重新读取文件。

前面已经有工具调用和知识检索了。这一课继续用它们，把故障前后发生了什么记下来。`null` 的含义是“当前检索证据无法确定”，不是“系统确定没有限制”。

### 2. 在临时资料副本制造文档缺口

`drop_doc` 要模拟“资料本来就拿不到”。它在每组实验的临时副本中移除 `limits.md`，不会改动只读挂载的原始知识库：

```python
workspace = prepare_workspace({}, "e07-" + uuid.uuid4().hex)
available = [
    d for d in documents
    if case["id"] != "drop_doc"
    or d["id"] != "e04/limits.md"
]
retrievals = []
```

两份原始资料按当前实验组筛选后，剩下的放进 `available`。随后代码把这些文档写入独立临时目录，让检索只搜索这个副本。

运行结束后，程序再次读取原始挂载文档并核对 SHA-256。实测报告中的 `source_mount_unchanged` 用来确认原文没有被实验修改。

到这里，还没开始检索。文档若已被移除，后面再怎么调整查询也取不回来；文档还在却没被返回，就要继续往检索环节查。

### 3. 同时保存检索的 before 和 after

检索干预集中在 `fault_dispatch`。它先执行真实检索并复制一份 `before`，然后才过滤或追加文档：

```python
hits = search_knowledge(QUERY, root=corpus)
before = json.loads(json.dumps(hits))
if case_id == "drop_hit":
    hits = [d for d in hits if d["id"] != "e04/limits.md"]
if case_id in ("add_old", "add_noise"):
    hits = [*hits, extra_document(case_id)]
retrievals.append({"query": QUERY, "before": before, "after": hits})
```

分发器接到工具调用后，按当前实验组处理资料副本。`before` 留下检索器原本找到的内容，`after` 才作为 `tool_result` 交给模型。

`drop_hit` 的 `before` 有 `e04/limits.md`，`after` 没有。`add_old` 与 `add_noise` 则在 `after` 中分别追加一份明确标注为过期的旧规范或无关办公说明。

这个分发器还要求参数必须恰好是固定 `QUERY`。实测中，`drop_hit` 曾尝试换查询，被检查拒绝；这次拒绝也会留在 `events` 中。其他工具仍交给原来的 `dispatch`，所以文件读写和权限路径没有变化。

### 4. 把故障分发器插回原有循环

第4课的 Agent 循环增加 `tool_dispatch` 参数，默认值仍是原来的 `dispatch`。本课在 `run_case` 中把它换成刚才的故障分发器：

```python
result = agent_loop(
    TASK, workspace,
    model=model or (
        lambda messages: call_model(messages, case["id"] == "bad_prompt")
    ),
    tool_dispatch=fault_dispatch(case["id"], corpus, retrievals),
)
```

循环中真正变化的只有工具执行这一行：

```python
policy, result = tool_dispatch(
    call,
    workspace,
    approve,
)
```

把本组的 `fault_dispatch` 传进去，循环仍然拿到原有的权限决定和工具结果。模型调用、权限检查、结果回填、停止判断与事件记录都沿用原流程。

生成阶段用 `bad_prompt` 打开另一个开关。课程代码把这个布尔值发给宿主机模型入口：

```python
data=json.dumps({
    "lesson": "e07",
    "messages": messages,
    "faulty_generation": faulty_generation,
}).encode()
```

只有 `bad_prompt` 将该值设为真。宿主机入口才追加明确错误的兼容限额 `524288` 指令，模型仍需自己生成并写入文件。随后仍由原来的循环执行模型提出的写文件操作。

### 5. 先看文件，再判断问题在哪

循环结束后，我们再打开实际文件。`inspect_artifact` 检查文件里的键、JSON 类型和三个业务字段：

```python
value = json.loads(raw) if raw is not None else None
if not isinstance(value, dict) or set(value) != {*EXPECTED, "sources"}:
    raise ValueError("Expected three business fields and sources")
for key in ("max_bytes", "over_limit_status"):
    if value[key] is not None and type(value[key]) is not int:
        raise ValueError("Numeric fields must be integers or null")
```

这段摘自函数内部，省略了 `sources` 与认证头的类型检查、返回字典和异常记录；逐字段匹配在返回字典中计算，完整逻辑见 [code.py](code.py)。它读取实际的 `upload_notes.json`，把原文、解析值、有效状态和逐字段匹配结果一起返回。

定位函数不读取 `case.id`，只看实际证据：

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

六组真实结果中，`drop_doc` 的资料与检索都缺限额，定位为 `knowledge_gap`；`drop_hit` 的资料和 `before` 有限额，只有 `after` 缺失，定位为 `retrieval_gap`。两组最终都诚实写了 `null`，但原因不同。

`bad_prompt` 的 `after` 含有正确的 `1048576`，实际文件却写成 `524288`，因此标记为 `generation_mismatch_requires_review`。这个标签把问题留在生成阶段继续复核。一次受控运行可以帮助提出假设，还不足以证明所有类似失败都出于同一原因。

### 6. 看看评分器看到了什么

现在再看两个指标。评分程序把实际文件中的三个业务字段各写成一句话，`sources` 和 Agent 最后的完成回执不在这次评分范围内；原始文件和完整轨迹都保留。

```python
contexts = [
    d["text"]
    for d in row["retrievals"][-1]["after"]
]
response = response_text(row["artifact"]["value"])
metric = ContextualRelevancyMetric(
    model=DeepJudge(transport), eval_mode="llm",
    async_mode=False, include_reason=False,
)
```

DeepEval 的上下文相关性越高越好，但高分只表示返回内容大多切题，不代表资料已经找全，也不代表模型使用正确。实测中 `bad_prompt` 的相关性为 1，文件限额仍然错误。

Ragas 的 NoiseSensitivity 越低越好。它按照文档是否支持 `reference` 声明，把上下文分为 `relevant` 和 `irrelevant`，不是按话题是否相似分组。旧规范虽然也谈上传接口，却可能不支持当前合同中的任何事实。

构造夹具中有三条回答声明：第一条正确；第二条错误且被两类上下文支持；第三条错误且只被无关组支持。两个模式都是 `1/3`。第二条已经由相关组覆盖，不会在无关组重复计算；分母是全部回答声明。这个手算只是测试夹具，不是 Agent 的实测成绩。

如果一个错误不受任何检索上下文支持，两个模式都可能是 0。实测 `bad_prompt` 正是如此，所以 NoiseSensitivity 为 0 不能宣布任务正确。详细提示词、支持矩阵和聚合过程见 [源码导读](source_walkthrough.md)，完整评分入口见 [eval.py](eval.py)。本课参考的上游章节与写作对应见 [Learn Claude Code 阅读记录](../../references/e07-teaching-pattern.md)。

`drop_doc` 在修订轮的 Noise relevant 仍为0.8。矩阵显示，两项“检索证据未知”被拆成四条声明：局部检索上下文支持这些缺信息说明，完整 reference 却给出了数值，裁判据此判为不支持。这个分数不能直接解释为“80%的内容被噪声带偏”；它提示我们检查指标如何处理缺项与拒答，再结合文件的 `null` 和阶段日志判断。

评分输入本身也可能出错。初轮 `reference` 漏写 `POST /upload`，并把 JSON 的 `null` 直接投影成 `None`，导致裁判可能误解。修订协议补全端点，并把空值写成“在本次检索证据中未知”。这里只重新评分，没有修改或重跑六组 Agent；两轮数值与原始记录保留在 [实测记录](run_summary.md)。

## 相对第6课的变更

| 部分 | 第6课 | 本课 |
|---|---|---|
| 版本化参考答案 | 保留 | 保留，并明确使用合成 v1 |
| 工具、权限与循环 | 使用既有流程 | 保留流程，增加分发接入参数 |
| 实验对象 | 构造回答或评价旧产物 | 对真实 Agent 分阶段干预并重跑 |
| 新增内容 | 回答质量评价 | 故障开关、阶段快照、噪声指标 |
| 判断依据 | 结果与参考答案 | 资料、检索、产物三层证据 |

`add_old` 和 `add_noise` 本次都没有造成业务字段错误，只能写“本次未观察到任务失败”。模型抽样没有固定，不能据此声称模型永远不受噪声影响；同样，一次失败也不能证明所有类似任务都会失败。

## 试一下

先在宿主机的两个终端分别启动桥接服务，并保持运行。已经运行着本课版本的服务可直接复用，登录凭据留在宿主机：

```bash
# 终端1
python3 tools/model_bridge.py
# 终端2
python3 tools/judge_bridge.py
```

它们分别监听 `8766` 和 `8768`。另开终端构建并运行六组 Agent：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e07_failure_diagnosis.code
```

结果写入 `runs/e07-agents.json`。然后对这些实际产物评分：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e07_failure_diagnosis.eval
```

评分写入 `runs/e07-evaluation.json`。重跑会覆盖这两个文件，需要比较多轮时请先另存。阅读课程页面可运行：

```bash
docker compose up -d
```

打开 `http://localhost:8765/lesson7`。完整实验说明见 [实测记录](run_summary.md)，动手题见 [练习](exercises.md) 与 [参考答案](solutions.md)。

查看报告时，试着回答三个问题：

1. 对比 `drop_doc` 与 `drop_hit`：`available_documents`、`retrievals.before` 和 `retrievals.after` 中，`e04/limits.md` 分别从哪里开始消失？
2. 对比 `baseline`、`add_old` 与 `add_noise`：新增文档是否真的进入 `after`？`artifact` 的三个业务字段实际有没有变化？
3. 查看 `drop_hit` 的 `events`：哪次工具调用因查询变化被拒绝？拒绝后 Agent 如何依据现有证据写出文件？

## 接下来

给一条待查案例保留 `available_documents`、检索 `before/after`、实际文件和事件轨迹。保持任务与查询不变，下次只恢复一个开关，就能继续核对当前的排查假设。

下一课会把这些带有证据的案例整理成评测数据集，每条包含明确任务、版本化标准和故障依据。
