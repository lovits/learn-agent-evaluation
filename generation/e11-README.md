# 第11课教材生成与审校

PocketFlow实际读取本课16个白名单材料文件，运行固定原版FetchRepo → BindLesson → WriteChapters → CombineTutorial，调用本机已登录Codex一次。没有运行主题识别、关系分析与章节排序，因为16课大纲和当前课均已确定。

- [生成约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e11-brief.md)
- [原始生成稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e11_task_completion/01_任务完成_先检查_再允许结束.md)
- [生成凭证与输入哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e11-provenance.json)
- [发布正文](../lessons/e11_task_completion/README.zh.md)
- [上游阅读清单](../references/e11-reading.json)

技术审校修正原稿的WorkflowOutput类型名、不存在的reader服务名和两个阻塞桥服务的启动终端说明，删除生成器包装尾注，核实实际运行数值。原稿完整保留。源码导读也核对了Ragas比较schema的reason没有传给MetricResult这一固定版本行为。

humanizer先完整读取当前正文，再审校六部分与六个关键步骤，共12个审校单元。删去泛化对比、开场铺垫和重复结尾，用实际变量和状态说明。润色前后78个代码块/行内代码/链接目标片段按顺序完全一致。正文代码之外约2287个汉字，保留六个二级标题和六步真实关键代码。各附页另做技术与文字复核，不将这次正文humanizer统计扩大成所有附页均执行同样保护校验。

本课没有新增图片。公开检查、续轮和最终验收的少量分支用短代码与表格表达；完整会话架构留到集成项目统一讲解。生成材料没有包含未来课程代码、真实凭据或运行时私有验收目录。原运行镜像源码在[generation/archive/e11-agent-runtime](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/archive/e11-agent-runtime/runtime_sources.json)归档；本次新增声明式冲突预检单独实测，未把旧Agent记录重写成新运行。
