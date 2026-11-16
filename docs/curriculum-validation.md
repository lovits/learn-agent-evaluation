# 课程设计核验（2026-11-16历史记录）

日期：2026-11-16。当时核验课程设计、生成流程与阅读器，没有把16课编程Agent实验当成已执行。

- 原24课恰好各映射一次，知识文字保留于新curriculum.json。
- Learn Claude Code的17个机制均有明确引入课程，状态为待实现/验证。
- PocketFlow原版规划节点生成16主题、22条关系与完整顺序；课程适配节点生成详细大纲。
- 共4次真实Codex生成调用；首次有效裸YAML通过围栏适配恢复，原响应与哈希保留。
- 每课均包含评测对象、知识点、Agent代码增量、实验、验收、来源六项。
- 29份固定源码引用已与对应Git提交的原始对象逐字节核对。
- 规划输入与公开大纲哈希核验通过；原始模型稿和审校稿分开保存。
- 本地20项SDK/阅读器/配置测试通过（6.31秒）；Ruff通过。

机器可读记录在docs/curriculum-validation.json；源码引用目录在references/curriculum-sources.json。
PocketFlow原始输出、调用与节点凭证在generation/output/curriculum_v2。

本页记录此前课程设计的核验。旧Faithfulness样章已按新指令清理；当前课程运行验收见第1课验证记录。
新编程Agent的功能等价、真实模型成绩与各课实验仍待按制作计划完成。

参见 [课程大纲](curriculum.md)、[制作计划](course-production-plan.md)、
[生成流程说明](../generation/curriculum-README.md)与 [已有样章验证](validation.md)。
