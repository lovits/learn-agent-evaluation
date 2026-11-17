# 第14课：后台、调度与效率，少几步就更好吗

当前为实施与写作约束，尚未生成教材，不能标为完成。沿16课既定大纲与统一正文标准制作；六个二级标题、六步真实短代码，约2000至3500汉字，细节移附页。PocketFlow实际运行后保留原稿，再技术审校与humanizer全篇通读。保留DeepEval/Ragas固定源码，不编造模型调用、定时触发或费用。

前课两个子任务同步运行，模型调用等待工具返回。当前课把明确请求的慢命令放入后台，先返回bg_id，后续模型轮注入独立通知；原始工具调用只有一次占位结果，通知不冒充第二条tool_result。权限与PreToolUse先于启动，不靠命令关键词猜后台。实际进程组正常/超时/退出清理，错误与超时分报；不是OS安全隔离。

后台状态、实际命令输出、开始/结束单调时间、通知投递与对应源码哈希单独保存；测试若在代码改动前运行，旧通过收据不能证明新代码。父循环正常结束但仍有待执行任务时不可判总体成功。只有真实进程执行才叫实测；讲师构造操作序列是协议控制，0模型调用，不冒称自主行为。

调度保留上游五段cron的*、*/N、数字、范围、列表及日/星期OR语义。定义/到期pending/模型成功接收ack与实际任务完成分开。持久记录先临时写再replace；到期前不投递，同分钟去重，模型请求失败恢复队列，重启恢复pending。至少一次交付的崩溃窗口仍可能重复，不能说exactly-once。进程关闭不再调度、不补停机错过分钟。受控时钟用于Docker有限实验，明确不是等待真实一天或生产调度可靠性。

正式实验在开始前冻结样本与步数/工具超时预算，按相同协议重复运行同一任务，不挑成功的一次。预声明至少3次同一正常任务，以及实际超时/有限重试/定时触发错误与边界控制。开始前完整列出成功条件：产物独立验收、任务/通知对应、终止状态、未运行和待交付状态不得伪成功。重复运行成功数/总数和每次错误全报；小样本不宣称稳定性已证明。若改协议必须另存，不能混成受控比较。

效率先记模型回合、工具次数、重复读取、超时/重试、墙钟/工具持续时间及实际usage。并行持续时间不可简单相加为端到端延迟；任务失败不能因步骤少而更优。应用、支持角色、裁判与教材生成分开计。缓存输入token保留，缺精确模型ID/价格时真实账单费用为null；演示价必须标讲师自定，不能用Ragas旧网页价格当现价。不能把字符预算当token或订阅额度费用。

DeepEval StepEfficiencyMetric使用真实SDK采集层级的去重投影，官方observe/evals_iterator与固定内部绑定分开；先从根输入抽Task，再直接生成EfficiencyVerdict(score,reason)，非自动1/tool_calls公式。固定eval_mode=llm、async_mode=False与阈值，额外检查有限0..1。模板刻意严格惩罚多余动作且排除正确/完整；高效率仍可能未完成。a_measure依赖顺序await，不等于后台应用任务或自动评测并发。

Ragas保留modern/legacy边界：modern collections重试/超时在实际client/adapter层，legacy RunConfig不是整个Agent全局调度开关。add_retry/add_async_retry的stop_after_attempt(max_retries)限制总尝试次数，含首次；单独timeout字段不被该重试装饰器自动执行。seed只给本地rng，不保证外部LLM确定。TokenUsageParser→CostCallbackHandler.on_llm_end→total_tokens/total_cost的分组和单价说明；空usage和缺模型价的固定版本边界需调用方先验，真实统计与构造费用算例分开。至少实际执行原生RunConfig有限重试控制与原生TokenUsage/成本聚合示例，清楚标0模型fixture；是否额外使用定制Ragas效率rubric以当前评测问题为准，不造同名原生指标。

六步带读预期：明确后台请求与占位；任务状态/进程组；后续轮单次通知和旧收据；cron到期与交付确认；可核查资源账本/原生效率裁判；独立产物与状态验收。一次性子任务、计划、权限、文件与可恢复上下文沿用已有课程；完整持久团队和工作流journal留第16课。所有实际运行、版本差异、来源与限制进run_summary/source_walkthrough，不写成正文数字报告。

本课正式定时实验仅暴露当前需要的文件/Bash/知识/MCP/todo与timed工具，未把第13课任务图/子代理混入同一测量；相应实现和独立课程仍保留，完整组合在第16课核验。正式协议已在references/e14-experiment-protocol.json冻结：3次同一正常任务与1次预声明超时恢复，20模型步，0.3秒教学延迟，正常5秒/故意首次0.05秒超时。先修代码，再后台回归+同一批独立读review，登记09:01持久一次性prompt，受控时钟推进60秒，模型收到后实际再次后台测试；实际文件、通知、收据、时钟、状态、计划/停止全部验收。


正文配图只用现有images/background-and-schedule.png，附同PNG放大链接和本项目GitHub的可编辑drawio图源链接。不要编造图片URL或指向PocketFlow仓库。节点9、边12，PNG为同图关系的本地预览，不是Desktop导出；制图过程留生成说明，不在主文讲作者工作流。

主文六步使用本课真实短代码：TimedPool.dispatch先查权限后BackgroundManager.start；execute的communicate超时和进程组清理；run_session在保存model_inputs前注入collect通知；Scheduler.poll/take/ack及失败restore；resources计数与StepEfficiencyMetric固定llm调用；grade_row核对真实文件/收据/通知/定时后执行。每段注明省略，不能拼出未定义变量的伪入口。代码输入/输出/接入点与一个具体失败解释都要讲清。

正文数字以最终run_summary为准，生成时若仍在运行，不能提前宣称四次全通过。三次正常路径的实测与故意超时恢复单列，接收ack不当任务完成，未完成的短路径不因效率高而通过。错误的镜像仓库超时导致旧镜像找不到模块，没有调用模型，属于环境准备错误，不计应用成功率。所有快照哈希和额外历史边界留附页，六部分主文集中讲原理。

试一下先在两个独立终端启动python3 tools/model_bridge.py（8766）与python3 tools/judge_bridge.py（8768），不要在同一阻塞终端串行启动。构建成功后再运行：docker compose run --rm -T --entrypoint python course -m lessons.e14_runtime.code；docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e14_runtime.controls；同verifier运行lessons.e14_runtime.eval；course运行lessons.e14_runtime.eval --judge。应用入口发现已有runs/e14-agent.json会拒绝覆盖，重跑须先另存原报告。知识库只读挂载、报告/工作区持久化、条件只给断网verifier，凭据留宿主。阅读http://localhost:8765/lesson14。主要报告e14-agent.json、e14-controls.json、e14-evaluation.json、e14-judges.json。观察后台ID何时变成真实结果、ack后实际多了哪条测试、旧收据为什么会失效三题。

附页明确链接source_walkthrough.md、exercises.md、solutions.md、run_summary.md、../../docs/e14-validation.md和../../generation/e14-README.md。接下来第15课：本课严格效率提示可能惩罚额外检查，也可能给少做的路径高分，如何用独立复核集校准裁判、检查偏差与中文标准。

最终已完成全部4条应用与独立验收：正常3/3，故意超时恢复单列通过，54次应用模型响应、4次摘要支持响应。原生StepEfficiency6输入实际12次成功评分响应、0错误，4条真实投影均0.25，构造未执行0，重复读0.25。正文不把低分当代码失败，也不声称少做构造案例本次拿了高分。源码附页记录原生全量工具结果与实际只发送预览的差异；恢复被截断结果可能被误判为重复读取，保留原始输入而不重测求高分。
