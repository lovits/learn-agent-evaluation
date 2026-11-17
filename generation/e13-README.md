# 第13课教材生成与审校

PocketFlow读取本课18个白名单材料文件，实际执行固定原版FetchRepo → BindLesson → WriteChapters → CombineTutorial，调用本机已登录Codex一次。当前课与大纲已经固定，未运行主题识别、关系分析或章节排序。实际文件数以生成凭证input_manifest为准。

- [写作约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e13-brief.md)。
- [原始稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e13_planning/01_计划_依赖与交接_拆开就能做完吗.md)。
- [实际节点、调用与输入哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e13-provenance.json)。
- [humanizer记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e13-humanizer.json)。
- [发布正文](../lessons/e13_planning/README.zh.md)。

技术审校修正生成稿的错误图源仓库链接，以真实源码替换缩略示意片段并注明省略；补清类型数组、任务提交范围、最后交接与早先失败的区别。生成器尾注只从发布稿删除，原稿保留。通读当前发布候选文件后进行humanizer润色，六部分加六步共12个审校单元；116个代码、行内代码及链接目标片段顺序不变，代码外3112个汉字。正文按Learn Claude Code的具体问题、关键短代码和运行观察组织，完整指标细节、错误与数字留在附页。

输入材料快照中正式应用尚在运行；生成器并未预先读到随后完成的验收和裁判结果。正式23次应用响应、30次评分响应及失败历史随后按真实记录技术补齐；这部分不能冒充生成当时的材料。当前生成凭证哈希识别当时快照，不要求等于后续更新的运行附页。

结构图使用本课原生drawio XML及同一节点关系渲染的PNG，已打开并检查。PNG是本地预览，未使用draw.io Desktop导出。范围是新增规划、依赖、交接与分开验收支路，完整17项机制仍留综合项目。来源与哈希见[e13-diagram.json](https://github.com/lovits/learn-agent-evaluation/blob/main/references/e13-diagram.json)。
