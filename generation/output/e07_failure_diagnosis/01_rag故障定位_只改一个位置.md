# Chapter 1: RAG故障定位：只改一个位置

这一课解决一个具体问题：同样漏掉“最大上传字节数”，怎样判断是资料没有、检索漏了，还是模型拿到资料后写错了？

## 问题

假设 Agent 最终生成了 `upload_notes.json`，其中 `max_bytes` 是 `null`。只看这个文件，三种情况几乎一模一样：

- 挂载资料里根本没有限额说明。
- 资料存在，但检索结果漏掉了它。
- 资料已经交给模型，模型却没有正确使用。

一个答案分数也区分不了这些位置。低分只能告诉我们“结果可能有问题”，不能告诉我们应该改文档、检索器还是生成指令。

本课固定回到第4课挂载资料使用的合成 v1 上传合同：认证头是 `X-Project-Token`，最大上传量是 `1048576` 字节，也就是 1 MiB，超限返回 `413`。第6课的 v2 合同是另一个受控版本，限额为 2 MiB，不能拿来判定本课的 v1 文档。这里继承的是“参考答案必须带版本”的方法，并不是说两课使用了相同的参考文本。

## 解决方案

做故障定位时，一次只改变一个位置，并保存改变前后的证据。

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

这样做像检查一条输水管：先看水源，再看管道出口，最后看接水的人。末端没有水，不等于水源一定为空。

## 工作原理

### 1. 先固定任务、查询和业务合同

如果查询或任务也在变化，就无法知道结果差异来自故障开关，还是来自另一种问法。因此第一步是固定三个业务字段与查询：

```python
QUERY = "POST upload API token size limit"
EXPECTED = {
    "auth_header": "X-Project-Token",
    "max_bytes": 1048576,
    "over_limit_status": 413,
}
REQUIRED = {"e04/auth.md", "e04/limits.md"}
```

输入是合成 v1 合同；输出是后续所有实验共同使用的 `EXPECTED` 和 `QUERY`。任务还明确要求写出 `upload_notes.json`，证据缺失时填 `null`，不能猜测，并在结束前重新读取文件。

读者已经在前面学过工具调用和知识检索。本课不增加新工具，只增加故障发生位置的记录。`null` 的含义是“当前检索证据无法确定”，不是“系统确定没有限制”。

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

输入是原始两份资料和当前实验组；输出是该组真正可用的 `available`。随后代码把这些文档写入独立临时目录，让检索只搜索这个副本。

运行结束后，程序再次读取原始挂载文档并核对 SHA-256。实测报告中的 `source_mount_unchanged` 用来确认原文没有被实验修改。

这一步区分了两件事：“拿不到”表示检索开始前就没有文档；“取不到”表示文档存在，但没有进入最终命中。

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

输入是工具调用、临时资料目录和实验组；输出中的 `before` 表示检索器原本找到了什么，`after` 才是真正作为 `tool_result` 交给模型的内容。

`drop_hit` 的 `before` 有 `e04/limits.md`，`after` 没有。`add_old` 与 `add_noise` 则在 `after` 中分别追加一份明确标注为过期的旧规范或无关办公说明。

这个分发器还要求参数必须恰好是固定 `QUERY`。实测中，`drop_hit` 曾尝试换查询，被检查拒绝；这次失败完整保存在 `events`，没有被伪装成成功。其他工具仍交给原来的 `dispatch`，所以文件读写和权限路径没有变化。

### 4. 把故障分发器插回原有循环

第4课的 Agent 循环只增加了一个参数，默认值仍是原来的分发函数：

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

循环中真正变化的只有工具执行这一行：

```python
policy, result = tool_dispatch(
    call,
    workspace,
    approve,
)
```

输入是本组的 `fault_dispatch`；输出仍是原有的权限决定和工具结果。模型调用、权限检查、结果回填、停止判断与事件记录都沿用原流程。

生成阶段的 `bad_prompt` 也不能靠手工改答案制造。课程代码只把布尔开关发给宿主机模型入口：

```python
data=json.dumps({
    "lesson": "e07",
    "messages": messages,
    "faulty_generation": faulty_generation,
}).encode()
```

只有 `bad_prompt` 将该值设为真。宿主机入口才追加明确错误的兼容限额 `524288` 指令，模型仍需自己生成并写入文件。这样得到的是一次真实生成故障，而不是伪造产物。

### 5. 独立读取文件，再依据证据定位

Agent 说“已经完成”不能代替文件事实。`inspect_artifact` 在循环结束后独立读取实际文件，检查键、JSON 类型和三个字段：

```python
value = json.loads(raw) if raw is not None else None
if not isinstance(value, dict):
    raise ValueError("Expected an object")
for key in ("max_bytes", "over_limit_status"):
    if value[key] is not None and type(value[key]) is not int:
        raise ValueError("Numeric fields must be integers or null")
field_matches = {k: value[k] == v for k, v in EXPECTED.items()}
```

这里省略了 `sources` 和认证头的类型检查；完整逻辑见 [code.py](code.py)。输入是实际的 `upload_notes.json`，输出包含原文、解析值、有效状态和逐字段匹配结果。

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

`bad_prompt` 的 `after` 含有正确的 `1048576`，实际文件却写成 `524288`，因此标记为 `generation_mismatch_requires_review`。这个名字有意保留“需要复核”：单次受控运行能支持排查假设，但不能自动证明普遍因果。

### 6. 最后才用指标辅助观察

阶段证据看清后，再引入两个指标。评分程序只把实际文件中的三个业务字段投影成文字，不评价 `sources`，也不评价 Agent 最后的完成回执；原始文件和完整轨迹仍保留。

```python
contexts = [
    d["text"]
    for d in row["retrievals"][-1]["after"]
]
response = response_text(row["artifact"]["value"])
metric = ContextualRelevancyMetric(
    model=DeepJudge(transport),
    async_mode=False,
)
```

DeepEval 的上下文相关性越高越好，但高分只表示返回内容大多切题，不代表资料已经找全，也不代表模型使用正确。实测中 `bad_prompt` 的相关性为 1，文件限额仍然错误。

Ragas 的 NoiseSensitivity 越低越好。它按照文档是否支持 `reference` 声明，把上下文分为 `relevant` 和 `irrelevant`，不是按话题是否相似分组。旧规范虽然也谈上传接口，却可能不支持当前合同中的任何事实。

构造夹具中有三条回答声明：第一条正确；第二条错误且被两类上下文支持；第三条错误且只被无关组支持。两个模式都是 `1/3`。第二条已经由相关组覆盖，不会在无关组重复计算；分母是全部回答声明。这个手算只是测试夹具，不是 Agent 的实测成绩。

如果一个错误不受任何检索上下文支持，两个模式都可能是 0。实测 `bad_prompt` 正是如此，所以 NoiseSensitivity 为 0 不能宣布任务正确。详细提示词、支持矩阵和聚合过程见 [源码导读](source_walkthrough.md)，完整评分入口见 [eval.py](eval.py)。

评分输入本身也可能出错。初轮 `reference` 漏写 `POST /upload`，并把 JSON 的 `null` 直接投影成 `None`，导致裁判可能误解。修订协议补全端点，并把空值写成“在本次检索证据中未知”。这里只重新评分，没有修改或重跑六组 Agent；两轮数值与原始记录保留在 [实测记录](run_summary.md)。

## 相对第6课的变更

| 部分 | 第6课 | 本课 |
|---|---|---|
| 版本化参考答案 | 保留 | 保留，并明确使用合成 v1 |
| 工具、权限与循环 | 使用既有流程 | 原样复用 |
| 实验对象 | 构造回答或评价旧产物 | 对真实 Agent 分阶段干预并重跑 |
| 新增内容 | 回答质量评价 | 故障开关、阶段快照、噪声指标 |
| 判断依据 | 结果与参考答案 | 资料、检索、产物三层证据 |

`add_old` 和 `add_noise` 本次都没有造成业务字段错误，只能写“本次未观察到任务失败”。模型抽样没有固定，不能据此声称模型永远不受噪声影响；同样，一次失败也不能证明所有类似任务都会失败。

## 试一下

先在宿主机保持两个桥接服务运行。已有登录凭据留在宿主机，不放进容器：

```bash
python3 tools/model_bridge.py
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

打开 `http://localhost:8765/lesson7`。完整实验说明与验收细节见 [实测记录](run_summary.md) 和 [练习](exercises.md)。

查看报告时，试着回答三个问题：

1. 对比 `drop_doc` 与 `drop_hit`：`available_documents`、`retrievals.before` 和 `retrievals.after` 中，`e04/limits.md` 分别从哪里开始消失？
2. 对比 `baseline`、`add_old` 与 `add_noise`：新增文档是否真的进入 `after`？`artifact` 的三个业务字段实际有没有变化？
3. 查看 `drop_hit` 的 `events`：哪次工具调用因查询变化被拒绝？拒绝后 Agent 如何依据现有证据写出文件？

## 接下来

这一课把一个末端错误拆回了资料、检索和生成三个位置。关键不是先看哪个指标低，而是固定任务与查询，每次只改变一个位置，并保留 `available_documents`、检索 `before/after`、实际文件和事件轨迹。

下一课会把这些有证据的坏案例整理成评测数据集：保存明确任务、版本化标准和故障依据，而不是只收藏一个低分。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)