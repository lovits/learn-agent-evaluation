# 第10课验收

## 真实Agent与原生指标

正式两种能力任务在Docker运行，均真实修改calculate.py并保存stdout为48。MCP能力任务实际连接docs、下一轮发现并调用mcp__docs__search。业务要求相同，但MCP版新增路由要求，因此不作受控性能比较。原先启用但仍使用builtin的运行保留，未改名冒充MCP。

复用已讲过的e04循环、原生文件工具、权限与hooks；本课只加入进程内模拟MCP工具池，按上游s14保持教学范围。名字冲突、handler固定绑定、输入错误与宿主策略均有验证；未实现MCP线协议互操作。

11条构造控制与2条真实核心投影产生91项原生规则分数；这些配置禁止模型请求。SDK边界包括重复、乱序、额外参数、类型与空调用。两份真实产物每份7项合同检查通过，verifier只读文件和已记录执行证据。

## 评分协议修订

首次把MCP轨迹裁成读/改/跑后判语义，遗漏连接与文档信息，导致2/3误判；原始6份模型响应保留。修订按model span恢复当轮工具与过去消息，排除未来结果，仅重新评分。最终13份模型响应、14项结果，9个真实非空决策轮的11个调用均为yes，verdict数量与输入调用数量一致。自动标签不作为人工标签或业务状态事实。

[完整Agent报告](../lessons/e10_tool_evaluation/example_report.json)、[原生规则与产物检查](../lessons/e10_tool_evaluation/grade_report.json)、[两轮裁判](../lessons/e10_tool_evaluation/judge_report.json)、[首次误判](../lessons/e10_tool_evaluation/first_judge_projection_report.json)及[镜像/源文件哈希](../lessons/e10_tool_evaluation/runtime_evidence.json)分别保存。

## 教材与发布核验

PocketFlow实际生成正文，技术审校核对API、代码摘录与报告；humanizer保护代码、命令和链接后润色。主文六部分及六步关键代码，源码导读、练习、答案和原始记录分开。一张动态工具池图有可编辑源与检查过的PNG。

本地与Docker断网各110项测试通过，保留1条既有DeepEval DAG弃用提示；Ruff通过。阅读器本课七条路由实测HTTP 200，PNG通过图片入口返回，整站页面与本地链接检查通过。GitHub CI按发布提交记录；飞书创建后核对六部分、代码、图片与附页，结果保存在references/feishu-e10.json。
