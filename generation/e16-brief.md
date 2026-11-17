# 第16课正文约束

给会Python、了解RAG/Agent的中文读者写结课正文，标题“综合回归：从运行证据到发布门禁”。以Learn Claude Code的短句、具体问题、真实短代码带读为样例。只用六个H2：问题、解决方案、工作原理、相对上一课的变更、试一下、接下来。代码外约2000–3500中文字符。工作原理六个加粗步骤，各有真实节选、完整源码链接、输入输出与接入位置、忽略此步会怎样；不能给伪入口或把省略片段冒充完整程序。先讲原理，数字集中在run_summary，避免口号、AI对比和重复收尾。

承接15课校准：裁判调好了，运行对象/证据没接对仍会误判。具体问题用真实运费修复：规范说测试必须保持，不能证明本次已保持；workflow完成也可能没读测试；普通trace SUCCESS可能只是函数正常返回错误字符串。正式代码本课才连接固定上游s15+原生s09+s16+s17；之前15课独立实现保留，不整篇贴完整Agent，读者沿调用链看六个必要接入点。

六步建议：
1. Runtime.submit/_goal_loop接原生agent_loop，17机制同入口，但模型判断与讲师阶段编排区分；协议先冻结，真实工作区/只读KB/独立验收不同职责。讲师批准当前计划与Git提交不能写成模型自主行为。
2. 保存可信course-review工作流：ctx.parallel两维检查→ctx.agent验证；schema、journal语义键、成功步骤恢复；此前两个真实并行检查后故意中断，新进程复用两步只新请求一次。流程完成不证明内容正确；旧缺测试上下文bad case保留，完整输入只够获得语义复核资格。
3. capture_native_traces+RecordedMessages：保存真实trace/请求/参数/响应，正常函数返回错误字符串仍可能SUCCESS。队友线程独立根不补造parent。普通Runtime对象不可整体观测（第一次137退出与根因假设边界只在附页详述）。
4. trace_samples：用原生响应ID定位实际trace，保留工具名/参数/输出/源UUID；首轮漏command，修订只改采样不重跑Agent，两版评分都保留。这是看过结果后的开发诊断，不宣称留出提升。Faithfulness分docs-only与observed-tools两个证据范围；原生工具比较另是指定read_file投影，不是唯一正确全任务轨迹。
5. 说明DeepEval/Ragas方法差异并用一个小算例：两个预期读取只剩一个，DeepEval覆盖0.5/exact0，RagasAccuracy0/F1约0.6667；同名指标不平均。Faithfulness默认YES+BORDERLINE与Ragas明确支持有差别，空声明/错误单列，详细prompt/schema/model/verdict/聚合/异步在source_walkthrough。
6. critical_gate逐关键条件is True，业务44输入/原测试保持与实际Task、worktree租约、记忆索引、cron确认、workflow日志独立验收。正常/未授权/越界真实任务都已通过对应外部检查。CI固定断网合同，真实模型实验另执行留证；没有创建夜间自动任务。

正文显示images/integrated-runtime.png一次即可，附可编辑.drawio链接。架构总体阅读链接../../integrated_agent/architecture.md，17项具体契约和局限链接../../integrated_agent/capabilities.md。详见source_walkthrough.md、run_summary.md、exercises.md、solutions.md及../../docs/e16-validation.md。不要把所有这些内容挤进主文；也不能省掉来源和关键边界。

运行：先python3 tools/integrated_bridge.py宿主独立终端；docker compose build course成功后，用新ID：docker compose --profile capstone run --rm -T --entrypoint python agent -m integrated_agent.scenario --workspace /data/workspaces/my-capstone --report /data/runs/my-capstone.json。KB默认knowledge_base/e16只读挂载，可用INTEGRATED_KNOWLEDGE_DIR换目录；宿主登录不入容器。随后docker compose --profile verify run --rm -T --entrypoint python verifier -m integrated_agent.verify --profile composed --workspace /data/workspaces/my-capstone --criteria /verification/e16-foundation.json --report /data/runs/my-capstone-evaluation.json。双框架重评先独立启动python3 tools/judge_bridge.py，再docker compose run --rm -T --entrypoint python course -m lessons.e16_regression.eval --input /data/runs/my-capstone.json --report /data/runs/my-capstone-metrics.json。报告拒绝覆盖，失败现场保留。离线练习python -m pytest tests/test_e16.py tests/test_integrated_capabilities.py -q（夹具不是供应商执行）。阅读器http://localhost:8765/lesson16，项目http://localhost:8765/project。

本次真实结果：正常33响应、28原生trace，错误/越界各3响应；两轮实际裁判共20响应、0评分错误；业务44输入+原测试+原生状态独立通过。v1Faithfulness docs-only Deep1/仅YES.6/Ragas0；tools Deep1/仅YES2/3/Ragas.5。v2docs Deep1/仅YES0/Ragas1/9；v2完整工具证据三项均1。细节移附页，正文只选支持原理的一例；不能宣称普遍准确率、随机性消除或全部来自采样修复。供应商精确型号和费用未知。原生schema/Todo/cron/Goal/进程边界按capabilities保留，不擅自包装成完整JSON Schema或通用安全保证。

接下来没有第17课，给自主结课项目的迁移步骤：换任务、知识库与成功合同，冻结数据，正常/错误/边界执行，独立验收，trace抽样，双框架解释，bad case入CI。不要写“学完就掌握一切评测”的结尾。
