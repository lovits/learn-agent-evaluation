# 第1课：最小编程 Agent 与第一份评测协议

> 学习目标：解释模型、Bash与验收器的职责；运行最小循环；从真实文件、输出和退出码核实任务结果。
> 前置：会Python，已准备Docker及本机Codex登录。完整代码与实验入口均在本课目录。

## 1. 一个具体问题：模型说“完成了”，任务就真的完成了吗？

先看一个很小的任务：

> 创建 `hello.py`，内容只包含一条 `print("Hello, World!")` 语句，然后使用 `python3` 运行它，报告实际结果。

模型可能直接回答：

> 已经创建并运行，输出为 `Hello, World!`。

但这句话本身不能证明任何事情。模型可能没有创建文件，也没有运行程序，甚至没有接触任务目录。

要得到可信结果，至少要分清三个角色：

| 角色 | 职责 | 不能代替什么 |
|---|---|---|
| 模型 | 决定下一步要执行的命令，或者停止并回答 | 不能自己证明命令真的执行过 |
| 课程循环 | 在独立的练习目录中执行真实 Bash | 不能自行决定任务是否满足合同 |
| 独立验收器 | 检查轨迹、输出和文件状态 | 不负责帮助模型完成任务 |

本课的核心结论是：

> `finished` 只表示模型停止了；`passed` 才表示独立验收通过。

我们会用一个只有模型调用、Bash 和循环的最小编程Agent，把这条边界真正跑出来。

---

## 2. 本课范围：只保留最小机制

本课只实现两件事：

1. 把当前消息交给模型，请模型返回 Bash 动作或最终回答。
2. 执行 Bash，把真实结果放回消息，再询问模型。

暂时不加入：

- 文件读取、写入或编辑专用工具；
- 知识检索与 RAG；
- 长期记忆；
- 计划器与任务系统；
- 子Agent；
- 多Agent协作。

模型若要查看文件、创建文件或运行程序，都只能生成 Bash 命令。这样做不是因为 Bash 足以构成完善的编程Agent，而是为了让第一课的因果链足够短：

```text
用户任务
  → 模型选择命令
  → 容器执行 Bash
  → 模型看到真实结果
  → 模型停止
  → 独立验收器检查任务合同
```

这里没有隐藏的复杂Agent。共享模块只负责保存报告等运行配套工作，不会偷偷替模型检索、规划或修改代码。

---

## 3. 从 Learn Claude Code 的最小循环开始

本课沿用 [Learn Claude Code s01 的固定版本源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py) 所展示的基本结构：

1. 把消息发送给模型；
2. 读取模型给出的工具动作；
3. 执行工具；
4. 把工具结果追加到消息历史；
5. 重复，直到模型不再调用工具。

原版 s01 使用 Anthropic 的 `tool_use` 和 `tool_result` 消息。本课为了复用宿主机已有登录，改用结构化 JSON 传输模型动作：

```json
{
  "answer": "",
  "tool_calls": [
    {"command": "python3 calculate.py"}
  ]
}
```

执行结束后，课程循环把真实结果放入下一轮消息：

```json
{
  "stdout": "42\n",
  "stderr": "",
  "exit_code": 0,
  "status": "ok"
}
```

如果模型决定停止，就返回空的 `tool_calls`：

```json
{
  "answer": "运行结果：42",
  "tool_calls": []
}
```

JSON 只是本课传输模型动作的格式，不改变核心循环。`tool_calls` 非空表示“还要行动”，为空表示“模型决定停止”。

---

## 4. 最小循环到底做了什么

完整实现位于 [code.py](code.py)，公开任务位于 [cases.jsonl](cases.jsonl)。

下文从完整程序摘出教学片段，省略了部分事件记录和配套参数；运行时使用完整 `code.py`，不把片段直接拼成另一份程序。先看核心循环：

```python
messages = [{"role": "user", "content": task}]
for step in range(1, max_steps + 1):
    response = model(messages)
    reply = response["reply"]
    messages.append({"role": "assistant", "content": reply})
```

`messages` 是模型目前能看到的对话历史。第一条消息只有用户任务。每轮得到模型动作后，再把它作为助手消息保存。

接着判断模型是否还要使用工具：

```python
if not reply["tool_calls"]:
    return {
        "status": "finished",
        "final_answer": reply["answer"],
        "events": events,
    }
```

这段代码只做停止判断。它没有检查文件是否存在，也没有检查输出是否正确。

因此，`finished` 的准确含义是：

> 模型返回了空的 `tool_calls`，课程循环正常结束。

它不等于“任务通过”。

如果模型给出了 Bash 动作，循环逐个执行：

```python
results = []
for call in reply["tool_calls"]:
    result = run_bash(call["command"], workspace)
    results.append(result)
messages.append({"role": "tool", "content": results})
```

下一次调用模型时，它会同时看到：

- 原始任务；
- 自己选择的 Bash 命令；
- 命令的真实标准输出；
- 命令的真实标准错误；
- 退出码和执行状态。

这一步像把实验结果交还给实验者。模型可以根据结果继续行动，也可以给出最终回答。

### 为什么不能省略工具结果

假设模型第一次返回：

```json
{"tool_calls": [{"command": "python3 fail.py"}], "answer": ""}
```

如果课程循环没有真实执行命令，而是直接再次询问模型，模型只能猜测发生了什么。只有把真实 `stderr` 和 `exit_code` 放回消息，最终回答才有观测依据。

所以两次模型响应之间必须有真实工具结果：

```text
模型请求命令
→ 容器执行命令
→ 返回真实结果
→ 模型基于结果回答
```

---

## 5. `run_bash`：动作真正发生的地方

模型只生成字符串。真正改变文件、运行程序的是 [code.py](code.py) 中的 `run_bash`。

它首先检查一份教学用阻断词表：

```python
BLOCKED = (
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "> /dev/",
)
```

如果命令命中阻断词，课程循环不会执行它，而是返回 `blocked`。这只是第一课的教学保护，不是完整的权限或安全体系。

未被阻断的命令通过子进程运行：

```python
with subprocess.Popen(
    command,
    shell=True,
    executable="/bin/bash",
    cwd=workspace,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    errors="replace",
    start_new_session=True,
) as process:
```

这里最重要的是 `cwd=workspace`：命令在当前任务的独立练习目录中执行，而不是在宿主机模型进程的目录中执行。

然后等待命令结束：

```python
stdout, stderr = process.communicate(timeout=timeout)
status = "ok" if process.returncode == 0 else "error"
```

课程循环分别保留：

- `stdout`：标准输出；
- `stderr`：标准错误；
- `exit_code`：退出码；
- `status`：课程循环对执行状态的分类。

返回结构类似：

```python
{
    "stdout": stdout[:50000],
    "stderr": stderr[:50000],
    "exit_code": process.returncode,
    "status": status,
}
```

输出过长时会截断，并在真实返回中记录 `truncated`。命令超时时，课程会终止对应进程组并标记 `timeout`。

### 工具失败不等于任务失败

`exit_code != 0` 只说明某条命令失败。任务是否通过取决于任务合同。

例如 `command_error` 的要求是：

> 运行 `fail.py`，如实报告实际错误，不要修改脚本或声称已修复。

这里非零退出码正是需要观察的证据。工具执行状态可以是 `error`，最终任务仍然可以通过。

---

## 6. 模型入口与容器执行必须分开

本课通过宿主机上的模型桥调用 Codex CLI，但 Codex CLI 只作为模型入口：

- Codex 自身工具被关闭；
- 它只返回结构化 JSON 动作；
- 它不负责执行课程任务；
- 练习目录不在宿主机模型进程中；
- 真正的命令由 Docker 内的课程循环执行。

这条边界很重要。如果模型入口自己也能读取或修改练习目录，我们将难以判断文件变化究竟来自课程循环，还是来自模型入口自带的工具。

本课的路径是：

```text
Docker 内课程循环
→ 向宿主机模型桥发送 messages
→ Codex CLI 只生成 JSON 动作
→ 课程循环在 Docker workspace 中执行 Bash
```

模型桥保留宿主机登录状态，不需要把登录凭据放入课程容器。

如果 CLI 没有返回确切的模型标识，报告中的 `reported_model` 就保持 `null`。不能因为 CLI 使用了默认选择，就把它描述成某个固定型号。

同样，报告中的令牌用量只表示 CLI 返回了相应计数。令牌用量不等于已知费用；没有明确计价信息时，不能据此编造金额。

---

## 7. 每条任务都有独立 workspace

运行任务前，`prepare_workspace` 会用新的 `run_id` 创建目录：

```python
workspace = (root / run_id).resolve()
workspace.mkdir(parents=True, exist_ok=False)
```

然后把公开样本中的初始文件写入这个目录：

```python
for name, content in case.get("files", {}).items():
    target = (workspace / name).resolve()
    if not target.is_relative_to(workspace):
        raise ValueError("样本文件不能越出练习目录。")
```

独立 workspace 能避免一种常见假阳性：

> 上一次运行遗留了 `hello.py`，下一次模型什么都没做，却因为旧文件仍然存在而通过。

每个 `run_id` 对应新的默认输入与结果目录。这里没有提供内核级任务隔离；跨目录访问约束在后续权限课进一步完善。

---

## 8. 与“只让模型回答”相比，增加了什么

起点只是一次模型问答：

```python
answer = model(task)
```

这种方式只能得到文本，不能证明模型真的执行了任务。

本课最小Agent增加了四样东西：

| 增加项 | 解决的问题 |
|---|---|
| `tool_calls` | 让模型表达下一步动作 |
| `run_bash` | 让动作在真实环境中执行 |
| `messages` 中的工具结果 | 让后续回答基于真实观测 |
| `events` 轨迹 | 让评测和复盘有证据可查 |

但这仍然不够。模型循环只负责完成过程，不能自己担任最终裁判。因此还需要独立验收协议。

---

## 9. 四条公开任务

本课的 [cases.jsonl](cases.jsonl) 包含四条公开任务：

| 任务 | 要求 | 关键证据 |
|---|---|---|
| `list_files` | 列出当前目录文件名 | Bash 输出包含两个给定文件名 |
| `create_and_run` | 创建指定 `hello.py` 并运行 | 成功输出和文件语法树 |
| `run_existing` | 运行已有脚本，不得修改 | 输出为 `42`，原文件保持不变 |
| `command_error` | 运行失败脚本并如实报告 | 错误确实出现，原文件保持不变 |

公开任务告诉模型要做什么。私有标准位于 `evaluation_private/e01.json`，不会挂载到 Agent 容器，也不会进入 Agent 镜像。

这并不是用隐藏条件刁难模型。验收条件必须由公开任务要求推导，例如：

- “不要修改脚本”对应文件哈希检查；
- “只包含一条 `print` 语句”对应 Python AST 检查；
- “报告实际错误”对应真实 `stderr` 检查。

不能先看模型结果，再为了让成绩好看而倒推或放宽标准。

---

## 10. 第一份评测合同

独立验收实现位于 [eval.py](eval.py)。

验收器先从事件中提取真实 Bash 记录：

```python
tools = [
    event
    for event in report["events"]
    if event["type"] == "bash"
]
```

然后检查两条所有任务共有的条件：

```python
checks = [
    {
        "name": "model_stopped",
        "passed": report["status"] == "finished",
    },
    {"name": "bash_was_executed", "passed": bool(tools)},
]
```

这能拒绝一种最简单的假完成：

> 最终回答写着“已经完成”，但轨迹中没有任何 Bash 事件。

任务专属规则再检查真实输出或文件状态。

### 检查成功输出

```python
return any(
    tool["result"]["exit_code"] == 0
    and value in tool["result"]["stdout"]
    for tool in tools
)
```

这要求目标内容出现在一条成功命令的真实标准输出中。模型最终回答里出现相同文字并不足够。

### 检查预期错误

```python
return any(
    tool["result"]["exit_code"] not in (0, None)
    and value in tool["result"]["stderr"]
    for tool in tools
)
```

`command_error` 就使用这种合同：必须真实观察到非零退出和指定错误，而不是让模型凭空复述错误消息。

### 检查文件未被修改

```python
digest = hashlib.sha256(target.read_bytes()).hexdigest()
return digest == rule["value"]
```

哈希检查适合验证已有脚本是否保持原样。

### 检查 `hello.py` 的结构

```python
actual = ast.dump(ast.parse(target.read_text()))
expected = ast.dump(ast.parse(rule["source"]))
return actual == expected
```

任务明确限定 `hello.py` 只包含一条 `print("Hello, World!")` 语句，因此 AST 合同比纯文本比较更合适：

- 单引号和双引号都可以；
- 注释和普通空白差异不会导致失败；
- 增加第二条语句会失败。

但这不是任意程序的功能正确性证明。AST 相同只适用于这个要求非常明确的小任务，不能据此推导通用代码质量、可维护性或语义等价。

### 汇总通过状态

```python
return {
    "passed": all(check["passed"] for check in checks),
    "score": sum(c["passed"] for c in checks) / len(checks),
    "checks": checks,
}
```

本课的评分来自程序断言。最终中文解释是否清楚、完整、诚实，目前不做语义评分。

自动合同只检查列出的证据。本次还逐条核对了报告中的实际Bash命令，确认相应Python调用；这些小任务检查不构成对抗性防投机或通用执行证明。

---

## 11. 独立验收为什么要放在另一个容器

Agent 容器与 verifier 容器承担不同职责：

| 环境 | 网络 | workspace | 私有标准 |
|---|---|---|---|
| Agent 容器 | 按课程运行配置 | 可写 | 不挂载 |
| verifier 容器 | 无网络 | 只读 | 只挂载给验收器 |

独立 verifier：

- 不调用模型；
- 不执行模型生成的程序；
- 只读取运行报告和 workspace；
- 用私有合同计算结果；
- 把评分报告写入 `runs`。

workspace 在 verifier 中只读，因此验收过程不能偷偷修复任务结果。私有标准不挂载给 Agent，也不进入 Agent 镜像，减少了模型针对验收实现投机的机会。

---

## 12. `finished`、`passed` 与其他停止状态

课程循环可能返回多种状态：

| 状态 | 含义 | 是否自动通过 |
|---|---|---|
| `finished` | 模型停止调用工具并给出回答 | 否 |
| `step_limit` | 用完最大循环步数 | 否 |
| `model_error` | 模型传输或动作结构出错 | 否 |
| Bash `timeout` | 某条命令超时 | 否 |
| Bash `error` | 某条命令非零退出 | 不一定 |

特别注意：

```text
模型停止：finished
独立验收：passed
```

模型可以正常停止但任务失败，例如：

- 没有执行 Bash；
- 创建了错误文件；
- 输出错误；
- 修改了本应保持不变的脚本；
- 声称成功但没有实际证据。

反过来，某条 Bash 命令非零退出也不一定让任务失败。`command_error` 的目标本来就是观察原始错误。

达到 `step_limit` 则表示预算耗尽，不是模型主动完成，不能当作成功停止。

---

## 13. 启动课程环境

先在宿主机终端保持模型桥运行：

```bash
python3 tools/model_bridge.py
```

模型桥需要持续运行。它接收容器传来的消息，并通过本机登录调用 Codex CLI。

在另一个终端启动课程服务：

```bash
docker compose up --build -d
```

课程阅读入口：

```text
http://localhost:8765/lesson
```

此时模型入口和任务执行环境已经分离：

- 宿主机模型桥只负责生成动作；
- Docker 内课程循环负责真实 Bash；
- verifier 容器负责独立验收。

---

## 14. 运行一条真实任务

运行 `create_and_run`：

```bash
docker compose run --rm -T course run \
  --case create_and_run
```

运行结束后，终端会打印一个真实 `run_id`、循环状态和报告路径。不要把示例中的编号复制成自己的运行编号。

随后使用刚刚得到的实际 `run_id` 进行独立验收：

```bash
docker compose --profile verify run --rm -T \
  verifier verify --run-id 实际run_id
```

你应分别阅读两份记录：

1. `e01-实际run_id.json`：Agent 的模型与 Bash 轨迹；
2. `grade-e01-实际run_id.json`：独立验收结果。

报告文件名经过严格校验，只允许课程规定的前缀和 32 位运行编号，避免通过文件名越出结果目录。对应实现位于 `eval_course/records.py`。

---

## 15. 批量运行四条公开任务

批量实验使用：

```bash
python3 tools/run_e01.py
```

批量脚本会运行公开任务并组织报告。真实模型结果必须从实际生成的报告中读取，不能根据单元测试或示例代码推测。

本课提供的 [example_report.json](example_report.json) 是一次已经保存的实际实验记录。它记录的实验发生于报告中的时间点，不代表你重新运行时必然得到相同结果。

---

## 16. 阅读实际示例报告

示例报告的汇总为：

| 指标 | 报告记录值 |
|---|---:|
| 任务数 | 4 |
| 通过数 | 4 |
| 模型请求数 | 8 |
| Bash 命令数 | 4 |

这四个数字都直接来自 [example_report.json](example_report.json)，不是估算值。

报告中的每条任务都经历了：

1. 第一次模型请求生成一条 Bash 命令；
2. 课程循环执行该命令；
3. 第二次模型请求基于工具结果给出最终回答；
4. 模型返回空 `tool_calls`，循环标记为 `finished`；
5. verifier 再根据任务合同给出 `passed`。

因此，该报告共记录 8 次模型请求和 4 条 Bash 命令。

### `list_files`

真实 Bash 命令为：

```bash
find . -maxdepth 1 -mindepth 1 -printf '%f\n' | sort
```

工具返回：

```text
alpha.py
notes.txt
```

验收器检查：

- 模型正常停止；
- 确实执行过 Bash；
- 实际输出中观察到 `alpha.py`；
- 实际输出中观察到 `notes.txt`。

该样本在示例报告中通过。

### `create_and_run`

模型生成的实际命令是：

```bash
printf '%s\n' 'print("Hello, World!")' \
  > hello.py && python3 hello.py
```

真实标准输出为：

```text
Hello, World!
```

验收器同时检查成功输出和文件 AST。两者都满足后，该样本在示例报告中通过。

这两个检查不能互相替代：

- 只有输出，可能是直接用 `printf` 伪造的；
- 只有文件，不能证明模型实际运行过它。

### `run_existing`

实际命令为：

```bash
python3 calculate.py
```

真实标准输出为 `42`。验收器还检查输入脚本哈希，确认模型没有修改 `calculate.py`。该样本在示例报告中通过。

### `command_error`

实际命令为：

```bash
python3 fail.py
```

报告记录：

- `exit_code` 为 `1`；
- Bash 状态为 `error`；
- `stderr` 包含 `RuntimeError: demo-failure`；
- Agent 最终状态为 `finished`；
- 独立验收结果为通过。

这正好说明：

> 工具非零退出和任务通过可以共存。

用户要求的是观察并如实报告错误，不是修复脚本。

---

## 17. 如何解释这份实验结果

示例报告证明的是：

- 在这一份固定实现和固定环境中；
- 针对四条公开任务；
- 实际运行产生了可检查的 Bash 轨迹；
- 独立程序断言判定四条任务通过。

它没有证明：

- 任意编程任务都能完成；
- 最终解释的语义质量足够好；
- Agent 具有通用编码能力；
- 模型费用是多少；
- CLI 使用了某个可确认的固定模型。

报告中每次模型调用的 `reported_model` 都是 `null`。因此只能说明 CLI 使用了报告记录的默认选择方式，不能把默认选择描述为某个固定型号。

报告也包含令牌计数，但没有已确认的费用金额。令牌用量不等于已知费用。

更不能把 `4/4` 扩写成脱离样本范围的“通用准确率”。它只是这一次报告中四条固定任务的通过情况。

---

## 18. 预设模型与合成假完成不能算作真实表现

项目中的单元测试会使用预设模型，也就是按脚本返回固定动作的测试替身。它们适合检查：

- 循环是否正确追加消息；
- 步数上限是否生效；
- 工具结果是否进入下一轮；
- 模型错误是否被正确记录。

但预设模型不是真实模型运行，不能计入真实模型表现。

类似地，课程还构造了一条“假报成功”的合成负例：

- 最终回答声称任务已经完成；
- 没有 Bash 事件；
- 没有真实文件或输出证据。

验收器应拒绝这条记录。这个实验是在测试验收器能否发现明显假完成，不是在测量真实Agent的“撒谎率”。

示例报告将它单独记录为：

```text
synthetic_verifier_test
```

不能把它和四条真实模型任务混在一起统计。

---

## 19. DeepEval 与 Ragas 在本课中的位置

第一课没有直接使用大模型裁判，也没有把程序断言伪装成 DeepEval 或 Ragas 指标。

本课借鉴的是两类框架共同的方法结构：

1. 先定义样本和预期；
2. 再运行待测系统；
3. 保存逐样本结果；
4. 使用明确指标评价；
5. 汇总实验记录，同时保留单条证据。

可以阅读以下固定版本源码：

- [DeepEval 数据集实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py)：理解数据、标准样本与运行结果的角色。
- [DeepEval 评测执行实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)：理解评测运行和结果组织。
- [Ragas 实验实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)：理解应用运行、逐样本评价和实验记录。

本课把这些思想落实成最小协议：

| 框架方法 | 本课对应物 |
|---|---|
| 样本 | `cases.jsonl` 中的公开任务 |
| 应用运行 | `agent_loop` |
| 运行轨迹 | `events` |
| 确定性指标 | `eval.py` 中的程序断言 |
| 逐样本结果 | `grade-e01-*.json` |
| 实验汇总 | 批量报告 |

第一课的评分就是程序断言。DeepEval 和 Ragas 在这里提供样本、运行与结果组织的方法依据；真正的框架适配会在后续课程逐步引入。

---

## 20. 推荐的源码阅读顺序

如果一开始直接读完整文件，网络传输、异常处理和报告字段容易遮住核心循环。建议按照下面的顺序阅读：

1. [cases.jsonl](cases.jsonl)：先明确四个任务合同。
2. [code.py](code.py) 的 `agent_loop`：看模型动作、Bash 结果和停止条件。
3. [code.py](code.py) 的 `run_bash`：看命令在哪执行、保存哪些事实。
4. [code.py](code.py) 的 `prepare_workspace`：看任务如何隔离。
5. [eval.py](eval.py) 的 `evaluate`：区分 `finished` 与 `passed`。
6. [eval.py](eval.py) 的 `check_rule`：看输出、错误、哈希和 AST 合同。
7. [example_report.json](example_report.json)：把代码结构对应到真实轨迹。
8. [源码导读](source_walkthrough.md)：复核模型、执行和验收三者的边界。

阅读 `agent_loop` 时，可以反复问三个问题：

- 这一行是在做模型决策、工具执行，还是验收？
- 这个值是模型声称的，还是环境实际观察到的？
- 当前状态说明“停止了”，还是说明“通过了”？

只要能稳定回答这三个问题，就抓住了本课的核心。

---

## 21. 练习与验收方式

完整练习位于 [第1课练习](exercises.md)，完成后再查看 [参考答案](solutions.md)。

### 练习一：读一条真实轨迹

运行 `list_files` 并独立验收，在报告中找出：

- 第一次模型动作；
- Bash 命令和真实返回；
- 第二次模型响应；
- `finished`；
- 独立评分中的 `passed`。

验收标准：能解释为什么两次模型响应之间必须有真实工具结果，以及为什么 `finished` 不等于 `passed`。

### 练习二：修改任务合同

把 `hello` 任务改成输出另一个明确字符串。先保持旧验收标准运行，再审查新合同。

验收标准：能说明任务要求、文件 AST 与成功输出必须属于同一版本。不能只为了提高分数而修改标准。

### 练习三：理解错误与步数上限

运行 `command_error`，观察非零退出码为什么仍可通过。然后阅读单元测试中的步数上限案例。

验收标准：能区分“脚本按任务要求暴露错误”和“Agent 因步数耗尽而未完成”。单元测试中的脚本化预设模型不能算真实模型实测。

### 练习四：构造假报成功

给验收器一条声称完成、但没有 Bash 事件和文件结果的合成记录。

验收标准：验收器应判失败；该记录必须作为验收器控制实验单独保存，不能计入真实模型表现。

### 练习五：说明合同局限

举出一个“输出看起来正确，但实现不满足要求”的例子，再指出一种本课没有评分的语义质量。

验收标准：理解 `hello` 的 AST 合同只适用于明确限定的单语句任务，不能从几个通过案例推出通用编码可靠性。

---

## 22. 学习验收清单

完成本课后，你应当能够逐项确认：

- [ ] 能画出“模型决策 → Docker 内 Bash 执行 → 独立验收”的边界。
- [ ] 能说明原版 s01 使用 `tool_use`/`tool_result`，本课使用 JSON `tool_calls`/`answer`。
- [ ] 能解释 Codex CLI 只是模型入口，自身工具被关闭。
- [ ] 能解释宿主机模型进程为什么不接触练习目录。
- [ ] 能逐行说明 `agent_loop` 如何追加模型动作和工具结果。
- [ ] 能说明 `run_bash` 保存 `stdout`、`stderr`、`exit_code` 和状态的原因。
- [ ] 能区分 `finished`、`passed`、`step_limit` 和 `model_error`。
- [ ] 能解释为什么 `command_error` 中非零退出仍可通过。
- [ ] 能说明 `hello` 的 AST 合同不是任意代码功能证明。
- [ ] 能说明每次任务为什么必须使用独立 workspace。
- [ ] 能说明 verifier 无网络、workspace 只读，私有标准不进入 Agent 环境。
- [ ] 能从实际报告读取任务数、模型请求数、Bash 次数和通过情况。
- [ ] 不把预设模型和合成假完成计入真实模型表现。
- [ ] 不根据令牌用量编造费用。
- [ ] 当 CLI 未返回确切模型标识时，保留 `null` 而不是猜测型号。
- [ ] 能说明第一课使用程序断言，DeepEval 与 Ragas 目前提供实验组织依据。

---

## 23. 下一课

这一课没有追求功能丰富，而是建立了一条最小、可观察、可验收的编程Agent链路：

```text
模型决定下一步
→ 课程循环执行真实 Bash
→ 工具事实返回模型
→ 模型决定停止
→ 独立验收器判断是否通过
```

复核这条链路时，要指出每个结论来自哪里：

- 模型动作来自结构化 JSON；
- 执行事实来自 Docker 内的 Bash；
- 任务是否通过来自独立程序断言；
- 实验数字来自保存的真实报告。

下一课将在保留这条边界的基础上继续完善工具与运行约束。无论以后加入文件工具、检索、记忆还是计划，都不应破坏本课建立的原则：模型停止不是任务通过，模型声明不能代替环境证据，执行系统也不能替代独立验收。

---

本章初稿由固定版本PocketFlow节点基于代码与真实运行记录生成，并经逐段核对。生成流程见 [PocketFlow制作记录](../../generation/README.md)，全课程规范见 [详细制作说明](../../docs/course-specification.md)。
