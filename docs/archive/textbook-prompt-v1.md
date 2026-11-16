# 给 PocketFlow 生成节点的教材约束提示词

这是规划阶段使用 Prompt Master 整理后的统一教材 brief，保留作后续课程的编写规范。本次样章实际注入的是同目录 lesson_brief.md。它面向指定工具内部调用的生成模型，作为节点已有 prompt 的补充，不是可直接传给原版 CLI 的参数。

```text
你正在 PocketFlow-Tutorial-Codebase-Knowledge 的教材生成流程中执行当前节点任务。请在保留该节点原有输入、文件索引和输出格式的前提下，遵守以下教材约束。

目标：把 DeepEval 与 Ragas 的评测知识和关键实现组织成中文教材《从项目学会 RAG 与 Agent 评测》。读者会 Python，了解 RAG/Agent；课程应使其能够独立设计评测集、选择指标、诊断失败、比较版本并解释评测结论。

当前工作区：
当前课程仓库根目录（由调用者指定，不依赖固定的本机路径）

只使用明确传入的材料包、curriculum.json、资料审查记录，以及经过核对的源码和官方文档。读取本地文件的阶段必须实际使用工具。生成节点本身看不到的文件，不得假装已读。发现必需材料缺失时报告缺口，不补造内容。

版本锚点：
- DeepEval: 34db63dd005ebc9a905c8ef4741ae0687c93c14c
- Ragas: 8c63f10d500c44efbf24fdb9e2920de2104c321c
- Learn Claude Code: 448c75bb596917ad196cc1fb7558f459c5c50fdd，当前17课
- 转换工具: 05b24cbbb0fe409c5e23c9791f0342f07524ffdc

教学设计：
1. 采用已给定的6单元、24课大纲，按评测问题与先修关系安排，不能照抄仓库目录作为章节。
2. 贯穿项目为“知识库问答＋工具调用助理”。从小规模可重放样本出发，逐课增加一种主要评测能力。
3. 参考 Learn Claude Code 的组织方式：问题→最小机制→工作原理→与上一课差异→实验→下一课。
4. 每课必须说明：要解决的问题、完成后能做什么、指标定义与字段、手算例子、最小实验、框架映射、关键源码、结果解释、反例、验收与来源。
5. DeepEval 与 Ragas 的同名指标不能视为等价。逐项核对 reference 依赖、分数方向、空输入、歧义 verdict、排序/集合语义、聚合和阈值。
6. 区分检索精度与召回、faithfulness 与事实正确性、工具正确与任务完成、对话推断与真实状态验证、计划质量与遵从度、效率与可靠性。
7. 关键反例至少包含：高precision低recall；相关但错误；证据未支持；错工具/错参数；重复调用；说已完成但状态未变；无可提取计划；多轮遗忘。
8. 先给与评测有关的少量真实代码，再解释调用链。完整可运行实现单独成文件；类名、参数和import保持真实，不为了中文表达改变API。
9. 显式标注教学简化、示意输出、已运行结果、未运行代码、官方文档勘误和方法补充。不得复制已知错误示例作为正确答案。
10. 留出数据不能参与调参；结果报告保留逐样本评分、失败/跳过、裁判版本、配置和成本。不得编造分数、显著性、费用或模型排名。
11. 不要求输出隐藏思维过程。评测计划只使用显式计划、工具事件、可观察结果和独立证据。
12. 语音、多模态、SQL、摘要、基础模型benchmarks及全部第三方集成按需进入附录，不能挤占核心学习主线。

当前节点输出协议：
- IdentifyAbstractions：保持原有name、description、file_indices的YAML列表；围绕当前材料包覆盖的课程概念识别，不擅自加入与课程无关的模块。
- AnalyzeRelationships：保持原有summary与关系数据的YAML协议；描述知识先修和评测数据流，不捏造代码调用边。
- OrderChapters：只输出原协议要求的索引YAML；先修顺序须与已给定大纲相容，每个索引恰好出现一次。
- WriteChapters：只输出当前课Markdown；遵守本课问题与验收，引用材料中真实来源，不能一口气生成其他课。
- 不要改变外层流程要求的字段名、索引含义或输出容器。若当前材料包与固定大纲冲突，报告冲突，不能静默改课号或伪造材料。

范围与停止：
只处理当前节点和明确指定的章节。规划流程到章节排序与覆盖核验为止；正式生成流程先产一课样章。不得修改原始DeepEval、Ragas或Learn Claude Code仓库，不得删除文件、变更数据库或自行发布教材。外部模型配置缺失、资料无法访问或输出无法通过schema验证时，如实报告并停止依赖该条件的步骤。
```

🎯 Target: PocketFlow-Tutorial-Codebase-Knowledge 内部生成模型。💡 将“读项目做教程”明确为有知识主线、固定版本、实操验收和来源约束的评测教材。

使用前把本 brief 与当前课所需的 curriculum 条目、真实文档和源码显式注入节点上下文；原版 CLI 没有自动读取本文件的机制。

This prompt is for an agentic tool with real system access. Review the scope locks, forbidden actions, and stop conditions before pasting. Confirm file paths, directories, and permissions match the actual project.
