# e12 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. `correct` 与 `claim_only` 在运行结束时都回复了 `"已完成。"`。指出两条运行在工作区产物和探针证据上分别留下了什么，说明为什么不能靠最终回复判断任务成功。
2. `hardcoded` 恰好通过了演示订单 `650` 的计算。请另举一组 `cases` 里已有或自拟的订单输入，说明它是如何暴露硬编码实现的。
3. `mutates_input` 返回的四组金额全部正确。为什么 `DeliveryContract` 依然判它得 `0` 分？如果改用子检查通过比例来打分，会掩盖什么问题？
4. `policy_changed` 正确修复了 `billing.py`，只改写了 `policy.txt`。在任务评测中，“不得修改策略文件”应当设计成加分项，还是必须满足的硬约束？
5. `equivalent_loop` 的实现代码和 `correct` 完全不同，却同样拿到了满分。为什么不应通过源码字符串相等来判断代码修复是否成功？
6. 对照 `TaskCompletionMetric` 抽出的 `outcome`、`reason` 以及 `independent_observation`。当语义裁判给出了较高分数（如 `policy_changed` 得 `0.65`），而 `DeliveryContract` 为 `0` 时，应当如何处理最终验收结论？
7. `policy.txt` 最终哈希不变，能否证明 Agent 在整个运行过程中从未写入过它？通过四组探针，能否证明程序对所有合法订单都正确？分别说明还需要补充什么证据。

[参考解释](solutions.md)
