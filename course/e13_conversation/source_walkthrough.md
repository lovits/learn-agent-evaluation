# e13 源码导读：会话、实际输入与有效约束

[教材](README.zh.md) · [上下文与执行](code.py) · [约束与会话评分](eval.py)

## 三种记录不能合并

`scenario.json` 的原始会话由课程构造，前两次确认也不是实际模型回复。用户先约定 report.md、短正文和40字限制，后来改成 summary.md、长正文并取消长度限制。中文与 policy.txt 保护条件仍有效。

其中 set、drop 是课程作者对原话的显式标注，用于形成评分标准；它们不是模型抽取结果，也不会进入实际模型输入。`active_requirements` 只处理用户的这些标注，记录当前值、来源回合和被覆盖内容。它是一份小型参考状态计算，不是通用自然语言约束解析器。

`context_for` 决定实际模型可见的前缀：完整历史、只留本轮、过期摘要、当前摘要或归档提示。两种摘要均为作者构造的控制条件，不是模型自动压缩结果。不能用这些条件的得分证明一个自动摘要器好或坏。

`next_response` 将前缀与本轮 messages 合并后再调用模型，保存每次实际输入。原始会话留存不代表模型看到了它；首次输入不含新路径，也不表示之后没有通过工具读到。恢复场景需要继续追踪后续输入和真实工具输出。

## 执行与归档恢复

仍复用第2课 agent_loop、TOOLS 与执行器。脚本条件实际写文件，决策来自构造；--live 另外让模型处理相同历史下的最终请求。它不是从第一轮起由真实用户与模型共同生成的完整会话。

归档文件 conversation.json 只含 id、role、content，没有评分参考 set、drop。归档恢复先产生 read_file 事件，工具结果回填后才进入下一次决策。构造的 archive_recovery 也分成两批调用，没有在一次响应中先安排读取、又假装已经根据未知结果作出了写入决定。

外部文件条件要求最新正文写到 summary.md、旧路径没有产物、策略文件保持原字节。原样正文比较忽略末尾换行，不忽略正文差异。已取消的 max_chars 不再参与评分；language 由完整中文正文的精确比较覆盖。若任务允许自由改写，应另写相应语义标准，不能照搬这个字面契约。

policy.txt 的检查复用第12课 fingerprint，文件缺失或指向工作区外均不算保持原样。它仍是最终状态检查，不是完整写入审计。

## Learn Claude Code：压缩保留什么，记忆何时读回

固定提交 [448c75b](https://github.com/shareAI-lab/learn-claude-code/tree/448c75bb596917ad196cc1fb7558f459c5c50fdd)。

[s08_context_compact/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/code.py) 在模型调用前准备上下文。大结果转存、归档与裁剪先于必要时的模型摘要；被缩短内容保留恢复路径。active_request 与 Conversation summary 分开，摘要只作参考。裁剪还保护工具调用与结果的配对。

[s09_memory/code.py](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py) 将跨会话信息存为文件，先选择相关记忆，再通过 load_memories 与 build_system 加入上下文。记忆只是背景，冲突时当前请求优先。

本课只保留足够解释评测的机制：区分原始历史、实际输入、摘要版本与可恢复归档，不复制完整压缩管线或记忆平台。尤其不能因为“已保存到文件”就宣布模型已获得相关事实。

## DeepEval：会话样本保存用户与回复

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)。[ConversationalTestCase](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/test_case/conversational_test_case.py) 使用 turns，Turn 保存 role、content 等字段。

`conversation_sample` 将原始用户会话与最终回复组成规范会话样本。裁判因此看到全部用户要求，可能比被测模型看到的内容更多。这是按原始需求评结果；不能反过来用裁判输入证明模型实际看到了相同信息。

本课的两个指标只用 role、content 的消息表示，不读取实际文件，也不据此验证工具产物。工具事件与模型输入保留在 run，文件判断另列；没有把评分端观察伪装成模型说过的话。

## DeepEval：Knowledge Retention 的 yes 表示遗忘

参考 [Knowledge Retention](https://deepeval.com/docs/metrics-knowledge-retention)，源码 [knowledge_retention.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/knowledge_retention.py)。本课固定 LLM 模式。

`_generate_knowledges` 对非 assistant 回合抽取 data，辅助的 earlier turns 用于理解当前消息。`_generate_verdicts` 再遍历 assistant 回合，把此前非空 knowledge.data 列表交给裁判；此前没有事实时会跳过该 assistant 回合。

[extract_data.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/templates/extract_data.txt) 要求从最新用户消息提取明确事实；[generate_verdict.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/templates/generate_verdict.txt) 中 yes 表示遗忘或矛盾，no 才是通过。重复询问已知信息可能算遗忘，必要的确认与澄清则不应机械算错。

源码累计此前各次抽取的事实，并没有像本课参考状态一样显式执行键覆盖、失效与删除。新旧规则同时出现时，要检查抽取内容及逐回合裁决，不能仅凭指标名保证它总能正确处理版本变更，也不能假定用户改口必定被误罚。

`_calculate_score` 以 no 为通过项。只有具有前置知识并产生有效裁决的 assistant 单位进入当前实现的分母；它不一定等于所有 assistant 回合数。两个确认回合通过、最后执行回合失败，也可能留下不低的会话分，不能用它替代最终产物条件。

## DeepEval：Conversation Completeness 以意图作单位

参考 [Conversation Completeness](https://deepeval.com/docs/metrics-conversation-completeness)，源码 [conversation_completeness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/conversation_completeness/conversation_completeness.py)。

`_extract_user_intentions` 从完整会话抽取高层意图，再为每个意图调用 `_generate_verdict`。这里 yes 表示满足，与知识保留的极性相反。分数为有效 yes 比例，单位是抽出的意图，不是消息数，也不是路径等字段的个数。

模板要求关注整体意图。细粒度的正文、路径、长度取消和保护要求是否被意图抽取保留，仍需要核对。`include_reason=False` 省去最终总结请求，逐项裁决及其否定理由仍保存。

## 聚合与空单位

两个指标共用 [utils/qag.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py) 的 score_qag_verdicts。它剔除 None，再按各自极性计算通过比例；全部为空时默认返回1。strict_mode 的阈值行为以固定源码为准，不能把某些文档中知识保留阈值为0的文字直接当成当前实现。

本课保存 sdk_score，并额外核对预期单位数与裁决覆盖。缺失裁决或 None 记评分错误；确实没有适用单位时记不适用，而不是把默认1解释成已观察到良好表现。

## Ragas：多轮结构不是上下文恢复证明

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，参考 [多轮会话评测](https://docs.ragas.io/en/stable/howtos/applications/evaluating_multi_turn_conversations/)。

[MultiTurnSample](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py) 的 user_input 是 HumanMessage、AIMessage、ToolMessage 序列，可附 reference、reference_tool_calls 与 rubrics。验证器要求先出现 AI 消息，工具消息前一条为带工具调用的 AI 消息或另一条工具消息。这是角色顺序检查，不是调用ID逐一对应的证明。

这只验证消息结构，不证明模型运行时真的看到全部消息，也不证明后来创建的规范样本与实际输入相同。to_messages、pretty_repr 是表示转换，不是恢复被删上下文的操作。

[AgentGoalAccuracy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/agent_goal_accuracy/metric.py) 从工作流推断最终状态，有参考时与 reference 比较，无参考时与推断的 user_goal 比较，延续第12课的目标判断思路。它与逐事实知识保留、逐意图完整性不是同一个单位；也不自动读取最终文件。本课没有执行 Ragas。

原始资料：[DeepEval guides](https://my.feishu.cn/docx/RMSkdusn8oeS1XxCTp6cNAK6noc)、[DeepEval docs](https://my.feishu.cn/docx/Ve2RdP0tyoPsumxuhnxcvsXuneD)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对多轮记录、知识保留、会话完整性与样本结构；实际行为以固定源码为准。
