# 从编程 Agent 学评测

从一个循环和 Bash 开始，让 Agent 真正处理文件，再问：怎样知道它做得对？

课程沿 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的思路逐步增加机制。知识库使用 [Datawhale TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/main/content/TinyRAG)，实际评测框架统一使用 DeepEval；同时从 Ragas 的文档与源码学习指标原理和数据集设计。适合会 Python、了解 RAG 与 Agent，想系统学习评测的读者。

## 课程

| 课 | 核心知识点 | 要解决的问题 |
|---|---|---|
| 01 | [定义成功](course/e01_success/README.zh.md) | 模型停下了，任务就完成了吗？ |
| 02 | [保存一次运行](course/e02_samples/README.zh.md) | 怎样把 Agent 的一次工作变成评测样本？ |
| 03 | [准备评测数据](course/e03_datasets/README.zh.md) | 怎样让题目代表你真正关心的能力？ |
| 04 | [给样本评分](course/e04_scoring/README.zh.md) | 什么时候用规则，什么时候请模型判断？ |
| 05 | [接通知识库](course/e05_knowledge_context/README.zh.md) | 检索出的资料，最后有哪些真的交给了模型？ |
| 06 | [上下文相关性与排序](course/e06_context_precision/README.zh.md) | 找到了资料，为什么还要看相关性和顺序？ |
| 07 | [上下文覆盖与召回](course/e07_context_recall/README.zh.md) | 资料看起来都相关，为什么问题仍答不全？ |
| 08 | [回答对上下文的忠实度](docs/curriculum.md#08-回答对上下文的忠实度) | 回答里的每条事实，资料都支持吗？ |
| 09 | [答案质量](docs/curriculum.md#09-答案质量) | 忠于资料，为什么仍可能没有回答好问题？ |
| 10 | [上下文干扰与故障定位](docs/curriculum.md#10-上下文干扰与故障定位) | 答案错了，应该先改资料、检索还是生成？ |
| 11 | [工具调用质量](docs/curriculum.md#11-工具调用质量) | 名字选对了，工具就用对了吗？ |
| 12 | [任务完成度](docs/curriculum.md#12-任务完成度) | 怎样确认 Agent 真的交付了用户要的结果？ |
| 13 | [会话上下文与约束保持](docs/curriculum.md#13-会话上下文与约束保持) | 用户改了要求以后，Agent 还记得哪一版？ |
| 14 | [校准 LLM 裁判](docs/curriculum.md#14-校准-llm-裁判) | 评分器自己的判断可信吗？ |
| 15 | [比较两个版本](docs/curriculum.md#15-比较两个版本) | 分数变高，怎样判断改动真的有用？ |
| 16 | [综合项目与持续回归](docs/curriculum.md#16-综合项目与持续回归) | 怎样让一次修复成为以后不会再犯的经验？ |

[飞书课程目录](https://my.feishu.cn/drive/folder/Cap7fQoFVlH3Y3dtgJ4cP55dnFg) · [完整大纲](docs/curriculum.md)

## 学完能做什么

- 把用户目标写成可检查的成功条件，从运行记录构造评测样本。
- 建立有来源、有参考、有划分的数据集，选用规则和 LLM 裁判。
- 评价上下文是否相关、排得合理、覆盖充分，以及回答是否有依据、正确、完整。
- 分开判断工具调用、任务完成和多轮约束，用证据定位失败。
- 读懂 DeepEval、Ragas 的关键判分过程，校准裁判、比较版本并接入持续回归。

## 怎样读

每课从一个具体困难开始，接着给出最小机制，再沿关键代码解释它怎样工作。教材只展开当前知识点，完整函数和框架依据放在源码导读，动手问题及参考解另放。

一条任务贯穿 Agent 与评分器：Agent 负责工作，评分器根据实际记录和结果判断。后续课程复用已有能力，最后组合成完整项目。代码可在 Docker 中执行，知识库通过只读目录挂载。

[来源与许可](THIRD_PARTY.md) · [固定源码版本](references/versions.json)
