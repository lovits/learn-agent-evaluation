# e11 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. wrong_path 的工具名与参考相同。为什么常规参数匹配还能得到部分分数，而目标文件没有生成？
2. 对比 reordered、extra_read、duplicate_write。保持参考顺序的子序列，与长度、每个位置完全一致，分别约束什么？
3. tool_failed 参数完全匹配，实际写入却失败。哪个字段可以看出失败？输出比较和任务完成度又有何区别？
4. 任务允许 Bash 复制。为什么单一文件工具参考可能给它低分？该改参考、改指标还是禁止这条路线？先说明评价目标。
5. permission_recovery 中第一次 denied 是预期结果。如果只检查最终 status.txt，能否证明 Agent 没有尝试绕过？
6. Ragas ToolCallF1 遇到额外一次相同 read_file 调用，为什么不一定下降？要评价重复次数，应保留什么？
7. 没有调用时，Argument Correctness 原生值为 1。为什么不能由此认为该复制任务做得很好？
