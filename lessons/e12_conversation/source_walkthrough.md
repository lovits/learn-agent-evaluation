# e12 源码导读：什么被保留，什么被评分

[教材](README.zh.md) · [会话](code.py) · [压缩](context.py) · [记忆](memory.py)

## 三条数据线

`visible` 决定模型实际输入，`raw` 保留完整轨迹，`turns` 保存各轮源码快照。`run_turn` 只接入新增消息，并在返回时补上最后回复，再进入公开停止审查。

检查过去一轮的代码要使用当时快照，不能只读已经被后续轮修改的最终文件。快照重新执行用于检查行为，不代表重新运行了过去的 Agent。

## 压缩如何保护工具协议

上游 [s08](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/code.py) 包含转存、裁剪、旧结果压缩、模型摘要与超长补救。本课 `prepare` 沿转存最新结果、裁剪、转存旧结果、摘要的顺序处理。

`check_pairs` 防止孤立的工具结果。最新请求独立保留，最近闭合批次不被一条摘要替换。分页恢复继续经过工作区权限；offset 是字符位置，与上游按行参数不同。

`successful_request_text_ranges` 只在请求成功返回后累计暴露区间。`exposure.py` 检查实际送达文本，重复页只计一次。写盘或读取进程拿到全文，不等于模型收到全文。

## 记忆怎样跨会话

上游 [s09](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s09_memory/code.py) 用 Markdown、元数据和索引保存长期内容，还包含整理与回滚。这里保留候选提取、临时范围拒绝、去重、磁盘写入与版本过滤。

召回按词项和显式版本筛选，只有选中正文进入模型。候选仍是模型判断，过滤不构成真实性保证。新会话用新消息列表，证明召回并非偷偷延续旧上下文。

## DeepEval 知识保留

[指南](https://deepeval.com/guides/guides-multi-turn-evaluation) · [KnowledgeRetention 文档](https://deepeval.com/docs/metrics-knowledge-retention) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/knowledge_retention/knowledge_retention.py)

```text
非 assistant 消息 → Knowledge(data)
之前积累的知识 + 当前 assistant → 遗忘裁决
no 比例 → 分数
```

抽取提示支持用户修正事实，但多个旧知识字典仍可能同时参与判断。要查看中间提取结果，确认400替换300没有被误判成遗忘。

空有效裁决默认1；strict mode 在固定源码设阈值1。会话完整性使用另一条路径，参见[文档](https://deepeval.com/docs/metrics-conversation-completeness)与[实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/conversation_completeness/conversation_completeness.py)：先提取 intentions，再数满足意图的 yes 比例。固定实现未按 `window_size` 切窗口，参数存在不代表路径已使用它。

## Ragas 多轮样本与 rubric

[多轮应用说明](https://docs.ragas.io/en/stable/howtos/applications/evaluating_multi_turn_conversations/) · [dataset_schema.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset_schema.py) · [AspectCritic](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/_aspect_critic.py)

`MultiTurnSample` 保留 Human/AI/Tool 消息序列并检查调用配对。本课旧式 `multi_turn_ascore` 把会话文本送入多轮 prompt，标准写在 definition 中；固定路径没有自动使用 sample.reference。

`strictness=1` 对应一次结果，不能按参数名字推断独立投票数。DeepEval Turn 的角色为 user/assistant，工具细节另存；两框架会话投影的边界都要讲清。

## 模拟覆盖与任务质量分别看

[ConversationSimulator 指南](https://deepeval.com/guides/guides-multi-turn-simulation)说明生成用户与应用回调的连接。`simulate.py` 实际回调 `Conversation.run_turn`，再返回 assistant Turn；场景版本识别仅支持本课约定。

轮数上限、终止控制、场景覆盖和每阶段行为分别记录。若请求尚未提出，缺口属于模拟覆盖；若已经提出但代码违反，则沿 Agent 轨迹继续定位。模拟用户、摘要支持模型与目标 Agent 是不同角色，不应混成一次应用输出。
