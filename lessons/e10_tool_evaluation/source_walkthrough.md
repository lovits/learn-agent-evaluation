# 第10课源码导读：工具匹配与真实执行

本课新增动态工具池与工具评分，继续使用第4课已经讲过的循环、权限和消息回填。完整调用仍是模型给动作、Docker运行工具；模型本身不执行宿主机命令。固定版本与实际读取文件哈希见[阅读记录](../../references/e10-reading.json)。

## Learn Claude Code：先发现，下一轮再可见

参考固定提交`448c75bb596917ad196cc1fb7558f459c5c50fdd`的[s14教材](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s14_mcp_plugin/README.zh.md)与[代码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s14_mcp_plugin/code.py)。上游本章本身采用进程内模拟server，没有实现MCP线协议。本课保持这个教学范围，不把函数调用说成实际stdio/HTTP互操作测试。

MCPClient保存工具定义与handler。connect_mcp只允许连接宿主配置中的docs；首次连接保存发现记录，再次连接不重复注册。ToolPool.assemble每轮重新组合既有工具、连接入口与已连接工具，将server的inputSchema转换为模型侧input_schema。

模型看见mcp__{server}__{tool}，运行时仍按原server名和工具名调用。名字先规范化，再检查冲突和64字符上限；不允许两个不同来源悄悄合并。绑定从运行时字典取出client和raw，参数字典不能覆盖这两个局部变量。

HOST_POLICY来自课程运行时配置。server的description或readOnlyHint只能描述接口，不能授予权限；未知策略要求批准，批量实验默认不批准。输入缺参、类型错误或未知参数停在工具边界，错误tool_result交回循环。MCP只是另一种工具来源，原有Hooks和记录方式保留。

首轮工具池中有connect_mcp而没有mcp__docs__search。连接动作执行后，下一轮模型输入才出现后者；tool_snapshots与每个model span编号能核对这一点。新增工具的schema、运行时授权和handler结果是三个不同对象。

## DeepEval ToolCorrectness：配置决定比较的是什么

依据[官方入口](https://deepeval.com/docs/metrics-tool-correctness)及固定提交`34db63dd005ebc9a905c8ef4741ae0687c93c14c`的[实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/tool_correctness/tool_correctness.py)。本课四种确定性模式都调用原生measure，显式固定eval_mode=llm；自定义接口在被请求时直接抛错，证明这些配置不需要模型。

- 默认按名字和类型匹配预期调用；同名但参数错也可能满分。没有available_tools时，选择最优工具的模型检查不运行。
- evaluation_params加入INPUT_PARAMETERS后，非精确模式用递归字典比较：匹配值按双方键的并集计权，额外键会降低分数。可以另选OUTPUT检查返回值，本课未将其启用。
- should_consider_ordering使用加权最长公共子序列，再除以预期调用数。顺序错误可以部分得分，额外预测调用未必降低该覆盖分。
- should_exact_match要求列表长度、位置、名字和类型完全相同，再检查配置指定的参数/输出；它优先于ordering。

在线页有把分母写为实际调用数的概括；本课固定实现的非精确和排序分支使用预期调用数。重复预测一次仍可能得1，不能把这一分数理解为同时处罚冗余的precision。strict_mode是阈值二值化，不等同于should_exact_match；默认阈值也不是业务成功标准。

本课实际调用同步measure(async_mode=False)。原生a_measure保留相同确定性匹配，在需要选择分时await对应模型请求；Ragas使用原生ascore协程，本课由asyncio.run逐项运行。异步入口与并发吞吐不是同一回事，本课没有进行异步加速实验。

传available_tools后，原生_get_tool_selection_score通过模板与ToolSelectionScore schema请求模型，最终取匹配分与选择分的较小值。本课另外实际运行这条分支，保留请求与理由；它和不传available_tools的确定性结果分别记账。

## Ragas：序列匹配和集合F1不是同一个合同

固定提交`8c63f10d500c44efbf24fdb9e2920de2104c321c`；使用[官方工具评测入口](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)中的collections API，而非旧MultiTurnSample接口。

[ToolCallAccuracy.ascore](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/metric.py)先从AIMessage抽出调用。strict_order比较完整名字序列；flexible先按工具名与参数键排序，再比较排序后的完整名字序列。列表长度不等时仍不对齐，因此本次重复/漏调场景最终为0；不要仅按docstring中的coverage描述推断会得到部分分。

名字序列对齐后，[exact_match_args](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_accuracy/util.py)只遍历reference的键，并用str(value)比较，再除以reference键数。多余预测键可能不扣分；整数42与字符串"42"也可能被判相同。因此名字序列通过后仍可有参数部分分，它并非始终二值。schema类型和handler是否接收必须另查。

[ToolCallF1](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/metric.py)把名字与完整参数通过[递归可哈希转换](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/tool_call_f1/util.py)放入集合。TP是集合交集，FP是多余调用种类，FN是缺失调用种类；precision=TP/(TP+FP)，recall=TP/(TP+FN)，F1为调和平均。它忽略顺序和相同调用的重复次数。重复次数、失败重试与成本不能交给集合F1负责。

本次双方空调用时，原生ToolCallAccuracy返回1，原生ToolCallF1返回0；第3课自写集合F1选择空/空为1，是另一条明确声明的约定。没有应调用工具的任务应单列适用域，不能因为名称都叫F1就混用边界。

## ArgumentCorrectness：输入需要保留决策时的证据

[官方入口](https://deepeval.com/docs/metrics-argument-correctness)与固定[实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/argument_correctness.py)：metric根据input和tools_called判断参数是否合适，不需要expected_tools。生成模板要求Verdicts列表，每项为yes/no及可选reason；_calculate_score调用score_qag_verdicts统计yes比例。本课固定同步LLM模式并关闭额外总理由请求，逐条判定理由仍保留。

[通用QAG聚合](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py)按有效verdict数计分；无效判定在相应解析路径可能被丢弃。因此本课另外核对verdict数量与输入调用数，不把缺失项自动当成已判正确。空调用在本版本measure中直接得1且不调用模型，它只说明没有参数可判，不能推出任务完成。

原生[trace适配](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/argument_correctness/utils.py)会把工具归属到选择参数的LLM span：父节点是LLM则用父节点，否则取同级先前最近的LLM。工具span可使用该LLM的input；已有显式tools_called时优先保留。

本课e04事件已经有parent_id，所以decision_contexts按模型轮次恢复当前tools与此前messages。先将上一轮真实工具结果回填，再构造本轮评分输入，最后才追加本轮assistant与未来结果。这样既保留连接、文档和文件证据，也不把尚未发生的结果泄漏到之前的决策。

第一轮曾把真实轨迹裁成“读、改、跑”，却仍拿要求MCP的完整任务判参数。模型因此认为没连接/检索，将真实成功的编辑判错。该轮保留在[first_judge_projection_report.json](first_judge_projection_report.json)；修订只改评分协议，没有修改文件或重跑Agent。最终结果见[运行摘要](run_summary.md)。

## 三种输入与多个合法路径

micro_traces.json中的错误路径、顺序、漏调、重复、额外参数和空调用都是明确编写的控制轨迹，没有实际执行。两份真实Agent报告则保留原始events、可见工具快照、文档检索、文件文本和模型usage。

确定性SDK对真实轨迹只做三动作教学投影：保留read/edit/write/bash尝试，省略文档查询与最终result.txt回读，保留source_span映射。其literal参考只是一条写法，不能据此判断整项业务。语义ArgumentCorrectness改用完整的每轮决策上下文。SDK样本的actual_output序列化当前被评分调用，它是组件投影而非最终业务回答；原始全轨迹始终留存，权限、错误和次数另报。

真实任务验收读取文件和已有执行证据，接受字面量相乘、变量相乘和命名中间结果等直线整数乘法；不强制只能edit_file，write_file修成同一合同也可。执行证据限定为成功的直接python调用、输出重定向或tee写法，不能把cat文件或用true掩盖失败当作运行成功。它不重新运行任意生成程序，也不声称证明带函数、导入或副作用的任意Python程序等价。更完整的代码任务验收在第11课继续。

工具名匹配、参数schema、模型认为参数合理、运行时放行、工具执行成功和任务完成应分开报告。工具F1高不能证明文件正确；业务通过也不意味着每次工具选择都高效或符合策略。
