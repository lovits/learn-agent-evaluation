# e13: 多轮会话评测：用户改口后，哪条要求还有效？

[e12](../e12_task_completion/README.zh.md) → `e13` → [e14](../e14_judge_calibration/README.zh.md) → … → e16

> *“历史会话里出现过一句话，只代表当时说过；Agent 这次做对没有，要核对当前有效约束和它真正看到的输入。”*
>
> **评测层：多轮会话。** 按回合归并用户的覆盖与取消标注，分别记录实际模型输入、工具恢复过程、最终文件与 DeepEval 会话指标。

## 问题

假设用户在多轮对话里先约定：把文件写到 `report.md`，正文不超过 40 字，用中文写，同时不要修改 `policy.txt`。下一轮用户改口：目标文件换成 `summary.md`，正文替换成一段超过 40 字的发布规范，并取消长度限制，其余要求继续有效。最后一轮用户只说一句：“现在按最新约定写文件，并回复最终路径。”

如果 Agent 最终仍然写了 `report.md`，原因可能是模型看到了最新要求却没执行，也可能是历史上下文被截断或摘要过时，模型从头到尾都没见过 `summary.md`。只盯着最后一句回复，无法把这两种问题区分开；如果在评分时继续沿用已经取消的 40 字限制，还会把按新约定交付的长正文误判为失败。

## 解决方案

把“当前有效约束”、“模型每轮实际看到的上下文”与“工作区最终文件”拆开记录。本课围绕同一条最终请求设置五种上下文前缀（完整历史、仅保留当前轮、过期摘要、当前摘要、归档提示），观察不同输入条件下 Agent 的执行路径与恢复动作。

![原始会话经过上下文选择后进入现有 Agent](https://lovits.github.io/learn-agent-evaluation/diagrams/e13-context-flow.svg?v=95b575b73552)

评分分两条线进行：独立文件检查先按当前有效约束核对工作区产物，再用 DeepEval 原生会话指标 `KnowledgeRetentionMetric` 与 `ConversationCompletenessMetric` 评价回复对历史事实与用户意图的覆盖情况，两类结果分别保留。

![当前约束、会话裁决与实际输入分别帮助判断和定位](https://lovits.github.io/learn-agent-evaluation/diagrams/e13-conversation-scoring.svg?v=238759e90a95)

## 工作原理

### 增量归并用户改口

[scenario.json](scenario.json) 为用户的每条历史发言附上显式的 `set` 和 `drop` 标注，用来计算评分依据的真值状态（去掉正文文本后如下）：

```json
{"id": "u1", "set": {"path": "report.md", "max_chars": 40}}
{"id": "u2", "set": {"path": "summary.md"}, "drop": ["max_chars"]}
```

这些标注仅提供给评分程序，发送给被测模型的对话消息与归档文件只保留纯文本内容。`set` 新增或覆盖对应字段，`drop` 移除已经取消的约束，未提及的 `language`（中文）与 `preserve`（保留 `policy.txt`）继续生效。

[active_requirements](eval.py) 按回合顺序归并这些标注，同时记录每一项约束的来源回合和被替换掉的旧值：

```python
active[key], sources[key] = value, turn["id"]
```

归并后，`path` 与 `body` 来自 `u2`，`preserve` 与 `language` 保留自 `u1`，`max_chars` 已经从 `active` 中移入 `superseded`。评分程序据此知道新正文不受旧的 40 字上限约束。

### 把历史保存与模型可见分开

原始会话保存在 `scenario.json` 的 `history` 里，而每次调用模型前实际拼装的上下文由 [context_for](code.py) 控制：

| 模式 | 起始输入 |
|---|---|
| `full` | 完整原始会话 |
| `tail` | 空前缀，仅保留当前轮次请求 |
| `stale` | 课程预置的过期摘要（仍写 `report.md` 与 40 字限制） |
| `current` | 课程预置的当前摘要（包含 `summary.md` 与取消长度限制） |
| `archive` | 归档路径提示，告知原会话保存在工作区 `conversation.json` |

本课复用第 2 课的 `agent_loop` 与文件工具。每次向模型发起请求时，[code.py](code.py) 先复制选定前缀与当前消息列表的快照存入 `model_inputs`，再发起决策：

```python
visible = copy.deepcopy(prefix + messages)
inputs.append(visible)
response = call_model(visible, tools=TOOLS) if live else next(scripted)
```

定位问题时应逐次查看 `model_inputs`，而不能默认完整会话已经自动进入模型上下文。

### 归档恢复与多步输入查证

参考 Learn Claude Code 在上下文压缩时保留归档文件并在需要时读回的设计，本课在隔离工作区里写入一份纯文本归档 `conversation.json`（只含 `id`、`role`、`content`，不含 `set` 与 `drop`）。当起始前缀只有归档提示时，Agent 可以通过现有 `read_file` 工具读回原对话：

```text
归档路径提示
  → read_file(conversation.json)
  → 真实工具输出回填进 messages
  → 下一轮 model_inputs 包含最新约定
  → 按最新要求写入 summary.md
```

在 `archive_recovery` 样本中，预设脚本将读取和写入拆分在两批决策里，先拿到真实工具返回再写入文件；在 `--live` 模式下，真实模型也是在读回归档之后的请求中才看到 `summary.md`。

因此，首次输入里没有 `summary.md` 只说明起跑点缺少该信息，后续仍可能通过主动读档或列目录补齐；反之，`expected_path_in_first_input` 为真也只是首次输入的字符串匹配，仍需结合后续调用和最终文件判断是否真的落实了更新。比如同样写了旧路径 `report.md`，`full_old` 的首次输入已经包含更新，排查重点是模型为何忽略新指令；`stale_memory` 的首次输入只有过期摘要，排查重点则是摘要机制为何遗漏了变更，以及是否提供了恢复入口。当上下文被截断到只剩当前轮次（`tail_only`）时，Agent 回复请求用户补充路径和正文，也是避免盲目猜测的合理选择，不应和危险越界混为一谈。

### 按最新约束核验磁盘产物

[check_delivery](eval.py) 直接读取工作区磁盘上的最新目标路径 `goal["path"]`，同时核对旧路径下没有生成多余产物、`policy.txt` 字节保持不变：

```python
checks = {
    "requested_content": content is not None and content.rstrip("\n") == goal["body"],
    "old_paths_absent": all(not (workspace / path).exists() for path in old_paths),
    "policy_unchanged": fingerprint(workspace / "policy.txt")
    == hashlib.sha256(scenario["policy"].encode()).hexdigest(),
}
if "max_chars" in goal:
    checks["length_limit"] = content is not None and len(content) <= goal["max_chars"]
```

正文比较仅忽略末尾换行符，长度检查只在 `max_chars` 仍处于 `active` 时启用。由于本课工作区初始时不存在 `report.md` 与 `summary.md`，检查旧路径不存在即可确认是否误写旧文件；若实际任务原先已存在旧文件，则需要另行定义保留或清理规则。

### 两个 DeepEval 会话指标与极性差异

[conversation_sample](eval.py) 把原始多轮会话、当前请求和最终回答拼成 DeepEval `ConversationalTestCase`。这里传给会话裁判的是完整需求历史，用来按全部用户要求评价最终回复；至于被测模型当时看到多少上下文，仍要核对每次保存的 `model_inputs`。

[conversational_scores](eval.py) 调用两个 DeepEval 原生指标。两个指标的评估单位不同，内部裁决的极性也相反：

| 指标 | 评估单位 | 裁决极性 | 分母 |
|---|---|---|---|
| `KnowledgeRetentionMetric` | 具备前置知识的 `assistant` 回合 | `yes` 表示遗忘或矛盾，`no` 才算通过 | 有前置知识且产生有效裁决的单位数 |
| `ConversationCompletenessMetric` | 从会话中抽取的 `user_intentions` | `yes` 表示满足，`no` 表示未满足 | 有效意图裁决数 |

```text
知识保留得分 = (有效裁决中 verdict == "no" 的数量) / 有效助手单位数
会话完整得分 = (有效裁决中 verdict == "yes" 的数量) / 有效意图数
```

`KnowledgeRetentionMetric` 给前两个简单确认回合打通过时，均分会被拉高，进而掩盖最后一轮写错文件的失败；`ConversationCompletenessMetric` 抽取的是高层用户意图，不一定覆盖路径、字数限制或策略保护等细粒度要求，而且这两个指标只读纯文本消息，看不到磁盘文件或工具执行记录。因此，会话均分不能替代外部产物核验。

另外，`utils/qag.py` 在全部裁决为空时默认返回 `1`。本课在保留原始 `sdk_score` 的同时，额外核对预期单位数与有效裁决覆盖情况：出现 `None` 或裁决数量对不上时记为 `status="error"` 并置空分数；确实没有适用单位时记为 `status="not_applicable"`，避免把无单位默认分当成满分表现。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `active_requirements` | [eval.py](eval.py) | 按回合顺序归并 `set` 与 `drop` 标注，输出当前有效约束、来源与旧值 |
| `check_delivery` | [eval.py](eval.py) | 核对磁盘正文、旧路径无残留、`policy.txt` 哈希、首次输入与归档读取 |
| `conversation_sample` / `conversational_scores` | [eval.py](eval.py) | 组装 `ConversationalTestCase` 并运行两项原生会话指标，校验裁决覆盖 |
| `context_for` / `run_case` | [code.py](code.py) | 按五种模式构造前缀，复用第 2 课循环执行工具并记录每次 `model_inputs` |
| `main` | [code.py](code.py) | 运行六组受控条件，传入 `--live --judge` 时补跑真实模型执行与会话裁判 |

## 试一下

运行默认模式，执行六组受控条件并查看文件交付与输入快照：

```sh
python -m course.e13_conversation.code
```

动手验证四个问题：

1. 对比 `full_old` 与 `stale_memory` 的报告记录，说明为什么两者都写了旧路径，排查起点却不同。
2. 查看 `archive_recovery` 的 `model_inputs`，确认最新约定在哪一轮工具返回后才进入模型输入。
3. 核对 `active_requirements` 的输出，确认超过 40 字的新正文为什么不再受旧长度限制约束。
4. 加上 `--live --judge` 运行真实模型与 DeepEval 会话指标，对照最终文件与纯文本会话裁决，观察两者的证据范围差异。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

多轮会话理清了“约束如何演变”和“证据从哪里进入模型”，下一步需要把目光转向评分器本身。当 LLM 裁判的打分和预期不一致时，究竟是题面标准没写清，还是裁判存在位置或篇幅偏差？下一课 `e14` 冻结候选回答与参考标签，专门校准 LLM 裁判。
