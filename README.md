# 从项目学会 RAG 与 Agent 评测

以 DeepEval、Ragas 的真实实现学习评测，按 Learn Claude Code 的方式：
**问题 → 最小实现 → 工作原理 → 源码 → 实验 → 验收**。

本仓库的第一个可运行样章是 **s07 Faithfulness**。
全课程规划为6单元24课，其余课程目前是教学路线，尚未实现。

## 一条命令启动

安装并启动 Docker Desktop / Docker Engine，然后在本仓库根目录执行：

```sh
docker compose up --build -d
```

打开 **http://localhost:8765**：课程、源码分析、练习、知识库与结果入口都在这里。
首次构建需要联网下载固定版本依赖；镜像建好后，离线回放不调用外部模型。

## 跑第一次实验

```sh
docker compose exec course python s07_faithfulness/code.py
```

这会调用**真实 DeepEval / Ragas SDK**，用课程预设的模型输出重放评分过程。
得到的是可复核的算法契约，不是某个模型的实际效果。
教学样本由本项目编写，未经过独立人工双标审核；它们用于演示已知边界，不是生产评测集。

| 样本 | DeepEval 默认 | 惩罚歧义 | Ragas |
|---|---:|---:|---:|
| supported | 1 | 1 | 1 |
| unsupported | 1 | 0 | 0 |
| contradicted | 0 | 0 | 0 |
| mixed | 2/3 | 1/3 | 1/3 |
| no_claims | 1 | 1 | null（未评分） |

上述数字来自固定教学判定；真实模型可能拆出不同声明或给出不同判定。
知识库变更会让旧回放快照失效，程序会拒绝沿用旧分数。

## 你会学到

- Faithfulness 测的是回答与检索证据的关系，如何与正确性、相关性区分。
- supported / unsupported / contradicted 三类声明及其分母。
- 为什么两个框架同名指标不保证同分，惩罚歧义与 strict_mode 又有什么不同。
- 沿真实源码从输入、schema、verdict 走到最终聚合。
- 怎样记录结果、解释空声明，并通过改证据发现回放的边界。

## 阅读和运行入口

- [s07 样章](s07_faithfulness/README.zh.md)
- [关键源码分析](s07_faithfulness/source_walkthrough.md)
- [练习](s07_faithfulness/exercises.md) / [参考答案](s07_faithfulness/solutions.md)
- [完整代码入口](s07_faithfulness/code.py) / [固定样本](s07_faithfulness/fixtures.json)
- [容器断网运行生成的示例报告](s07_faithfulness/example_report.json)
- [Docker、知识库挂载、结果持久化和真实裁判配置](docs/docker.md)
- [24课路线](docs/curriculum.md)
- [已确认需求与项目计划](docs/project-plan.md)
- [PocketFlow 实际生成过程](generation/README.md)
- [依赖与来源版本](references/versions.json)

## 知识库和实验结果

默认知识库在 `knowledge_base/`，包含虚构退款政策和概念卡片。
它以只读目录挂载，实验结果写入可持久化的 `runs/`。

```sh
docker compose run --rm course search "退款"
docker compose run --rm course replay --sample mixed
```

切换自己的 Markdown/TXT 目录，只需设置 `.env` 中的 KNOWLEDGE_DIR 并重建容器。
详细步骤和快照失效规则见 Docker 说明。

## 不用 Docker 的本地开发

需要 Python 3.11/3.12 与 uv，依赖精确版本由 uv.lock 固定：

```sh
uv sync --frozen
uv run python s07_faithfulness/code.py
uv run python -m eval_course serve --port 8765
uv run pytest -q
```

## 真实模型实验

配置支持 Chat Completions JSON 模式的裁判模型和本地密钥文件后：

```sh
docker compose -f compose.yaml -f compose.live.yaml run --rm course live --sample mixed
```

该模式会产生真实模型调用；结果保存在 runs 中，记录模型、token usage 和逐阶段输出。
本轮验证范围和实测结果见 [验证记录](docs/validation.md)。

## 第三方代码

课程原创部分使用 MIT 许可。SDK 源码快照与 PocketFlow 的许可、版本和修改边界见
[第三方说明](THIRD_PARTY.md)。没有把飞书私人文档原始响应、API key或Codex登录凭据上传到仓库。
