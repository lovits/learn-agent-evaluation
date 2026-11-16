# PocketFlow 样章生成

本项目使用固定 commit 的 **PocketFlow-Tutorial-Codebase-Knowledge**，
原版节点位于 vendor/pocketflow_tutorial，保留上游 MIT 许可。

生成入口为 tools/generate_lesson.py：

1. 原版 FetchRepo 读取明确白名单内的课程代码、固定证据和源码快照。
2. BindLesson 将已批准的 s07 教学任务绑定到文件索引。
3. 原版 WriteChapters 实际调用生成模型撰写单课。
4. 原版 CombineTutorial 写出章节与索引。

本课的课程内容和顺序已经确定，故没有重新运行自动抽象识别、关系分析和章节排序。
不能把实际运行的四节点流程描述为完整六节点自动探索。

此次生成使用用户确认的宿主机 Codex 登录。调用为临时只读执行，
prompt 已包含全部材料，不要求模型操作文件；凭据没有被复制到容器或仓库。
原版节点源码没有改动，只替换了模型传输函数并注入本课 brief。

## 生成与审核的分工

- lesson_brief.md：本课目标、边界、必要事实、实验命令和验收约束。
- provenance.json：实际调用数量、节点、输入/输出哈希、耗时和生成器 commit。
- output/s07_faithfulness/：原始 PocketFlow 输出，保留以供复核。
- s07_faithfulness/README.zh.md：经源码和运行结果核对后的课程版本。
- private/：完整 prompt / response 的本地副本，默认不提交。

原始生成稿把固定标注称为“人工”，最终课程与报告已明确改为课程预设标注；
这些样本没有经过独立人工双标审核。生成内容仍需校核。课程的可运行代码、测试和 Docker 配置由项目维护者实现，
不把语言模型输出直接当成“代码已经运行通过”的证据。

## 重建样章

全课程通用约束见 [Prompt Master 教材提示词](textbook_prompt.md)，
当前课实际输入见 [lesson_brief.md](lesson_brief.md)。

```sh
uv run python tools/generate_lesson.py --backend codex
```

需要本机 Codex 已登录。也可使用 --backend openai，并按Docker说明配置模型。
生成器写入原始输出目录，不会自动覆盖已经审核的课程文件。
