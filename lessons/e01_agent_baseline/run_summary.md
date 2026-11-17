# 第1课运行证据

本页保存与当前第1课实现对应的真实 Docker 运行记录，独立于教材正文。

[完整逐任务记录](example_report.json)保存任务、模型响应、Bash 事件、工作目录编号和评分结果。模型通过宿主接口给出动作，Bash 在课程容器执行；评分器在另一个无网络容器中读取记录和只读工作目录。

运行编号：`27884a167e1448f981e0e8e129b97bdc`；创建时间：`2026-11-17T15:29:59.565928+00:00`。

| 任务 | 循环状态 | 任务规则是否全部通过 |
|---|---|---|
| list_files | finished | True |
| create_and_run | finished | True |
| run_existing | finished | True |
| command_error | finished | True |

`command_error` 的目标是运行原脚本并观察指定错误，因此非零退出可提供正确证据。

另有明确标记的构造反例：没有 Bash 事件和文件，仅回复“已完成”；评分器拒绝接受。它用于检查评分逻辑，不属于真实模型任务的成绩。

这些任务验证当前教学链路，没有评价最终解释的语义、通用编程水平或费用。模型接口未返回确切模型编号时，记录保留为空；不推测身份或金额。

首次实现时的记录保存在 [历史证据](../../generation/archive/e01-before-outline-v2/example_report.json)。
