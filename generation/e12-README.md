# 第12课教材生成与审校

PocketFlow读取本课19个白名单材料文件，实际运行固定原版FetchRepo → BindLesson → WriteChapters → CombineTutorial，调用本机已登录Codex一次。大纲与当前课已经固定，未运行主题识别、关系分析或章节排序。

- [生成约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e12-brief.md)
- [原始生成稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e12_conversation/01_多轮_压缩与记忆_约束还在吗.md)
- [实际节点、调用与输入哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e12-provenance.json)
- [主文审校记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e12-humanizer.json)
- [发布正文](../lessons/e12_conversation/README.zh.md)

技术审校核对真实源码片段，明确省略处，修正两项阻塞桥服务应分终端启动的说明。生成器尾注只从发布稿删除，原稿保留。主文完整通读后做humanizer润色，六部分与六步共12个审校单元；87个代码块、行内代码和链接目标片段按顺序保持一致，代码外2649个汉字。删去铺垫、无信息对比与重复结尾，保留具体变量、状态和错误。

图只展开本课上下文与磁盘记忆支路，不代替整套Agent架构。可编辑drawio XML与PNG来自同一节点关系，已检查并打开预览；PNG为本地生成预览，未声称draw.io Desktop导出。对应记录见[e12-diagram.json](https://github.com/lovits/learn-agent-evaluation/blob/main/references/e12-diagram.json)。

模型输入字符审查与业务验收分开。固定两路径、区间记录增量路径、原生模拟器、构造对话和确定性协议fixture分别记录，不把旧14步协议、暂停中断与32步实验合并为受控性能比较。教材生成时的材料哈希是当时快照；生成之后补齐的运行结果和源码附页按实际最终证据技术审校，不能说生成器预先读到了尚未发生的运行。
