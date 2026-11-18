# e13: 用户改口后，哪条要求还有效？

[e12](../e12_task_completion/README.zh.md) → `e13` → [e14](../e14_judge_calibration/README.zh.md) → … → e16

> 先核对当前要求，再看它怎样进入模型的输入。

## 问题

用户先约定：写 report.md，正文不超过40字。随后改成 summary.md，换了正文，取消长度限制，但仍要求中文、不改 policy.txt。最后只说：“现在按最新约定写文件。”

如果 Agent 仍写 report.md，是忘了修改，还是根本没看到修改？只看最终回复，无法区分。

原始会话里出现过一句话，也不代表本次模型请求仍包含它。

## 解决方案

保留原始约定、每次实际模型输入与最终产物。用完整历史、过期摘要、当前摘要和归档恢复几个小场景，观察同一请求怎样执行。

![原始会话经过上下文选择后进入现有 Agent](https://lovits.github.io/learn-agent-evaluation/diagrams/e13-context-flow.svg?v=95b575b73552)

评分先核对最新有效条件，再检查文件。DeepEval 会话指标补充判断回复中的事实保留与意图满足。

![当前约束、会话裁决与实际输入分别帮助判断和定位](https://lovits.github.io/learn-agent-evaluation/diagrams/e13-conversation-scoring.svg?v=238759e90a95)

## 工作原理

### 用户修改的是部分要求

[场景文件](scenario.json) 为用户原话附上明确标注。这里省略正文，只看修改关系：

```json
{"id": "u1", "set": {"path": "report.md", "max_chars": 40}}
{"id": "u2", "set": {"path": "summary.md"}, "drop": ["max_chars"]}
```

set 新增或覆盖指定项，drop 取消指定项。没有被修改的中文与保护条件继续有效。

这些标注由课程作者提供给评分程序，不是模型抽取结果，也不发给被测模型。原始会话和前两次确认同样是构造材料；真实模型只负责最后的执行。

[active_requirements](eval.py) 按顺序归并标注，保留值与来源：

```python
active[key], sources[key] = value, turn["id"]
```

遇到取消项，就从 active 中移除。最终路径来自u2，保护条件来自u1，max_chars 已经不在当前状态里。不能继续用旧的40字限制扣分。

### 历史保存与模型可见是两件事

[context_for](code.py) 只决定本次附加什么前缀：

| 模式 | 起始输入 |
|---|---|
| full | 原始会话 |
| tail | 不附早期约定 |
| stale | 过期摘要 |
| current | 当前摘要 |
| archive | 归档位置提示 |

两份摘要由作者构造，用于控制信息是否保留；本课没有用它们冒充模型自动压缩的结果。

循环和工具仍复用第2课。真正调用模型前，把选定前缀与本轮消息组合：

```python
visible = copy.deepcopy(prefix + messages)
inputs.append(visible)
response = call_model(visible, tools=TOOLS) if live else next(scripted)
```

model_inputs 保存的是每次请求当时的快照。排查时读这一份，不能把事后组装的完整会话当成模型已经看过的内容。

### 文件归档只是恢复入口

Learn Claude Code 的上下文压缩会保留归档路径，记忆也要在相关时读回。本课只保留这个最小关系：conversation.json 保存原消息，模型通过已有 read_file 读取。

```text
归档路径提示
  → read_file(conversation.json)
  → 真实工具结果回填
  → 下一次模型输入包含原约定
  → 按最新修改写文件
```

归档只含 id、role、content，没有评分用的 set、drop。构造恢复场景也分两批调用，读取完成后才安排写入。

因此，首次输入没有 summary.md，只说明起点缺少它。后面可能通过检索或读文件补回来；需要继续核对每次输入。读成功也不代表一定理解正确，最终仍要看产物。

### 相同旧路径，排查顺序不同

full_old 在完整历史下仍写旧文件；stale_memory 起初只提供旧摘要。两者的文件条件都不满足，但前者应查更新后的约束为何没有落实，后者先查摘要版本与恢复路径。

`expected_path_in_first_input` 只做首次输入的字符串检查，不是完整语义归因。路径出现，不证明模型理解了覆盖关系；路径首次没出现，也不证明后来没有获取。

只剩当前请求时，澄清问题和主动查找归档都是可能的合理行为。不能预先断言截断一定导致猜测或失败。

### 评分按当前条件检查文件

[check_delivery](eval.py) 找到当前路径，比较新正文与策略文件，同时检查旧路径没有留下产物：

```python
checks = {
    "requested_content": content is not None and content.rstrip("\n") == goal["body"],
    "old_paths_absent": all(not (workspace / path).exists() for path in old_paths),
    # 另核对 policy.txt 的实际字节
}
```

正文比较只忽略末尾换行。若长度约束仍在 active 中才检查，已取消就不再适用。工作区原本没有 report.md 或 summary.md，本课据此检查路径更新是否落实；已有旧文件的任务需另定保留规则。

这些关键条件全部满足，文件交付才通过。它们与会话分分别记录。

### 两个会话指标，两个评价单位

`conversation_sample` 用原始会话、当前请求和最终回复构造 DeepEval ConversationalTestCase。裁判看到的是完整约定，可能比被测模型最初看到的更多；它用来评价回复，不用来证明模型输入的范围。

Knowledge Retention 先抽取此前事实，再判断后续助手回复有无遗忘。这里 yes 表示遗忘或矛盾，no 才通过。分母是具有前置知识、得到有效裁决的助手单位。

Conversation Completeness 先抽取用户意图，再判断每个意图是否满足。这里 yes 表示通过，分母是有效意图裁决。

```text
知识保留：没有遗忘的有效助手单位 / 有效助手单位
会话完整：满足的有效意图 / 有效意图
```

先前两个确认回合都通过，可能稀释最后一次执行失败。高层意图抽取也可能遗漏某个细节；不能用会话平均分覆盖真实文件的关键失败。

原生指标会跳过没有前置知识的回合，也可能丢弃无效裁决。本课保存抽取内容、逐项裁决和 sdk_score，另外核对覆盖；缺失裁决记评分错误，没有适用单位记不适用。

Ragas 的 MultiTurnSample 与目标评测帮助理解消息顺序、工具结果和目标来源。本课只读这些原理与源码，不再重复运行第二个框架。

## 本课变化

只增加上下文前缀、最小归档恢复、带来源的参考约束和两种原生会话指标。Agent 的工具与循环没有新增能力，不建设完整记忆平台。

## 试一下

```sh
python -m course.e13_conversation.code
```

1. 对照 full_old 与 stale_memory，先找实际输入，再找错误写入。
2. 看 archive_recovery 的读取结果在哪一次请求进入模型。
3. 确认新正文超过40字时，为何不应继续受旧限制约束。
4. 加 `--live --judge`，逐次核对模型输入、归档读取、最终文件与会话裁决。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

约束和证据范围理清后，还要问评分器有没有判错。下一课固定候选回答与标注，检查裁判的误接收、误拒绝和偏差。
