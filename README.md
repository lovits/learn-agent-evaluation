# 从 Learn Claude Code 编程 Agent 学评测

课程围绕同一个编程Agent递进，每课只引入当前评测需要的代码。
第1课从最小循环与Bash开始；第2课加入文件工具、权限分支和可关联的轨迹。
两课都使用真实模型决策，在Docker执行工具，再独立验收结果。

- [16课详细设计与制作规范](docs/course-specification.md)
- [飞书云文档](https://my.feishu.cn/docx/V8CPdL3Y8oMZt4xJ8RCc4HfNnfb)
- [16课大纲](docs/curriculum.md)
- [第1课教材](lessons/e01_agent_baseline/README.zh.md)
- [第2课教材](lessons/e02_tools_traces/README.zh.md) / [飞书版](https://my.feishu.cn/docx/KVAkdoPHlofNEOxSPQqcfXuenfn) / [源码导读](lessons/e02_tools_traces/source_walkthrough.md)
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

旧Faithfulness样章和专属回放实现已清理；该主题将在第5课以编程案例重新制作。
当前已制作第1、2、3、4课，其余12课保留详细设计。DeepEval/Ragas用于评测方法和源码依据，
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
