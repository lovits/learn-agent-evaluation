# Chapter 1: 工具、参数与MCP：分开看才评得准

## 问题

先看一个具体任务。工作区里的 `calculate.py` 是：

```python
quantity = 6
unit_price = 7
print(quantity * unit_price)
```

挂载的项目文档却规定，本次演示账单应使用 `quantity=6`、`unit_price=8`。编程 Agent 要读取文档、把脚本修好、真实运行程序，再把标准输出 `48` 保存到 `result.txt`。

困难在于，同一个正确结果可能来自两条路径：Agent 可以调用内置的 `search_knowledge`，也可以先连接教学用 MCP 服务，再调用动态发现的 `mcp__docs__search`。只检查最终文件，无法知道它是否遵守指定路由；只检查工具名，又无法知道参数、顺序、权限和文件是否正确。

因此，至少要把六件事分开观察：

1. 工具名是否合适；
2. 参数是否符合接口；
3. 调用顺序是否满足任务；
4. 宿主策略是否允许运行；
5. 工具是否真实执行成功；
6. 最终文件是否满足业务合同。

这仍然是编程 Agent，不是回答“答案是48”的问答机器人。它必须修改文件并留下运行证据；只回复 `48`，甚至把程序直接改成 `print(48)`，都没有完成“用6和8相乘”的任务。

## 解决方案

本课复用第4课已有的 Agent 循环、文件工具、权限判断和事件轨迹，只加入两部分：进程内模拟的 MCP 工具发现与分发，以及独立的工具调用评分。完整入口见 [code.py](code.py)、[mcp_tools.py](mcp_tools.py)、[metrics.py](metrics.py) 和 [eval.py](eval.py)。

这里的 MCP 与 Learn Claude Code 固定版本的 `s14` 一样，使用进程内模拟服务，目的是讲清发现和分发机制，不声称实现了 MCP 的标准输入输出或 HTTP 线协议。

![动态工具池](images/dynamic-tool-pool.png)

[放大查看动态工具池](images/dynamic-tool-pool.png)

图中只画出获准执行的路径。拒绝结果不会进入服务端处理器，而是作为工具结果直接回到原有 Agent 循环。模型桥运行在宿主机，只返回受限的 JSON 动作；文件、检索和命令工具仍在 Docker 中真实执行。是否放行由宿主配置决定，服务端写了“只读”或 `readOnlyHint` 并不会自动获得权限。

正式记录中，两版任务的业务合同都通过：内置版走 `search_knowledge`，MCP 能力版走 `connect_mcp` 和 `mcp__docs__search`，最后都得到真实的 `48\n`。不过，MCP 版额外明确要求了路由，所以这不是只改变一个因素的性能因果实验。

## 工作原理

**第1步：每一轮重新组装模型当前能看见的工具**

动态工具不能在连接前凭空出现。`run_case` 中的闭包先组装工具，再保存快照并请求宿主机模型桥：

```python
def model(messages):
    tools = pool.assemble()
    snapshots.append(
        {"model_turn": len(snapshots) + 1, "tools": tools}
    )
    return call_model(messages, tools)

result = agent_loop(
    task, workspace, model=model, max_steps=10,
    tool_dispatch=pool.dispatch,
)
```

摘自 [code.py](code.py)，局部省略。`messages` 是截至当前轮的对话，`tools` 是这一轮允许模型选择的接口。首轮只有原生工具、知识库搜索和 `connect_mcp`，还没有 `mcp__docs__search`。模型返回动作后，同一个第4课循环把调用交给 `pool.dispatch`，基础循环没有被替换。

**第2步：连接服务后，下一轮才加入发现的工具**

`connect` 只允许连接宿主预先配置的 `docs` 服务，并把工具定义和处理器保存在客户端中：

```python
def connect(self, name):
    if not self.enabled or name != "docs":
        raise ValueError(
            "Only the configured docs teaching server can be connected"
        )
    if name not in self.clients:
        self.clients[name] = docs_server()
        self.discovery_events.append({
            "server": name,
            "tools": copy.deepcopy(self.clients[name].tools),
            "transport": "in_process_teaching_stand_in",
        })
```

摘自 [mcp_tools.py](mcp_tools.py)，局部省略。下一轮调用 `assemble` 时，服务端的 `inputSchema` 被转换成模型侧的 `input_schema`，工具名变为 `mcp__服务器__工具`：

```python
name = (
    f"mcp__{normalize(client.name)}__"
    f"{normalize(tool['name'])}"
)
if len(name) > 64 or name in names:
    raise ValueError(
        "Normalized tool name collision or length above 64"
    )
schema = tool.get("inputSchema")
tools.append({
    "name": name,
    "description": tool.get("description", ""),
    "input_schema": copy.deepcopy(schema),
})
```

摘自 [mcp_tools.py](mcp_tools.py)，局部省略。规范化后的名字不能冲突，也不能超过64个字符。原生5个工具和 `search_knowledge` 都继续存在；连接只是扩充工具池，不是换掉原工具。

**第3步：分发时分别检查绑定、权限和参数**

模型给出的 `arguments_json` 先被解码为字典。分发器随后从内部绑定表取出固定的客户端和原始工具名：

```python
self.assemble()
client, raw = self.bindings[name]
policy = HOST_POLICY.get(
    (client.name, raw), "confirm"
)
if policy != "allow" and not approve(name, args):
    return {
        "decision": "deny",
        "reason": "host_mcp_policy",
    }, {
        "status": "denied",
        "output": "External tool not approved",
    }
```

摘自 [mcp_tools.py](mcp_tools.py)，局部省略。`HOST_POLICY` 才是授权依据。批量运行默认不会替模型确认未知工具，因此未批准调用会被拒绝。参数中的 `tool` 也不能改写已经绑定的 `raw`。

获准后，真实参数进入处理器。缺少参数、类型错误或多传字段都会变成工具错误，而不是悄悄修正。`mcp__docs__search` 的结果来自挂载知识库；它不是为了教材临时编造的一段搜索回答。非 MCP 工具则继续交给已有的 `previous_dispatch`。

**第4步：从原始事件生成不同用途的评分样本**

原始事件保留调用名、原始参数、顺序、权限决策和执行结果。确定性评分只取教学所需的局部投影：

```python
for event in row["events"]:
    if event["type"] != "tool":
        continue
    call = event["call"]
    args = json.loads(call["arguments_json"])
    if call["name"] == "read_file" and (
        args.get("path") == "result.txt"
    ):
        continue
    if call["name"] in {
        "read_file", "edit_file", "write_file", "bash"
    }:
        selected.append({
            "name": call["name"], "args": args,
            "source_span": event["span_id"],
        })
```

摘自 [metrics.py](metrics.py)，局部省略。11条 `micro_traces` 是人工构造但没有执行的控制样本；两条真实轨迹只投影读、改、写、运行等动作，并用 `source_span` 指回原事件。它们用于解释指标，不代表整项任务质量。

业务验收另读实际文件和已有执行证据，并接受 `edit_file`、`write_file` 等不同合法路径。它只验证直线整数乘法这个小合同，不重新执行任意生成程序，也不声称能证明一般 Python 程序等价。

**第5步：名字、参数、序列和集合会给出不同答案**

本课直接调用 DeepEval 与 Ragas 的固定版本接口：

```python
metric = ToolCorrectnessMetric(
    model=model,
    eval_mode="llm",
    async_mode=False,
    **options,
)
scores[name] = metric.measure(
    sample, _show_indicator=False
)
scores.update(asyncio.run(ragas_scores(row)))
```

摘自 [metrics.py](metrics.py)，局部省略。DeepEval 的 `ToolCorrectness` 默认主要看工具名；加入 `INPUT_PARAMETERS` 后，按双方参数键的并集计算匹配比例。开启排序时使用加权最长公共子序列并除以预期调用数；精确模式则严格比较整个列表。只有传入 `available_tools`，才会额外请求模型判断工具选择，并取规则分与选择分的较小值。本课真实运行了这个分支。

Ragas 的严格模式比较完整名字序列；灵活模式可以排序，但重复调用导致长度不同仍会失败。它的参数比较只遍历参考参数，并以字符串形式比较值，所以多余参数或类型错误可能被放过。实际处理器仍可能拒绝这些输入。

例如，正确的三次调用后又重复一次相同的 `read_file`：集合中的元素没有增加，因此完整 `(name, args)` 集合 F1 仍是1；严格序列因长度不同得到0。默认分数不能代替业务合同。双方空调用时，Ragas F1 为0而 Accuracy 为1，具体边界和完整矩阵见 [源码导读](source_walkthrough.md) 与 [运行摘要](run_summary.md)。

**第6步：语义参数评分必须看到决策当时的证据**

`ArgumentCorrectness` 让裁判根据 `input` 判断每次参数是否合理，再按原生 `Verdicts` 中 `yes` 的比例聚合。关键是：`input` 必须属于那次模型决策。

```python
if pending:
    messages.append({
        "role": "tool",
        "content": pending,
    })
    pending = []
calls = event["reply"]["tool_calls"]
if calls:
    index = int(
        event["span_id"].removeprefix("model-")
    ) - 1
```

摘自 [metrics.py](metrics.py)，局部省略。`pending` 保存上一轮已经发生的工具结果；进入下一模型轮前才回填。随后用同一轮的工具快照和此前消息构造评分输入，绝不加入本轮尚未发生的未来结果。

第一次评分把 MCP 轨迹裁掉了连接和文档检索，却保留完整任务要求，裁判因此把三次核心动作中的一次判错。真实 Agent 并不缺证据，是评分投影丢了证据。修订后只重建 `decision_contexts` 并重新评分，没有修改文件，也没有重跑 Agent。最终9个非空决策轮中的11次工具调用均由自动裁判判为 `yes`，不是人工标签。

如果没有工具调用，`ArgumentCorrectness` 会返回1且不请求裁判。这只表示“没有参数可判”，不能推出任务已经完成。两轮评分协议不同，分数变化也不能称为 Agent 改善。

## 相对上一课的变更

| 范围 | 上一课已有 | 本课新增 |
|---|---|---|
| Agent 执行 | 循环、知识库、文件工具、权限、轨迹 | 原样保留 |
| 工具来源 | 启动时已有工具 | 连接后下一轮动态发现 |
| 工具分发 | 原生工具分发 | MCP 名字绑定与宿主策略 |
| 评估重点 | 数量与统计比较 | 名字、参数、序列、集合分别评分 |
| 任务验收 | 独立检查结果 | 继续与工具指标分开 |

本课不再重复启动基础循环，也不提前引入目标审查、计划、记忆或完整 Agent。详细调用链、公式、原生裁判结构和边界差异放在 [source_walkthrough.md](source_walkthrough.md)。

## 试一下

先在宿主机启动模型桥。若旧进程是在代码更新前启动的，请先按 `Ctrl+C` 停止，再重新运行：

```bash
python3 tools/model_bridge.py
```

它监听8766端口。另开一个终端启动语义裁判桥：

```bash
python3 tools/judge_bridge.py
```

它监听8768端口，凭据始终留在宿主机。然后构建镜像并运行两版真实 Agent：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e10_tool_evaluation.code
```

执行断网的规则评分和只读业务验收：

```bash
docker compose --profile verify run --rm -T \
  --entrypoint python verifier \
  -m lessons.e10_tool_evaluation.eval
```

最后执行需要裁判桥的语义阶段：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e10_tool_evaluation.eval --judge
```

三步会分别覆盖 `runs/e10-agents.json`、`runs/e10-evaluation.json` 和 `runs/e10-judges.json`。要比较旧结果，请先另存旧文件。运行中写出的 `e10-agents.partial.json` 只表示已经保存部分进度，不表示所有轮次完成。

启动课程页面：

```bash
docker compose up -d
```

浏览器打开 `http://localhost:8765/lesson10`。实际证据和限制以 [run_summary.md](run_summary.md) 为准，验收过程见 [e10-validation.md](../../docs/e10-validation.md)，生成记录见 [e10-README.md](../../generation/e10-README.md)。

运行后尝试回答三个问题：

1. 首轮与连接后的工具快照中，哪两个新名字出现了？
2. 为什么重复一次相同调用时，集合 F1 仍为1，而严格序列为0？
3. MCP 首次误判是 Agent 缺少证据，还是评分输入丢失证据？

更多练习见 [exercises.md](exercises.md)，完成后再对照 [solutions.md](solutions.md)。

## 接下来

本课把工具发现、参数正确性、调用顺序、宿主授权、执行结果和业务产物拆开了。这样即使两个 Agent 都写出 `48`，我们仍能判断它们走了什么路径，以及每一种分数究竟证明了什么。

下一课将严格进入大纲第11课：面对更真实的编程任务，检查任务是否真正完成、目标状态是否达到，并为业务合同编写自定义指标。重点会从“这次工具调用是否匹配”推进到“整个真实任务是否完成”，还不会跳到计划系统。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)