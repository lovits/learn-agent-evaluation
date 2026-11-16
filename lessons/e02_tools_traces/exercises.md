# 第2课练习

先保留自己的运行报告，做完再看参考答案。

1. 对照一次 edit_and_run，找出每个工具的父模型、参数和返回值。说明为什么两次 read_file 不能只用名字关联。
2. 各写一条 denied、invalid_arguments、error 的记录。解释哪些状态真正进入了工具执行函数，哪些没有。
3. 复制一份报告，交换两个工具事件，再运行 trace_errors。解释报错依据。如果只改 stdout 字符串，内部关联检查能否判断它是真的？
4. 把导出的 DeepEval 工具字典直接载入 LLMTestCase，观察当前版本的报错。通过 restore_samples 重新加载四种样本，核对 denied 和 exit_code 没有丢失。
5. 为 edit_file 写一个 old_text 不存在的失败例，要求原文件内容不变。另写一个目录外符号链接例，验收文件工具拒绝访问。
6. 为五条 development 任务补一份真正的 calibration/holdout 设计。说明如何按任务族划分，以及什么时候可以查看留出集的详细结果。
