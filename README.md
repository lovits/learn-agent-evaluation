# 从编程 Agent 学评测

从一个循环和 Bash 开始，给编程 Agent 逐步接上工具、知识库与长期任务。每增加一种能力，就问一个问题：怎样知道它做得对？

课程以 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的编程 Agent 为贯穿项目，知识库部分接入 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/main/content/TinyRAG)，用 DeepEval 和 Ragas 解释评测方法。你会从真实文件和工具动作入手，再读到指标中的声明拆解、模型裁决和分数聚合。

适合会 Python、了解 RAG 和 Agent，希望系统学习评测的读者。

## 课程

| 课 | 核心知识点 | 这一课解决什么问题 | 源码导读 |
|---|---|---|---|
| 01 | [Agent 循环](lessons/e01_agent_baseline/README.zh.md) | 模型停下了，任务就完成了吗？ | [源码](lessons/e01_agent_baseline/source_walkthrough.md) |
| 02 | [评测样本](lessons/e02_tools_traces/README.zh.md) | 怎样把一次工具调用变成可评测的记录？ | [源码](lessons/e02_tools_traces/source_walkthrough.md) |
| 03 | [评分标准](lessons/e03_judges/README.zh.md) | 什么交给规则，什么交给 LLM 裁判？ | [源码](lessons/e03_judges/source_walkthrough.md) |
| 04 | [检索质量](lessons/e04_retrieval/README.zh.md) | 找到相关资料，就算找全了吗？ | [源码](lessons/e04_retrieval/source_walkthrough.md) |
| 05 | [证据忠实度](lessons/e05_faithfulness/README.zh.md) | 回答的每条声明都有依据吗？ | [源码](lessons/e05_faithfulness/source_walkthrough.md) |
| 06 | [答案质量](lessons/e06_answer_quality/README.zh.md) | 忠于证据的回答，为什么仍可能不合格？ | [源码](lessons/e06_answer_quality/source_walkthrough.md) |
| 07 | [失败定位](lessons/e07_failure_diagnosis/README.zh.md) | 错误从资料、检索还是生成开始？ | [源码](lessons/e07_failure_diagnosis/source_walkthrough.md) |
| 08 | [评测数据集](lessons/e08_datasets/README.zh.md) | 怎样把一次坏案例变成能反复使用的题目？ | [源码](lessons/e08_datasets/source_walkthrough.md) |
| 09 | [版本比较](lessons/e09_comparison/README.zh.md) | 分数上涨，怎样判断是不是改动带来的？ | [源码](lessons/e09_comparison/source_walkthrough.md) |
| 10 | [工具调用质量](lessons/e10_tool_evaluation/README.zh.md) | 工具名字对了，调用就对了吗？ | [源码](lessons/e10_tool_evaluation/source_walkthrough.md) |
| 11 | [任务完成度](lessons/e11_task_completion/README.zh.md) | 谁来确认代码真的修好了？ | [源码](lessons/e11_task_completion/source_walkthrough.md) |
| 12 | [跨轮约束](lessons/e12_conversation/README.zh.md) | 会话变长以后，哪些要求还应有效？ | [源码](lessons/e12_conversation/source_walkthrough.md) |
| 13 | [计划与协作](lessons/e13_planning/README.zh.md) | 子任务都完成，整体就完成了吗？ | [源码](lessons/e13_planning/source_walkthrough.md) |
| 14 | [执行效率](lessons/e14_runtime/README.zh.md) | 怎样评价等待、重试和后台工作？ | [源码](lessons/e14_runtime/source_walkthrough.md) |
| 15 | [裁判校准](lessons/e15_calibration/README.zh.md) | 评分器自己的判断可靠吗？ | [源码](lessons/e15_calibration/source_walkthrough.md) |
| 16 | [持续回归](lessons/e16_regression/README.zh.md) | 怎样把这些评测接回完整 Agent？ | [源码](lessons/e16_regression/source_walkthrough.md) |

[完整大纲](docs/curriculum.md) · [综合 Agent 项目](integrated_agent/README.md) · [飞书课程](https://my.feishu.cn/docx/V8CPdL3Y8oMZt4xJ8RCc4HfNnfb)

## 学完能做什么

- 给 Agent 定义可检查的成功条件，区分模型停止、工具成功与任务完成。
- 为 RAG 分别评价检索、证据忠实度和答案质量，并定位失败阶段。
- 构建有来源、有参考、有划分的评测集，比较两个版本是否改善。
- 评价工具调用、多轮约束、计划与效率，检查 LLM 裁判自身的误判。
- 顺着 DeepEval、Ragas 的关键源码解释分数，把评测接进自己的 Agent 项目。

## 怎样读

每课从一个具体困难开始，只展开解决它所需的机制。先读教材里的关键代码，再沿源码导读进入完整函数和框架实现。`code.py` 放本课场景，`eval.py` 放评测入口；需要进一步动手时，课末有“试一下”和练习。

前几课逐步构造 Agent，后面的评分课复用已出现的能力。完整运行时放在结课项目，知识库通过只读目录挂载，代码和评测可在 Docker 中运行。需要启动或换挂载时，可以直接让 Codex 根据项目配置处理。

## 参考

课程保留 [DeepEval 文档](https://deepeval.com/docs/metrics-introduction)与 [Ragas 文档](https://docs.ragas.io/en/stable/concepts/metrics/overview/)的概念依据。具体算法与接口以[固定源码版本](references/versions.json)为准，各课源码导读链接到相应实现。

[来源与许可](THIRD_PARTY.md)
