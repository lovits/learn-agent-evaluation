# 第14课教材生成与审校

PocketFlow读取本课21个白名单材料文件，实际执行固定原版FetchRepo → BindLesson → WriteChapters → CombineTutorial，调用本机已登录Codex一次。大纲与当前课固定，未运行主题识别、关系分析或章节排序。

- [生成约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e14-brief.md)。
- [原始稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e14_runtime/01_后台_调度与效率_少几步就更好吗.md)。
- [实际节点、调用和材料哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e14-provenance.json)。
- [humanizer全篇审校记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e14-humanizer.json)。
- [发布正文](../lessons/e14_runtime/README.zh.md)。

生成时4条正式应用、独立验收和12次效率评分响应均已完成，材料附页包含实际结果。后续出版文字及验证记录按最终事实补齐，输入哈希仍识别生成时的快照。原稿完整保留。

技术审校把误用的“一次模型问答”标题改成“相对上一课的变更”，修正id字段、消息/异常范围和通知检查代码，使用真实源码选段并注明省略；补齐构建、阅读器命令和图源的项目绝对链接。正文以后台占位、真实结果、调度接收和实际执行为主线，数字及完整SDK调用链保留在附页。

完整通读当前发布候选文件后用humanizer审校，六部分和六步共12个单元，64个代码、行内代码与链接目标片段按顺序不变，代码外2347个汉字。删去多余比喻、阶段铺垫和重复结尾，保留实际状态、错误与适用边界；无未覆盖章节。

图使用原生drawio XML与同一9节点/12边关系的PNG预览，已打开检查。Desktop未安装，未声称Desktop导出。图只展开本课新增后台/调度与验收关系，完整17机制架构留综合项目。记录见[e14-diagram.json](https://github.com/lovits/learn-agent-evaluation/blob/main/references/e14-diagram.json)。
