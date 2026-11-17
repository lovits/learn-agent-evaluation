# PocketFlow 教材编排

`curriculum.json` 保存完整16课学习顺序与每课核心问题。逐课实现完成后，教材与源码导读进入人工审校；`ready` 表示已迁移，`planned` 表示还在新大纲中。

`tools/generate_lesson.py` 使用固定上游的 FetchRepo、WriteChapters 与 CombineTutorial，中间用 BindLesson 绑定已确定的本课范围。它读取真实代码，用本机已登录的模型生成草稿。原始草稿与正式教材分开；模型请求数、输入哈希和输出哈希保存在逐课 provenance 文件，不把生成结果直接当成审校后的教材。

`tools/organize_course.py` 使用 FetchRepo 与 CombineTutorial，由 BindCourse 组织已经审校的 `ready` 章节。它不请求模型，也不生成运行成绩。新大纲下目前只编排第1课，后续课不会误用原编号内容。

[正文标准](../references/textbook-writing-standard.md) · [大纲](../docs/curriculum.md) · [制作规范](../docs/course-specification.md)
