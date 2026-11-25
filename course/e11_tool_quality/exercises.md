# e11 练习

[教材](README.zh.md) · [参考解释](solutions.md)

1. `wrong_path` 调用的工具名与参考完全相同。为什么常规参数匹配还能拿到 `0.5` 分，而目标文件 `delivery.txt` 并没有生成？
2. 对比 `reordered`、`extra_read`、`duplicate_write` 三种情况：保持参考顺序的加权子序列，与长度、位置全部一致的精确匹配，各自约束了什么？
3. `tool_failed` 的参数与参考完全匹配，实际写入却失败了。从哪个字段能看到失败？工具输出匹配与最终任务完成度有什么区别？
4. 复制任务允许用 `bash` 完成。为什么以文件工具为参考的规则匹配会给它 `0` 分？遇到这种情况应该改参考、换指标，还是禁止 `bash` 路线？请先明确评测目标。
5. `permission_recovery` 中第一次收到 `denied` 是预期结果。如果只检查最终的 `status.txt`，能不能证明 Agent 没有用 `bash` 绕过权限限制？
6. `ToolCorrectnessMetric` 在非精确模式下遇到 `extra_read` 或 `duplicate_write` 时为什么依然能得 `1` 分？如果要约束多余或重复调用，应该怎么处理？
7. 当 `tools_called` 为空时，`ArgumentCorrectnessMetric` 的原生返回值是 `1`。为什么不能据此认为复制任务做得很好？
