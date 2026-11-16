# 本次实际验证记录

本页为已有Faithfulness回放工程的验证记录，哈希对应当次实现。新的课程设计核验见
[课程设计核验](curriculum-validation.md)，不将规划中的编程Agent实验列作已完成。

验证日期：2026-11-16。环境为 macOS Docker Desktop、Linux/arm64 容器、Python 3.11。
SDK 固定版本：DeepEval 4.3.4、Ragas 0.4.4；源码 commit 见 references/versions.json。
本页只记录实际完成的步骤。机器可读记录在 docs/validation.json，含代码与配置哈希。

| 检查 | 实际结果 |
|---|---|
| 原版 PocketFlow 节点 | FetchRepo → BindLesson → WriteChapters → CombineTutorial 完成 |
| 生成模型 | 复用本机 Codex 登录，1 次生成调用，保留原稿与调用哈希 |
| 本地测试 | 20 项通过 |
| 镜像构建与服务 | Docker 构建成功；Compose 健康；12 个课程入口 HTTP 200 |
| 断网真实 SDK 回放 | --network none 下，5 个案例全部得到预期值 |
| 容器内测试 | 20 项通过，6.75 秒；全程无外部网络 |
| 代码检查 | 容器内 Ruff 通过 |
| 默认知识库 | 挂载两个文档；退款政策 SHA 与 fixture 一致 |
| 只读边界 | 容器尝试打开政策文件写入，返回只读文件系统错误 |
| 自定义挂载 | 搜索读到新规则；旧回放以退出码 1 拒绝继续评分 |
| 持久化 | 服务重启后，宿主机报告存在，课程页仍可读取 |
| 阅读体验 | 桌面 1176px、手机 390px 视觉检查；无横向溢出；搜索表单可用 |
| 上游文件 | PocketFlow 8 个文件保持字节一致；SDK 6 份快照哈希测试通过 |

## 实际回放结果

| 案例 | DeepEval 默认 | 惩罚歧义 | Ragas |
|---|---:|---:|---:|
| supported | 1 | 1 | 1 |
| unsupported | 1 | 0 | 0 |
| contradicted | 0 | 0 | 0 |
| mixed | 2/3 | 1/3 | 1/3 |
| no_claims | 1 | 1 | null |

[容器生成的完整示例报告](../s07_faithfulness/example_report.json)包含版本、证据哈希、
预设声明、SDK 请求的 schema、各阶段响应和逐条裁决。特殊值按严格 JSON 保存。
这些是课程预设结构化输出下的聚合结果，没有测量模型实际判断能力。

## 如何复核

```sh
docker compose up --build -d
docker compose exec course python s07_faithfulness/code.py
docker compose exec course python -m pytest -q
docker compose exec course ruff check eval_course s07_faithfulness/code.py tests tools
```

已建镜像的纯断网测试：

```sh
docker run --rm --network none --entrypoint python learn-agent-evaluation:local -m pytest -q
```

固定样本测试显式读取镜像内的示例知识库，挂载测试则读取运行时目录，避免把两者混为一谈。
交付前补齐教学文档和验证报告，并重新构建课程镜像；上表记录的是功能代码的实际验证。
GitHub 工作流会在新的提交上构建并执行断网测试，其状态以仓库 Actions 页面为准。

## 未进行的验证

- 未配置独立裁判 API Key，因此没有运行 live 模型实验；不声称已测模型准确率、费用或延迟。
- PocketFlow 的 OpenAI 接口后端未运行；本次运行的是用户指定的 Codex 后端。
- 其他 23 课仍处于路线阶段，不把它们算作已实现、已测试的课程。
