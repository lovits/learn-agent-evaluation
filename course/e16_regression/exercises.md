# e16 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. 独立行为检查 `inspect_delivery` 全部通过，但 Agent 的最终回复只写了“已完成。”，漏掉了任务要求说明的修复细节。这种情况下任务算完成吗？行为与说明两类证据分别来自哪里？
2. 查看 `tool_events` 时确认 Agent 已经成功调用 `search_knowledge`，但上游摘要型裁判却在理由里写出“未确认查询规范”。此时应该先修改 Agent 提示词，还是先核对裁判的输入证据与评分范围？
3. 候选版本在 `quantity` 和 `preserve` 两题拿到满分，但在 `empty` 一题修改了受保护的 `policy.txt`。如果按平均分看依然很高，`gate` 应该给出什么裁决？
4. 某次回归运行中，一条样本遇到评分接口超时报错，另一条样本则是候选代码算错了空订单金额。为什么 `gate` 要把这两种情况分别判为 `blocked` 和 `reject`？
5. 两个版本在 [cases.jsonl](cases.jsonl) 的三道公开回归题上全部通过，能否据此宣布候选提示词 `REPAIR` 显著提升了 Agent 质量？接下来需要补充哪些验证材料？
