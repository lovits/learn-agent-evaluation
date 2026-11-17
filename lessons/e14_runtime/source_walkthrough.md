# 第14课源码导读：后台执行和调度交付

当前模块接入真实Agent，4条预声明运行与独立验收已经完成；数值与评分以运行附页为准。版本、所读方法及源码哈希见[e14-reading.json](../../references/e14-reading.json)。

## s11：后台任务先返回，结果后通知

Learn Claude Code固定版本用should_run_background检查bash的显式run_in_background布尔值，不根据install或test等词猜测。PreToolUse先执行权限判断，随后BackgroundManager.start登记状态并启动线程。原工具调用先收到含bg_id的占位结果；下一模型轮collect取完成队列，把输出作为独立task_notification放入上下文。占位结果已经闭合原调用，通知不复用原tool_use_id。

上游后台线程执行真正的Shell进程，退出0为completed，非零退出和执行异常为failed。超时用独立结果说明；POSIX进程组在超时、正常命令结束及运行时退出时清理。这是生命周期管理，进程另建session仍可能逃出原组，不能称操作系统安全隔离。后台结果不主动唤醒模型，下一次进入循环时才收集。

本课[background.py](background.py)保留显式启动、线程、真实进程组与单次收集，并分别记录completed/error/timeout，保存实际stdout/stderr、退出码、单调时钟及源码哈希。记录留在.background而不在消费后删除，便于独立验收回查；输出只保留前50000字符，并标明截断。close终止当前进程组并等待线程结束，不留下仍在工作的任务却宣称会话已验收。

后台收据包含initial_hashes与final_hashes。两者相等且等于当前文件哈希，才支持“这次执行对应当前版本”的有限判断。代码改动以后，旧测试通过结果不再是新版本的证据；两个端点哈希也不能证明测试期间完全没有改过再改回。正式任务应避免测试与其被测源码并发修改。

工具调用权限仍应在分发层先检查；底层Manager不承担用户授权判断。角色文件工具守卫和Lead Bash的边界继续沿用前课。当前基础模块不能在进程崩溃后恢复一个已经消失的操作系统后台进程，完整工作流续跑留综合课处理。

## s12：到点、收到与做完是不同状态

上游schedule_job验证五段cron，支持星号、步长、数字、范围和列表。分钟、小时、月必须匹配；日期与星期都有约束时采用OR语义。cron.py保留这组纯函数，导入不会启动线程。

poll_due_jobs发现到期后，先持久化pending_delivery和last_fired，再让任务进入内存队列。同分钟的last_fired与尚未确认的pending_delivery防止重复入队。队列处理线程通过agent_lock等待Agent空闲，而不是同时修改同一消息列表。

Agent取队列任务并把prompt交给模型；模型请求失败时撤回本轮注入并restore，成功收到响应后acknowledge。一次性定义此时删除，周期定义清除pending等待下次匹配。这里确认的是模型收到prompt，不是代码任务已经完成。

上游durable定义写入.scheduled_tasks.json，临时文件后replace；保存失败会回滚内存状态，不暴露未落盘的交付。重启恢复pending，但不补跑停机期间错过的分钟；进程关闭时调度线程也停止。崩溃发生在模型已接收、ack尚未保存之间时，重启可能再次交付，因此是至少一次。

本课[scheduler.py](scheduler.py)用显式poll(moment)提供受控时钟，测试真实执行状态转换而不等待一天。transaction保护当前实例的状态和队列，并在持久化失败时回滚；这不提供跨进程锁。损坏的持久记录抛出可见错误，上游则打印错误并跳过，二者行为明确区分。分钟标记包含传入时区偏移；没有替用户推断时区。并发用户回合的串行化与实时调度线程应由运行时接入，不能把纯状态模块当成常驻服务已运行。

## DeepEval：效率评分不负责验收产物

[Step Efficiency文档](https://deepeval.com/docs/metrics-step-efficiency)要求真实轨迹。固定llm路径先prepare_measure校验，再用Task(task字符串)从根用户输入抽取任务，将任务与执行树交给效率提示，返回EfficiencyVerdict(score浮点, reason字符串)。没有按“正确工具次数/全部次数”计算的确定性公式。strict_mode按阈值置零；调用方还应检查有限值和0至1范围。

提示刻意严格：重复检索、额外调用和与任务无关的润色会扣分。它明确排除正确性与完整性，因此少做但未完成的路径也可能拿高分。它不会自动测量真实账单或墙钟延迟，应用必须另外记录这些数据，并保留业务验收。

a_measure仍先await抽任务、再await评分；这与应用后台进程、不同样本外层并行是三个层次。不同eval_mode有不同模型与评分路径，本课固定llm，不能与hybrid/system_one混作同一实验。原生SDK采集、去重投影、固定内部绑定的边界沿用第13课，原始输入与执行证据仍须保存。

## Ragas：执行配置和模型客户端有层次

[Run Config文档](https://docs.ragas.io/en/stable/howtos/customizations/run_config/)区分modern collections的客户端配置与legacy RunConfig。当前固定版本RunConfig保存timeout、max_retries、max_wait、max_workers及seed；这些字段存在，不意味着给整个编程Agent安装了全局超时和重试器。

实际add_retry/add_async_retry用tenacity的stop_after_attempt(max_retries)，因此当前实现限制的是包含首次在内的总尝试数。wait_random_exponential配置重试等待，exception_types决定何时重试。这个包装器没有读取timeout来中断函数，超时由调用它的具体执行层处理。seed只初始化本地numpy RNG，不保证外部模型确定，也没有自动固定所有重试抖动。

本课[controls.py](controls.py)实际调用原生add_retry：第一次由讲师注入TimeoutError，第二次返回；没有请求模型。另一个真实函数在timeout字段为1时运行超过1秒仍返回，展示该包装器不自动执行这个字段。这些是原生SDK协议控制，不是供应商可用率实测。现代指标若用自定义传输适配器，必须以该适配器的真实超时/重试行为为准，不能声称client示例自动控制了它。

## Ragas：token聚合与费用边界

[成本文档](https://docs.ragas.io/en/stable/howtos/customizations/metrics/_cost/)使用TokenUsageParser把LLMResult转成TokenUsage。CostCallbackHandler.on_llm_end追加记录，total_tokens按模型聚合，total_cost再乘调用者提供的输入/输出单价。TokenUsage.cost在输出单价缺省时使用输入单价。固定回调在没有usage时直接取第一项，调用方要先处理空记录；多模型路径若漏价格，可能跳过该模型，调用方必须检查价格覆盖。

控制实验的1500输入、150输出token、模型名illustrative-model和单价都是讲师构造，实际运行原生聚合得到演示费用0.0036单位，真实账单保留null。它只解释公式和调用链，既不是当前市场报价，也不是Codex订阅账单。

正式Agent和裁判应分别保留真实返回的usage、缓存输入token、模型响应次数与失败请求。仅有HTTP成功响应的usage不能推断失败请求是否产生费用；模型ID或价格缺失时也不能填0。并行工具持续时间之和不等于端到端墙钟时间，缓存输入不能重复加进输入总量。当前网页的历史示例价格不用于本课实际费用。

## 当前运行时怎样接起来

[code.py](code.py)保留前课的e04执行循环、可恢复上下文与原生SDK层级，在本课会话快照加入通知和调度。修改局限在新课，没有改写已发布第13课的运行逻辑。当前任务只暴露文件/Bash/知识/MCP、todo和6个timed工具；第13课任务图与子代理代码仍保留，完整组合到第16课核验。

每个模型请求前先收集已经结束的后台任务，再poll受控时钟、take到期提示，把它们追加到可见消息之后，才记录model_inputs及原生LLM span输入。这样保存的请求与实际发送相同，而不是记录后再偷偷补消息。后台通知是参考数据，定时文本来自本次显式注册的授权任务；工具定义与任意资料都不自动提升权限。

模型请求失败会restore尚未确认的定时任务，response_received保持false；成功后先保存真实返回元数据，再ack。ack写盘失败仍会恢复队列并使当前回合异常结束，不能删掉真实成功返回的usage。一次性定义在模型收到时消失，后续后台命令必须另外完成并出现在通知中。停止时记录仍在运行的任务，close负责清理，但清理不把早停改成成功。

[tools.py](tools.py)以独立background_bash工具表达显式后台意图，区别于上游在bash参数中设置run_in_background；本课只允许声明的python3 slow_tests.py。参数按真正的number/integer/boolean校验，字符串false和bool冒充秒数会被拒绝；权限检查先于进程启动。advance_clock只推进本轮显式教学时间，不安装系统定时器、不等待真实一天。

[eval.py](eval.py)读取实际目录、原测试和运行时记录，沿用前课受限执行器对核心/入口分别执行22个保留输入。为复用原检查，业务源码在临时目录重新绑定执行；实际目录的额外文件、保护fixture、后台JSON、调度状态和报告快照另在原目录检查。这个临时重执行不是重新运行过去的Agent。

后台公开回归只有5个原测试，外部44次函数输入执行与之分开；保留条件是可查看的教学回归数据，不声称盲测。验收还核对事前计划、最终todo、父循环正常停止、所有通知进入成功收到响应的请求、旧收据/当前文件哈希、独立读取与后台待完成时间重叠，以及一次性prompt接收后是否真实再次执行。

[resources.py](resources.py)从成功收到的模型元数据聚合原始usage；字段缺失保留null，模型ID和真实账单缺少依据也保持未知。字面相同读取次数只是线索，不考虑源码版本就不能把它认作无用步骤。工具时间之和、后台时间之和与墙钟分别保存；应用、支持和裁判也分别记录。

## 评分投影会遗漏哪种上下文

本次4条真实轨迹的效率分均为0.25，但各自独立验收均通过；完整reason在运行附页。第一条轨迹中，检索输出在第4个实际模型请求（零基索引3）已变成带300字符预览的转存提示，随后模型通过read_file读取.task_outputs/53a74c5fe6e94b53b860ea1bc9423ecd.txt的0至2000字符。原生工具span仍保留原始全量返回。省去实际模型请求的评分投影因此不能完整表达“模型当时只看到了预览”；裁判把这次恢复读取列为冗余，需要结合model_inputs复核。

这不证明所有额外步骤都必要。失败路径探索、重复todo等还要分别检查目的与用户要求。也不应先改应用去追逐一个效率分；第15课将固定复核集、校准标准并保留分歧。
