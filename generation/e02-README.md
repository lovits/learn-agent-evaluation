# 第2课生成与正文重写

首次生成稿和凭证保存在generation/archive/e02-before-course-revision。本轮按[统一写作标准](../references/textbook-writing-standard.md)重写，实际使用FetchRepo → BindLesson → WriteChapters → CombineTutorial，写作调用1次，大纲识别与排序未重跑。

当前原稿在generation/output/e02_tools_traces，技术审校后发布在lessons/e02_tools_traces/README.zh.md。六节正文与六步代码共12节全部完成humanizer审校；润色时保护代码、命令、行内代码和链接。原报告保留，未新增Agent或裁判实验。生成输入、调用和发布哈希在generation/e02-provenance.json，验证见[阶段验收](../docs/course-revision-validation.md)。

```sh
uv run python tools/generate_lesson.py --lesson e02
```
