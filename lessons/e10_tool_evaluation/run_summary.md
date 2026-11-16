# 第10课真实工具实验与评分解释

## 两条实际修复路径

在Docker内正式运行内置工具版与MCP能力版各一次。业务任务相同：读取calculate.py，按挂载合成文档把unit_price从7修成8，运行程序并保存实际stdout。MCP能力版另加明确的工具路由要求，因此这是接入能力演示，不是只改变一个因素的性能因果比较。

- 内置工具版：read_file → search_knowledge → edit_file → bash → read_file；状态finished，result.txt为'48\n'。
- MCP能力版：connect_mcp → mcp__docs__search → read_file → edit_file → bash → read_file；状态finished，result.txt为'48\n'。

两份实际脚本均以quantity=6、unit_price=8进行乘法并打印。断网verifier重读两份脚本和结果文件，每份7项合同检查通过；没有重新执行任意生成代码。正式应用共11份模型响应，工具快照与发现记录见[完整Agent报告](example_report.json)。MCP首轮可见7个名字，发现后为9个；模型只提交动作，工具在容器内执行。

上游s14与本课均使用进程内模拟MCP server。它调用真实只读知识库检索；未做stdio/HTTP线协议互操作。最初只有“启用MCP”而未明确能力路由时，两次运行都选择内置搜索并完成任务，未发生MCP发现。该轮已归档于generation/archive/e10-before-route-instruction；随后明确能力任务、真实重跑两版，不把原来的builtin搜索改标成MCP调用。正式前后代码与报告哈希分别保存。

## 构造轨迹与原生规则评分

11条明确编写的控制轨迹没有执行工具；两条真实轨迹另做三动作教学投影，保留原span与参数映射。13份输入各运行7种原生确定性配置，共91项分数。接口被配置为不请求模型，若发生请求会直接报错；不能把这91项说成91个模型判断或91次Agent任务。

| 控制轨迹 | Deep参数 | Deep排序 | Ragas严格 | Ragas F1 |
|---|---|---|---|---|
| perfect | 1 | 1 | 1 | 1 |
| wrong_order | 1 | 0.6667 | 0 | 1 |
| duplicate | 1 | 1 | 0 | 1 |
| extra_argument | 0.8333 | 0.8333 | 1 | 0.6667 |
| wrong_path | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| missing | 0.6667 | 0.6667 | 0 | 0.8 |
| both_empty | 1 | 1 | 1 | 0 |
| argument_type | 0 | 0 | 1 | 0 |

重复调用不会增加集合元素，所以F1仍1；严格列表因长度不同得0。额外参数被Ragas reference-key比较忽略，但实际read_file/MCP handler会拒绝不接受的字段。数值类型也可能被str比较掩盖。DeepEval非精确参数分按并集计权，对三个调用中单个多余键得到5/6。双方空调用原生F1为0，Accuracy为1；边界不同须按适用域解释。完整七列与warnings见[规则与产物验收](grade_report.json)。

真实核心轨迹的literal得分只针对被选出的读/改/跑投影。查询与最终回读被明确排除，原始全轨迹仍留存；write_file等合法替代路径不必与该literal参考相同。业务产物通过与单一路径匹配分分别判断。

## 两轮语义判分：修的是样本协议

首轮原生ArgumentCorrectness对裁成读/改/跑的MCP轨迹给2/3，理由是“未先连接并检索文档”。实际全轨迹已有连接和文档；错误来自评分输入删掉了依据。该轮6份实际模型响应保留在[首次投影评分](first_judge_projection_report.json)，不能抹去。

修订后，decision_contexts为每个有工具调用的model span恢复当时工具定义及此前messages；不注入该轮未来结果。Agent文件、运行与应用响应没有改动，只重新评分。最终原生语义阶段13份模型响应、14项metric结果，逐项verdict数与调用数一致。两个真实运行的9个非空决策轮、11次工具调用均被判yes；这些是自动判定，不是人工标签，也不证明普遍可靠。

构造perfect的ArgumentCorrectness为1，wrong_path为2/3；空调用直接得1且0次模型请求，仅表示无参数可判。ToolCorrectness另传available_tools后实际请求模型，perfect为1、wrong_tool为2/3，最后取确定性匹配与选择分的较小值。实际prompt、响应、每项输入和source_model_span见[最终裁判记录](judge_report.json)。两轮协议输入不同，分数升高不能说成Agent版本变强。

## 验收范围与复跑

单元检查覆盖工具发现、幂等连接、宿主策略、名字冲突、handler绑定、缺参/错参、真实挂载检索、原生指标边界、直线乘法、执行证据及决策上下文。明确拒绝cat文件冒充运行、用true掩盖失败、未来结果泄漏和只写print(48)的假计算。

重新运行Agent会覆盖runs/e10-agents.json，规则验收覆盖runs/e10-evaluation.json，裁判覆盖runs/e10-judges.json；比较前先另存。教材固定报告不会被这些入口覆盖。模型采样未固定，动作路径和请求数重跑可能变化。费用和确切型号缺失时保持未知；应用、规则指标、裁判及教材调用分开记录。最终测试与同步见[验收说明](../../docs/e10-validation.md)。
