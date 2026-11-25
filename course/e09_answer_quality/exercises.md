# e09 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. 对 `incomplete` 的 `{command}` 与参考 `{command, gate, fix}`，分别计算 TP、FP、FN、精确率、召回率和 F1。把 `beta` 分别改为 `2.0` 与 `0.5` 时，F-beta 如何变化？
2. `off_topic` 中的“审计日志保留 14 天”在知识库里完全属实，却在本题参考集合之外。出现 FP 能直接判定回答编造了假事实吗？如果参考集合本身漏掉了必要事实，计数会出现什么偏差？
3. `complete` 与 `unsupported_answer` 的回答文本完全一致，为什么 `task_metric`（`GEval`）给出截然不同的结果？应当查看样本里的哪个字段才能解释两者的差异？
4. `reasonable_refusal` 没有覆盖三个发布事实，依然在 `task_metric` 中得到满分。同样的一句拒答，在什么条件下应当判为 `0` 分？
5. 如果把正确规则“只有全部检查通过才能提交发布”改成“即使全部检查失败也能提交发布”，为什么字面相似度高或 `AnswerRelevancyMetric` 满分都不能用来验收发布答案？
6. 查看真实 Agent（`live_agent`）在 `AnswerRelevancyMetric` 下的 `statements` 与 `verdicts`。当一个回答切题性为 `1.0` 却漏掉了发布门槛时，应当补哪几类检查？

[参考解释](solutions.md)
