# Docker与第1课运行

## 模型在本机，命令在容器

宿主机先运行`python3 tools/model_bridge.py`，默认监听127.0.0.1:8766。
Docker使用host.docker.internal访问这个本机入口。无需将Codex登录文件或API Key挂载到容器。
Linux原生Docker需要让host.docker.internal解析到宿主机，并确认能访问该本机入口；
本轮实际验证环境为macOS Docker Desktop。当前不把Linux宿主机网络兼容性标为已测。

```sh
docker compose up --build -d
docker compose run --rm -T course run --case list_files
```

课内模型只提供tool_calls/answer，循环在Docker执行Bash。预设模型只出现在离线单元测试，
示例运行报告使用live_codex_bridge，并保留模型请求、实际命令与状态。

## 挂载与独立验收

| 目录 | Agent容器 | verifier容器 |
|---|---|---|
| knowledge_base | 只读 | 不需要 |
| workspaces | 可写 | 只读 |
| runs | 写轨迹 | 写评分 |
| evaluation_private | 不挂载，镜像也不包含 | /verification只读 |

```sh
docker compose --profile verify run --rm -T verifier verify --run-id 实际run_id
```

verifier没有外部网络，也不调用模型。它在Agent结束后核对固定任务合同。
hello任务限定一条print语句；AST合同接受引号/注释变化，但并非任意程序功能证明。

## 自定义与停止

.env.example包含阅读端口、知识库路径、模型入口与UID/GID示例。修改知识库目录前先创建目录。
Linux文件权限需要与宿主机用户一致；macOS Docker Desktop的共享目录本轮已验证。

```sh
docker compose down
```

宿主机模型入口在对应终端Ctrl+C停止。停止容器不删除workspaces和runs。

## 教材生成

实际代码和实验通过后，在宿主机执行：

```sh
uv run python tools/generate_lesson.py
```

它只读取第1课白名单材料，原始输出保存在generation/output/e01_agent_baseline，
不会自动覆盖审校后的教材。Codex CLI只需要安装在宿主机。

## 第2课：工具与轨迹

模型入口仍使用 `python3 tools/model_bridge.py`。如果入口是在更新代码前启动的，请先停止旧进程再启动。
Docker 更新后用 `docker compose up --build -d` 启动阅读器，打开 http://localhost:8765/lesson2 。

```sh
docker compose run --rm -T course run-e02 --case edit_and_run
docker compose --profile verify run --rm -T verifier verify-e02 --run-id 实际run_id
python3 tools/run_e02.py
```

第2课报告前缀为 e02、grade-e02、e02-suite。每次任务独立创建练习目录；验收器继续断网运行，
只读练习目录和 evaluation_private/e02.json。它构造并往返恢复四种原生SDK样本，不调用模型裁判。
权限实验的危险命令批准回调固定拒绝。Bash规则是教学策略，不能保证拦截任意危险命令。
知识库仍只读挂载，本课尚未接入检索。

## 第8课：独立数据生成与审核

数据生成器与参考审核器在宿主机两个终端分别启动。它们复用本机登录，角色提示词与端口分开，底层模型来源相同，不能据此声称独立模型投票。

```sh
python3 tools/generation_bridge.py
```

```sh
python3 tools/judge_bridge.py
```

随后运行：

```sh
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e08_datasets.code
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e08_datasets.eval
```

知识库继续只读挂载；生成读取e04/auth.md与e04/limits.md，记录当前内容哈希。报告写runs/e08-dataset.json；断网验收写runs/e08-dataset-grade.json，重跑前请另存需要比较的记录。本课不运行目标Agent。阅读器更新后打开 /lesson8，候选样本仍待人工确认。

`.env`可分别覆盖GENERATION_BRIDGE_URL与JUDGE_BRIDGE_URL；不要把服务端登录凭据写进环境文件或镜像。教材生成仍在宿主机使用`uv run python tools/generate_lesson.py --lesson e08`，原稿与发布正文分开保存。

## 第9课：有顺序的版本比较

先运行development，保存开发报告、冻结决定与manifest；再运行holdout。代码、任务、文档或协议哈希不一致时会拒绝沿用旧决定。每次真实运行使用独立workspace；断网verifier从只读挂载目录重读产物。

```sh
docker compose run --rm -T --entrypoint python course -m lessons.e09_comparison.code --phase development
docker compose run --rm -T --entrypoint python course -m lessons.e09_comparison.code --phase holdout
docker compose --profile verify run --rm -T --entrypoint python verifier -m lessons.e09_comparison.eval
```

应用使用8766入口；`eval --repeat-judge`是可选联网裁判阶段，使用8768入口。默认eval不调用模型，只分析真实报告和文件。partial文件在每个完成运行后更新，不能作为完整实验；同名报告会覆盖，保留旧对照前先另存。
