# 第16课教材生成与审校

本课使用固定版本 PocketFlow-Tutorial-Codebase-Knowledge，实际执行 FetchRepo → BindLesson → WriteChapters → CombineTutorial，复用宿主已登录 Codex，生成模型实际请求一次。课程和大纲早已确定，没有运行主题识别、关系分析或章节排序节点。

- [生成约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-brief.md)
- [未改写原稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e16_regression/01_%E7%BB%BC%E5%90%88%E5%9B%9E%E5%BD%92_%E4%BB%8E%E8%BF%90%E8%A1%8C%E8%AF%81%E6%8D%AE%E5%88%B0%E5%8F%91%E5%B8%83%E9%97%A8%E7%A6%81.md)
- [节点、材料与哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-provenance.json)
- [技术审校后、润色前](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-technical-before-humanizer.md)
- [humanizer记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-humanizer.json)
- [发布正文](../lessons/e16_regression/README.zh.md)

生成前已经完成正常、错误、边界任务与两轮原生评分，运行摘要作为材料输入。技术审校把原稿中的示意变量与简写分发换成实际代码节选，补齐省略说明，拆开模型桥与构建的终端操作，增加 Docker 断网练习命令。没有修改原 Agent 记录来迎合分数。

humanizer从当前完整文件通读后审校六部分、六步，共12个单元，无遗漏。66个代码、行内代码与链接目标前后按顺序一致；正文代码外2245个汉字。改写去掉机械职责列表与重复句式，保留讲师编排、模型执行、评分范围和失败来源。

综合图使用原生draw.io XML，预览从同一XML渲染并目视核对。本机没有draw.io Desktop，因此PNG明确作为预览，未冒充Desktop导出；可编辑原图保留。框架详细调用链、实验结果、练习/答案与总体架构单独成页，避免把正文写成一张验收清单。
