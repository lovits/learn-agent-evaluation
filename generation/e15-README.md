# 第15课教材生成与审校

PocketFlow读取本课12份白名单材料，实际执行固定版本的FetchRepo → BindLesson → WriteChapters → CombineTutorial，复用宿主已登录Codex，真实调用生成模型一次。当前课程和大纲已确定，未运行主题识别、关系分析或章节排序。

- [生成约束](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e15-brief.md)。
- [保留原稿](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/output/e15_calibration/01_裁判校准_分数对了_标准也对了吗.md)。
- [实际节点与输入哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e15-provenance.json)。
- [humanizer审校记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e15-humanizer.json)。
- [发布正文](../lessons/e15_calibration/README.zh.md)。

生成时48次正式裁判响应已完成，选读与运行记录均作为输入；没有先写成功结论再补实验。技术审校补回样本验证状态条件，修正留出Dataset变量、开发错误信息和κ计算片段，去掉不必要的流程图及生成器页脚。实际评分代码、数据与冻结协议没有在实验后修改。

整篇从当前文件通读后按humanizer审校六部分、六步，共12个单元，无遗漏部分。52个代码、行内代码与链接目标片段前后按顺序一致。正文代码外2079个汉字。删去重复收尾与夸张对比，补清误放行、未评分与类别分布，保留构造来源和人工审核未完成的边界。

本课仅改裁判，六个短代码段已经能说明调用关系，因此使用简短对照表，不添加装饰图。框架源码、练习与答案、实测和验收保留独立附页；全项目架构在综合课展开。
