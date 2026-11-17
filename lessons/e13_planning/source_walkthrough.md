# 第13课源码导读：计划、依赖和结果各回答什么

固定版本、所读符号与文件哈希见[e13-reading.json](../../references/e13-reading.json)。本课沿用Learn Claude Code固定版本，实际分析s05清单、s10任务依赖、s06独立子循环以及s13的认领与邮箱片段。大文件哈希用于识别版本，不等于声称逐行读完全部框架源码。

## 先区分三种判断

计划质量问“照这份计划做，能否完成要求”；计划遵从问“实际动作是否遵循声明的计划”；业务验收问“两个API最终是否满足合同”。好计划可能没执行完，坏计划也可能被完整执行；三种结论要分别保留。

本课延续v3运费规则，新增checkout.quote。初始shipping.py仍有开始计费档位错误；checkout.py调用shipping_fee时漏传expedited。任务要求保持两个签名、6000上限、400加急费及原测试。核心组件改好不代表入口转发也正确。评测不要求唯一工具序列，但必须满足用户明确要求的先声明计划、建立依赖、分别委派和实际验证。

## s05：显式清单和提醒

上游TodoManager.update先解析整个输入，验证后才替换items。它接受列表、JSON字符串以及通过ast.literal_eval解析的Python列表表示；最多20项，同一时刻最多一个in_progress。上游允许空列表清空清单，并把content/status转换成字符串。本课教学工具收紧为非空结构化JSON数组、明确的content/status字段及字符串值；这是接口适配差异，不声称所有输入形式完全相同。

本课[state.py](state.py)同样先检查整个列表再替换，避免后半条出错时前半条已写入。todo_write更新的是声明状态，不执行代码，也不证明步骤完成。初期多层JSON字符串的运行曾产生参数尾部多余文本，严格解析拒绝后模型反复更新清单。当前宿主输出schema按工具定义生成类型分支，规划字段直接使用数组；宿主只规范化一次为旧循环的arguments_json。原始wire_reply与规范化结果都保存，不把无效参数截断成“可用JSON”。一个没有调用todo_write的工具批次记一轮，连续三轮后向模型输入追加reminder；单轮调用四个工具仍只算一轮。它是明确的运行时消息，不伪装成工具执行结果。

## s10：任务记录与依赖转换

TaskStore把每条任务写进.tasks/task_*.json。先创建节点、拿到真实ID，再添加blocked_by边；同一模型回复中的兄弟工具请求还不知道彼此尚未产生的返回值，因此不能引用虚构ID。

add_dependencies只允许修改pending且无人认领的节点；先验证依赖存在和无环，再一次保存。claim在同一RLock中读取状态、检查所有依赖completed、检查owner没有另一项进行中任务，再更新owner/status。重复认领和未满足依赖会拒绝。TaskStore.complete只允许当前owner把in_progress改成completed，事件命名complete_claim。角色工具层提交task_complete时，先运行其分配组件的8个公开输入与原测试字节保护；失败保持in_progress，证据完整保存。核心组件通过时，不要求尚未执行的入口组件也已修好；最终两个API仍交给独立保留输入检查。公共检查失败会把真实案例、检查项或执行器错误反馈给模型，保持in_progress；公共通过支持局部完成声明，不能证明整项目正确。工具明确返回whole_project_assessment=not_assessed，表示尚未评估整体；它不等于已知失败。实际四文件哈希与原测试哈希一起返回，父端可结合真实测试检查保存状态。

状态先写临时文件再replace，防止单条记录半写；所有角色共享一个TaskStore实例及锁。本课锁保证单进程线程内原子认领，不是跨进程分布式锁。新建Store能读回持久记录；完整跨进程协调和工作流恢复仍在综合项目核验。路径与符号链接检查避免任务和邮箱逃出工作区。

独立验收重放task_events，检查每次claim之前依赖是否已有完成记录，再比较最后事件状态、保存的任务表与实际磁盘记录。否则直接改任务JSON就可能制造一张全部completed的表。事件顺序属于调度证据，文件执行结果仍另验。

## s06：新消息列表不等于独立文件系统

上游run_subagent创建全新messages，只提供BASE_TOOLS，没有task工具；它和父循环共享工作目录，最后只返回文本。因此隔离的是会话上下文，文件副作用仍可影响整个项目。

本课[code.py](code.py)保留已有e04循环，沿用e12可恢复压缩，当前规划协议使用30000字符预算、50条消息触发snip，20模型步上限不变。旧5000字符/16消息是压缩演示压力配置，旧运行分开保存；协议变更不作为受控性能比较。run_child把任务说明和显式prompt组成新请求，不自动复制父历史。子Agent没有task、创建节点或改依赖工具；其初始消息、实际模型输入和完整子轨迹保存，便于核对交接信息来自哪里。父Agent仍需明确传递接口约束，或让子Agent查询挂载知识库；上下文新建不能保证交接内容完整。

角色文件守卫只允许子Agent通过专用工具修改分配到的shipping.py或checkout.py。Worker Bash只开放声明的unittest命令（包括两个模块的组合）；Lead保留原Bash能力。专用修改工具在共享锁内比较任务开始时的文件哈希，写入成功后更新该角色预期哈希；已完成或不属于当前角色的任务不再允许修改。两个角色拿到同一旧版本时，后写者会收到stale拒绝，需重新审查和分配。它不是完整Git合并或操作系统文件隔离，Lead Bash也不受这套专用工具的哈希锁约束。可选worktree与持久队友生命周期留到综合项目。

## s13：一处消费结果邮箱

MessageBus把带sender、recipient、task_id和status的结果写入.mailboxes/*.jsonl，consume读取后删除文件。父循环只有一个运行时消费者，在下一次模型调用前把真实结果作为数据注入上下文；模型不用轮询邮箱。

task工具返回任务ID、角色与交付状态，具体子任务摘要由运行时邮箱投递。这样可以追踪一份摘要何时送达，也能检查第二次消费为空。摘要仍然是子Agent的声明；要结合真实工具事件与文件结果。本课是同步的一次性子任务加最小协作接口，未实现s13完整的持久队友WORK/IDLE、主动认领、审批协议、关机和worktree管理。

## 原生轨迹：记录实际发生的嵌套

[Plan Quality官方文档](https://deepeval.com/docs/metrics-plan-quality)和[Plan Adherence官方文档](https://deepeval.com/docs/metrics-plan-adherence)推荐observe/evals_iterator的轨迹评测。本课实际用@observe标记agent、llm、tool三个层次，并用update_current_span显式写输入、输出和角色。task执行期间调用子run_session，所以父工具span下会出现真实子Agent及其模型/工具span，而非事后拼装的假调用树。

Lead入口保存当前Trace对象引用；装饰器退出后，同一个对象已带结束时间和完整子树。对象使用Pydantic model_dump(mode="json")导出；固定版本的get_trace_dict仍调用dataclass工具，不能仅依据它的返回类型注解就假定拿到普通JSON字典。回归检查实际运行原生SDK、确认关闭时间及父子UUID，并验证整份含ToolCall对象的报告可序列化。

native_deepeval_trace保留完整原生对象。native_metric_trace使用SDK自己的create_nested_spans_dict，和固定trace_scope/agentic评测路径相同；该转换去掉UUID、时间、状态和metadata等字段，保留嵌套输入输出。返回字典内仍可能包含ToolCall模型，写报告前沿用SDK的serialize_to_json转换，再解析成普通JSON数据；只检查外层是dict会漏掉这种嵌套对象。回归测试实际放入原生ToolCall，验证整份报告可以序列化。评分投影进一步省去LLM节点中重复的整段请求历史，但保留其真实回复及工具参数/结果；原始请求仍在报告，不把投影称为未经变动的完整trace。

低层measure演示把上述投影绑定到固定版本LLMTestCase._trace_dict；这是自动observe/dataset流程通常负责的内部绑定。它依赖固定版本，不是建议在其他版本直接依赖私有字段。官方自动评测入口与本课分开运行应用和裁判的调试方式要区分。

SDK的SUCCESS主要表示被观察函数正常返回，不等于业务任务成功。循环捕获模型错误后也可能正常返回一个model_error结果；必须继续检查业务状态与独立产物。

## DeepEval：质量与遵从的调用链

| 阶段 | PlanQualityMetric | PlanAdherenceMetric |
|---|---|---|
| 输入校验 | prepare_measure检查input/actual_output等 | 同左 |
| 任务抽取 | Task(task字符串)，来自根用户输入 | 同左 |
| 计划抽取 | AgentPlan(plan字符串列表)，共用计划抽取模板 | 同左 |
| 评分输入 | task与提取计划 | task、提取计划、实际执行trace |
| 输出 | PlanQualityScore(score浮点, reason) | PlanAdherenceScore(score浮点, reason) |
| 无计划 | 直接得1并附缺少计划说明 | 同左 |

提取模板要求每个计划步骤有可观察文本支持，不能靠任务已经完成反推模型先前必有计划。本课只记录显式清单和回复，不采集或编造隐藏思维链。完整trace含多次计划更新，抽取可能混合初始计划与后续修改；本课保存每次AgentPlan和原始清单，发现差异时需检查来源。

质量评分模板检查覆盖、顺序、必要性、细节和任务一致性；遵从模板明确只评价执行是否符合计划，不评价计划是否有用。评分是模型直接给出的浮点等级，不是yes/no比例。模板列出0、0.25、0.5、0.75、1，schema本身只声明float；本课额外检查有限且在[0,1]内，不强行四舍五入到五档。

llm模式按任务抽取、计划抽取、评分顺序调用；空计划跳过最后评分，默认1仅表示没找到可评计划。必须单列extracted_plans与empty_plan_default，不能记为完美规划或任务完成。规则验收仍要求实际存在计划。单元测试使用明确的结构化替身验证这个分支，两次替身调用不冒充真实模型请求。

strict_mode把阈值设1，低于阈值的评分置0；本课固定llm、async_mode=False、threshold=0.7，避免和hybrid/system_one混比。reason和评分在同一JSON返回，当前路径没有另一次总评生成。a_measure沿相同依赖顺序逐步await；本课对不同样本的外层并行与指标内部异步要分别说明。

## Ragas：定制rubric，不冒充同名计划指标

[通用指标文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/general_purpose/)说明按等级定义rubric；网页示例使用旧RubricsScore。本课实际使用固定modern collections的DomainSpecificRubrics，并提供InstructorBaseRagasLLM兼容适配，不能把两种导入/API混写。

构造函数把rubric描述拼入RubricScorePrompt，ascore构造RubricScoreInput、生成提示、调用agenerate，最后将RubricScoreOutput(score整数, feedback字符串)转成MetricResult(value浮点, reason=feedback)。输入字段user_input、response、reference和上下文等均可选；with_reference主要影响默认rubric选择，不能凭参数名声称自动补充参考答案。

本课分别定制计划质量与遵从两套1至5等级。质量输入是首次实际todo声明，尽量不让最终结果泄漏成计划质量；遵从输入还含执行投影。DeepEval可能从整个trace提取多次计划，两者证据选择与标准不完全相同，数值不能直接等同。输出schema只有int描述，调用方仍检查有效等级与有限值，错误记null。

无计划时本课Ragas标准给最低档1；DeepEval空计划默认也是数字1，却位于0至1量尺的最高端。相同数字的含义相反，报告必须保留名称、尺度、缺少依据标记和解释。

## 文件验收与实验来源

[verify.py](verify.py)沿用e11受限子进程执行器。先独立检查核心函数，再把checkout唯一允许的from shipping import shipping_fee在内存绑定到实际核心函数。重命名后继续由原AST边界检查器验证和执行，不允许任意import或文件IO。两个API分别执行同一组22个保留输入，共44次函数输入执行；原有Bash测试另外实际运行，二者不混计。

签名缺失、转发合同违反和测试删除是已知失败；不支持的import或语法导致执行器不适用时保留unscored，不伪装成0。保护测试比较实际内容；最终文件与保存快照也核对，并检查除了声明的项目文件、标准Python缓存及运行时记录之外，没有新增项目文件。受限执行只覆盖声明的教学子集与有限输入，不能证明任意Python程序全域正确。

协议控制实际执行状态转换、并发认领、文件修改和邮箱消费，不调用模型；工具请求是讲师构造，不能计为模型自主行为。交接漏传和删除测试的状态则由讲师构造后实际重新验收。好计划未执行、坏计划照做和无计划的评分对话也明确标为构造输入。真实Agent轨迹、原生SDK记录、构造控制与历史首轮传输失败分别保留，结果见[运行记录](run_summary.md)。

调度验收还将子任务早先失败与同一task_id最后一次交接分开。最后一次仍异常时拒绝；显式重试后最后一次正常交接且产物合格时可记为完成，同时保留child_attempt_errors与completed_after_child_retries，不能说全部调用一路成功。
