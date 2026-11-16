# 从 Learn Claude Code 编程 Agent 学评测

课程围绕同一个编程Agent递进，每课只引入当前评测需要的代码。
第1课从最小循环与Bash开始；第2课加入文件工具、权限分支和可关联的轨迹。
两课都使用真实模型决策，在Docker执行工具，再独立验收结果。

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
当前第1至10课已制作，第1至7课按统一正文标准完成重写与复核，第8至10课沿同一写法制作，其余6课保留详细设计。DeepEval/Ragas用于评测方法和源码依据，
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
