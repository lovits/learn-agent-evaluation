# e13 样本与评测记录

[教材](README.zh.md) · [场景](scenario.json) · [控制条件](cases.jsonl) · [完整记录](assessment.json)

## 样本设计

[scenario.json](scenario.json) 构造了包含 `u1`、`a1`、`u2`、`a2` 的历史会话、两份用于控制信息可见性的摘要，以及供评分使用的 `set`、`drop` 标注。模型输入与工作区生成的 `conversation.json` 归档只保留纯对话文本，不包含任何评分标注。

[cases.jsonl](cases.jsonl) 定义了六组脚本决策条件，所有工具调用均在隔离工作区真实读写文件；加上 `--live --judge` 后，另由真实模型在相同前置历史下处理最终一轮请求（`live_full`、`live_tail`、`live_archive`），并运行原生 DeepEval 会话裁判。

## Docker 中的构造条件

默认运行编号 `a70c17d2872147e3979add1c620ef53d`，共完成六组真实文件执行，无模型请求与裁判请求：

| 条件 | 文件交付 | 首次输入含新路径 | 观察要点 |
|---|---|---|---|
| `full_correct` | 通过 | 是 | 完整历史下按最新路径与正文写入 |
| `full_old` | 未通过 | 是 | 首次输入已含更新，但脚本仍写旧路径 `report.md` |
| `stale_memory` | 未通过 | 否 | 首次输入只有过期摘要，按旧约定写入 |
| `tail_only` | 未通过 | 否 | 仅保留当前请求时主动回复澄清，未写文件 |
| `current_memory` | 通过 | 是 | 预设当前摘要保留了路径、正文与取消长度限制 |
| `archive_recovery` | 通过 | 否 | 先调用 `read_file` 读归档，下一轮再写入 `summary.md` |

文件交付检查核对最新正文、`report.md` 无残留以及 `policy.txt` 字节哈希不变；由于 `max_chars` 已被 `u2` 取消，超过 40 字的新正文不再触发长度限制扣分。`tail_only` 未完成文件交付，同时没有做出无依据写入，两项记录分别保留。

## 真实模型最终轮执行

运行编号 `677acb8edac74730b694d7a3dd6d85e1` 在 Docker 中完成了六组受控条件与三组真实模型最终轮执行：

| 条件 | 模型响应数 | 工具事件数 | 文件交付 | 本次行为 |
|---|---:|---:|---|---|
| `live_full` | 2 | 1 | 通过 | 直接写入最新路径 `summary.md` |
| `live_tail` | 5 | 5 | 通过 | 自主列出目录，读取 `policy.txt` 与 `conversation.json` 后写入并读回 |
| `live_archive` | 4 | 3 | 通过 | 按提示读取 `conversation.json`，写入 `summary.md` 并读回 |

`live_tail` 在初始上下文为空的情况下，通过列出工作区目录发现了 `conversation.json`，读回原会话后补齐了最新要求。`live_archive` 同样在 `read_file` 返回进入下一轮 `model_inputs` 后才写入正确路径。三组真实运行的最终正文与 `policy.txt` 保护条件全部满足，记录反映了这组构造任务下的执行路径。

## DeepEval 原生会话指标

同次运行共执行 30 次原生裁判请求，分别在 `full_correct`、`full_old` 与 `live_archive` 三组样本上运行 `KnowledgeRetentionMetric` 与 `ConversationCompletenessMetric`（其余条件未执行裁判，不保留会话分数）：

| 条件 | 知识保留 | 会话完整性 | 独立文件交付 |
|---|---:|---:|---|
| `full_correct` | 1 | 1 | 通过 |
| `full_old` | 2/3 | 1/3 | 未通过 |
| `live_archive` | 1 | 1/3 | 通过 |

每组样本的 `KnowledgeRetentionMetric` 均产生 3 个有效助手裁决，`ConversationCompletenessMetric` 均抽取出 3 条用户意图，所有中间抽取结果、逐项裁决与 `sdk_score` 保存在 [assessment.json](assessment.json) 中（`include_reason=False`）。

在 `full_old` 上，前两个确认回合未遗忘事实，最后回复旧路径被判遗忘，知识保留得 `2/3`；在默认 `threshold=0.5` 下，该指标给出了 `passed=True`，而外部文件交付实际未通过，说明会话指标的均分与通过标记不能取代最终产物检查。

## 一个证据范围分歧案例

`live_archive` 的工具事件记录显示，Agent 已经真实写入并读回了正确文件，最后按任务要求回复了最终路径 `summary.md`。然而 `ConversationCompletenessMetric` 只接收纯文本对话，裁判理由认为对话里缺少明确的写入声明或确认动作，将其中两条意图判为未满足，打出 `1/3` 分。

这个分歧源于评分单位与证据输入范围不同：纯文本会话指标无法看到工作区文件与工具结果。本课按原样保留了这次分数与否定理由，并把它作为典型分歧案例带入第 14 课，先核对指标应读哪些证据，再决定是否调整裁判提示词或样本字段。

## 软件检查与测试范围

单元测试（[test_conversation.py](../../tests/test_conversation.py)）覆盖了 `active_requirements` 的覆盖、取消与保留逻辑，六组受控条件的文件与输入快照差异，归档文件不包含 `set`/`drop` 标注，工具返回进入后续 `model_inputs` 的先后关系，`policy.txt` 缺失不被当作未修改，以及两个会话指标相反的 `yes` 极性与缺失裁决、空意图的异常分支处理。
