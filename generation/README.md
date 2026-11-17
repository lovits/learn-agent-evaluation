# 教材生成

`tools/generate_lesson.py` 使用固定版本 PocketFlow-Tutorial-Codebase-Knowledge 的 FetchRepo、WriteChapters 和 CombineTutorial 节点，从本课源码生成草稿。BindLesson 绑定已确认的大纲范围，不重排课程。

草稿保存在私有生成目录，正式教材在 `course/`。逐课 provenance 保存实际模型调用与输入输出哈希。正式课文按源码核对、压缩和润色，草稿不直接替代发布稿。

[课程范围](../docs/curriculum.md) · [制作规范](../docs/course-specification.md)
