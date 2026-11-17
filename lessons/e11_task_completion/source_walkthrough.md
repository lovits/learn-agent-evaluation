# 第11课源码导读：谁有资格说完成了

本课固定版本与源码哈希见 [e11-reading.json](../../references/e11-reading.json)。DeepEval 为4.3.4、Ragas 为0.4.4；所有结论限于所列源码与本课接口。官方文档说明推荐用法，固定源码说明实验实际走到哪个分支。没有声称通读两个框架全部文档。

## 任务合同和证据的归属

任务是修复纯函数shipping_fee，费用以整数分表示。起步1000克600分，之后每开始1000克增加200分，加急增加300分。重量必须是精确int，1至5000；加急必须是精确bool。错误类型先抛TypeError，合法类型但重量越界抛ValueError。原测试文件必须原样保留。

三个公开例子检查1000、2000和1001克。独立验收再检查其他边界、加急与错误输入。私有验收文件位于宿主机evaluation_private，Docker构建排除它，只由断网verifier服务只读挂载到/verification。公开审查结果可以回传Agent；保留检查在Agent停止后运行，不拿其反馈继续调当前修复。结果公布后，这组检查已经是教学示例，不能继续声称它是未见过的盲测集。模型凭据仍留宿主机。

文件事实由 [verify.py](verify.py) 从实际目录读取，绝不从final_answer解析“通过”。两个真实工作目录保持原样；控制样本在验收器临时目录另建，明确标注instructor_mutated_snapshot。这些控制的状态确实执行了检查，但没有对应的真实Agent工具轨迹。

## 从s17提取停止审查，不提前搬入整套会话

上游 [s17说明](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s17_goal_loop/README.zh.md) 以具体问题说明：模型这一轮停下，不代表目标已达成。代码中PromptGoalEvaluator读对话，用GoalEvaluation的ok、reason、impossible返回结构化判断；GoalController.evaluate_after_turn处理allow、block、defer、error和limit；AgentSession._run_query在没有工具结果可执行时调用它。block把原因加入同一消息历史并继续循环，后台运行则defer；错误和上限不伪装成完成。源码还包括设置、替换、清除、状态查询和恢复；这些完整会话功能留到后续集成核对，本课没有宣称功能等价。

本课保留已讲e04循环，外层run_case最多审查三次，每轮内部最多12个模型步骤。一次内部finished只是一个待审查的停止候选。GoalState.review的ready_for_external_verification只表示“公开例子通过且测试文件原样保留”。它从不命名为完整任务完成。公开条件不通过返回blocked并把原任务与真实检查结果追加到下一轮；超限返回limit；检查无法评分返回review_error，保留条件与记录。显式约束同时要求保留测试与删除所有测试时，前置检查给impossible并保留冲突原因，不调用模型。它只识别这个声明式矛盾，不承担一般自由文本可满足性判断。没有后台任务，所以本课不实现defer。

recorded_messages从实际model/tool事件重建完整消息，按模型轮把此前工具结果回填，接到下一段循环之前。旧循环的span_id是内部轮局部编号，因此可能跨审查轮重复；定位必须同时使用turns下标，不能把所有事件拍平后只按span_id连接。ToolPool实例跨续轮保留，已经发现的工具继续可用。宿主桥仍使用e10动态工具契约；这表示复用接口，不表示偷偷运行第10课计算案例。

首轮假报完成是任务末尾明确加入的故障注入指令，来源标为live_model_with_controlled_first_turn。不能据此宣称模型自然发生了虚报。评分阶段的early_claim_only是刻意只投影业务请求与实际回答，故障注入说明仍在原始运行报告中；这种评分输入与原始对话并不相同。

## 外部执行器的适用范围

[runner.py](runner.py)先解析AST，检查既定纯Python子集和函数签名，再在独立子进程运行函数。允许算术、变量、条件、循环、辅助函数和指定基础内置函数；拒绝import、属性访问、dunder、类、async、with、try等。它的适用范围事先写入任务，不按模型交出的答案临时收窄。调用时比较返回值和精确类型；异常以异常类名比较。使用不同的合法公式或中间变量均可以通过，不按源字符串与标准答案相等判分。

子进程用python -I -S启动，父进程墙钟等待4秒；CPU上限2秒；Linux Docker另设256 MiB地址空间上限。macOS不设置RLIMIT_AS，结果明确记录memory_bytes=null，本课最终实验以Linux容器为准。限制字段由runner写入原始结果。该执行器用于声明的教学子集，不能当作承受任意恶意Python的安全边界。真实部署需要另做进程/容器隔离和资源策略。

已支持的错误实现得到scored和失败检查；语法错误、不支持的代码、进程超时等得到unscored，passed=null。测试文件缺失是已经观察到的合同违反，因此得失败。源文件不存在也是失败。工具或验收器异常不能塞进“任务失败率”当作普通0分；先看适用范围与错误。

本课保存源文件哈希、是否改变、测试文件哈希一致性和逐输入结果。source_changed用来说明差异，实际合同检查以行为为主。只保留一个布尔总分会丢掉“公式正确但测试被删”的原因。

## DeepEval TaskCompletion的两次判断

[官方Task Completion文档](https://deepeval.com/docs/metrics-task-completion)推荐对完整Agent trace设置tracing并在observe上挂指标。固定源码TaskCompletionMetric也设置requires_trace=True，但直接measure仍保留一个注释TODO: Deprecate this soon的兼容路径：没有_trace_dict字典时，使用input、actual_output和tools_called提取task与outcome。

本课明确走这个兼容分支：input/task为版本化业务目标，actual_output为序列化对话，必要时附真实外部检查，未设置私有_trace_dict，也没有声称执行SDK原生trace采集。完整SDK trace接入仍是集成课的工作。将工具内容写入actual_output是本课投影选择，不能和官方完整trace路径混称。

实际调用链：measure → prepare_measure检查INPUT/ACTUAL_OUTPUT并重置计费字段 → _extract_task_and_outcome → _get_prompt的extract_goal_and_outcome模板 → DeepJudge.generate → 宿主裁判 → TaskAndOutcome(task,outcome)。然后_generate_verdicts用目标和提取的outcome生成第二个prompt，经TaskCompletionVerdict(verdict:float,reason)解析，_calculate_score得到分数，is_successful按threshold比较。传task会固定评价目标，但提取阶段仍执行；它不省掉第一次请求。

模板要求outcome只描述轨迹事实，但这个要求仍由模型执行。单独一句“修好了”无法成为外部文件事实。完整trace模板也只是要求从嵌套span提取事实，没有替Agent运行测试。严格模式把低于阈值的分数压为0；本课threshold=1但strict_mode默认False，因此可以保留0到1的中间分，是否通过另作比较。schema中的verdict仅声明float，不在字段上限制0到1，本课在SDK返回后另查有限数及范围。

a_measure沿同样的两阶段逻辑调用_a_extract_task_and_outcome及_a_generate_verdicts。DeepJudge.a_generate通过asyncio.to_thread调用相同传输；它不是离线规则。原生LLM指标本轮用同步measure实际运行；自定义指标另验证同步/异步结果一致。没有原生模型计价，本课不填未知费用与具体模型ID。

## Ragas目标准确率：参考目标来自哪里

[官方Agentic指标文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)把WithReference和WithoutReference分开。固定collections源码要求现代InstructorBaseRagasLLM，旧BaseRagasLLM包装器不能直接传入。沿用CapturingJudge，真实保留每次结构化输出。

WithReference.ascore先检查非空消息列表和reference，把HumanMessage、AIMessage和ToolMessage的pretty_repr拼为workflow；workflow_prompt通过WorkflowOutput提取user_goal与end_state，再用reference和end_state经CompareOutcomeOutput比较。verdict只允许字符串“0”或“1”，结果转float并放入MetricResult。固定源码返回时只传value，没有把比较schema中的reason传给MetricResult，因此本轮result.reason为None；解释仍保存在捕获的CompareOutcomeOutput中。

WithoutReference也先推断user_goal/end_state，区别是第二阶段拿推断的user_goal比较。它仍调用裁判两次。“无参考”只表示没有外部参考目标，不表示不需要证据，更不表示结果天然可信。只给压缩回答、遗漏文件检查或把指令混进被评文本，都可能改变推断的目标或结束状态。

本课conversation把真实JSON动作和工具结果序列化成消息正文，保留顺序；没有冒充原生ToolCall字段的结构化调用。外部验收作为明确的post-run ToolMessage追加，时间在Agent停止之后，不回流给Agent。这是同一产物的评分输入补充，不是Agent改进。控制样本的消息注明讲师构造状态，不能拼接成假Agent轨迹。

## 自定义指标：规则、裁判和组合

[DeepEval自定义指标指南](https://deepeval.com/guides/guides-building-custom-metrics)提供BaseMetric扩展入口。本课ExternalCompletionMetric在measure读取metadata.external_evidence，严格解析Evidence结构，检查非空布尔checks并取逻辑与。a_measure复用这段无网络规则；每次重置score/error/reason，避免前一条失败污染下一条。is_successful使用原生BaseMetric：有error则False，否则score≥threshold，threshold缺省None时另有不判通过的语义，本课固定1。

RagasExternalCompletion继承collections.BaseMetric并覆盖ascore，返回MetricResult(value,reason)。父类ascore只是占位0，不能继承后忘记覆盖。同步score在没有运行中的event loop时用asyncio.run包装；已经在异步环境中应直接await ascore。实验实际执行两框架的同步/异步规则，检查四者一致。BaseMetric本身提供接口与部分组件验证，不会替本课理解业务合同；布尔类型检查与错误语义由本课实现。

规则满足全部必需检查得1，任一失败得0；未知、无检查或结构错误抛异常，由外层记为unscored和null分数。别把字符串“true”当布尔True。LLM原生指标保留reason和抽取步骤，和规则分别展示。

组合采用min(rule_score, judge_score)，缺任一有效分则unscored；规则为0时裁判即使给1也不能抬高结果。这个组合只是一项明确业务政策，不能当作框架统一默认公式。要做部分完成诊断，可看逐项checks或另报通过比例，验收总闸仍要求全部必需项通过。

## 阅读与实验顺序

先读code.py的停止候选和GoalState，再读verify.py/runner.py的实际行为，随后读metrics.py与eval.py的原生调用。对照[运行摘要](run_summary.md)确认本次真实执行、构造控制、原生裁判投影分别来自哪里。最后做[练习](exercises.md)，答案在[solutions.md](solutions.md)。官方通用指标入口保留为[General Purpose](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/general_purpose/)，AspectCritic和rubric已经在前课介绍，本课集中讲业务扩展接口。
