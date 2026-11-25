# e02 练习

1. 跟住 `copy` 任务的一次完整运行，找出模型提出的参数、工具实际返回和落盘文件。这三份信息分别保存在哪里？
2. 同样调用 `write_file`，一次写入工作目录内，一次尝试写入目录外。转换成 DeepEval 的 `LLMTestCase` 后，从哪个字段可以区分这两次结果？
3. 分别用 `read_file` 读取不存在的文件，以及用错误参数调用 `read_file`。对比记录里的 `error` 和 `invalid` 两种状态有什么不同。
4. 如果从 `LLMTestCase` 中删去 `tools_called`，只保留 `input` 和 `actual_output`，还能判断哪些动作真正执行过吗？
5. 假设模型不调用任何工具，直接回复 `"完成"`。此时导出 `LLMTestCase` 能否成功？[eval.py](eval.py) 的任务检查又会给出什么结论？

[参考解释](solutions.md)
