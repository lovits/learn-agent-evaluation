# 第2课参考答案

1. 先根据 run_id 找到实验，再根据工具 parent_id 找模型事件。该模型第 i 个动作对应 model-N:tool-i，原始 call 与工具 span 的 call 应一致。重复的 read_file 名字无法区分 a.txt、b.txt，也无法区分一次成功与一次报错。
2. denied 在权限层结束；invalid_arguments 在参数层结束，两者都不执行 handler。error 表示执行层失败，例如 FileNotFoundError 或 Bash 非零退出。timeout 单独记录。Bash 被第1课执行器阻断时还可能是 blocked，不能强行改成 ok。
3. 顺序或父节点错位触发 tool_result_order_or_owner；少了结果还会触发 missing_tool_result。内部一致性检查无法验证任意 stdout 的真实性。要结合独立文件状态、可信执行日志和任务合同。
4. 4.3.4 的 before validator 要求 tools_called 内元素已经是 ToolCall。restore_samples 先把嵌套字典恢复为对象。Ragas 多轮样本恢复 Human/AI/Tool 消息，call_id 留在 metadata。具体代码见 samples.py 和 test_e02.py 的 SDK 往返测试。
5. edit_file 找不到 old_text 时返回 error，不执行 write_text。路径在 permission 中先 resolve；指向工作目录外的链接会被拒绝。对应测试实际检查了返回状态和文件内容。
6. 例如开发集调普通单文件编辑，校准集加入多处同名文本和明确的 rubric，留出集使用独立的小仓库与需求。不能把同一题改个文件名就分到别的集合。本课另备有各2条校准和留出任务及验收标准，但没有运行，不纳入5条开发实验的成绩。正式项目应扩充任务族，校准阈值后冻结标准再跑留出集。

这组实验没有判断最终回答是否解释充分，也没有测工具路径是否最省。它验证固定任务状态、权限分支、轨迹关联和样本转换。后两项质量维度会在后面的课程展开。
