# 第2课：工具、权限、轨迹与统一评测样本

上一课，你已经让 Agent 在练习目录里执行过 Bash。这次要改一个 Python 文件：先找到它，读清内容，改一处，再运行看看。我们沿着这条操作过程，逐步加上文件工具、权限检查和执行记录，最后把记录交给 DeepEval 和 Ragas。第1课的代码继续保留。

本课不会加入检索、记忆、计划、子 Agent 或模型裁判。目标很具体：让 Agent 修改 `calculate.py`，运行程序，再判断整条操作过程是否符合任务合同。

完整实现见 [code.py](code.py)，完整任务见 [cases.jsonl](cases.jsonl)。

## 1. 从修改 `calculate.py` 开始

第一条任务 `edit_and_run` 的初始文件是：

```python
print(6 * 7)
```

任务要求 Agent：

1. 用 `glob` 找到 Python 文件；
2. 用 `read_file` 读取 `calculate.py`；
3. 用 `edit_file` 把 `6 * 7` 改成 `6 * 8`；
4. 用 `bash` 运行 `python3 calculate.py`；
5. 用 `write_file` 把实际输出写入 `result.txt`。

期望程序输出为 `48`，最终文件内容为：

```text
48
```

第1课的 Bash 其实可以完成全部工作，例如用 shell 命令查找、读取和改写文件。这里仍然增加具名工具，是因为评测不能只看最后有没有得到 `48`。我们还想知道：Agent 是否先读后改，改了哪个文件，编辑是否成功，以及它有没有用 Bash 绕过指定操作。

看到 `read_file`，你就知道这一步准备读取文件；看到 `edit_file`，就能直接核对旧文本和新文本。换成一长串 Bash，评测器还得先解析 shell，才知道它准备读写什么，权限判断也会更复杂。

本课只从第1课复用两个函数：

- `prepare_workspace`：为任务准备独立工作目录；
- `run_bash`：执行 Bash，并保留标准输出、标准错误、退出码和超时信息。

其余工具分发、权限和轨迹均在本课实现，没有提前引入未来课程的 Agent 代码。

## 2. 五种工具与参数校验

工具声明保存在 `TOOL_SPEC` 中：

```python
TOOL_SPEC = {
    "bash": {"command": "str"},
    "read_file": {"path": "str"},
    "write_file": {"path": "str", "content": "str"},
    "edit_file": {"path": "str", "old_text": "str", "new_text": "str"},
    "glob": {"pattern": "str"},
}
```

五种工具的必需参数如下：

| 工具 | 必需参数 | 本课行为 |
|---|---|---|
| `bash` | `command` | 调用第1课执行器 |
| `read_file` | `path` | 读取 UTF-8 文本 |
| `write_file` | `path`、`content` | 创建父目录并写入文本 |
| `edit_file` | `path`、`old_text`、`new_text` | 只替换第一处匹配 |
| `glob` | `pattern` | 排序后最多返回200项 |

`edit_file` 使用替换次数为 `1`，所以同一段文字出现多次时不会全部修改。`glob` 即使匹配了更多文件，也只展示前200项。这里没有加入原版 `read_file` 的可选读取行数。

模型传来的 `arguments_json` 先由 `validate_call` 解析。参数集合必须与声明完全一致，所有参数值都必须是字符串。下面摘出参数集合检查，完整函数还检查工具名、对象类型和参数值类型：

```python
args = json.loads(call["arguments_json"])
if set(args) != set(TOOL_SPEC[name]):
    raise ValueError("Expected arguments")
```

`missing_argument` 故意调用：

```json
{"name":"read_file","arguments_json":"{}"}
```

由于缺少 `path`，分发器在执行工具前返回 `invalid_arguments`。它不会读取文件，也不会进入权限判断。多传参数、参数不是字符串或 JSON 无法解析，同样属于参数错误。

## 3. 执行前权限：允许、拒绝与请求批准

参数有效后，`permission` 才检查权限。读报告时要同时看 decision 和 reason。三条权限分支分别是：

- `allow`：允许进入工具执行函数；
- `deny`：直接拒绝；
- `approval_required`：该规则要求批准，最终仍要由批准回调决定允许或拒绝。

例如，文件工具会先解析真实路径：

```python
path = (workspace / args["path"]).resolve()
if not path.is_relative_to(workspace):
    return "deny", "outside_workspace"
```

所以读取 `/etc/hostname` 会直接被拒绝。指向目录外的符号链接经过 `resolve` 后也会被拒绝。`glob` 的绝对路径或包含 `..` 的模式同样不允许。

Bash 中的部分危险命令进入硬拒绝或批准分支。批量实验的批准回调固定返回 `False`，不会弹出确认框。因此 `rm notes.txt` 的原因是 `approval_required`，最终决定仍是 `deny`，工具结果状态为 `denied`。

需要分清以下状态：

| 状态 | 停在哪一层 | 是否进入工具执行 |
|---|---|---|
| `invalid_arguments` | 参数校验 | 否 |
| `denied` | 权限判断 | 否 |
| `error` | 工具执行 | 是 |
| `timeout` | Bash 执行超时 | 是 |
| `ok` | 执行完成 | 是 |

`error` 不等于整个任务失败。例如读取不存在的 `missing.txt` 会产生 `FileNotFoundError`；运行 `fail.py` 会得到非零退出码和 `e02-demo-failure`。这些正是 `tool_error` 任务要求观察的结果。`timeout` 单独表示命令超过时限，不能混写成普通异常。第1课 Bash 执行器还可能返回 `blocked`，也不能强行改成 `ok`。

这些权限规则只是教学策略，不是任意 Bash 命令的安全隔离证明。字符串规则无法完整理解 shell 的重定向、解释器和间接调用。本课让 Docker 执行工具，宿主机 Codex 只返回动作；宿主机代码目录和登录凭据不挂入 Agent 容器。

## 4. 与原版 s02、s03、s04 的改编差异

本课参考固定提交中的 Learn Claude Code，但没有照搬全部机制。详细链接集中在 [源码导读](source_walkthrough.md)。

- 原版 s02 用 `TOOL_HANDLERS` 按名字选择函数，并用 `tool_use_id` 关联结果。本课保留五种工具，使用自己的 `call_id`，还明确规定 `edit_file` 只替换第一处、`glob` 最多返回200项。
- 原版 s03 先查拒绝规则，需要确认时调用 `ask_user`。本课保留允许、硬拒绝和请求批准三条分支，但批量运行固定拒绝批准请求；目录外文件也直接拒绝。
- 原版 s04 提供通用 hook 注册机制。本课只在 `UserPromptSubmit`、`PreToolUse`、`PostToolUse` 和 `Stop` 位置写记录，不搭建插件系统。
- 本课连拒绝和参数错误也记录成完整的 `PreToolUse`、`PostToolUse` 配对；原版在拒绝后直接继续，不会经过执行后的 Post hook。

因此，本课验证的是自己的教学合同，不能据此宣称与原版所有行为完全等价。

## 5. 用父子 span 还原一次调用

只记“调用过两次 `read_file`”不够。`mixed_order` 在同一轮依次读取 `a.txt`、读取 `b.txt`，再运行一条 Bash 命令。如果只按工具名匹配，两个读取结果会无法区分。

本课用四层标识建立关系：

- `run_id`：区分两次独立实验；
- `agent`：一次实验中的 Agent 根节点；
- `model-N`：第 N 次模型响应；
- `model-N:tool-i`：该响应中的第 i 个工具动作。

工具事件的 `parent_id` 指向所属 `model-N`，发回模型的结果也携带同一个 `call_id`。

每次工具请求先记录 `PreToolUse`，分发完成后记录 `PostToolUse`。这样回头查日志时，也能找到目录外拒绝、缺少参数和执行异常的完整经过。

`samples.py` 中的 `trace_errors` 会检查：

- 模型 span 是否重复，父节点是否为 `agent`；
- 工具顺序、`parent_id` 和原始调用是否匹配；
- 是否缺少工具结果；
- Pre/Post hook 是否缺失或状态错位。

交换两个工具事件会出现 `tool_result_order_or_owner`；漏掉结果会出现 `missing_tool_result`；删除 Post hook 会出现 `hook_coverage`。但这只是内部一致性检查，不是防篡改证明。若有人同时伪造事件和输出，它不能凭轨迹本身证明 stdout 真实，仍需独立验收文件状态和执行结果。

## 6. 从轨迹生成两套框架样本

单轮视图回答“这道任务最终输入和输出是什么”；多轮视图保留“模型在哪一轮提出了哪些工具动作，工具怎样返回”。

本课实际构造并往返恢复四种对象：

- DeepEval `LLMTestCase`；
- DeepEval `ConversationalTestCase`；
- Ragas `SingleTurnSample`；
- Ragas `MultiTurnSample`。

字段映射如下：

| 本课事实 | DeepEval | Ragas |
|---|---|---|
| 任务 | `input` | `user_input`／`HumanMessage` |
| 最终回答 | `actual_output` | `response`／末尾 `AIMessage` |
| 预期答案 | `expected_output` | `reference` |
| 工具请求 | `tools_called` | `ToolCall` |
| 工具结果 | `ToolCall.output` | `ToolMessage.content` |
| 检索证据 | `retrieval_context` | `retrieved_contexts` |

DeepEval 的四个基础字段是 `input`、`actual_output`、`expected_output`、`retrieval_context`，工具动作另放在 `tools_called`。Ragas 单轮样本对应 `user_input`、`response`、`reference`、`retrieved_contexts`；多轮样本使用 `HumanMessage`、`AIMessage` 和 `ToolMessage`。

本课没有检索知识库。文件读取内容是工具输出，不能伪装成检索证据。因此相关字段保持 `None`。`None` 表示“没有提供这个事实”，空列表表示“明确提供了一个空集合”，两者不能随意互换。

轨迹结束条件与任务通过条件也要分开。Agent 返回无工具调用的最终回答时，运行状态可以成为 `finished`；但只有文件、输出、轨迹和样本合同全部通过，任务才算通过。

## 7. JSON 往返中的 SDK 细节

`eval.py` 会先构造四种原生 SDK 对象，再导出 JSON，并从 JSON 恢复对象。这一步能发现只看普通字典看不到的校验问题。

当前固定版本 DeepEval 4.3.4 的 before validator 要求 `tools_called` 中已经是 `ToolCall` 实例。把导出的嵌套字典直接传回 `LLMTestCase` 会报错，所以恢复时要先建 `ToolCall`：

```python
single["tools_called"] = [
    ToolCall.model_validate(c)
    for c in single["tools_called"]
]
```

会话样本中每个 `Turn` 的工具列表也要这样恢复。实现见 [samples.py](samples.py)。

Ragas 0.4.4 的 `ToolCall` 有 `name` 和 `args`，却没有本课需要的独立 `call_id` 字段。因此关联 ID 放在 `AIMessage` 与 `ToolMessage` 的 `metadata` 中，同时继续保留原始轨迹。后续指标未必读取这些 metadata，不能把“成功保存”误写成“所有指标都会使用”。

SDK 对象构造成功，只能说明结构满足当前模型校验，不能说明任意指标都可运行。本课没有运行 G-Eval、Faithfulness 或工具质量分数，也没有评价最终回答的语义质量和工具路径是否最优。这里不新增裁判调用，没有裁判提示词、裁决聚合或异步评分。

固定版本的源码入口和官方说明见 [source_walkthrough.md](source_walkthrough.md)。其中包括 DeepEval `LLMTestCase`、`ToolCall`、`ConversationalTestCase`、`TraceManager.add_span_to_trace`，以及 Ragas `SingleTurnSample`、`MultiTurnSample`、`validate_user_input` 和消息类型。DeepEval Tracing 会按父节点组织子节点；Ragas 会校验 Tool 消息之前的 AI 消息及消息顺序。本课只是用本地 `parent_id` 实现同类归属关系，没有调用 `observe`，也没有接入原生云端 tracing。

## 8. Docker 实验与独立验收

先在宿主机启动模型动作桥接：

```sh
python3 tools/model_bridge.py
```

另开终端执行：

```sh
docker compose up --build -d
docker compose run --rm -T course run-e02 --case edit_and_run
docker compose --profile verify run --rm -T verifier verify-e02 --run-id 实际run_id
python3 tools/run_e02.py
```

单条任务运行后会输出实际 `run_id`。把它填入验收命令，不要照抄“实际run_id”。重跑会在 `runs` 中新建报告，默认不会覆盖固定示例。

课程容器负责执行工具。独立 verifier 容器断网，工作目录以只读方式挂载，私有验收标准只挂给 verifier，不进入 Agent 镜像。凭据也不进入容器。本课知识库仍不参与检索。

每个任务必须同时满足：

- 运行状态为 `finished`；
- 轨迹内部一致；
- 指定工具具有要求的状态；
- 指定文件或标准输出、退出码符合合同；
- 四种 SDK 样本都能构造、导出并恢复。

任一检查失败，该任务就不通过。分母只有五条实际执行的开发任务。

## 9. 五条开发任务的实际结果

固定运行摘要见 [run_summary.md](run_summary.md)，逐事件报告见 [example_report.json](example_report.json)。

| 任务 | 实际观察 | 验收 |
|---|---|---|
| `edit_and_run` | 五种工具完成；程序输出48；`result.txt` 为48加换行 | 通过 |
| `permission_denied` | 目录外读取被拒绝；`rm` 要求批准后被固定拒绝；`notes.txt` 未变 | 通过 |
| `missing_argument` | `read_file` 缺少 `path`，执行前返回 `invalid_arguments` | 通过 |
| `tool_error` | 缺失文件返回 `error`；原脚本退出1并输出 `e02-demo-failure` | 通过 |
| `mixed_order` | 两次读取与 Bash 均有独立 `call_id`；文件保持 A/B/N 顺序 | 通过 |

本次五条开发任务全部通过，共有16次真实模型请求、14次工具请求。其中2次被拒绝，1次参数校验失败，其余11次进入工具执行。每条记录都完成四种 SDK 对象的构造和往返恢复，共20份原生对象视图。

看到 `error` 时，先回头读任务：这道题要求 Agent 观察错误，验收就要检查它是否遇到了预期错误、原文件是否保持不变、退出码是否符合要求。这些故障是我们刻意设置的实验条件，不能拿来统计模型自然犯错的频率。

数据集共有开发5条、校准2条、留出2条。校准集和留出集具有完整任务、初始文件与验收标准，但尚未执行，不计入本次通过率，也不进入 Agent 镜像。具体标识、数量和哈希见 [dataset_manifest.json](dataset_manifest.json)。

## 10. 练习

完整题目见 [exercises.md](exercises.md)，完成后再对照 [solutions.md](solutions.md)。

建议至少完成以下检查：

1. 在 `mixed_order` 中追踪两个重复的 `read_file`，说明为什么工具名不足以关联返回。
2. 分别构造 `denied`、`invalid_arguments`、`error`，判断哪些真正进入执行函数。
3. 交换两个工具事件，再运行 `trace_errors`，观察错位轨迹怎样被识别。
4. 导出并恢复四种 SDK 样本，确认工具状态、`call_id` 和 `exit_code` 没有丢失。
5. 让 `edit_file` 查找不存在的 `old_text`，确认返回 `error` 且原文件不变。
6. 按任务族设计 calibration 和 holdout，避免只改文件名就把同类题分到不同集合。

## 接下来评回答质量

做完练习，你应该能沿着一份记录找到动作、权限决定和实际结果，也能检查它是否满足本课的确定性合同。第3课会接着处理一个尚未评分的问题：Agent 的最终解释写得怎样，工具用得是否合适。我们会比较规则评分和 LLM 裁判。
