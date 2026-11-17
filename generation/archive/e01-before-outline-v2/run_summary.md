# 第1课原始实验记录

这是首次实现时已经保存的真实实验，不是本次文档改写新跑的成绩。原始[完整报告](example_report.json)保留不改。

| 任务 | Agent停止 | 独立验收 |
|---|---|---|
| list_files | finished | True |
| create_and_run | finished | True |
| run_existing | finished | True |
| command_error | finished | True |

原报告汇总为4条任务、4条通过、8次模型请求、4条Bash。不能从这四个固定任务推出通用编码准确率。

## 逐条检查什么

- list_files：真实Bash输出应包含alpha.py、notes.txt。
- create_and_run：成功输出包含Hello, World!，hello.py满足单条print的AST合同。自动断言只检查列出的证据，原实验另逐条复核了具体Python调用，不作为通用防投机执行证明。
- run_existing：成功输出为42，已有calculate.py的哈希保持不变。
- command_error：fail.py真实非零退出，stderr包含RuntimeError: demo-failure，脚本保持原样。任务目标是观察原错误，因此工具error与任务passed可以同时成立。

合成假完成记录没有Bash事件和文件证据，被验收器拒绝；它是验收器控制实验，不算真实模型的撒谎率。单元测试中的脚本化模型也不算真实模型成绩。

reported_model未返回时原样保留null；usage只记录CLI返回计数，没有确定计价时不编造费用。最终中文解释的清晰、完整和语义诚实程度，本课未评分。
