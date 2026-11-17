# PocketFlow 教材编排

课程以 curriculum.json 保存学习顺序与每课核心问题，逐课教材和源码导读是审校后的内容。PocketFlow-Tutorial-Codebase-Knowledge 读取这些材料并组织章节。

`tools/organize_course.py` 使用固定上游 FetchRepo 与 CombineTutorial，中间的 BindCourse 绑定已审校章节，输出到 generation/output/course。这个入口只做编排，不请求新模型，也不生成运行成绩。

`tools/generate_lesson.py` 用于按当前写作标准生成新的逐课草稿，调用原生 WriteChapters；它使用本机模型接口，输出与正式教材分开。

写作要求见[正文标准](../references/textbook-writing-standard.md)，课程顺序见[大纲](../docs/curriculum.md)。供应商接口适配在项目 tools 中，上游节点保持原样。
