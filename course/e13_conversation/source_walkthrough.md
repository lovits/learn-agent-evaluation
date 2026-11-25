# e13 源码导读：会话、实际输入与有效约束

[教材](README.zh.md) · [上下文与执行](code.py) · [约束与会话评分](eval.py)

## 三份独立记录

[scenario.json](scenario.json) 保存了课程构造的多轮会话、两种预设摘要以及用户改口标注。用户先在 `u1` 约定写 `report.md`、短正文和 40 字上限，再在 `u2` 改成 `summary.md`、长正文并取消长度限制，中文与不修改 `policy.txt` 两项继续保留。

其中 `set` 和 `drop` 是附加在用户消息旁的真值标注，专供评分程序计算有效约束，不会写进 `conversation.json` 或发送给模型。[eval.py](eval.py) 中的 `active_requirements` 按顺序处理用户的增删标注，记录当前有效值、来源回合以及被覆盖的旧值，为这组教学场景提供确定的参考状态。

[code.py](code.py) 中的 `context_for` 决定每次运行前拼入什么上下文前缀：`full`（完整历史）、`tail`（空前缀）、`stale`（过期摘要）、`current`（当前摘要）或 `archive`（归档路径提示）。其中 `stale` 与 `current` 两种摘要均由课程预置，用来隔离“摘要信息是否滞后”这一单变量，反映的是输入信息完整度对执行的影响。

`next_response` 在每次调用模型前将选定前缀与本轮 `messages` 深拷贝并追加进 `model_inputs`。原始历史的存在代表档案里有记录，首次输入不含新路径也只说明起点状态，排查归档恢复过程时必须沿着后续每次 `model_inputs` 与真实工具返回逐轮追踪。

## 执行与归档恢复

本课的执行循环和文件工具继续复用第 2 课的 `agent_loop` 与 `TOOLS`。默认模式下，工具调用批次由 [cases.jsonl](cases.jsonl) 预设，文件读写和目录创建则在隔离工作区里真实执行；传入 `--live` 时，`live_full`、`live_tail` 与 `live_archive` 三组条件在相同前置历史下由真实模型自主完成最终轮次的决策与工具调用。

工作区初始化时生成的 `conversation.json` 只保留 `id`、`role` 与 `content` 三个字段，剥离了所有评分标注。构造样本 `archive_recovery` 将读取和写入拆分成两批工具调用：第一轮调用 `read_file` 读取 `conversation.json`，工具真实输出回填进消息队列后，第二轮模型输入才包含最新要求，继而写入 `summary.md`。

外部文件核对由 [eval.py](eval.py) 中的 `check_delivery` 完成：目标文件路径 `summary.md` 存在且正文与最新要求一致（忽略末尾换行符差异）、旧路径 `report.md` 下没有产物、`policy.txt` 的 SHA-256 哈希与初始值一致。已取消的 `max_chars` 不再进入 `checks`，`language` 要求则由精确中文正文比对直接覆盖。若实际业务允许自由改写正文，应改用对应的语义或结构判据。`policy.txt` 的校验复用第 12 课的 `fingerprint`，文件缺失或指向工作区外部软链接均判为未通过，它核对的是运行结束时磁盘文件的字节状态。

## Learn Claude Code：压缩保留什么，记忆何时读回

以下源码分析基于 Learn Claude Code 固定提交 [448c75b](https://github.com/shareAI-lab/learn-claude-code/tree/448c75bb596917ad196cc1fb7558f459c5c50fdd)。

- [s08_context_compact/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/code.py)：在请求模型前整理上下文，依次处理大工具结果转存、归档与裁剪，再按需生成模型摘要。被压缩内容保留可恢复的归档路径，摘要仅作为参考，同时确保工具调用与工具结果成对保留。
- [s09_memory/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py)：把跨会话信息存成文件，检索相关条目后再经 `load_memories` 与 `build_system` 注入上下文。历史记忆属于背景材料，与当前用户指令冲突时以当前请求为准。

本课提炼了评测最需要观察的接口边界：区分原始历史、实际输入、摘要版本与可恢复归档，避免把“信息已写入文件”直接当作“模型已经获得该事实”。

## DeepEval：会话样本保存用户与回复

以下源码分析基于 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)。

[ConversationalTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py) 通过 `turns` 列表保存对话，每个 `Turn` 记录 `role`、`content` 等字段。`conversation_sample` 把原始历史会话、当前轮次请求与 Agent 最终回答组装成规范会话样本。由于这里送入裁判的是完整用户历史，裁判了解全部改口需求，而当上下文被截断或摘要过时时，被测模型实际看到的可能比裁判更少。这份样本用来按原始需求评价最终响应，而不能反过来证明被测模型当时看到了相同上下文。

本课启用的两个原生会话指标只读取消息里的 `role` 与 `content`，不会去查看工作区磁盘文件或验证工具产物。工具事件轨迹、每轮 `model_inputs` 与最终文件核验都保存在外层报告中，与对话文本评分分开结算。

## DeepEval：Knowledge Retention 的 yes 表示遗忘

参考 [Knowledge Retention 文档](https://deepeval.com/docs/metrics-knowledge-retention) 与源码 [knowledge_retention.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/knowledge_retention.py)，本课固定采用 LLM 模式：

1. `_generate_knowledges` 遍历非 `assistant` 回合，结合此前对话上下文从当前用户消息中抽取结构化事实存入 `data`（模板见 [extract_data.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/templates/extract_data.txt)）。
2. `_generate_verdicts` 遍历 `assistant` 回合，把此前累计的非空 `knowledge.data` 列表交给裁判模型判断有无遗忘或矛盾；若某轮 `assistant` 回复之前没有任何抽取事实，则跳过该回合（模板见 [generate_verdict.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/templates/generate_verdict.txt)）。
3. 需要注意裁决极性：这里 `yes` 代表遗忘或与已知事实矛盾，`no` 才代表正确保留。重复追问已知信息通常判为遗忘，但合理的确认与澄清应结合上下文辨别。

在多轮改口场景下，原生源码是按回合累加此前抽出的全部事实，并未像本课 `active_requirements` 那样显式执行键覆盖与失效删除。当新旧规则先后出现在累计事实列表里时，必须打开抽取出的 `knowledges` 与逐回合 `verdicts` 核对裁判是否正确理解了修改关系。

`_calculate_score` 统计 `no` 在有效裁决中的占比。分母是具备前置知识且获得有效裁决的 `assistant` 单位数，不一定等于全部 `assistant` 回合数。由于前面的确认回合容易拿到 `no`（通过），即便最后一轮执行回复写错了目标路径，整体会话得分依然可能不低，因此不能拿它覆盖最终交付条件。

## DeepEval：Conversation Completeness 以意图作单位

参考 [Conversation Completeness 文档](https://deepeval.com/docs/metrics-conversation-completeness) 与源码 [conversation_completeness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/conversation_completeness/conversation_completeness.py)：

1. `_extract_user_intentions` 从整段对话抽取高层用户意图列表。
2. `_generate_verdict` 针对每条意图判断整段会话是否满足了该需求。与知识保留相反，这里 `yes` 代表满足、`no` 代表未满足。
3. 得分等于有效 `yes` 裁决占总意图的比例，分母单位是抽取出的意图条数，与消息回合数或约束字段数无关。

因为提示词模板强调关注整体意图，诸如精确正文、特定文件路径、已取消的字数限制或保护文件要求是否被抽进意图列表，都需要检查实际保存的 `intentions` 字段。本课设置 `include_reason=False` 省去最终总结请求，同时保留每条否定裁决自带的理由字段。

## 聚合逻辑与空单位处理

两个会话指标共用 [utils/qag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 中的 `score_qag_verdicts`：先过滤掉 `None` 裁决，再按各自极性统计通过占比；当有效裁决列表为空时默认返回 `1`。`strict_mode` 下的阈值判断以当前固定版本的源码行为为准。

为了避免缺失裁决或空单位被默认 `1` 掩盖，[conversational_scores](eval.py) 在保留原始 `sdk_score` 的同时，额外检查预期单位数与实际裁决覆盖：如果任一裁决为 `None` 或数量不等于 `expected_units`，将状态设为 `error`、分数置为 `None`；如果 `expected_units` 为 `0`，则记为 `not_applicable`。

原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[DeepEval docs](https://my.feishu.cn/docx/Ve2RdP0tyoPsumxuhnxcvsXuneD)。

[样本与评测记录](assessment.md)
