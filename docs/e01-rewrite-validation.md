# 第1课图文改写验收

这次改写采用 Learn Claude Code 的正文结构：问题、解决方案、工作原理、相对一次模型问答的变更、试一下、接下来。工作原理按六步带读实际函数；异常、验收边界、框架来源与首次实验放在附页。

## 改了哪些内容

- 主文围绕创建并运行 `hello.py`，解释任务、动作、真实输出与独立验收。
- 两张关键图对应 `code.py` 的执行循环，以及 `eval.py` 的独立验收路径；同时提供可编辑 draw.io 源文件和 PNG。
- 源码导读保留 Learn Claude Code、DeepEval、Ragas 的固定版本依据，并补齐消息、预算、错误、哈希和 AST 的阅读位置。
- PocketFlow 通过原版 FetchRepo → BindLesson → WriteChapters → CombineTutorial 节点生成本次原稿，实际调用本机 Codex 一次。humanizer 审阅六节主文和六个工作步骤，代码、命令和链接在润色阶段保持一致。
- Docker 阅读页新增图片展示、点击查看原图，以及结果和本次验收附页。

## 历史记录与本次检查

首次运行的四条真实任务、8 次模型请求、4 条 Bash 命令保存在原示例报告中。它们是历史实验，不是本次改写重新测量的数字。

`code.py`、`eval.py`、`cases.jsonl` 和 `example_report.json` 与改写前逐文件 SHA-256 比较保持一致。原 PocketFlow 原稿和凭证归档在 `generation/archive/e01-first-generation`，本次原稿与发布稿分别保留。

本地与 Docker 断网环境均为78项测试通过；项目自有代码 Ruff 检查通过。测试有1条既有 DeepEval DAG 接口弃用警告，不影响通过。浏览器已实际检查两张图：均成功加载，按正文宽度缩放，无横向溢出；点击可查看原图。飞书发布与回读另记录在同步凭证中。机器记录见 [JSON](https://github.com/lovits/learn-agent-evaluation/blob/main/docs/e01-rewrite-validation.json)。
