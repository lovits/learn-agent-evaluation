# 第13课：计划、依赖与交接，拆开就能做完吗

按references/textbook-writing-standard.md与Learn Claude Code的中文带读正文组织。主文约2000至3500汉字，代码另算；只有六个二级标题“问题、解决方案、工作原理、相对上一课的变更、试一下、接下来”。六个加粗短步骤，每步解释需要、给当前真实短代码、说明输入输出与接入点；注明省略，完整代码独立链接。语气平实具体，不用口号、无信息对比和每节重复小结。完整指标源码、schema/prompt/async/边界留source_walkthrough，数字与历史留run_summary。不能丢知识点。

从具体跨文件问题开场：v3核心shipping_fee和checkout.quote应该同样计费，但初始核心把1001算成600，入口又漏传expedited导致加急1000克仍600；应为800与1000。保持两个函数签名、6000上限、400加急费、精确类型检查及原测试。两个角色都说完成还得检查调用关系与真实结果。文件清单、TaskStore和原始轨迹各自含义说明，不把父/子/工具/裁判混称Agent。

复用已有e04执行循环、文件/Bash权限和e12可恢复压缩。新增TodoManager、持久TaskStore、一次性子任务新消息列表、角色文件守卫、最小MessageBus与原生SDK采集。本课只有同步一次性协作；完整持久队友WORK/IDLE、工作树、审批关机和跨进程协调仍留综合项目，不冒称完整s13实现。不提前引入后台、定时、自动重试、工作流journal。

六步：
1. TodoManager先验证整个数组再替换，最多20项且至多1个in_progress；三工具轮没有更新才提醒，一轮多个调用仍算一轮。计划状态是声明不执行代码。早期把数组塞进多层JSON字符串，真实运行出现解析额外文本错误；当前宿主按工具定义生成typed arguments输出schema，todos/blocked_by/files直接为数组，只规范化一次给旧循环arguments_json。原始wire_reply和规范化参数都保存。点出结构化输出约束，不把非法尾部截掉装成功。给TodoManager.update或真实typed schema片段，主要解释计划表不等于执行证据。
2. TaskStore先create拿实际ID再add_dependencies，claim共享锁内查pending/owner/前置completed再认领；环和不满足依赖先验证再拒绝。状态单文件临时写再replace，当前RLock只保证单进程共享实例线程，不称分布式锁。TaskStore事件记录complete_claim。角色task_complete先执行分配组件8个公开输入和测试字节保护，失败不改状态；核心通过不要求尚未执行的入口组件已经完成，整体仍验22个保留输入。给claim局部真实代码，完整state.py链接。
3. Runtime.run_child仅用description、显式prompt和角色约束创建新user消息，不自动复制父历史；共享工作目录但专用工具限制分配文件，子Agent没有task不能递归。接口约束要传或查询资料，不能假定新会话知道父历史。给context或run_session调用短片段。原工具测试仍在Docker实际执行；明确角色工具池提供哪些能力。
4. MessageBus子结果带task_id写盘，父只有一个运行时消费者，在下一模型请求前投递；模型不轮询，摘要不是独立验收。专用文件修改锁内查预期哈希，两个角色同一旧版本后写者stale拒绝，防止静默覆盖。本课不声称约束Lead任意Bash或提供完整Git合并。给consume或哈希检查短片段。说明受控并发认领/修改确实执行状态和文件操作，但调用由讲师构造，非真实模型并行故障率。
5. 实际@observe标agent/llm/tool，父task下真正嵌套子Agent，closed Trace用model_dump JSON导出。create_nested_spans_dict再经SDK serialize_to_json转普通数据，防止ToolCall对象使报告写入失败（原失败已归档，非伪造新report）。指标输入省掉重复模型请求历史，保留真实回复、工具参数/结果，原始全量记录仍存。固定低层measure绑定_trace_dict，官方自动observe/dataset通常负责此内部绑定，注明固定版本适配。DeepEval PlanQuality先Task→AgentPlan→直接评分JSON；PlanAdherence多看实际执行。分清计划可行与按计划做，坏计划也能高遵从。无计划原生默认1必须单列，不等于完美或完成。Ragas用modern DomainSpecificRubrics定制1..5，两套标准而非同名原生计划指标；质量看首次声明，遵从加执行证据，输入范围不同不能直接比分。示例无计划Native1是默认最高端，Ragas定制1最低档。给本课原生cls(...)或@observe真实代码，不列一串指标名。
6. 先按任务事件核认领依赖，再从实际目录检查两个API和保护测试；core好但quote漏参数会失败。quote只允许声明的shipping导入，内存绑定真实核心后用前课受限执行器分别跑相同22保留输入，共44函数输入执行，和真实Bash公开测试分开。缺失签名/删测试已知失败，不支持import不适用保留unscored。以文件、依赖、正常停止、声明计划和实际子会话综合验收；不把流程错误因为文件对就改成通过。给verify/evaluate的真实短片段，细节附页。

图只用现有![计划、认领与交接](images/plan-and-handoff.png)，放大链接同PNG，可编辑图源使用GitHub绝对链接；不要另外生成Mermaid或图片占位。图source与PNG来自同节点边关系，PNG是本地预览不是Desktop导出。正文无需叙述制图过程，生成凭证说明即可。

相对前课简表说明已有循环工具权限/可恢复上下文保留、新增显式计划、持久依赖、子上下文、交接、原生span及计划指标。各模块code.py/state.py/tools.py/verify.py/controls.py/eval.py链接，正文别贴整个Agent。已有磁盘记忆机制见前课，综合项目才统一全部17机制，不把当下子集写成全功能已完成。

实际结果以run_summary.md为唯一数值依据。首轮无SDK的真实业务修复两个子会话完成、产物合格但父请求502，所以整体流程失败。第二轮原生SDK的报告序列化遇到ToolCall对象，完整内存结果没保存，只能保留工作目录、transcripts和终止日志，不能伪造该轮完整原生trace；多层字符串参数错误同样在原始记录。当前typed协议与序列化修复后的运行单独记录。不要把各轮混成一次控制因果比较，不写未知模型ID、费用，不挑高分当改进。

试一下：宿主两个独立终端python3 tools/model_bridge.py与python3 tools/judge_bridge.py，8766/8768，同一登录后端不同角色而非独立模型；更新协议需重启旧桥。docker compose build；docker compose run --rm -T --entrypoint python course -m lessons.e13_planning.code；docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e13_planning.controls；docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e13_planning.eval；docker compose run --rm -T --entrypoint python course -m lessons.e13_planning.eval --judge。输入knowledge_base/e13挂载、runs/workspaces持久化、private条件只给断网verifier，凭据留宿主。重跑先另存。产物e13-agent.json、e13-controls.json、e13-evaluation.json、e13-judges.json。docker compose up -d阅读http://localhost:8765/lesson13。

观察三题：第一次计划在何时，之后改过什么？后续任务在哪条claim前等到了前置完成？核心正确入口漏传时哪个输入失败，为什么全部completed也不能代替验收？附页源码导读、运行结果、练习、解答、../../docs/e13-validation.md、../../generation/e13-README.md。接下来第14课后台任务、调度、效率和恢复，任务暂未完成时怎样等待通知、计算实际成本与判断重试。

最终公开组件审查协议另行冻结：每组件8公开输入，不替代22保留输入。每个task_id最后一次交接须正常，早先失败保留并单列completed_after_child_retries，最后一次异常不能因文件正确而放过。结构化参数但未接组件公开审查的运行与当前运行分别存档，禁止混作同次受控比较。

工具修改追加边界：Worker只有当前in_progress且归属自己的任务才可改分配文件，已完成后拒绝继续改。该权限增量用独立Docker控制验证，若正式Agent运行镜像较早，必须单独说明源码差异并核对原轨迹没有完成后修改。角色公开审查失败给真实案例反馈；外部还检查未声明的项目文件，不能只验函数值。

正式规划协议使用30000输入字符预算与50条消息触发snip，20模型步上限不变；旧5000/16是前课压缩演示压力配置，旧轮单独记录。组件公开通过仅写whole_project_assessment=not_assessed，表示整体尚未评估，不能解释为已知失败。返回实际四文件哈希和两保护测试原哈希，父端实际测试后能检查保存是否保持；独立保留输入依然在Agent之外。不要重复同一通过检查直到耗尽步数。
