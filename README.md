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
| 08 | [回答对上下文的忠实度](course/e08_faithfulness/README.zh.md) | 回答里的每条事实，资料都支持吗？ |
| 09 | [答案质量](course/e09_answer_quality/README.zh.md) | 忠于资料，为什么仍可能没有回答好问题？ |
| 10 | [上下文干扰与故障定位](course/e10_rag_diagnosis/README.zh.md) | 答案错了，应该先改资料、检索还是生成？ |
| 11 | [工具调用质量](course/e11_tool_quality/README.zh.md) | 名字选对了，工具就用对了吗？ |
| 12 | [任务完成度](course/e12_task_completion/README.zh.md) | 怎样确认 Agent 真的交付了用户要的结果？ |
| 13 | [会话上下文与约束保持](course/e13_conversation/README.zh.md) | 用户改了要求以后，Agent 还记得哪一版？ |
| 14 | [校准 LLM 裁判](course/e14_judge_calibration/README.zh.md) | 评分器自己的判断可信吗？ |
| 15 | [比较两个版本](course/e15_version_comparison/README.zh.md) | 分数变高，怎样判断改动真的有用？ |
| 16 | [综合项目与持续回归](course/e16_regression/README.zh.md) | 怎样让一次修复成为以后不会再犯的经验？ |

[完整大纲](docs/curriculum.md)

## 能学到哪些知识点与原理

- **Agent 的工作原理**：模型、工具与执行结果怎样组成循环；停止条件、权限边界和运行轨迹各自解决什么问题。
- **评测的基本组成**：任务目标、成功条件、运行证据、参考答案与评分标准之间的关系；过程质量和最终结果为什么要分别判断。
- **评测样本与数据集**：单次运行如何表示为评测样本；题目来源、人工审核、去重与能力覆盖；开发集、留出集和数据泄漏。
- **规则评分与 LLM 裁判**：确定性检查与语义判断的适用范围；G-Eval 的评价步骤、量表、阈值和评分理由；异常与缺失分数的含义。
- **RAG 与上下文构建**：文档分块、向量检索和上下文组装的基本过程；检索候选与模型实际看到的资料有什么区别；如何保留来源和版本。
- **上下文相关性与排序**：Precision、AP、倒数排名和 NDCG 的计算思路；相关资料的数量与排列位置如何影响检索质量。
- **上下文覆盖与召回**：必要事实、参考答案与证据归因；如何判断资料是否足以覆盖问题，以及精度与召回各自关注什么。
- **回答忠实度**：将回答拆成事实声明，逐条核对上下文支持，再聚合评分；忠实度与事实正确性的区别。
- **答案质量**：回答相关性、事实精度、事实召回、F 分数与完整性；为什么有依据的回答仍可能没有答好问题。
- **RAG 故障定位**：资料缺失、检索遗漏、上下文组装和生成错误的区别；通过干扰样本与单变量对照追踪失败原因。
- **工具调用与任务完成度**：工具选择、参数、顺序和执行结果的评价方法；如何结合业务条件、文件产物与行为证据判断任务是否完成。
- **多轮会话评测**：历史消息与实际模型输入的区别；用户约束如何新增、覆盖和撤销；知识保持与会话完整性的评价思路。
- **LLM 裁判校准**：人工参考标签、误判、分歧与阈值；等价表达、位置变化和指令干扰如何影响裁判判断。
- **版本比较与持续回归**：同题配对、重复运行、题族重采样和不确定性；如何同时考虑质量与成本，并将复核后的失败样本纳入回归集。
- **DeepEval 与 Ragas 的指标原理**：从文档和关键源码理解样本字段、证据提取、逐项判断与分数聚合；实际评测统一接入 DeepEval，借 Ragas 对照理解指标定义与适用边界。

## 仓库结构

```text
learn-agent-evaluation/
├── README.md                    课程总览、知识点与文件导航
├── course/
│   ├── e01_success/             最小 Agent 循环与成功条件
│   ├── e02_samples/             工具、权限、轨迹与统一样本
│   ├── e03_datasets/            评测数据集
│   ├── e04_scoring/             规则评分与 LLM 裁判
│   ├── e05_knowledge_context/   Agent 接入 TinyRAG
│   ├── e06_context_precision/  上下文相关性与排序
│   ├── e07_context_recall/      上下文覆盖与召回
│   ├── e08_faithfulness/        回答忠实度
│   ├── e09_answer_quality/      答案质量
│   ├── e10_rag_diagnosis/       RAG 故障定位
│   ├── e11_tool_quality/        工具调用质量
│   ├── e12_task_completion/     任务完成度
│   ├── e13_conversation/        多轮约束保持
│   ├── e14_judge_calibration/   裁判校准
│   ├── e15_version_comparison/  版本比较
│   ├── e16_regression/          综合 Agent 与持续回归
│   ├── run.py                  前两课的任务运行入口
│   └── grade.py                前两课的记录评分入口
├── eval_course/                 模型调用、裁判适配、TinyRAG 与记录等共享代码
├── knowledge_base/              可挂载的知识库资料
├── docs/                        完整大纲、课程规范与综合项目讲解
├── references/                  上游文档、指标源码依据与固定版本
├── vendor/                      课程引用的上游代码片段
├── generation/                  PocketFlow 教材组织输入与生成依据
├── tools/                       教材生成、模型桥接和绘图工具
├── tests/                       代码检查，独立于课程质量评测
├── Dockerfile                   课程运行镜像
└── compose.yaml                 知识库、工作区与运行记录的挂载配置
```

### 每课的文件结构

下面是各课共有的结构。`code.py` 与 `eval.py` 分开，方便对照“被观察的过程”和“判断它的依据”；主教材不混入运行报告。

```text
course/eXX_topic/
├── README.zh.md            教材：问题、解决方案、工作原理与关键代码
├── code.py                 本课机制或实验入口，按需复用已有 Agent
├── eval.py                 本课评分、指标调用或证据检查
├── cases.jsonl             任务、参考与评测样本
├── source_walkthrough.md   关键调用链及上游文档、源码依据
├── exercises.md            动手问题
├── solutions.md            参考解释
├── assessment.md           独立的评测样本说明与运行结果
├── assessment.json         对应的结构化记录
└── images/                 两张关键流程图及源文件
```

少数课程有额外文件：第 2 课的 [tools.py](course/e02_samples/tools.py) 实现工具与权限边界，[samples.py](course/e02_samples/samples.py) 转换评测样本；第 3 课的 [generate.py](course/e03_datasets/generate.py) 准备候选题；第 13 课的 [scenario.json](course/e13_conversation/scenario.json) 保存会话场景。其余配套文件在各课源码导读中解释。

### Agent 的代码从哪里读

| 部分 | 文件 | 负责什么 |
|---|---|---|
| 最小循环 | [第 1 课 code.py](course/e01_success/code.py) | 请求模型、执行 Bash、把结果交回模型 |
| 具名工具循环 | [第 2 课 code.py](course/e02_samples/code.py) | 复用的 Agent 主循环，记录工具动作与返回 |
| 工具与权限 | [第 2 课 tools.py](course/e02_samples/tools.py) | 文件读写、Bash 分发与文件路径边界 |
| 评测样本转换 | [第 2 课 samples.py](course/e02_samples/samples.py) | 将运行记录转换为 DeepEval 样本 |
| 知识库接入 | [第 5 课 code.py](course/e05_knowledge_context/code.py) · [tinyrag.py](eval_course/tinyrag.py) | 增加检索工具，保存检索结果与实际送入模型的上下文 |
| 综合项目 | [第 16 课 code.py](course/e16_regression/code.py) · [eval.py](course/e16_regression/eval.py) | 组合既有 Agent 与评测逻辑，形成回归流程 |

上游原代码与课程代码的对应关系见每课源码导读；本地参考片段位于 [vendor](vendor/) 与 [references/upstream](references/upstream/)，固定版本见 [versions.json](references/versions.json)。

## 学完能做什么

- 把用户目标写成可检查的成功条件，从运行记录构造评测样本。
- 建立有来源、有参考、有划分的数据集，选用规则和 LLM 裁判。
- 评价上下文是否相关、排得合理、覆盖充分，以及回答是否有依据、正确、完整。
- 分开判断工具调用、任务完成和多轮约束，用证据定位失败。
- 读懂 DeepEval、Ragas 的关键判分过程，校准裁判、比较版本并接入持续回归。

## 怎样读

每课从一个具体困难开始，接着给出最小机制，再沿关键代码解释它怎样工作。教材只展开当前知识点，完整函数和框架依据放在源码导读，动手问题及参考解另放。

一条任务贯穿 Agent 与评分器：Agent 负责工作，评分器根据实际记录和结果判断。后续课程复用已有能力，最后组合成[完整项目](docs/integrated-project.md)。代码可在 Docker 中执行，知识库通过只读目录挂载。

[来源与许可](THIRD_PARTY.md) · [固定源码版本](references/versions.json)
