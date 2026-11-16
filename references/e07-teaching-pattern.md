# 第7课采用的 Learn Claude Code 写作方式

实际细读固定提交448c75bb596917ad196cc1fb7558f459c5c50fdd的s01、s02、s07、s08中文正文，并对照s01循环、s02分发、s07按需加载的对应代码。文件哈希与阅读范围见e07-learn-claude-code-reading.json。本课借鉴讲解方法，不提前引入压缩、记忆或其他未讲机制。

## 从上游提取的写作动作

- s01先写“模型只给命令、不会自己执行”的具体困难，再按消息初始化、模型调用、判停、执行工具、回填结果拆成五步。每步先交代作用，再给对应短代码。
- s02先比较已有Bash与具名工具的接口成本，指出循环里哪一行发生变化，再解释dispatch map。相对上一课的变化集中放表格；试验任务带观察问题。
- s07先举“所有文档塞system prompt”的场景，再解释目录与正文进入上下文的位置。scan、catalog、load分别讲，读者可以沿一条信息流跟到实际调用点。
- s08按可以恢复的信息与有损摘要组织顺序，逐层说明触发条件、保留内容、代价，再放回循环；实验提示读者观察具体磁盘产物。

## 本课的正文合同

标题之后只给一句本课要解决的问题。正文顺序采用：问题 → 解决方案 → 工作原理（分步代码）→ 相对第6课的变更 → 试一下 → 接下来。完整代码、实测详情、框架源码和练习以链接提供，正文不先变成指标词典或验收清单。

问题使用“同样漏了限额，究竟是资料没有、检索漏掉，还是模型没用对”。工作原理每步只解释一个新动作：固定任务与资料快照；文档移除；检索结果过滤/追加；生成指令变化；插回既有循环；独立读取产物并对照三层记录。每个代码块控制在约5至15行，变量与函数都对应实际代码；删略时说明删了什么。

评分器在读者已看懂阶段证据后出现。DeepEval上下文相关性和Ragas NoiseSensitivity只解释它们能帮忙回答的问题、输入、分数方向与局限；逐prompt/schema/聚合细节留源码导读。真实模型没有被噪声带偏也照实写，不把注入意图当结果。

试验命令运行现有容器入口；观察点必须具体到available_documents、retrievals.before/after、artifact和events。相对前课明确保留什么，只增什么。主文以短句和自然段带读者动手，避免“能力地图”“验收体系”一类抽象汇报口吻。

上游可核对：[s01](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/README.zh.md)、[s02](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/README.zh.md)、[s07](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s07_skill_loading/README.zh.md)、[s08](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s08_context_compact/README.zh.md)。
