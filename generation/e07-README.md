# 第7课教材生成与审校

先细读固定版本Learn Claude Code的s01、s02、s07、s08中文正文，并对照循环、分发和按需加载代码，再据此限定本课写法。[实际阅读与写作对应](../references/e07-teaching-pattern.md)列出来源、章节和讲解动作；不把“参考过”当成已迁移所有机制。

本课真正运行PocketFlow的FetchRepo → BindLesson → WriteChapters → CombineTutorial，实际教材模型调用1次。既定16课不重新做主题识别与排序，vendor节点未改。输入是当前故障代码、必要的第4课循环、六组实验摘要、评分源码导读、练习/答案、写作方式与固定版本信息，没有整套集成Agent。

[原始生成稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e07_failure_diagnosis/index.md)与[生成凭证](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e07-provenance.json)分别保留。运行：

```sh
uv run python tools/generate_lesson.py --lesson e07
```

[发布正文](../lessons/e07_failure_diagnosis/README.zh.md)采用问题、解决方案、工作原理、相对前课变更、试一下、接下来六部分；工作原理有六个短代码步骤。技术审校逐段核对实际实现，修正不完整的函数签名片段和产物校验片段，补充评分配置、缺信息分数的解释。随后humanizer通读并润色12个主节/步骤，未审校小节0，保持代码块、行内代码、命令和链接目标。

原始生成稿不被审校覆盖。输入哈希、生成响应哈希、发布版哈希分开保存；完整prompt/response在Git忽略的generation/private/e07，凭据留宿主机。正文先讲问题和代码，详细实验、指标公式与验收放附页。

本轮整套课程修订再次实际生成1次，旧原稿、brief与凭证在generation/archive/e07-before-course-revision，当前凭证单列本轮调用。原执行代码、样本及固定报告保持一致，本轮未新增Agent或裁判测量。六部分正文与六步代码均完成humanizer审校，详见[阶段验收](../docs/course-revision-validation.md)。
