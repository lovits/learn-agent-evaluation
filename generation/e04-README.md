# 第4课教材生成与审校

固定版本PocketFlow-Tutorial-Codebase-Knowledge执行FetchRepo、BindLesson、WriteChapters、CombineTutorial。既定大纲无需再次识别抽象或排序。输入限本课代码、数据、实测摘要、源码导读、练习与知识库示例；没有整套后续Agent。

`uv run python tools/generate_lesson.py --lesson e04`生成原稿。原稿、输入输出哈希和实际调用数保存在generation/output/e04_retrieval与generation/e04-provenance.json。发布版通读后按humanizer润色，代码、命令、数据与链接另按实验核对。

真实Agent轨迹、受控扰动、初次失败与修复后结果分别保留。教材生成调用与评测模型请求分开计数。

本轮整套课程修订再次实际生成1次，旧原稿、brief与凭证在generation/archive/e04-before-course-revision，当前凭证单列本轮调用。原执行代码、样本及固定报告保持一致，本轮未新增Agent或裁判测量。六部分正文与六步代码均完成humanizer审校，详见[阶段验收](../docs/course-revision-validation.md)。
