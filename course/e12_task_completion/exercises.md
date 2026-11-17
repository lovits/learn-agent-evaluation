# e12 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. correct 与 claim_only 最后都说“已完成”。指出两条运行中分别有什么证据，为什么最终回复不能决定任务成功。
2. hardcoded 恰好返回演示订单的650。再写一组输入，说明它违反哪条业务规则。
3. mutates_input 的金额都正确。为什么 DeliveryContract 仍应失败？如果把各子项取平均，会掩盖什么？
4. policy_changed 的计算完全正确。这个任务中的“不能改策略文件”应该是加分项，还是必须满足的条件？
5. equivalent_loop 与参考写法不同。为什么不应该用完整源码字符串相等判断它是否成功？
6. 对照 Task Completion 的 outcome、理由与独立观察。裁判给高分时，应该如何处理明确失败的硬条件？
7. policy.txt 的最终哈希不变，是否证明过程中从未被写过？程序通过四组输入，是否证明对所有订单正确？分别指出缺少什么证据。
