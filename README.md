# 从 Learn Claude Code 编程 Agent 学评测

全套16课围绕同一个编程Agent递进，每课只引入当前评测需要的代码。
从最小循环与Bash开始，逐步加入知识库、RAG评测、工具与任务评测、数据集、版本比较和裁判校准，最后接通17项原生机制与独立验收。
各课保留实际执行、构造样本、夹具控制与历史记录的来源，主文沿六部分、六步关键代码阅读。

- [16课详细设计与制作规范](docs/course-specification.md)
- [飞书云文档](https://my.feishu.cn/docx/V8CPdL3Y8oMZt4xJ8RCc4HfNnfb)
- [16课大纲](docs/curriculum.md)
- [第1课教材：已按 Learn Claude Code 方式改写，含两张关键结构图](lessons/e01_agent_baseline/README.zh.md) / [飞书版](https://my.feishu.cn/docx/ZIlFdoY5EoFvaExYY9dcvQnnnce) / [图文改写验收](docs/e01-rewrite-validation.md)
- [第2课教材（已按统一标准重写）](lessons/e02_tools_traces/README.zh.md) / [飞书版](https://my.feishu.cn/docx/KVAkdoPHlofNEOxSPQqcfXuenfn) / [源码导读](lessons/e02_tools_traces/source_walkthrough.md)
- [第2课运行结果](lessons/e02_tools_traces/run_summary.md) / [验收记录](docs/e02-validation.md)
- [第1课源码导读](lessons/e01_agent_baseline/source_walkthrough.md)
- [练习](lessons/e01_agent_baseline/exercises.md) / [参考答案](lessons/e01_agent_baseline/solutions.md)
- [实际运行报告](lessons/e01_agent_baseline/example_report.json) / [验收记录](docs/validation.md)

## 启动

需要Docker Desktop/Engine、Python 3.11以上，以及宿主机已登录的Codex CLI。
先在宿主机终端启动模型入口，保持这个终端运行：

```sh
python3 tools/model_bridge.py
```

另开终端，在项目目录启动课程：

```sh
docker compose up --build -d
```

打开 http://localhost:8765 。登录凭据留在宿主机，容器只获取模型动作。
Codex自身工具被关闭；实际Bash由本课Agent在容器的独立练习目录执行。

## 跑一条真实任务并独立验收

```sh
docker compose run --rm -T course run --case create_and_run
```

命令输出run_id后，将实际值用于：

```sh
docker compose --profile verify run --rm -T verifier verify --run-id 实际run_id
```

批量运行4条真实任务并逐条验收：

```sh
python3 tools/run_e01.py
```

新记录保存在runs。随教材发布的example_report.json是固定的一次运行；默认重跑不覆盖它。
`finished`表示模型停止，`passed`表示独立验收通过。脚本错误任务要求观察原始失败，所以
非零命令退出与任务验收通过可以同时成立。验收器不评价最终中文解释的语义质量。

## 数据与挂载

- knowledge_base：只读项目资料，第1课不执行检索。
- workspaces：每次任务独立的可写目录。
- runs：持久化轨迹和评分。
- evaluation_private：只挂载给离线verifier，不进入Agent镜像。

完整操作、模型接入和验证边界见 [Docker说明](docs/docker.md)。

## 项目状态

旧Faithfulness样章和专属回放实现已清理；该主题已在第5课以编程案例重新制作。
当前第1至15课已制作，第1至7课按统一正文标准完成重写与复核，第8至15课沿同一写法制作，第16课的集成实现与验收正在进行。DeepEval/Ragas用于评测方法和源码依据，
第一课先用确定性任务合同判断文件、输出和退出码，后续再逐步引入框架接口与模型裁判。

教材通过 [PocketFlow流程](generation/README.md)组织，来源与许可见 [第三方说明](THIRD_PARTY.md)。

## 第2课实验

沿用上面的宿主机模型入口和Docker环境。升级项目后重新启动模型入口，让它载入第2课的工具描述。

```sh
docker compose run --rm -T course run-e02 --case edit_and_run
docker compose --profile verify run --rm -T verifier verify-e02 --run-id 实际run_id
python3 tools/run_e02.py
```

阅读页面：http://localhost:8765/lesson2 。[五组实验及结果](lessons/e02_tools_traces/run_summary.md)中区分正常任务与故障注入。

## 第3课：规则评分与LLM裁判

正文已按六部分与六步关键代码重写，[阶段验收](docs/course-revision-validation.md)。

[教材](lessons/e03_judges/README.zh.md)、[源码导读](lessons/e03_judges/source_walkthrough.md)、[实验与校准](lessons/e03_judges/run_summary.md)。先启动 `python3 tools/judge_bridge.py`，再运行 `docker compose run --rm -T --entrypoint python course -m lessons.e03_judges.eval`。阅读地址：http://localhost:8765/lesson3 。

[第3课飞书完整教材](https://my.feishu.cn/docx/J6iAd17kSonCjCxqlOWcjyGonTg) / [第3课验收](docs/e03-validation.md)。

## 第4课：知识库检索

[教材](lessons/e04_retrieval/README.zh.md)、[源码导读](lessons/e04_retrieval/source_walkthrough.md)、[实验结果](lessons/e04_retrieval/run_summary.md)、[验收记录](docs/e04-validation.md)。本机阅读：http://localhost:8765/lesson4 。

先保持 `python3 tools/model_bridge.py` 与 `python3 tools/judge_bridge.py` 运行，再执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e04_retrieval.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e04_retrieval.verify
docker compose run --rm -T --entrypoint python course -m lessons.e04_retrieval.eval
```

使用自己的知识库时，设置 `KNOWLEDGE_DIR=/实际绝对路径` 再运行compose；只需检索即可验证新挂载，固定upload例题与验收标准用于附带的合成资料。新目录必须已存在。

[第4课飞书完整版本](https://my.feishu.cn/docx/SPD5dOh7vo7LVtxrbykc7tgSn4g)。

## 第5课：Faithfulness

[教材](lessons/e05_faithfulness/README.zh.md)、[源码导读](lessons/e05_faithfulness/source_walkthrough.md)、[实验结果](lessons/e05_faithfulness/run_summary.md)、[验收记录](docs/e05-validation.md)。宿主机保持 `python3 tools/judge_bridge.py` 运行，容器执行 `docker compose run --rm -T --entrypoint python course -m lessons.e05_faithfulness.eval`。阅读地址：http://localhost:8765/lesson5 。

[第5课飞书完整教材](https://my.feishu.cn/docx/VnU4dKOOHoMJhEx55jpcQ83fn4e)。

## 第6课：答案质量与拒答

[教材](lessons/e06_answer_quality/README.zh.md)、[源码导读](lessons/e06_answer_quality/source_walkthrough.md)、[实验结果](lessons/e06_answer_quality/run_summary.md)、[练习与解答](lessons/e06_answer_quality/exercises.md)、[验收记录](docs/e06-validation.md)。从只答对认证头开始，区分切题、正确、完整与适当拒答；数字用于理解原理。人工计算演示与真实裁判结果分别标注。

宿主机保持 `python3 tools/judge_bridge.py` 运行；容器执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e06_answer_quality.eval
docker compose run --rm -T --entrypoint python course tools/e06_reference_repair.py
```

阅读地址：http://localhost:8765/lesson6 。本课复用旧Agent记录，不执行新Agent；默认混合公式做手算，原生AnswerCorrectness实测[1,0]，没有embedding模型调用。

[第6课飞书完整教材](https://my.feishu.cn/docx/IrtXdlfrVoYPZcxNPkLccRzHn0b)。

## 第7课：RAG故障定位

[教材](lessons/e07_failure_diagnosis/README.zh.md)沿Learn Claude Code的问题、方案、分步代码、变更、试验与下一课组织，先追踪资料、检索与文件，再看评分。[源码导读](lessons/e07_failure_diagnosis/source_walkthrough.md)、[实验记录](lessons/e07_failure_diagnosis/run_summary.md)、[练习](lessons/e07_failure_diagnosis/exercises.md)、[验收](docs/e07-validation.md)。

宿主机分别保持 `python3 tools/model_bridge.py` 和 `python3 tools/judge_bridge.py` 运行。构建后依次执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e07_failure_diagnosis.code
docker compose run --rm -T --entrypoint python course -m lessons.e07_failure_diagnosis.eval
```

本机阅读：http://localhost:8765/lesson7 。每次运行会覆盖同名runs报告，比较前先另存；教材里的固定记录保留。

[第7课飞书完整教材](https://my.feishu.cn/docx/Yueedp2OAo3ljdxc5Fich78ZnWc)。

## 第8课：从候选题到可审核数据

[教材](lessons/e08_datasets/README.zh.md)沿六步讲解挂载资料、DeepEval原生Synthesizer、Ragas图谱与场景、参考审核、去重和题族划分。[源码导读](lessons/e08_datasets/source_walkthrough.md)、[实验记录](lessons/e08_datasets/run_summary.md)、[独立练习](lessons/e08_datasets/exercises.md)、[验收](docs/e08-validation.md)。

宿主机两个终端分别保持`python3 tools/generation_bridge.py`与`python3 tools/judge_bridge.py`运行；然后：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e08_datasets.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e08_datasets.eval
```

阅读地址：http://localhost:8765/lesson8 。报告写runs/e08-dataset.json与runs/e08-dataset-grade.json，重跑覆盖，比较前先另存。此课没有执行目标Agent；7条候选仍待人工确认，公开种子分组不构成盲测。

[第8课飞书完整教材](https://my.feishu.cn/docx/MxtCd79nEojnljxIBc4cwhCon9f)。

## 第9课：版本比较，先配对再看均值

[教材](lessons/e09_comparison/README.zh.md)、[源码导读](lessons/e09_comparison/source_walkthrough.md)、[真实结果](lessons/e09_comparison/run_summary.md)、[练习](lessons/e09_comparison/exercises.md)、[验收](docs/e09-validation.md)。只改变检索返回数量，保留编程Agent与真实文件验收，先开发选择再留出验证。

宿主机保持`python3 tools/model_bridge.py`运行；可选重复裁判另启动`python3 tools/judge_bridge.py`。顺序执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e09_comparison.code --phase development
docker compose run --rm -T --entrypoint python course -m lessons.e09_comparison.code --phase holdout
docker compose run --rm -T --entrypoint python course -m lessons.e09_comparison.eval --repeat-judge
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e09_comparison.eval
```

阅读地址：http://localhost:8765/lesson9 。runs/e09-*同名文件重跑覆盖；比较前另存。协议或数据改变后须重新开发阶段，不能改旧manifest继续留出。公开合成题只演示方法，四次执行不等于四个独立任务，零宽bootstrap区间也不能保证总体效果。

[第9课飞书完整教材](https://my.feishu.cn/docx/P3iUd8PkyoI1BixVVuCcUqsRnOg)。

## 第10课：工具、参数与MCP

[教材](lessons/e10_tool_evaluation/README.zh.md)、[源码导读](lessons/e10_tool_evaluation/source_walkthrough.md)、[实际实验](lessons/e10_tool_evaluation/run_summary.md)、[练习](lessons/e10_tool_evaluation/exercises.md)、[验收](docs/e10-validation.md)。沿Learn Claude Code s14增加进程内模拟工具发现，继续真实检索、改文件与运行命令。工具名字、参数、顺序、权限与业务产物分别评价。

宿主机运行最新`python3 tools/model_bridge.py`与`python3 tools/judge_bridge.py`；旧入口需停止后重启。随后执行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e10_tool_evaluation.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e10_tool_evaluation.eval
docker compose run --rm -T --entrypoint python course -m lessons.e10_tool_evaluation.eval --judge
```

阅读地址：http://localhost:8765/lesson10 。runs/e10-*重跑覆盖，比较前先另存。控制轨迹明确标为构造；MCP为进程内模拟；两轮评分协议与原始误判均保留。评分协议修订时没有重跑Agent或改动产物。

[第10课飞书完整教材](https://my.feishu.cn/docx/YszVdRUrLoT6CpxsUIpcJJIgnQe)。

## 第11课：真实任务完成与自定义指标

[教材](lessons/e11_task_completion/README.zh.md)、[源码导读](lessons/e11_task_completion/source_walkthrough.md)、[实际实验](lessons/e11_task_completion/run_summary.md)、[练习](lessons/e11_task_completion/exercises.md)、[验收](docs/e11-validation.md)。在已有编程Agent外增加公开停止审查，修复挂载知识库约束下的运费函数，再由独立容器检查边界、类型和测试保留。原生TaskCompletion、AgentGoalAccuracy与业务规则分开展示，保留真实裁判误判。

```sh
docker compose run --rm -T --entrypoint python course -m lessons.e11_task_completion.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e11_task_completion.eval
docker compose run --rm -T --entrypoint python course -m lessons.e11_task_completion.eval --judge
```

阅读地址：http://localhost:8765/lesson11 。报告前缀runs/e11-*，重跑前另存需要比较的记录。六个负例状态是讲师构造、真实执行验收；显式首轮故障注入不是自然错误率。完整SDK trace采集与完整s17会话控制仍待集成课核验。

[第11课飞书完整教材](https://my.feishu.cn/docx/K7hJd2iAVoIJYcxCEC4c5AKInBe)。

## 第12课：多轮、压缩与跨会话记忆

[教材](lessons/e12_conversation/README.zh.md)、[源码导读](lessons/e12_conversation/source_walkthrough.md)、[实验结果](lessons/e12_conversation/run_summary.md)、[练习](lessons/e12_conversation/exercises.md)、[验收](docs/e12-validation.md)。连续更新同一运费函数，分别追踪实际模型输入、原始轨迹、摘要和磁盘记忆。原生会话评分、代码行为与模拟用户覆盖分别审查。

```bash
docker compose run --rm -T --entrypoint python course -m lessons.e12_conversation.code
docker compose run --rm -T --entrypoint python course -m lessons.e12_conversation.simulate
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e12_conversation.context_controls
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e12_conversation.eval
docker compose run --rm -T --entrypoint python course -m lessons.e12_conversation.eval --judge
```

需先分别启动8766模型桥和8768裁判桥，再构建当前镜像。阅读地址：http://localhost:8765/lesson12 。固定两路径、区间记录增量运行与模拟用户有各自原始报告；32步/6用户轮协议与旧预算实验分开，接口失败保留未评分。完整主动压缩、记忆整理和回滚继续留到综合项目核验。

[第12课飞书完整教材](https://my.feishu.cn/docx/FxDedeXzmoburRxNAJpczv10nyd)。

## 第13课：计划、依赖与交接

[教材](lessons/e13_planning/README.zh.md)、[源码导读](lessons/e13_planning/source_walkthrough.md)、[实验结果](lessons/e13_planning/run_summary.md)、[练习](lessons/e13_planning/exercises.md)、[验收](docs/e13-validation.md)。先声明计划，再用真实ID建依赖图，分别委派核心计算和入口转发；父子新上下文、共享文件、结果邮箱、原生SDK树与独立验收分开追踪。

```bash
docker compose run --rm -T --entrypoint python course -m lessons.e13_planning.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e13_planning.controls
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e13_planning.eval
docker compose run --rm -T --entrypoint python course -m lessons.e13_planning.eval --judge
```

先分别启动宿主8766模型桥与8768裁判桥，再构建当前镜像。阅读地址：http://localhost:8765/lesson13 。真实应用与两个API独立验收通过；计划质量、遵从与业务结果有不同含义，保留低分、空计划默认及裁判分歧。同步一次性子任务不代表完整持久团队；其他机制继续在综合项目核验。

[第13课飞书完整教材](https://my.feishu.cn/docx/LEyndiChQo7i8Vx1zodcfvwSnD4)。

## 第14课：后台、调度与效率

[教材](lessons/e14_runtime/README.zh.md)、[源码导读](lessons/e14_runtime/source_walkthrough.md)、[实验结果](lessons/e14_runtime/run_summary.md)、[练习](lessons/e14_runtime/exercises.md)、[验收](docs/e14-validation.md)。把后台编号、真实命令结果、定时提示接收和任务完成分开，按当前文件版本核对测试收据；效率、资源和业务验收分别解释。

```bash
docker compose run --rm -T --entrypoint python course -m lessons.e14_runtime.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e14_runtime.controls
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e14_runtime.eval
docker compose run --rm -T --entrypoint python course -m lessons.e14_runtime.eval --judge
```

先分别启动8766模型桥和8768裁判桥并确认镜像构建成功。已有e14-agent.json时先另存原报告，入口拒绝覆盖。阅读地址：http://localhost:8765/lesson14 。预声明正常任务3/3，故意超时恢复单列通过；原生效率低分与必要恢复读取的分歧保留。受控时钟不等于常驻生产调度服务，完整机制仍到综合课核验。

[第14课飞书完整教材](https://my.feishu.cn/docx/Y2DBdLG3Nouii3xym8NcjZNsnjg)。

## 第15课：裁判校准、偏差与中文适配

[教材](lessons/e15_calibration/README.zh.md)、[源码导读](lessons/e15_calibration/source_walkthrough.md)、[实验结果](lessons/e15_calibration/run_summary.md)、[练习](lessons/e15_calibration/exercises.md)、[验收](docs/e15-validation.md)。保持Agent不变，按家族隔离数据，在开发集选择标准后冻结，再评价留出结果；区分规则标签、人工审核与模型判分。

```bash
docker compose run --rm -T --entrypoint python course -m lessons.e15_calibration.eval
```

先在宿主启动8768裁判桥并确认镜像构建成功。已有e15-calibration.json会拒绝覆盖，须另存旧报告再明确新实验。48次真实裁判响应均保留，未测出准确率提升或成对标签翻转；这些简单构造案例不证明普遍无偏。阅读地址：http://localhost:8765/lesson15 。

[第15课飞书完整教材](https://my.feishu.cn/docx/HBwudv2QzoZgeQxocH1cAMXcnFg)。

## 第16课与综合编程Agent评测项目

[第16课教材](lessons/e16_regression/README.zh.md)、[完整架构与调用链](integrated_agent/architecture.md)、[17项机制与限制](integrated_agent/capabilities.md)、[实验结果](lessons/e16_regression/run_summary.md)、[验收记录](docs/e16-validation.md)。综合项目接入固定上游核心，默认只读挂载 `knowledge_base/e16`；模型登录保留在宿主，容器执行实际项目工具，另一个断网容器验收业务与原生状态。

正常组合任务完成33次模型响应，导出28条原生trace；未授权与越界任务各3次响应，分别被实际权限边界拒绝。两个API的44条外部输入、原测试与运行状态独立通过。两轮双框架评分共20次裁判响应，采样漏命令修订前后均保留，指标口径与事实验收分开解释。

先按[项目入口](integrated_agent/README.md)启动宿主模型桥并构建镜像，再使用全新的实验目录：

```bash
docker compose --profile capstone run --rm -T --entrypoint python agent \
  -m integrated_agent.scenario --workspace /data/workspaces/my-capstone \
  --report /data/runs/my-capstone.json
docker compose --profile verify run --rm -T --entrypoint python verifier \
  -m integrated_agent.verify --profile composed \
  --workspace /data/workspaces/my-capstone --criteria /verification/e16-foundation.json \
  --report /data/runs/my-capstone-evaluation.json
```

本地阅读：http://localhost:8765/lesson16 、http://localhost:8765/project-architecture 。讲师脚本明确负责阶段排序、计划批准与Git提交；这部分编排不冒充模型自主规划。自有项目需要重新定义成功合同，不能套用本练习的有限输入作为一般可靠性证明。

[第16课飞书教材](https://my.feishu.cn/docx/UzRzdHS2ioW8m1x3702cX54onOh) / [综合项目飞书讲解](https://my.feishu.cn/docx/Odeld6l1Co6pWlx3qBTcItBLn3d)。
